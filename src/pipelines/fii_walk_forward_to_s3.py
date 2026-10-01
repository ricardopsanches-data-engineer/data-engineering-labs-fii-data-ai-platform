from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from src.storage.s3 import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WALK_FORWARD_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_walk_forward"
)

FOLD_METRICS_PATH = (
    WALK_FORWARD_DIR
    / "fold_metrics.parquet"
)

SUMMARY_PATH = (
    WALK_FORWARD_DIR
    / "summary.json"
)

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

S3_PREFIX = (
    "gold/ml/"
    "fii_walk_forward"
)

EXPECTED_WALK_FORWARD_VERSION = "v1"

EXPECTED_MODELS = {
    "dummy_mean",
    "linear_regression",
    "random_forest",
}

EXPECTED_FOLDS = set(
    range(
        1,
        13,
    )
)

EXPECTED_RESULT_ROWS = 36

EXPECTED_POLICY = (
    "EXPANDING_WINDOW_PURGED"
)

EXPECTED_TEST_POLICY = (
    "RESERVED_FINAL_HOLDOUT_"
    "NO_MODEL_EVALUATION"
)


def load_fold_metrics() -> pd.DataFrame:
    """
    Carrega e valida o artefato físico
    de métricas Walk-Forward.
    """

    if not FOLD_METRICS_PATH.exists():
        raise FileNotFoundError(
            "Fold metrics não encontrado: "
            f"{FOLD_METRICS_PATH}"
        )

    print(
        "Carregando fold metrics: "
        f"{FOLD_METRICS_PATH}"
    )

    dataframe = pd.read_parquet(
        FOLD_METRICS_PATH
    )

    required_columns = [
        "walk_forward_version",
        "fold_id",
        "model",
        "validation_feature_sessions",
        "train_start",
        "train_end",
        "train_target_max",
        "validation_start",
        "validation_end",
        "validation_target_min",
        "validation_target_max",
        "train_rows",
        "validation_rows",
        "mae",
        "rmse",
        "r2",
        "directional_accuracy",
        "directional_lift",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Fold metrics possui colunas "
            "obrigatórias ausentes: "
            f"{missing_columns}"
        )

    if len(dataframe) != (
        EXPECTED_RESULT_ROWS
    ):
        raise ValueError(
            "Quantidade inesperada de linhas "
            "em fold_metrics. "
            f"Esperado={EXPECTED_RESULT_ROWS}, "
            f"obtido={len(dataframe)}."
        )

    versions = set(
        dataframe[
            "walk_forward_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if versions != {
        EXPECTED_WALK_FORWARD_VERSION
    }:
        raise ValueError(
            "walk_forward_version "
            "incompatível: "
            f"{sorted(versions)}"
        )

    models = set(
        dataframe[
            "model"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if models != EXPECTED_MODELS:
        raise ValueError(
            "Modelos inesperados: "
            f"{sorted(models)}"
        )

    folds = set(
        dataframe[
            "fold_id"
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if folds != EXPECTED_FOLDS:
        raise ValueError(
            "Folds inesperados: "
            f"{sorted(folds)}"
        )

    metric_columns = [
        "mae",
        "rmse",
        "r2",
        "directional_accuracy",
        "directional_lift",
    ]

    if dataframe[
        metric_columns
    ].isna().any().any():
        raise ValueError(
            "Fold metrics possui métricas "
            "nulas."
        )

    return dataframe


def load_summary() -> dict[str, Any]:
    """
    Carrega e valida o summary.json
    do Walk-Forward.
    """

    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(
            "Summary não encontrado: "
            f"{SUMMARY_PATH}"
        )

    print(
        "Carregando summary: "
        f"{SUMMARY_PATH}"
    )

    summary = json.loads(
        SUMMARY_PATH.read_text(
            encoding="utf-8"
        )
    )

    required_keys = [
        "walk_forward_version",
        "generated_at",
        "policy",
        "fold_count",
        "validation_feature_sessions",
        "minimum_train_feature_sessions",
        "target",
        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",
        "feature_count",
        "feature_columns",
        "source_contract",
        "test_start",
        "test_policy",
        "test_features_used",
        "test_targets_used",
        "test_predictions_generated",
        "eligible_pre_test_rows",
        "eligible_pre_test_tickers",
        "models",
        "best_models",
    ]

    missing_keys = [
        key
        for key in required_keys
        if key not in summary
    ]

    if missing_keys:
        raise ValueError(
            "Summary possui chaves "
            "obrigatórias ausentes: "
            f"{missing_keys}"
        )

    if (
        summary[
            "walk_forward_version"
        ]
        != EXPECTED_WALK_FORWARD_VERSION
    ):
        raise ValueError(
            "summary.walk_forward_version "
            "incompatível."
        )

    if (
        summary[
            "policy"
        ]
        != EXPECTED_POLICY
    ):
        raise ValueError(
            "summary.policy incompatível."
        )

    if (
        int(
            summary[
                "fold_count"
            ]
        )
        != len(
            EXPECTED_FOLDS
        )
    ):
        raise ValueError(
            "summary.fold_count "
            "incompatível."
        )

    if (
        summary[
            "test_policy"
        ]
        != EXPECTED_TEST_POLICY
    ):
        raise ValueError(
            "summary.test_policy "
            "incompatível."
        )

    if (
        bool(
            summary[
                "test_features_used"
            ]
        )
        or bool(
            summary[
                "test_targets_used"
            ]
        )
        or bool(
            summary[
                "test_predictions_generated"
            ]
        )
    ):
        raise ValueError(
            "TEST final foi marcado como "
            "utilizado pelo Walk-Forward."
        )

    return summary


def validate_cross_artifact_contract(
    dataframe: pd.DataFrame,
    summary: dict[str, Any],
) -> None:
    """
    Valida consistência entre fold_metrics
    e summary.
    """

    metric_version = (
        dataframe[
            "walk_forward_version"
        ]
        .astype(str)
        .unique()
        .tolist()
    )

    if metric_version != [
        summary[
            "walk_forward_version"
        ]
    ]:
        raise ValueError(
            "Versão diverge entre "
            "fold_metrics e summary."
        )

    metric_fold_count = int(
        dataframe[
            "fold_id"
        ].nunique()
    )

    if metric_fold_count != int(
        summary[
            "fold_count"
        ]
    ):
        raise ValueError(
            "Quantidade de folds diverge "
            "entre fold_metrics e summary."
        )

    metric_models = set(
        dataframe[
            "model"
        ]
        .astype(str)
        .unique()
        .tolist()
    )

    summary_models = set(
        summary[
            "models"
        ].keys()
    )

    if metric_models != summary_models:
        raise ValueError(
            "Modelos divergem entre "
            "fold_metrics e summary."
        )

    print()
    print(
        "Contrato cruzado "
        "fold_metrics x summary: PASS"
    )


def calculate_dataframe_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico
    do fold_metrics.
    """

    canonical = (
        dataframe
        .sort_values(
            by=[
                "fold_id",
                "model",
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


def calculate_summary_content_sha256(
    summary: dict[str, Any],
) -> str:
    """
    Calcula fingerprint lógico do summary.

    generated_at é metadado operacional
    e não participa da identidade lógica.
    """

    canonical = dict(
        summary
    )

    canonical.pop(
        "generated_at",
        None,
    )

    canonical_json = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    )

    return hashlib.sha256(
        canonical_json.encode(
            "utf-8"
        )
    ).hexdigest()


def publish_fold_metrics(
    dataframe: pd.DataFrame,
    force: bool = False,
) -> str:
    """
    Publica fold_metrics.parquet.
    """

    content_sha256 = (
        calculate_dataframe_content_sha256(
            dataframe
        )
    )

    s3_key = (
        f"{S3_PREFIX}/"
        "fold_metrics/"
        "fold_metrics.parquet"
    )

    print()
    print(
        "--------------------------------------"
    )
    print(
        "Artefato: fold_metrics.parquet"
    )
    print(
        f"Linhas: {len(dataframe):,}"
    )
    print(
        f"Colunas: {len(dataframe.columns):,}"
    )
    print(
        "Walk-Forward version: "
        f"{EXPECTED_WALK_FORWARD_VERSION}"
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
        local_path=FOLD_METRICS_PATH,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        content_sha256=content_sha256,
        force=force,
    )


def publish_summary(
    summary: dict[str, Any],
    force: bool = False,
) -> str:
    """
    Publica summary.json.
    """

    content_sha256 = (
        calculate_summary_content_sha256(
            summary
        )
    )

    s3_key = (
        f"{S3_PREFIX}/"
        "summary/"
        "summary.json"
    )

    print()
    print(
        "--------------------------------------"
    )
    print(
        "Artefato: summary.json"
    )
    print(
        "Walk-Forward version: "
        f"{summary['walk_forward_version']}"
    )
    print(
        f"Folds: "
        f"{summary['fold_count']}"
    )
    print(
        f"Policy: "
        f"{summary['policy']}"
    )
    print(
        f"TEST start: "
        f"{summary['test_start']}"
    )
    print(
        f"TEST policy: "
        f"{summary['test_policy']}"
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
        local_path=SUMMARY_PATH,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> list[str]:
    """
    Publica os artefatos Walk-Forward.
    """

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII WALK-FORWARD -> S3"
    )
    print(
        "======================================"
    )

    fold_metrics = (
        load_fold_metrics()
    )

    summary = (
        load_summary()
    )

    validate_cross_artifact_contract(
        dataframe=fold_metrics,
        summary=summary,
    )

    published_uris = [
        publish_fold_metrics(
            dataframe=fold_metrics,
            force=force,
        ),
        publish_summary(
            summary=summary,
            force=force,
        ),
    ]

    print()
    print(
        "======================================"
    )
    print(
        "GOLD ML FII WALK-FORWARD PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Artefatos: "
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
            "Publica os artefatos Gold ML "
            "FII Walk-Forward no Data Lake S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar "
            "nova versão de objetos já existentes."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()