from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ADJUSTED_PRICES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
    / "fii_corporate_action_adjusted_prices.parquet"
)

DISCONTINUITIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_discontinuities"
    / "fii_price_discontinuities.parquet"
)

EXTREME_RETURN_THRESHOLD = 0.50


def load_adjusted_prices() -> pd.DataFrame:
    if not ADJUSTED_PRICES_PATH.exists():
        raise FileNotFoundError(
            "Adjusted Prices não encontrado: "
            f"{ADJUSTED_PRICES_PATH}"
        )

    dataframe = pd.read_parquet(
        ADJUSTED_PRICES_PATH
    )

    dataframe["trade_date"] = pd.to_datetime(
        dataframe["trade_date"]
    )

    dataframe["ticker"] = (
        dataframe["ticker"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return dataframe


def load_discontinuities() -> pd.DataFrame:
    if not DISCONTINUITIES_PATH.exists():
        raise FileNotFoundError(
            "Price Discontinuities não encontrado: "
            f"{DISCONTINUITIES_PATH}"
        )

    dataframe = pd.read_parquet(
        DISCONTINUITIES_PATH
    )

    dataframe["event_date"] = pd.to_datetime(
        dataframe["event_date"]
    )

    dataframe["previous_trade_date"] = pd.to_datetime(
        dataframe["previous_trade_date"]
    )

    dataframe["ticker"] = (
        dataframe["ticker"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return dataframe


def validate_source(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "trade_date",
        "ticker",
        "close_price_raw",
        "close_price_adjusted",
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
        "review_status_on_date",
        "pending_review_on_date",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Adjusted Prices possui colunas ausentes: "
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

    non_finite_economic = int(
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
        "Não finitos em "
        "daily_return_economic: "
        f"{non_finite_economic:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Fonte possui duplicidades."
        )

    if non_finite_economic > 0:
        raise ValueError(
            "Fonte possui retorno econômico "
            "não finito."
        )

    print(
        "\nData Quality aprovada."
    )


def build_global_session_index(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
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
        "previous_trade_date_calculated"
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
        "previous_close_price_raw_calculated"
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


def add_trading_gap_metrics(
    dataframe: pd.DataFrame,
    global_calendar: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "trading_gap_calendar_days"
    ] = (
        result[
            "trade_date"
        ]
        - result[
            "previous_trade_date_calculated"
        ]
    ).dt.days

    current_calendar = global_calendar.rename(
        columns={
            "global_session_index": (
                "current_global_session_index"
            )
        }
    )

    previous_calendar = global_calendar.rename(
        columns={
            "trade_date": (
                "previous_trade_date_calculated"
            ),
            "global_session_index": (
                "previous_global_session_index"
            ),
        }
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
        on="previous_trade_date_calculated",
        validate="many_to_one",
    )

    result[
        "trading_gap_sessions"
    ] = (
        result[
            "current_global_session_index"
        ]
        - result[
            "previous_global_session_index"
        ]
    )

    return result


def attach_discontinuity_metadata(
    dataframe: pd.DataFrame,
    discontinuities: pd.DataFrame,
) -> pd.DataFrame:
    metadata_columns = [
        "ticker",
        "event_date",
        "previous_trade_date",
        "classification",
        "confidence",
        "review_status",
        "event_type",
        "factor_match",
        "nearest_common_factor",
        "factor_relative_error",
        "is_confirmed_corporate_action",
    ]

    available_columns = [
        column
        for column in metadata_columns
        if column in discontinuities.columns
    ]

    metadata = discontinuities[
        available_columns
    ].copy()

    metadata = metadata.rename(
        columns={
            "event_date": "trade_date",
            "previous_trade_date": (
                "detector_previous_trade_date"
            ),
            "classification": (
                "detector_classification"
            ),
            "confidence": (
                "detector_confidence"
            ),
            "review_status": (
                "detector_review_status"
            ),
            "event_type": (
                "detector_event_type"
            ),
            "factor_match": (
                "detector_factor_match"
            ),
            "nearest_common_factor": (
                "detector_nearest_common_factor"
            ),
            "factor_relative_error": (
                "detector_factor_relative_error"
            ),
            "is_confirmed_corporate_action": (
                "detector_confirmed_action"
            ),
        }
    )

    result = dataframe.merge(
        metadata,
        how="left",
        on=[
            "ticker",
            "trade_date",
        ],
        validate="one_to_one",
    )

    return result


def build_extremes(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    valid = dataframe[
        dataframe[
            "daily_return_economic"
        ].notna()
    ].copy()

    extremes = valid[
        valid[
            "daily_return_economic"
        ].abs()
        >= EXTREME_RETURN_THRESHOLD
    ].copy()

    extremes[
        "absolute_economic_return"
    ] = extremes[
        "daily_return_economic"
    ].abs()

    return extremes.sort_values(
        [
            "absolute_economic_return",
            "trade_date",
            "ticker",
        ],
        ascending=[
            False,
            True,
            True,
        ],
    )


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

    if sessions <= 5:
        return "SHORT_GAP"

    if sessions <= 20:
        return "MEDIUM_GAP"

    return "LONG_GAP"


def add_gap_classification(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "trading_gap_class"
    ] = result[
        "trading_gap_sessions"
    ].map(
        classify_gap
    )

    return result


def print_summary(
    extremes: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Resumo - Extremos Econômicos"
    )
    print(
        "======================================"
    )

    print(
        "Threshold: "
        f">= {EXTREME_RETURN_THRESHOLD * 100:.0f}%"
    )

    print(
        f"Eventos extremos: "
        f"{len(extremes):,}"
    )

    print(
        f"Tickers afetados: "
        f"{extremes['ticker'].nunique():,}"
    )

    pending_count = int(
        (
            extremes[
                "detector_review_status"
            ]
            == "PENDING_REVIEW"
        ).sum()
    )

    not_applicable_count = int(
        (
            extremes[
                "detector_review_status"
            ]
            == "NOT_APPLICABLE"
        ).sum()
    )

    no_detector_count = int(
        extremes[
            "detector_review_status"
        ].isna().sum()
    )

    print(
        "\nDetector status:"
    )

    print(
        f"  PENDING_REVIEW: "
        f"{pending_count:,}"
    )

    print(
        f"  NOT_APPLICABLE: "
        f"{not_applicable_count:,}"
    )

    print(
        f"  Sem evento no detector: "
        f"{no_detector_count:,}"
    )

    print(
        "\nTrading gap:"
    )

    for value, count in (
        extremes[
            "trading_gap_class"
        ]
        .value_counts(
            dropna=False
        )
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )


def print_extreme_table(
    extremes: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Eventos extremos remanescentes"
    )
    print(
        "======================================"
    )

    display = extremes[
        [
            "ticker",
            "previous_trade_date_calculated",
            "trade_date",
            "trading_gap_calendar_days",
            "trading_gap_sessions",
            "trading_gap_class",
            "previous_close_price_raw_calculated",
            "close_price_raw",
            "daily_return_raw",
            "daily_return_adjusted_price",
            "daily_return_economic",
            "detector_classification",
            "detector_confidence",
            "detector_review_status",
            "detector_event_type",
            "detector_factor_match",
            "detector_nearest_common_factor",
            "detector_confirmed_action",
        ]
    ].copy()

    for column in [
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
    ]:
        display[
            column
        ] = (
            display[
                column
            ]
            * 100
        )

    print(
        display.to_string(
            index=False
        )
    )


def print_long_gap_extremes(
    extremes: pd.DataFrame,
) -> None:
    long_gap = extremes[
        extremes[
            "trading_gap_class"
        ]
        == "LONG_GAP"
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Extremos com LONG_GAP"
    )
    print(
        "======================================"
    )

    print(
        f"Eventos: "
        f"{len(long_gap):,}"
    )

    if long_gap.empty:
        return

    display = long_gap[
        [
            "ticker",
            "previous_trade_date_calculated",
            "trade_date",
            "trading_gap_calendar_days",
            "trading_gap_sessions",
            "daily_return_economic",
            "detector_review_status",
            "detector_classification",
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

    print(
        display.to_string(
            index=False
        )
    )


def print_detector_escape_cases(
    extremes: pd.DataFrame,
) -> None:
    escaped = extremes[
        extremes[
            "detector_review_status"
        ].ne(
            "PENDING_REVIEW"
        )
        |
        extremes[
            "detector_review_status"
        ].isna()
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Extremos fora de PENDING_REVIEW"
    )
    print(
        "======================================"
    )

    print(
        f"Eventos: "
        f"{len(escaped):,}"
    )

    if escaped.empty:
        return

    display = escaped[
        [
            "ticker",
            "trade_date",
            "daily_return_economic",
            "trading_gap_sessions",
            "trading_gap_class",
            "detector_classification",
            "detector_confidence",
            "detector_review_status",
            "detector_factor_match",
            "detector_nearest_common_factor",
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

    print(
        display.to_string(
            index=False
        )
    )


def main() -> None:
    print(
        "Diagnosticando retornos econômicos "
        "extremos remanescentes..."
    )

    adjusted_prices = (
        load_adjusted_prices()
    )

    validate_source(
        adjusted_prices
    )

    discontinuities = (
        load_discontinuities()
    )

    global_calendar = (
        build_global_session_index(
            adjusted_prices
        )
    )

    enriched = (
        add_previous_trade_information(
            adjusted_prices
        )
    )

    enriched = (
        add_trading_gap_metrics(
            dataframe=enriched,
            global_calendar=global_calendar,
        )
    )

    enriched = (
        attach_discontinuity_metadata(
            dataframe=enriched,
            discontinuities=discontinuities,
        )
    )

    extremes = (
        build_extremes(
            enriched
        )
    )

    extremes = (
        add_gap_classification(
            extremes
        )
    )

    print_summary(
        extremes
    )

    print_extreme_table(
        extremes
    )

    print_long_gap_extremes(
        extremes
    )

    print_detector_escape_cases(
        extremes
    )

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico concluído"
    )
    print(
        "======================================"
    )

    print(
        "Nenhum dado foi alterado."
    )

    print(
        "Este script mede extremos, "
        "gaps de negociação e falhas "
        "de cobertura do detector."
    )


if __name__ == "__main__":
    main()