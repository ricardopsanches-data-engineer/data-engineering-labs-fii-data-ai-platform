from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRAINING_DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
    / "fii_training_dataset.parquet"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_PREFIX = (
    "gold/ml/"
    "fii_training_dataset"
)


def load_training_dataset(
    path: Path = TRAINING_DATASET_PATH,
) -> pd.DataFrame:
    """
    Carrega o Gold ML FII Training Dataset
    produzido pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            "FII Training Dataset não encontrado: "
            f"{path}"
        )

    print(
        "Carregando Gold ML FII Training Dataset: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    if dataframe.empty:
        raise ValueError(
            "Gold ML FII Training Dataset está vazio."
        )

    required_columns = [
        "ticker",
        "feature_date",
        "target_date",
        "ml_eligible",
        "training_dataset_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Gold ML FII Training Dataset possui "
            "colunas obrigatórias ausentes: "
            f"{missing_columns}"
        )

    dataframe = dataframe.copy()

    dataframe["feature_date"] = pd.to_datetime(
        dataframe["feature_date"],
        errors="raise",
    )

    dataframe["target_date"] = pd.to_datetime(
        dataframe["target_date"],
        errors="raise",
    )

    return dataframe


def calculate_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico.

    Timestamps operacionais de criação não
    participam da identidade lógica.
    """

    canonical = dataframe.copy()

    canonical = canonical.drop(
        columns=[
            "features_created_at",
            "training_dataset_created_at",
        ],
        errors="ignore",
    )

    canonical = (
        canonical.sort_values(
            by=[
                "feature_date",
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


def build_s3_key(
    year: int,
    month: int,
) -> str:
    """
    Monta a chave S3 da partição mensal.
    """

    return (
        f"{S3_PREFIX}/"
        f"year={year:04d}/"
        f"month={month:02d}/"
        "fii_training_dataset.parquet"
    )


def publish_partition(
    dataframe: pd.DataFrame,
    year: int,
    month: int,
    force: bool = False,
) -> str:
    """
    Publica uma partição mensal no S3.
    """

    ordered = (
        dataframe.sort_values(
            by=[
                "feature_date",
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

    s3_key = build_s3_key(
        year=year,
        month=month,
    )

    eligible_count = int(
        ordered[
            "ml_eligible"
        ].sum()
    )

    ineligible_count = (
        len(ordered)
        - eligible_count
    )

    versions = sorted(
        ordered[
            "training_dataset_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    print()
    print(
        "--------------------------------------"
    )

    print(
        f"Partição: "
        f"{year:04d}-{month:02d}"
    )

    print(
        f"Linhas:   "
        f"{len(ordered):,}"
    )

    print(
        f"Eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"Ineligible:"
        f"{ineligible_count:,}"
    )

    print(
        f"Version: "
        f"{versions}"
    )

    print(
        "Fingerprint lógico: "
        f"{content_sha256}"
    )

    print(
        "Destino: "
        f"s3://{BUCKET_NAME}/{s3_key}"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = (
            Path(temp_dir)
            / "fii_training_dataset.parquet"
        )

        ordered.to_parquet(
            temp_path,
            index=False,
        )

        return upload_file(
            local_path=temp_path,
            bucket_name=BUCKET_NAME,
            s3_key=s3_key,
            content_sha256=content_sha256,
            force=force,
        )


def publish_training_dataset(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> list[str]:
    """
    Publica o Training Dataset particionado
    mensalmente por feature_date.
    """

    dataframe = dataframe.copy()

    dataframe["partition_year"] = (
        dataframe[
            "feature_date"
        ].dt.year
    )

    dataframe["partition_month"] = (
        dataframe[
            "feature_date"
        ].dt.month
    )

    partition_count = (
        dataframe[
            [
                "partition_year",
                "partition_month",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    eligible_count = int(
        dataframe[
            "ml_eligible"
        ].sum()
    )

    ineligible_count = (
        len(dataframe)
        - eligible_count
    )

    versions = sorted(
        dataframe[
            "training_dataset_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII TRAINING DATASET -> S3"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas totais: "
        f"{len(dataframe):,}"
    )

    print(
        f"Colunas: "
        f"{len(dataframe.columns) - 2:,}"
    )

    print(
        f"ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"ML ineligible: "
        f"{ineligible_count:,}"
    )

    print(
        f"Partições mensais: "
        f"{partition_count:,}"
    )

    print(
        "Feature date: "
        f"{dataframe['feature_date'].min().date()} "
        "-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        "Target date: "
        f"{dataframe['target_date'].min().date()} "
        "-> "
        f"{dataframe['target_date'].max().date()}"
    )

    print(
        f"Training Dataset version: "
        f"{versions}"
    )

    published_uris: list[str] = []

    grouped = dataframe.groupby(
        [
            "partition_year",
            "partition_month",
        ],
        sort=True,
    )

    for (
        year,
        month,
    ), partition in grouped:
        partition = partition.drop(
            columns=[
                "partition_year",
                "partition_month",
            ]
        )

        uri = publish_partition(
            dataframe=partition,
            year=int(year),
            month=int(month),
            force=force,
        )

        published_uris.append(
            uri
        )

    return published_uris


def run(
    force: bool = False,
) -> list[str]:
    """
    Executa publicação do Gold ML
    FII Training Dataset.
    """

    dataframe = load_training_dataset()

    published_uris = (
        publish_training_dataset(
            dataframe=dataframe,
            force=force,
        )
    )

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII TRAINING DATASET PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Partições: "
        f"{len(published_uris):,}"
    )

    for uri in published_uris:
        print(
            f"  {uri}"
        )

    return published_uris


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publica Gold ML FII Training Dataset "
            "no Data Lake S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar nova "
            "versão de objetos já existentes."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()