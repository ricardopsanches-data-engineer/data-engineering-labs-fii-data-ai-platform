from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ML_ELIGIBILITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_ml_eligibility"
    / "fii_ml_eligibility.parquet"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_KEY = (
    "gold/ml/"
    "fii_ml_eligibility/"
    "fii_ml_eligibility.parquet"
)


def load_ml_eligibility(
    path: Path = ML_ELIGIBILITY_PATH,
) -> pd.DataFrame:
    """
    Carrega o Gold ML FII ML Eligibility
    produzido pelo builder local.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"FII ML Eligibility não encontrado: {path}"
        )

    print(
        f"Carregando Gold ML FII ML Eligibility: {path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    if dataframe.empty:
        raise ValueError(
            "Gold ML FII ML Eligibility está vazio."
        )

    required_columns = [
        "ticker",
        "feature_date",
        "target_date",
        "ml_eligible",
        "ml_eligibility_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Gold ML FII ML Eligibility possui "
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


def publish_ml_eligibility(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> str:
    """
    Publica o dataset completo de ML Eligibility
    no Data Lake S3.
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
            "ml_eligibility_version"
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
        "GOLD ML FII ML ELIGIBILITY -> S3"
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
        f"ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"ML ineligible: "
        f"{ineligible_count:,}"
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
        f"Eligibility version: "
        f"{versions}"
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
        local_path=ML_ELIGIBILITY_PATH,
        bucket_name=BUCKET_NAME,
        s3_key=S3_KEY,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> str:
    """
    Executa publicação do Gold ML
    FII ML Eligibility.
    """

    dataframe = load_ml_eligibility()

    s3_uri = publish_ml_eligibility(
        dataframe=dataframe,
        force=force,
    )

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII ML ELIGIBILITY PUBLICADO"
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
            "Publica Gold ML FII ML Eligibility "
            "no Data Lake S3."
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