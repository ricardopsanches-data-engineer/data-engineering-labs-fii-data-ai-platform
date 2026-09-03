from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================
# Project
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]


# ============================================================
# Walk-Forward contract
# ============================================================

WALK_FORWARD_VERSION = "v1"

EXPECTED_TRAINING_DATASET_VERSION = "v4"
EXPECTED_FEATURE_VERSION = "v7"
EXPECTED_ELIGIBILITY_VERSION = "v3"
EXPECTED_PRICE_HISTORY_VERSION = "v3"
EXPECTED_PRICE_QUALITY_VERSION = "v2"

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)

EXPECTED_TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS = (
    "TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND"
)

TARGET_COLUMN = (
    "target_return_next_5d"
)

VALIDATION_FEATURE_SESSIONS = 5

N_FOLDS = 12

MIN_TRAIN_FEATURE_SESSIONS = 80

RANDOM_STATE = 42


# ============================================================
# Governed feature allowlist
# ============================================================

FEATURE_COLUMNS = [
    "daily_return",
    "return_5d",
    "volatility_5d",
    "price_to_ma5",

    "return_10d",
    "volatility_10d",
    "price_to_ma10",

    "return_20d",
    "volatility_20d",
    "price_to_ma20",

    "return_spread_5d_10d",
    "ma_ratio_5_10",
    "volatility_ratio_5d_10d",
    "trades_ratio_5d_10d",

    "return_spread_10d_20d",
    "ma_ratio_10_20",
    "volatility_ratio_10d_20d",
    "trades_ratio_10d_20d",
]


# ============================================================
# Inputs
# ============================================================

TRAINING_DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
    / "fii_training_dataset.parquet"
)

TEST_SPLIT_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
    / "test.parquet"
)


# ============================================================
# Outputs
# ============================================================

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_walk_forward"
)

FOLD_METRICS_PATH = (
    OUTPUT_DIR
    / "fold_metrics.parquet"
)

SUMMARY_PATH = (
    OUTPUT_DIR
    / "summary.json"
)


# ============================================================
# Structures
# ============================================================

@dataclass(frozen=True)
class FoldDefinition:
    fold_id: int

    validation_dates: tuple[
        pd.Timestamp,
        ...
    ]

    validation_start: pd.Timestamp
    validation_end: pd.Timestamp


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
        value_float = float(
            value
        )

        if not np.isfinite(
            value_float
        ):
            return None

        return value_float

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

    if (
        converted is not value
        or converted is None
    ):
        return converted

    raise TypeError(
        "Objeto não serializável: "
        f"{type(value).__name__}"
    )


# ============================================================
# Generic helpers
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


def require_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    missing = [
        column
        for column in required_columns
        if column
        not in dataframe.columns
    ]

    if missing:
        raise RuntimeError(
            f"{dataset_name} não possui "
            "as colunas obrigatórias: "
            f"{missing}"
        )


def assert_single_value(
    dataframe: pd.DataFrame,
    column: str,
    expected: Any,
    dataset_name: str,
) -> None:
    values = unique_values(
        dataframe,
        column,
    )

    if values != [
        expected
    ]:
        raise RuntimeError(
            f"{dataset_name}.{column} "
            "incompatível. "
            f"Esperado={expected!r}, "
            f"encontrado={values!r}"
        )


def assert_optional_single_value(
    dataframe: pd.DataFrame,
    column: str,
    expected: Any,
    dataset_name: str,
) -> None:
    """
    Valida metadado adicional quando
    a coluna existe fisicamente.
    """

    if column not in dataframe.columns:
        return

    assert_single_value(
        dataframe=dataframe,
        column=column,
        expected=expected,
        dataset_name=dataset_name,
    )


# ============================================================
# Loading
# ============================================================

def load_training_dataset() -> pd.DataFrame:
    if not TRAINING_DATASET_PATH.exists():
        raise FileNotFoundError(
            "Training Dataset não encontrado: "
            f"{TRAINING_DATASET_PATH}"
        )

    dataframe = pd.read_parquet(
        TRAINING_DATASET_PATH
    )

    required = [
        "ticker",
        "feature_date",
        "target_date",
        "ml_eligible",
        "feature_ready",
        TARGET_COLUMN,

        "training_dataset_version",

        "feature_version",
        "ml_eligibility_version",
        "source_price_history_version",
        "source_price_quality_version",

        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",

        "price_semantics",
        "return_semantics",
        (
            "corporate_action_value_semantics"
        ),

        *FEATURE_COLUMNS,
    ]

    require_columns(
        dataframe=dataframe,
        required_columns=required,
        dataset_name="Training Dataset",
    )

    dataframe = (
        dataframe.copy()
    )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
        ],
        errors="raise",
    )

    dataframe[
        "target_date"
    ] = pd.to_datetime(
        dataframe[
            "target_date"
        ],
        errors="raise",
    )

    return dataframe


def load_test_boundary() -> pd.Timestamp:
    """
    O TEST é lido somente para descobrir
    sua fronteira temporal.

    Nenhuma feature, target ou prediction
    do TEST é usada na avaliação
    walk-forward.
    """

    if not TEST_SPLIT_PATH.exists():
        raise FileNotFoundError(
            "TEST split não encontrado: "
            f"{TEST_SPLIT_PATH}"
        )

    test = pd.read_parquet(
        TEST_SPLIT_PATH,
        columns=[
            "feature_date",
        ],
    )

    if test.empty:
        raise RuntimeError(
            "TEST split está vazio."
        )

    test[
        "feature_date"
    ] = pd.to_datetime(
        test[
            "feature_date"
        ],
        errors="raise",
    )

    test_start = pd.Timestamp(
        test[
            "feature_date"
        ].min()
    )

    return test_start


# ============================================================
# Contract validation
# ============================================================

def validate_training_contract(
    dataframe: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )

    print(
        "Training Dataset Contract"
    )

    print(
        "======================================"
    )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    target_null_count = int(
        dataframe[
            TARGET_COLUMN
        ].isna().sum()
    )

    target_nonfinite_count = int(
        (
            ~np.isfinite(
                dataframe[
                    TARGET_COLUMN
                ].astype(
                    float
                )
            )
        ).sum()
    )

    invalid_target_order = int(
        (
            dataframe[
                "target_date"
            ]
            <= dataframe[
                "feature_date"
            ]
        ).sum()
    )

    print(
        f"Rows: {len(dataframe):,}"
    )

    print(
        "Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        "Feature dates: "
        f"{dataframe['feature_date'].min().date()} "
        "-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        "Target dates: "
        f"{dataframe['target_date'].min().date()} "
        "-> "
        f"{dataframe['target_date'].max().date()}"
    )

    print(
        f"Duplicates: {duplicate_count:,}"
    )

    print(
        f"Target nulls: {target_null_count:,}"
    )

    print(
        "Target nonfinite: "
        f"{target_nonfinite_count:,}"
    )

    print(
        "Invalid target chronology: "
        f"{invalid_target_order:,}"
    )

    if duplicate_count != 0:
        raise RuntimeError(
            "Training Dataset possui "
            "duplicidades."
        )

    if target_null_count != 0:
        raise RuntimeError(
            "Training Dataset possui "
            "targets nulos."
        )

    if target_nonfinite_count != 0:
        raise RuntimeError(
            "Training Dataset possui "
            "targets não finitos."
        )

    if invalid_target_order != 0:
        raise RuntimeError(
            "Training Dataset possui "
            "target_date <= feature_date."
        )

    assert_single_value(
        dataframe,
        "training_dataset_version",
        EXPECTED_TRAINING_DATASET_VERSION,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "feature_version",
        EXPECTED_FEATURE_VERSION,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "ml_eligibility_version",
        EXPECTED_ELIGIBILITY_VERSION,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "source_price_history_version",
        EXPECTED_PRICE_HISTORY_VERSION,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "source_price_quality_version",
        EXPECTED_PRICE_QUALITY_VERSION,
        "Training Dataset",
    )

    assert_optional_single_value(
        dataframe,
        "source_feature_version",
        EXPECTED_FEATURE_VERSION,
        "Training Dataset",
    )

    assert_optional_single_value(
        dataframe,
        "source_ml_eligibility_version",
        EXPECTED_ELIGIBILITY_VERSION,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "target_horizon",
        EXPECTED_TARGET_HORIZON,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "target_horizon_semantics",
        EXPECTED_TARGET_HORIZON_SEMANTICS,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "target_return_semantics",
        EXPECTED_TARGET_RETURN_SEMANTICS,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "price_semantics",
        EXPECTED_PRICE_SEMANTICS,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "return_semantics",
        EXPECTED_RETURN_SEMANTICS,
        "Training Dataset",
    )

    assert_single_value(
        dataframe,
        "corporate_action_value_semantics",
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS,
        "Training Dataset",
    )

    numeric_failures: list[
        str
    ] = []

    nonfinite_counts: dict[
        str,
        int,
    ] = {}

    for column in FEATURE_COLUMNS:
        if not pd.api.types.is_numeric_dtype(
            dataframe[
                column
            ]
        ):
            numeric_failures.append(
                column
            )

            continue

        values = dataframe[
            column
        ].to_numpy(
            dtype=float,
            na_value=np.nan,
        )

        nonfinite_mask = (
            np.isinf(
                values
            )
        )

        nonfinite_count = int(
            nonfinite_mask.sum()
        )

        if nonfinite_count > 0:
            nonfinite_counts[
                column
            ] = nonfinite_count

    if numeric_failures:
        raise RuntimeError(
            "Features não numéricas: "
            f"{numeric_failures}"
        )

    if nonfinite_counts:
        raise RuntimeError(
            "Features possuem valores "
            "inf/-inf: "
            f"{nonfinite_counts}"
        )

    print(
        "Training Dataset contract: PASS"
    )


# ============================================================
# Eligible universe
# ============================================================

def build_eligible_universe(
    dataframe: pd.DataFrame,
    test_start: pd.Timestamp,
) -> pd.DataFrame:
    eligible = dataframe.loc[
        dataframe[
            "ml_eligible"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
        & dataframe[
            "feature_ready"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
        & (
            dataframe[
                "feature_date"
            ]
            < test_start
        )
        & (
            dataframe[
                "target_date"
            ]
            < test_start
        )
    ].copy()

    eligible = eligible.sort_values(
        [
            "feature_date",
            "ticker",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    if eligible.empty:
        raise RuntimeError(
            "Universo pré-TEST elegível "
            "ficou vazio."
        )

    return eligible


# ============================================================
# Fold generation
# ============================================================

def build_folds(
    eligible: pd.DataFrame,
) -> list[
    FoldDefinition
]:
    feature_dates = (
        eligible[
            "feature_date"
        ]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    feature_dates = [
        pd.Timestamp(
            value
        )
        for value in feature_dates
    ]

    minimum_needed = (
        MIN_TRAIN_FEATURE_SESSIONS
        + (
            N_FOLDS
            * VALIDATION_FEATURE_SESSIONS
        )
    )

    if len(
        feature_dates
    ) < minimum_needed:
        raise RuntimeError(
            "Histórico insuficiente para "
            "Walk-Forward v1. "
            f"Datas disponíveis={len(feature_dates)}, "
            f"mínimo requerido={minimum_needed}."
        )

    validation_pool_size = (
        N_FOLDS
        * VALIDATION_FEATURE_SESSIONS
    )

    validation_pool = (
        feature_dates[
            -validation_pool_size:
        ]
    )

    folds: list[
        FoldDefinition
    ] = []

    for fold_index in range(
        N_FOLDS
    ):
        start_index = (
            fold_index
            * VALIDATION_FEATURE_SESSIONS
        )

        end_index = (
            start_index
            + VALIDATION_FEATURE_SESSIONS
        )

        fold_dates = (
            validation_pool[
                start_index:end_index
            ]
        )

        if (
            len(
                fold_dates
            )
            != VALIDATION_FEATURE_SESSIONS
        ):
            raise RuntimeError(
                "Falha ao construir "
                "validation window."
            )

        folds.append(
            FoldDefinition(
                fold_id=(
                    fold_index
                    + 1
                ),
                validation_dates=tuple(
                    fold_dates
                ),
                validation_start=(
                    fold_dates[
                        0
                    ]
                ),
                validation_end=(
                    fold_dates[
                        -1
                    ]
                ),
            )
        )

    return folds


# ============================================================
# Fold materialization
# ============================================================

def materialize_fold(
    eligible: pd.DataFrame,
    fold: FoldDefinition,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    train = eligible.loc[
        (
            eligible[
                "feature_date"
            ]
            < fold.validation_start
        )
        & (
            eligible[
                "target_date"
            ]
            < fold.validation_start
        )
    ].copy()

    validation = eligible.loc[
        eligible[
            "feature_date"
        ].isin(
            fold.validation_dates
        )
    ].copy()

    train = train.sort_values(
        [
            "feature_date",
            "ticker",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    validation = validation.sort_values(
        [
            "feature_date",
            "ticker",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    if train.empty:
        raise RuntimeError(
            f"Fold {fold.fold_id}: "
            "TRAIN vazio."
        )

    if validation.empty:
        raise RuntimeError(
            f"Fold {fold.fold_id}: "
            "VALIDATION vazia."
        )

    train_dates = (
        train[
            "feature_date"
        ]
        .drop_duplicates()
        .nunique()
    )

    if (
        train_dates
        < MIN_TRAIN_FEATURE_SESSIONS
    ):
        raise RuntimeError(
            f"Fold {fold.fold_id}: "
            "histórico de treino abaixo "
            "do mínimo. "
            f"Datas={train_dates}, "
            f"mínimo="
            f"{MIN_TRAIN_FEATURE_SESSIONS}."
        )

    train_target_max = pd.Timestamp(
        train[
            "target_date"
        ].max()
    )

    validation_feature_min = (
        pd.Timestamp(
            validation[
                "feature_date"
            ].min()
        )
    )

    if not (
        train_target_max
        < validation_feature_min
    ):
        raise RuntimeError(
            f"Fold {fold.fold_id}: "
            "purge temporal violado."
        )

    train_keys = set(
        zip(
            train[
                "feature_date"
            ],
            train[
                "ticker"
            ].astype(
                str
            ),
        )
    )

    validation_keys = set(
        zip(
            validation[
                "feature_date"
            ],
            validation[
                "ticker"
            ].astype(
                str
            ),
        )
    )

    overlap = len(
        train_keys
        & validation_keys
    )

    if overlap != 0:
        raise RuntimeError(
            f"Fold {fold.fold_id}: "
            f"overlap={overlap}."
        )

    return (
        train,
        validation,
    )


# ============================================================
# ML matrices
# ============================================================

def prepare_xy(
    dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.Series,
]:
    X = dataframe[
        FEATURE_COLUMNS
    ].copy()

    y = dataframe[
        TARGET_COLUMN
    ].astype(
        float
    ).copy()

    return (
        X,
        y,
    )


# ============================================================
# Models
# ============================================================

def build_models() -> dict[
    str,
    Any,
]:
    return {
        "dummy_mean": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "model",
                    DummyRegressor(
                        strategy="mean"
                    ),
                ),
            ]
        ),

        "linear_regression": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "model",
                    LinearRegression(),
                ),
            ]
        ),

        "random_forest": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=200,
                        random_state=(
                            RANDOM_STATE
                        ),
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


# ============================================================
# Metrics
# ============================================================

def directional_accuracy(
    y_true: pd.Series,
    prediction: np.ndarray,
) -> float:
    true_positive = (
        y_true.to_numpy(
            dtype=float
        )
        > 0
    )

    predicted_positive = (
        np.asarray(
            prediction,
            dtype=float,
        )
        > 0
    )

    return float(
        np.mean(
            true_positive
            == predicted_positive
        )
    )


def majority_direction_from_train(
    y_train: pd.Series,
) -> str:
    positive_share = float(
        (
            y_train
            > 0
        ).mean()
    )

    if positive_share > 0.5:
        return "POSITIVE"

    return "NON_POSITIVE"


def majority_direction_accuracy(
    y_validation: pd.Series,
    direction: str,
) -> float:
    true_positive = (
        y_validation.to_numpy(
            dtype=float
        )
        > 0
    )

    if direction == "POSITIVE":
        predicted_positive = (
            np.ones(
                len(
                    y_validation
                ),
                dtype=bool,
            )
        )

    else:
        predicted_positive = (
            np.zeros(
                len(
                    y_validation
                ),
                dtype=bool,
            )
        )

    return float(
        np.mean(
            true_positive
            == predicted_positive
        )
    )


def calculate_model_metrics(
    model_name: str,
    y_validation: pd.Series,
    prediction: np.ndarray,
    majority_accuracy: float,
) -> dict[str, Any]:
    mae = float(
        mean_absolute_error(
            y_validation,
            prediction,
        )
    )

    rmse = float(
        np.sqrt(
            mean_squared_error(
                y_validation,
                prediction,
            )
        )
    )

    r2 = float(
        r2_score(
            y_validation,
            prediction,
        )
    )

    direction_accuracy = (
        directional_accuracy(
            y_true=y_validation,
            prediction=prediction,
        )
    )

    direction_lift = (
        direction_accuracy
        - majority_accuracy
    )

    prediction_array = np.asarray(
        prediction,
        dtype=float,
    )

    return {
        "model": model_name,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,

        "directional_accuracy": (
            direction_accuracy
        ),

        "directional_lift": (
            direction_lift
        ),

        "prediction_mean": float(
            prediction_array.mean()
        ),

        "prediction_median": float(
            np.median(
                prediction_array
            )
        ),

        "prediction_min": float(
            prediction_array.min()
        ),

        "prediction_max": float(
            prediction_array.max()
        ),
    }


# ============================================================
# Fold execution
# ============================================================

def execute_fold(
    eligible: pd.DataFrame,
    fold: FoldDefinition,
) -> list[
    dict[str, Any]
]:
    (
        train,
        validation,
    ) = materialize_fold(
        eligible=eligible,
        fold=fold,
    )

    (
        X_train,
        y_train,
    ) = prepare_xy(
        train
    )

    (
        X_validation,
        y_validation,
    ) = prepare_xy(
        validation
    )

    train_nan_count = int(
        X_train.isna().sum().sum()
    )

    validation_nan_count = int(
        X_validation.isna().sum().sum()
    )

    majority_direction = (
        majority_direction_from_train(
            y_train
        )
    )

    majority_accuracy = (
        majority_direction_accuracy(
            y_validation=(
                y_validation
            ),
            direction=(
                majority_direction
            ),
        )
    )

    models = build_models()

    results: list[
        dict[str, Any]
    ] = []

    print(
        "\n--------------------------------------"
    )

    print(
        f"Fold {fold.fold_id:02d}"
    )

    print(
        "--------------------------------------"
    )

    print(
        "TRAIN feature dates: "
        f"{train['feature_date'].min().date()} "
        "-> "
        f"{train['feature_date'].max().date()}"
    )

    print(
        "TRAIN target max: "
        f"{train['target_date'].max().date()}"
    )

    print(
        "VALIDATION feature dates: "
        f"{validation['feature_date'].min().date()} "
        "-> "
        f"{validation['feature_date'].max().date()}"
    )

    print(
        "VALIDATION target dates: "
        f"{validation['target_date'].min().date()} "
        "-> "
        f"{validation['target_date'].max().date()}"
    )

    print(
        f"TRAIN rows: {len(train):,}"
    )

    print(
        "VALIDATION rows: "
        f"{len(validation):,}"
    )

    print(
        "TRAIN tickers: "
        f"{train['ticker'].nunique():,}"
    )

    print(
        "VALIDATION tickers: "
        f"{validation['ticker'].nunique():,}"
    )

    print(
        "TRAIN NaNs before imputation: "
        f"{train_nan_count:,}"
    )

    print(
        "VALIDATION NaNs before imputation: "
        f"{validation_nan_count:,}"
    )

    print(
        "Majority direction learned "
        "from TRAIN: "
        f"{majority_direction}"
    )

    print(
        "Majority validation accuracy: "
        f"{majority_accuracy:.2%}"
    )

    train_target_mean = float(
        y_train.mean()
    )

    train_target_median = float(
        y_train.median()
    )

    validation_target_mean = float(
        y_validation.mean()
    )

    validation_target_median = float(
        y_validation.median()
    )

    train_positive_share = float(
        (
            y_train
            > 0
        ).mean()
    )

    validation_positive_share = float(
        (
            y_validation
            > 0
        ).mean()
    )

    for (
        model_name,
        model,
    ) in models.items():

        model.fit(
            X_train,
            y_train,
        )

        prediction = model.predict(
            X_validation
        )

        metrics = (
            calculate_model_metrics(
                model_name=model_name,
                y_validation=(
                    y_validation
                ),
                prediction=(
                    prediction
                ),
                majority_accuracy=(
                    majority_accuracy
                ),
            )
        )

        record = {
            "walk_forward_version": (
                WALK_FORWARD_VERSION
            ),

            "fold_id": (
                fold.fold_id
            ),

            "model": (
                model_name
            ),

            "validation_feature_sessions": (
                VALIDATION_FEATURE_SESSIONS
            ),

            "train_start": (
                train[
                    "feature_date"
                ]
                .min()
            ),

            "train_end": (
                train[
                    "feature_date"
                ]
                .max()
            ),

            "train_target_max": (
                train[
                    "target_date"
                ]
                .max()
            ),

            "validation_start": (
                validation[
                    "feature_date"
                ]
                .min()
            ),

            "validation_end": (
                validation[
                    "feature_date"
                ]
                .max()
            ),

            "validation_target_min": (
                validation[
                    "target_date"
                ]
                .min()
            ),

            "validation_target_max": (
                validation[
                    "target_date"
                ]
                .max()
            ),

            "train_rows": int(
                len(
                    train
                )
            ),

            "validation_rows": int(
                len(
                    validation
                )
            ),

            "train_tickers": int(
                train[
                    "ticker"
                ].nunique()
            ),

            "validation_tickers": int(
                validation[
                    "ticker"
                ].nunique()
            ),

            "train_feature_dates": int(
                train[
                    "feature_date"
                ].nunique()
            ),

            "validation_feature_dates": int(
                validation[
                    "feature_date"
                ].nunique()
            ),

            "train_nan_count": (
                train_nan_count
            ),

            "validation_nan_count": (
                validation_nan_count
            ),

            "train_target_mean": (
                train_target_mean
            ),

            "train_target_median": (
                train_target_median
            ),

            "train_positive_share": (
                train_positive_share
            ),

            "validation_target_mean": (
                validation_target_mean
            ),

            "validation_target_median": (
                validation_target_median
            ),

            "validation_positive_share": (
                validation_positive_share
            ),

            "majority_direction": (
                majority_direction
            ),

            "majority_directional_accuracy": (
                majority_accuracy
            ),

            **metrics,
        }

        results.append(
            record
        )

        print(
            "\n"
            f"{model_name}:"
        )

        print(
            f"  MAE: "
            f"{metrics['mae']:.4%}"
        )

        print(
            f"  RMSE: "
            f"{metrics['rmse']:.4%}"
        )

        print(
            f"  R²: "
            f"{metrics['r2']:.6f}"
        )

        print(
            "  Directional accuracy: "
            f"{metrics['directional_accuracy']:.2%}"
        )

        print(
            "  Directional lift: "
            f"{metrics['directional_lift']:+.2%}"
        )

    return results


# ============================================================
# Aggregate results
# ============================================================

def build_model_summary(
    fold_metrics: pd.DataFrame,
) -> dict[
    str,
    Any,
]:
    summary: dict[
        str,
        Any,
    ] = {}

    for model_name in (
        fold_metrics[
            "model"
        ]
        .drop_duplicates()
        .tolist()
    ):
        model_rows = (
            fold_metrics.loc[
                fold_metrics[
                    "model"
                ]
                == model_name
            ]
            .copy()
        )

        summary[
            model_name
        ] = {
            "folds": int(
                len(
                    model_rows
                )
            ),

            "mae_mean": float(
                model_rows[
                    "mae"
                ].mean()
            ),

            "mae_median": float(
                model_rows[
                    "mae"
                ].median()
            ),

            "mae_std": float(
                model_rows[
                    "mae"
                ].std(
                    ddof=0
                )
            ),

            "rmse_mean": float(
                model_rows[
                    "rmse"
                ].mean()
            ),

            "rmse_median": float(
                model_rows[
                    "rmse"
                ].median()
            ),

            "rmse_std": float(
                model_rows[
                    "rmse"
                ].std(
                    ddof=0
                )
            ),

            "r2_mean": float(
                model_rows[
                    "r2"
                ].mean()
            ),

            "r2_median": float(
                model_rows[
                    "r2"
                ].median()
            ),

            "directional_accuracy_mean": float(
                model_rows[
                    "directional_accuracy"
                ].mean()
            ),

            "directional_accuracy_median": float(
                model_rows[
                    "directional_accuracy"
                ].median()
            ),

            "directional_lift_mean": float(
                model_rows[
                    "directional_lift"
                ].mean()
            ),

            "directional_lift_median": float(
                model_rows[
                    "directional_lift"
                ].median()
            ),

            "positive_directional_lift_folds": int(
                (
                    model_rows[
                        "directional_lift"
                    ]
                    > 0
                ).sum()
            ),

            "non_positive_directional_lift_folds": int(
                (
                    model_rows[
                        "directional_lift"
                    ]
                    <= 0
                ).sum()
            ),

            "positive_r2_folds": int(
                (
                    model_rows[
                        "r2"
                    ]
                    > 0
                ).sum()
            ),

            "non_positive_r2_folds": int(
                (
                    model_rows[
                        "r2"
                    ]
                    <= 0
                ).sum()
            ),
        }

    return summary


def identify_best_models(
    model_summary: dict[
        str,
        Any,
    ],
) -> dict[
    str,
    str,
]:
    best_mae = min(
        model_summary,
        key=lambda model: (
            model_summary[
                model
            ][
                "mae_mean"
            ]
        ),
    )

    best_rmse = min(
        model_summary,
        key=lambda model: (
            model_summary[
                model
            ][
                "rmse_mean"
            ]
        ),
    )

    best_r2 = max(
        model_summary,
        key=lambda model: (
            model_summary[
                model
            ][
                "r2_mean"
            ]
        ),
    )

    best_direction = max(
        model_summary,
        key=lambda model: (
            model_summary[
                model
            ][
                "directional_accuracy_mean"
            ]
        ),
    )

    best_lift = max(
        model_summary,
        key=lambda model: (
            model_summary[
                model
            ][
                "directional_lift_mean"
            ]
        ),
    )

    return {
        "best_mean_mae": (
            best_mae
        ),
        "best_mean_rmse": (
            best_rmse
        ),
        "best_mean_r2": (
            best_r2
        ),
        (
            "best_mean_directional_accuracy"
        ): (
            best_direction
        ),
        "best_mean_directional_lift": (
            best_lift
        ),
    }


# ============================================================
# Persistence
# ============================================================

def save_outputs(
    fold_metrics: pd.DataFrame,
    summary: dict[
        str,
        Any,
    ],
) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fold_metrics.to_parquet(
        FOLD_METRICS_PATH,
        index=False,
    )

    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            default=json_default,
        ),
        encoding="utf-8",
    )


# ============================================================
# Console summary
# ============================================================

def print_final_summary(
    summary: dict[
        str,
        Any,
    ],
) -> None:
    print(
        "\n======================================"
    )

    print(
        "Walk-Forward Summary"
    )

    print(
        "======================================"
    )

    print(
        "Walk-Forward version: "
        f"{summary['walk_forward_version']}"
    )

    print(
        "Folds: "
        f"{summary['fold_count']}"
    )

    print(
        "Validation sessions/fold: "
        f"{summary['validation_feature_sessions']}"
    )

    print(
        "TEST boundary: "
        f"{summary['test_start']}"
    )

    print(
        "TEST used for model evaluation: NO"
    )

    print(
        "\nAggregate metrics:"
    )

    for (
        model_name,
        metrics,
    ) in summary[
        "models"
    ].items():

        print(
            f"\n{model_name}"
        )

        print(
            "  Mean MAE: "
            f"{metrics['mae_mean']:.4%}"
        )

        print(
            "  Median MAE: "
            f"{metrics['mae_median']:.4%}"
        )

        print(
            "  Mean RMSE: "
            f"{metrics['rmse_mean']:.4%}"
        )

        print(
            "  Mean R²: "
            f"{metrics['r2_mean']:.6f}"
        )

        print(
            "  Mean directional accuracy: "
            f"{metrics['directional_accuracy_mean']:.2%}"
        )

        print(
            "  Mean directional lift: "
            f"{metrics['directional_lift_mean']:+.2%}"
        )

        print(
            "  Positive lift folds: "
            f"{metrics['positive_directional_lift_folds']}"
            "/"
            f"{metrics['folds']}"
        )

        print(
            "  Positive R² folds: "
            f"{metrics['positive_r2_folds']}"
            "/"
            f"{metrics['folds']}"
        )

    print(
        "\nBest aggregate models:"
    )

    for (
        criterion,
        model,
    ) in summary[
        "best_models"
    ].items():

        print(
            f"  {criterion}: "
            f"{model}"
        )

    print(
        "\nOutputs:"
    )

    print(
        f"  Fold metrics: "
        f"{FOLD_METRICS_PATH}"
    )

    print(
        f"  Summary: "
        f"{SUMMARY_PATH}"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    print(
        "Executando FII Walk-Forward..."
    )

    print(
        "Walk-Forward version: "
        f"{WALK_FORWARD_VERSION}"
    )

    print(
        "Policy: EXPANDING WINDOW"
    )

    print(
        "Validation sessions/fold: "
        f"{VALIDATION_FEATURE_SESSIONS}"
    )

    print(
        f"Requested folds: "
        f"{N_FOLDS}"
    )

    print(
        "Target: "
        f"{TARGET_COLUMN}"
    )

    print(
        "Target semantics: "
        f"{EXPECTED_TARGET_RETURN_SEMANTICS}"
    )

    print(
        "Feature count: "
        f"{len(FEATURE_COLUMNS)}"
    )

    training = (
        load_training_dataset()
    )

    validate_training_contract(
        training
    )

    test_start = (
        load_test_boundary()
    )

    print(
        "\n======================================"
    )

    print(
        "Final TEST Protection"
    )

    print(
        "======================================"
    )

    print(
        "TEST feature start: "
        f"{test_start.date()}"
    )

    print(
        "TEST features used in modeling: NO"
    )

    print(
        "TEST targets used in modeling: NO"
    )

    print(
        "TEST predictions generated: NO"
    )

    print(
        "TEST role: "
        "RESERVED FINAL HOLDOUT"
    )

    eligible = (
        build_eligible_universe(
            dataframe=training,
            test_start=test_start,
        )
    )

    print(
        "\n======================================"
    )

    print(
        "Walk-Forward Eligible Universe"
    )

    print(
        "======================================"
    )

    print(
        f"Rows: {len(eligible):,}"
    )

    print(
        "Tickers: "
        f"{eligible['ticker'].nunique():,}"
    )

    print(
        "Feature dates: "
        f"{eligible['feature_date'].min().date()} "
        "-> "
        f"{eligible['feature_date'].max().date()}"
    )

    print(
        "Target dates: "
        f"{eligible['target_date'].min().date()} "
        "-> "
        f"{eligible['target_date'].max().date()}"
    )

    folds = build_folds(
        eligible
    )

    print(
        "\n======================================"
    )

    print(
        "Fold Plan"
    )

    print(
        "======================================"
    )

    for fold in folds:
        print(
            f"Fold {fold.fold_id:02d}: "
            f"{fold.validation_start.date()} "
            "-> "
            f"{fold.validation_end.date()}"
        )

    all_results: list[
        dict[str, Any]
    ] = []

    for fold in folds:
        fold_results = (
            execute_fold(
                eligible=eligible,
                fold=fold,
            )
        )

        all_results.extend(
            fold_results
        )

    fold_metrics = (
        pd.DataFrame(
            all_results
        )
    )

    expected_result_rows = (
        N_FOLDS
        * 3
    )

    if (
        len(
            fold_metrics
        )
        != expected_result_rows
    ):
        raise RuntimeError(
            "Quantidade inesperada de "
            "resultados. "
            f"Esperado={expected_result_rows}, "
            f"obtido={len(fold_metrics)}."
        )

    metric_columns = [
        "mae",
        "rmse",
        "r2",
        "directional_accuracy",
        "directional_lift",
    ]

    if fold_metrics[
        metric_columns
    ].isna().any().any():
        raise RuntimeError(
            "Fold metrics possui NaN."
        )

    model_summary = (
        build_model_summary(
            fold_metrics
        )
    )

    best_models = (
        identify_best_models(
            model_summary
        )
    )

    generated_at = datetime.now(
        timezone.utc
    )

    summary = {
        "walk_forward_version": (
            WALK_FORWARD_VERSION
        ),

        "generated_at": (
            generated_at.isoformat()
        ),

        "policy": (
            "EXPANDING_WINDOW_PURGED"
        ),

        "fold_count": (
            N_FOLDS
        ),

        "validation_feature_sessions": (
            VALIDATION_FEATURE_SESSIONS
        ),

        "minimum_train_feature_sessions": (
            MIN_TRAIN_FEATURE_SESSIONS
        ),

        "target": (
            TARGET_COLUMN
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

        "feature_count": int(
            len(
                FEATURE_COLUMNS
            )
        ),

        "feature_columns": (
            FEATURE_COLUMNS
        ),

        "source_contract": {
            "training_dataset_version": (
                EXPECTED_TRAINING_DATASET_VERSION
            ),

            "feature_version": (
                EXPECTED_FEATURE_VERSION
            ),

            "ml_eligibility_version": (
                EXPECTED_ELIGIBILITY_VERSION
            ),

            "source_price_history_version": (
                EXPECTED_PRICE_HISTORY_VERSION
            ),

            "source_price_quality_version": (
                EXPECTED_PRICE_QUALITY_VERSION
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
        },

        "test_start": (
            test_start
            .date()
            .isoformat()
        ),

        "test_policy": (
            "RESERVED_FINAL_HOLDOUT_"
            "NO_MODEL_EVALUATION"
        ),

        "test_features_used": (
            False
        ),

        "test_targets_used": (
            False
        ),

        "test_predictions_generated": (
            False
        ),

        "eligible_pre_test_rows": int(
            len(
                eligible
            )
        ),

        "eligible_pre_test_tickers": int(
            eligible[
                "ticker"
            ].nunique()
        ),

        "models": (
            model_summary
        ),

        "best_models": (
            best_models
        ),
    }

    save_outputs(
        fold_metrics=(
            fold_metrics
        ),
        summary=summary,
    )

    print_final_summary(
        summary
    )

    print(
        "\nFII Walk-Forward concluído "
        "com sucesso."
    )


if __name__ == "__main__":
    main()