from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

import pandas as pd

from src.ingestion.cvm.parser import parse_cvm_class_register
from src.storage.s3_silver import upload_silver_file


DEFAULT_SILVER_ROOT = Path(
    "data/silver/cvm"
)


def validate_cvm_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "ID_Registro_Fundo",
        "ID_Registro_Classe",
        "CNPJ_Classe",
        "Codigo_CVM",
        "Tipo_Classe",
        "Denominacao_Social",
        "Situacao",
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
            "O DataFrame da CVM está vazio."
        )


def build_silver_output_path(
    reference_date: date,
    silver_root: str | Path = DEFAULT_SILVER_ROOT,
) -> Path:
    silver_root = Path(
        silver_root
    )

    output_directory = (
        silver_root
        / f"year={reference_date.year:04d}"
        / f"month={reference_date.month:02d}"
        / f"day={reference_date.day:02d}"
    )

    return (
        output_directory
        / "cvm_fund_classes.parquet"
    )


def build_silver_s3_key(
    reference_date: date,
) -> str:
    return (
        "silver/cvm/"
        f"year={reference_date.year:04d}/"
        f"month={reference_date.month:02d}/"
        f"day={reference_date.day:02d}/"
        "cvm_fund_classes.parquet"
    )


def write_silver_parquet(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        output_path,
        index=False,
    )


def transform_cvm_raw_to_silver(
    raw_zip_path: str | Path,
    reference_date: date,
    silver_root: str | Path = DEFAULT_SILVER_ROOT,
    upload_to_s3: bool = False,
    force: bool = False,
) -> tuple[Path, dict[str, object]]:
    raw_zip_path = Path(
        raw_zip_path
    )

    if not raw_zip_path.exists():
        raise FileNotFoundError(
            f"Arquivo RAW não encontrado: {raw_zip_path}"
        )

    print("======================================")
    print("CVM RAW -> SILVER")
    print("======================================")
    print(f"RAW: {raw_zip_path}")
    print(f"Reference date: {reference_date}")
    print(f"Silver root: {silver_root}")
    print()

    dataframe = parse_cvm_class_register(
        raw_zip_path
    )

    print(
        "Registros extraídos: "
        f"{len(dataframe):,}"
    )

    validate_cvm_dataframe(
        dataframe
    )

    print(
        "Validação do DataFrame: OK"
    )

    output_path = build_silver_output_path(
        reference_date=reference_date,
        silver_root=silver_root,
    )

    write_silver_parquet(
        dataframe=dataframe,
        output_path=output_path,
    )

    s3_key = build_silver_s3_key(
        reference_date
    )

    silver_metadata: dict[str, object] = {
        "source": "cvm",
        "raw_file": str(raw_zip_path),
        "silver_file": str(output_path),
        "s3_key": s3_key,
        "records": len(dataframe),
        "reference_date": reference_date.isoformat(),
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
            s3_key=s3_key,
            records=len(dataframe),
            source="cvm",
            raw_file=raw_zip_path.name,
            reference_date=reference_date.isoformat(),
            force=force,
        )

        silver_metadata["s3_uri"] = (
            s3_uri
        )

    print()
    print(
        "CVM RAW -> SILVER concluído."
    )

    return (
        output_path,
        silver_metadata,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Transforma o RAW cadastral da CVM "
            "em Parquet na camada Silver."
        )
    )

    parser.add_argument(
        "raw_zip_path",
        help="Caminho para o ZIP RAW da CVM.",
    )

    parser.add_argument(
        "--reference-date",
        required=True,
        help="Data de referência no formato YYYY-MM-DD.",
    )

    parser.add_argument(
        "--silver-root",
        default=str(
            DEFAULT_SILVER_ROOT
        ),
    )

    parser.add_argument(
        "--upload",
        action="store_true",
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    transform_cvm_raw_to_silver(
        raw_zip_path=args.raw_zip_path,
        reference_date=date.fromisoformat(
            args.reference_date
        ),
        silver_root=args.silver_root,
        upload_to_s3=args.upload,
        force=args.force,
    )


if __name__ == "__main__":
    main()