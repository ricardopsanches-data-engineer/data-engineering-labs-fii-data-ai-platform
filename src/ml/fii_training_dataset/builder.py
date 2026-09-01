from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# Paths
# ============================================================

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

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_training_dataset.parquet"
)


# ============================================================
# Target contract
# ============================================================

DEFAULT_TARGET_HORIZON = 5

TRAINING_DATASET_VERSION = "v4"

TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)

TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)


# ============================================================
# Upstream contracts
# ============================================================

EXPECTED_FEATURE_VERSION = "v7"

EXPECTED_ELIGIBILITY_VERSION = "v3"

EXPECTED_PRICE_QUALITY_VERSION = "v2"

EXPECTED_PRICE_HISTORY_VERSION = "v3"

EXPECTED_PRICE_HISTORY_SOURCE = (
    "FII_CORPORATE_ACTION_ADJUSTED_PRICES_V3"
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

EXPECTED_FEATURE_CORPORATE_ACTION_POLICY = (
    "ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_"
    "NO_DIRECT_CA_PAYLOAD_FEATURES"
)


# ============================================================
# Features
# ============================================================

def load_features() -> pd.DataFrame:
    """
    Carrega Gold ML Features v7.
    """

    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            "FII Features não encontrado: "
            f"{FEATURES_PATH}"
        )

    print(
        "Carregando FII Features..."
    )

    dataframe = pd.read_parquet(
        FEATURES_PATH
    )

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price",

        "feature_ready",
        "feature_version",

        "price_semantics",
        "return_semantics",

        "corporate_action_value_semantics",
        "feature_corporate_action_policy",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "FII Features possui "
            "schema incompatível: "
            f"{missing_columns}"
        )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
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

    return dataframe


def validate_features(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida Features v7 e sua semântica.
    """

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "feature_date",
            ]
        ).sum()
    )

    versions = sorted(
        dataframe[
            "feature_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_semantics = sorted(
        dataframe[
            "price_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return_semantics = sorted(
        dataframe[
            "return_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    corporate_action_value_semantics = sorted(
        dataframe[
            "corporate_action_value_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    corporate_action_policy = sorted(
        dataframe[
            "feature_corporate_action_policy"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    ready_count = int(
        dataframe[
            "feature_ready"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - FII Features"
    )
    print(
        "======================================"
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
        f"Feature ready: "
        f"{ready_count:,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Feature versions: "
        f"{versions}"
    )

    print(
        f"Price semantics: "
        f"{price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{corporate_action_value_semantics}"
    )

    print(
        "Corporate Action feature policy: "
        f"{corporate_action_policy}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "FII Features possui "
            "duplicidades."
        )

    if versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "Training Dataset v4 exige "
            f"FII Features "
            f"{EXPECTED_FEATURE_VERSION}."
        )

    if price_semantics != [
        EXPECTED_PRICE_SEMANTICS
    ]:
        raise ValueError(
            "Features possui "
            "price_semantics incompatível."
        )

    if return_semantics != [
        EXPECTED_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "Features possui "
            "return_semantics incompatível."
        )

    if corporate_action_value_semantics != [
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ]:
        raise ValueError(
            "Features possui "
            "corporate_action_value_semantics "
            "incompatível."
        )

    if corporate_action_policy != [
        EXPECTED_FEATURE_CORPORATE_ACTION_POLICY
    ]:
        raise ValueError(
            "Features possui "
            "feature_corporate_action_policy "
            "incompatível."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# ML Eligibility
# ============================================================

def load_ml_eligibility() -> pd.DataFrame:
    """
    Carrega universo supervisionável
    e governança temporal da
    ML Eligibility v3.
    """

    if not ML_ELIGIBILITY_PATH.exists():
        raise FileNotFoundError(
            "FII ML Eligibility não encontrado: "
            f"{ML_ELIGIBILITY_PATH}"
        )

    print(
        "\nCarregando FII ML Eligibility..."
    )

    dataframe = pd.read_parquet(
        ML_ELIGIBILITY_PATH
    )

    required_columns = [
        "ticker",
        "feature_date",
        "target_date",

        "feature_global_session_index",
        "target_global_session_index",

        "target_horizon",
        "target_horizon_semantics",

        "feature_return_window",
        "feature_price_lookback_observations",

        "feature_window_clean",
        "target_horizon_clean",

        "ml_eligible",
        "ml_ineligibility_reason",

        "ml_eligibility_version",

        "source_feature_version",
        "source_price_quality_version",

        "price_semantics",
        "return_semantics",
        "corporate_action_value_semantics",

        "eligibility_policy",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "ML Eligibility possui "
            "schema incompatível: "
            f"{missing_columns}"
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

    return dataframe


def validate_ml_eligibility(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Valida ML Eligibility v3.

    Ela é a fonte oficial do universo
    supervisionável no Training v4.
    """

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "feature_date",
            ]
        ).sum()
    )

    versions = sorted(
        dataframe[
            "ml_eligibility_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    feature_versions = sorted(
        dataframe[
            "source_feature_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_quality_versions = sorted(
        dataframe[
            "source_price_quality_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    horizons = sorted(
        dataframe[
            "target_horizon"
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    horizon_semantics = sorted(
        dataframe[
            "target_horizon_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_semantics = sorted(
        dataframe[
            "price_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return_semantics = sorted(
        dataframe[
            "return_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    corporate_action_value_semantics = sorted(
        dataframe[
            "corporate_action_value_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    eligibility_policies = sorted(
        dataframe[
            "eligibility_policy"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    eligible_count = int(
        dataframe[
            "ml_eligible"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - ML Eligibility"
    )
    print(
        "======================================"
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
        f"ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        "ML ineligible: "
        f"{len(dataframe) - eligible_count:,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Eligibility versions: "
        f"{versions}"
    )

    print(
        f"Feature versions: "
        f"{feature_versions}"
    )

    print(
        "Price Quality versions: "
        f"{price_quality_versions}"
    )

    print(
        f"Target horizons: "
        f"{horizons}"
    )

    print(
        "Target horizon semantics: "
        f"{horizon_semantics}"
    )

    print(
        f"Price semantics: "
        f"{price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{corporate_action_value_semantics}"
    )

    print(
        "Eligibility policies: "
        f"{eligibility_policies}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "ML Eligibility possui "
            "duplicidades."
        )

    if versions != [
        EXPECTED_ELIGIBILITY_VERSION
    ]:
        raise ValueError(
            "Training Dataset v4 exige "
            f"ML Eligibility "
            f"{EXPECTED_ELIGIBILITY_VERSION}."
        )

    if feature_versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "Eligibility não referencia "
            f"Features {EXPECTED_FEATURE_VERSION}."
        )

    if price_quality_versions != [
        EXPECTED_PRICE_QUALITY_VERSION
    ]:
        raise ValueError(
            "Eligibility não referencia "
            "Price Quality "
            f"{EXPECTED_PRICE_QUALITY_VERSION}."
        )

    if horizons != [
        target_horizon
    ]:
        raise ValueError(
            "Eligibility possui horizonte "
            "diferente do solicitado: "
            f"{horizons}"
        )

    if horizon_semantics != [
        TARGET_HORIZON_SEMANTICS
    ]:
        raise ValueError(
            "Eligibility possui semântica "
            "de horizonte incompatível."
        )

    if price_semantics != [
        EXPECTED_PRICE_SEMANTICS
    ]:
        raise ValueError(
            "Eligibility possui "
            "price_semantics incompatível."
        )

    if return_semantics != [
        EXPECTED_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "Eligibility possui "
            "return_semantics incompatível."
        )

    if corporate_action_value_semantics != [
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ]:
        raise ValueError(
            "Eligibility possui "
            "corporate_action_value_semantics "
            "incompatível."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Price History
# ============================================================

def load_price_history() -> pd.DataFrame:
    """
    Carrega Price History v3.

    O histórico fornece:

    - calendário global observado
    - preço ajustado no target
    - daily_return_economic
    - curva acumulada de retorno econômico
    - contrato econômico de Corporate Actions
    """

    if not PRICE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "FII Price History não encontrado: "
            f"{PRICE_HISTORY_PATH}"
        )

    print(
        "\nCarregando FII Price History..."
    )

    dataframe = pd.read_parquet(
        PRICE_HISTORY_PATH,
        columns=[
            "trade_date",
            "ticker",

            "close_price",
            "close_price_raw",
            "close_price_adjusted",

            "daily_return_raw",
            "daily_return_adjusted_price",
            "daily_return_economic",

            "cash_amount_per_unit_adjusted",
            "in_kind_amount_per_unit_adjusted",
            "corporate_action_value_per_unit_adjusted",

            "price_history_version",
            "price_history_source",

            "price_semantics",
            "return_semantics",
            "corporate_action_value_semantics",
        ],
    )

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
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

    return dataframe


def validate_price_history(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida Price History v3 e
    sua semântica econômica.
    """

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    versions = sorted(
        dataframe[
            "price_history_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    sources = sorted(
        dataframe[
            "price_history_source"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_semantics = sorted(
        dataframe[
            "price_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return_semantics = sorted(
        dataframe[
            "return_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    corporate_action_value_semantics = sorted(
        dataframe[
            "corporate_action_value_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    invalid_close_prices = int(
        (
            dataframe[
                "close_price"
            ]
            <= 0
        ).sum()
    )

    non_finite_economic_returns = int(
        (
            dataframe[
                "daily_return_economic"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "daily_return_economic"
                ]
            )
        ).sum()
    )

    invalid_economic_return_floor = int(
        (
            dataframe[
                "daily_return_economic"
            ].notna()
            &
            (
                dataframe[
                    "daily_return_economic"
                ]
                <= -1.0
            )
        ).sum()
    )

    close_alias_mismatch = int(
        (
            ~np.isclose(
                dataframe[
                    "close_price"
                ],
                dataframe[
                    "close_price_adjusted"
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    negative_cash = int(
        (
            dataframe[
                "cash_amount_per_unit_adjusted"
            ]
            < 0
        ).sum()
    )

    negative_in_kind = int(
        (
            dataframe[
                "in_kind_amount_per_unit_adjusted"
            ]
            < 0
        ).sum()
    )

    negative_total_value = int(
        (
            dataframe[
                "corporate_action_value_per_unit_adjusted"
            ]
            < 0
        ).sum()
    )

    economic_component_mismatch = int(
        (
            ~np.isclose(
                (
                    dataframe[
                        "cash_amount_per_unit_adjusted"
                    ]
                    +
                    dataframe[
                        "in_kind_amount_per_unit_adjusted"
                    ]
                ),
                dataframe[
                    "corporate_action_value_per_unit_adjusted"
                ],
                rtol=1e-8,
                atol=1e-8,
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Price History"
    )
    print(
        "======================================"
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
        f"Pregões: "
        f"{dataframe['trade_date'].nunique():,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Histórico versions: "
        f"{versions}"
    )

    print(
        f"Histórico sources: "
        f"{sources}"
    )

    print(
        f"Price semantics: "
        f"{price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{corporate_action_value_semantics}"
    )

    print(
        f"close_price inválidos: "
        f"{invalid_close_prices:,}"
    )

    print(
        "daily_return_economic "
        "não finitos: "
        f"{non_finite_economic_returns:,}"
    )

    print(
        "daily_return_economic <= -100%: "
        f"{invalid_economic_return_floor:,}"
    )

    print(
        "close_price != "
        "close_price_adjusted: "
        f"{close_alias_mismatch:,}"
    )

    print(
        f"Cash ajustado negativo: "
        f"{negative_cash:,}"
    )

    print(
        f"In-kind ajustado negativo: "
        f"{negative_in_kind:,}"
    )

    print(
        "Valor econômico ajustado negativo: "
        f"{negative_total_value:,}"
    )

    print(
        "Mismatch cash + in-kind != total: "
        f"{economic_component_mismatch:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price History possui "
            "duplicidades."
        )

    if versions != [
        EXPECTED_PRICE_HISTORY_VERSION
    ]:
        raise ValueError(
            "Training Dataset v4 exige "
            "Price History v3."
        )

    if sources != [
        EXPECTED_PRICE_HISTORY_SOURCE
    ]:
        raise ValueError(
            "Price History possui "
            "source incompatível: "
            f"{sources}"
        )

    if price_semantics != [
        EXPECTED_PRICE_SEMANTICS
    ]:
        raise ValueError(
            "Price History possui "
            "price_semantics incompatível."
        )

    if return_semantics != [
        EXPECTED_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "Price History possui "
            "return_semantics incompatível."
        )

    if corporate_action_value_semantics != [
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ]:
        raise ValueError(
            "Price History possui "
            "corporate_action_value_semantics "
            "incompatível."
        )

    if invalid_close_prices > 0:
        raise ValueError(
            "Price History possui "
            "close_price inválido."
        )

    if non_finite_economic_returns > 0:
        raise ValueError(
            "Price History possui "
            "daily_return_economic "
            "não finito."
        )

    if invalid_economic_return_floor > 0:
        raise ValueError(
            "Price History possui retorno "
            "econômico <= -100%, incompatível "
            "com composição geométrica."
        )

    if close_alias_mismatch > 0:
        raise ValueError(
            "close_price não representa "
            "close_price_adjusted."
        )

    if negative_cash > 0:
        raise ValueError(
            "Price History possui "
            "cash ajustado negativo."
        )

    if negative_in_kind > 0:
        raise ValueError(
            "Price History possui "
            "in-kind ajustado negativo."
        )

    if negative_total_value > 0:
        raise ValueError(
            "Price History possui "
            "valor econômico ajustado negativo."
        )

    if economic_component_mismatch > 0:
        raise ValueError(
            "Price History possui "
            "cash + in-kind diferente "
            "do valor econômico total."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Global calendar
# ============================================================

def build_global_calendar(
    price_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calendário global observado na
    Price History.
    """

    calendar = (
        price_history[
            [
                "trade_date",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "trade_date"
        )
        .reset_index(
            drop=True
        )
    )

    calendar[
        "global_session_index"
    ] = np.arange(
        len(calendar),
        dtype=np.int64,
    )

    if calendar.empty:
        raise ValueError(
            "Calendário global B3 vazio."
        )

    return calendar


def validate_eligibility_calendar(
    eligibility: pd.DataFrame,
    calendar: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Revalida independentemente:

        feature_date
        ->
        target_date

    como exatamente T+N no calendário
    global B3 observado.

    O Training Dataset não aceita
    silenciosamente target_date incorreto.
    """

    feature_calendar = calendar.rename(
        columns={
            "trade_date": (
                "feature_date"
            ),
            "global_session_index": (
                "expected_feature_session_index"
            ),
        }
    )

    target_calendar = calendar.rename(
        columns={
            "trade_date": (
                "target_date"
            ),
            "global_session_index": (
                "expected_target_session_index"
            ),
        }
    )

    check = eligibility.merge(
        feature_calendar,
        how="left",
        on="feature_date",
        validate="many_to_one",
    )

    check = check.merge(
        target_calendar,
        how="left",
        on="target_date",
        validate="many_to_one",
    )

    missing_calendar_dates = int(
        check[
            [
                "expected_feature_session_index",
                "expected_target_session_index",
            ]
        ]
        .isna()
        .sum()
        .sum()
    )

    if missing_calendar_dates > 0:
        raise ValueError(
            "Eligibility possui data "
            "fora do calendário Price History."
        )

    expected_difference = (
        check[
            "expected_target_session_index"
        ]
        - check[
            "expected_feature_session_index"
        ]
    )

    invalid_horizon = int(
        (
            expected_difference
            != target_horizon
        ).sum()
    )

    stored_feature_index_mismatch = int(
        (
            check[
                "feature_global_session_index"
            ]
            != check[
                "expected_feature_session_index"
            ]
        ).sum()
    )

    stored_target_index_mismatch = int(
        (
            check[
                "target_global_session_index"
            ]
            != check[
                "expected_target_session_index"
            ]
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Validação - Calendário Global B3"
    )
    print(
        "======================================"
    )

    print(
        "Samples: "
        f"{len(check):,}"
    )

    print(
        "Datas fora do calendário: "
        f"{missing_calendar_dates:,}"
    )

    print(
        f"Horizontes diferentes de T+"
        f"{target_horizon}: "
        f"{invalid_horizon:,}"
    )

    print(
        "Feature session index divergente: "
        f"{stored_feature_index_mismatch:,}"
    )

    print(
        "Target session index divergente: "
        f"{stored_target_index_mismatch:,}"
    )

    if invalid_horizon > 0:
        raise ValueError(
            "Eligibility não respeita "
            "integralmente T+5 global B3."
        )

    if stored_feature_index_mismatch > 0:
        raise ValueError(
            "feature_global_session_index "
            "diverge do Price History."
        )

    if stored_target_index_mismatch > 0:
        raise ValueError(
            "target_global_session_index "
            "diverge do Price History."
        )

    print(
        "\nCalendário global aprovado."
    )


# ============================================================
# Economic return curve
# ============================================================

def build_economic_return_curve(
    price_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói curva acumulada de retorno
    econômico por ticker.

    Para cada observação:

        growth_factor_t
            =
        1 + daily_return_economic_t

    e:

        cumulative_log_growth_t
            =
        soma log(growth_factor)

    Portanto o retorno entre:

        feature_date = T
        target_date  = U

    é:

        exp(
            cumulative_log_growth_U
            -
            cumulative_log_growth_T
        ) - 1

    Semântica temporal:

        (T, U]

    O retorno existente em T é excluído.
    Os retornos posteriores até U são
    incluídos.

    daily_return_economic já incorpora
    corretamente:

        - ajuste estrutural
        - cash
        - in-kind
        - valor econômico total
    """

    history = price_history.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    #
    # Primeira observação possui
    # NULL estrutural esperado.
    #

    history[
        "economic_return_component"
    ] = (
        history[
            "daily_return_economic"
        ]
        .fillna(
            0.0
        )
    )

    history[
        "economic_growth_factor"
    ] = (
        1.0
        + history[
            "economic_return_component"
        ]
    )

    invalid_growth_factor = int(
        (
            history[
                "economic_growth_factor"
            ]
            <= 0
        ).sum()
    )

    if invalid_growth_factor > 0:
        raise ValueError(
            "Retorno econômico produziu "
            "growth factor <= 0."
        )

    history[
        "economic_log_growth"
    ] = np.log(
        history[
            "economic_growth_factor"
        ]
    )

    history[
        "cumulative_economic_log_growth"
    ] = (
        history
        .groupby(
            "ticker",
            sort=False,
        )[
            "economic_log_growth"
        ]
        .cumsum()
    )

    non_finite_curve = int(
        (
            ~np.isfinite(
                history[
                    "cumulative_economic_log_growth"
                ]
            )
        ).sum()
    )

    if non_finite_curve > 0:
        raise ValueError(
            "Curva acumulada econômica "
            "possui valor não finito."
        )

    return history


# ============================================================
# Training universe
# ============================================================

def build_training_base(
    features: pd.DataFrame,
    eligibility: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói base supervisionável usando
    exatamente o universo da
    ML Eligibility v3.

    IMPORTANTE:

    ml_eligible NÃO remove fisicamente
    samples nesta camada.

    Training Dataset preserva:

        eligible
        +
        ineligible

    para permitir auditoria e aplicação
    governada posterior pelo Split /
    treinamento.
    """

    ready_features = features[
        features[
            "feature_ready"
        ]
        .fillna(False)
        .astype(bool)
    ].copy()

    eligibility_columns = [
        "ticker",
        "feature_date",
        "target_date",

        "feature_global_session_index",
        "target_global_session_index",

        "target_horizon",
        "target_horizon_semantics",

        "feature_return_window",
        "feature_price_lookback_observations",

        "blocking_feature_lookback_count",
        "blocking_target_horizon_count",

        "feature_window_clean",
        "target_horizon_clean",

        "ml_eligible",
        "ml_ineligibility_reason",

        "ml_eligibility_version",

        "source_feature_version",
        "source_price_quality_version",

        "eligibility_policy",

        "corporate_action_value_semantics",
    ]

    eligibility_base = eligibility[
        eligibility_columns
    ].copy()

    dataframe = eligibility_base.merge(
        ready_features,
        how="left",
        on=[
            "ticker",
            "feature_date",
        ],
        validate="one_to_one",
        suffixes=(
            "_eligibility",
            "",
        ),
    )

    missing_feature_rows = int(
        dataframe[
            "feature_ready"
        ]
        .isna()
        .sum()
    )

    if missing_feature_rows > 0:
        raise ValueError(
            "Existem samples da Eligibility "
            "sem Features v7 correspondentes."
        )

    invalid_ready = int(
        (
            ~dataframe[
                "feature_ready"
            ]
            .fillna(False)
            .astype(bool)
        ).sum()
    )

    if invalid_ready > 0:
        raise ValueError(
            "Eligibility contém sample "
            "com feature_ready=False."
        )

    return dataframe


# ============================================================
# Feature economic curve
# ============================================================

def attach_feature_economic_curve(
    dataframe: pd.DataFrame,
    economic_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Anexa o ponto acumulado econômico
    exatamente na feature_date.
    """

    lookup = economic_history[
        [
            "ticker",
            "trade_date",
            "cumulative_economic_log_growth",
        ]
    ].rename(
        columns={
            "trade_date": (
                "feature_date"
            ),
            "cumulative_economic_log_growth": (
                "economic_curve_at_feature"
            ),
        }
    )

    result = dataframe.merge(
        lookup,
        how="left",
        on=[
            "ticker",
            "feature_date",
        ],
        validate="one_to_one",
    )

    missing = int(
        result[
            "economic_curve_at_feature"
        ]
        .isna()
        .sum()
    )

    if missing > 0:
        raise ValueError(
            "Samples sem curva econômica "
            "na feature_date."
        )

    return result


# ============================================================
# Target economic curve
# ============================================================

def attach_target_economic_curve(
    dataframe: pd.DataFrame,
    economic_history: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Anexa preço e curva econômica
    exatamente na target_date.
    """

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    lookup = economic_history[
        [
            "ticker",
            "trade_date",

            "close_price",
            "close_price_raw",

            "cumulative_economic_log_growth",
        ]
    ].rename(
        columns={
            "trade_date": (
                "target_date"
            ),
            "close_price": (
                target_price_column
            ),
            "close_price_raw": (
                "target_price_raw"
            ),
            "cumulative_economic_log_growth": (
                "economic_curve_at_target"
            ),
        }
    )

    result = dataframe.merge(
        lookup,
        how="left",
        on=[
            "ticker",
            "target_date",
        ],
        validate="one_to_one",
    )

    required_target_columns = [
        target_price_column,
        "target_price_raw",
        "economic_curve_at_target",
    ]

    missing = int(
        result[
            required_target_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    if missing > 0:
        raise ValueError(
            "Samples sem preço/curva econômica "
            "na target_date."
        )

    return result


# ============================================================
# Target calculation
# ============================================================

def calculate_targets(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Calcula target oficial econômico.

    target_return_next_Nd:

        produto(
            1 + daily_return_economic
        )

    para observações em:

        (feature_date, target_date]

    O target é portanto temporalmente
    posterior às features.

    A razão simples de preços permanece
    apenas como diagnóstico.
    """

    result = dataframe.copy()

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    target_price_return_column = (
        f"target_price_return_next_"
        f"{target_horizon}d"
    )

    target_price_return_pct_column = (
        f"{target_price_return_column}_pct"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"{target_return_column}_pct"
    )

    #
    # --------------------------------------------------------
    # Price-only diagnostic
    # --------------------------------------------------------
    #

    result[
        target_price_return_column
    ] = (
        result[
            target_price_column
        ]
        / result[
            "close_price"
        ]
        - 1.0
    )

    result[
        target_price_return_pct_column
    ] = (
        result[
            target_price_return_column
        ]
        * 100
    )

    #
    # --------------------------------------------------------
    # Official economic target
    # --------------------------------------------------------
    #

    economic_log_return = (
        result[
            "economic_curve_at_target"
        ]
        - result[
            "economic_curve_at_feature"
        ]
    )

    result[
        target_return_column
    ] = (
        np.exp(
            economic_log_return
        )
        - 1.0
    )

    result[
        target_return_pct_column
    ] = (
        result[
            target_return_column
        ]
        * 100
    )

    #
    # --------------------------------------------------------
    # Economic vs price-only audit
    # --------------------------------------------------------
    #

    result[
        "target_economic_vs_price_difference"
    ] = (
        result[
            target_return_column
        ]
        - result[
            target_price_return_column
        ]
    )

    result[
        "target_economic_vs_price_difference_pct"
    ] = (
        result[
            "target_economic_vs_price_difference"
        ]
        * 100
    )

    result[
        "target_name"
    ] = target_return_column

    result[
        "target_return_semantics"
    ] = (
        TARGET_RETURN_SEMANTICS
    )

    return result


# ============================================================
# Metadata
# ============================================================

def add_metadata(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Persiste linhagem técnica e
    semântica do Training Dataset v4.
    """

    result = dataframe.copy()

    result[
        "target_horizon"
    ] = target_horizon

    result[
        "target_horizon_semantics"
    ] = (
        TARGET_HORIZON_SEMANTICS
    )

    result[
        "training_dataset_version"
    ] = (
        TRAINING_DATASET_VERSION
    )

    result[
        "source_feature_version"
    ] = (
        EXPECTED_FEATURE_VERSION
    )

    result[
        "source_ml_eligibility_version"
    ] = (
        EXPECTED_ELIGIBILITY_VERSION
    )

    result[
        "source_price_quality_version"
    ] = (
        EXPECTED_PRICE_QUALITY_VERSION
    )

    result[
        "source_price_history_version"
    ] = (
        EXPECTED_PRICE_HISTORY_VERSION
    )

    result[
        "source_price_history_source"
    ] = (
        EXPECTED_PRICE_HISTORY_SOURCE
    )

    result[
        "price_semantics"
    ] = (
        EXPECTED_PRICE_SEMANTICS
    )

    result[
        "return_semantics"
    ] = (
        EXPECTED_RETURN_SEMANTICS
    )

    result[
        "corporate_action_value_semantics"
    ] = (
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    )

    result[
        "training_sample_policy"
    ] = (
        "PRESERVE_ALL_SUPERVISABLE_SAMPLES_"
        "ML_ELIGIBLE_FILTER_DOWNSTREAM"
    )

    result[
        "training_dataset_created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


# ============================================================
# Training Dataset validation
# ============================================================

def validate_training_dataset(
    dataframe: pd.DataFrame,
    calendar: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Valida contrato e semântica do
    Training Dataset v4.
    """

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    target_price_return_column = (
        f"target_price_return_next_"
        f"{target_horizon}d"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"{target_return_column}_pct"
    )

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price",

        "target_date",

        target_price_column,
        target_price_return_column,

        target_return_column,
        target_return_pct_column,

        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",

        "target_name",

        "feature_ready",

        "ml_eligible",
        "ml_ineligibility_reason",

        "training_dataset_version",

        "source_feature_version",
        "source_ml_eligibility_version",
        "source_price_quality_version",
        "source_price_history_version",
        "source_price_history_source",

        "price_semantics",
        "return_semantics",
        "corporate_action_value_semantics",

        "training_sample_policy",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Training Dataset possui "
            "colunas ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    required_null_count = int(
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    invalid_target_prices = int(
        (
            dataframe[
                target_price_column
            ]
            <= 0
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

    non_finite_targets = int(
        (
            ~np.isfinite(
                dataframe[
                    target_return_column
                ]
            )
        ).sum()
    )

    non_finite_price_targets = int(
        (
            ~np.isfinite(
                dataframe[
                    target_price_return_column
                ]
            )
        ).sum()
    )

    target_below_floor = int(
        (
            dataframe[
                target_return_column
            ]
            <= -1.0
        ).sum()
    )

    eligible_count = int(
        dataframe[
            "ml_eligible"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    ineligible_count = (
        len(dataframe)
        - eligible_count
    )

    #
    # --------------------------------------------------------
    # Independent global B3 horizon validation
    # --------------------------------------------------------
    #

    feature_calendar = calendar.rename(
        columns={
            "trade_date": (
                "feature_date"
            ),
            "global_session_index": (
                "expected_feature_index"
            ),
        }
    )

    target_calendar = calendar.rename(
        columns={
            "trade_date": (
                "target_date"
            ),
            "global_session_index": (
                "expected_target_index"
            ),
        }
    )

    calendar_check = dataframe[
        [
            "ticker",
            "feature_date",
            "target_date",
        ]
    ].merge(
        feature_calendar,
        how="left",
        on="feature_date",
        validate="many_to_one",
    )

    calendar_check = calendar_check.merge(
        target_calendar,
        how="left",
        on="target_date",
        validate="many_to_one",
    )

    missing_calendar_dates = int(
        calendar_check[
            [
                "expected_feature_index",
                "expected_target_index",
            ]
        ]
        .isna()
        .sum()
        .sum()
    )

    exact_horizon = (
        calendar_check[
            "expected_target_index"
        ]
        - calendar_check[
            "expected_feature_index"
        ]
    )

    invalid_global_horizon = int(
        (
            exact_horizon
            != target_horizon
        ).sum()
    )

    #
    # --------------------------------------------------------
    # Semantic metadata
    # --------------------------------------------------------
    #

    versions = sorted(
        dataframe[
            "training_dataset_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    feature_versions = sorted(
        dataframe[
            "source_feature_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    eligibility_versions = sorted(
        dataframe[
            "source_ml_eligibility_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_quality_versions = sorted(
        dataframe[
            "source_price_quality_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_history_versions = sorted(
        dataframe[
            "source_price_history_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    target_semantics = sorted(
        dataframe[
            "target_return_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    corporate_action_value_semantics = sorted(
        dataframe[
            "corporate_action_value_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Training Dataset v4"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas supervisionadas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
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
        f"ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"ML ineligible: "
        f"{ineligible_count:,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Nulos obrigatórios: "
        f"{required_null_count:,}"
    )

    print(
        f"Datas fora do calendário: "
        f"{missing_calendar_dates:,}"
    )

    print(
        f"Target prices inválidos: "
        f"{invalid_target_prices:,}"
    )

    print(
        "Targets com data <= feature_date: "
        f"{invalid_target_dates:,}"
    )

    print(
        "Targets econômicos não finitos: "
        f"{non_finite_targets:,}"
    )

    print(
        "Targets price-only não finitos: "
        f"{non_finite_price_targets:,}"
    )

    print(
        "Targets econômicos <= -100%: "
        f"{target_below_floor:,}"
    )

    print(
        "Horizontes diferentes de "
        f"T+{target_horizon}: "
        f"{invalid_global_horizon:,}"
    )

    print(
        f"Dataset versions: "
        f"{versions}"
    )

    print(
        f"Feature versions: "
        f"{feature_versions}"
    )

    print(
        "Eligibility versions: "
        f"{eligibility_versions}"
    )

    print(
        "Price Quality versions: "
        f"{price_quality_versions}"
    )

    print(
        "Price History versions: "
        f"{price_history_versions}"
    )

    print(
        "Target return semantics: "
        f"{target_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{corporate_action_value_semantics}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Training Dataset possui "
            "duplicidades."
        )

    if required_null_count > 0:
        raise ValueError(
            "Training Dataset possui "
            "campos obrigatórios nulos."
        )

    if missing_calendar_dates > 0:
        raise ValueError(
            "Training Dataset possui "
            "datas fora do calendário global."
        )

    if invalid_target_prices > 0:
        raise ValueError(
            "Training Dataset possui "
            "target_price inválido."
        )

    if invalid_target_dates > 0:
        raise ValueError(
            "Training Dataset possui "
            "target_date inválida."
        )

    if non_finite_targets > 0:
        raise ValueError(
            "Training Dataset possui "
            "target econômico não finito."
        )

    if non_finite_price_targets > 0:
        raise ValueError(
            "Training Dataset possui "
            "target price-only não finito."
        )

    if target_below_floor > 0:
        raise ValueError(
            "Training Dataset possui "
            "target econômico <= -100%."
        )

    if invalid_global_horizon > 0:
        raise ValueError(
            "Training Dataset não respeita "
            "integralmente T+5 global B3."
        )

    if versions != [
        TRAINING_DATASET_VERSION
    ]:
        raise ValueError(
            "training_dataset_version "
            "inconsistente."
        )

    if feature_versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "source_feature_version "
            "inconsistente."
        )

    if eligibility_versions != [
        EXPECTED_ELIGIBILITY_VERSION
    ]:
        raise ValueError(
            "source_ml_eligibility_version "
            "inconsistente."
        )

    if price_quality_versions != [
        EXPECTED_PRICE_QUALITY_VERSION
    ]:
        raise ValueError(
            "source_price_quality_version "
            "inconsistente."
        )

    if price_history_versions != [
        EXPECTED_PRICE_HISTORY_VERSION
    ]:
        raise ValueError(
            "source_price_history_version "
            "inconsistente."
        )

    if target_semantics != [
        TARGET_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "target_return_semantics "
            "inconsistente."
        )

    if corporate_action_value_semantics != [
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ]:
        raise ValueError(
            "corporate_action_value_semantics "
            "inconsistente."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Economic target diagnostics
# ============================================================

def print_economic_target_diagnostics(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Mostra quando target econômico e
    simples razão de preços diferem.

    Diferenças podem ocorrer quando
    Corporate Actions econômicos entram
    em (feature_date, target_date].
    """

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_price_return_column = (
        f"target_price_return_next_"
        f"{target_horizon}d"
    )

    difference_column = (
        "target_economic_vs_price_difference"
    )

    absolute_difference = (
        dataframe[
            difference_column
        ].abs()
    )

    different_count = int(
        (
            absolute_difference
            > 1e-10
        ).sum()
    )

    materially_different_count = int(
        (
            absolute_difference
            > 0.001
        ).sum()
    )

    eligible_difference_count = int(
        (
            dataframe[
                "ml_eligible"
            ]
            .fillna(False)
            .astype(bool)
            &
            (
                absolute_difference
                > 1e-10
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico - Economic vs Price Target"
    )
    print(
        "======================================"
    )

    print(
        "Samples com qualquer diferença: "
        f"{different_count:,}"
    )

    print(
        "Samples com diferença > 0,10 p.p.: "
        f"{materially_different_count:,}"
    )

    print(
        "Samples ML eligible com diferença: "
        f"{eligible_difference_count:,}"
    )

    if different_count == 0:
        print(
            "\nNenhuma diferença encontrada."
        )

        return

    display = dataframe[
        absolute_difference
        > 1e-10
    ][
        [
            "ticker",
            "feature_date",
            "target_date",

            "close_price",

            f"target_price_next_"
            f"{target_horizon}d",

            target_price_return_column,
            target_return_column,

            difference_column,

            "ml_eligible",
        ]
    ].copy()

    display = display.sort_values(
        difference_column,
        key=lambda series: (
            series.abs()
        ),
        ascending=False,
    )

    print(
        "\nMaiores diferenças:"
    )

    print(
        display.head(
            30
        ).to_string(
            index=False
        )
    )


# ============================================================
# Summary
# ============================================================

def print_summary(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Resumo final.
    """

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    eligible = dataframe[
        dataframe[
            "ml_eligible"
        ]
        .fillna(False)
        .astype(bool)
    ].copy()

    positive_count = int(
        (
            dataframe[
                target_return_column
            ]
            > 0
        ).sum()
    )

    non_positive_count = (
        len(dataframe)
        - positive_count
    )

    eligible_positive_count = int(
        (
            eligible[
                target_return_column
            ]
            > 0
        ).sum()
    )

    eligible_non_positive_count = (
        len(eligible)
        - eligible_positive_count
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo FII Training Dataset"
    )
    print(
        "======================================"
    )

    print(
        f"Dataset version: "
        f"{TRAINING_DATASET_VERSION}"
    )

    print(
        "Source Features: "
        f"{EXPECTED_FEATURE_VERSION}"
    )

    print(
        "Source Eligibility: "
        f"{EXPECTED_ELIGIBILITY_VERSION}"
    )

    print(
        "Source Price Quality: "
        f"{EXPECTED_PRICE_QUALITY_VERSION}"
    )

    print(
        "Source Price History: "
        f"{EXPECTED_PRICE_HISTORY_VERSION}"
    )

    print(
        "Target horizon: "
        f"{target_horizon} "
        "pregões B3 globais"
    )

    print(
        "Target horizon semantics: "
        f"{TARGET_HORIZON_SEMANTICS}"
    )

    print(
        "Target return semantics: "
        f"{TARGET_RETURN_SEMANTICS}"
    )

    print(
        "Corporate Action value semantics: "
        f"{EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS}"
    )

    print(
        "Target: "
        f"{target_return_column}"
    )

    print(
        f"\nLinhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
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
        "\nTodas as samples:"
    )

    print(
        "  Target médio: "
        f"{dataframe[target_return_column].mean() * 100:.4f}%"
    )

    print(
        "  Target mediano: "
        f"{dataframe[target_return_column].median() * 100:.4f}%"
    )

    print(
        "  Targets positivos: "
        f"{positive_count:,}"
    )

    print(
        "  Targets <= 0: "
        f"{non_positive_count:,}"
    )

    print(
        "\nSamples ML eligible:"
    )

    print(
        f"  Linhas: "
        f"{len(eligible):,}"
    )

    print(
        "  Target médio: "
        f"{eligible[target_return_column].mean() * 100:.4f}%"
    )

    print(
        "  Target mediano: "
        f"{eligible[target_return_column].median() * 100:.4f}%"
    )

    print(
        "  Targets positivos: "
        f"{eligible_positive_count:,}"
    )

    print(
        "  Targets <= 0: "
        f"{eligible_non_positive_count:,}"
    )

    print(
        "\nArquivo:"
    )

    print(
        OUTPUT_PATH
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Constrói FII Training Dataset v4 "
            "com target econômico e horizonte "
            "global B3."
        )
    )

    parser.add_argument(
        "--target-horizon",
        type=int,
        default=DEFAULT_TARGET_HORIZON,
        help=(
            "Horizonte futuro em pregões "
            "globais B3. "
            "A ML Eligibility v3 atual foi "
            "construída para 5."
        ),
    )

    args = parser.parse_args()

    target_horizon = (
        args.target_horizon
    )

    if target_horizon <= 0:
        raise ValueError(
            "--target-horizon deve ser "
            "maior que zero."
        )

    print(
        "Construindo FII Training Dataset..."
    )

    print(
        f"Version: "
        f"{TRAINING_DATASET_VERSION}"
    )

    print(
        "Source Features: "
        f"{EXPECTED_FEATURE_VERSION}"
    )

    print(
        "Source Eligibility: "
        f"{EXPECTED_ELIGIBILITY_VERSION}"
    )

    print(
        "Source Price History: "
        f"{EXPECTED_PRICE_HISTORY_VERSION}"
    )

    print(
        "Target horizon: "
        f"{target_horizon} "
        "pregões B3 globais"
    )

    print(
        "Target return semantics: "
        f"{TARGET_RETURN_SEMANTICS}"
    )

    features = load_features()

    validate_features(
        features
    )

    eligibility = (
        load_ml_eligibility()
    )

    validate_ml_eligibility(
        dataframe=eligibility,
        target_horizon=target_horizon,
    )

    price_history = (
        load_price_history()
    )

    validate_price_history(
        price_history
    )

    calendar = build_global_calendar(
        price_history
    )

    print(
        "\nCalendário global B3: "
        f"{len(calendar):,} pregões"
    )

    validate_eligibility_calendar(
        eligibility=eligibility,
        calendar=calendar,
        target_horizon=target_horizon,
    )

    economic_history = (
        build_economic_return_curve(
            price_history
        )
    )

    training_dataset = (
        build_training_base(
            features=features,
            eligibility=eligibility,
        )
    )

    training_dataset = (
        attach_feature_economic_curve(
            dataframe=training_dataset,
            economic_history=economic_history,
        )
    )

    training_dataset = (
        attach_target_economic_curve(
            dataframe=training_dataset,
            economic_history=economic_history,
            target_horizon=target_horizon,
        )
    )

    training_dataset = (
        calculate_targets(
            dataframe=training_dataset,
            target_horizon=target_horizon,
        )
    )

    training_dataset = add_metadata(
        dataframe=training_dataset,
        target_horizon=target_horizon,
    )

    validate_training_dataset(
        dataframe=training_dataset,
        calendar=calendar,
        target_horizon=target_horizon,
    )

    print_economic_target_diagnostics(
        dataframe=training_dataset,
        target_horizon=target_horizon,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    training_dataset.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print_summary(
        dataframe=training_dataset,
        target_horizon=target_horizon,
    )

    print(
        "\nFII Training Dataset "
        f"{TRAINING_DATASET_VERSION} "
        "criado com sucesso."
    )

    print(
        "O universo supervisionável vem "
        "da ML Eligibility v3."
    )

    print(
        "Nenhuma sample foi removida "
        "automaticamente por ml_eligible."
    )

    print(
        "O target oficial usa composição "
        "de daily_return_economic em "
        "(feature_date, target_date]."
    )

    print(
        "O target permanece exatamente "
        "T+5 sessões globais B3."
    )

    print(
        "target_price_return permanece "
        "somente para auditoria."
    )

    print(
        "Corporate Actions confirmados "
        "já estão incorporados "
        "economicamente nos retornos."
    )

    print(
        "Cash e in-kind permanecem "
        "semanticamente separados upstream."
    )

    print(
        "O Training Dataset não utiliza "
        "payload futuro de Corporate Action "
        "como feature."
    )


if __name__ == "__main__":
    main()