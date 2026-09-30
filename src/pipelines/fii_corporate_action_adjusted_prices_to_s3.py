from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ADJUSTED_PRICES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
    / "fii_corporate_action_adjusted_prices.parquet"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_BASE_PREFIX = (
    "gold/analytics/"
    "fii_corporate_action_adjusted_prices"
)


def load_adjusted_prices(
    path: Path = ADJUSTED_PRICES_PATH,
) -> pd.DataFrame:
    """
    Carrega o Gold Analytics Corporate Action
    Adjusted Prices produzido pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            "Corporate Action Adjusted Prices "
            f"não encontrado: {path}"
        )

    print(
        "Carregando Corporate Action "
        f"Adjusted Prices: {path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    if dataframe.empty:
        raise ValueError(
            "Corporate Action Adjusted Prices "
            "está vazio."
        )

    if "trade_date" not in dataframe.columns:
        raise ValueError(
            "Corporate Action Adjusted Prices "
            "não possui trade_date."
        )

    dataframe = dataframe.copy()

    dataframe["trade_date"] = pd.to_datetime(
        dataframe["trade_date"],
        errors="raise",
    )

    return dataframe


def calculate_partition_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico
    da partição anual.

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

    sort_columns = [
        column
        for column in [
            "trade_date",
            "ticker",
        ]
        if column in canonical.columns
    ]

    if sort_columns:
        canonical = (
            canonical.sort_values(
                by=sort_columns,
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


def build_partition_s3_key(
    year: int,
) -> str:
    """
    Monta a chave S3 da partição anual.
    """

    return (
        f"{S3_BASE_PREFIX}/"
        f"year={year:04d}/"
        "fii_corporate_action_adjusted_prices.parquet"
    )


def publish_partition(
    dataframe: pd.DataFrame,
    year: int,
    temporary_directory: Path,
    force: bool = False,
) -> str:
    """
    Materializa e publica uma partição anual.
    """

    partition = dataframe[
        dataframe["trade_date"].dt.year
        == year
    ].copy()

    if partition.empty:
        raise ValueError(
            f"Partição anual vazia: {year}"
        )

    partition = (
        partition.sort_values(
            by=[
                "trade_date",
                "ticker",
            ],
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )

    local_path = (
        temporary_directory
        / (
            "fii_corporate_action_"
            f"adjusted_prices_{year}.parquet"
        )
    )

    partition.to_parquet(
        local_path,
        index=False,
    )

    content_sha256 = (
        calculate_partition_content_sha256(
            partition
        )
    )

    s3_key = build_partition_s3_key(
        year=year,
    )

    print()
    print(
        "--------------------------------------"
    )
    print(
        f"Partição: {year}"
    )
    print(
        f"Linhas:   {len(partition):,}"
    )
    print(
        "Fingerprint lógico: "
        f"{content_sha256}"
    )
    print(
        "Destino: "
        f"s3://{BUCKET_NAME}/{s3_key}"
    )

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        content_sha256=content_sha256,
        force=force,
    )


def publish_adjusted_prices(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> list[str]:
    """
    Publica o Corporate Action Adjusted Prices
    em partições anuais.
    """

    years = sorted(
        dataframe[
            "trade_date"
        ]
        .dt.year
        .drop_duplicates()
        .astype(int)
        .tolist()
    )

    if not years:
        raise ValueError(
            "Nenhuma partição anual encontrada."
        )

    print()
    print(
        "======================================"
    )
    print(
        "CORPORATE ACTION ADJUSTED PRICES -> S3"
    )
    print(
        "======================================"
    )
    print(
        f"Linhas totais: "
        f"{len(dataframe):,}"
    )
    print(
        f"Partições anuais: "
        f"{len(years):,}"
    )
    print(
        "Período: "
        f"{dataframe['trade_date'].min().date()} "
        "-> "
        f"{dataframe['trade_date'].max().date()}"
    )

    uploaded_uris: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="fii_adjusted_prices_"
    ) as temporary_directory_name:

        temporary_directory = Path(
            temporary_directory_name
        )

        for year in years:
            s3_uri = publish_partition(
                dataframe=dataframe,
                year=year,
                temporary_directory=(
                    temporary_directory
                ),
                force=force,
            )

            uploaded_uris.append(
                s3_uri
            )

    return uploaded_uris


def run(
    force: bool = False,
) -> list[str]:
    """
    Carrega e publica o Gold Analytics
    Corporate Action Adjusted Prices.
    """

    dataframe = load_adjusted_prices()

    uploaded_uris = (
        publish_adjusted_prices(
            dataframe=dataframe,
            force=force,
        )
    )

    print()
    print(
        "======================================"
    )
    print(
        "ADJUSTED PRICES PUBLICADO"
    )
    print(
        "======================================"
    )
    print(
        f"Partições: "
        f"{len(uploaded_uris):,}"
    )

    for uri in uploaded_uris:
        print(
            f"  {uri}"
        )

    return uploaded_uris


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publica o Gold Analytics Corporate "
            "Action Adjusted Prices no Data Lake "
            "S3 em partições anuais."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar nova "
            "versão de partições já existentes."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()