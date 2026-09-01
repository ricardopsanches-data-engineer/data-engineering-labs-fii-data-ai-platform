from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# Paths
# ============================================================

ADJUSTED_PRICES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
    / "fii_corporate_action_adjusted_prices.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "quality"
    / "fii_price_quality"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_price_quality.parquet"
)


# ============================================================
# Version / upstream contract
# ============================================================

PRICE_QUALITY_VERSION = "v2"

EXPECTED_ADJUSTED_PRICES_VERSION = "v3"

EXPECTED_ADJUSTED_PRICES_SOURCE = (
    "SILVER_FII_DAILY_PRICES"
)

EXPECTED_CORPORATE_ACTION_SOURCE = (
    "FII_PRICE_DISCONTINUITIES_V5_REGISTRY_V2"
)


# ============================================================
# Quality thresholds
# ============================================================

EXTREME_RETURN_THRESHOLD = 0.50

LOW_PRICE_THRESHOLD = 1.00

SHORT_GAP_MAX_SESSIONS = 5
MEDIUM_GAP_MAX_SESSIONS = 20


# ============================================================
# Load source
# ============================================================

def load_source() -> pd.DataFrame:
    """
    Carrega Corporate Action Adjusted
    Prices v3.

    Price Quality passa a depender
    explicitamente do contrato econômico
    v3.
    """

    if not ADJUSTED_PRICES_PATH.exists():
        raise FileNotFoundError(
            "Adjusted Prices não encontrado: "
            f"{ADJUSTED_PRICES_PATH}"
        )

    print(
        "Carregando FII Corporate Action "
        "Adjusted Prices..."
    )

    dataframe = pd.read_parquet(
        ADJUSTED_PRICES_PATH
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
# Source validation
# ============================================================

def validate_source(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida Adjusted Prices v3 e sua
    semântica econômica antes de produzir
    qualquer flag de qualidade.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price_raw",
        "close_price_adjusted",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        "cash_amount_per_unit_raw",
        "in_kind_amount_per_unit_raw",
        "corporate_action_value_per_unit_raw",

        "review_status_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",

        "confirmed_event_type",
        "confirmed_in_kind_asset_ticker",

        "adjusted_prices_version",
        "adjusted_prices_source",
        "corporate_action_source",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Fonte possui colunas ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    invalid_raw_prices = int(
        (
            dataframe[
                "close_price_raw"
            ]
            <= 0
        ).sum()
    )

    invalid_adjusted_prices = int(
        (
            dataframe[
                "close_price_adjusted"
            ]
            <= 0
        ).sum()
    )

    non_finite_raw_returns = int(
        (
            dataframe[
                "daily_return_raw"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "daily_return_raw"
                ]
            )
        ).sum()
    )

    non_finite_adjusted_returns = int(
        (
            dataframe[
                "daily_return_adjusted_price"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "daily_return_adjusted_price"
                ]
            )
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

    negative_cash = int(
        (
            dataframe[
                "cash_amount_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    negative_in_kind = int(
        (
            dataframe[
                "in_kind_amount_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    negative_total_value = int(
        (
            dataframe[
                "corporate_action_value_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    economic_component_mismatch = int(
        (
            ~np.isclose(
                (
                    dataframe[
                        "cash_amount_per_unit_raw"
                    ]
                    +
                    dataframe[
                        "in_kind_amount_per_unit_raw"
                    ]
                ),
                dataframe[
                    "corporate_action_value_per_unit_raw"
                ],
                rtol=1e-8,
                atol=1e-8,
            )
        ).sum()
    )

    invalid_version = int(
        (
            dataframe[
                "adjusted_prices_version"
            ]
            != EXPECTED_ADJUSTED_PRICES_VERSION
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "adjusted_prices_source"
            ]
            != EXPECTED_ADJUSTED_PRICES_SOURCE
        ).sum()
    )

    invalid_corporate_action_source = int(
        (
            dataframe[
                "corporate_action_source"
            ]
            != EXPECTED_CORPORATE_ACTION_SOURCE
        ).sum()
    )

    pending_count = int(
        dataframe[
            "pending_review_on_date"
        ]
        .fillna(
            False
        )
        .astype(bool)
        .sum()
    )

    confirmed_count = int(
        dataframe[
            "confirmed_action_on_date"
        ]
        .fillna(
            False
        )
        .astype(bool)
        .sum()
    )

    economic_action_count = int(
        dataframe[
            "corporate_action_value_per_unit_raw"
        ]
        .gt(
            0
        )
        .sum()
    )

    in_kind_action_count = int(
        dataframe[
            "in_kind_amount_per_unit_raw"
        ]
        .gt(
            0
        )
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Fonte"
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
        f"Preços RAW inválidos: "
        f"{invalid_raw_prices:,}"
    )

    print(
        f"Preços adjusted inválidos: "
        f"{invalid_adjusted_prices:,}"
    )

    print(
        "Retornos RAW não finitos: "
        f"{non_finite_raw_returns:,}"
    )

    print(
        "Retornos adjusted não finitos: "
        f"{non_finite_adjusted_returns:,}"
    )

    print(
        "Retornos econômicos não finitos: "
        f"{non_finite_economic_returns:,}"
    )

    print(
        f"Cash negativo: "
        f"{negative_cash:,}"
    )

    print(
        f"In-kind negativo: "
        f"{negative_in_kind:,}"
    )

    print(
        "Valor econômico negativo: "
        f"{negative_total_value:,}"
    )

    print(
        "Mismatch cash + in-kind != total: "
        f"{economic_component_mismatch:,}"
    )

    print(
        f"Versões inválidas: "
        f"{invalid_version:,}"
    )

    print(
        f"Sources inválidos: "
        f"{invalid_source:,}"
    )

    print(
        "Corporate Action Sources inválidos: "
        f"{invalid_corporate_action_source:,}"
    )

    print(
        f"Corporate Actions confirmados: "
        f"{confirmed_count:,}"
    )

    print(
        f"Eventos econômicos: "
        f"{economic_action_count:,}"
    )

    print(
        f"Eventos in-kind: "
        f"{in_kind_action_count:,}"
    )

    print(
        f"Eventos PENDING_REVIEW: "
        f"{pending_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Fonte possui duplicidades."
        )

    if invalid_raw_prices > 0:
        raise ValueError(
            "Fonte possui preços RAW inválidos."
        )

    if invalid_adjusted_prices > 0:
        raise ValueError(
            "Fonte possui preços adjusted "
            "inválidos."
        )

    if non_finite_raw_returns > 0:
        raise ValueError(
            "Fonte possui retorno RAW "
            "não finito."
        )

    if non_finite_adjusted_returns > 0:
        raise ValueError(
            "Fonte possui retorno adjusted "
            "não finito."
        )

    if non_finite_economic_returns > 0:
        raise ValueError(
            "Fonte possui retorno econômico "
            "não finito."
        )

    if negative_cash > 0:
        raise ValueError(
            "Fonte possui cash negativo."
        )

    if negative_in_kind > 0:
        raise ValueError(
            "Fonte possui in-kind negativo."
        )

    if negative_total_value > 0:
        raise ValueError(
            "Fonte possui valor econômico "
            "corporativo negativo."
        )

    if economic_component_mismatch > 0:
        raise ValueError(
            "Fonte possui inconsistência "
            "cash + in-kind != "
            "total economic value."
        )

    if invalid_version > 0:
        raise ValueError(
            "Price Quality v2 exige "
            "Adjusted Prices v3."
        )

    if invalid_source > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "source incompatível."
        )

    if invalid_corporate_action_source > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "Corporate Action Source "
            "incompatível."
        )

    if pending_count > 0:
        raise ValueError(
            "Price Quality v2 não aceita "
            "eventos PENDING_REVIEW."
        )

    print(
        "\nData Quality da fonte aprovada."
    )


# ============================================================
# Global trading calendar
# ============================================================

def build_global_calendar(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói calendário global a partir
    das sessões existentes no dataset.

    O objetivo é medir ausência de negócios
    do ticker em unidades de pregão,
    e não apenas dias corridos.
    """

    calendar = (
        dataframe[
            ["trade_date"]
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
# Previous trade information
# ============================================================

def add_previous_trade_information(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    result[
        "previous_trade_date"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "trade_date"
        ]
        .shift(1)
    )

    result[
        "previous_close_price_raw"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "close_price_raw"
        ]
        .shift(1)
    )

    return result


# ============================================================
# Gap metrics
# ============================================================

def add_gap_metrics(
    dataframe: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "trading_gap_calendar_days"
    ] = (
        result[
            "trade_date"
        ]
        - result[
            "previous_trade_date"
        ]
    ).dt.days

    current_calendar = (
        calendar.rename(
            columns={
                "global_session_index": (
                    "current_session_index"
                )
            }
        )
    )

    previous_calendar = (
        calendar.rename(
            columns={
                "trade_date": (
                    "previous_trade_date"
                ),
                "global_session_index": (
                    "previous_session_index"
                ),
            }
        )
    )

    result = result.merge(
        current_calendar,
        how="left",
        on="trade_date",
        validate="many_to_one",
    )

    result = result.merge(
        previous_calendar,
        how="left",
        on="previous_trade_date",
        validate="many_to_one",
    )

    result[
        "trading_gap_sessions"
    ] = (
        result[
            "current_session_index"
        ]
        - result[
            "previous_session_index"
        ]
    )

    return result


def classify_gap(
    sessions: float,
) -> str:
    if pd.isna(
        sessions
    ):
        return "UNKNOWN"

    sessions = int(
        sessions
    )

    if sessions <= 1:
        return "CONTIGUOUS"

    if sessions <= SHORT_GAP_MAX_SESSIONS:
        return "SHORT_GAP"

    if sessions <= MEDIUM_GAP_MAX_SESSIONS:
        return "MEDIUM_GAP"

    return "LONG_GAP"


# ============================================================
# Quality flags
# ============================================================

def add_quality_flags(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cria sinais de qualidade.

    IMPORTANTE:

    flag_extreme_return usa
    daily_return_economic.

    Portanto movimentos mecânicos já
    explicados por split/amortização não
    são tratados automaticamente como
    anomalias econômicas.

    Corporate Actions confirmados são
    contexto auditável e NÃO erro de
    qualidade por definição.
    """

    result = dataframe.copy()

    result[
        "trading_gap_class"
    ] = result[
        "trading_gap_sessions"
    ].map(
        classify_gap
    )

    result[
        "flag_extreme_return"
    ] = (
        result[
            "daily_return_economic"
        ]
        .abs()
        >= EXTREME_RETURN_THRESHOLD
    )

    result[
        "flag_low_price"
    ] = (
        result[
            "close_price_raw"
        ]
        <= LOW_PRICE_THRESHOLD
    )

    result[
        "flag_short_gap"
    ] = (
        result[
            "trading_gap_class"
        ]
        == "SHORT_GAP"
    )

    result[
        "flag_medium_gap"
    ] = (
        result[
            "trading_gap_class"
        ]
        == "MEDIUM_GAP"
    )

    result[
        "flag_long_gap"
    ] = (
        result[
            "trading_gap_class"
        ]
        == "LONG_GAP"
    )

    result[
        "flag_pending_corporate_action"
    ] = (
        result[
            "pending_review_on_date"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
    )

    result[
        "flag_confirmed_corporate_action"
    ] = (
        result[
            "confirmed_action_on_date"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
    )

    result[
        "flag_confirmed_economic_corporate_action"
    ] = (
        result[
            "flag_confirmed_corporate_action"
        ]
        &
        result[
            "confirmed_event_type"
        ]
        .fillna("")
        .eq(
            "AMORTIZATION"
        )
    )

    result[
        "flag_in_kind_corporate_action"
    ] = (
        result[
            "flag_confirmed_corporate_action"
        ]
        &
        result[
            "in_kind_amount_per_unit_raw"
        ]
        .gt(
            0.0
        )
    )

    result[
        "flag_possible_microliquidity"
    ] = (
        result[
            "flag_extreme_return"
        ]
        &
        (
            result[
                "flag_low_price"
            ]
            |
            result[
                "flag_long_gap"
            ]
        )
    )

    return result


# ============================================================
# Quality flag serialization
# ============================================================

def build_quality_flag_list(
    row: pd.Series,
) -> str:
    flags: list[str] = []

    if row[
        "flag_extreme_return"
    ]:
        flags.append(
            "EXTREME_RETURN"
        )

    if row[
        "flag_low_price"
    ]:
        flags.append(
            "LOW_PRICE"
        )

    if row[
        "flag_short_gap"
    ]:
        flags.append(
            "SHORT_TRADING_GAP"
        )

    if row[
        "flag_medium_gap"
    ]:
        flags.append(
            "MEDIUM_TRADING_GAP"
        )

    if row[
        "flag_long_gap"
    ]:
        flags.append(
            "LONG_TRADING_GAP"
        )

    if row[
        "flag_pending_corporate_action"
    ]:
        flags.append(
            "PENDING_CORPORATE_ACTION"
        )

    if row[
        "flag_confirmed_corporate_action"
    ]:
        flags.append(
            "CONFIRMED_CORPORATE_ACTION"
        )

    if row[
        "flag_confirmed_economic_corporate_action"
    ]:
        flags.append(
            "CONFIRMED_ECONOMIC_CORPORATE_ACTION"
        )

    if row[
        "flag_in_kind_corporate_action"
    ]:
        flags.append(
            "IN_KIND_CORPORATE_ACTION"
        )

    if row[
        "flag_possible_microliquidity"
    ]:
        flags.append(
            "POSSIBLE_MICROLIQUIDITY"
        )

    if not flags:
        return "NONE"

    return "|".join(
        flags
    )


# ============================================================
# ML quality status
# ============================================================

def add_quality_status(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Define status informativo.

    PASS:
        nenhum risco que exija atenção.

    REVIEW:
        risco de qualidade / liquidez /
        governança ainda não resolvida.

    Corporate Action CONFIRMED não gera
    REVIEW por si só.
    """

    result = dataframe.copy()

    result[
        "quality_flags"
    ] = result.apply(
        build_quality_flag_list,
        axis=1,
    )

    result[
        "ml_quality_status"
    ] = "PASS"

    review_mask = (
        result[
            "flag_pending_corporate_action"
        ]
        |
        result[
            "flag_long_gap"
        ]
        |
        result[
            "flag_possible_microliquidity"
        ]
    )

    result.loc[
        review_mask,
        "ml_quality_status",
    ] = "REVIEW"

    return result


# ============================================================
# Metadata
# ============================================================

def add_metadata(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "price_quality_version"
    ] = PRICE_QUALITY_VERSION

    result[
        "price_quality_source"
    ] = (
        "FII_CORPORATE_ACTION_ADJUSTED_PRICES_V3"
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
    required_schema_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price_raw",
        "close_price_adjusted",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        "cash_amount_per_unit_raw",
        "in_kind_amount_per_unit_raw",
        "corporate_action_value_per_unit_raw",

        "previous_trade_date",
        "previous_close_price_raw",

        "trading_gap_calendar_days",
        "trading_gap_sessions",
        "trading_gap_class",

        "review_status_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",

        "confirmed_event_type",
        "confirmed_in_kind_asset_ticker",

        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",

        "flag_pending_corporate_action",
        "flag_confirmed_corporate_action",
        "flag_confirmed_economic_corporate_action",
        "flag_in_kind_corporate_action",

        "flag_possible_microliquidity",

        "quality_flags",
        "ml_quality_status",

        "price_quality_version",
        "price_quality_source",
    ]

    missing_columns = [
        column
        for column in required_schema_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Saída possui colunas ausentes: "
            f"{missing_columns}"
        )

    non_nullable_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price_raw",
        "close_price_adjusted",

        "cash_amount_per_unit_raw",
        "in_kind_amount_per_unit_raw",
        "corporate_action_value_per_unit_raw",

        "trading_gap_class",

        "review_status_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",

        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",

        "flag_pending_corporate_action",
        "flag_confirmed_corporate_action",
        "flag_confirmed_economic_corporate_action",
        "flag_in_kind_corporate_action",

        "flag_possible_microliquidity",

        "quality_flags",
        "ml_quality_status",

        "price_quality_version",
        "price_quality_source",
    ]

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    unexpected_null_count = int(
        dataframe[
            non_nullable_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    #
    # A primeira observação de cada ticker
    # não possui sessão/preço anterior.
    #

    first_observation_mask = (
        dataframe[
            "previous_trade_date"
        ].isna()
    )

    first_observation_count = int(
        first_observation_mask.sum()
    )

    ticker_count = int(
        dataframe[
            "ticker"
        ].nunique()
    )

    null_economic_return_count = int(
        dataframe[
            "daily_return_economic"
        ]
        .isna()
        .sum()
    )

    null_raw_return_count = int(
        dataframe[
            "daily_return_raw"
        ]
        .isna()
        .sum()
    )

    null_adjusted_return_count = int(
        dataframe[
            "daily_return_adjusted_price"
        ]
        .isna()
        .sum()
    )

    null_previous_price_count = int(
        dataframe[
            "previous_close_price_raw"
        ]
        .isna()
        .sum()
    )

    null_gap_sessions_count = int(
        dataframe[
            "trading_gap_sessions"
        ]
        .isna()
        .sum()
    )

    null_gap_days_count = int(
        dataframe[
            "trading_gap_calendar_days"
        ]
        .isna()
        .sum()
    )

    unexpected_return_nulls = int(
        (
            dataframe[
                "daily_return_economic"
            ].isna()
            &
            dataframe[
                "previous_trade_date"
            ].notna()
        ).sum()
    )

    unexpected_raw_return_nulls = int(
        (
            dataframe[
                "daily_return_raw"
            ].isna()
            &
            dataframe[
                "previous_trade_date"
            ].notna()
        ).sum()
    )

    unexpected_adjusted_return_nulls = int(
        (
            dataframe[
                "daily_return_adjusted_price"
            ].isna()
            &
            dataframe[
                "previous_trade_date"
            ].notna()
        ).sum()
    )

    unexpected_previous_price_nulls = int(
        (
            dataframe[
                "previous_close_price_raw"
            ].isna()
            &
            dataframe[
                "previous_trade_date"
            ].notna()
        ).sum()
    )

    unexpected_gap_sessions_nulls = int(
        (
            dataframe[
                "trading_gap_sessions"
            ].isna()
            &
            dataframe[
                "previous_trade_date"
            ].notna()
        ).sum()
    )

    unexpected_gap_days_nulls = int(
        (
            dataframe[
                "trading_gap_calendar_days"
            ].isna()
            &
            dataframe[
                "previous_trade_date"
            ].notna()
        ).sum()
    )

    invalid_statuses = sorted(
        set(
            dataframe[
                "ml_quality_status"
            ].unique()
        )
        - {
            "PASS",
            "REVIEW",
        }
    )

    invalid_version = int(
        (
            dataframe[
                "price_quality_version"
            ]
            != PRICE_QUALITY_VERSION
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "price_quality_source"
            ]
            != (
                "FII_CORPORATE_ACTION_"
                "ADJUSTED_PRICES_V3"
            )
        ).sum()
    )

    pending_flag_count = int(
        dataframe[
            "flag_pending_corporate_action"
        ].sum()
    )

    confirmed_flag_count = int(
        dataframe[
            "flag_confirmed_corporate_action"
        ].sum()
    )

    economic_flag_count = int(
        dataframe[
            "flag_confirmed_economic_corporate_action"
        ].sum()
    )

    in_kind_flag_count = int(
        dataframe[
            "flag_in_kind_corporate_action"
        ].sum()
    )

    in_kind_payload_count = int(
        dataframe[
            "in_kind_amount_per_unit_raw"
        ]
        .gt(
            0
        )
        .sum()
    )

    in_kind_flag_mismatch = int(
        (
            dataframe[
                "flag_in_kind_corporate_action"
            ]
            != dataframe[
                "in_kind_amount_per_unit_raw"
            ]
            .gt(
                0
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Price Quality v2"
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
        f"{ticker_count:,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Nulos inesperados em campos "
        f"obrigatórios: "
        f"{unexpected_null_count:,}"
    )

    print(
        "\nNULLs estruturais esperados:"
    )

    print(
        "  Primeiras observações: "
        f"{first_observation_count:,}"
    )

    print(
        "  daily_return_raw: "
        f"{null_raw_return_count:,}"
    )

    print(
        "  daily_return_adjusted_price: "
        f"{null_adjusted_return_count:,}"
    )

    print(
        "  daily_return_economic: "
        f"{null_economic_return_count:,}"
    )

    print(
        "  previous_close_price_raw: "
        f"{null_previous_price_count:,}"
    )

    print(
        "  trading_gap_sessions: "
        f"{null_gap_sessions_count:,}"
    )

    print(
        "  trading_gap_calendar_days: "
        f"{null_gap_days_count:,}"
    )

    print(
        "\nNULLs estruturais inesperados:"
    )

    print(
        "  daily_return_raw: "
        f"{unexpected_raw_return_nulls:,}"
    )

    print(
        "  daily_return_adjusted_price: "
        f"{unexpected_adjusted_return_nulls:,}"
    )

    print(
        "  daily_return_economic: "
        f"{unexpected_return_nulls:,}"
    )

    print(
        "  previous_close_price_raw: "
        f"{unexpected_previous_price_nulls:,}"
    )

    print(
        "  trading_gap_sessions: "
        f"{unexpected_gap_sessions_nulls:,}"
    )

    print(
        "  trading_gap_calendar_days: "
        f"{unexpected_gap_days_nulls:,}"
    )

    print(
        "\nCorporate Action flags:"
    )

    print(
        "  Confirmed: "
        f"{confirmed_flag_count:,}"
    )

    print(
        "  Confirmed economic: "
        f"{economic_flag_count:,}"
    )

    print(
        "  In-kind: "
        f"{in_kind_flag_count:,}"
    )

    print(
        "  In-kind payload rows: "
        f"{in_kind_payload_count:,}"
    )

    print(
        "  In-kind flag mismatch: "
        f"{in_kind_flag_mismatch:,}"
    )

    print(
        "  Pending: "
        f"{pending_flag_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Saída possui duplicidades."
        )

    if unexpected_null_count > 0:
        raise ValueError(
            "Saída possui NULL inesperado "
            "em campo obrigatório."
        )

    if (
        first_observation_count
        != ticker_count
    ):
        raise ValueError(
            "Quantidade de primeiras "
            "observações diverge da quantidade "
            "de tickers."
        )

    if unexpected_raw_return_nulls > 0:
        raise ValueError(
            "daily_return_raw possui NULL "
            "fora da primeira observação "
            "do ticker."
        )

    if unexpected_adjusted_return_nulls > 0:
        raise ValueError(
            "daily_return_adjusted_price possui "
            "NULL fora da primeira observação "
            "do ticker."
        )

    if unexpected_return_nulls > 0:
        raise ValueError(
            "daily_return_economic possui "
            "NULL fora da primeira observação "
            "do ticker."
        )

    if unexpected_previous_price_nulls > 0:
        raise ValueError(
            "previous_close_price_raw possui "
            "NULL fora da primeira observação "
            "do ticker."
        )

    if unexpected_gap_sessions_nulls > 0:
        raise ValueError(
            "trading_gap_sessions possui "
            "NULL fora da primeira observação "
            "do ticker."
        )

    if unexpected_gap_days_nulls > 0:
        raise ValueError(
            "trading_gap_calendar_days possui "
            "NULL fora da primeira observação "
            "do ticker."
        )

    if invalid_statuses:
        raise ValueError(
            "ml_quality_status inválidos: "
            f"{invalid_statuses}"
        )

    if invalid_version > 0:
        raise ValueError(
            "price_quality_version inválida."
        )

    if invalid_source > 0:
        raise ValueError(
            "price_quality_source inválida."
        )

    if pending_flag_count > 0:
        raise ValueError(
            "Price Quality v2 recebeu "
            "Corporate Action pendente."
        )

    if in_kind_flag_mismatch > 0:
        raise ValueError(
            "flag_in_kind_corporate_action "
            "inconsistente com o payload "
            "econômico."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Summary
# ============================================================

def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Resumo - FII Price Quality"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{PRICE_QUALITY_VERSION}"
    )

    print(
        "Source: "
        "FII_CORPORATE_ACTION_ADJUSTED_PRICES_V3"
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
        "\nML Quality Status:"
    )

    for value, count in (
        dataframe[
            "ml_quality_status"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nFlags:"
    )

    flag_columns = [
        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",

        "flag_pending_corporate_action",
        "flag_confirmed_corporate_action",
        "flag_confirmed_economic_corporate_action",
        "flag_in_kind_corporate_action",

        "flag_possible_microliquidity",
    ]

    for column in flag_columns:
        count = int(
            dataframe[
                column
            ].sum()
        )

        print(
            f"  {column}: "
            f"{count:,}"
        )

    review = dataframe[
        dataframe[
            "ml_quality_status"
        ]
        .eq(
            "REVIEW"
        )
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Amostra - REVIEW"
    )
    print(
        "======================================"
    )

    if review.empty:
        print(
            "Nenhuma linha em REVIEW."
        )

    else:
        display = review[
            [
                "ticker",
                "previous_trade_date",
                "trade_date",
                "trading_gap_sessions",
                "trading_gap_class",
                "close_price_raw",
                "daily_return_economic",
                "quality_flags",
            ]
        ].copy()

        display[
            "daily_return_economic"
        ] = (
            display[
                "daily_return_economic"
            ]
            * 100
        )

        display = display.sort_values(
            [
                "trade_date",
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
# Output contract
# ============================================================

def select_output_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price_raw",
        "close_price_adjusted",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        #
        # Economic Corporate Action context
        #
        "cash_amount_per_unit_raw",
        "in_kind_amount_per_unit_raw",
        "corporate_action_value_per_unit_raw",

        "confirmed_event_type",
        "confirmed_in_kind_asset_ticker",

        #
        # Trading continuity
        #
        "previous_trade_date",
        "previous_close_price_raw",

        "trading_gap_calendar_days",
        "trading_gap_sessions",
        "trading_gap_class",

        #
        # Governance context
        #
        "review_status_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",

        #
        # Quality flags
        #
        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",

        "flag_pending_corporate_action",
        "flag_confirmed_corporate_action",
        "flag_confirmed_economic_corporate_action",
        "flag_in_kind_corporate_action",

        "flag_possible_microliquidity",

        "quality_flags",
        "ml_quality_status",

        #
        # Metadata
        #
        "price_quality_version",
        "price_quality_source",
        "created_at",
    ]

    return dataframe[
        columns
    ].copy()


# ============================================================
# Main
# ============================================================

def main() -> None:
    print(
        "Construindo camada "
        "FII Price Quality..."
    )

    print(
        f"Version: "
        f"{PRICE_QUALITY_VERSION}"
    )

    print(
        "Expected source: "
        "Adjusted Prices v3"
    )

    dataframe = load_source()

    validate_source(
        dataframe
    )

    calendar = build_global_calendar(
        dataframe
    )

    dataframe = (
        add_previous_trade_information(
            dataframe
        )
    )

    dataframe = add_gap_metrics(
        dataframe=dataframe,
        calendar=calendar,
    )

    dataframe = add_quality_flags(
        dataframe
    )

    dataframe = add_quality_status(
        dataframe
    )

    dataframe = add_metadata(
        dataframe
    )

    validate_output(
        dataframe
    )

    output = select_output_columns(
        dataframe
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
        output
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "Price Quality v2 consome "
        "Adjusted Prices v3."
    )

    print(
        "daily_return_economic continua "
        "sendo a referência para detectar "
        "retornos extremos."
    )

    print(
        "Corporate Actions confirmados não "
        "são tratados automaticamente como "
        "falha de qualidade."
    )

    print(
        "Eventos econômicos e in-kind "
        "permanecem explicitamente "
        "identificáveis."
    )

    print(
        "Nenhuma linha foi removida."
    )

    print(
        "NULLs da primeira observação "
        "de cada ticker foram preservados "
        "intencionalmente."
    )

    print(
        "ml_quality_status continua sendo "
        "sinalização e não exclusão "
        "automática do ML."
    )


if __name__ == "__main__":
    main()