from __future__ import annotations

from datetime import datetime, timezone
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


PRICE_QUALITY_VERSION = "v1"

EXTREME_RETURN_THRESHOLD = 0.50
LOW_PRICE_THRESHOLD = 1.00

SHORT_GAP_MAX_SESSIONS = 5
MEDIUM_GAP_MAX_SESSIONS = 20


def load_source() -> pd.DataFrame:
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


def validate_source(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price_raw",
        "close_price_adjusted",
        "daily_return_economic",
        "review_status_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",
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

    invalid_prices = int(
        (
            dataframe[
                "close_price_raw"
            ]
            <= 0
        ).sum()
    )

    non_finite_returns = int(
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
        f"Preços inválidos: "
        f"{invalid_prices:,}"
    )

    print(
        "Retornos econômicos "
        f"não finitos: {non_finite_returns:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Fonte possui duplicidades."
        )

    if invalid_prices > 0:
        raise ValueError(
            "Fonte possui preços inválidos."
        )

    if non_finite_returns > 0:
        raise ValueError(
            "Fonte possui retorno econômico "
            "não finito."
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

    current_calendar = calendar.rename(
        columns={
            "global_session_index": (
                "current_session_index"
            )
        }
    )

    previous_calendar = calendar.rename(
        columns={
            "trade_date": (
                "previous_trade_date"
            ),
            "global_session_index": (
                "previous_session_index"
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


def add_quality_flags(
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


def build_quality_flag_list(
    row: pd.Series,
) -> str:
    flags = []

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


def add_quality_status(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
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

    #
    # Nesta versão não existe FAIL.
    #
    # Estamos apenas sinalizando riscos
    # de qualidade. Nenhuma linha é
    # excluída automaticamente do ML.
    #

    return result


def add_metadata(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "price_quality_version"
    ] = PRICE_QUALITY_VERSION

    result[
        "created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


def validate_output(
    dataframe: pd.DataFrame,
) -> None:
    required_schema_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price_raw",
        "daily_return_economic",
        "previous_trade_date",
        "previous_close_price_raw",
        "trading_gap_calendar_days",
        "trading_gap_sessions",
        "trading_gap_class",
        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",
        "flag_pending_corporate_action",
        "flag_confirmed_corporate_action",
        "flag_possible_microliquidity",
        "quality_flags",
        "ml_quality_status",
        "price_quality_version",
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

    #
    # Campos que realmente nunca podem
    # possuir NULL.
    #
    non_nullable_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price_raw",
        "trading_gap_class",
        "flag_extreme_return",
        "flag_low_price",
        "flag_short_gap",
        "flag_medium_gap",
        "flag_long_gap",
        "flag_pending_corporate_action",
        "flag_confirmed_corporate_action",
        "flag_possible_microliquidity",
        "quality_flags",
        "ml_quality_status",
        "price_quality_version",
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
    # Portanto esses NULLs são legítimos.
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
        ].isna().sum()
    )

    null_previous_price_count = int(
        dataframe[
            "previous_close_price_raw"
        ].isna().sum()
    )

    null_gap_sessions_count = int(
        dataframe[
            "trading_gap_sessions"
        ].isna().sum()
    )

    null_gap_days_count = int(
        dataframe[
            "trading_gap_calendar_days"
        ].isna().sum()
    )

    #
    # Retorno econômico nulo somente é
    # permitido na primeira observação
    # de cada ticker.
    #
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

    #
    # Da mesma forma, quando já existe
    # previous_trade_date, esperamos
    # previous_close e métricas de gap.
    #
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
        f"{ticker_count:,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Nulos inesperados em campos "
        f"obrigatórios: {unexpected_null_count:,}"
    )

    print(
        "\nNULLs estruturais esperados:"
    )

    print(
        "  Primeiras observações: "
        f"{first_observation_count:,}"
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

    if duplicate_count > 0:
        raise ValueError(
            "Saída possui duplicidades."
        )

    if unexpected_null_count > 0:
        raise ValueError(
            "Saída possui NULL inesperado "
            "em campo obrigatório."
        )

    #
    # Deve existir exatamente uma primeira
    # observação por ticker.
    #
    if (
        first_observation_count
        != ticker_count
    ):
        raise ValueError(
            "Quantidade de primeiras "
            "observações diverge da quantidade "
            "de tickers."
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

    print(
        "\nData Quality aprovada."
    )


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
        == "REVIEW"
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
        "daily_return_economic",

        "previous_trade_date",
        "previous_close_price_raw",

        "trading_gap_calendar_days",
        "trading_gap_sessions",
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
        "flag_possible_microliquidity",

        "quality_flags",
        "ml_quality_status",

        "price_quality_version",
        "created_at",
    ]

    return dataframe[
        columns
    ].copy()


def main() -> None:
    print(
        "Construindo camada FII Price Quality..."
    )

    print(
        f"Version: "
        f"{PRICE_QUALITY_VERSION}"
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
        "Nenhuma linha foi removida."
    )

    print(
        "NULLs da primeira observação "
        "de cada ticker foram preservados "
        "intencionalmente."
    )

    print(
        "ml_quality_status é apenas "
        "sinalização nesta versão."
    )


if __name__ == "__main__":
    main()