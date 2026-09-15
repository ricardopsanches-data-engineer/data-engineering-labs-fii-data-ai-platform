from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from src.ingestion.b3.parser import parse_b3_download
from src.storage.s3_silver import upload_silver_file


SILVER_ROOT = Path("data/silver/b3")


def validate_b3_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    """
    Executa validações mínimas antes da escrita na camada Silver.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "instrument_id",
        "instrument_id_type",
        "market",
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(missing_columns)
        )

    if dataframe.empty:
        raise ValueError(
            "O DataFrame da B3 está vazio."
        )

    if dataframe["trade_date"].isna().all():
        raise ValueError(
            "Nenhuma data de pregão válida foi encontrada."
        )

    unique_trade_dates = (
        dataframe["trade_date"]
        .dropna()
        .dt.date
        .unique()
    )

    if len(unique_trade_dates) != 1:
        raise ValueError(
            "Esperávamos exatamente uma trade_date "
            "no arquivo diário da B3, mas foram encontradas: "
            f"{unique_trade_dates.tolist()}"
        )


def build_silver_output_path(
    dataframe: pd.DataFrame,
) -> Path:
    """
    Constrói o caminho particionado da camada Silver.
    """

    trade_date = (
        dataframe["trade_date"]
        .dropna()
        .iloc[0]
    )

    output_directory = (
        SILVER_ROOT
        / f"year={trade_date.year:04d}"
        / f"month={trade_date.month:02d}"
        / f"day={trade_date.day:02d}"
    )

    return (
        output_directory
        / "b3_trades.parquet"
    )


def write_silver_parquet(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Grava o DataFrame da B3 em formato Parquet.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        output_path,
        index=False,
    )


def transform_b3_raw_to_silver(
    raw_zip_path: str | Path,
    upload_to_s3: bool = False,
    force: bool = False,
) -> tuple[Path, dict[str, object]]:
    """
    Executa a transformação completa RAW -> Silver.

    Fluxo:
        ZIP RAW B3
            -> parser
            -> validação
            -> Parquet Silver
            -> upload S3 opcional
    """

    raw_zip_path = Path(raw_zip_path)

    if not raw_zip_path.exists():
        raise FileNotFoundError(
            f"Arquivo RAW não encontrado: {raw_zip_path}"
        )

    print("======================================")
    print("B3 RAW -> SILVER")
    print("======================================")
    print(f"RAW: {raw_zip_path}")
    print()

    dataframe, source_metadata = parse_b3_download(
        raw_zip_path
    )

    print(
        "Registros extraídos: "
        f"{len(dataframe):,}"
    )

    validate_b3_dataframe(
        dataframe
    )

    print(
        "Validação do DataFrame: OK"
    )

    output_path = build_silver_output_path(
        dataframe
    )

    write_silver_parquet(
        dataframe=dataframe,
        output_path=output_path,
    )

    trade_date = (
        dataframe["trade_date"]
        .dropna()
        .iloc[0]
        .date()
        .isoformat()
    )

    silver_metadata: dict[str, object] = {
        "source": "b3",
        "raw_file": str(raw_zip_path),
        "silver_file": str(output_path),
        "records": len(dataframe),
        "trade_date": trade_date,
        "outer_zip": source_metadata["outer_zip"],
        "inner_zip": source_metadata["inner_zip"],
        "xml_file": source_metadata["xml_file"],
    }

    print()
    print(
        "Silver Parquet criado:"
    )

    print(
        f"  {output_path}"
    )

    print(
        "Registros gravados: "
        f"{len(dataframe):,}"
    )

    if upload_to_s3:
        bucket_name = os.environ.get(
            "FII_DATA_LAKE_BUCKET"
        )

        if not bucket_name:
            raise RuntimeError(
                "FII_DATA_LAKE_BUCKET não está configurado."
            )

        print()
        print(
            "Iniciando upload Silver para S3..."
        )

        s3_uri = upload_silver_file(
            local_path=output_path,
            bucket_name=bucket_name,
            records=len(dataframe),
            source="b3",
            raw_file=source_metadata["outer_zip"],
            trade_date=trade_date,
            force=force,
        )

        silver_metadata["s3_uri"] = s3_uri

    print()
    print(
        "B3 RAW -> SILVER concluído."
    )

    return output_path, silver_metadata


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Transforma o RAW diário da B3 "
            "em Parquet na camada Silver."
        )
    )

    parser.add_argument(
        "raw_zip_path",
        help=(
            "Caminho para o ZIP RAW diário da B3."
        ),
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help=(
            "Realiza upload do Parquet Silver para o S3."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite criar nova versão no S3 "
            "quando já existe objeto diferente."
        ),
    )

    args = parser.parse_args()

    transform_b3_raw_to_silver(
        raw_zip_path=args.raw_zip_path,
        upload_to_s3=args.upload,
        force=args.force,
    )


if __name__ == "__main__":
    main()