from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


SILVER_PRICES_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "fii_daily_prices"
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


ADJUSTED_PRICES_VERSION = "v2"


STRUCTURAL_EVENT_TYPES = {
    "SPLIT",
    "REVERSE_SPLIT",
}

CASH_EVENT_TYPES = {
    "AMORTIZATION",
}


PARTITION_PATTERN = re.compile(
    r"year=(\d{4}).*month=(\d{2}).*day=(\d{2})"
)


RAW_PRICE_COLUMNS = [
    "open_price",
    "low_price",
    "high_price",
    "average_price",
    "close_price",
]


def extract_partition_date(
    path: Path,
) -> tuple[int, int, int]:
    """
    Extrai YYYY/MM/DD do caminho
    particionado da Silver.
    """

    match = PARTITION_PATTERN.search(
        str(path.parent)
    )

    if match is None:
        raise ValueError(
            "Não foi possível identificar "
            f"a data da partição: {path}"
        )

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def find_all_silver_price_files(
    base_directory: Path,
) -> list[Path]:
    """
    Localiza todas as partições Silver
    de FII Daily Prices.
    """

    files = list(
        base_directory.rglob(
            "fii_daily_prices.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            "Nenhuma Silver de preços encontrada "
            f"em {base_directory}"
        )

    return sorted(
        files,
        key=extract_partition_date,
    )


def validate_silver_partition_schema(
    dataframe: pd.DataFrame,
    source_path: Path,
) -> None:
    """
    Valida o contrato mínimo de uma
    partição Silver.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
        "ticker_resolution_status",
        "market_evidence_confidence",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Arquivo {source_path} possui "
            f"colunas ausentes: {missing_columns}"
        )


def load_silver_prices(
    silver_files: list[Path],
) -> pd.DataFrame:
    """
    Carrega diretamente todas as partições
    Silver de preços.

    Esta camada NÃO depende mais de
    fii_price_history.
    """

    dataframes: list[pd.DataFrame] = []

    print(
        "\n======================================"
    )
    print(
        "Carregando Silver FII Daily Prices"
    )
    print(
        "======================================"
    )

    for index, path in enumerate(
        silver_files,
        start=1,
    ):
        year, month, day = (
            extract_partition_date(
                path
            )
        )

        print(
            f"[{index}/{len(silver_files)}] "
            f"{year:04d}-{month:02d}-{day:02d}"
        )

        dataframe = pd.read_parquet(
            path
        )

        validate_silver_partition_schema(
            dataframe=dataframe,
            source_path=path,
        )

        dataframes.append(
            dataframe
        )

    prices = pd.concat(
        dataframes,
        ignore_index=True,
    )

    prices[
        "trade_date"
    ] = pd.to_datetime(
        prices[
            "trade_date"
        ]
    )

    prices[
        "ticker"
    ] = (
        prices[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return prices


def validate_silver_prices(
    dataframe: pd.DataFrame,
) -> None:
    """
    Data Quality da fonte Silver consolidada.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
        "ticker_resolution_status",
        "market_evidence_confidence",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Silver consolidada possui "
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

    invalid_close_prices = int(
        (
            dataframe[
                "close_price"
            ]
            <= 0
        ).sum()
    )

    invalid_open_prices = int(
        (
            dataframe[
                "open_price"
            ]
            <= 0
        ).sum()
    )

    invalid_low_prices = int(
        (
            dataframe[
                "low_price"
            ]
            <= 0
        ).sum()
    )

    invalid_high_prices = int(
        (
            dataframe[
                "high_price"
            ]
            <= 0
        ).sum()
    )

    invalid_average_prices = int(
        (
            dataframe[
                "average_price"
            ]
            <= 0
        ).sum()
    )

    invalid_trades = int(
        (
            dataframe[
                "trades_quantity"
            ]
            < 0
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Silver Prices"
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
        f"Nulos obrigatórios: "
        f"{null_count:,}"
    )

    print(
        f"close_price inválidos: "
        f"{invalid_close_prices:,}"
    )

    print(
        f"open_price inválidos: "
        f"{invalid_open_prices:,}"
    )

    print(
        f"low_price inválidos: "
        f"{invalid_low_prices:,}"
    )

    print(
        f"high_price inválidos: "
        f"{invalid_high_prices:,}"
    )

    print(
        f"average_price inválidos: "
        f"{invalid_average_prices:,}"
    )

    print(
        f"trades_quantity inválidos: "
        f"{invalid_trades:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Silver possui duplicidades."
        )

    if null_count > 0:
        raise ValueError(
            "Silver possui campos "
            "obrigatórios nulos."
        )

    if invalid_close_prices > 0:
        raise ValueError(
            "Silver possui close_price inválido."
        )

    if invalid_open_prices > 0:
        raise ValueError(
            "Silver possui open_price inválido."
        )

    if invalid_low_prices > 0:
        raise ValueError(
            "Silver possui low_price inválido."
        )

    if invalid_high_prices > 0:
        raise ValueError(
            "Silver possui high_price inválido."
        )

    if invalid_average_prices > 0:
        raise ValueError(
            "Silver possui average_price inválido."
        )

    if invalid_trades > 0:
        raise ValueError(
            "Silver possui trades_quantity "
            "inválido."
        )

    print(
        "\nData Quality aprovada."
    )


def load_discontinuities() -> pd.DataFrame:
    if not DISCONTINUITIES_PATH.exists():
        raise FileNotFoundError(
            "FII Price Discontinuities não encontrado: "
            f"{DISCONTINUITIES_PATH}"
        )

    print(
        "\nCarregando FII Price Discontinuities..."
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
            "suportado: "
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

        product = (
            structural[
                "quantity_multiplier"
            ].astype(float)
            * structural[
                "price_adjustment_factor"
            ].astype(float)
        )

        invalid_reciprocal = (
            ~np.isclose(
                product,
                1.0,
                rtol=0.05,
                atol=0.0,
            )
        )

        if invalid_reciprocal.any():
            raise ValueError(
                "SPLIT/REVERSE_SPLIT possui "
                "quantity_multiplier e "
                "price_adjustment_factor "
                "não recíprocos."
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
    silver_prices: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    if confirmed_actions.empty:
        return

    available_keys = set(
        zip(
            silver_prices[
                "ticker"
            ],
            silver_prices[
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
                    "event_date": row.event_date,
                    "event_type": row.event_type,
                }
            )

    if missing_events:
        missing_dataframe = pd.DataFrame(
            missing_events
        )

        raise ValueError(
            "Corporate Action confirmado "
            "sem preço Silver disponível "
            "na event_date:\n"
            f"{missing_dataframe.to_string(index=False)}"
        )


def build_structural_adjustment_factor(
    silver_prices: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói fator estrutural retroativo.

    SPLIT com fator 0.10 em D:

    datas < D
        factor *= 0.10

    datas >= D
        o preço bruto já está na nova escala.

    Múltiplos eventos futuros são
    multiplicados retroativamente.
    """

    result = silver_prices.copy()

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
    """
    Preserva preços RAW e cria preços
    estruturalmente ajustados.

    Todos os OHLC/average usam o mesmo
    structural_adjustment_factor.
    """

    result = dataframe.copy()

    for column in RAW_PRICE_COLUMNS:
        raw_column = (
            f"{column}_raw"
        )

        adjusted_column = (
            f"{column}_adjusted"
        )

        result[
            raw_column
        ] = result[
            column
        ].astype(
            float
        )

        result[
            adjusted_column
        ] = (
            result[
                raw_column
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
    # Cash flow e preço precisam ficar
    # na mesma base estrutural.
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
        "adjusted_prices_source"
    ] = (
        "SILVER_FII_DAILY_PRICES"
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
        "instrument_id",
        "trades_quantity",

        "open_price_raw",
        "low_price_raw",
        "high_price_raw",
        "average_price_raw",
        "close_price_raw",

        "structural_adjustment_factor",

        "open_price_adjusted",
        "low_price_adjusted",
        "high_price_adjusted",
        "average_price_adjusted",
        "close_price_adjusted",

        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        "review_status_on_date",
        "event_type_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",

        "ticker_resolution_status",
        "market_evidence_confidence",

        "adjusted_prices_version",
        "adjusted_prices_source",
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

    invalid_raw_prices = 0
    invalid_adjusted_prices = 0
    raw_preservation_error = 0

    for column in RAW_PRICE_COLUMNS:
        raw_column = (
            f"{column}_raw"
        )

        adjusted_column = (
            f"{column}_adjusted"
        )

        invalid_raw_prices += int(
            (
                dataframe[
                    raw_column
                ]
                <= 0
            ).sum()
        )

        invalid_adjusted_prices += int(
            (
                dataframe[
                    adjusted_column
                ]
                <= 0
            ).sum()
        )

        raw_preservation_error += int(
            (
                ~np.isclose(
                    dataframe[
                        raw_column
                    ],
                    dataframe[
                        column
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

    non_finite_raw_return = int(
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

    non_finite_adjusted_return = int(
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

    non_finite_economic_return = int(
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
        f"Pregões: "
        f"{dataframe['trade_date'].nunique():,}"
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
        f"Preços RAW inválidos: "
        f"{invalid_raw_prices:,}"
    )

    print(
        f"Preços adjusted inválidos: "
        f"{invalid_adjusted_prices:,}"
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
        "daily_return_raw não finitos: "
        f"{non_finite_raw_return:,}"
    )

    print(
        "daily_return_adjusted_price "
        f"não finitos: {non_finite_adjusted_return:,}"
    )

    print(
        "daily_return_economic "
        f"não finitos: {non_finite_economic_return:,}"
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

    if invalid_raw_prices > 0:
        raise ValueError(
            "Saída possui preços RAW inválidos."
        )

    if invalid_adjusted_prices > 0:
        raise ValueError(
            "Saída possui preços adjusted "
            "inválidos."
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
            "Colunas RAW não preservam "
            "exatamente a Silver."
        )

    if non_finite_raw_return > 0:
        raise ValueError(
            "daily_return_raw possui "
            "valor não finito."
        )

    if non_finite_adjusted_return > 0:
        raise ValueError(
            "daily_return_adjusted_price possui "
            "valor não finito."
        )

    if non_finite_economic_return > 0:
        raise ValueError(
            "daily_return_economic possui "
            "valor não finito."
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

        adjusted_return = event_row[
            "daily_return_adjusted_price"
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
    silver_file_count: int,
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
        "Source: "
        "SILVER_FII_DAILY_PRICES"
    )

    print(
        f"Partições Silver: "
        f"{silver_file_count:,}"
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
        "instrument_id",

        "open_price_raw",
        "low_price_raw",
        "high_price_raw",
        "average_price_raw",
        "close_price_raw",

        "structural_adjustment_factor",

        "open_price_adjusted",
        "low_price_adjusted",
        "high_price_adjusted",
        "average_price_adjusted",
        "close_price_adjusted",

        "trades_quantity",

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

        "ticker_resolution_status",
        "market_evidence_confidence",

        "adjusted_prices_version",
        "adjusted_prices_source",
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

    print(
        "Source: "
        "SILVER_FII_DAILY_PRICES"
    )

    silver_files = (
        find_all_silver_price_files(
            SILVER_PRICES_BASE_DIR
        )
    )

    print(
        f"\nPartições Silver encontradas: "
        f"{len(silver_files):,}"
    )

    silver_prices = load_silver_prices(
        silver_files
    )

    validate_silver_prices(
        silver_prices
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
        silver_prices=silver_prices,
        confirmed_actions=confirmed_actions,
    )

    adjusted = (
        build_structural_adjustment_factor(
            silver_prices=silver_prices,
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
        silver_file_count=len(
            silver_files
        ),
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "A fonte desta versão é diretamente "
        "a Silver FII Daily Prices."
    )

    print(
        "Nenhuma dependência de "
        "FII Price History permanece."
    )

    print(
        "Preços RAW foram preservados."
    )

    print(
        "OHLC/average receberam o mesmo "
        "ajuste estrutural do close."
    )

    print(
        "SPLIT/REVERSE_SPLIT alteram apenas "
        "a escala estrutural."
    )

    print(
        "AMORTIZATION entra como cash flow "
        "no retorno econômico."
    )

    print(
        "Eventos não confirmados não geram "
        "ajuste automático."
    )


if __name__ == "__main__":
    main()