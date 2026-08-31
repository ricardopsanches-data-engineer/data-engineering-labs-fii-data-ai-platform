from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


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


ML_ELIGIBILITY_VERSION = "v2"

EXPECTED_FEATURE_VERSION = "v6"

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)


#
# A maior feature é return_20d.
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

    ready_count = int(
        dataframe[
            "feature_ready"
        ]
        .fillna(
            False
        )
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

    if duplicate_count > 0:
        raise ValueError(
            "FII Features possui "
            "duplicidades."
        )

    if versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "ML Eligibility v2 exige "
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

    print(
        "\nData Quality aprovada."
    )


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
        "flag_pending_corporate_action",
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

    pending_count = int(
        dataframe[
            "flag_pending_corporate_action"
        ]
        .fillna(
            False
        )
        .sum()
    )

    confirmed_count = int(
        dataframe[
            "flag_confirmed_corporate_action"
        ]
        .fillna(
            False
        )
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
        "Status inválidos: "
        f"{len(invalid_statuses):,}"
    )

    print(
        "Corporate Actions pendentes: "
        f"{pending_count:,}"
    )

    print(
        "Corporate Actions confirmados: "
        f"{confirmed_count:,}"
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

    if pending_count > 0:
        raise ValueError(
            "ML Eligibility v2 não será "
            "construída com Corporate Actions "
            "PENDING_REVIEW."
        )

    print(
        "\nData Quality aprovada."
    )


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


def build_blocking_signals(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    result = price_quality.copy()

    #
    # REVIEW da camada de qualidade
    # continua bloqueante.
    #
    result[
        "blocking_price_quality_review"
    ] = (
        result[
            "ml_quality_status"
        ]
        == "REVIEW"
    )

    #
    # REJECTED significa:
    # investigado como Corporate Action
    # e concluído como outro tipo de evento.
    #
    # Mesmo que a heurística Price Quality v1
    # não o coloque em REVIEW, queremos
    # mantê-lo governado no ML.
    #
    result[
        "blocking_rejected_ca_review"
    ] = (
        result[
            "review_status_on_date"
        ]
        == "REJECTED"
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
    # Evento confirmado não bloqueia mais:
    # Price History v2 e Features v6 já
    # incorporam sua semântica econômica.
    #
    result[
        "informational_confirmed_ca"
    ] = (
        result[
            "flag_confirmed_corporate_action"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
    )

    #
    # EXTREME_RETURN isoladamente também
    # não bloqueia.
    #
    result[
        "informational_extreme_return"
    ] = (
        result[
            "flag_extreme_return"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
    )

    return result


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


def add_quality_temporal_signals(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cria dois tipos de agregação:

    1. Rolling por observações do ticker
       para contaminação das FEATURES.

    2. Cumulativo por ticker
       para consulta eficiente do TARGET
       T+1 ... T+5.
    """

    result = price_quality.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    #
    # -----------------------------------------
    # FEATURE LOOKBACK
    #
    # 21 preços / observações do ticker.
    # -----------------------------------------
    #

    result[
        "blocking_feature_lookback_count"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "blocking_signal"
        ]
        .transform(
            lambda series: (
                series
                .astype(
                    "int64"
                )
                .rolling(
                    window=(
                        FEATURE_PRICE_LOOKBACK_OBSERVATIONS
                    ),
                    min_periods=1,
                )
                .sum()
            )
        )
        .astype(
            "int64"
        )
    )

    result[
        "extreme_feature_lookback_count"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "informational_extreme_return"
        ]
        .transform(
            lambda series: (
                series
                .astype(
                    "int64"
                )
                .rolling(
                    window=(
                        FEATURE_PRICE_LOOKBACK_OBSERVATIONS
                    ),
                    min_periods=1,
                )
                .sum()
            )
        )
        .astype(
            "int64"
        )
    )

    result[
        "confirmed_ca_feature_lookback_count"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "informational_confirmed_ca"
        ]
        .transform(
            lambda series: (
                series
                .astype(
                    "int64"
                )
                .rolling(
                    window=(
                        FEATURE_PRICE_LOOKBACK_OBSERVATIONS
                    ),
                    min_periods=1,
                )
                .sum()
            )
        )
        .astype(
            "int64"
        )
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
    # -----------------------------------------
    # TARGET PREFIX COUNTS
    #
    # Para target horizon:
    #
    # count(T+1 ... T+5)
    #
    # =
    #
    # cumulative(T+5)
    # -
    # cumulative(T)
    #
    # -----------------------------------------
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
            .astype(
                "int64"
            )
        )

    return result


def build_sample_universe(
    features: pd.DataFrame,
    calendar: pd.DataFrame,
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reconstrói o universo supervisionado
    diretamente das Features v6.

    Não utiliza o Training Dataset RAW antigo.

    Regras:

    - feature_ready=True
    - target global exatamente T+5
    - mesmo ticker precisa possuir preço/
      qualidade na target_date
    """

    samples = features[
        features[
            "feature_ready"
        ]
        .fillna(
            False
        )
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
    ].astype(
        "int64"
    )

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
    # As últimas cinco sessões globais não
    # possuem target T+5 dentro da amostra.
    #
    samples = samples[
        samples[
            "target_date"
        ].notna()
    ].copy()

    #
    # Mesmo existindo T+5 global,
    # o ticker precisa ter observação
    # exatamente nessa sessão.
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
        .astype(
            "boolean"
        )
        .fillna(
            False
        )
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

            "feature_window_clean",

            "blocking_cumulative_count",
            "extreme_cumulative_count",
            "price_quality_review_cumulative_count",
            "rejected_ca_cumulative_count",
            "confirmed_ca_cumulative_count",
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

    result[
        "blocking_target_horizon_count"
    ] = (
        result[
            "blocking_cumulative_at_target"
        ]
        - result[
            "blocking_cumulative_at_feature"
        ]
    ).astype(
        "int64"
    )

    result[
        "extreme_target_horizon_count"
    ] = (
        result[
            "extreme_cumulative_at_target"
        ]
        - result[
            "extreme_cumulative_at_feature"
        ]
    ).astype(
        "int64"
    )

    result[
        "price_quality_review_target_count"
    ] = (
        result[
            "price_quality_review_cumulative_at_target"
        ]
        - result[
            "price_quality_review_cumulative_at_feature"
        ]
    ).astype(
        "int64"
    )

    result[
        "rejected_ca_review_target_count"
    ] = (
        result[
            "rejected_ca_cumulative_at_target"
        ]
        - result[
            "rejected_ca_cumulative_at_feature"
        ]
    ).astype(
        "int64"
    )

    result[
        "confirmed_ca_target_count"
    ] = (
        result[
            "confirmed_ca_cumulative_at_target"
        ]
        - result[
            "confirmed_ca_cumulative_at_feature"
        ]
    ).astype(
        "int64"
    )

    result[
        "target_horizon_clean"
    ] = (
        result[
            "blocking_target_horizon_count"
        ]
        == 0
    )

    return result


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
        "created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


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

        "feature_price_lookback_observations",

        "blocking_feature_lookback_count",
        "blocking_target_horizon_count",

        "feature_window_clean",
        "target_horizon_clean",

        "ml_eligible",
        "ml_ineligibility_reason",

        "ml_eligibility_version",
        "source_feature_version",

        "price_semantics",
        "return_semantics",
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

    negative_target_counts = int(
        (
            dataframe[
                [
                    "blocking_target_horizon_count",
                    "extreme_target_horizon_count",
                    "price_quality_review_target_count",
                    "rejected_ca_review_target_count",
                    "confirmed_ca_target_count",
                ]
            ]
            < 0
        )
        .sum()
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

    print(
        "\nData Quality aprovada."
    )


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

        "blocking_signal_on_feature_date",
        "price_quality_review_on_feature_date",
        "rejected_ca_review_on_feature_date",

        "blocking_feature_lookback_count",
        "extreme_feature_lookback_count",
        "confirmed_ca_feature_lookback_count",

        "feature_window_clean",

        "blocking_target_horizon_count",
        "extreme_target_horizon_count",

        "price_quality_review_target_count",
        "rejected_ca_review_target_count",
        "confirmed_ca_target_count",

        "target_horizon_clean",

        "ml_eligible",
        "ml_ineligibility_reason",

        "ml_eligibility_version",
        "source_feature_version",

        "price_semantics",
        "return_semantics",

        "created_at",
    ]

    return dataframe[
        columns
    ].copy()


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
        .fillna(
            False
        )
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
        "Features v6."
    )

    print(
        "Nenhuma dependência do Training "
        "Dataset RAW antigo permanece."
    )

    print(
        "O lookback de features considera "
        "21 observações para cobrir "
        "return_20d corretamente."
    )

    print(
        "Corporate Actions CONFIRMED são "
        "informacionais porque a série já "
        "está economicamente corrigida."
    )

    print(
        "EXTREME_RETURN isoladamente "
        "permanece não bloqueante."
    )


if __name__ == "__main__":
    main()