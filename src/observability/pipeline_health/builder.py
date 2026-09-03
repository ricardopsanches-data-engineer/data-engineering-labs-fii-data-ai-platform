from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# Observability contract
# ============================================================

OBSERVABILITY_VERSION = "v2"

DEFAULT_MAX_FRESHNESS_DAYS = 7


# ============================================================
# Input datasets
# ============================================================

ADJUSTED_PRICES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
    / "fii_corporate_action_adjusted_prices.parquet"
)

PRICE_DISCONTINUITIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_discontinuities"
    / "fii_price_discontinuities.parquet"
)

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

PRICE_QUALITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "quality"
    / "fii_price_quality"
    / "fii_price_quality.parquet"
)

CORPORATE_ACTION_REVIEW_QUEUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "quality"
    / "fii_corporate_action_review_queue"
    / "fii_corporate_action_review_queue.parquet"
)

FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_features"
    / "fii_features.parquet"
)

ML_ELIGIBILITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_ml_eligibility"
    / "fii_ml_eligibility.parquet"
)

TRAINING_DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
    / "fii_training_dataset.parquet"
)

TEMPORAL_SPLIT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
)

TRAIN_PATH = (
    TEMPORAL_SPLIT_DIR
    / "train.parquet"
)

VALIDATION_PATH = (
    TEMPORAL_SPLIT_DIR
    / "validation.parquet"
)

TEST_PATH = (
    TEMPORAL_SPLIT_DIR
    / "test.parquet"
)


# ============================================================
# Observability outputs
# ============================================================

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "observability"
    / "pipeline_health"
)

LATEST_PATH = (
    OUTPUT_DIR
    / "latest.json"
)

HISTORY_DIR = (
    OUTPUT_DIR
    / "history"
)


# ============================================================
# Expected semantic versions / contracts
# ============================================================

EXPECTED_PRICE_HISTORY_VERSION = "v3"

EXPECTED_FEATURE_VERSION = "v7"

EXPECTED_ELIGIBILITY_VERSION = "v3"

EXPECTED_TRAINING_DATASET_VERSION = "v4"

EXPECTED_TEMPORAL_SPLIT_VERSION = "v3"

EXPECTED_PRICE_QUALITY_VERSION = "v2"

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)

EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS = (
    "TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND"
)

EXPECTED_PURGE_SEMANTICS = (
    "TARGET_DATE_BEFORE_NEXT_SPLIT"
)

EXPECTED_TEST_HOLDOUT_POLICY = (
    "RESERVED_UNTOUCHED_FOR_MODEL_SELECTION"
)


# ============================================================
# Structures
# ============================================================

FreshnessMode = Literal[
    "DATA_DATE",
    "TARGET_DATE",
    "EVENT_DRIVEN",
    "HISTORICAL_SPLIT",
]


@dataclass(frozen=True)
class DatasetSpec:
    """
    Contrato de observabilidade de um dataset.

    DATA_DATE
        Freshness pela data operacional do dado.

    TARGET_DATE
        Freshness pelo target supervisionado
        mais recente.

    EVENT_DRIVEN
        O último evento pode ser antigo sem
        significar staleness.

    HISTORICAL_SPLIT
        O artefato é deliberadamente histórico.
        Sua saúde depende das fronteiras,
        purge, eligibility e overlap.
    """

    name: str

    path: Path

    date_candidates: tuple[str, ...]

    key_candidates: tuple[
        tuple[str, ...],
        ...
    ]

    required_columns: tuple[
        str,
        ...
    ] = ()

    allow_empty: bool = False

    freshness_mode: FreshnessMode = (
        "DATA_DATE"
    )

    freshness_date_candidates: tuple[
        str,
        ...
    ] = ()


# ============================================================
# Dataset definitions
# ============================================================

DATASETS = (
    DatasetSpec(
        name=(
            "corporate_action_adjusted_prices"
        ),
        path=ADJUSTED_PRICES_PATH,
        date_candidates=(
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "trade_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
        ),
        freshness_mode="DATA_DATE",
        freshness_date_candidates=(
            "trade_date",
            "date",
        ),
    ),

    DatasetSpec(
        name="price_discontinuities",
        path=PRICE_DISCONTINUITIES_PATH,
        date_candidates=(
            "event_date",
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "event_date",
                "ticker",
            ),
            (
                "trade_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
        ),
        freshness_mode="EVENT_DRIVEN",
    ),

    DatasetSpec(
        name="price_history",
        path=PRICE_HISTORY_PATH,
        date_candidates=(
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "trade_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
            "price_history_version",
            "price_semantics",
            "return_semantics",
            "corporate_action_value_semantics",
        ),
        freshness_mode="DATA_DATE",
        freshness_date_candidates=(
            "trade_date",
            "date",
        ),
    ),

    DatasetSpec(
        name="price_quality",
        path=PRICE_QUALITY_PATH,
        date_candidates=(
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "trade_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
        ),
        freshness_mode="DATA_DATE",
        freshness_date_candidates=(
            "trade_date",
            "date",
        ),
    ),

    DatasetSpec(
        name=(
            "corporate_action_review_queue"
        ),
        path=(
            CORPORATE_ACTION_REVIEW_QUEUE_PATH
        ),
        date_candidates=(
            "event_date",
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "event_date",
                "ticker",
            ),
            (
                "trade_date",
                "ticker",
            ),
        ),
        allow_empty=True,
        freshness_mode="EVENT_DRIVEN",
    ),

    DatasetSpec(
        name="features",
        path=FEATURES_PATH,
        date_candidates=(
            "feature_date",
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
            (
                "trade_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
            "feature_version",
            "feature_ready",
            "price_semantics",
            "return_semantics",
            "corporate_action_value_semantics",
        ),
        freshness_mode="DATA_DATE",
        freshness_date_candidates=(
            "feature_date",
            "trade_date",
            "date",
        ),
    ),

    DatasetSpec(
        name="ml_eligibility",
        path=ML_ELIGIBILITY_PATH,
        date_candidates=(
            "feature_date",
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
            "ml_eligible",
            "target_date",
        ),
        freshness_mode="TARGET_DATE",
        freshness_date_candidates=(
            "target_date",
        ),
    ),

    DatasetSpec(
        name="training_dataset",
        path=TRAINING_DATASET_PATH,
        date_candidates=(
            "feature_date",
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
        ),
        required_columns=(
            "feature_date",
            "target_date",
            "ticker",
            "ml_eligible",
            "training_dataset_version",
            "target_horizon",
            "target_horizon_semantics",
            "target_return_semantics",
        ),
        freshness_mode="TARGET_DATE",
        freshness_date_candidates=(
            "target_date",
        ),
    ),

    DatasetSpec(
        name="temporal_split_train",
        path=TRAIN_PATH,
        date_candidates=(
            "feature_date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
        ),
        required_columns=(
            "feature_date",
            "target_date",
            "ticker",
            "ml_eligible",
            "split_name",
            "split_version",
        ),
        freshness_mode=(
            "HISTORICAL_SPLIT"
        ),
    ),

    DatasetSpec(
        name=(
            "temporal_split_validation"
        ),
        path=VALIDATION_PATH,
        date_candidates=(
            "feature_date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
        ),
        required_columns=(
            "feature_date",
            "target_date",
            "ticker",
            "ml_eligible",
            "split_name",
            "split_version",
        ),
        freshness_mode=(
            "HISTORICAL_SPLIT"
        ),
    ),

    DatasetSpec(
        name="temporal_split_test",
        path=TEST_PATH,
        date_candidates=(
            "feature_date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
        ),
        required_columns=(
            "feature_date",
            "target_date",
            "ticker",
            "ml_eligible",
            "split_name",
            "split_version",
        ),
        freshness_mode=(
            "HISTORICAL_SPLIT"
        ),
    ),
)


# ============================================================
# JSON helpers
# ============================================================

def make_json_safe(
    value: Any,
) -> Any:
    if isinstance(
        value,
        np.integer,
    ):
        return int(
            value
        )

    if isinstance(
        value,
        np.floating,
    ):
        return float(
            value
        )

    if isinstance(
        value,
        np.bool_,
    ):
        return bool(
            value
        )

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
        ),
    ):
        return value.isoformat()

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    return value


def json_default(
    value: Any,
) -> Any:
    converted = make_json_safe(
        value
    )

    if converted is not value:
        return converted

    raise TypeError(
        "Objeto não serializável: "
        f"{type(value).__name__}"
    )


# ============================================================
# Generic check
# ============================================================

def build_check(
    name: str,
    status: str,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    result: dict[
        str,
        Any,
    ] = {
        "name": name,
        "status": status,
        "message": message,
    }

    if details:
        result[
            "details"
        ] = details

    return result


# ============================================================
# Helpers
# ============================================================

def unique_values(
    dataframe: pd.DataFrame,
    column: str,
) -> list[Any]:
    if column not in dataframe.columns:
        return []

    values = (
        dataframe[
            column
        ]
        .dropna()
        .unique()
        .tolist()
    )

    return [
        make_json_safe(
            value
        )
        for value in values
    ]


def resolve_date_column(
    dataframe: pd.DataFrame,
    candidates: tuple[
        str,
        ...
    ],
) -> str | None:
    for column in candidates:
        if column in dataframe.columns:
            return column

    return None


def resolve_key_columns(
    dataframe: pd.DataFrame,
    candidates: tuple[
        tuple[str, ...],
        ...
    ],
) -> tuple[str, ...] | None:
    for candidate in candidates:
        if all(
            column in dataframe.columns
            for column in candidate
        ):
            return candidate

    return None


def resolve_dataset_status(
    checks: list[
        dict[str, Any]
    ],
) -> str:
    statuses = [
        check.get(
            "status",
            "FAIL",
        )
        for check in checks
    ]

    if "FAIL" in statuses:
        return "FAIL"

    if "WARN" in statuses:
        return "WARN"

    return "PASS"


# ============================================================
# Freshness
# ============================================================

def add_freshness_check(
    result: dict[str, Any],
    dataframe: pd.DataFrame,
    spec: DatasetSpec,
    reference_date: pd.Timestamp,
    max_freshness_days: int,
) -> None:
    """
    Aplica freshness conforme a semântica
    do dataset.
    """

    result[
        "freshness_mode"
    ] = spec.freshness_mode

    if (
        spec.freshness_mode
        == "EVENT_DRIVEN"
    ):
        result[
            "checks"
        ].append(
            build_check(
                name="freshness",
                status="PASS",
                message=(
                    "Freshness por último "
                    "evento não se aplica "
                    "a dataset event-driven."
                ),
                policy=(
                    "EVENT_DRIVEN_"
                    "NOT_LAST_EVENT_AGE"
                ),
            )
        )

        return

    if (
        spec.freshness_mode
        == "HISTORICAL_SPLIT"
    ):
        result[
            "checks"
        ].append(
            build_check(
                name="freshness",
                status="PASS",
                message=(
                    "Freshness contra a data "
                    "atual não se aplica a "
                    "split histórico/purgado."
                ),
                policy=(
                    "HISTORICAL_SPLIT_"
                    "BOUNDARIES_GOVERN_HEALTH"
                ),
            )
        )

        return

    candidates = (
        spec.freshness_date_candidates
        if (
            spec.freshness_date_candidates
        )
        else spec.date_candidates
    )

    freshness_column = (
        resolve_date_column(
            dataframe=dataframe,
            candidates=candidates,
        )
    )

    if freshness_column is None:
        result[
            "checks"
        ].append(
            build_check(
                name="freshness",
                status="FAIL",
                message=(
                    "Nenhuma coluna compatível "
                    "com a política de freshness "
                    "foi encontrada."
                ),
                freshness_mode=(
                    spec.freshness_mode
                ),
                candidates=list(
                    candidates
                ),
            )
        )

        return

    if dataframe.empty:
        if spec.allow_empty:
            status = "PASS"

            message = (
                "Dataset vazio permitido; "
                "freshness não é aplicável."
            )

        else:
            status = "FAIL"

            message = (
                "Dataset vazio sem data "
                "para freshness."
            )

        result[
            "checks"
        ].append(
            build_check(
                name="freshness",
                status=status,
                message=message,
                freshness_mode=(
                    spec.freshness_mode
                ),
            )
        )

        return

    dates = pd.to_datetime(
        dataframe[
            freshness_column
        ],
        errors="coerce",
    )

    valid_dates = (
        dates.dropna()
    )

    if valid_dates.empty:
        result[
            "checks"
        ].append(
            build_check(
                name="freshness",
                status="FAIL",
                message=(
                    "Coluna de freshness "
                    "não possui datas válidas."
                ),
                freshness_column=(
                    freshness_column
                ),
            )
        )

        return

    latest_date = pd.Timestamp(
        valid_dates.max()
    )

    if latest_date.tzinfo is not None:
        latest_date = (
            latest_date.tz_localize(
                None
            )
        )

    normalized_reference = (
        pd.Timestamp(
            reference_date
        )
    )

    if (
        normalized_reference.tzinfo
        is not None
    ):
        normalized_reference = (
            normalized_reference
            .tz_localize(
                None
            )
        )

    latest_date = (
        latest_date.normalize()
    )

    normalized_reference = (
        normalized_reference.normalize()
    )

    freshness_days = int(
        (
            normalized_reference
            - latest_date
        ).days
    )

    result[
        "freshness_column"
    ] = freshness_column

    result[
        "freshness_latest_date"
    ] = (
        latest_date
        .date()
        .isoformat()
    )

    result[
        "freshness_days"
    ] = freshness_days

    if freshness_days < 0:
        result[
            "checks"
        ].append(
            build_check(
                name="freshness",
                status="FAIL",
                message=(
                    "Dataset possui informação "
                    "futura em relação à data "
                    "de referência."
                ),
                latest_date=(
                    latest_date
                    .date()
                    .isoformat()
                ),
                reference_date=(
                    normalized_reference
                    .date()
                    .isoformat()
                ),
                freshness_days=(
                    freshness_days
                ),
            )
        )

        return

    status = (
        "PASS"
        if (
            freshness_days
            <= max_freshness_days
        )
        else "FAIL"
    )

    result[
        "checks"
    ].append(
        build_check(
            name="freshness",
            status=status,
            message=(
                "Freshness dentro do limite."
                if status == "PASS"
                else (
                    "Dataset excede o limite "
                    "de freshness."
                )
            ),
            freshness_mode=(
                spec.freshness_mode
            ),
            freshness_column=(
                freshness_column
            ),
            latest_date=(
                latest_date
                .date()
                .isoformat()
            ),
            reference_date=(
                normalized_reference
                .date()
                .isoformat()
            ),
            freshness_days=(
                freshness_days
            ),
            max_freshness_days=(
                max_freshness_days
            ),
        )
    )


# ============================================================
# Dataset inspection
# ============================================================

def inspect_dataset(
    spec: DatasetSpec,
    reference_date: pd.Timestamp,
    max_freshness_days: int,
) -> tuple[
    dict[str, Any],
    pd.DataFrame | None,
]:
    result: dict[
        str,
        Any,
    ] = {
        "name": spec.name,
        "path": str(
            spec.path
        ),
        "freshness_mode": (
            spec.freshness_mode
        ),
        "checks": [],
    }

    if not spec.path.exists():
        result[
            "checks"
        ].append(
            build_check(
                name="file_exists",
                status="FAIL",
                message=(
                    "Arquivo não encontrado."
                ),
            )
        )

        result[
            "status"
        ] = "FAIL"

        return (
            result,
            None,
        )

    result[
        "checks"
    ].append(
        build_check(
            name="file_exists",
            status="PASS",
            message=(
                "Arquivo encontrado."
            ),
        )
    )

    result[
        "file_size_bytes"
    ] = int(
        spec.path.stat().st_size
    )

    result[
        "file_modified_at"
    ] = datetime.fromtimestamp(
        spec.path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat()

    try:
        dataframe = pd.read_parquet(
            spec.path
        )

    except Exception as error:
        result[
            "checks"
        ].append(
            build_check(
                name="parquet_read",
                status="FAIL",
                message=(
                    "Falha ao ler Parquet."
                ),
                error=str(
                    error
                ),
            )
        )

        result[
            "status"
        ] = "FAIL"

        return (
            result,
            None,
        )

    result[
        "checks"
    ].append(
        build_check(
            name="parquet_read",
            status="PASS",
            message=(
                "Parquet lido com sucesso."
            ),
        )
    )

    row_count = len(
        dataframe
    )

    result[
        "row_count"
    ] = int(
        row_count
    )

    valid_row_count = (
        row_count > 0
        or spec.allow_empty
    )

    result[
        "checks"
    ].append(
        build_check(
            name="row_count",
            status=(
                "PASS"
                if valid_row_count
                else "FAIL"
            ),
            message=(
                "Row count válido."
                if valid_row_count
                else "Dataset vazio."
            ),
            row_count=row_count,
            allow_empty=(
                spec.allow_empty
            ),
        )
    )

    missing_required_columns = [
        column
        for column
        in spec.required_columns
        if column
        not in dataframe.columns
    ]

    result[
        "checks"
    ].append(
        build_check(
            name="required_columns",
            status=(
                "PASS"
                if not (
                    missing_required_columns
                )
                else "FAIL"
            ),
            message=(
                "Schema mínimo presente."
                if not (
                    missing_required_columns
                )
                else (
                    "Schema mínimo "
                    "incompatível."
                )
            ),
            missing_columns=(
                missing_required_columns
            ),
        )
    )

    if "ticker" in dataframe.columns:
        result[
            "ticker_count"
        ] = int(
            dataframe[
                "ticker"
            ]
            .dropna()
            .nunique()
        )

    key_columns = (
        resolve_key_columns(
            dataframe=dataframe,
            candidates=(
                spec.key_candidates
            ),
        )
    )

    if key_columns is not None:
        duplicate_count = int(
            dataframe.duplicated(
                subset=list(
                    key_columns
                )
            ).sum()
        )

        result[
            "duplicate_count"
        ] = duplicate_count

        result[
            "key_columns"
        ] = list(
            key_columns
        )

        result[
            "checks"
        ].append(
            build_check(
                name="duplicates",
                status=(
                    "PASS"
                    if duplicate_count == 0
                    else "FAIL"
                ),
                message=(
                    "Nenhuma duplicidade "
                    "na chave."
                    if duplicate_count == 0
                    else (
                        "Duplicidades "
                        "encontradas."
                    )
                ),
                duplicate_count=(
                    duplicate_count
                ),
                key_columns=list(
                    key_columns
                ),
            )
        )

    date_column = (
        resolve_date_column(
            dataframe=dataframe,
            candidates=(
                spec.date_candidates
            ),
        )
    )

    if (
        date_column is not None
        and not dataframe.empty
    ):
        dates = pd.to_datetime(
            dataframe[
                date_column
            ],
            errors="coerce",
        )

        invalid_dates = int(
            dates.isna().sum()
        )

        result[
            "date_column"
        ] = date_column

        result[
            "invalid_date_count"
        ] = invalid_dates

        if dates.notna().any():
            min_date = pd.Timestamp(
                dates.min()
            )

            max_date = pd.Timestamp(
                dates.max()
            )

            result[
                "min_date"
            ] = (
                min_date
                .date()
                .isoformat()
            )

            result[
                "max_date"
            ] = (
                max_date
                .date()
                .isoformat()
            )

        result[
            "checks"
        ].append(
            build_check(
                name="date_parse",
                status=(
                    "PASS"
                    if invalid_dates == 0
                    else "FAIL"
                ),
                message=(
                    "Datas válidas."
                    if invalid_dates == 0
                    else (
                        "Existem datas "
                        "inválidas."
                    )
                ),
                invalid_date_count=(
                    invalid_dates
                ),
                date_column=(
                    date_column
                ),
            )
        )

    add_freshness_check(
        result=result,
        dataframe=dataframe,
        spec=spec,
        reference_date=(
            reference_date
        ),
        max_freshness_days=(
            max_freshness_days
        ),
    )

    result[
        "status"
    ] = resolve_dataset_status(
        result[
            "checks"
        ]
    )

    return (
        result,
        dataframe,
    )


# ============================================================
# Core semantics
# ============================================================

def validate_core_semantics(
    datasets: dict[
        str,
        pd.DataFrame | None,
    ],
) -> list[
    dict[str, Any]
]:
    checks: list[
        dict[str, Any]
    ] = []

    price_history = datasets.get(
        "price_history"
    )

    if price_history is not None:
        expected = {
            "price_history_version": (
                EXPECTED_PRICE_HISTORY_VERSION
            ),
            "price_semantics": (
                EXPECTED_PRICE_SEMANTICS
            ),
            "return_semantics": (
                EXPECTED_RETURN_SEMANTICS
            ),
            (
                "corporate_action_value_semantics"
            ): (
                EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
            ),
        }

        for (
            column,
            expected_value,
        ) in expected.items():

            values = unique_values(
                price_history,
                column,
            )

            checks.append(
                build_check(
                    name=(
                        "price_history."
                        f"{column}"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            expected_value
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Contrato correto."
                        if values
                        == [
                            expected_value
                        ]
                        else (
                            "Contrato "
                            "incompatível."
                        )
                    ),
                    expected=(
                        expected_value
                    ),
                    found=values,
                )
            )

    price_quality = datasets.get(
        "price_quality"
    )

    if price_quality is not None:
        version_columns = (
            "price_quality_version",
            "quality_version",
        )

        discovered = next(
            (
                column
                for column
                in version_columns
                if column
                in price_quality.columns
            ),
            None,
        )

        if discovered is None:
            checks.append(
                build_check(
                    name=(
                        "price_quality.version"
                    ),
                    status="WARN",
                    message=(
                        "Coluna de versão de "
                        "Price Quality não "
                        "localizada."
                    ),
                )
            )

        else:
            values = unique_values(
                price_quality,
                discovered,
            )

            checks.append(
                build_check(
                    name=(
                        "price_quality.version"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            EXPECTED_PRICE_QUALITY_VERSION
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Price Quality version "
                        "correta."
                        if values
                        == [
                            EXPECTED_PRICE_QUALITY_VERSION
                        ]
                        else (
                            "Price Quality "
                            "version incompatível."
                        )
                    ),
                    column=discovered,
                    expected=(
                        EXPECTED_PRICE_QUALITY_VERSION
                    ),
                    found=values,
                )
            )

    features = datasets.get(
        "features"
    )

    if features is not None:
        feature_versions = (
            unique_values(
                features,
                "feature_version",
            )
        )

        checks.append(
            build_check(
                name="features.version",
                status=(
                    "PASS"
                    if feature_versions
                    == [
                        EXPECTED_FEATURE_VERSION
                    ]
                    else "FAIL"
                ),
                message=(
                    "Feature version correta."
                    if feature_versions
                    == [
                        EXPECTED_FEATURE_VERSION
                    ]
                    else (
                        "Feature version "
                        "incompatível."
                    )
                ),
                expected=(
                    EXPECTED_FEATURE_VERSION
                ),
                found=feature_versions,
            )
        )

        feature_semantics = {
            "price_semantics": (
                EXPECTED_PRICE_SEMANTICS
            ),
            "return_semantics": (
                EXPECTED_RETURN_SEMANTICS
            ),
            (
                "corporate_action_value_semantics"
            ): (
                EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
            ),
        }

        for (
            column,
            expected_value,
        ) in feature_semantics.items():

            values = unique_values(
                features,
                column,
            )

            checks.append(
                build_check(
                    name=(
                        f"features.{column}"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            expected_value
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Contrato correto."
                        if values
                        == [
                            expected_value
                        ]
                        else (
                            "Contrato "
                            "incompatível."
                        )
                    ),
                    expected=(
                        expected_value
                    ),
                    found=values,
                )
            )

    eligibility = datasets.get(
        "ml_eligibility"
    )

    if eligibility is not None:
        version_columns = (
            "ml_eligibility_version",
            "eligibility_version",
        )

        discovered = next(
            (
                column
                for column
                in version_columns
                if column
                in eligibility.columns
            ),
            None,
        )

        if discovered is None:
            checks.append(
                build_check(
                    name=(
                        "ml_eligibility.version"
                    ),
                    status="WARN",
                    message=(
                        "Coluna de versão de "
                        "ML Eligibility não "
                        "localizada."
                    ),
                )
            )

        else:
            values = unique_values(
                eligibility,
                discovered,
            )

            checks.append(
                build_check(
                    name=(
                        "ml_eligibility.version"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            EXPECTED_ELIGIBILITY_VERSION
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Eligibility version "
                        "correta."
                        if values
                        == [
                            EXPECTED_ELIGIBILITY_VERSION
                        ]
                        else (
                            "Eligibility version "
                            "incompatível."
                        )
                    ),
                    column=discovered,
                    expected=(
                        EXPECTED_ELIGIBILITY_VERSION
                    ),
                    found=values,
                )
            )

    training = datasets.get(
        "training_dataset"
    )

    if training is not None:
        expected = {
            "training_dataset_version": (
                EXPECTED_TRAINING_DATASET_VERSION
            ),
            "target_horizon": (
                EXPECTED_TARGET_HORIZON
            ),
            "target_horizon_semantics": (
                EXPECTED_TARGET_HORIZON_SEMANTICS
            ),
            "target_return_semantics": (
                EXPECTED_TARGET_RETURN_SEMANTICS
            ),
        }

        for (
            column,
            expected_value,
        ) in expected.items():

            values = unique_values(
                training,
                column,
            )

            checks.append(
                build_check(
                    name=(
                        "training_dataset."
                        f"{column}"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            expected_value
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Contrato correto."
                        if values
                        == [
                            expected_value
                        ]
                        else (
                            "Contrato "
                            "incompatível."
                        )
                    ),
                    expected=(
                        expected_value
                    ),
                    found=values,
                )
            )

    return checks


# ============================================================
# Cross-dataset reconciliation
# ============================================================

def validate_cross_dataset_relations(
    datasets: dict[
        str,
        pd.DataFrame | None,
    ],
) -> list[
    dict[str, Any]
]:
    checks: list[
        dict[str, Any]
    ] = []

    price_history = datasets.get(
        "price_history"
    )

    features = datasets.get(
        "features"
    )

    if (
        price_history is not None
        and features is not None
    ):
        equal_rows = (
            len(
                price_history
            )
            == len(
                features
            )
        )

        checks.append(
            build_check(
                name=(
                    "price_history_vs_"
                    "features_rows"
                ),
                status=(
                    "PASS"
                    if equal_rows
                    else "FAIL"
                ),
                message=(
                    "Price History e Features "
                    "possuem o mesmo row count."
                    if equal_rows
                    else (
                        "Row counts divergentes "
                        "entre Price History "
                        "e Features."
                    )
                ),
                price_history_rows=(
                    len(
                        price_history
                    )
                ),
                feature_rows=(
                    len(
                        features
                    )
                ),
            )
        )

    eligibility = datasets.get(
        "ml_eligibility"
    )

    training = datasets.get(
        "training_dataset"
    )

    if (
        eligibility is not None
        and training is not None
    ):
        equal_rows = (
            len(
                eligibility
            )
            == len(
                training
            )
        )

        checks.append(
            build_check(
                name=(
                    "eligibility_vs_"
                    "training_rows"
                ),
                status=(
                    "PASS"
                    if equal_rows
                    else "FAIL"
                ),
                message=(
                    "Eligibility e Training "
                    "Dataset reconciliados."
                    if equal_rows
                    else (
                        "Row counts divergentes "
                        "entre Eligibility e "
                        "Training Dataset."
                    )
                ),
                eligibility_rows=(
                    len(
                        eligibility
                    )
                ),
                training_rows=(
                    len(
                        training
                    )
                ),
            )
        )

        required_key_columns = {
            "feature_date",
            "ticker",
        }

        if (
            required_key_columns
            <= set(
                eligibility.columns
            )
            and required_key_columns
            <= set(
                training.columns
            )
        ):
            eligibility_keys = set(
                zip(
                    pd.to_datetime(
                        eligibility[
                            "feature_date"
                        ]
                    ),
                    eligibility[
                        "ticker"
                    ].astype(
                        str
                    ),
                )
            )

            training_keys = set(
                zip(
                    pd.to_datetime(
                        training[
                            "feature_date"
                        ]
                    ),
                    training[
                        "ticker"
                    ].astype(
                        str
                    ),
                )
            )

            key_match = (
                eligibility_keys
                == training_keys
            )

            checks.append(
                build_check(
                    name=(
                        "eligibility_vs_"
                        "training_keys"
                    ),
                    status=(
                        "PASS"
                        if key_match
                        else "FAIL"
                    ),
                    message=(
                        "Eligibility e Training "
                        "Dataset possuem o mesmo "
                        "universo de samples."
                        if key_match
                        else (
                            "Universos de samples "
                            "divergentes."
                        )
                    ),
                    eligibility_keys=(
                        len(
                            eligibility_keys
                        )
                    ),
                    training_keys=(
                        len(
                            training_keys
                        )
                    ),
                )
            )

    return checks


# ============================================================
# Temporal split checks
# ============================================================

def validate_temporal_splits(
    datasets: dict[
        str,
        pd.DataFrame | None,
    ],
) -> list[
    dict[str, Any]
]:
    checks: list[
        dict[str, Any]
    ] = []

    train = datasets.get(
        "temporal_split_train"
    )

    validation = datasets.get(
        "temporal_split_validation"
    )

    test = datasets.get(
        "temporal_split_test"
    )

    eligibility = datasets.get(
        "ml_eligibility"
    )

    if any(
        dataframe is None
        for dataframe
        in (
            train,
            validation,
            test,
        )
    ):
        checks.append(
            build_check(
                name=(
                    "temporal_split_available"
                ),
                status="FAIL",
                message=(
                    "Um ou mais splits "
                    "não estão disponíveis."
                ),
            )
        )

        return checks

    assert train is not None

    assert validation is not None

    assert test is not None

    splits = {
        "train": train,
        "validation": validation,
        "test": test,
    }

    for (
        name,
        dataframe,
    ) in splits.items():

        versions = unique_values(
            dataframe,
            "split_version",
        )

        stored_names = unique_values(
            dataframe,
            "split_name",
        )

        checks.append(
            build_check(
                name=(
                    f"{name}.split_version"
                ),
                status=(
                    "PASS"
                    if versions
                    == [
                        EXPECTED_TEMPORAL_SPLIT_VERSION
                    ]
                    else "FAIL"
                ),
                message=(
                    "Split version correta."
                    if versions
                    == [
                        EXPECTED_TEMPORAL_SPLIT_VERSION
                    ]
                    else (
                        "Split version "
                        "incompatível."
                    )
                ),
                expected=(
                    EXPECTED_TEMPORAL_SPLIT_VERSION
                ),
                found=versions,
            )
        )

        checks.append(
            build_check(
                name=(
                    f"{name}.split_name"
                ),
                status=(
                    "PASS"
                    if stored_names
                    == [
                        name
                    ]
                    else "FAIL"
                ),
                message=(
                    "split_name correto."
                    if stored_names
                    == [
                        name
                    ]
                    else (
                        "split_name "
                        "incompatível."
                    )
                ),
                expected=name,
                found=stored_names,
            )
        )

        if (
            "ml_eligible"
            in dataframe.columns
        ):
            ineligible_count = int(
                (
                    ~dataframe[
                        "ml_eligible"
                    ]
                    .fillna(
                        False
                    )
                    .astype(
                        bool
                    )
                ).sum()
            )

            checks.append(
                build_check(
                    name=(
                        f"{name}.ml_eligible"
                    ),
                    status=(
                        "PASS"
                        if ineligible_count == 0
                        else "FAIL"
                    ),
                    message=(
                        "Somente samples "
                        "elegíveis."
                        if ineligible_count == 0
                        else (
                            "Split contém "
                            "samples inelegíveis."
                        )
                    ),
                    ineligible_count=(
                        ineligible_count
                    ),
                )
            )

        if (
            "split_purge_semantics"
            in dataframe.columns
        ):
            values = unique_values(
                dataframe,
                "split_purge_semantics",
            )

            checks.append(
                build_check(
                    name=(
                        f"{name}."
                        "purge_semantics"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            EXPECTED_PURGE_SEMANTICS
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Purge semantics correta."
                        if values
                        == [
                            EXPECTED_PURGE_SEMANTICS
                        ]
                        else (
                            "Purge semantics "
                            "incompatível."
                        )
                    ),
                    expected=(
                        EXPECTED_PURGE_SEMANTICS
                    ),
                    found=values,
                )
            )

        if (
            "test_holdout_policy"
            in dataframe.columns
        ):
            values = unique_values(
                dataframe,
                "test_holdout_policy",
            )

            checks.append(
                build_check(
                    name=(
                        f"{name}."
                        "test_holdout_policy"
                    ),
                    status=(
                        "PASS"
                        if values
                        == [
                            EXPECTED_TEST_HOLDOUT_POLICY
                        ]
                        else "FAIL"
                    ),
                    message=(
                        "Holdout policy correta."
                        if values
                        == [
                            EXPECTED_TEST_HOLDOUT_POLICY
                        ]
                        else (
                            "Holdout policy "
                            "incompatível."
                        )
                    ),
                    expected=(
                        EXPECTED_TEST_HOLDOUT_POLICY
                    ),
                    found=values,
                )
            )

    def build_keys(
        dataframe: pd.DataFrame,
    ) -> set[
        tuple[Any, Any]
    ]:
        return set(
            zip(
                pd.to_datetime(
                    dataframe[
                        "feature_date"
                    ]
                ),
                dataframe[
                    "ticker"
                ].astype(
                    str
                ),
            )
        )

    train_keys = (
        build_keys(
            train
        )
    )

    validation_keys = (
        build_keys(
            validation
        )
    )

    test_keys = (
        build_keys(
            test
        )
    )

    overlaps = {
        "train_validation": len(
            train_keys
            & validation_keys
        ),
        "train_test": len(
            train_keys
            & test_keys
        ),
        "validation_test": len(
            validation_keys
            & test_keys
        ),
    }

    overlap_total = sum(
        overlaps.values()
    )

    checks.append(
        build_check(
            name=(
                "temporal_split_overlap"
            ),
            status=(
                "PASS"
                if overlap_total == 0
                else "FAIL"
            ),
            message=(
                "Não existe overlap "
                "entre splits."
                if overlap_total == 0
                else (
                    "Existe overlap "
                    "entre splits."
                )
            ),
            **overlaps,
        )
    )

    train_target_max = (
        pd.to_datetime(
            train[
                "target_date"
            ]
        ).max()
    )

    validation_feature_min = (
        pd.to_datetime(
            validation[
                "feature_date"
            ]
        ).min()
    )

    validation_target_max = (
        pd.to_datetime(
            validation[
                "target_date"
            ]
        ).max()
    )

    test_feature_min = (
        pd.to_datetime(
            test[
                "feature_date"
            ]
        ).min()
    )

    train_purge_ok = (
        train_target_max
        < validation_feature_min
    )

    validation_purge_ok = (
        validation_target_max
        < test_feature_min
    )

    checks.append(
        build_check(
            name=(
                "train_validation_purge"
            ),
            status=(
                "PASS"
                if train_purge_ok
                else "FAIL"
            ),
            message=(
                "Train target termina antes "
                "do início da validation."
                if train_purge_ok
                else (
                    "Train target invade "
                    "validation."
                )
            ),
            train_max_target=(
                pd.Timestamp(
                    train_target_max
                )
                .date()
                .isoformat()
            ),
            validation_min_feature=(
                pd.Timestamp(
                    validation_feature_min
                )
                .date()
                .isoformat()
            ),
        )
    )

    checks.append(
        build_check(
            name=(
                "validation_test_purge"
            ),
            status=(
                "PASS"
                if validation_purge_ok
                else "FAIL"
            ),
            message=(
                "Validation target termina "
                "antes do início do test."
                if validation_purge_ok
                else (
                    "Validation target "
                    "invade test."
                )
            ),
            validation_max_target=(
                pd.Timestamp(
                    validation_target_max
                )
                .date()
                .isoformat()
            ),
            test_min_feature=(
                pd.Timestamp(
                    test_feature_min
                )
                .date()
                .isoformat()
            ),
        )
    )

    final_split_rows = (
        len(
            train
        )
        + len(
            validation
        )
        + len(
            test
        )
    )

    if (
        eligibility is not None
        and "ml_eligible"
        in eligibility.columns
    ):
        eligible_count = int(
            eligibility[
                "ml_eligible"
            ]
            .fillna(
                False
            )
            .astype(
                bool
            )
            .sum()
        )

        reconciliation_ok = (
            final_split_rows
            <= eligible_count
        )

        checks.append(
            build_check(
                name=(
                    "split_vs_eligible_"
                    "reconciliation"
                ),
                status=(
                    "PASS"
                    if reconciliation_ok
                    else "FAIL"
                ),
                message=(
                    "Splits são subconjunto "
                    "do universo elegível."
                    if reconciliation_ok
                    else (
                        "Splits excedem "
                        "o universo elegível."
                    )
                ),
                eligible_rows=(
                    eligible_count
                ),
                final_split_rows=(
                    final_split_rows
                ),
                purged_or_unassigned_rows=(
                    eligible_count
                    - final_split_rows
                ),
            )
        )

    return checks


# ============================================================
# Overall status
# ============================================================

def resolve_overall_status(
    dataset_results: list[
        dict[str, Any]
    ],
    platform_checks: list[
        dict[str, Any]
    ],
) -> str:
    statuses: list[
        str
    ] = []

    statuses.extend(
        result.get(
            "status",
            "FAIL",
        )
        for result
        in dataset_results
    )

    statuses.extend(
        check.get(
            "status",
            "FAIL",
        )
        for check
        in platform_checks
    )

    if "FAIL" in statuses:
        return "FAIL"

    if "WARN" in statuses:
        return "WARN"

    return "PASS"


# ============================================================
# Console
# ============================================================

def print_dataset_summary(
    result: dict[
        str,
        Any,
    ],
) -> None:
    print(
        f"\n{result['name'].upper()}"
    )

    print(
        "-" * 50
    )

    print(
        f"Status: "
        f"{result.get('status')}"
    )

    print(
        "Freshness policy: "
        f"{result.get('freshness_mode')}"
    )

    if (
        "row_count"
        in result
    ):
        print(
            f"Rows: "
            f"{result['row_count']:,}"
        )

    if (
        "ticker_count"
        in result
    ):
        print(
            f"Tickers: "
            f"{result['ticker_count']:,}"
        )

    if (
        "duplicate_count"
        in result
    ):
        print(
            f"Duplicates: "
            f"{result['duplicate_count']:,}"
        )

    if (
        "min_date"
        in result
    ):
        print(
            f"Date: "
            f"{result['min_date']} "
            "-> "
            f"{result['max_date']}"
        )

    if (
        "freshness_column"
        in result
    ):
        print(
            "Freshness column: "
            f"{result['freshness_column']}"
        )

    if (
        "freshness_latest_date"
        in result
    ):
        print(
            "Freshness latest date: "
            f"{result['freshness_latest_date']}"
        )

    if (
        "freshness_days"
        in result
    ):
        print(
            "Freshness: "
            f"{result['freshness_days']} "
            "dia(s)"
        )

    non_pass_checks = [
        check
        for check
        in result[
            "checks"
        ]
        if check[
            "status"
        ]
        != "PASS"
    ]

    if non_pass_checks:
        print(
            "Alerts:"
        )

        for check in (
            non_pass_checks
        ):
            print(
                f"  [{check['status']}] "
                f"{check['name']}: "
                f"{check['message']}"
            )


def print_platform_checks(
    checks: list[
        dict[str, Any]
    ],
) -> None:
    print(
        "\n======================================"
    )

    print(
        "Platform Contract Checks"
    )

    print(
        "======================================"
    )

    for check in checks:
        print(
            f"[{check['status']}] "
            f"{check['name']}: "
            f"{check['message']}"
        )


# ============================================================
# Persistence
# ============================================================

def save_report(
    report: dict[
        str,
        Any,
    ],
) -> Path:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated_at = (
        datetime.fromisoformat(
            report[
                "generated_at"
            ]
        )
    )

    history_filename = (
        generated_at
        .strftime(
            "%Y%m%dT%H%M%SZ"
        )
        + ".json"
    )

    history_path = (
        HISTORY_DIR
        / history_filename
    )

    payload = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        default=json_default,
    )

    LATEST_PATH.write_text(
        payload,
        encoding="utf-8",
    )

    history_path.write_text(
        payload,
        encoding="utf-8",
    )

    return history_path


# ============================================================
# Check counters
# ============================================================

def count_checks(
    dataset_results: list[
        dict[str, Any]
    ],
    platform_checks: list[
        dict[str, Any]
    ],
    status: str,
) -> int:
    dataset_count = sum(
        check[
            "status"
        ]
        == status
        for result
        in dataset_results
        for check
        in result[
            "checks"
        ]
    )

    platform_count = sum(
        check[
            "status"
        ]
        == status
        for check
        in platform_checks
    )

    return int(
        dataset_count
        + platform_count
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = (
        argparse.ArgumentParser(
            description=(
                "Executa observabilidade "
                "semântica da FII Data & "
                "AI Platform."
            )
        )
    )

    parser.add_argument(
        "--max-freshness-days",
        type=int,
        default=(
            DEFAULT_MAX_FRESHNESS_DAYS
        ),
        help=(
            "Máximo de dias aceitos para "
            "datasets com freshness temporal "
            "aplicável. Default: 7."
        ),
    )

    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help=(
            "Data de referência YYYY-MM-DD. "
            "Default: data UTC atual."
        ),
    )

    args = parser.parse_args()

    if (
        args.max_freshness_days
        < 0
    ):
        raise ValueError(
            "--max-freshness-days não "
            "pode ser negativo."
        )

    if args.reference_date:
        reference_date = (
            pd.Timestamp(
                args.reference_date
            )
        )

    else:
        reference_date = (
            pd.Timestamp.now(
                tz="UTC"
            )
            .tz_localize(
                None
            )
        )

    generated_at = datetime.now(
        timezone.utc
    )

    print(
        "Executando Pipeline Health..."
    )

    print(
        "Observability version: "
        f"{OBSERVABILITY_VERSION}"
    )

    print(
        "Reference date: "
        f"{reference_date.date()}"
    )

    print(
        "Max freshness: "
        f"{args.max_freshness_days} "
        "dia(s)"
    )

    print(
        "Freshness semantics: "
        "DATA_DATE / TARGET_DATE / "
        "EVENT_DRIVEN / HISTORICAL_SPLIT"
    )

    dataset_results: list[
        dict[str, Any]
    ] = []

    loaded_datasets: dict[
        str,
        pd.DataFrame | None,
    ] = {}

    print(
        "\n======================================"
    )

    print(
        "Dataset Health"
    )

    print(
        "======================================"
    )

    for spec in DATASETS:
        (
            result,
            dataframe,
        ) = inspect_dataset(
            spec=spec,
            reference_date=(
                reference_date
            ),
            max_freshness_days=(
                args.max_freshness_days
            ),
        )

        dataset_results.append(
            result
        )

        loaded_datasets[
            spec.name
        ] = dataframe

        print_dataset_summary(
            result
        )

    platform_checks: list[
        dict[str, Any]
    ] = []

    platform_checks.extend(
        validate_core_semantics(
            loaded_datasets
        )
    )

    platform_checks.extend(
        validate_cross_dataset_relations(
            loaded_datasets
        )
    )

    platform_checks.extend(
        validate_temporal_splits(
            loaded_datasets
        )
    )

    print_platform_checks(
        platform_checks
    )

    overall_status = (
        resolve_overall_status(
            dataset_results=(
                dataset_results
            ),
            platform_checks=(
                platform_checks
            ),
        )
    )

    pass_count = count_checks(
        dataset_results=(
            dataset_results
        ),
        platform_checks=(
            platform_checks
        ),
        status="PASS",
    )

    warn_count = count_checks(
        dataset_results=(
            dataset_results
        ),
        platform_checks=(
            platform_checks
        ),
        status="WARN",
    )

    fail_count = count_checks(
        dataset_results=(
            dataset_results
        ),
        platform_checks=(
            platform_checks
        ),
        status="FAIL",
    )

    report = {
        "observability_version": (
            OBSERVABILITY_VERSION
        ),
        "generated_at": (
            generated_at.isoformat()
        ),
        "reference_date": (
            reference_date
            .date()
            .isoformat()
        ),
        "max_freshness_days": (
            args.max_freshness_days
        ),
        "freshness_policy": {
            "DATA_DATE": (
                "Uses latest operational "
                "data date."
            ),
            "TARGET_DATE": (
                "Uses latest supervised "
                "target_date."
            ),
            "EVENT_DRIVEN": (
                "Last event age is not "
                "used as staleness."
            ),
            "HISTORICAL_SPLIT": (
                "Health is governed by "
                "split boundaries, purge "
                "and overlap checks."
            ),
        },
        "overall_status": (
            overall_status
        ),
        "summary": {
            "datasets_monitored": (
                len(
                    dataset_results
                )
            ),
            "checks_passed": (
                pass_count
            ),
            "checks_warned": (
                warn_count
            ),
            "checks_failed": (
                fail_count
            ),
        },
        "datasets": {
            result[
                "name"
            ]: result
            for result
            in dataset_results
        },
        "platform_checks": (
            platform_checks
        ),
    }

    history_path = save_report(
        report
    )

    print(
        "\n======================================"
    )

    print(
        "Pipeline Health Summary"
    )

    print(
        "======================================"
    )

    print(
        "Overall status: "
        f"{overall_status}"
    )

    print(
        "Datasets monitored: "
        f"{len(dataset_results)}"
    )

    print(
        f"Checks PASS: "
        f"{pass_count}"
    )

    print(
        f"Checks WARN: "
        f"{warn_count}"
    )

    print(
        f"Checks FAIL: "
        f"{fail_count}"
    )

    print(
        "\nOutputs:"
    )

    print(
        f"Latest: "
        f"{LATEST_PATH}"
    )

    print(
        f"History: "
        f"{history_path}"
    )

    if overall_status == "FAIL":
        raise RuntimeError(
            "Pipeline Health terminou "
            "com status FAIL. "
            "Consulte latest.json."
        )

    print(
        "\nPipeline Health concluído "
        f"com status {overall_status}."
    )


if __name__ == "__main__":
    main()