from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FII_FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_features"
    / "fii_features.parquet"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_BASE_PREFIX = "gold/ml/fii_features"


def load_fii_features(
    path: Path = FII_FEATURES_PATH,
) -> pd.DataFrame:
    """
    Carrega a Gold ML FII Features produzida
    pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"FII Features não encontrado: {path}"
        )

    print(
        f"Carregando Gold ML FII Features: {path}"
    )

    dataframe = pd.read_parquet(path)

    if dataframe.empty:
        raise ValueError(
            "Gold ML FII Features está vazia."
        )

    required_columns = [
        "feature_date",
        "ticker",
        "feature_ready",
        "feature_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Gold ML FII Features possui "
            "colunas obrigatórias ausentes: "
            f"{missing_columns}"
        )

    dataframe = dataframe.copy()

    dataframe["feature_date"] = pd.to_datetime(
        dataframe["feature_date"],
        errors="raise",
    )

    return dataframe


def calculate_partition_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico
    da partição.

    features_created_at é metadata operacional
    e não participa da identidade lógica.
    """

    canonical = dataframe.copy()

    canonical = canonical.drop(
        columns=[
            "features_created_at",
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
        "fii_features.parquet"
    )


def publish_partition(
    dataframe: pd.DataFrame,
    year: int,
    month: int,
    temporary_directory: Path,
    force: bool = False,
) -> str:
    """
    Materializa e publica uma partição mensal.
    """

    partition = dataframe[
        (
            dataframe["feature_date"].dt.year
            == year
        )
        &
        (
            dataframe["feature_date"].dt.month
            == month
        )
    ].copy()

    if partition.empty:
        raise ValueError(
            "Partição mensal vazia: "
            f"{year}-{month:02d}"
        )

    partition = (
        partition.sort_values(
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

    local_path = (
        temporary_directory
        / (
            "fii_features_"
            f"{year}_{month:02d}.parquet"
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

    ready_count = int(
        partition[
            "feature_ready"
        ].sum()
    )

    not_ready_count = (
        len(partition)
        - ready_count
    )

    print()
    print(
        "--------------------------------------"
    )
    print(
        f"Partição: {year}-{month:02d}"
    )
    print(
        f"Linhas:   {len(partition):,}"
    )
    print(
        f"Ready:    {ready_count:,}"
    )
    print(
        f"Not ready:{not_ready_count:,}"
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


def publish_fii_features(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> list[str]:
    """
    Publica FII Features em partições mensais.
    """

    partitions = (
        dataframe[
            "feature_date"
        ]
        .dt.to_period(
            "M"
        )
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if not partitions:
        raise ValueError(
            "Nenhuma partição mensal encontrada."
        )

    ready_count = int(
        dataframe[
            "feature_ready"
        ].sum()
    )

    not_ready_count = (
        len(dataframe)
        - ready_count
    )

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII FEATURES -> S3"
    )
    print(
        "======================================"
    )
    print(
        f"Linhas totais: "
        f"{len(dataframe):,}"
    )
    print(
        f"Feature ready: "
        f"{ready_count:,}"
    )
    print(
        f"Feature not ready: "
        f"{not_ready_count:,}"
    )
    print(
        f"Partições mensais: "
        f"{len(partitions):,}"
    )
    print(
        "Período: "
        f"{dataframe['feature_date'].min().date()} "
        "-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    feature_versions = sorted(
        dataframe[
            "feature_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    print(
        f"Feature version: "
        f"{feature_versions}"
    )

    uploaded_uris: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="fii_features_"
    ) as temporary_directory_name:

        temporary_directory = Path(
            temporary_directory_name
        )

        for period in partitions:
            s3_uri = publish_partition(
                dataframe=dataframe,
                year=int(
                    period.year
                ),
                month=int(
                    period.month
                ),
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
    Carrega e publica Gold ML FII Features.
    """

    dataframe = load_fii_features()

    uploaded_uris = (
        publish_fii_features(
            dataframe=dataframe,
            force=force,
        )
    )

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII FEATURES PUBLICADO"
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
            "Publica Gold ML FII Features no "
            "Data Lake S3 em partições mensais."
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