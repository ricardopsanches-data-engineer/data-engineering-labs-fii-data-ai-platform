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


TARGET_CASES = [
    ("RCFA11", "2025-09-02"),
    ("RCFA11", "2026-08-26"),
    ("IBBP11", "2025-10-30"),
    ("SJAU11", "2025-12-22"),
    ("PNRC11", "2026-06-15"),
]


RECENT_WINDOWS = [
    5,
    20,
]


def load_adjusted_prices() -> pd.DataFrame:
    if not ADJUSTED_PRICES_PATH.exists():
        raise FileNotFoundError(
            "Adjusted Prices não encontrado: "
            f"{ADJUSTED_PRICES_PATH}"
        )

    print(
        "Carregando Corporate Action "
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


def load_price_history() -> pd.DataFrame:
    if not PRICE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "FII Price History não encontrado: "
            f"{PRICE_HISTORY_PATH}"
        )

    print(
        "Carregando FII Price History..."
    )

    dataframe = pd.read_parquet(
        PRICE_HISTORY_PATH
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


def load_price_quality() -> pd.DataFrame:
    if not PRICE_QUALITY_PATH.exists():
        raise FileNotFoundError(
            "FII Price Quality não encontrado: "
            f"{PRICE_QUALITY_PATH}"
        )

    print(
        "Carregando FII Price Quality..."
    )

    dataframe = pd.read_parquet(
        PRICE_QUALITY_PATH
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
    required_columns = [
        "trade_date",
        "ticker",
        "close_price",
        "trades_quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        print(
            "\nColunas disponíveis no "
            "FII Price History:"
        )

        for column in dataframe.columns:
            print(
                f"  {column}"
            )

        raise ValueError(
            "FII Price History não possui "
            "as colunas necessárias para "
            "o diagnóstico de liquidez: "
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

    invalid_trades = int(
        (
            dataframe[
                "trades_quantity"
            ].notna()
            &
            (
                dataframe[
                    "trades_quantity"
                ]
                < 0
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
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "trades_quantity inválidos: "
        f"{invalid_trades:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price History possui duplicidades."
        )

    if invalid_trades > 0:
        raise ValueError(
            "Price History possui "
            "trades_quantity inválido."
        )

    print(
        "\nData Quality aprovada."
    )


def build_global_calendar(
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
        "session_index"
    ] = np.arange(
        len(calendar),
        dtype=np.int64,
    )

    return calendar


def add_liquidity_metrics(
    price_history: pd.DataFrame,
) -> pd.DataFrame:
    result = price_history.sort_values(
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
        "previous_close_price"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "close_price"
        ]
        .shift(1)
    )

    result[
        "previous_trades_quantity"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "trades_quantity"
        ]
        .shift(1)
    )

    for window in RECENT_WINDOWS:
        result[
            f"trades_avg_prev_{window}"
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
            )[
                "trades_quantity"
            ]
            .transform(
                lambda series: (
                    series
                    .shift(1)
                    .rolling(
                        window=window,
                        min_periods=1,
                    )
                    .mean()
                )
            )
        )

        result[
            f"trades_median_prev_{window}"
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
            )[
                "trades_quantity"
            ]
            .transform(
                lambda series: (
                    series
                    .shift(1)
                    .rolling(
                        window=window,
                        min_periods=1,
                    )
                    .median()
                )
            )
        )

        result[
            f"price_volatility_prev_{window}"
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
            )[
                "close_price"
            ]
            .transform(
                lambda series: (
                    series
                    .pct_change(
                        fill_method=None
                    )
                    .shift(1)
                    .rolling(
                        window=window,
                        min_periods=2,
                    )
                    .std()
                )
            )
        )

    return result


def add_gap_sessions(
    dataframe: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    current_calendar = (
        calendar.rename(
            columns={
                "session_index": (
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
                "session_index": (
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

    return result


def build_target_cases() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "trade_date": (
                    pd.Timestamp(
                        trade_date
                    )
                ),
            }
            for ticker, trade_date
            in TARGET_CASES
        ]
    )


def build_case_dataset(
    adjusted_prices: pd.DataFrame,
    price_history: pd.DataFrame,
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    target_cases = (
        build_target_cases()
    )

    liquidity_columns = [
        "ticker",
        "trade_date",
        "close_price",
        "trades_quantity",
        "previous_trade_date",
        "previous_close_price",
        "previous_trades_quantity",
        "trading_gap_sessions",
        "trading_gap_calendar_days",
        "trades_avg_prev_5",
        "trades_median_prev_5",
        "trades_avg_prev_20",
        "trades_median_prev_20",
        "price_volatility_prev_5",
        "price_volatility_prev_20",
    ]

    liquidity = price_history[
        liquidity_columns
    ].copy()

    adjusted_columns = [
        "ticker",
        "trade_date",
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
        "review_status_on_date",
        "event_type_on_date",
        "pending_review_on_date",
    ]

    adjusted = adjusted_prices[
        adjusted_columns
    ].copy()

    quality_columns = [
        "ticker",
        "trade_date",
        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",
        "flag_pending_corporate_action",
        "flag_possible_microliquidity",
        "quality_flags",
        "ml_quality_status",
    ]

    quality = price_quality[
        quality_columns
    ].copy()

    result = target_cases.merge(
        liquidity,
        how="left",
        on=[
            "ticker",
            "trade_date",
        ],
        validate="one_to_one",
    )

    result = result.merge(
        adjusted,
        how="left",
        on=[
            "ticker",
            "trade_date",
        ],
        validate="one_to_one",
    )

    result = result.merge(
        quality,
        how="left",
        on=[
            "ticker",
            "trade_date",
        ],
        validate="one_to_one",
    )

    missing_cases = result[
        "close_price"
    ].isna()

    if missing_cases.any():
        raise ValueError(
            "Alguns target cases não foram "
            "encontrados:\n"
            f"{result.loc[missing_cases, ['ticker', 'trade_date']].to_string(index=False)}"
        )

    return result


def add_relative_liquidity_metrics(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "trades_vs_avg5_ratio"
    ] = (
        result[
            "trades_quantity"
        ]
        / result[
            "trades_avg_prev_5"
        ].replace(
            0,
            np.nan,
        )
    )

    result[
        "trades_vs_avg20_ratio"
    ] = (
        result[
            "trades_quantity"
        ]
        / result[
            "trades_avg_prev_20"
        ].replace(
            0,
            np.nan,
        )
    )

    return result


def build_diagnostic_classification(
    row: pd.Series,
) -> tuple[str, str]:
    gap_sessions = row[
        "trading_gap_sessions"
    ]

    price = row[
        "close_price"
    ]

    trades = row[
        "trades_quantity"
    ]

    extreme_return = abs(
        row[
            "daily_return_economic"
        ]
    )

    if (
        pd.notna(
            gap_sessions
        )
        and gap_sessions > 20
    ):
        return (
            "STRONG_LIQUIDITY_GAP_SIGNAL",
            (
                "Movimento cruza mais de "
                "20 sessões B3 sem negócio."
            ),
        )

    if (
        pd.notna(
            price
        )
        and price <= 1.00
        and extreme_return >= 0.50
    ):
        return (
            "STRONG_MICROLIQUIDITY_SIGNAL",
            (
                "Preço muito baixo combinado "
                "com retorno extremo."
            ),
        )

    if (
        pd.notna(
            trades
        )
        and trades <= 5
        and extreme_return >= 0.50
    ):
        return (
            "LOW_TRADING_ACTIVITY_SIGNAL",
            (
                "Pouquíssimos negócios na "
                "sessão do movimento extremo."
            ),
        )

    return (
        "UNRESOLVED",
        (
            "Liquidez/gap não explicam "
            "sozinhos o movimento."
        ),
    )


def add_diagnostic_classification(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    classifications = result.apply(
        build_diagnostic_classification,
        axis=1,
    )

    result[
        "diagnostic_classification"
    ] = [
        value[0]
        for value in classifications
    ]

    result[
        "diagnostic_reason"
    ] = [
        value[1]
        for value in classifications
    ]

    return result


def print_case(
    row: pd.Series,
) -> None:
    print(
        "\n--------------------------------------"
    )

    print(
        f"{row['ticker']} | "
        f"{row['trade_date'].date()}"
    )

    print(
        "--------------------------------------"
    )

    print(
        "Previous trade date: "
        f"{row['previous_trade_date']}"
    )

    print(
        "Trading gap sessions: "
        f"{row['trading_gap_sessions']}"
    )

    print(
        "Trading gap calendar days: "
        f"{row['trading_gap_calendar_days']}"
    )

    print(
        "\nPreço:"
    )

    print(
        "  Previous close: "
        f"{row['previous_close_price']}"
    )

    print(
        "  Close: "
        f"{row['close_price']}"
    )

    print(
        "  Economic return: "
        f"{row['daily_return_economic'] * 100:.4f}%"
    )

    print(
        "\nNegociações:"
    )

    print(
        "  Trades na sessão: "
        f"{row['trades_quantity']}"
    )

    print(
        "  Trades sessão anterior: "
        f"{row['previous_trades_quantity']}"
    )

    print(
        "  Média trades anteriores 5: "
        f"{row['trades_avg_prev_5']:.2f}"
        if pd.notna(
            row[
                "trades_avg_prev_5"
            ]
        )
        else
        "  Média trades anteriores 5: N/A"
    )

    print(
        "  Mediana trades anteriores 5: "
        f"{row['trades_median_prev_5']:.2f}"
        if pd.notna(
            row[
                "trades_median_prev_5"
            ]
        )
        else
        "  Mediana trades anteriores 5: N/A"
    )

    print(
        "  Média trades anteriores 20: "
        f"{row['trades_avg_prev_20']:.2f}"
        if pd.notna(
            row[
                "trades_avg_prev_20"
            ]
        )
        else
        "  Média trades anteriores 20: N/A"
    )

    print(
        "  Trades / avg5: "
        f"{row['trades_vs_avg5_ratio']:.2f}x"
        if pd.notna(
            row[
                "trades_vs_avg5_ratio"
            ]
        )
        else
        "  Trades / avg5: N/A"
    )

    print(
        "  Trades / avg20: "
        f"{row['trades_vs_avg20_ratio']:.2f}x"
        if pd.notna(
            row[
                "trades_vs_avg20_ratio"
            ]
        )
        else
        "  Trades / avg20: N/A"
    )

    print(
        "\nVolatilidade histórica anterior:"
    )

    print(
        "  5 sessões: "
        f"{row['price_volatility_prev_5'] * 100:.4f}%"
        if pd.notna(
            row[
                "price_volatility_prev_5"
            ]
        )
        else
        "  5 sessões: N/A"
    )

    print(
        "  20 sessões: "
        f"{row['price_volatility_prev_20'] * 100:.4f}%"
        if pd.notna(
            row[
                "price_volatility_prev_20"
            ]
        )
        else
        "  20 sessões: N/A"
    )

    print(
        "\nPrice Quality:"
    )

    print(
        f"  {row['quality_flags']}"
    )

    print(
        "  ML status: "
        f"{row['ml_quality_status']}"
    )

    print(
        "\nDiagnóstico automático:"
    )

    print(
        "  Classification: "
        f"{row['diagnostic_classification']}"
    )

    print(
        "  Reason: "
        f"{row['diagnostic_reason']}"
    )


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Resumo - 5 Pending Cases"
    )
    print(
        "======================================"
    )

    for classification, count in (
        dataframe[
            "diagnostic_classification"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {classification}: "
            f"{count}"
        )

    print(
        "\nMatriz resumida:"
    )

    display = dataframe[
        [
            "ticker",
            "trade_date",
            "trading_gap_sessions",
            "close_price",
            "trades_quantity",
            "daily_return_economic",
            "diagnostic_classification",
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
        "Diagnosticando os 5 Corporate "
        "Action cases pendentes..."
    )

    adjusted_prices = (
        load_adjusted_prices()
    )

    price_history = (
        load_price_history()
    )

    validate_price_history(
        price_history
    )

    price_quality = (
        load_price_quality()
    )

    calendar = (
        build_global_calendar(
            adjusted_prices
        )
    )

    price_history = (
        add_liquidity_metrics(
            price_history
        )
    )

    price_history = (
        add_gap_sessions(
            dataframe=price_history,
            calendar=calendar,
        )
    )

    cases = build_case_dataset(
        adjusted_prices=adjusted_prices,
        price_history=price_history,
        price_quality=price_quality,
    )

    cases = (
        add_relative_liquidity_metrics(
            cases
        )
    )

    cases = (
        add_diagnostic_classification(
            cases
        )
    )

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico individual"
    )
    print(
        "======================================"
    )

    for _, row in (
        cases.sort_values(
            [
                "trade_date",
                "ticker",
            ]
        ).iterrows()
    ):
        print_case(
            row
        )

    print_summary(
        cases
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
        "Nenhuma decisão de corporate action "
        "foi alterada automaticamente."
    )

    print(
        "Nenhum dado foi removido."
    )


if __name__ == "__main__":
    main()