from __future__ import annotations

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

PRICE_QUALITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "quality"
    / "fii_price_quality"
    / "fii_price_quality.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_ml_eligibility"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_ml_eligibility.parquet"
)


# ============================================================
# Version / source contracts
# ============================================================

ML_ELIGIBILITY_VERSION = "v3"

EXPECTED_FEATURE_VERSION = "v7"

EXPECTED_PRICE_QUALITY_VERSION = "v2"

EXPECTED_PRICE_QUALITY_SOURCE = (
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
# Target contract
# ============================================================

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)


# ============================================================
# Feature lookback contract
# ============================================================

#
# A maior feature atualmente é return_20d.
#
# 20 retornos:
#
# T-19 -> T-18
# ...
# T-1  -> T
#
# exigem 21 preços:
#
# T-20 ... T
#
MAX_FEATURE_RETURN_WINDOW = 20

FEATURE_PRICE_LOOKBACK_OBSERVATIONS = (
    MAX_FEATURE_RETURN_WINDOW + 1
)


# ============================================================
# Features loading
# ============================================================

def load_features() -> pd.DataFrame:
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


# ============================================================
# Features validation
# ============================================================

def validate_features(
    dataframe: pd.DataFrame,
) -> None:
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
            "ML Eligibility v3 exige "
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
# Price Quality loading
# ============================================================

def load_price_quality() -> pd.DataFrame:
    if not PRICE_QUALITY_PATH.exists():
        raise FileNotFoundError(
            "FII Price Quality não encontrado: "
            f"{PRICE_QUALITY_PATH}"
        )

    print(
        "\nCarregando FII Price Quality..."
    )

    dataframe = pd.read_parquet(
        PRICE_QUALITY_PATH
    )

    required_columns = [
        "ticker",
        "trade_date",

        "ml_quality_status",

        "review_status_on_date",

        "flag_extreme_return",
        "flag_long_gap",
        "flag_possible_microliquidity",

        "flag_confirmed_corporate_action",
        "flag_confirmed_economic_corporate_action",
        "flag_in_kind_corporate_action",
        "flag_pending_corporate_action",

        "price_quality_version",
        "price_quality_source",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price Quality possui "
            "schema incompatível: "
            f"{missing_columns}"
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


# ============================================================
# Price Quality validation
# ============================================================

def validate_price_quality(
    dataframe: pd.DataFrame,
) -> None:
    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    invalid_statuses = sorted(
        set(
            dataframe[
                "ml_quality_status"
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        - {
            "PASS",
            "REVIEW",
        }
    )

    versions = sorted(
        dataframe[
            "price_quality_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    sources = sorted(
        dataframe[
            "price_quality_source"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    pending_count = int(
        dataframe[
            "flag_pending_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    confirmed_count = int(
        dataframe[
            "flag_confirmed_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    confirmed_economic_count = int(
        dataframe[
            "flag_confirmed_economic_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    in_kind_count = int(
        dataframe[
            "flag_in_kind_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    review_count = int(
        dataframe[
            "ml_quality_status"
        ]
        .eq(
            "REVIEW"
        )
        .sum()
    )

    extreme_count = int(
        dataframe[
            "flag_extreme_return"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Price Quality"
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
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Price Quality versions: "
        f"{versions}"
    )

    print(
        "Price Quality sources: "
        f"{sources}"
    )

    print(
        "Status inválidos: "
        f"{len(invalid_statuses):,}"
    )

    print(
        f"REVIEW: "
        f"{review_count:,}"
    )

    print(
        f"EXTREME_RETURN: "
        f"{extreme_count:,}"
    )

    print(
        "Corporate Actions pendentes: "
        f"{pending_count:,}"
    )

    print(
        "Corporate Actions confirmados: "
        f"{confirmed_count:,}"
    )

    print(
        "Corporate Actions econômicos: "
        f"{confirmed_economic_count:,}"
    )

    print(
        "Corporate Actions in-kind: "
        f"{in_kind_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price Quality possui "
            "duplicidades."
        )

    if invalid_statuses:
        raise ValueError(
            "Price Quality possui "
            "ml_quality_status inválido: "
            f"{invalid_statuses}"
        )

    if versions != [
        EXPECTED_PRICE_QUALITY_VERSION
    ]:
        raise ValueError(
            "ML Eligibility v3 exige "
            "Price Quality "
            f"{EXPECTED_PRICE_QUALITY_VERSION}."
        )

    if sources != [
        EXPECTED_PRICE_QUALITY_SOURCE
    ]:
        raise ValueError(
            "Price Quality possui "
            "source incompatível: "
            f"{sources}"
        )

    if pending_count > 0:
        raise ValueError(
            "ML Eligibility v3 não será "
            "construída com Corporate Actions "
            "PENDING_REVIEW."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Global B3 calendar
# ============================================================

def build_global_calendar(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    calendar = (
        price_quality[
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

    return calendar


# ============================================================
# Blocking policy
# ============================================================

def build_blocking_signals(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    """
    Define a política de bloqueio do
    ML Eligibility v3.

    IMPORTANTE:

    Esta versão PRESERVA a política
    anteriormente governada.

    Bloqueantes:
        - Price Quality REVIEW
        - Corporate Action candidate
          investigado e REJECTED

    Informacionais:
        - EXTREME_RETURN isolado
        - Corporate Action CONFIRMED

    Corporate Actions CONFIRMED já estão
    economicamente incorporadas na série
    de preços/retornos e não bloqueiam
    automaticamente o ML.
    """

    result = price_quality.copy()

    #
    # --------------------------------------------------------
    # Price Quality REVIEW
    # --------------------------------------------------------
    #

    result[
        "blocking_price_quality_review"
    ] = (
        result[
            "ml_quality_status"
        ]
        .eq(
            "REVIEW"
        )
    )

    #
    # --------------------------------------------------------
    # REJECTED Corporate Action candidate
    # --------------------------------------------------------
    #
    # REJECTED significa que a observação
    # foi investigada formalmente como
    # possível Corporate Action e não foi
    # confirmada como tal.
    #
    # Mantemos esta observação governada
    # como bloqueante no Eligibility.
    #

    result[
        "blocking_rejected_ca_review"
    ] = (
        result[
            "review_status_on_date"
        ]
        .eq(
            "REJECTED"
        )
    )

    result[
        "blocking_signal"
    ] = (
        result[
            "blocking_price_quality_review"
        ]
        |
        result[
            "blocking_rejected_ca_review"
        ]
    )

    #
    # --------------------------------------------------------
    # Confirmed Corporate Action
    # --------------------------------------------------------
    #

    result[
        "informational_confirmed_ca"
    ] = (
        result[
            "flag_confirmed_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
    )

    #
    # --------------------------------------------------------
    # Confirmed economic Corporate Action
    # --------------------------------------------------------
    #

    result[
        "informational_confirmed_economic_ca"
    ] = (
        result[
            "flag_confirmed_economic_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
    )

    #
    # --------------------------------------------------------
    # In-kind Corporate Action
    # --------------------------------------------------------
    #

    result[
        "informational_in_kind_ca"
    ] = (
        result[
            "flag_in_kind_corporate_action"
        ]
        .fillna(False)
        .astype(bool)
    )

    #
    # --------------------------------------------------------
    # Extreme return
    # --------------------------------------------------------
    #
    # EXTREME_RETURN isolado continua
    # informacional.
    #
    # Quando ele também gera REVIEW via
    # Price Quality, o blocking_signal
    # será True por essa outra regra.
    #

    result[
        "informational_extreme_return"
    ] = (
        result[
            "flag_extreme_return"
        ]
        .fillna(False)
        .astype(bool)
    )

    return result


# ============================================================
# Global session index
# ============================================================

def add_global_session_index(
    price_quality: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    result = price_quality.merge(
        calendar,
        how="left",
        on="trade_date",
        validate="many_to_one",
    )

    if result[
        "global_session_index"
    ].isna().any():
        raise ValueError(
            "Price Quality possui data "
            "fora do calendário global."
        )

    result[
        "global_session_index"
    ] = result[
        "global_session_index"
    ].astype(
        "int64"
    )

    return result


# ============================================================
# Temporal quality signals
# ============================================================

def add_quality_temporal_signals(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cria dois tipos de agregação:

    1. Rolling por observações do ticker
       para contaminação das FEATURES.

    2. Cumulativo por ticker
       para consulta eficiente do TARGET
       global B3 T+1 ... T+5.
    """

    result = price_quality.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    #
    # --------------------------------------------------------
    # FEATURE LOOKBACK
    #
    # 21 preços / observações do ticker
    # cobrem corretamente return_20d.
    # --------------------------------------------------------
    #

    rolling_sources = {
        "blocking_signal": (
            "blocking_feature_lookback_count"
        ),
        "informational_extreme_return": (
            "extreme_feature_lookback_count"
        ),
        "informational_confirmed_ca": (
            "confirmed_ca_feature_lookback_count"
        ),
        "informational_confirmed_economic_ca": (
            "confirmed_economic_ca_feature_lookback_count"
        ),
        "informational_in_kind_ca": (
            "in_kind_ca_feature_lookback_count"
        ),
    }

    for (
        source_column,
        destination_column,
    ) in rolling_sources.items():

        result[
            destination_column
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
            )[
                source_column
            ]
            .transform(
                lambda series: (
                    series
                    .astype("int64")
                    .rolling(
                        window=(
                            FEATURE_PRICE_LOOKBACK_OBSERVATIONS
                        ),
                        min_periods=1,
                    )
                    .sum()
                )
            )
            .astype("int64")
        )

    result[
        "feature_window_clean"
    ] = (
        result[
            "blocking_feature_lookback_count"
        ]
        == 0
    )

    #
    # --------------------------------------------------------
    # TARGET PREFIX COUNTS
    #
    # count(T+1 ... T+5)
    #
    # =
    #
    # cumulative(T+5)
    # -
    # cumulative(T)
    # --------------------------------------------------------
    #

    cumulative_sources = {
        "blocking_signal": (
            "blocking_cumulative_count"
        ),
        "informational_extreme_return": (
            "extreme_cumulative_count"
        ),
        "blocking_price_quality_review": (
            "price_quality_review_cumulative_count"
        ),
        "blocking_rejected_ca_review": (
            "rejected_ca_cumulative_count"
        ),
        "informational_confirmed_ca": (
            "confirmed_ca_cumulative_count"
        ),
        "informational_confirmed_economic_ca": (
            "confirmed_economic_ca_cumulative_count"
        ),
        "informational_in_kind_ca": (
            "in_kind_ca_cumulative_count"
        ),
    }

    for (
        source_column,
        destination_column,
    ) in cumulative_sources.items():

        result[
            destination_column
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
            )[
                source_column
            ]
            .cumsum()
            .astype("int64")
        )

    return result


# ============================================================
# Supervised sample universe
# ============================================================

def build_sample_universe(
    features: pd.DataFrame,
    calendar: pd.DataFrame,
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reconstrói o universo supervisionável
    diretamente das Features v7.

    Regras:

    - feature_ready=True
    - target global exatamente T+5
    - ticker precisa possuir observação
      exatamente na target_date
    """

    samples = features[
        features[
            "feature_ready"
        ]
        .fillna(False)
        .astype(bool)
    ][
        [
            "feature_date",
            "ticker",
        ]
    ].copy()

    feature_calendar = calendar.rename(
        columns={
            "trade_date": (
                "feature_date"
            ),
            "global_session_index": (
                "feature_global_session_index"
            ),
        }
    )

    samples = samples.merge(
        feature_calendar,
        how="left",
        on="feature_date",
        validate="many_to_one",
    )

    missing_feature_sessions = int(
        samples[
            "feature_global_session_index"
        ]
        .isna()
        .sum()
    )

    if missing_feature_sessions > 0:
        raise ValueError(
            "Existem feature_dates fora "
            "do calendário global B3."
        )

    samples[
        "feature_global_session_index"
    ] = samples[
        "feature_global_session_index"
    ].astype("int64")

    samples[
        "target_global_session_index"
    ] = (
        samples[
            "feature_global_session_index"
        ]
        + EXPECTED_TARGET_HORIZON
    )

    target_calendar = calendar.rename(
        columns={
            "trade_date": (
                "target_date"
            ),
            "global_session_index": (
                "target_global_session_index"
            ),
        }
    )

    samples = samples.merge(
        target_calendar,
        how="left",
        on="target_global_session_index",
        validate="many_to_one",
    )

    #
    # Últimas cinco sessões globais não
    # possuem target T+5 dentro da amostra.
    #

    samples = samples[
        samples[
            "target_date"
        ].notna()
    ].copy()

    #
    # Mesmo existindo T+5 global,
    # o ticker precisa possuir negociação
    # observada exatamente nessa sessão.
    #

    target_availability = (
        price_quality[
            [
                "ticker",
                "trade_date",
            ]
        ]
        .rename(
            columns={
                "trade_date": (
                    "target_date"
                )
            }
        )
        .assign(
            target_available=True
        )
    )

    samples = samples.merge(
        target_availability,
        how="left",
        on=[
            "ticker",
            "target_date",
        ],
        validate="one_to_one",
    )

    samples[
        "target_available"
    ] = (
        samples[
            "target_available"
        ]
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )

    samples = samples[
        samples[
            "target_available"
        ]
    ].copy()

    samples = samples.drop(
        columns=[
            "target_available",
        ]
    )

    samples[
        "target_horizon"
    ] = EXPECTED_TARGET_HORIZON

    samples[
        "target_horizon_semantics"
    ] = (
        EXPECTED_TARGET_HORIZON_SEMANTICS
    )

    return samples


# ============================================================
# Attach feature-date quality
# ============================================================

def attach_feature_quality(
    samples: pd.DataFrame,
    quality: pd.DataFrame,
) -> pd.DataFrame:

    feature_quality = quality[
        [
            "ticker",
            "trade_date",

            "blocking_signal",
            "blocking_price_quality_review",
            "blocking_rejected_ca_review",

            "blocking_feature_lookback_count",
            "extreme_feature_lookback_count",
            "confirmed_ca_feature_lookback_count",
            "confirmed_economic_ca_feature_lookback_count",
            "in_kind_ca_feature_lookback_count",

            "feature_window_clean",

            "blocking_cumulative_count",
            "extreme_cumulative_count",
            "price_quality_review_cumulative_count",
            "rejected_ca_cumulative_count",
            "confirmed_ca_cumulative_count",
            "confirmed_economic_ca_cumulative_count",
            "in_kind_ca_cumulative_count",
        ]
    ].rename(
        columns={
            "trade_date": (
                "feature_date"
            ),

            "blocking_signal": (
                "blocking_signal_on_feature_date"
            ),

            "blocking_price_quality_review": (
                "price_quality_review_on_feature_date"
            ),

            "blocking_rejected_ca_review": (
                "rejected_ca_review_on_feature_date"
            ),

            "blocking_cumulative_count": (
                "blocking_cumulative_at_feature"
            ),

            "extreme_cumulative_count": (
                "extreme_cumulative_at_feature"
            ),

            "price_quality_review_cumulative_count": (
                "price_quality_review_cumulative_at_feature"
            ),

            "rejected_ca_cumulative_count": (
                "rejected_ca_cumulative_at_feature"
            ),

            "confirmed_ca_cumulative_count": (
                "confirmed_ca_cumulative_at_feature"
            ),

            "confirmed_economic_ca_cumulative_count": (
                "confirmed_economic_ca_cumulative_at_feature"
            ),

            "in_kind_ca_cumulative_count": (
                "in_kind_ca_cumulative_at_feature"
            ),
        }
    )

    result = samples.merge(
        feature_quality,
        how="left",
        on=[
            "ticker",
            "feature_date",
        ],
        validate="one_to_one",
    )

    missing = int(
        result[
            "feature_window_clean"
        ]
        .isna()
        .sum()
    )

    if missing > 0:
        raise ValueError(
            "Existem samples sem "
            "Price Quality na feature_date."
        )

    return result


# ============================================================
# Attach target-date quality
# ============================================================

def attach_target_quality(
    samples: pd.DataFrame,
    quality: pd.DataFrame,
) -> pd.DataFrame:

    target_quality = quality[
        [
            "ticker",
            "trade_date",

            "blocking_cumulative_count",
            "extreme_cumulative_count",
            "price_quality_review_cumulative_count",
            "rejected_ca_cumulative_count",
            "confirmed_ca_cumulative_count",
            "confirmed_economic_ca_cumulative_count",
            "in_kind_ca_cumulative_count",
        ]
    ].rename(
        columns={
            "trade_date": (
                "target_date"
            ),

            "blocking_cumulative_count": (
                "blocking_cumulative_at_target"
            ),

            "extreme_cumulative_count": (
                "extreme_cumulative_at_target"
            ),

            "price_quality_review_cumulative_count": (
                "price_quality_review_cumulative_at_target"
            ),

            "rejected_ca_cumulative_count": (
                "rejected_ca_cumulative_at_target"
            ),

            "confirmed_ca_cumulative_count": (
                "confirmed_ca_cumulative_at_target"
            ),

            "confirmed_economic_ca_cumulative_count": (
                "confirmed_economic_ca_cumulative_at_target"
            ),

            "in_kind_ca_cumulative_count": (
                "in_kind_ca_cumulative_at_target"
            ),
        }
    )

    result = samples.merge(
        target_quality,
        how="left",
        on=[
            "ticker",
            "target_date",
        ],
        validate="one_to_one",
    )

    cumulative_columns = [
        "blocking_cumulative_at_target",
        "extreme_cumulative_at_target",
        "price_quality_review_cumulative_at_target",
        "rejected_ca_cumulative_at_target",
        "confirmed_ca_cumulative_at_target",
        "confirmed_economic_ca_cumulative_at_target",
        "in_kind_ca_cumulative_at_target",
    ]

    missing_count = int(
        result[
            cumulative_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    if missing_count > 0:
        raise ValueError(
            "Existem samples sem "
            "Price Quality na target_date."
        )

    return result


# ============================================================
# Target horizon signals
# ============================================================

def calculate_target_horizon_signals(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    #
    # Cumulative(target)
    # -
    # Cumulative(feature)
    #
    # inclui T+1 ... T+5
    # e exclui T.
    #

    target_counts = {
        "blocking_target_horizon_count": (
            "blocking_cumulative_at_target",
            "blocking_cumulative_at_feature",
        ),
        "extreme_target_horizon_count": (
            "extreme_cumulative_at_target",
            "extreme_cumulative_at_feature",
        ),
        "price_quality_review_target_count": (
            "price_quality_review_cumulative_at_target",
            "price_quality_review_cumulative_at_feature",
        ),
        "rejected_ca_review_target_count": (
            "rejected_ca_cumulative_at_target",
            "rejected_ca_cumulative_at_feature",
        ),
        "confirmed_ca_target_count": (
            "confirmed_ca_cumulative_at_target",
            "confirmed_ca_cumulative_at_feature",
        ),
        "confirmed_economic_ca_target_count": (
            "confirmed_economic_ca_cumulative_at_target",
            "confirmed_economic_ca_cumulative_at_feature",
        ),
        "in_kind_ca_target_count": (
            "in_kind_ca_cumulative_at_target",
            "in_kind_ca_cumulative_at_feature",
        ),
    }

    for (
        destination_column,
        (
            target_column,
            feature_column,
        ),
    ) in target_counts.items():

        result[
            destination_column
        ] = (
            result[
                target_column
            ]
            - result[
                feature_column
            ]
        ).astype("int64")

    result[
        "target_horizon_clean"
    ] = (
        result[
            "blocking_target_horizon_count"
        ]
        == 0
    )

    return result


# ============================================================
# Eligibility reason
# ============================================================

def build_ineligibility_reason(
    row: pd.Series,
) -> str:
    reasons: list[str] = []

    if not row[
        "feature_window_clean"
    ]:
        reasons.append(
            "BLOCKING_EVENT_IN_FEATURE_LOOKBACK"
        )

    if not row[
        "target_horizon_clean"
    ]:
        reasons.append(
            "BLOCKING_EVENT_IN_TARGET_HORIZON"
        )

    if not reasons:
        return "NONE"

    return "|".join(
        reasons
    )


# ============================================================
# Final eligibility
# ============================================================

def add_final_eligibility(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "ml_eligible"
    ] = (
        result[
            "feature_window_clean"
        ]
        &
        result[
            "target_horizon_clean"
        ]
    )

    result[
        "ml_ineligibility_reason"
    ] = result.apply(
        build_ineligibility_reason,
        axis=1,
    )

    result[
        "feature_return_window"
    ] = (
        MAX_FEATURE_RETURN_WINDOW
    )

    result[
        "feature_price_lookback_observations"
    ] = (
        FEATURE_PRICE_LOOKBACK_OBSERVATIONS
    )

    result[
        "ml_eligibility_version"
    ] = (
        ML_ELIGIBILITY_VERSION
    )

    result[
        "source_feature_version"
    ] = (
        EXPECTED_FEATURE_VERSION
    )

    result[
        "source_price_quality_version"
    ] = (
        EXPECTED_PRICE_QUALITY_VERSION
    )

    result[
        "source_price_quality_source"
    ] = (
        EXPECTED_PRICE_QUALITY_SOURCE
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
        "eligibility_policy"
    ] = (
        "QUALITY_REVIEW_OR_REJECTED_CA_BLOCKS_"
        "CONFIRMED_CA_AND_ISOLATED_EXTREME_INFORMATIONAL"
    )

    result[
        "created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


# ============================================================
# Output validation
# ============================================================

def validate_output(
    dataframe: pd.DataFrame,
) -> None:

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

        "blocking_feature_lookback_count",
        "blocking_target_horizon_count",

        "feature_window_clean",
        "target_horizon_clean",

        "ml_eligible",
        "ml_ineligibility_reason",

        "ml_eligibility_version",

        "source_feature_version",
        "source_price_quality_version",
        "source_price_quality_source",

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
            "colunas ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "feature_date",
            ]
        ).sum()
    )

    null_count = int(
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    calculated_horizon = (
        dataframe[
            "target_global_session_index"
        ]
        - dataframe[
            "feature_global_session_index"
        ]
    )

    invalid_global_horizon = int(
        (
            calculated_horizon
            != EXPECTED_TARGET_HORIZON
        ).sum()
    )

    invalid_target_semantics = int(
        (
            dataframe[
                "target_horizon_semantics"
            ]
            != EXPECTED_TARGET_HORIZON_SEMANTICS
        ).sum()
    )

    invalid_lookback = int(
        (
            dataframe[
                "feature_price_lookback_observations"
            ]
            != FEATURE_PRICE_LOOKBACK_OBSERVATIONS
        ).sum()
    )

    inconsistent_eligibility = int(
        (
            dataframe[
                "ml_eligible"
            ]
            != (
                dataframe[
                    "feature_window_clean"
                ]
                &
                dataframe[
                    "target_horizon_clean"
                ]
            )
        ).sum()
    )

    eligible_with_reason = int(
        (
            dataframe[
                "ml_eligible"
            ]
            &
            (
                dataframe[
                    "ml_ineligibility_reason"
                ]
                != "NONE"
            )
        ).sum()
    )

    ineligible_without_reason = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
            &
            (
                dataframe[
                    "ml_ineligibility_reason"
                ]
                == "NONE"
            )
        ).sum()
    )

    count_columns = [
        "blocking_target_horizon_count",
        "extreme_target_horizon_count",
        "price_quality_review_target_count",
        "rejected_ca_review_target_count",
        "confirmed_ca_target_count",
        "confirmed_economic_ca_target_count",
        "in_kind_ca_target_count",
    ]

    negative_target_counts = int(
        (
            dataframe[
                count_columns
            ]
            < 0
        )
        .sum()
        .sum()
    )

    invalid_versions = int(
        (
            dataframe[
                "ml_eligibility_version"
            ]
            != ML_ELIGIBILITY_VERSION
        ).sum()
    )

    invalid_feature_versions = int(
        (
            dataframe[
                "source_feature_version"
            ]
            != EXPECTED_FEATURE_VERSION
        ).sum()
    )

    invalid_quality_versions = int(
        (
            dataframe[
                "source_price_quality_version"
            ]
            != EXPECTED_PRICE_QUALITY_VERSION
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - ML Eligibility v3"
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
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Nulos obrigatórios: "
        f"{null_count:,}"
    )

    print(
        "Horizontes diferentes de "
        "T+5 global B3: "
        f"{invalid_global_horizon:,}"
    )

    print(
        "Target semantics inválidas: "
        f"{invalid_target_semantics:,}"
    )

    print(
        "Lookbacks diferentes de "
        f"{FEATURE_PRICE_LOOKBACK_OBSERVATIONS}: "
        f"{invalid_lookback:,}"
    )

    print(
        "Contagens target negativas: "
        f"{negative_target_counts:,}"
    )

    print(
        "Inconsistências ml_eligible: "
        f"{inconsistent_eligibility:,}"
    )

    print(
        "Eligible com motivo de bloqueio: "
        f"{eligible_with_reason:,}"
    )

    print(
        "Ineligible sem motivo: "
        f"{ineligible_without_reason:,}"
    )

    print(
        "Eligibility versions inválidas: "
        f"{invalid_versions:,}"
    )

    print(
        "Feature versions inválidas: "
        f"{invalid_feature_versions:,}"
    )

    print(
        "Price Quality versions inválidas: "
        f"{invalid_quality_versions:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Eligibility possui duplicidades."
        )

    if null_count > 0:
        raise ValueError(
            "Eligibility possui NULL "
            "em campo obrigatório."
        )

    if invalid_global_horizon > 0:
        raise ValueError(
            "Eligibility encontrou target "
            "fora da semântica global B3 T+5."
        )

    if invalid_target_semantics > 0:
        raise ValueError(
            "Eligibility possui "
            "target_horizon_semantics inválida."
        )

    if invalid_lookback > 0:
        raise ValueError(
            "Eligibility possui feature "
            "lookback inconsistente."
        )

    if negative_target_counts > 0:
        raise ValueError(
            "Eligibility gerou contagem "
            "target negativa."
        )

    if inconsistent_eligibility > 0:
        raise ValueError(
            "Eligibility possui status "
            "inconsistente."
        )

    if eligible_with_reason > 0:
        raise ValueError(
            "Existem samples eligible "
            "com motivo de bloqueio."
        )

    if ineligible_without_reason > 0:
        raise ValueError(
            "Existem samples ineligible "
            "sem motivo."
        )

    if invalid_versions > 0:
        raise ValueError(
            "ml_eligibility_version inválida."
        )

    if invalid_feature_versions > 0:
        raise ValueError(
            "source_feature_version inválida."
        )

    if invalid_quality_versions > 0:
        raise ValueError(
            "source_price_quality_version "
            "inválida."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Output contract
# ============================================================

def select_output_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    columns = [
        "ticker",
        "feature_date",
        "target_date",

        "feature_global_session_index",
        "target_global_session_index",

        "target_horizon",
        "target_horizon_semantics",

        "feature_return_window",
        "feature_price_lookback_observations",

        #
        # Feature-date blocking
        #
        "blocking_signal_on_feature_date",
        "price_quality_review_on_feature_date",
        "rejected_ca_review_on_feature_date",

        #
        # Feature lookback
        #
        "blocking_feature_lookback_count",
        "extreme_feature_lookback_count",

        "confirmed_ca_feature_lookback_count",
        "confirmed_economic_ca_feature_lookback_count",
        "in_kind_ca_feature_lookback_count",

        "feature_window_clean",

        #
        # Target horizon
        #
        "blocking_target_horizon_count",
        "extreme_target_horizon_count",

        "price_quality_review_target_count",
        "rejected_ca_review_target_count",

        "confirmed_ca_target_count",
        "confirmed_economic_ca_target_count",
        "in_kind_ca_target_count",

        "target_horizon_clean",

        #
        # Final eligibility
        #
        "ml_eligible",
        "ml_ineligibility_reason",

        #
        # Metadata
        #
        "ml_eligibility_version",

        "source_feature_version",
        "source_price_quality_version",
        "source_price_quality_source",

        "price_semantics",
        "return_semantics",
        "corporate_action_value_semantics",

        "eligibility_policy",

        "created_at",
    ]

    return dataframe[
        columns
    ].copy()


# ============================================================
# Summary
# ============================================================

def print_summary(
    dataframe: pd.DataFrame,
    feature_ready_count: int,
) -> None:

    eligible_count = int(
        dataframe[
            "ml_eligible"
        ].sum()
    )

    ineligible_count = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
        ).sum()
    )

    feature_contaminated = int(
        (
            ~dataframe[
                "feature_window_clean"
            ]
        ).sum()
    )

    target_contaminated = int(
        (
            ~dataframe[
                "target_horizon_clean"
            ]
        ).sum()
    )

    both_contaminated = int(
        (
            ~dataframe[
                "feature_window_clean"
            ]
            &
            ~dataframe[
                "target_horizon_clean"
            ]
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo - FII ML Eligibility"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{ML_ELIGIBILITY_VERSION}"
    )

    print(
        "Source feature version: "
        f"{EXPECTED_FEATURE_VERSION}"
    )

    print(
        "Source Price Quality: "
        f"{EXPECTED_PRICE_QUALITY_VERSION}"
    )

    print(
        "Feature return window: "
        f"{MAX_FEATURE_RETURN_WINDOW}"
    )

    print(
        "Feature price lookback: "
        f"{FEATURE_PRICE_LOOKBACK_OBSERVATIONS} "
        "observações"
    )

    print(
        "Target horizon: "
        "GLOBAL_B3_TRADING_DAYS T+5"
    )

    print(
        "\nUniverso:"
    )

    print(
        "  Feature rows prontas: "
        f"{feature_ready_count:,}"
    )

    print(
        "  Samples supervisionáveis: "
        f"{len(dataframe):,}"
    )

    print(
        "\nEligibility:"
    )

    print(
        f"  ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"  ML ineligible: "
        f"{ineligible_count:,}"
    )

    if len(dataframe) > 0:
        print(
            "  Eligibility rate: "
            f"{eligible_count / len(dataframe) * 100:.2f}%"
        )

    print(
        "\nContaminação temporal:"
    )

    print(
        "  Feature lookback contaminado: "
        f"{feature_contaminated:,}"
    )

    print(
        "  Target horizon contaminado: "
        f"{target_contaminated:,}"
    )

    print(
        "  Ambos: "
        f"{both_contaminated:,}"
    )

    print(
        "\nMotivos:"
    )

    for value, count in (
        dataframe[
            "ml_ineligibility_reason"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nSinais informacionais:"
    )

    print(
        "  EXTREME_RETURN no feature lookback: "
        f"{int((dataframe['extreme_feature_lookback_count'] > 0).sum()):,}"
    )

    print(
        "  EXTREME_RETURN no target horizon: "
        f"{int((dataframe['extreme_target_horizon_count'] > 0).sum()):,}"
    )

    print(
        "  CONFIRMED CA no feature lookback: "
        f"{int((dataframe['confirmed_ca_feature_lookback_count'] > 0).sum()):,}"
    )

    print(
        "  CONFIRMED CA no target horizon: "
        f"{int((dataframe['confirmed_ca_target_count'] > 0).sum()):,}"
    )

    print(
        "  CONFIRMED ECONOMIC CA "
        "no feature lookback: "
        f"{int((dataframe['confirmed_economic_ca_feature_lookback_count'] > 0).sum()):,}"
    )

    print(
        "  CONFIRMED ECONOMIC CA "
        "no target horizon: "
        f"{int((dataframe['confirmed_economic_ca_target_count'] > 0).sum()):,}"
    )

    print(
        "  IN-KIND CA no feature lookback: "
        f"{int((dataframe['in_kind_ca_feature_lookback_count'] > 0).sum()):,}"
    )

    print(
        "  IN-KIND CA no target horizon: "
        f"{int((dataframe['in_kind_ca_target_count'] > 0).sum()):,}"
    )

    print(
        "  REJECTED CA na feature_date: "
        f"{int(dataframe['rejected_ca_review_on_feature_date'].sum()):,}"
    )

    print(
        "  REJECTED CA no target horizon: "
        f"{int((dataframe['rejected_ca_review_target_count'] > 0).sum()):,}"
    )

    ineligible = dataframe[
        ~dataframe[
            "ml_eligible"
        ]
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Amostra - ML INELIGIBLE"
    )
    print(
        "======================================"
    )

    if ineligible.empty:
        print(
            "Nenhuma amostra inelegível."
        )

    else:
        display = ineligible[
            [
                "ticker",
                "feature_date",
                "target_date",
                "blocking_feature_lookback_count",
                "blocking_target_horizon_count",
                "extreme_feature_lookback_count",
                "extreme_target_horizon_count",
                "ml_ineligibility_reason",
            ]
        ].sort_values(
            [
                "feature_date",
                "ticker",
            ]
        )

        print(
            display.head(
                50
            ).to_string(
                index=False
            )
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

    print(
        "Construindo FII ML Eligibility..."
    )

    print(
        f"Version: "
        f"{ML_ELIGIBILITY_VERSION}"
    )

    print(
        "Feature source: "
        f"FII Features {EXPECTED_FEATURE_VERSION}"
    )

    print(
        "Price Quality source: "
        f"v{EXPECTED_PRICE_QUALITY_VERSION.lstrip('v')}"
    )

    print(
        "Feature return window: "
        f"{MAX_FEATURE_RETURN_WINDOW}"
    )

    print(
        "Feature price lookback: "
        f"{FEATURE_PRICE_LOOKBACK_OBSERVATIONS} "
        "observações"
    )

    print(
        "Target horizon: "
        "GLOBAL_B3_TRADING_DAYS T+5"
    )

    features = load_features()

    validate_features(
        features
    )

    feature_ready_count = int(
        features[
            "feature_ready"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    quality = load_price_quality()

    validate_price_quality(
        quality
    )

    calendar = build_global_calendar(
        quality
    )

    quality = build_blocking_signals(
        quality
    )

    quality = add_global_session_index(
        price_quality=quality,
        calendar=calendar,
    )

    quality = add_quality_temporal_signals(
        quality
    )

    samples = build_sample_universe(
        features=features,
        calendar=calendar,
        price_quality=quality,
    )

    samples = attach_feature_quality(
        samples=samples,
        quality=quality,
    )

    samples = attach_target_quality(
        samples=samples,
        quality=quality,
    )

    samples = calculate_target_horizon_signals(
        samples
    )

    samples = add_final_eligibility(
        samples
    )

    validate_output(
        samples
    )

    output = select_output_columns(
        samples
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print_summary(
        dataframe=output,
        feature_ready_count=feature_ready_count,
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "Nenhuma sample foi removida "
        "fisicamente."
    )

    print(
        "O universo supervisionado foi "
        "reconstruído diretamente das "
        "Features v7."
    )

    print(
        "Nenhuma dependência do Training "
        "Dataset antigo permanece."
    )

    print(
        "O lookback de features considera "
        "21 observações para cobrir "
        "return_20d corretamente."
    )

    print(
        "O target permanece exatamente "
        "T+5 sessões globais B3."
    )

    print(
        "Corporate Actions CONFIRMED são "
        "informacionais porque a série já "
        "está economicamente corrigida."
    )

    print(
        "Corporate Actions econômicos e "
        "in-kind permanecem auditáveis."
    )

    print(
        "EXTREME_RETURN isoladamente "
        "permanece não bloqueante."
    )

    print(
        "A política de bloqueio anterior "
        "foi preservada."
    )


if __name__ == "__main__":
    main()