from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

DISCONTINUITIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_discontinuities"
    / "fii_price_discontinuities.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_corporate_action_adjusted_prices.parquet"
)


ADJUSTED_PRICES_VERSION = "v1"


STRUCTURAL_EVENT_TYPES = {
    "SPLIT",
    "REVERSE_SPLIT",
}

CASH_EVENT_TYPES = {
    "AMORTIZATION",
}


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
        PRICE_HISTORY_PATH,
        columns=[
            "trade_date",
            "ticker",
            "cnpj",
            "codigo_cvm",
            "close_price",
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


def load_discontinuities() -> pd.DataFrame:
    if not DISCONTINUITIES_PATH.exists():
        raise FileNotFoundError(
            "FII Price Discontinuities não encontrado: "
            f"{DISCONTINUITIES_PATH}"
        )

    print(
        "Carregando FII Price Discontinuities..."
    )

    dataframe = pd.read_parquet(
        DISCONTINUITIES_PATH
    )

    required_columns = [
        "ticker",
        "event_date",
        "review_status",
        "event_type",
        "quantity_multiplier",
        "price_adjustment_factor",
        "cash_amount_per_unit",
        "confirmation_source",
        "confirmation_date",
        "is_confirmed_corporate_action",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price Discontinuities possui "
            "schema incompatível."
            "\nColunas ausentes: "
            f"{missing_columns}"
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

    dataframe[
        "event_date"
    ] = pd.to_datetime(
        dataframe[
            "event_date"
        ]
    )

    dataframe[
        "confirmation_date"
    ] = pd.to_datetime(
        dataframe[
            "confirmation_date"
        ],
        errors="coerce",
    )

    return dataframe


def validate_price_history(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price History possui "
            f"colunas ausentes: {missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "trade_date",
                "ticker",
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

    invalid_prices = int(
        (
            dataframe[
                "close_price"
            ]
            <= 0
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
        f"Nulos obrigatórios: "
        f"{null_count:,}"
    )

    print(
        f"Preços inválidos: "
        f"{invalid_prices:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price History possui duplicidades."
        )

    if null_count > 0:
        raise ValueError(
            "Price History possui "
            "campos obrigatórios nulos."
        )

    if invalid_prices > 0:
        raise ValueError(
            "Price History possui "
            "preços inválidos."
        )

    print(
        "\nData Quality aprovada."
    )


def get_confirmed_actions(
    discontinuities: pd.DataFrame,
) -> pd.DataFrame:
    confirmed = discontinuities[
        discontinuities[
            "is_confirmed_corporate_action"
        ]
    ].copy()

    status_mismatch = confirmed[
        "review_status"
    ].ne(
        "CONFIRMED"
    )

    if status_mismatch.any():
        raise ValueError(
            "Evento marcado como confirmado "
            "possui review_status diferente "
            "de CONFIRMED."
        )

    valid_types = (
        STRUCTURAL_EVENT_TYPES
        | CASH_EVENT_TYPES
    )

    unsupported_types = sorted(
        set(
            confirmed[
                "event_type"
            ].dropna()
        )
        - valid_types
    )

    if unsupported_types:
        raise ValueError(
            "Corporate Actions confirmados "
            "com event_type ainda não "
            "suportado pela camada v1: "
            f"{unsupported_types}"
        )

    duplicate_count = int(
        confirmed.duplicated(
            subset=[
                "ticker",
                "event_date",
            ]
        ).sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Corporate Actions confirmados "
            "duplicados por "
            "(ticker + event_date)."
        )

    structural = confirmed[
        confirmed[
            "event_type"
        ].isin(
            STRUCTURAL_EVENT_TYPES
        )
    ]

    if not structural.empty:
        invalid_factor = (
            structural[
                "price_adjustment_factor"
            ].isna()
            |
            (
                structural[
                    "price_adjustment_factor"
                ]
                <= 0
            )
        )

        if invalid_factor.any():
            raise ValueError(
                "SPLIT/REVERSE_SPLIT confirmado "
                "sem price_adjustment_factor "
                "válido."
            )

        invalid_quantity = (
            structural[
                "quantity_multiplier"
            ].isna()
            |
            (
                structural[
                    "quantity_multiplier"
                ]
                <= 0
            )
        )

        if invalid_quantity.any():
            raise ValueError(
                "SPLIT/REVERSE_SPLIT confirmado "
                "sem quantity_multiplier válido."
            )

    cash_events = confirmed[
        confirmed[
            "event_type"
        ].isin(
            CASH_EVENT_TYPES
        )
    ]

    if not cash_events.empty:
        invalid_cash = (
            cash_events[
                "cash_amount_per_unit"
            ].isna()
            |
            (
                cash_events[
                    "cash_amount_per_unit"
                ]
                <= 0
            )
        )

        if invalid_cash.any():
            raise ValueError(
                "AMORTIZATION confirmada sem "
                "cash_amount_per_unit válido."
            )

    print(
        "\n======================================"
    )
    print(
        "Corporate Actions confirmados"
    )
    print(
        "======================================"
    )

    print(
        f"Eventos confirmados: "
        f"{len(confirmed):,}"
    )

    if confirmed.empty:
        print(
            "Nenhum Corporate Action confirmado."
        )

        return confirmed

    for event_type, count in (
        confirmed[
            "event_type"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {event_type}: "
            f"{count:,}"
        )

    return confirmed


def validate_event_dates(
    price_history: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    if confirmed_actions.empty:
        return

    available_keys = set(
        zip(
            price_history[
                "ticker"
            ],
            price_history[
                "trade_date"
            ],
        )
    )

    missing_events = []

    for row in confirmed_actions.itertuples(
        index=False
    ):
        key = (
            row.ticker,
            row.event_date,
        )

        if key not in available_keys:
            missing_events.append(
                {
                    "ticker": row.ticker,
                    "event_date": (
                        row.event_date
                    ),
                    "event_type": (
                        row.event_type
                    ),
                }
            )

    if missing_events:
        missing_dataframe = pd.DataFrame(
            missing_events
        )

        raise ValueError(
            "Corporate Action confirmado "
            "sem preço disponível na "
            "event_date:\n"
            f"{missing_dataframe.to_string(index=False)}"
        )


def build_structural_adjustment_factor(
    price_history: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói fator estrutural retroativo.

    Para um SPLIT com fator 0.10 em D:

    datas < D:
        structural_adjustment_factor *= 0.10

    datas >= D:
        o evento já está refletido no preço
        bruto e não aplicamos o fator daquele
        evento novamente.

    Caso existam múltiplos eventos estruturais
    futuros para um ticker, os fatores são
    multiplicados retroativamente.
    """

    result = price_history.copy()

    result[
        "structural_adjustment_factor"
    ] = 1.0

    structural_actions = confirmed_actions[
        confirmed_actions[
            "event_type"
        ].isin(
            STRUCTURAL_EVENT_TYPES
        )
    ].copy()

    if structural_actions.empty:
        return result

    structural_actions = (
        structural_actions.sort_values(
            [
                "ticker",
                "event_date",
            ]
        )
    )

    for action in (
        structural_actions.itertuples(
            index=False
        )
    ):
        historical_mask = (
            result[
                "ticker"
            ].eq(
                action.ticker
            )
            &
            result[
                "trade_date"
            ].lt(
                action.event_date
            )
        )

        result.loc[
            historical_mask,
            "structural_adjustment_factor",
        ] = (
            result.loc[
                historical_mask,
                "structural_adjustment_factor",
            ]
            * float(
                action.price_adjustment_factor
            )
        )

    return result


def attach_event_information(
    dataframe: pd.DataFrame,
    discontinuities: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    event_columns = [
        "ticker",
        "event_date",
        "review_status",
        "event_type",
        "confidence",
        "is_confirmed_corporate_action",
    ]

    available_event_columns = [
        column
        for column in event_columns
        if column in discontinuities.columns
    ]

    event_information = (
        discontinuities[
            available_event_columns
        ]
        .copy()
    )

    event_information = (
        event_information.rename(
            columns={
                "event_date": (
                    "trade_date"
                ),
                "review_status": (
                    "review_status_on_date"
                ),
                "event_type": (
                    "event_type_on_date"
                ),
                "confidence": (
                    "discontinuity_confidence_on_date"
                ),
                "is_confirmed_corporate_action": (
                    "confirmed_action_on_date"
                ),
            }
        )
    )

    result = result.merge(
        event_information,
        how="left",
        on=[
            "ticker",
            "trade_date",
        ],
        validate="one_to_one",
    )

    result[
        "review_status_on_date"
    ] = result[
        "review_status_on_date"
    ].fillna(
        "NONE"
    )

    result[
        "event_type_on_date"
    ] = result[
        "event_type_on_date"
    ].fillna(
        "NONE"
    )

    result[
        "discontinuity_confidence_on_date"
    ] = result[
        "discontinuity_confidence_on_date"
    ].fillna(
        "NONE"
    )

    #
    # Correção do FutureWarning do pandas:
    #
    # convertemos primeiro para nullable boolean,
    # preenchemos os nulos e somente depois
    # voltamos para bool nativo.
    #
    result[
        "confirmed_action_on_date"
    ] = (
        result[
            "confirmed_action_on_date"
        ]
        .astype(
            "boolean"
        )
        .fillna(
            False
        )
        .astype(
            bool
        )
    )

    result[
        "pending_review_on_date"
    ] = (
        result[
            "review_status_on_date"
        ]
        == "PENDING_REVIEW"
    )

    action_payload = confirmed_actions[
        [
            "ticker",
            "event_date",
            "event_type",
            "quantity_multiplier",
            "price_adjustment_factor",
            "cash_amount_per_unit",
            "confirmation_source",
            "confirmation_date",
        ]
    ].copy()

    action_payload = action_payload.rename(
        columns={
            "event_date": (
                "trade_date"
            ),
            "event_type": (
                "confirmed_event_type"
            ),
            "quantity_multiplier": (
                "confirmed_quantity_multiplier"
            ),
            "price_adjustment_factor": (
                "confirmed_price_adjustment_factor"
            ),
            "cash_amount_per_unit": (
                "confirmed_cash_amount_per_unit"
            ),
            "confirmation_source": (
                "confirmed_action_source"
            ),
            "confirmation_date": (
                "confirmed_action_confirmation_date"
            ),
        }
    )

    result = result.merge(
        action_payload,
        how="left",
        on=[
            "ticker",
            "trade_date",
        ],
        validate="one_to_one",
    )

    return result


def calculate_adjusted_prices(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "close_price_raw"
    ] = result[
        "close_price"
    ].astype(
        float
    )

    result[
        "close_price_adjusted"
    ] = (
        result[
            "close_price_raw"
        ]
        * result[
            "structural_adjustment_factor"
        ]
    )

    result[
        "cash_flow_per_unit_raw"
    ] = (
        result[
            "confirmed_cash_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        .astype(
            float
        )
    )

    #
    # Cash flow e preço ajustado devem
    # permanecer na mesma base estrutural.
    #
    result[
        "cash_flow_per_unit_adjusted"
    ] = (
        result[
            "cash_flow_per_unit_raw"
        ]
        * result[
            "structural_adjustment_factor"
        ]
    )

    return result


def calculate_returns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

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

    result[
        "previous_close_price_adjusted"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "close_price_adjusted"
        ]
        .shift(1)
    )

    result[
        "daily_return_raw"
    ] = (
        result[
            "close_price_raw"
        ]
        / result[
            "previous_close_price_raw"
        ]
        - 1
    )

    result[
        "daily_return_adjusted_price"
    ] = (
        result[
            "close_price_adjusted"
        ]
        / result[
            "previous_close_price_adjusted"
        ]
        - 1
    )

    result[
        "daily_return_economic"
    ] = (
        (
            result[
                "close_price_adjusted"
            ]
            + result[
                "cash_flow_per_unit_adjusted"
            ]
        )
        / result[
            "previous_close_price_adjusted"
        ]
        - 1
    )

    return result


def add_metadata(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "adjusted_prices_version"
    ] = (
        ADJUSTED_PRICES_VERSION
    )

    result[
        "created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


def validate_adjusted_output(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price_raw",
        "structural_adjustment_factor",
        "close_price_adjusted",
        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",
        "review_status_on_date",
        "event_type_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",
        "adjusted_prices_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Saída possui colunas ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "trade_date",
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

    invalid_raw = int(
        (
            dataframe[
                "close_price_raw"
            ]
            <= 0
        ).sum()
    )

    invalid_adjusted = int(
        (
            dataframe[
                "close_price_adjusted"
            ]
            <= 0
        ).sum()
    )

    invalid_factor = int(
        (
            dataframe[
                "structural_adjustment_factor"
            ]
            <= 0
        ).sum()
    )

    negative_cash = int(
        (
            dataframe[
                "cash_flow_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    raw_preservation_error = int(
        (
            ~np.isclose(
                dataframe[
                    "close_price_raw"
                ],
                dataframe[
                    "close_price"
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    confirmed_count = int(
        dataframe[
            "confirmed_action_on_date"
        ].sum()
    )

    expected_confirmed_count = len(
        confirmed_actions
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Adjusted Prices"
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
        f"{required_null_count:,}"
    )

    print(
        f"close_price_raw inválidos: "
        f"{invalid_raw:,}"
    )

    print(
        f"close_price_adjusted inválidos: "
        f"{invalid_adjusted:,}"
    )

    print(
        "structural_adjustment_factor "
        f"inválidos: {invalid_factor:,}"
    )

    print(
        f"Cash flows negativos: "
        f"{negative_cash:,}"
    )

    print(
        "Erros de preservação do RAW: "
        f"{raw_preservation_error:,}"
    )

    print(
        "Corporate Actions aplicados: "
        f"{confirmed_count:,}"
    )

    print(
        "Corporate Actions esperados: "
        f"{expected_confirmed_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Saída possui duplicidades."
        )

    if required_null_count > 0:
        raise ValueError(
            "Saída possui campos "
            "obrigatórios nulos."
        )

    if invalid_raw > 0:
        raise ValueError(
            "Saída possui close_price_raw "
            "inválido."
        )

    if invalid_adjusted > 0:
        raise ValueError(
            "Saída possui "
            "close_price_adjusted inválido."
        )

    if invalid_factor > 0:
        raise ValueError(
            "Saída possui fator estrutural "
            "inválido."
        )

    if negative_cash > 0:
        raise ValueError(
            "Saída possui cash flow negativo."
        )

    if raw_preservation_error > 0:
        raise ValueError(
            "close_price_raw não preserva "
            "exatamente o preço de origem."
        )

    if (
        confirmed_count
        != expected_confirmed_count
    ):
        raise ValueError(
            "Quantidade de Corporate Actions "
            "aplicados diverge da quantidade "
            "confirmada."
        )

    print(
        "\nData Quality aprovada."
    )


def validate_split_behavior(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    structural_actions = confirmed_actions[
        confirmed_actions[
            "event_type"
        ].isin(
            STRUCTURAL_EVENT_TYPES
        )
    ]

    if structural_actions.empty:
        return

    print(
        "\n======================================"
    )
    print(
        "Validação - SPLIT / REVERSE_SPLIT"
    )
    print(
        "======================================"
    )

    failures = []

    for action in (
        structural_actions.itertuples(
            index=False
        )
    ):
        ticker_data = dataframe[
            dataframe[
                "ticker"
            ].eq(
                action.ticker
            )
        ].sort_values(
            "trade_date"
        )

        event_row = ticker_data[
            ticker_data[
                "trade_date"
            ].eq(
                action.event_date
            )
        ]

        if len(event_row) != 1:
            failures.append(
                (
                    action.ticker,
                    action.event_date,
                    "EVENT_ROW_NOT_FOUND",
                )
            )

            continue

        event_row = event_row.iloc[0]

        adjusted_return = event_row[
            "daily_return_adjusted_price"
        ]

        raw_return = event_row[
            "daily_return_raw"
        ]

        print(
            f"{action.ticker} | "
            f"{action.event_date.date()}"
        )

        print(
            f"  Event type: "
            f"{action.event_type}"
        )

        print(
            "  Confirmed factor: "
            f"{action.price_adjustment_factor}"
        )

        print(
            f"  RAW return: "
            f"{raw_return * 100:.4f}%"
        )

        print(
            "  Adjusted price return: "
            f"{adjusted_return * 100:.4f}%"
        )

    if failures:
        raise ValueError(
            "Falha na validação estrutural: "
            f"{failures}"
        )


def validate_amortization_behavior(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    amortizations = confirmed_actions[
        confirmed_actions[
            "event_type"
        ].eq(
            "AMORTIZATION"
        )
    ]

    if amortizations.empty:
        return

    print(
        "\n======================================"
    )
    print(
        "Validação - AMORTIZATION"
    )
    print(
        "======================================"
    )

    failures = []

    for action in (
        amortizations.itertuples(
            index=False
        )
    ):
        event_row = dataframe[
            dataframe[
                "ticker"
            ].eq(
                action.ticker
            )
            &
            dataframe[
                "trade_date"
            ].eq(
                action.event_date
            )
        ]

        if len(event_row) != 1:
            failures.append(
                (
                    action.ticker,
                    action.event_date,
                    "EVENT_ROW_NOT_FOUND",
                )
            )

            continue

        event_row = event_row.iloc[0]

        raw_return = event_row[
            "daily_return_raw"
        ]

        adjusted_price_return = event_row[
            "daily_return_adjusted_price"
        ]

        economic_return = event_row[
            "daily_return_economic"
        ]

        cash = event_row[
            "cash_flow_per_unit_raw"
        ]

        print(
            f"{action.ticker} | "
            f"{action.event_date.date()}"
        )

        print(
            f"  Cash amount: "
            f"{cash:.9f}"
        )

        print(
            f"  RAW return: "
            f"{raw_return * 100:.4f}%"
        )

        print(
            "  Adjusted price return: "
            f"{adjusted_price_return * 100:.4f}%"
        )

        print(
            "  Economic return: "
            f"{economic_return * 100:.4f}%"
        )

    if failures:
        raise ValueError(
            "Falha na validação "
            "de amortizações: "
            f"{failures}"
        )


def print_summary(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    structural_rows = int(
        (
            ~np.isclose(
                dataframe[
                    "structural_adjustment_factor"
                ],
                1.0,
            )
        ).sum()
    )

    cash_rows = int(
        (
            dataframe[
                "cash_flow_per_unit_raw"
            ]
            > 0
        ).sum()
    )

    pending_rows = int(
        dataframe[
            "pending_review_on_date"
        ].sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo - Corporate Action "
        "Adjusted Prices"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{ADJUSTED_PRICES_VERSION}"
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
        "Corporate Actions confirmados: "
        f"{len(confirmed_actions):,}"
    )

    print(
        "Linhas historicamente "
        "ajustadas por fator estrutural: "
        f"{structural_rows:,}"
    )

    print(
        "Linhas com cash flow "
        f"corporativo: {cash_rows:,}"
    )

    print(
        "Datas de descontinuidade "
        "ainda PENDING_REVIEW: "
        f"{pending_rows:,}"
    )

    print(
        "\nPeríodo:"
    )

    print(
        f"  {dataframe['trade_date'].min().date()}"
        " -> "
        f"{dataframe['trade_date'].max().date()}"
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
        "structural_adjustment_factor",
        "close_price_adjusted",

        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        "previous_close_price_raw",
        "previous_close_price_adjusted",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        "review_status_on_date",
        "event_type_on_date",
        "discontinuity_confidence_on_date",

        "confirmed_action_on_date",
        "pending_review_on_date",

        "confirmed_event_type",
        "confirmed_quantity_multiplier",
        "confirmed_price_adjustment_factor",
        "confirmed_cash_amount_per_unit",
        "confirmed_action_source",
        "confirmed_action_confirmation_date",

        "adjusted_prices_version",
        "created_at",
    ]

    return dataframe[
        columns
    ].copy()


def main() -> None:
    print(
        "Construindo FII Corporate Action "
        "Adjusted Prices..."
    )

    print(
        f"Version: "
        f"{ADJUSTED_PRICES_VERSION}"
    )

    price_history = (
        load_price_history()
    )

    validate_price_history(
        price_history
    )

    discontinuities = (
        load_discontinuities()
    )

    confirmed_actions = (
        get_confirmed_actions(
            discontinuities
        )
    )

    validate_event_dates(
        price_history=price_history,
        confirmed_actions=confirmed_actions,
    )

    adjusted = (
        build_structural_adjustment_factor(
            price_history=price_history,
            confirmed_actions=confirmed_actions,
        )
    )

    adjusted = attach_event_information(
        dataframe=adjusted,
        discontinuities=discontinuities,
        confirmed_actions=confirmed_actions,
    )

    adjusted = calculate_adjusted_prices(
        adjusted
    )

    adjusted = calculate_returns(
        adjusted
    )

    adjusted = add_metadata(
        adjusted
    )

    validate_adjusted_output(
        dataframe=adjusted,
        confirmed_actions=confirmed_actions,
    )

    validate_split_behavior(
        dataframe=adjusted,
        confirmed_actions=confirmed_actions,
    )

    validate_amortization_behavior(
        dataframe=adjusted,
        confirmed_actions=confirmed_actions,
    )

    output = select_output_columns(
        adjusted
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
        confirmed_actions=confirmed_actions,
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "close_price_raw foi preservado."
    )

    print(
        "SPLIT/REVERSE_SPLIT afetam somente "
        "a escala estrutural da série."
    )

    print(
        "AMORTIZATION entra como cash flow "
        "no retorno econômico."
    )

    print(
        "Eventos PENDING_REVIEW não geram "
        "ajuste automático."
    )


if __name__ == "__main__":
    main()