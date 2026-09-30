from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_BASE_PREFIX = (
    "gold/analytics/fii_price_history"
)


def load_price_history(
    path: Path = PRICE_HISTORY_PATH,
) -> pd.DataFrame:
    """
    Carrega o Gold Analytics FII Price History
    produzido pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            "FII Price History não encontrado: "
            f"{path}"
        )

    print(
        f"Carregando Price History: {path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    if "trade_date" not in dataframe.columns:
        raise ValueError(
            "Price History não possui "
            "a coluna trade_date."
        )

    if dataframe.empty:
        raise ValueError(
            "Price History está vazio."
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
    da partição mensal.

    gold_created_at é removido porque representa
    metadata operacional da execução e não deve
    alterar a identidade lógica do dataset.
    """

    canonical = dataframe.copy()

    canonical = canonical.drop(
        columns=[
            "gold_created_at",
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
    month: int,
) -> str:
    """
    Monta a chave S3 da partição mensal.
    """

    return (
        f"{S3_BASE_PREFIX}/"
        f"year={year:04d}/"
        f"month={month:02d}/"
        "fii_price_history.parquet"
    )


def publish_partition(
    dataframe: pd.DataFrame,
    year: int,
    month: int,
    temporary_directory: Path,
    force: bool = False,
) -> str:
    """
    Materializa uma partição mensal temporária
    em Parquet e publica no S3.
    """

    partition = dataframe[
        (
            dataframe["trade_date"].dt.year
            == year
        )
        &
        (
            dataframe["trade_date"].dt.month
            == month
        )
    ].copy()

    if partition.empty:
        raise ValueError(
            "Partição mensal vazia: "
            f"{year:04d}-{month:02d}"
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
            f"fii_price_history_"
            f"{year:04d}_{month:02d}.parquet"
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
        month=month,
    )

    print()
    print(
        "--------------------------------------"
    )
    print(
        f"Partição: {year:04d}-{month:02d}"
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


def publish_price_history(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> list[str]:
    """
    Publica o Price History em partições
    mensais year/month.
    """

    partitions = (
        dataframe[
            [
                "trade_date",
            ]
        ]
        .assign(
            year=lambda frame: (
                frame["trade_date"].dt.year
            ),
            month=lambda frame: (
                frame["trade_date"].dt.month
            ),
        )
        [
            [
                "year",
                "month",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            by=[
                "year",
                "month",
            ]
        )
        .itertuples(
            index=False,
            name=None,
        )
    )

    partition_list = list(
        partitions
    )

    if not partition_list:
        raise ValueError(
            "Nenhuma partição mensal encontrada."
        )

    print()
    print(
        "======================================"
    )
    print(
        "FII PRICE HISTORY -> S3"
    )
    print(
        "======================================"
    )
    print(
        f"Linhas totais: "
        f"{len(dataframe):,}"
    )
    print(
        f"Partições mensais: "
        f"{len(partition_list):,}"
    )
    print(
        "Período: "
        f"{dataframe['trade_date'].min().date()} "
        "-> "
        f"{dataframe['trade_date'].max().date()}"
    )

    uploaded_uris: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="fii_price_history_"
    ) as temporary_directory_name:

        temporary_directory = Path(
            temporary_directory_name
        )

        for year, month in partition_list:
            s3_uri = publish_partition(
                dataframe=dataframe,
                year=int(year),
                month=int(month),
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
    Carrega o Gold Price History existente
    e publica suas partições mensais no S3.
    """

    dataframe = load_price_history()

    uploaded_uris = (
        publish_price_history(
            dataframe=dataframe,
            force=force,
        )
    )

    print()
    print(
        "======================================"
    )
    print(
        "FII PRICE HISTORY PUBLICADO"
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
            "Publica o Gold Analytics "
            "FII Price History no Data Lake S3 "
            "em partições mensais."
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