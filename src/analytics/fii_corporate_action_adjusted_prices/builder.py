from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# Paths
# ============================================================

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


# ============================================================
# Version / source
# ============================================================

ADJUSTED_PRICES_VERSION = "v3"

ADJUSTED_PRICES_SOURCE = (
    "SILVER_FII_DAILY_PRICES"
)

CORPORATE_ACTION_SOURCE = (
    "FII_PRICE_DISCONTINUITIES_V5_REGISTRY_V2"
)


# ============================================================
# Corporate Action contract
# ============================================================

STRUCTURAL_EVENT_TYPES = {
    "SPLIT",
    "REVERSE_SPLIT",
}

ECONOMIC_EVENT_TYPES = {
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


CORPORATE_ACTION_DATE_COLUMNS = [
    "corporate_action_record_date",
    "corporate_action_effective_date",
    "cash_payment_date",
    "in_kind_delivery_date",
    "first_post_event_trade_date",
    "confirmation_date",
    "governance_review_date",
]


# ============================================================
# Silver discovery
# ============================================================

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


# ============================================================
# Silver loading / validation
# ============================================================

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

    Esta camada NÃO depende de
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

    invalid_prices = 0
    non_finite_prices = 0

    for column in RAW_PRICE_COLUMNS:
        invalid_prices += int(
            (
                dataframe[
                    column
                ]
                <= 0
            ).sum()
        )

        non_finite_prices += int(
            (
                dataframe[
                    column
                ].notna()
                &
                ~np.isfinite(
                    dataframe[
                        column
                    ]
                )
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
        f"Preços inválidos: "
        f"{invalid_prices:,}"
    )

    print(
        f"Preços não finitos: "
        f"{non_finite_prices:,}"
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

    if invalid_prices > 0:
        raise ValueError(
            "Silver possui preços inválidos."
        )

    if non_finite_prices > 0:
        raise ValueError(
            "Silver possui preços não finitos."
        )

    if invalid_trades > 0:
        raise ValueError(
            "Silver possui trades_quantity "
            "inválido."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Price Discontinuities / Registry v2 payload
# ============================================================

def load_discontinuities() -> pd.DataFrame:
    """
    Carrega Price Discontinuities v5
    contendo o payload do Registry v2.
    """

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
        "confidence",

        "quantity_multiplier",
        "price_adjustment_factor",

        "cash_amount_per_unit",
        "in_kind_amount_per_unit",
        "total_economic_value_per_unit",
        "in_kind_asset_ticker",
        "in_kind_quantity_per_unit",

        "corporate_action_record_date",
        "corporate_action_effective_date",
        "cash_payment_date",
        "in_kind_delivery_date",
        "first_post_event_trade_date",

        "confirmation_source",
        "confirmation_date",
        "governance_review_date",

        "is_confirmed_corporate_action",

        "discontinuity_version",
        "discontinuity_source",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price Discontinuities possui "
            "schema incompatível com "
            "Registry v2."
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

    for column in (
        CORPORATE_ACTION_DATE_COLUMNS
    ):
        dataframe[
            column
        ] = pd.to_datetime(
            dataframe[
                column
            ],
            errors="coerce",
        )

    numeric_columns = [
        "quantity_multiplier",
        "price_adjustment_factor",
        "cash_amount_per_unit",
        "in_kind_amount_per_unit",
        "total_economic_value_per_unit",
        "in_kind_quantity_per_unit",
    ]

    for column in numeric_columns:
        dataframe[
            column
        ] = pd.to_numeric(
            dataframe[
                column
            ],
            errors="coerce",
        )

    dataframe[
        "in_kind_asset_ticker"
    ] = (
        dataframe[
            "in_kind_asset_ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return dataframe


def validate_discontinuity_contract(
    dataframe: pd.DataFrame,
) -> None:
    """
    Garante que esta camada recebe a versão
    de Price Discontinuities esperada.
    """

    invalid_version = int(
        (
            dataframe[
                "discontinuity_version"
            ]
            != "v5"
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "discontinuity_source"
            ]
            != "SILVER_FII_DAILY_PRICES"
        ).sum()
    )

    pending_count = int(
        dataframe[
            "review_status"
        ]
        .eq(
            "PENDING_REVIEW"
        )
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Contrato - Price Discontinuities"
    )
    print(
        "======================================"
    )

    print(
        f"Eventos: "
        f"{len(dataframe):,}"
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
        f"Eventos pendentes: "
        f"{pending_count:,}"
    )

    if invalid_version > 0:
        raise ValueError(
            "Adjusted Prices v3 exige "
            "Price Discontinuities v5."
        )

    if invalid_source > 0:
        raise ValueError(
            "Price Discontinuities possui "
            "source incompatível."
        )

    if pending_count > 0:
        raise ValueError(
            "Adjusted Prices v3 não pode ser "
            "construído enquanto existirem "
            "Corporate Action candidates "
            "PENDING_REVIEW."
        )

    print(
        "\nContrato de entrada aprovado."
    )


# ============================================================
# Confirmed Corporate Actions
# ============================================================

def get_confirmed_actions(
    discontinuities: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extrai somente Corporate Actions
    explicitamente CONFIRMED pelo registry.
    """

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
        | ECONOMIC_EVENT_TYPES
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
            "com event_type não suportado: "
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

    #
    # --------------------------------------------------------
    # Date semantics
    # --------------------------------------------------------
    #

    missing_first_post_trade = (
        confirmed[
            "first_post_event_trade_date"
        ]
        .isna()
    )

    if missing_first_post_trade.any():
        raise ValueError(
            "Corporate Action CONFIRMED sem "
            "first_post_event_trade_date."
        )

    event_date_mismatch = (
        confirmed[
            "event_date"
        ]
        != confirmed[
            "first_post_event_trade_date"
        ]
    )

    if event_date_mismatch.any():
        invalid_rows = confirmed.loc[
            event_date_mismatch,
            [
                "ticker",
                "event_date",
                "first_post_event_trade_date",
            ],
        ]

        raise ValueError(
            "Contrato atual exige "
            "event_date == "
            "first_post_event_trade_date:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    #
    # --------------------------------------------------------
    # Structural events
    # --------------------------------------------------------
    #

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

    #
    # --------------------------------------------------------
    # Economic events
    # --------------------------------------------------------
    #

    economic_events = confirmed[
        confirmed[
            "event_type"
        ].isin(
            ECONOMIC_EVENT_TYPES
        )
    ].copy()

    if not economic_events.empty:
        invalid_total_value = (
            economic_events[
                "total_economic_value_per_unit"
            ].isna()
            |
            (
                economic_events[
                    "total_economic_value_per_unit"
                ]
                <= 0
            )
        )

        if invalid_total_value.any():
            invalid_rows = (
                economic_events.loc[
                    invalid_total_value,
                    [
                        "ticker",
                        "event_date",
                        "total_economic_value_per_unit",
                    ],
                ]
            )

            raise ValueError(
                "AMORTIZATION confirmada sem "
                "total_economic_value_per_unit "
                "válido:\n"
                f"{invalid_rows.to_string(index=False)}"
            )

        negative_cash = (
            economic_events[
                "cash_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .lt(
                0.0
            )
        )

        if negative_cash.any():
            raise ValueError(
                "AMORTIZATION confirmada possui "
                "cash_amount_per_unit negativo."
            )

        negative_in_kind = (
            economic_events[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .lt(
                0.0
            )
        )

        if negative_in_kind.any():
            raise ValueError(
                "AMORTIZATION confirmada possui "
                "in_kind_amount_per_unit negativo."
            )

        component_sum = (
            economic_events[
                "cash_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .astype(float)
            +
            economic_events[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .astype(float)
        )

        total_value = (
            economic_events[
                "total_economic_value_per_unit"
            ]
            .astype(float)
        )

        component_mismatch = (
            ~np.isclose(
                component_sum,
                total_value,
                rtol=1e-8,
                atol=1e-8,
            )
        )

        if component_mismatch.any():
            invalid_rows = (
                economic_events.loc[
                    component_mismatch,
                    [
                        "ticker",
                        "event_date",
                        "cash_amount_per_unit",
                        "in_kind_amount_per_unit",
                        "total_economic_value_per_unit",
                    ],
                ]
            )

            raise ValueError(
                "Componentes econômicos não "
                "fecham com o valor total:\n"
                f"{invalid_rows.to_string(index=False)}"
            )

        in_kind_events = economic_events[
            economic_events[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .gt(
                0.0
            )
        ]

        if not in_kind_events.empty:
            missing_asset = (
                in_kind_events[
                    "in_kind_asset_ticker"
                ]
                .isna()
            )

            if missing_asset.any():
                raise ValueError(
                    "Evento in-kind confirmado "
                    "sem in_kind_asset_ticker."
                )

            invalid_in_kind_quantity = (
                in_kind_events[
                    "in_kind_quantity_per_unit"
                ]
                .isna()
                |
                (
                    in_kind_events[
                        "in_kind_quantity_per_unit"
                    ]
                    <= 0
                )
            )

            if invalid_in_kind_quantity.any():
                raise ValueError(
                    "Evento in-kind confirmado "
                    "sem in_kind_quantity_per_unit "
                    "válido."
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

    print(
        f"Structural events: "
        f"{len(structural):,}"
    )

    print(
        f"Economic events: "
        f"{len(economic_events):,}"
    )

    in_kind_count = int(
        (
            economic_events[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            > 0
        ).sum()
    )

    print(
        "Eventos com componente in-kind: "
        f"{in_kind_count:,}"
    )

    if confirmed.empty:
        print(
            "Nenhum Corporate Action confirmado."
        )

        return confirmed

    print(
        "\nEvent Types:"
    )

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


# ============================================================
# Event date availability
# ============================================================

def validate_event_dates(
    silver_prices: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    """
    event_date representa atualmente
    first_post_event_trade_date.

    Portanto todo evento confirmado precisa
    possuir observação Silver exatamente
    nessa chave.
    """

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
                    "ticker": (
                        row.ticker
                    ),
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
            "sem preço Silver disponível "
            "na first_post_event_trade_date:\n"
            f"{missing_dataframe.to_string(index=False)}"
        )


# ============================================================
# Structural adjustment
# ============================================================

def build_structural_adjustment_factor(
    silver_prices: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói fator estrutural retroativo.

    Exemplo:

    SPLIT 1:10 com factor=0.10 em D

        datas < D:
            factor *= 0.10

        datas >= D:
            o preço bruto já está
            na nova escala.

    Múltiplos eventos futuros são
    multiplicados retroativamente.
    """

    result = silver_prices.copy()

    result[
        "structural_adjustment_factor"
    ] = 1.0

    structural_actions = (
        confirmed_actions[
            confirmed_actions[
                "event_type"
            ].isin(
                STRUCTURAL_EVENT_TYPES
            )
        ]
        .copy()
        .sort_values(
            [
                "ticker",
                "event_date",
            ]
        )
    )

    if structural_actions.empty:
        return result

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


# ============================================================
# Attach governance/event information
# ============================================================

def attach_event_information(
    dataframe: pd.DataFrame,
    discontinuities: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adiciona:

    1. informação de qualquer
       descontinuidade detectada;

    2. payload governado somente das
       Corporate Actions confirmadas.
    """

    result = dataframe.copy()

    #
    # --------------------------------------------------------
    # Detector information
    # --------------------------------------------------------
    #

    event_columns = [
        "ticker",
        "event_date",
        "review_status",
        "event_type",
        "confidence",
        "is_confirmed_corporate_action",
    ]

    event_information = (
        discontinuities[
            event_columns
        ]
        .copy()
        .rename(
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

    #
    # --------------------------------------------------------
    # Governed Corporate Action payload
    # --------------------------------------------------------
    #

    action_payload_columns = [
        "ticker",
        "event_date",
        "event_type",

        "quantity_multiplier",
        "price_adjustment_factor",

        "cash_amount_per_unit",
        "in_kind_amount_per_unit",
        "total_economic_value_per_unit",
        "in_kind_asset_ticker",
        "in_kind_quantity_per_unit",

        "corporate_action_record_date",
        "corporate_action_effective_date",
        "cash_payment_date",
        "in_kind_delivery_date",
        "first_post_event_trade_date",

        "confirmation_source",
        "confirmation_date",
        "governance_review_date",
    ]

    action_payload = (
        confirmed_actions[
            action_payload_columns
        ]
        .copy()
        .rename(
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
                "in_kind_amount_per_unit": (
                    "confirmed_in_kind_amount_per_unit"
                ),
                "total_economic_value_per_unit": (
                    "confirmed_total_economic_value_per_unit"
                ),
                "in_kind_asset_ticker": (
                    "confirmed_in_kind_asset_ticker"
                ),
                "in_kind_quantity_per_unit": (
                    "confirmed_in_kind_quantity_per_unit"
                ),
                "corporate_action_record_date": (
                    "confirmed_corporate_action_record_date"
                ),
                "corporate_action_effective_date": (
                    "confirmed_corporate_action_effective_date"
                ),
                "cash_payment_date": (
                    "confirmed_cash_payment_date"
                ),
                "in_kind_delivery_date": (
                    "confirmed_in_kind_delivery_date"
                ),
                "first_post_event_trade_date": (
                    "confirmed_first_post_event_trade_date"
                ),
                "confirmation_source": (
                    "confirmed_action_source"
                ),
                "confirmation_date": (
                    "confirmed_action_confirmation_date"
                ),
                "governance_review_date": (
                    "confirmed_governance_review_date"
                ),
            }
        )
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


# ============================================================
# Adjusted prices / economic components
# ============================================================

def calculate_adjusted_prices(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Preserva preços RAW e cria preços
    estruturalmente ajustados.

    Todos os OHLC/average usam o mesmo
    structural_adjustment_factor.

    v3:
        cash != total economic value

    Portanto mantemos separadamente:

        cash component
        in-kind component
        total corporate-action value
    """

    result = dataframe.copy()

    #
    # --------------------------------------------------------
    # Raw + structural adjusted prices
    # --------------------------------------------------------
    #

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

    #
    # --------------------------------------------------------
    # Economic components
    # --------------------------------------------------------
    #

    result[
        "cash_amount_per_unit_raw"
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

    result[
        "in_kind_amount_per_unit_raw"
    ] = (
        result[
            "confirmed_in_kind_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        .astype(
            float
        )
    )

    result[
        "corporate_action_value_per_unit_raw"
    ] = (
        result[
            "confirmed_total_economic_value_per_unit"
        ]
        .fillna(
            0.0
        )
        .astype(
            float
        )
    )

    #
    # O valor econômico e seus componentes
    # precisam ficar na mesma escala dos
    # preços estruturalmente ajustados.
    #

    result[
        "cash_amount_per_unit_adjusted"
    ] = (
        result[
            "cash_amount_per_unit_raw"
        ]
        * result[
            "structural_adjustment_factor"
        ]
    )

    result[
        "in_kind_amount_per_unit_adjusted"
    ] = (
        result[
            "in_kind_amount_per_unit_raw"
        ]
        * result[
            "structural_adjustment_factor"
        ]
    )

    result[
        "corporate_action_value_per_unit_adjusted"
    ] = (
        result[
            "corporate_action_value_per_unit_raw"
        ]
        * result[
            "structural_adjustment_factor"
        ]
    )

    #
    # --------------------------------------------------------
    # Legacy aliases
    # --------------------------------------------------------
    #
    # Agora estes campos significam
    # APENAS caixa real.
    #
    # Eles são preservados temporariamente
    # para facilitar migração downstream.
    #

    result[
        "cash_flow_per_unit_raw"
    ] = result[
        "cash_amount_per_unit_raw"
    ]

    result[
        "cash_flow_per_unit_adjusted"
    ] = result[
        "cash_amount_per_unit_adjusted"
    ]

    return result


# ============================================================
# Returns
# ============================================================

def calculate_returns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula três retornos distintos:

    daily_return_raw
        movimento bruto da B3

    daily_return_adjusted_price
        movimento após correção apenas
        de escala estrutural

    daily_return_economic
        retorno econômico incluindo
        TOTAL economic value da Corporate
        Action, seja cash ou in-kind
    """

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
        - 1.0
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
        - 1.0
    )

    result[
        "daily_return_economic"
    ] = (
        (
            result[
                "close_price_adjusted"
            ]
            +
            result[
                "corporate_action_value_per_unit_adjusted"
            ]
        )
        / result[
            "previous_close_price_adjusted"
        ]
        - 1.0
    )

    return result


# ============================================================
# Metadata
# ============================================================

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
        ADJUSTED_PRICES_SOURCE
    )

    result[
        "corporate_action_source"
    ] = (
        CORPORATE_ACTION_SOURCE
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

def validate_adjusted_output(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    """
    Data Quality forte do Adjusted Prices v3.
    """

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

        "cash_amount_per_unit_raw",
        "cash_amount_per_unit_adjusted",

        "in_kind_amount_per_unit_raw",
        "in_kind_amount_per_unit_adjusted",

        "corporate_action_value_per_unit_raw",
        "corporate_action_value_per_unit_adjusted",

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
        "corporate_action_source",
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

    component_sum_mismatch = int(
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

    legacy_cash_alias_mismatch = int(
        (
            ~np.isclose(
                dataframe[
                    "cash_flow_per_unit_raw"
                ],
                dataframe[
                    "cash_amount_per_unit_raw"
                ],
                rtol=0.0,
                atol=1e-12,
            )
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

    expected_structural_count = int(
        confirmed_actions[
            "event_type"
        ]
        .isin(
            STRUCTURAL_EVENT_TYPES
        )
        .sum()
    )

    expected_economic_count = int(
        confirmed_actions[
            "event_type"
        ]
        .isin(
            ECONOMIC_EVENT_TYPES
        )
        .sum()
    )

    expected_in_kind_count = int(
        (
            confirmed_actions[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            > 0
        ).sum()
    )

    applied_economic_count = int(
        (
            dataframe[
                "corporate_action_value_per_unit_raw"
            ]
            > 0
        ).sum()
    )

    applied_in_kind_count = int(
        (
            dataframe[
                "in_kind_amount_per_unit_raw"
            ]
            > 0
        ).sum()
    )

    pending_count = int(
        dataframe[
            "pending_review_on_date"
        ].sum()
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

    invalid_version = int(
        (
            dataframe[
                "adjusted_prices_version"
            ]
            != ADJUSTED_PRICES_VERSION
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "adjusted_prices_source"
            ]
            != ADJUSTED_PRICES_SOURCE
        ).sum()
    )

    invalid_ca_source = int(
        (
            dataframe[
                "corporate_action_source"
            ]
            != CORPORATE_ACTION_SOURCE
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Adjusted Prices v3"
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
        f"Cash values negativos: "
        f"{negative_cash:,}"
    )

    print(
        f"In-kind values negativos: "
        f"{negative_in_kind:,}"
    )

    print(
        "Corporate Action values negativos: "
        f"{negative_total_value:,}"
    )

    print(
        "Mismatch cash + in-kind != total: "
        f"{component_sum_mismatch:,}"
    )

    print(
        "Mismatch legacy cash alias: "
        f"{legacy_cash_alias_mismatch:,}"
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
        f"não finitos: "
        f"{non_finite_adjusted_return:,}"
    )

    print(
        "daily_return_economic "
        f"não finitos: "
        f"{non_finite_economic_return:,}"
    )

    print(
        "Corporate Actions aplicados: "
        f"{confirmed_count:,}"
    )

    print(
        "Corporate Actions esperados: "
        f"{expected_confirmed_count:,}"
    )

    print(
        "Structural events esperados: "
        f"{expected_structural_count:,}"
    )

    print(
        "Economic events aplicados: "
        f"{applied_economic_count:,}"
    )

    print(
        "Economic events esperados: "
        f"{expected_economic_count:,}"
    )

    print(
        "Eventos in-kind aplicados: "
        f"{applied_in_kind_count:,}"
    )

    print(
        "Eventos in-kind esperados: "
        f"{expected_in_kind_count:,}"
    )

    print(
        f"Pendentes de review: "
        f"{pending_count:,}"
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
            "Saída possui cash negativo."
        )

    if negative_in_kind > 0:
        raise ValueError(
            "Saída possui in-kind negativo."
        )

    if negative_total_value > 0:
        raise ValueError(
            "Saída possui Corporate Action "
            "value negativo."
        )

    if component_sum_mismatch > 0:
        raise ValueError(
            "cash + in-kind diverge do "
            "total economic value."
        )

    if legacy_cash_alias_mismatch > 0:
        raise ValueError(
            "Legacy cash_flow alias não "
            "representa cash puro."
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

    if (
        applied_economic_count
        != expected_economic_count
    ):
        raise ValueError(
            "Quantidade de eventos econômicos "
            "aplicados diverge da esperada."
        )

    if (
        applied_in_kind_count
        != expected_in_kind_count
    ):
        raise ValueError(
            "Quantidade de eventos in-kind "
            "aplicados diverge da esperada."
        )

    if pending_count > 0:
        raise ValueError(
            "Adjusted Prices v3 possui "
            "eventos ainda pendentes."
        )

    if invalid_version > 0:
        raise ValueError(
            "adjusted_prices_version inválida."
        )

    if invalid_source > 0:
        raise ValueError(
            "adjusted_prices_source inválida."
        )

    if invalid_ca_source > 0:
        raise ValueError(
            "corporate_action_source inválida."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Structural behavior validation
# ============================================================

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


# ============================================================
# Economic event validation
# ============================================================

def validate_economic_event_behavior(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    """
    Mostra explicitamente o efeito econômico
    das amortizações.

    Esta validação é importante porque v3
    deixa de assumir que todo valor econômico
    é caixa.
    """

    economic_events = confirmed_actions[
        confirmed_actions[
            "event_type"
        ].isin(
            ECONOMIC_EVENT_TYPES
        )
    ]

    if economic_events.empty:
        return

    print(
        "\n======================================"
    )
    print(
        "Validação - Economic Corporate Actions"
    )
    print(
        "======================================"
    )

    failures = []

    for action in (
        economic_events.itertuples(
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

        cash = float(
            event_row[
                "cash_amount_per_unit_raw"
            ]
        )

        in_kind = float(
            event_row[
                "in_kind_amount_per_unit_raw"
            ]
        )

        total_value = float(
            event_row[
                "corporate_action_value_per_unit_raw"
            ]
        )

        raw_return = event_row[
            "daily_return_raw"
        ]

        adjusted_price_return = event_row[
            "daily_return_adjusted_price"
        ]

        economic_return = event_row[
            "daily_return_economic"
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
            f"  Cash component: "
            f"{cash:.9f}"
        )

        print(
            f"  In-kind component: "
            f"{in_kind:.9f}"
        )

        print(
            f"  Total economic value: "
            f"{total_value:.9f}"
        )

        if in_kind > 0:
            print(
                "  In-kind asset: "
                f"{action.in_kind_asset_ticker}"
            )

            print(
                "  In-kind quantity/unit: "
                f"{action.in_kind_quantity_per_unit:.9f}"
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
            "Falha na validação de "
            "Corporate Actions econômicos: "
            f"{failures}"
        )


# ============================================================
# VIUR11 regression check
# ============================================================

def validate_viur11_semantics(
    dataframe: pd.DataFrame,
    confirmed_actions: pd.DataFrame,
) -> None:
    """
    Regression check específico para o
    evento que motivou a evolução v2 -> v3.

    VIUR11 não pode voltar a ser modelado
    como 100% cash.
    """

    viur_actions = confirmed_actions[
        confirmed_actions[
            "ticker"
        ].eq(
            "VIUR11"
        )
        &
        confirmed_actions[
            "event_type"
        ].eq(
            "AMORTIZATION"
        )
    ]

    print(
        "\n======================================"
    )
    print(
        "Regression Check - VIUR11 in-kind"
    )
    print(
        "======================================"
    )

    if viur_actions.empty:
        print(
            "Nenhum evento VIUR11 confirmado."
        )

        return

    if len(viur_actions) != 1:
        raise ValueError(
            "Quantidade inesperada de eventos "
            "VIUR11 confirmados."
        )

    action = viur_actions.iloc[0]

    event_row = dataframe[
        dataframe[
            "ticker"
        ].eq(
            "VIUR11"
        )
        &
        dataframe[
            "trade_date"
        ].eq(
            action[
                "event_date"
            ]
        )
    ]

    if len(event_row) != 1:
        raise ValueError(
            "VIUR11 não possui exatamente "
            "uma linha na event_date."
        )

    event_row = event_row.iloc[0]

    cash = float(
        event_row[
            "cash_amount_per_unit_raw"
        ]
    )

    in_kind = float(
        event_row[
            "in_kind_amount_per_unit_raw"
        ]
    )

    total_value = float(
        event_row[
            "corporate_action_value_per_unit_raw"
        ]
    )

    asset_ticker = event_row[
        "confirmed_in_kind_asset_ticker"
    ]

    quantity = event_row[
        "confirmed_in_kind_quantity_per_unit"
    ]

    print(
        f"Cash: "
        f"{cash:.9f}"
    )

    print(
        f"In-kind: "
        f"{in_kind:.9f}"
    )

    print(
        f"Total economic value: "
        f"{total_value:.9f}"
    )

    print(
        f"In-kind asset: "
        f"{asset_ticker}"
    )

    print(
        "In-kind quantity per VIUR11: "
        f"{quantity:.9f}"
    )

    if cash <= 0:
        raise ValueError(
            "VIUR11 deveria possuir "
            "componente cash positivo."
        )

    if in_kind <= 0:
        raise ValueError(
            "VIUR11 deveria possuir "
            "componente in-kind positivo."
        )

    if asset_ticker != "TRXF11":
        raise ValueError(
            "VIUR11 deveria possuir "
            "TRXF11 como ativo in-kind."
        )

    if not np.isclose(
        cash + in_kind,
        total_value,
        rtol=1e-8,
        atol=1e-8,
    ):
        raise ValueError(
            "VIUR11 possui componentes "
            "econômicos inconsistentes."
        )

    print(
        "\nSemântica VIUR11 aprovada."
    )


# ============================================================
# Summary
# ============================================================

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
                "cash_amount_per_unit_raw"
            ]
            > 0
        ).sum()
    )

    in_kind_rows = int(
        (
            dataframe[
                "in_kind_amount_per_unit_raw"
            ]
            > 0
        ).sum()
    )

    economic_rows = int(
        (
            dataframe[
                "corporate_action_value_per_unit_raw"
            ]
            > 0
        ).sum()
    )

    pending_rows = int(
        dataframe[
            "pending_review_on_date"
        ].sum()
    )

    structural_actions = int(
        confirmed_actions[
            "event_type"
        ]
        .isin(
            STRUCTURAL_EVENT_TYPES
        )
        .sum()
    )

    economic_actions = int(
        confirmed_actions[
            "event_type"
        ]
        .isin(
            ECONOMIC_EVENT_TYPES
        )
        .sum()
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
        f"Source: "
        f"{ADJUSTED_PRICES_SOURCE}"
    )

    print(
        "Corporate Action Source: "
        f"{CORPORATE_ACTION_SOURCE}"
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
        "Structural Corporate Actions: "
        f"{structural_actions:,}"
    )

    print(
        "Economic Corporate Actions: "
        f"{economic_actions:,}"
    )

    print(
        "Linhas historicamente ajustadas "
        "por fator estrutural: "
        f"{structural_rows:,}"
    )

    print(
        "Linhas com componente cash: "
        f"{cash_rows:,}"
    )

    print(
        "Linhas com componente in-kind: "
        f"{in_kind_rows:,}"
    )

    print(
        "Linhas com valor econômico "
        f"corporativo: {economic_rows:,}"
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


# ============================================================
# Output contract
# ============================================================

def select_output_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Define contrato físico do Adjusted
    Prices v3.
    """

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

        #
        # Economic components v3
        #
        "cash_amount_per_unit_raw",
        "cash_amount_per_unit_adjusted",

        "in_kind_amount_per_unit_raw",
        "in_kind_amount_per_unit_adjusted",

        "corporate_action_value_per_unit_raw",
        "corporate_action_value_per_unit_adjusted",

        #
        # Legacy aliases:
        # cash only
        #
        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        "previous_close_price_raw",
        "previous_close_price_adjusted",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        #
        # Detector information
        #
        "review_status_on_date",
        "event_type_on_date",
        "discontinuity_confidence_on_date",

        "confirmed_action_on_date",
        "pending_review_on_date",

        #
        # Governed action payload
        #
        "confirmed_event_type",
        "confirmed_quantity_multiplier",
        "confirmed_price_adjustment_factor",

        "confirmed_cash_amount_per_unit",
        "confirmed_in_kind_amount_per_unit",
        "confirmed_total_economic_value_per_unit",

        "confirmed_in_kind_asset_ticker",
        "confirmed_in_kind_quantity_per_unit",

        "confirmed_corporate_action_record_date",
        "confirmed_corporate_action_effective_date",
        "confirmed_cash_payment_date",
        "confirmed_in_kind_delivery_date",
        "confirmed_first_post_event_trade_date",

        "confirmed_action_source",
        "confirmed_action_confirmation_date",
        "confirmed_governance_review_date",

        #
        # Market identity / evidence
        #
        "ticker_resolution_status",
        "market_evidence_confidence",

        #
        # Metadata
        #
        "adjusted_prices_version",
        "adjusted_prices_source",
        "corporate_action_source",
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
        "Construindo FII Corporate Action "
        "Adjusted Prices..."
    )

    print(
        f"Version: "
        f"{ADJUSTED_PRICES_VERSION}"
    )

    print(
        f"Source: "
        f"{ADJUSTED_PRICES_SOURCE}"
    )

    print(
        "Corporate Action Source: "
        f"{CORPORATE_ACTION_SOURCE}"
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

    validate_discontinuity_contract(
        discontinuities
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

    validate_economic_event_behavior(
        dataframe=adjusted,
        confirmed_actions=confirmed_actions,
    )

    validate_viur11_semantics(
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
        "Adjusted Prices v3 usa diretamente "
        "a Silver FII Daily Prices."
    )

    print(
        "Corporate Actions vêm de "
        "Price Discontinuities v5 "
        "com Registry v2."
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
        "AMORTIZATION usa agora o valor "
        "econômico total no retorno."
    )

    print(
        "Cash e in-kind permanecem "
        "componentes separados."
    )

    print(
        "VIUR11 não é mais representado "
        "como amortização 100% cash."
    )

    print(
        "cash_flow_per_unit foi preservado "
        "temporariamente como alias de "
        "cash puro para migração downstream."
    )

    print(
        "Eventos não confirmados não geram "
        "ajuste automático."
    )

    print(
        "Nenhum evento PENDING_REVIEW é "
        "aceito nesta camada."
    )


if __name__ == "__main__":
    main()