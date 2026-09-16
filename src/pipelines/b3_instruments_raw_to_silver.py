from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.ingestion.b3.parser import (
    parse_b3_instrument_download,
)
from src.storage.s3_silver import (
    upload_silver_file,
)


DEFAULT_SILVER_ROOT = Path(
    "data/silver/b3-instruments"
)


def validate_b3_instruments_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    """
    Executa validações mínimas antes
    da escrita na camada Silver.
    """

    required_columns = [
        "instrument_type",
        "security_category",
        "ticker",
        "isin",
        "distribution_id",
        "cfi_code",
        "specification_code",
        "corporate_name",
        "trading_start_date",
        "trading_end_date",
        "underlying_instrument_id",
        "underlying_instrument_id_type",
        "underlying_market",
        "source_xml",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(
                missing_columns
            )
        )

    if dataframe.empty:
        raise ValueError(
            "O DataFrame de instrumentos "
            "da B3 está vazio."
        )

    if (
        dataframe["ticker"]
        .notna()
        .sum()
        == 0
    ):
        raise ValueError(
            "Nenhum ticker válido foi encontrado."
        )

    if (
        dataframe["instrument_type"]
        .notna()
        .sum()
        == 0
    ):
        raise ValueError(
            "Nenhum tipo de instrumento "
            "foi encontrado."
        )


def get_reference_date(
    source_metadata: dict[str, object],
) -> str:
    """
    Obtém a data de referência a partir
    do nome do ZIP interno.

    Exemplo:
        IN260911.zip
        ->
        2026-09-11
    """

    inner_zip = str(
        source_metadata[
            "inner_zip"
        ]
    )

    filename = Path(
        inner_zip
    ).name

    if (
        not filename.upper().startswith(
            "IN"
        )
        or not filename.lower().endswith(
            ".zip"
        )
    ):
        raise ValueError(
            "Nome inesperado de ZIP interno "
            f"de instrumentos: {filename}"
        )

    compact_date = (
        filename[2:-4]
    )

    try:
        reference_date = datetime.strptime(
            compact_date,
            "%y%m%d",
        ).date()
    except ValueError as error:
        raise ValueError(
            "Não foi possível extrair a data "
            f"de referência de {filename}."
        ) from error

    return reference_date.isoformat()


def build_silver_output_path(
    reference_date: str,
    silver_root: str | Path = (
        DEFAULT_SILVER_ROOT
    ),
) -> Path:
    """
    Constrói o caminho local particionado
    da Silver de instrumentos B3.
    """

    silver_root = Path(
        silver_root
    )

    parsed_date = pd.Timestamp(
        reference_date
    )

    output_directory = (
        silver_root
        / f"year={parsed_date.year:04d}"
        / f"month={parsed_date.month:02d}"
        / f"day={parsed_date.day:02d}"
    )

    return (
        output_directory
        / "b3_instruments.parquet"
    )


def build_silver_s3_key(
    reference_date: str,
) -> str:
    """
    Constrói a chave definitiva da Silver
    de instrumentos no S3.
    """

    parsed_date = pd.Timestamp(
        reference_date
    )

    return (
        "silver/b3-instruments/"
        f"year={parsed_date.year:04d}/"
        f"month={parsed_date.month:02d}/"
        f"day={parsed_date.day:02d}/"
        "b3_instruments.parquet"
    )


def write_silver_parquet(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Grava o DataFrame de instrumentos
    em formato Parquet.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        output_path,
        index=False,
    )


def transform_b3_instruments_raw_to_silver(
    raw_zip_path: str | Path,
    silver_root: str | Path = (
        DEFAULT_SILVER_ROOT
    ),
    upload_to_s3: bool = False,
    force: bool = False,
) -> tuple[
    Path,
    dict[str, object],
]:
    """
    Executa a transformação completa
    B3 Instruments RAW -> Silver.

    Fluxo:
        ZIP RAW
            -> parser BVBG.028.02
            -> snapshot canônico
            -> deduplicação exata
            -> validação
            -> Parquet Silver
            -> upload S3 opcional
    """

    raw_zip_path = Path(
        raw_zip_path
    )

    silver_root = Path(
        silver_root
    )

    if not raw_zip_path.exists():
        raise FileNotFoundError(
            "Arquivo RAW não encontrado: "
            f"{raw_zip_path}"
        )

    print(
        "======================================"
    )
    print(
        "B3 INSTRUMENTS RAW -> SILVER"
    )
    print(
        "======================================"
    )

    print(
        f"RAW: {raw_zip_path}"
    )

    print(
        f"Silver root: {silver_root}"
    )

    print()

    (
        dataframe,
        source_metadata,
    ) = parse_b3_instrument_download(
        raw_zip_path
    )

    print(
        "Registros após consolidação: "
        f"{len(dataframe):,}"
    )

    print(
        "Duplicidades exatas removidas: "
        f"{source_metadata['duplicates_removed']:,}"
    )

    validate_b3_instruments_dataframe(
        dataframe
    )

    print(
        "Validação do DataFrame: OK"
    )

    reference_date = get_reference_date(
        source_metadata
    )

    output_path = (
        build_silver_output_path(
            reference_date=reference_date,
            silver_root=silver_root,
        )
    )

    write_silver_parquet(
        dataframe=dataframe,
        output_path=output_path,
    )

    s3_key = build_silver_s3_key(
        reference_date
    )

    silver_metadata: dict[
        str,
        object,
    ] = {
        "source": "b3-instruments",
        "raw_file": str(
            raw_zip_path
        ),
        "silver_file": str(
            output_path
        ),
        "s3_key": s3_key,
        "records": len(
            dataframe
        ),
        "reference_date": (
            reference_date
        ),
        "outer_zip": (
            source_metadata[
                "outer_zip"
            ]
        ),
        "inner_zip": (
            source_metadata[
                "inner_zip"
            ]
        ),
        "selected_xml": (
            source_metadata[
                "selected_xml"
            ]
        ),
        "xml_count": (
            source_metadata[
                "xml_count"
            ]
        ),
        "duplicates_removed": (
            source_metadata[
                "duplicates_removed"
            ]
        ),
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
                "FII_DATA_LAKE_BUCKET "
                "não está configurado."
            )

        print()

        print(
            "Iniciando upload Silver "
            "para S3..."
        )

        s3_uri = upload_silver_file(
            local_path=output_path,
            bucket_name=bucket_name,
            s3_key=s3_key,
            records=len(
                dataframe
            ),
            source="b3-instruments",
            raw_file=str(
                source_metadata[
                    "outer_zip"
                ]
            ),
            reference_date=reference_date,
            force=force,
        )

        silver_metadata[
            "s3_uri"
        ] = s3_uri

    print()

    print(
        "B3 Instruments RAW -> "
        "SILVER concluído."
    )

    return (
        output_path,
        silver_metadata,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Transforma o Cadastro diário "
            "de Instrumentos B3 "
            "BVBG.028.02 em Parquet Silver."
        )
    )

    parser.add_argument(
        "raw_zip_path",
        help=(
            "Caminho para pesquisa-pregao.zip "
            "contendo INYYMMDD.zip."
        ),
    )

    parser.add_argument(
        "--silver-root",
        default=str(
            DEFAULT_SILVER_ROOT
        ),
        help=(
            "Diretório local usado para "
            "gerar a Silver."
        ),
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help=(
            "Realiza upload do Parquet "
            "Silver para o S3."
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

    transform_b3_instruments_raw_to_silver(
        raw_zip_path=args.raw_zip_path,
        silver_root=args.silver_root,
        upload_to_s3=args.upload,
        force=args.force,
    )


if __name__ == "__main__":
    main()