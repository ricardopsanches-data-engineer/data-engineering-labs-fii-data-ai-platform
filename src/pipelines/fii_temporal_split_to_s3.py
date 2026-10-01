from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEMPORAL_SPLIT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
)

SPLIT_FILES = {
    "train": (
        TEMPORAL_SPLIT_DIR
        / "train.parquet"
    ),
    "validation": (
        TEMPORAL_SPLIT_DIR
        / "validation.parquet"
    ),
    "test": (
        TEMPORAL_SPLIT_DIR
        / "test.parquet"
    ),
}

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_PREFIX = (
    "gold/ml/"
    "fii_temporal_split"
)


def load_split(
    split_name: str,
    path: Path,
) -> pd.DataFrame:
    """
    Carrega um split temporal produzido
    pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Split {split_name} não encontrado: "
            f"{path}"
        )

    print(
        f"Carregando split {split_name}: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    if dataframe.empty:
        raise ValueError(
            f"Split {split_name} está vazio."
        )

    required_columns = [
        "ticker",
        "feature_date",
        "target_date",
        "ml_eligible",
        "split_name",
        "split_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Split {split_name} possui "
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

    split_names = sorted(
        dataframe[
            "split_name"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if split_names != [
        split_name
    ]:
        raise ValueError(
            f"Split físico {split_name} possui "
            f"split_name incompatível: "
            f"{split_names}"
        )

    ineligible_count = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
            .fillna(False)
            .astype(bool)
        ).sum()
    )

    if ineligible_count > 0:
        raise ValueError(
            f"Split {split_name} contém "
            "samples ML inelegíveis."
        )

    return dataframe


def calculate_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico.

    Metadados puramente operacionais de criação
    não participam da identidade lógica.
    """

    canonical = dataframe.copy()

    canonical = canonical.drop(
        columns=[
            "features_created_at",
            "training_dataset_created_at",
            "split_created_at",
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
    split_name: str,
) -> str:
    """
    Monta chave S3 do split.
    """

    return (
        f"{S3_PREFIX}/"
        f"split={split_name}/"
        f"{split_name}.parquet"
    )


def publish_split(
    split_name: str,
    dataframe: pd.DataFrame,
    local_path: Path,
    force: bool = False,
) -> str:
    """
    Publica um split temporal no S3.
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

    versions = sorted(
        ordered[
            "split_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    s3_key = build_s3_key(
        split_name=split_name,
    )

    print()
    print(
        "--------------------------------------"
    )

    print(
        f"Split: "
        f"{split_name}"
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
        "Feature date: "
        f"{ordered['feature_date'].min().date()} "
        "-> "
        f"{ordered['feature_date'].max().date()}"
    )

    print(
        "Target date: "
        f"{ordered['target_date'].min().date()} "
        "-> "
        f"{ordered['target_date'].max().date()}"
    )

    print(
        f"Split version: "
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

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> list[str]:
    """
    Publica os três splits temporais.
    """

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII TEMPORAL SPLIT -> S3"
    )
    print(
        "======================================"
    )

    published_uris: list[str] = []

    for (
        split_name,
        local_path,
    ) in SPLIT_FILES.items():
        dataframe = load_split(
            split_name=split_name,
            path=local_path,
        )

        uri = publish_split(
            split_name=split_name,
            dataframe=dataframe,
            local_path=local_path,
            force=force,
        )

        published_uris.append(
            uri
        )

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII TEMPORAL SPLIT PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Splits: "
        f"{len(published_uris)}"
    )

    for uri in published_uris:
        print(
            f"  {uri}"
        )

    return published_uris


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publica Gold ML FII Temporal Split "
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