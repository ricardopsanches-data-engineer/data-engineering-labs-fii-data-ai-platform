from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


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

from src.ml.common.feature_contract import (
    get_feature_contract,
)


# ============================================================
# Paths
# ============================================================

SPLIT_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
)

TRAIN_PATH = (
    SPLIT_BASE_DIR
    / "train.parquet"
)

VALIDATION_PATH = (
    SPLIT_BASE_DIR
    / "validation.parquet"
)

TEST_PATH = (
    SPLIT_BASE_DIR
    / "test.parquet"
)


# ============================================================
# Runtime configuration
# ============================================================

DEFAULT_RANDOM_STATE = 42

DEFAULT_RF_ESTIMATORS = 200


# ============================================================
# Baseline contract
# ============================================================

BASELINE_VERSION = "v5"


EXPECTED_SPLIT_VERSION = "v3"

EXPECTED_TRAINING_DATASET_VERSION = "v4"

EXPECTED_FEATURE_CONTRACT_VERSION = "v3"

EXPECTED_FEATURE_VERSION = "v7"

EXPECTED_ELIGIBILITY_VERSION = "v3"

EXPECTED_PRICE_QUALITY_VERSION = "v2"

EXPECTED_PRICE_HISTORY_VERSION = "v3"

EXPECTED_PRICE_HISTORY_SOURCE = (
    "FII_CORPORATE_ACTION_ADJUSTED_PRICES_V3"
)

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


# ============================================================
# Result structures
# ============================================================

@dataclass
class MajorityDirectionBaseline:
    """
    Regra direcional aprendida
    exclusivamente no TRAIN.
    """

    direction: str

    positive_rate_train: float

    non_positive_rate_train: float

    train_accuracy: float


@dataclass
class ModelResult:
    """
    Resultado de um modelo avaliado
    exclusivamente na VALIDATION.
    """

    name: str

    mae: float

    rmse: float

    r2: float

    directional_accuracy: float

    directional_lift: float

    prediction_min: float

    prediction_max: float

    prediction_mean: float

    prediction_median: float


# ============================================================
# Split loading
# ============================================================

def load_split(
    path: Path,
    split_name: str,
) -> pd.DataFrame:
    """
    Carrega um split temporal.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Split {split_name} não encontrado: "
            f"{path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    required_identity_columns = [
        "feature_date",
        "target_date",
        "ticker",
    ]

    missing_identity_columns = [
        column
        for column in required_identity_columns
        if column not in dataframe.columns
    ]

    if missing_identity_columns:
        raise ValueError(
            f"{split_name} possui schema "
            "mínimo incompatível: "
            f"{missing_identity_columns}"
        )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
        ]
    )

    dataframe[
        "target_date"
    ] = pd.to_datetime(
        dataframe[
            "target_date"
        ]
    )

    dataframe[
        "ticker"
    ] = (
        dataframe[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    print(
        f"{split_name}: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


# ============================================================
# Metadata helpers
# ============================================================

def get_unique_string_value(
    dataframe: pd.DataFrame,
    column: str,
    split_name: str,
) -> str:
    """
    Retorna exatamente um valor textual
    de metadata.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"{split_name}: coluna "
            f"{column} ausente."
        )

    values = (
        dataframe[
            column
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    if len(values) != 1:
        raise ValueError(
            f"{split_name}: metadata "
            f"{column} ambígua: "
            f"{values}"
        )

    return values[0]


def get_unique_int_value(
    dataframe: pd.DataFrame,
    column: str,
    split_name: str,
) -> int:
    """
    Retorna exatamente um valor inteiro
    de metadata.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"{split_name}: coluna "
            f"{column} ausente."
        )

    values = (
        dataframe[
            column
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if len(values) != 1:
        raise ValueError(
            f"{split_name}: metadata "
            f"{column} ambígua: "
            f"{values}"
        )

    return int(
        values[0]
    )


# ============================================================
# Target discovery
# ============================================================

def discover_target_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Descobre dinamicamente o target
    oficial do Training Dataset.
    """

    if "target_name" not in dataframe.columns:
        raise ValueError(
            "Coluna target_name "
            "não encontrada."
        )

    values = (
        dataframe[
            "target_name"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    if len(values) == 0:
        raise ValueError(
            "Nenhum target_name encontrado."
        )

    if len(values) > 1:
        raise ValueError(
            "Mais de um target_name "
            "encontrado: "
            f"{values}"
        )

    target_column = values[0]

    if target_column not in dataframe.columns:
        raise ValueError(
            f"Target {target_column} "
            "não existe no dataset."
        )

    return target_column


# ============================================================
# Split contract validation
# ============================================================

def validate_split_contract(
    dataframe: pd.DataFrame,
    split_name: str,
    target_column: str,
) -> None:
    """
    Valida contrato completo de um split.

    Baseline v5 exige:

    - Temporal Split v3;
    - Training Dataset v4;
    - Feature Contract v3;
    - Features v7;
    - Eligibility v3;
    - Price Quality v2;
    - Price History v3;
    - target econômico T+5;
    - somente ml_eligible=True.
    """

    required_columns = [
        "feature_date",
        "target_date",

        "ticker",
        "cnpj",
        "codigo_cvm",

        "feature_ready",
        "ml_eligible",

        target_column,

        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",

        "training_dataset_version",

        "source_feature_version",
        "source_ml_eligibility_version",
        "source_price_quality_version",
        "source_price_history_version",
        "source_price_history_source",

        "price_semantics",
        "return_semantics",
        "corporate_action_value_semantics",

        "split_name",
        "split_version",

        "split_source_training_dataset_version",
        "split_source_feature_version",
        "split_source_ml_eligibility_version",
        "split_source_price_quality_version",
        "split_source_price_history_version",

        "split_requires_ml_eligible",
        "split_purge_semantics",

        "split_target_horizon",
        "split_target_horizon_semantics",
        "split_target_return_semantics",

        "split_price_semantics",
        "split_return_semantics",
        "split_corporate_action_value_semantics",

        "test_holdout_policy",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{split_name} possui colunas "
            f"ausentes: {missing_columns}"
        )

    if dataframe.empty:
        raise ValueError(
            f"{split_name} está vazio."
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
            target_column
        ]
        .isna()
        .sum()
    )

    non_finite_target_count = int(
        (
            dataframe[
                target_column
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    target_column
                ]
            )
        ).sum()
    )

    feature_ready_invalid = int(
        (
            ~dataframe[
                "feature_ready"
            ]
            .fillna(False)
            .astype(bool)
        ).sum()
    )

    ml_eligible_invalid = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
            .fillna(False)
            .astype(bool)
        ).sum()
    )

    invalid_target_dates = int(
        (
            dataframe[
                "target_date"
            ]
            <= dataframe[
                "feature_date"
            ]
        ).sum()
    )

    stored_split_name = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_name",
            split_name=split_name,
        )
    )

    split_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_version",
            split_name=split_name,
        )
    )

    training_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="training_dataset_version",
            split_name=split_name,
        )
    )

    split_source_training_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column=(
                "split_source_training_dataset_version"
            ),
            split_name=split_name,
        )
    )

    feature_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="source_feature_version",
            split_name=split_name,
        )
    )

    split_feature_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_source_feature_version",
            split_name=split_name,
        )
    )

    eligibility_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="source_ml_eligibility_version",
            split_name=split_name,
        )
    )

    split_eligibility_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_source_ml_eligibility_version",
            split_name=split_name,
        )
    )

    price_quality_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="source_price_quality_version",
            split_name=split_name,
        )
    )

    split_price_quality_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_source_price_quality_version",
            split_name=split_name,
        )
    )

    price_history_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="source_price_history_version",
            split_name=split_name,
        )
    )

    split_price_history_version = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_source_price_history_version",
            split_name=split_name,
        )
    )

    price_history_source = (
        get_unique_string_value(
            dataframe=dataframe,
            column="source_price_history_source",
            split_name=split_name,
        )
    )

    target_horizon = (
        get_unique_int_value(
            dataframe=dataframe,
            column="target_horizon",
            split_name=split_name,
        )
    )

    split_target_horizon = (
        get_unique_int_value(
            dataframe=dataframe,
            column="split_target_horizon",
            split_name=split_name,
        )
    )

    target_horizon_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="target_horizon_semantics",
            split_name=split_name,
        )
    )

    split_target_horizon_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_target_horizon_semantics",
            split_name=split_name,
        )
    )

    target_return_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="target_return_semantics",
            split_name=split_name,
        )
    )

    split_target_return_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_target_return_semantics",
            split_name=split_name,
        )
    )

    price_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="price_semantics",
            split_name=split_name,
        )
    )

    split_price_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_price_semantics",
            split_name=split_name,
        )
    )

    return_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="return_semantics",
            split_name=split_name,
        )
    )

    split_return_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_return_semantics",
            split_name=split_name,
        )
    )

    corporate_action_value_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="corporate_action_value_semantics",
            split_name=split_name,
        )
    )

    split_corporate_action_value_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column=(
                "split_corporate_action_value_semantics"
            ),
            split_name=split_name,
        )
    )

    purge_semantics = (
        get_unique_string_value(
            dataframe=dataframe,
            column="split_purge_semantics",
            split_name=split_name,
        )
    )

    test_policy = (
        get_unique_string_value(
            dataframe=dataframe,
            column="test_holdout_policy",
            split_name=split_name,
        )
    )

    eligibility_policy_values = (
        dataframe[
            "split_requires_ml_eligible"
        ]
        .dropna()
        .astype(bool)
        .unique()
        .tolist()
    )

    print(
        f"\n{split_name.upper()}"
    )

    print(
        "-" * 38
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Target nulo: "
        f"{target_null_count:,}"
    )

    print(
        f"Target não finito: "
        f"{non_finite_target_count:,}"
    )

    print(
        "feature_ready=False: "
        f"{feature_ready_invalid:,}"
    )

    print(
        "ml_eligible=False: "
        f"{ml_eligible_invalid:,}"
    )

    print(
        "Target date inválida: "
        f"{invalid_target_dates:,}"
    )

    print(
        f"Split version: "
        f"{split_version}"
    )

    print(
        "Training Dataset version: "
        f"{training_version}"
    )

    print(
        "Feature version: "
        f"{feature_version}"
    )

    print(
        "Eligibility version: "
        f"{eligibility_version}"
    )

    print(
        "Price Quality version: "
        f"{price_quality_version}"
    )

    print(
        "Price History version: "
        f"{price_history_version}"
    )

    print(
        "Target semantics: "
        f"{target_return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{corporate_action_value_semantics}"
    )

    if duplicate_count > 0:
        raise ValueError(
            f"{split_name} possui "
            "duplicidades."
        )

    if target_null_count > 0:
        raise ValueError(
            f"{split_name} possui "
            "target nulo."
        )

    if non_finite_target_count > 0:
        raise ValueError(
            f"{split_name} possui "
            "target não finito."
        )

    if feature_ready_invalid > 0:
        raise ValueError(
            f"{split_name} possui "
            "feature_ready=False."
        )

    if ml_eligible_invalid > 0:
        raise ValueError(
            f"{split_name} possui "
            "ml_eligible=False."
        )

    if invalid_target_dates > 0:
        raise ValueError(
            f"{split_name} possui "
            "target_date inválida."
        )

    if stored_split_name != split_name:
        raise ValueError(
            f"{split_name}: split_name "
            f"incompatível: "
            f"{stored_split_name}"
        )

    if split_version != EXPECTED_SPLIT_VERSION:
        raise ValueError(
            "Baseline v5 exige "
            f"Temporal Split "
            f"{EXPECTED_SPLIT_VERSION}."
        )

    if (
        training_version
        != EXPECTED_TRAINING_DATASET_VERSION
    ):
        raise ValueError(
            "Baseline v5 exige "
            f"Training Dataset "
            f"{EXPECTED_TRAINING_DATASET_VERSION}."
        )

    if (
        split_source_training_version
        != EXPECTED_TRAINING_DATASET_VERSION
    ):
        raise ValueError(
            "Split referencia Training Dataset "
            "incompatível."
        )

    if (
        feature_version
        != EXPECTED_FEATURE_VERSION
    ):
        raise ValueError(
            "Baseline v5 exige "
            f"Features "
            f"{EXPECTED_FEATURE_VERSION}."
        )

    if (
        split_feature_version
        != EXPECTED_FEATURE_VERSION
    ):
        raise ValueError(
            "Split referencia Features "
            "incompatível."
        )

    if (
        eligibility_version
        != EXPECTED_ELIGIBILITY_VERSION
    ):
        raise ValueError(
            "Baseline v5 exige "
            f"ML Eligibility "
            f"{EXPECTED_ELIGIBILITY_VERSION}."
        )

    if (
        split_eligibility_version
        != EXPECTED_ELIGIBILITY_VERSION
    ):
        raise ValueError(
            "Split referencia ML Eligibility "
            "incompatível."
        )

    if (
        price_quality_version
        != EXPECTED_PRICE_QUALITY_VERSION
    ):
        raise ValueError(
            "Baseline v5 exige "
            "Price Quality "
            f"{EXPECTED_PRICE_QUALITY_VERSION}."
        )

    if (
        split_price_quality_version
        != EXPECTED_PRICE_QUALITY_VERSION
    ):
        raise ValueError(
            "Split referencia Price Quality "
            "incompatível."
        )

    if (
        price_history_version
        != EXPECTED_PRICE_HISTORY_VERSION
    ):
        raise ValueError(
            "Baseline v5 exige "
            "Price History "
            f"{EXPECTED_PRICE_HISTORY_VERSION}."
        )

    if (
        split_price_history_version
        != EXPECTED_PRICE_HISTORY_VERSION
    ):
        raise ValueError(
            "Split referencia Price History "
            "incompatível."
        )

    if (
        price_history_source
        != EXPECTED_PRICE_HISTORY_SOURCE
    ):
        raise ValueError(
            "Baseline encontrou "
            "Price History source "
            "incompatível."
        )

    if (
        target_horizon
        != EXPECTED_TARGET_HORIZON
    ):
        raise ValueError(
            "Baseline v5 exige "
            f"target_horizon="
            f"{EXPECTED_TARGET_HORIZON}."
        )

    if (
        split_target_horizon
        != EXPECTED_TARGET_HORIZON
    ):
        raise ValueError(
            "Split possui target horizon "
            "incompatível."
        )

    if (
        target_horizon_semantics
        != EXPECTED_TARGET_HORIZON_SEMANTICS
    ):
        raise ValueError(
            "target_horizon_semantics "
            "incompatível."
        )

    if (
        split_target_horizon_semantics
        != EXPECTED_TARGET_HORIZON_SEMANTICS
    ):
        raise ValueError(
            "Split possui target horizon "
            "semantics incompatível."
        )

    if (
        target_return_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Baseline exige target "
            "econômico."
        )

    if (
        split_target_return_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Split possui target return "
            "semantics incompatível."
        )

    if (
        price_semantics
        != EXPECTED_PRICE_SEMANTICS
    ):
        raise ValueError(
            "price_semantics incompatível."
        )

    if (
        split_price_semantics
        != EXPECTED_PRICE_SEMANTICS
    ):
        raise ValueError(
            "Split possui "
            "price_semantics incompatível."
        )

    if (
        return_semantics
        != EXPECTED_RETURN_SEMANTICS
    ):
        raise ValueError(
            "return_semantics incompatível."
        )

    if (
        split_return_semantics
        != EXPECTED_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Split possui "
            "return_semantics incompatível."
        )

    if (
        corporate_action_value_semantics
        != EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ):
        raise ValueError(
            "Corporate Action value semantics "
            "incompatível."
        )

    if (
        split_corporate_action_value_semantics
        != EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ):
        raise ValueError(
            "Split possui Corporate Action "
            "value semantics incompatível."
        )

    if eligibility_policy_values != [
        True
    ]:
        raise ValueError(
            f"{split_name} não registra "
            "split_requires_ml_eligible=True."
        )

    if purge_semantics != (
        "TARGET_DATE_BEFORE_NEXT_SPLIT"
    ):
        raise ValueError(
            "Semântica de purge incompatível."
        )

    if test_policy != (
        "RESERVED_UNTOUCHED_FOR_MODEL_SELECTION"
    ):
        raise ValueError(
            "Política de holdout TEST "
            "incompatível."
        )


# ============================================================
# All-splits validation
# ============================================================

def validate_all_splits(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    target_column: str,
) -> None:
    """
    Valida os três splits.

    TEST é validado estruturalmente,
    mas não é utilizado na modelagem.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Temporal Splits"
    )
    print(
        "======================================"
    )

    validate_split_contract(
        dataframe=train,
        split_name="train",
        target_column=target_column,
    )

    validate_split_contract(
        dataframe=validation,
        split_name="validation",
        target_column=target_column,
    )

    validate_split_contract(
        dataframe=test,
        split_name="test",
        target_column=target_column,
    )

    print(
        "\nData Quality dos splits aprovada."
    )


# ============================================================
# Target consistency
# ============================================================

def validate_target_consistency(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    """
    Confirma que todos os splits declaram
    exatamente o mesmo target_name.
    """

    targets = {}

    for name, dataframe in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:
        targets[name] = (
            discover_target_column(
                dataframe
            )
        )

    unique_targets = set(
        targets.values()
    )

    print(
        "\nTarget por split:"
    )

    for name, target in targets.items():
        print(
            f"  {name}: "
            f"{target}"
        )

    if len(unique_targets) != 1:
        raise ValueError(
            "Os splits possuem targets "
            "diferentes: "
            f"{targets}"
        )


# ============================================================
# X / y preparation
# ============================================================

def prepare_xy(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> tuple[
    pd.DataFrame,
    pd.Series,
]:
    """
    Separa X e y usando exclusivamente
    a allowlist do Feature Contract.

    Nenhuma seleção automática por dtype
    é utilizada.
    """

    x = dataframe[
        feature_columns
    ].copy()

    y = dataframe[
        target_column
    ].astype(
        float
    ).copy()

    return (
        x,
        y,
    )


# ============================================================
# Models
# ============================================================

def build_models(
    random_state: int,
    rf_estimators: int,
) -> dict[str, object]:
    """
    Modelos baseline.

    Todos os transformers são ajustados
    exclusivamente no TRAIN por meio
    de sklearn Pipeline.

    NaNs estruturais são tratados por
    SimpleImputer ajustado somente
    no TRAIN.

    Portanto statistics de VALIDATION
    e TEST não entram no imputer/scaler.
    """

    models: dict[
        str,
        object,
    ] = {}

    models[
        "DummyRegressor"
    ] = Pipeline(
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
    )

    models[
        "LinearRegression"
    ] = Pipeline(
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
    )

    models[
        "RandomForestRegressor"
    ] = Pipeline(
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
                    n_estimators=rf_estimators,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    return models


# ============================================================
# Majority direction baseline
# ============================================================

def fit_majority_direction_baseline(
    y_train: pd.Series,
) -> MajorityDirectionBaseline:
    """
    Aprende a regra direcional SOMENTE
    no TRAIN.
    """

    positive_rate = float(
        (
            y_train
            > 0
        ).mean()
    )

    non_positive_rate = (
        1.0
        - positive_rate
    )

    if positive_rate > non_positive_rate:
        direction = "POSITIVE"
        train_accuracy = positive_rate

    else:
        direction = "NON_POSITIVE"
        train_accuracy = non_positive_rate

    return MajorityDirectionBaseline(
        direction=direction,
        positive_rate_train=positive_rate,
        non_positive_rate_train=(
            non_positive_rate
        ),
        train_accuracy=float(
            train_accuracy
        ),
    )


def evaluate_majority_direction_baseline(
    baseline: MajorityDirectionBaseline,
    y_validation: pd.Series,
) -> float:
    """
    Avalia na VALIDATION a regra fixa
    aprendida exclusivamente no TRAIN.
    """

    true_positive = (
        np.asarray(
            y_validation
        )
        > 0
    )

    if baseline.direction == "POSITIVE":
        predicted_positive = np.ones(
            len(y_validation),
            dtype=bool,
        )

    elif baseline.direction == "NON_POSITIVE":
        predicted_positive = np.zeros(
            len(y_validation),
            dtype=bool,
        )

    else:
        raise ValueError(
            "Direção majoritária inválida: "
            f"{baseline.direction}"
        )

    accuracy = (
        true_positive
        == predicted_positive
    ).mean()

    return float(
        accuracy
    )


# ============================================================
# Metrics
# ============================================================

def calculate_directional_accuracy(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> float:
    """
    Mede acerto do sinal do retorno.
    """

    true_direction = (
        np.asarray(
            y_true
        )
        > 0
    )

    predicted_direction = (
        np.asarray(
            y_pred
        )
        > 0
    )

    accuracy = (
        true_direction
        == predicted_direction
    ).mean()

    return float(
        accuracy
    )


def calculate_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
    majority_validation_accuracy: float,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
]:
    """
    Calcula métricas de regressão
    e direção na VALIDATION.
    """

    mae = mean_absolute_error(
        y_true,
        y_pred,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred,
        )
    )

    r2 = r2_score(
        y_true,
        y_pred,
    )

    directional_accuracy = (
        calculate_directional_accuracy(
            y_true=y_true,
            y_pred=y_pred,
        )
    )

    directional_lift = (
        directional_accuracy
        - majority_validation_accuracy
    )

    return (
        float(mae),
        float(rmse),
        float(r2),
        float(directional_accuracy),
        float(directional_lift),
    )


# ============================================================
# Prediction validation
# ============================================================

def validate_predictions(
    model_name: str,
    predictions: np.ndarray,
) -> None:
    """
    Proteção contra previsões inválidas.

    Nenhum clipping automático é aplicado.
    """

    predictions_array = np.asarray(
        predictions,
        dtype=float,
    )

    non_finite_count = int(
        (
            ~np.isfinite(
                predictions_array
            )
        ).sum()
    )

    if non_finite_count > 0:
        raise ValueError(
            f"{model_name} produziu "
            f"{non_finite_count:,} "
            "previsões não finitas."
        )


# ============================================================
# Train / validation evaluation
# ============================================================

def evaluate_models(
    models: dict[str, object],
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_validation: pd.DataFrame,
    y_validation: pd.Series,
    majority_validation_accuracy: float,
) -> list[ModelResult]:
    """
    Treina exclusivamente no TRAIN.

    Avalia exclusivamente na VALIDATION.

    TEST não participa desta função.
    """

    results: list[
        ModelResult
    ] = []

    print(
        "\n======================================"
    )
    print(
        "Treinamento e Validation"
    )
    print(
        "======================================"
    )

    for name, model in models.items():
        print(
            f"\nTreinando: "
            f"{name}"
        )

        model.fit(
            x_train,
            y_train,
        )

        predictions = model.predict(
            x_validation
        )

        validate_predictions(
            model_name=name,
            predictions=predictions,
        )

        (
            mae,
            rmse,
            r2,
            directional_accuracy,
            directional_lift,
        ) = calculate_metrics(
            y_true=y_validation,
            y_pred=predictions,
            majority_validation_accuracy=(
                majority_validation_accuracy
            ),
        )

        prediction_min = float(
            np.min(
                predictions
            )
        )

        prediction_max = float(
            np.max(
                predictions
            )
        )

        prediction_mean = float(
            np.mean(
                predictions
            )
        )

        prediction_median = float(
            np.median(
                predictions
            )
        )

        results.append(
            ModelResult(
                name=name,

                mae=mae,

                rmse=rmse,

                r2=r2,

                directional_accuracy=(
                    directional_accuracy
                ),

                directional_lift=(
                    directional_lift
                ),

                prediction_min=(
                    prediction_min
                ),

                prediction_max=(
                    prediction_max
                ),

                prediction_mean=(
                    prediction_mean
                ),

                prediction_median=(
                    prediction_median
                ),
            )
        )

        print(
            f"  MAE:  "
            f"{mae:.8f} "
            f"({mae * 100:.4f}%)"
        )

        print(
            f"  RMSE: "
            f"{rmse:.8f} "
            f"({rmse * 100:.4f}%)"
        )

        print(
            f"  R²:   "
            f"{r2:.8f}"
        )

        print(
            "  Directional Accuracy: "
            f"{directional_accuracy:.4f} "
            f"({directional_accuracy * 100:.2f}%)"
        )

        print(
            "  Directional Lift: "
            f"{directional_lift * 100:+.2f} p.p."
        )

        print(
            "  Prediction min: "
            f"{prediction_min * 100:.4f}%"
        )

        print(
            "  Prediction max: "
            f"{prediction_max * 100:.4f}%"
        )

        print(
            "  Prediction mean: "
            f"{prediction_mean * 100:.4f}%"
        )

        print(
            "  Prediction median: "
            f"{prediction_median * 100:.4f}%"
        )

    return results


# ============================================================
# Results dataframe
# ============================================================

def results_to_dataframe(
    results: list[ModelResult],
) -> pd.DataFrame:
    """
    Converte resultados em DataFrame.
    """

    return pd.DataFrame(
        [
            {
                "model": result.name,

                "mae": result.mae,

                "rmse": result.rmse,

                "r2": result.r2,

                "directional_accuracy": (
                    result.directional_accuracy
                ),

                "directional_lift": (
                    result.directional_lift
                ),

                "prediction_min": (
                    result.prediction_min
                ),

                "prediction_max": (
                    result.prediction_max
                ),

                "prediction_mean": (
                    result.prediction_mean
                ),

                "prediction_median": (
                    result.prediction_median
                ),
            }

            for result in results
        ]
    )


# ============================================================
# Feature Contract diagnostics
# ============================================================

def print_feature_contract_summary(
    feature_contract: object,
) -> None:
    """
    Mostra Feature Contract utilizado.
    """

    print(
        "\n======================================"
    )
    print(
        "Feature Contract - Baseline"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{feature_contract.version}"
    )

    print(
        f"Source feature version: "
        f"{feature_contract.source_feature_version}"
    )

    print(
        f"Price semantics: "
        f"{feature_contract.price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{feature_contract.return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{feature_contract.corporate_action_value_semantics}"
    )

    print(
        "Corporate Action policy: "
        f"{feature_contract.corporate_action_policy}"
    )

    print(
        f"Windows: "
        f"{feature_contract.windows}"
    )

    print(
        f"Features: "
        f"{len(feature_contract.features):,}"
    )

    for feature in feature_contract.features:
        print(
            f"  {feature}"
        )

    if (
        feature_contract.version
        != EXPECTED_FEATURE_CONTRACT_VERSION
    ):
        raise ValueError(
            "Baseline v5 exige "
            f"Feature Contract "
            f"{EXPECTED_FEATURE_CONTRACT_VERSION}."
        )

    if (
        feature_contract.source_feature_version
        != EXPECTED_FEATURE_VERSION
    ):
        raise ValueError(
            "Feature Contract referencia "
            "versão de Features incompatível."
        )

    if (
        feature_contract.corporate_action_value_semantics
        != EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ):
        raise ValueError(
            "Feature Contract possui "
            "Corporate Action semantics "
            "incompatível."
        )


# ============================================================
# Feature matrix diagnostics
# ============================================================

def print_feature_matrix_diagnostics(
    x_train: pd.DataFrame,
    x_validation: pd.DataFrame,
) -> None:
    """
    Diagnóstico explícito dos NaNs
    estruturais antes da imputação.

    Isso permite comprovar que:

    - Feature Contract aceita NaN estrutural;
    - sklearn Pipeline realiza a imputação;
    - imputer é treinado somente no TRAIN.
    """

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico - Feature Matrix"
    )
    print(
        "======================================"
    )

    print(
        f"Features: "
        f"{x_train.shape[1]:,}"
    )

    print(
        f"Train rows: "
        f"{len(x_train):,}"
    )

    print(
        f"Validation rows: "
        f"{len(x_validation):,}"
    )

    train_nulls = (
        x_train
        .isna()
        .sum()
    )

    validation_nulls = (
        x_validation
        .isna()
        .sum()
    )

    train_total_nulls = int(
        train_nulls.sum()
    )

    validation_total_nulls = int(
        validation_nulls.sum()
    )

    print(
        "NaNs antes da imputação:"
    )

    print(
        f"  Train total: "
        f"{train_total_nulls:,}"
    )

    print(
        f"  Validation total: "
        f"{validation_total_nulls:,}"
    )

    columns_with_nulls = sorted(
        set(
            train_nulls[
                train_nulls > 0
            ].index.tolist()
        )
        |
        set(
            validation_nulls[
                validation_nulls > 0
            ].index.tolist()
        )
    )

    if not columns_with_nulls:
        print(
            "  Nenhuma feature com NaN."
        )

    else:
        print(
            "\nFeatures com NaN:"
        )

        for column in columns_with_nulls:
            print(
                f"  {column}: "
                f"train="
                f"{int(train_nulls.get(column, 0)):,} | "
                f"validation="
                f"{int(validation_nulls.get(column, 0)):,}"
            )


# ============================================================
# Target diagnostics
# ============================================================

def print_target_summary(
    y_train: pd.Series,
    y_validation: pd.Series,
) -> None:
    """
    Exibe distribuição do target
    sem acessar TEST.
    """

    print(
        "\n======================================"
    )
    print(
        "Distribuição do target"
    )
    print(
        "======================================"
    )

    for name, target in [
        ("Train", y_train),
        ("Validation", y_validation),
    ]:
        positive_rate = float(
            (
                target
                > 0
            ).mean()
        )

        quantiles = target.quantile(
            [
                0.01,
                0.05,
                0.25,
                0.50,
                0.75,
                0.95,
                0.99,
            ]
        )

        print(
            f"\n{name}:"
        )

        print(
            f"  Média: "
            f"{target.mean() * 100:.4f}%"
        )

        print(
            f"  Mediana: "
            f"{target.median() * 100:.4f}%"
        )

        print(
            f"  Desvio padrão: "
            f"{target.std() * 100:.4f}%"
        )

        print(
            f"  Mínimo: "
            f"{target.min() * 100:.4f}%"
        )

        print(
            f"  Máximo: "
            f"{target.max() * 100:.4f}%"
        )

        print(
            f"  Positivos: "
            f"{positive_rate * 100:.2f}%"
        )

        print(
            f"  Não positivos: "
            f"{(1.0 - positive_rate) * 100:.2f}%"
        )

        print(
            "  Quantis:"
        )

        for quantile, value in (
            quantiles.items()
        ):
            print(
                f"    q{int(quantile * 100):02d}: "
                f"{value * 100:.4f}%"
            )


# ============================================================
# Majority baseline diagnostics
# ============================================================

def print_majority_baseline(
    baseline: MajorityDirectionBaseline,
    validation_accuracy: float,
) -> None:
    """
    Exibe claramente:

    - regra aprendida no TRAIN;
    - desempenho da mesma regra
      na VALIDATION.
    """

    print(
        "\n======================================"
    )
    print(
        "Majority Direction Baseline"
    )
    print(
        "======================================"
    )

    print(
        "Aprendido exclusivamente no TRAIN."
    )

    print(
        "\nDistribuição TRAIN:"
    )

    print(
        "  Positive: "
        f"{baseline.positive_rate_train * 100:.2f}%"
    )

    print(
        "  Non-positive: "
        f"{baseline.non_positive_rate_train * 100:.2f}%"
    )

    print(
        "\nDireção aprendida: "
        f"{baseline.direction}"
    )

    print(
        "Accuracy no TRAIN: "
        f"{baseline.train_accuracy * 100:.2f}%"
    )

    print(
        "Accuracy da MESMA regra "
        "na VALIDATION: "
        f"{validation_accuracy * 100:.2f}%"
    )


# ============================================================
# Prediction diagnostics
# ============================================================

def print_prediction_diagnostics(
    results: pd.DataFrame,
    y_validation: pd.Series,
) -> None:
    """
    Diagnóstico das previsões.

    Nenhum clipping é feito.
    """

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico - Predictions"
    )
    print(
        "======================================"
    )

    print(
        "Validation target range:"
    )

    print(
        f"  min: "
        f"{y_validation.min() * 100:.4f}%"
    )

    print(
        f"  max: "
        f"{y_validation.max() * 100:.4f}%"
    )

    for _, row in results.iterrows():
        print(
            f"\n{row['model']}:"
        )

        print(
            "  prediction min: "
            f"{row['prediction_min'] * 100:.4f}%"
        )

        print(
            "  prediction max: "
            f"{row['prediction_max'] * 100:.4f}%"
        )

        print(
            "  prediction mean: "
            f"{row['prediction_mean'] * 100:.4f}%"
        )

        print(
            "  prediction median: "
            f"{row['prediction_median'] * 100:.4f}%"
        )


# ============================================================
# Metric rankings
# ============================================================

def print_metric_rankings(
    results: pd.DataFrame,
) -> None:
    """
    Exibe rankings separados.
    """

    rankings = [
        (
            "MAE",
            "mae",
            True,
            "%",
        ),
        (
            "RMSE",
            "rmse",
            True,
            "%",
        ),
        (
            "R²",
            "r2",
            False,
            "r2",
        ),
        (
            "Directional Accuracy",
            "directional_accuracy",
            False,
            "%",
        ),
        (
            "Directional Lift",
            "directional_lift",
            False,
            "pp",
        ),
    ]

    for (
        title,
        column,
        ascending,
        display_type,
    ) in rankings:

        print(
            "\n======================================"
        )

        print(
            f"Ranking por {title}"
        )

        print(
            "======================================"
        )

        ranking = results.sort_values(
            by=column,
            ascending=ascending,
        )

        for position, (_, row) in enumerate(
            ranking.iterrows(),
            start=1,
        ):
            value = row[
                column
            ]

            if display_type == "%":
                display = (
                    f"{value * 100:.4f}%"
                )

            elif display_type == "pp":
                display = (
                    f"{value * 100:+.2f} p.p."
                )

            else:
                display = (
                    f"{value:.6f}"
                )

            print(
                f"{position}. "
                f"{row['model']} | "
                f"{display}"
            )


# ============================================================
# Best models by metric
# ============================================================

def print_best_by_metric(
    results: pd.DataFrame,
) -> None:
    """
    Resume melhor modelo por métrica
    somente na VALIDATION.
    """

    best_mae = (
        results.sort_values(
            "mae"
        )
        .iloc[0]
    )

    best_rmse = (
        results.sort_values(
            "rmse"
        )
        .iloc[0]
    )

    best_r2 = (
        results.sort_values(
            "r2",
            ascending=False,
        )
        .iloc[0]
    )

    best_direction = (
        results.sort_values(
            "directional_accuracy",
            ascending=False,
        )
        .iloc[0]
    )

    best_lift = (
        results.sort_values(
            "directional_lift",
            ascending=False,
        )
        .iloc[0]
    )

    print(
        "\n======================================"
    )
    print(
        "Melhores por métrica - VALIDATION"
    )
    print(
        "======================================"
    )

    print(
        f"MAE: "
        f"{best_mae['model']} "
        f"({best_mae['mae'] * 100:.4f}%)"
    )

    print(
        f"RMSE: "
        f"{best_rmse['model']} "
        f"({best_rmse['rmse'] * 100:.4f}%)"
    )

    print(
        f"R²: "
        f"{best_r2['model']} "
        f"({best_r2['r2']:.6f})"
    )

    print(
        "Directional Accuracy: "
        f"{best_direction['model']} "
        f"("
        f"{best_direction['directional_accuracy'] * 100:.2f}%"
        f")"
    )

    print(
        "Directional Lift: "
        f"{best_lift['model']} "
        f"("
        f"{best_lift['directional_lift'] * 100:+.2f} p.p."
        f")"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Executa FII ML Baseline v5 "
            "sobre a cadeia econômica "
            "governada da Fase 0."
        )
    )

    parser.add_argument(
        "--rf-estimators",
        type=int,
        default=DEFAULT_RF_ESTIMATORS,
        help=(
            "Quantidade de árvores do "
            "RandomForest. Default: 200."
        ),
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=DEFAULT_RANDOM_STATE,
        help=(
            "Seed para reprodutibilidade. "
            "Default: 42."
        ),
    )

    args = parser.parse_args()

    if args.rf_estimators <= 0:
        raise ValueError(
            "--rf-estimators deve ser "
            "maior que zero."
        )

    print(
        "Executando FII ML Baseline..."
    )

    print(
        f"Baseline version: "
        f"{BASELINE_VERSION}"
    )

    print(
        "Evaluation policy: "
        "TRAIN -> VALIDATION"
    )

    print(
        "TEST policy: "
        "RESERVED / NO MODEL EVALUATION"
    )

    print(
        "\nCarregando splits:"
    )

    train = load_split(
        TRAIN_PATH,
        "train",
    )

    validation = load_split(
        VALIDATION_PATH,
        "validation",
    )

    test = load_split(
        TEST_PATH,
        "test",
    )

    target_column = (
        discover_target_column(
            train
        )
    )

    print(
        f"\nTarget oficial: "
        f"{target_column}"
    )

    validate_target_consistency(
        train=train,
        validation=validation,
        test=test,
    )

    validate_all_splits(
        train=train,
        validation=validation,
        test=test,
        target_column=target_column,
    )

    #
    # Feature Contract é criado a partir
    # do TRAIN.
    #
    # Nenhuma informação de VALIDATION
    # ou TEST é usada para definir
    # a allowlist.
    #

    feature_contract = (
        get_feature_contract(
            train
        )
    )

    print_feature_contract_summary(
        feature_contract
    )

    feature_columns = list(
        feature_contract.features
    )

    #
    # Somente TRAIN e VALIDATION
    # entram em X/y.
    #
    # TEST não é preparado nem utilizado
    # durante model selection.
    #

    x_train, y_train = prepare_xy(
        dataframe=train,
        feature_columns=feature_columns,
        target_column=target_column,
    )

    (
        x_validation,
        y_validation,
    ) = prepare_xy(
        dataframe=validation,
        feature_columns=feature_columns,
        target_column=target_column,
    )

    print(
        "\n======================================"
    )
    print(
        "Datasets usados pelo baseline"
    )
    print(
        "======================================"
    )

    print(
        f"Train: "
        f"{len(x_train):,}"
    )

    print(
        f"Validation: "
        f"{len(x_validation):,}"
    )

    print(
        f"Test reservado: "
        f"{len(test):,}"
    )

    print(
        "\nTEST não foi convertido para X/y "
        "e não participará de métricas."
    )

    print_feature_matrix_diagnostics(
        x_train=x_train,
        x_validation=x_validation,
    )

    print_target_summary(
        y_train=y_train,
        y_validation=y_validation,
    )

    #
    # --------------------------------------------------------
    # Majority direction baseline
    # --------------------------------------------------------
    #

    majority_baseline = (
        fit_majority_direction_baseline(
            y_train
        )
    )

    majority_validation_accuracy = (
        evaluate_majority_direction_baseline(
            baseline=majority_baseline,
            y_validation=y_validation,
        )
    )

    print_majority_baseline(
        baseline=majority_baseline,
        validation_accuracy=(
            majority_validation_accuracy
        ),
    )

    #
    # --------------------------------------------------------
    # Models
    # --------------------------------------------------------
    #

    models = build_models(
        random_state=args.random_state,
        rf_estimators=args.rf_estimators,
    )

    results = evaluate_models(
        models=models,

        x_train=x_train,
        y_train=y_train,

        x_validation=x_validation,
        y_validation=y_validation,

        majority_validation_accuracy=(
            majority_validation_accuracy
        ),
    )

    results_dataframe = (
        results_to_dataframe(
            results
        )
    )

    print_prediction_diagnostics(
        results=results_dataframe,
        y_validation=y_validation,
    )

    print_metric_rankings(
        results_dataframe
    )

    print_best_by_metric(
        results_dataframe
    )

    print(
        "\n======================================"
    )
    print(
        "Conclusão do baseline"
    )
    print(
        "======================================"
    )

    print(
        f"Baseline version: "
        f"{BASELINE_VERSION}"
    )

    print(
        "Temporal Split: "
        f"{EXPECTED_SPLIT_VERSION}"
    )

    print(
        "Training Dataset: "
        f"{EXPECTED_TRAINING_DATASET_VERSION}"
    )

    print(
        "Feature Contract: "
        f"{feature_contract.version}"
    )

    print(
        "Feature source: "
        f"{feature_contract.source_feature_version}"
    )

    print(
        "Eligibility source: "
        f"{EXPECTED_ELIGIBILITY_VERSION}"
    )

    print(
        "Price Quality source: "
        f"{EXPECTED_PRICE_QUALITY_VERSION}"
    )

    print(
        "Price History source: "
        f"{EXPECTED_PRICE_HISTORY_VERSION}"
    )

    print(
        "Target semantics: "
        f"{EXPECTED_TARGET_RETURN_SEMANTICS}"
    )

    print(
        "Corporate Action value semantics: "
        f"{EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS}"
    )

    print(
        "\nA direção majoritária foi aprendida "
        "exclusivamente no TRAIN."
    )

    print(
        "Os modelos foram treinados "
        "exclusivamente no TRAIN."
    )

    print(
        "Imputer e scaler foram ajustados "
        "exclusivamente no TRAIN."
    )

    print(
        "Model selection foi avaliada "
        "exclusivamente na VALIDATION."
    )

    print(
        "O TEST permaneceu reservado "
        "e não recebeu previsões."
    )

    print(
        "Nenhum clipping automático "
        "de targets ou predictions "
        "foi aplicado."
    )


if __name__ == "__main__":
    main()