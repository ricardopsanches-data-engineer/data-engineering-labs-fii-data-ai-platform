from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PRICE_DISCONTINUITIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_discontinuities"
    / "fii_price_discontinuities.parquet"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_KEY = (
    "gold/analytics/"
    "fii_price_discontinuities/"
    "fii_price_discontinuities.parquet"
)


def load_price_discontinuities(
    path: Path = PRICE_DISCONTINUITIES_PATH,
) -> pd.DataFrame:
    """
    Carrega o Gold Analytics FII Price
    Discontinuities produzido pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            "FII Price Discontinuities "
            f"não encontrado: {path}"
        )

    print(
        "Carregando FII Price Discontinuities: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    if dataframe.empty:
        raise ValueError(
            "FII Price Discontinuities está vazio."
        )

    required_columns = [
        "ticker",
        "event_date",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "FII Price Discontinuities possui "
            "colunas obrigatórias ausentes: "
            f"{missing_columns}"
        )

    dataframe = dataframe.copy()

    dataframe["event_date"] = pd.to_datetime(
        dataframe["event_date"],
        errors="raise",
    )

    return dataframe


def calculate_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico.

    created_at é metadata operacional e não
    participa da identidade lógica do dataset.
    """

    canonical = dataframe.copy()

    canonical = canonical.drop(
        columns=[
            "created_at",
        ],
        errors="ignore",
    )

    canonical = (
        canonical.sort_values(
            by=[
                "event_date",
                "ticker",
            ],
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )

    schema_text = "|".join(
        f"{column}:{canonical[column].dtype}"
        for column in canonical.columns
    )

    row_hashes = (
        pd.util.hash_pandas_object(
            canonical,
            index=False,
        )
        .values
        .tobytes()
    )

    sha256 = hashlib.sha256()

    sha256.update(
        schema_text.encode(
            "utf-8"
        )
    )

    sha256.update(
        row_hashes
    )

    return sha256.hexdigest()


def publish_price_discontinuities(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> str:
    """
    Publica o dataset completo no Data Lake S3.
    """

    ordered = (
        dataframe.sort_values(
            by=[
                "event_date",
                "ticker",
            ],
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )

    content_sha256 = (
        calculate_content_sha256(
            ordered
        )
    )

    print()
    print(
        "======================================"
    )
    print(
        "FII PRICE DISCONTINUITIES -> S3"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(ordered):,}"
    )

    print(
        f"Colunas: "
        f"{len(ordered.columns):,}"
    )

    print(
        "Período: "
        f"{ordered['event_date'].min().date()} "
        "-> "
        f"{ordered['event_date'].max().date()}"
    )

    print(
        "Fingerprint lógico: "
        f"{content_sha256}"
    )

    print(
        "Destino: "
        f"s3://{BUCKET_NAME}/{S3_KEY}"
    )

    return upload_file(
        local_path=PRICE_DISCONTINUITIES_PATH,
        bucket_name=BUCKET_NAME,
        s3_key=S3_KEY,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> str:
    """
    Executa publicação do Gold Analytics
    FII Price Discontinuities.
    """

    dataframe = load_price_discontinuities()

    s3_uri = publish_price_discontinuities(
        dataframe=dataframe,
        force=force,
    )

    print()
    print(
        "======================================"
    )
    print(
        "PRICE DISCONTINUITIES PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        s3_uri
    )

    return s3_uri


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publica o Gold Analytics "
            "FII Price Discontinuities no "
            "Data Lake S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar nova "
            "versão do objeto já existente."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()