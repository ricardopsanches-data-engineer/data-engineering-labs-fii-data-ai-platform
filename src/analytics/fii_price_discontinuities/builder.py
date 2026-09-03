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

REVIEW_PATH = (
    PROJECT_ROOT
    / "config"
    / "corporate_actions"
    / "fii_corporate_action_reviews.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_discontinuities"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_price_discontinuities.parquet"
)


# ============================================================
# Version / source
# ============================================================

DISCONTINUITY_VERSION = "v5"

DISCONTINUITY_SOURCE = (
    "SILVER_FII_DAILY_PRICES"
)


# ============================================================
# Detection policy
# ============================================================

PARTITION_PATTERN = re.compile(
    r"year=(\d{4}).*month=(\d{2}).*day=(\d{2})"
)


COMMON_FACTORS = [
    0.05,
    0.10,
    0.20,
    0.25,
    0.50,
    2.00,
    4.00,
    5.00,
    10.00,
    20.00,
]


FACTOR_TOLERANCE = 0.10


MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN = 0.30

LEGACY_V4_THRESHOLD = 0.50


DETECTION_POLICY = (
    "ABS_DAILY_RETURN_GTE_30_PERCENT"
)


REVIEW_POLICY = (
    "ALL_DETECTED_CANDIDATES_REQUIRE_REVIEW"
)


# ============================================================
# Governance contract
# ============================================================

VALID_REVIEW_STATUSES = {
    "PENDING_REVIEW",
    "CONFIRMED",
    "REJECTED",
    "NOT_APPLICABLE",
}


VALID_EVENT_TYPES = {
    "UNKNOWN",
    "SPLIT",
    "REVERSE_SPLIT",
    "AMORTIZATION",
    "OTHER",
}


REVIEW_COLUMNS = [
    "ticker",
    "event_date",
    "review_status",
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
    "review_notes",
]


DATE_REVIEW_COLUMNS = [
    "event_date",
    "corporate_action_record_date",
    "corporate_action_effective_date",
    "cash_payment_date",
    "in_kind_delivery_date",
    "first_post_event_trade_date",
    "confirmation_date",
    "governance_review_date",
]


NUMERIC_REVIEW_COLUMNS = [
    "quantity_multiplier",
    "price_adjustment_factor",
    "cash_amount_per_unit",
    "in_kind_amount_per_unit",
    "total_economic_value_per_unit",
    "in_kind_quantity_per_unit",
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
        str(
            path.parent
        )
    )

    if match is None:
        raise ValueError(
            "Não foi possível identificar "
            "a data da partição: "
            f"{path}"
        )

    return (
        int(
            match.group(1)
        ),
        int(
            match.group(2)
        ),
        int(
            match.group(3)
        ),
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
            "Nenhuma Silver de preços "
            "encontrada em "
            f"{base_directory}"
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
    Valida contrato mínimo da partição
    usada pelo detector.
    """

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
            f"Arquivo {source_path} possui "
            "colunas ausentes: "
            f"{missing_columns}"
        )


def load_silver_prices(
    silver_files: list[Path],
) -> pd.DataFrame:
    """
    Carrega diretamente as partições
    Silver.

    O detector continua independente
    de Price History e das camadas Gold.
    """

    dataframes: list[
        pd.DataFrame
    ] = []

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
        (
            year,
            month,
            day,
        ) = extract_partition_date(
            path
        )

        print(
            f"[{index}/{len(silver_files)}] "
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

        dataframe = pd.read_parquet(
            path,
            columns=[
                "trade_date",
                "ticker",
                "cnpj",
                "codigo_cvm",
                "close_price",
            ],
        )

        validate_silver_partition_schema(
            dataframe=dataframe,
            source_path=path,
        )

        dataframes.append(
            dataframe
        )

    dataframe = pd.concat(
        dataframes,
        ignore_index=True,
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


def validate_source(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida a fonte Silver consolidada.
    """

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
            "Colunas ausentes: "
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

    null_counts = (
        dataframe[
            required_columns
        ]
        .isna()
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

    non_finite_prices = int(
        (
            dataframe[
                "close_price"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "close_price"
                ]
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Fonte Silver"
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
        f"Preços inválidos: "
        f"{invalid_prices:,}"
    )

    print(
        f"Preços não finitos: "
        f"{non_finite_prices:,}"
    )

    print(
        "\nNulos:"
    )

    for column in required_columns:
        print(
            f"  {column}: "
            f"{int(null_counts[column]):,}"
        )

    if duplicate_count > 0:
        raise ValueError(
            "Fonte possui duplicidades."
        )

    if invalid_prices > 0:
        raise ValueError(
            "Fonte possui preços inválidos."
        )

    if non_finite_prices > 0:
        raise ValueError(
            "Fonte possui preços não finitos."
        )

    if int(
        null_counts.sum()
    ) > 0:
        raise ValueError(
            "Fonte possui campos "
            "obrigatórios nulos."
        )

    print(
        "\nData Quality da fonte aprovada."
    )


# ============================================================
# Review registry v2
# ============================================================

def load_reviews() -> pd.DataFrame:
    """
    Carrega decisões humanas/governadas.

    Registry v2 contém também o payload
    econômico e temporal das Corporate
    Actions confirmadas.

    O detector nunca transforma candidato
    automaticamente em corporate action.
    """

    if not REVIEW_PATH.exists():
        print(
            "\nArquivo de reviews "
            "não encontrado."
        )

        return pd.DataFrame(
            columns=REVIEW_COLUMNS
        )

    reviews = pd.read_csv(
        REVIEW_PATH,
        dtype={
            "ticker": "string",
            "review_status": "string",
            "event_type": "string",
            "in_kind_asset_ticker": "string",
            "confirmation_source": "string",
            "review_notes": "string",
        },
    )

    missing_columns = [
        column
        for column in REVIEW_COLUMNS
        if column not in reviews.columns
    ]

    if missing_columns:
        raise ValueError(
            "Arquivo de reviews possui "
            "schema incompatível com "
            "Registry v2."
            "\nColunas ausentes: "
            f"{missing_columns}"
        )

    reviews = reviews[
        REVIEW_COLUMNS
    ].copy()

    if reviews.empty:
        print(
            "\nArquivo de reviews carregado."
        )

        print(
            "Reviews cadastrados: 0"
        )

        return reviews

    reviews[
        "ticker"
    ] = (
        reviews[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    reviews[
        "review_status"
    ] = (
        reviews[
            "review_status"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    reviews[
        "event_type"
    ] = (
        reviews[
            "event_type"
        ]
        .fillna(
            "UNKNOWN"
        )
        .astype("string")
        .str.strip()
        .str.upper()
        .replace(
            "",
            "UNKNOWN",
        )
    )

    reviews[
        "in_kind_asset_ticker"
    ] = (
        reviews[
            "in_kind_asset_ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    for column in DATE_REVIEW_COLUMNS:
        reviews[
            column
        ] = pd.to_datetime(
            reviews[
                column
            ],
            errors="coerce",
        )

    for column in NUMERIC_REVIEW_COLUMNS:
        reviews[
            column
        ] = pd.to_numeric(
            reviews[
                column
            ],
            errors="coerce",
        )

    validate_reviews(
        reviews
    )

    print(
        "\nArquivo de reviews carregado."
    )

    print(
        f"Reviews cadastrados: "
        f"{len(reviews):,}"
    )

    confirmed_count = int(
        reviews[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
        .sum()
    )

    print(
        "Corporate Actions CONFIRMED: "
        f"{confirmed_count:,}"
    )

    return reviews


def validate_reviews(
    reviews: pd.DataFrame,
) -> None:
    """
    Valida Registry v2.

    Regras financeiras mais fortes são
    aplicadas apenas às Corporate Actions
    CONFIRMED.
    """

    if reviews.empty:
        return

    missing_columns = [
        column
        for column in REVIEW_COLUMNS
        if column not in reviews.columns
    ]

    if missing_columns:
        raise ValueError(
            "Registry v2 possui colunas "
            "ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        reviews.duplicated(
            subset=[
                "ticker",
                "event_date",
            ]
        ).sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Arquivo de reviews possui "
            "duplicidade "
            "(ticker + event_date)."
        )

    if reviews[
        "event_date"
    ].isna().any():
        raise ValueError(
            "Arquivo de reviews possui "
            "event_date inválida."
        )

    if reviews[
        "ticker"
    ].isna().any():
        raise ValueError(
            "Arquivo de reviews possui "
            "ticker vazio."
        )

    invalid_statuses = sorted(
        set(
            reviews[
                "review_status"
            ]
            .dropna()
            .tolist()
        )
        - VALID_REVIEW_STATUSES
    )

    if invalid_statuses:
        raise ValueError(
            "review_status inválidos: "
            f"{invalid_statuses}"
        )

    if reviews[
        "review_status"
    ].isna().any():
        raise ValueError(
            "Arquivo de reviews possui "
            "review_status vazio."
        )

    invalid_event_types = sorted(
        set(
            reviews[
                "event_type"
            ]
            .dropna()
            .tolist()
        )
        - VALID_EVENT_TYPES
    )

    if invalid_event_types:
        raise ValueError(
            "event_type inválidos: "
            f"{invalid_event_types}"
        )

    confirmed = reviews[
        reviews[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
    ].copy()

    if confirmed.empty:
        return

    invalid_unknown = (
        confirmed[
            "event_type"
        ]
        .eq(
            "UNKNOWN"
        )
    )

    if invalid_unknown.any():
        raise ValueError(
            "Review CONFIRMED não pode "
            "ter event_type UNKNOWN."
        )

    missing_source = (
        confirmed[
            "confirmation_source"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
    )

    if missing_source.any():
        raise ValueError(
            "Reviews CONFIRMED exigem "
            "confirmation_source."
        )

    #
    # confirmation_date é campo legado.
    #
    # Não é mais usado como fonte de
    # semântica financeira, mas permanece
    # obrigatório para compatibilidade com
    # o histórico já governado.
    #
    if confirmed[
        "confirmation_date"
    ].isna().any():
        raise ValueError(
            "Reviews CONFIRMED exigem "
            "confirmation_date legacy."
        )

    missing_first_post_trade = (
        confirmed[
            "first_post_event_trade_date"
        ]
        .isna()
    )

    if missing_first_post_trade.any():
        raise ValueError(
            "Corporate Action CONFIRMED exige "
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

    record_date_after_trade = (
        confirmed[
            "corporate_action_record_date"
        ]
        .notna()
        &
        (
            confirmed[
                "corporate_action_record_date"
            ]
            >
            confirmed[
                "first_post_event_trade_date"
            ]
        )
    )

    if record_date_after_trade.any():
        invalid_rows = confirmed.loc[
            record_date_after_trade,
            [
                "ticker",
                "event_date",
                "corporate_action_record_date",
                "first_post_event_trade_date",
            ],
        ]

        raise ValueError(
            "corporate_action_record_date "
            "posterior ao primeiro trade "
            "pós-evento:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    split_events = confirmed[
        confirmed[
            "event_type"
        ].isin(
            [
                "SPLIT",
                "REVERSE_SPLIT",
            ]
        )
    ]

    if not split_events.empty:
        invalid_quantity = (
            split_events[
                "quantity_multiplier"
            ].isna()
            |
            (
                split_events[
                    "quantity_multiplier"
                ]
                <= 0
            )
        )

        if invalid_quantity.any():
            raise ValueError(
                "SPLIT/REVERSE_SPLIT "
                "CONFIRMED exigem "
                "quantity_multiplier > 0."
            )

        invalid_price_factor = (
            split_events[
                "price_adjustment_factor"
            ].isna()
            |
            (
                split_events[
                    "price_adjustment_factor"
                ]
                <= 0
            )
        )

        if invalid_price_factor.any():
            raise ValueError(
                "SPLIT/REVERSE_SPLIT "
                "CONFIRMED exigem "
                "price_adjustment_factor > 0."
            )

        reciprocal_product = (
            split_events[
                "quantity_multiplier"
            ]
            * split_events[
                "price_adjustment_factor"
            ]
        )

        reciprocal_error = (
            reciprocal_product
            - 1.0
        ).abs()

        if (
            reciprocal_error
            > 0.01
        ).any():
            raise ValueError(
                "Para SPLIT/REVERSE_SPLIT, "
                "quantity_multiplier * "
                "price_adjustment_factor "
                "deve ser aproximadamente 1."
            )

    amortizations = confirmed[
        confirmed[
            "event_type"
        ]
        .eq(
            "AMORTIZATION"
        )
    ].copy()

    if not amortizations.empty:
        invalid_total_value = (
            amortizations[
                "total_economic_value_per_unit"
            ].isna()
            |
            (
                amortizations[
                    "total_economic_value_per_unit"
                ]
                <= 0
            )
        )

        if invalid_total_value.any():
            raise ValueError(
                "AMORTIZATION CONFIRMED exige "
                "total_economic_value_per_unit > 0."
            )

        negative_cash = (
            amortizations[
                "cash_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            < 0
        )

        if negative_cash.any():
            raise ValueError(
                "AMORTIZATION possui "
                "cash_amount_per_unit negativo."
            )

        negative_in_kind = (
            amortizations[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            < 0
        )

        if negative_in_kind.any():
            raise ValueError(
                "AMORTIZATION possui "
                "in_kind_amount_per_unit negativo."
            )

        component_sum = (
            amortizations[
                "cash_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .astype(float)
            +
            amortizations[
                "in_kind_amount_per_unit"
            ]
            .fillna(
                0.0
            )
            .astype(float)
        )

        total_value = (
            amortizations[
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
            invalid_rows = amortizations.loc[
                component_mismatch,
                [
                    "ticker",
                    "event_date",
                    "cash_amount_per_unit",
                    "in_kind_amount_per_unit",
                    "total_economic_value_per_unit",
                ],
            ]

            raise ValueError(
                "Componentes econômicos da "
                "AMORTIZATION não fecham:\n"
                f"{invalid_rows.to_string(index=False)}"
            )

        in_kind_events = amortizations[
            amortizations[
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
                    "AMORTIZATION in-kind exige "
                    "in_kind_asset_ticker."
                )

            invalid_quantity = (
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

            if invalid_quantity.any():
                raise ValueError(
                    "AMORTIZATION in-kind exige "
                    "in_kind_quantity_per_unit > 0."
                )


# ============================================================
# Price movement calculation
# ============================================================

def calculate_price_movements(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula movimento entre observações
    consecutivas do mesmo ticker.
    """

    ordered = dataframe.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    ordered[
        "previous_trade_date"
    ] = (
        ordered
        .groupby(
            "ticker",
            sort=False,
        )[
            "trade_date"
        ]
        .shift(1)
    )

    ordered[
        "previous_close_price"
    ] = (
        ordered
        .groupby(
            "ticker",
            sort=False,
        )[
            "close_price"
        ]
        .shift(1)
    )

    ordered[
        "price_factor"
    ] = (
        ordered[
            "close_price"
        ]
        / ordered[
            "previous_close_price"
        ]
    )

    ordered[
        "daily_return"
    ] = (
        ordered[
            "price_factor"
        ]
        - 1.0
    )

    return ordered


def nearest_common_factor(
    factor: float,
) -> tuple[
    float,
    float,
]:
    """
    Identifica o fator corporativo comum
    mais próximo.

    Isso é evidência para triagem,
    nunca confirmação automática.
    """

    nearest = min(
        COMMON_FACTORS,
        key=lambda candidate: abs(
            factor
            - candidate
        ),
    )

    relative_error = (
        abs(
            factor
            - nearest
        )
        / nearest
    )

    return (
        float(
            nearest
        ),
        float(
            relative_error
        ),
    )


# ============================================================
# Candidate classification
# ============================================================

def classify_candidate(
    factor: float,
    daily_return: float,
) -> tuple[
    float,
    float,
    bool,
    str,
    str,
    str,
    str,
]:
    """
    Classifica uma observação.

    PRINCÍPIO v5:

    detector != decisão.

    Qualquer movimento que ultrapassa
    o threshold é somente um candidato
    e recebe PENDING_REVIEW.

    O CSV governado é o único responsável
    por CONFIRMED / REJECTED /
    NOT_APPLICABLE.
    """

    (
        nearest_factor,
        relative_error,
    ) = nearest_common_factor(
        factor
    )

    factor_match = (
        relative_error
        <= FACTOR_TOLERANCE
    )

    absolute_return = abs(
        daily_return
    )

    if (
        absolute_return
        < MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN
    ):
        return (
            nearest_factor,
            relative_error,
            factor_match,
            "NORMAL_PRICE_MOVE",
            "NONE",
            "NOT_APPLICABLE",
            "BELOW_CANDIDATE_THRESHOLD",
        )

    if factor_match:
        classification = (
            "POSSIBLE_CORPORATE_FACTOR"
        )

        confidence = (
            "HIGH"
            if relative_error <= 0.05
            else "MEDIUM"
        )

        candidate_reason = (
            "EXTREME_RETURN_AND_COMMON_FACTOR_MATCH"
        )

    else:
        classification = (
            "LARGE_SINGLE_DAY_MOVE"
        )

        if (
            absolute_return
            >= LEGACY_V4_THRESHOLD
        ):
            confidence = "MEDIUM"

        else:
            confidence = "LOW"

        candidate_reason = (
            "EXTREME_RETURN_WITHOUT_COMMON_FACTOR_MATCH"
        )

    review_status = (
        "PENDING_REVIEW"
    )

    return (
        nearest_factor,
        relative_error,
        factor_match,
        classification,
        confidence,
        review_status,
        candidate_reason,
    )


# ============================================================
# Candidate builder
# ============================================================

def build_discontinuities(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói candidatos a descontinuidade.

    A camada é deliberadamente conservadora:
    gera candidatos e deixa a decisão para
    o registry governado.
    """

    movements = calculate_price_movements(
        dataframe
    )

    movements = movements[
        movements[
            "previous_close_price"
        ].notna()
    ].copy()

    records: list[
        dict[str, object]
    ] = []

    created_at = datetime.now(
        timezone.utc
    )

    for row in movements.itertuples(
        index=False
    ):
        daily_return = float(
            row.daily_return
        )

        factor = float(
            row.price_factor
        )

        if not np.isfinite(
            daily_return
        ):
            continue

        if not np.isfinite(
            factor
        ):
            continue

        (
            nearest_factor,
            relative_error,
            factor_match,
            classification,
            confidence,
            review_status,
            candidate_reason,
        ) = classify_candidate(
            factor=factor,
            daily_return=daily_return,
        )

        if (
            classification
            == "NORMAL_PRICE_MOVE"
        ):
            continue

        absolute_daily_return = abs(
            daily_return
        )

        detected_by_v4_threshold = (
            absolute_daily_return
            >= LEGACY_V4_THRESHOLD
        )

        newly_visible_in_v5_band = (
            (
                absolute_daily_return
                >= MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN
            )
            and
            (
                absolute_daily_return
                < LEGACY_V4_THRESHOLD
            )
        )

        records.append(
            {
                "ticker": (
                    row.ticker
                ),

                "cnpj": (
                    row.cnpj
                ),

                "codigo_cvm": (
                    row.codigo_cvm
                ),

                "previous_trade_date": (
                    row.previous_trade_date
                ),

                "event_date": (
                    row.trade_date
                ),

                "price_before": float(
                    row.previous_close_price
                ),

                "price_after": float(
                    row.close_price
                ),

                "daily_return": (
                    daily_return
                ),

                "daily_return_pct": (
                    daily_return
                    * 100.0
                ),

                "absolute_daily_return": (
                    absolute_daily_return
                ),

                "observed_factor": (
                    factor
                ),

                "nearest_common_factor": (
                    nearest_factor
                ),

                "factor_relative_error": (
                    relative_error
                ),

                "factor_match": (
                    factor_match
                ),

                "classification": (
                    classification
                ),

                "confidence": (
                    confidence
                ),

                "candidate_reason": (
                    candidate_reason
                ),

                "review_status": (
                    review_status
                ),

                "event_type": (
                    "UNKNOWN"
                ),

                "quantity_multiplier": (
                    np.nan
                ),

                "price_adjustment_factor": (
                    np.nan
                ),

                "cash_amount_per_unit": (
                    np.nan
                ),

                "in_kind_amount_per_unit": (
                    np.nan
                ),

                "total_economic_value_per_unit": (
                    np.nan
                ),

                "in_kind_asset_ticker": (
                    None
                ),

                "in_kind_quantity_per_unit": (
                    np.nan
                ),

                "corporate_action_record_date": (
                    pd.NaT
                ),

                "corporate_action_effective_date": (
                    pd.NaT
                ),

                "cash_payment_date": (
                    pd.NaT
                ),

                "in_kind_delivery_date": (
                    pd.NaT
                ),

                "first_post_event_trade_date": (
                    pd.NaT
                ),

                "confirmation_source": (
                    None
                ),

                "confirmation_date": (
                    pd.NaT
                ),

                "governance_review_date": (
                    pd.NaT
                ),

                "review_notes": (
                    None
                ),

                "is_confirmed_corporate_action": (
                    False
                ),

                "detected_by_v4_threshold": (
                    detected_by_v4_threshold
                ),

                "newly_visible_in_v5_band": (
                    newly_visible_in_v5_band
                ),

                "candidate_threshold": (
                    MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN
                ),

                "detection_policy": (
                    DETECTION_POLICY
                ),

                "review_policy": (
                    REVIEW_POLICY
                ),

                "discontinuity_version": (
                    DISCONTINUITY_VERSION
                ),

                "discontinuity_source": (
                    DISCONTINUITY_SOURCE
                ),

                "created_at": (
                    created_at
                ),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# Governance coverage
# ============================================================

def validate_review_coverage(
    discontinuities: pd.DataFrame,
    reviews: pd.DataFrame,
) -> None:
    """
    Garante que toda decisão governada
    previamente continua correspondendo
    a um candidato detectado.
    """

    if reviews.empty:
        return

    if discontinuities.empty:
        raise ValueError(
            "Existem reviews governados, "
            "mas nenhum candidato foi "
            "detectado."
        )

    detected_keys = set(
        zip(
            discontinuities[
                "ticker"
            ],
            discontinuities[
                "event_date"
            ],
        )
    )

    missing_reviews: list[
        dict[str, object]
    ] = []

    for row in reviews.itertuples(
        index=False
    ):
        key = (
            row.ticker,
            row.event_date,
        )

        if key not in detected_keys:
            missing_reviews.append(
                {
                    "ticker": (
                        row.ticker
                    ),

                    "event_date": (
                        row.event_date
                    ),

                    "review_status": (
                        row.review_status
                    ),

                    "event_type": (
                        row.event_type
                    ),
                }
            )

    print(
        "\n======================================"
    )
    print(
        "Governança - Review Coverage"
    )
    print(
        "======================================"
    )

    print(
        f"Reviews cadastrados: "
        f"{len(reviews):,}"
    )

    print(
        "Reviews sem candidato detectado: "
        f"{len(missing_reviews):,}"
    )

    if missing_reviews:
        missing_dataframe = (
            pd.DataFrame(
                missing_reviews
            )
        )

        raise ValueError(
            "Existem decisões governadas "
            "sem evento correspondente no "
            "detector:\n"
            f"{missing_dataframe.to_string(index=False)}"
        )

    print(
        "\nCobertura de reviews aprovada."
    )


# ============================================================
# Apply governed decisions
# ============================================================

def apply_reviews(
    discontinuities: pd.DataFrame,
    reviews: pd.DataFrame,
) -> pd.DataFrame:
    """
    Sobrepõe decisões do Registry v2
    aos defaults PENDING_REVIEW do detector.

    Todos os atributos econômicos e
    temporais continuam sendo governados,
    nunca inferidos pelo detector.
    """

    if reviews.empty:
        return discontinuities

    merge_columns = REVIEW_COLUMNS.copy()

    manual = reviews[
        merge_columns
    ].copy()

    manual = manual.rename(
        columns={
            column: (
                f"{column}_manual"
            )
            for column in merge_columns
            if column not in {
                "ticker",
                "event_date",
            }
        }
    )

    result = discontinuities.merge(
        manual,
        how="left",
        on=[
            "ticker",
            "event_date",
        ],
        validate="one_to_one",
    )

    manual_mask = result[
        "review_status_manual"
    ].notna()

    columns_to_apply = [
        column
        for column in REVIEW_COLUMNS
        if column not in {
            "ticker",
            "event_date",
        }
    ]

    for column in columns_to_apply:
        manual_column = (
            f"{column}_manual"
        )

        result.loc[
            manual_mask,
            column,
        ] = result.loc[
            manual_mask,
            manual_column,
        ]

    result[
        "is_confirmed_corporate_action"
    ] = (
        result[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
    )

    manual_columns = [
        column
        for column in result.columns
        if column.endswith(
            "_manual"
        )
    ]

    result = result.drop(
        columns=manual_columns
    )

    return result


# ============================================================
# Output validation
# ============================================================

def validate_output(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida o contrato da camada v5,
    incluindo o payload governado do
    Registry v2.
    """

    required_columns = [
        "ticker",
        "cnpj",
        "codigo_cvm",

        "previous_trade_date",
        "event_date",

        "price_before",
        "price_after",

        "daily_return",
        "daily_return_pct",
        "absolute_daily_return",

        "observed_factor",
        "nearest_common_factor",
        "factor_relative_error",
        "factor_match",

        "classification",
        "confidence",
        "candidate_reason",

        "review_status",
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
        "review_notes",

        "is_confirmed_corporate_action",

        "detected_by_v4_threshold",
        "newly_visible_in_v5_band",

        "candidate_threshold",
        "detection_policy",
        "review_policy",

        "discontinuity_version",
        "discontinuity_source",
    ]

    if dataframe.empty:
        raise ValueError(
            "Nenhuma descontinuidade "
            "foi encontrada."
        )

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Output possui colunas "
            "obrigatórias ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "event_date",
            ]
        ).sum()
    )

    base_required_non_null = [
        "ticker",
        "cnpj",
        "codigo_cvm",
        "previous_trade_date",
        "event_date",
        "price_before",
        "price_after",
        "daily_return",
        "daily_return_pct",
        "absolute_daily_return",
        "observed_factor",
        "nearest_common_factor",
        "factor_relative_error",
        "factor_match",
        "classification",
        "confidence",
        "candidate_reason",
        "review_status",
        "event_type",
        "is_confirmed_corporate_action",
        "detected_by_v4_threshold",
        "newly_visible_in_v5_band",
        "candidate_threshold",
        "detection_policy",
        "review_policy",
        "discontinuity_version",
        "discontinuity_source",
    ]

    null_count = int(
        dataframe[
            base_required_non_null
        ]
        .isna()
        .sum()
        .sum()
    )

    invalid_statuses = sorted(
        set(
            dataframe[
                "review_status"
            ].tolist()
        )
        - VALID_REVIEW_STATUSES
    )

    invalid_event_types = sorted(
        set(
            dataframe[
                "event_type"
            ].tolist()
        )
        - VALID_EVENT_TYPES
    )

    flag_mismatch = int(
        (
            dataframe[
                "is_confirmed_corporate_action"
            ]
            != (
                dataframe[
                    "review_status"
                ]
                == "CONFIRMED"
            )
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "discontinuity_source"
            ]
            != DISCONTINUITY_SOURCE
        ).sum()
    )

    invalid_version = int(
        (
            dataframe[
                "discontinuity_version"
            ]
            != DISCONTINUITY_VERSION
        ).sum()
    )

    invalid_threshold = int(
        (
            ~np.isclose(
                dataframe[
                    "candidate_threshold"
                ].astype(float),
                MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN,
            )
        ).sum()
    )

    below_detection_threshold = int(
        (
            dataframe[
                "absolute_daily_return"
            ]
            < MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN
        ).sum()
    )

    invalid_band_overlap = int(
        (
            dataframe[
                "detected_by_v4_threshold"
            ]
            &
            dataframe[
                "newly_visible_in_v5_band"
            ]
        ).sum()
    )

    expected_new_band = (
        (
            dataframe[
                "absolute_daily_return"
            ]
            >= MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN
        )
        &
        (
            dataframe[
                "absolute_daily_return"
            ]
            < LEGACY_V4_THRESHOLD
        )
    )

    new_band_mismatch = int(
        (
            dataframe[
                "newly_visible_in_v5_band"
            ]
            != expected_new_band
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Discontinuidades"
    )
    print(
        "======================================"
    )

    print(
        f"Eventos: "
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
        f"Nulos obrigatórios base: "
        f"{null_count:,}"
    )

    print(
        "Inconsistências status x flag: "
        f"{flag_mismatch:,}"
    )

    print(
        "Fonte inválida: "
        f"{invalid_source:,}"
    )

    print(
        "Versão inválida: "
        f"{invalid_version:,}"
    )

    print(
        "Threshold metadata inválido: "
        f"{invalid_threshold:,}"
    )

    print(
        "Eventos abaixo do threshold: "
        f"{below_detection_threshold:,}"
    )

    print(
        "Sobreposição v4/v5 band inválida: "
        f"{invalid_band_overlap:,}"
    )

    print(
        "Mismatch da faixa nova v5: "
        f"{new_band_mismatch:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Eventos duplicados."
        )

    if null_count > 0:
        raise ValueError(
            "Campos obrigatórios base nulos."
        )

    if invalid_statuses:
        raise ValueError(
            "review_status inválidos: "
            f"{invalid_statuses}"
        )

    if invalid_event_types:
        raise ValueError(
            "event_type inválidos: "
            f"{invalid_event_types}"
        )

    if flag_mismatch > 0:
        raise ValueError(
            "Status de confirmação "
            "inconsistente."
        )

    if invalid_source > 0:
        raise ValueError(
            "Discontinuidades possuem "
            "source inconsistente."
        )

    if invalid_version > 0:
        raise ValueError(
            "Discontinuidades possuem "
            "version inconsistente."
        )

    if invalid_threshold > 0:
        raise ValueError(
            "Candidate threshold "
            "inconsistente."
        )

    if below_detection_threshold > 0:
        raise ValueError(
            "Existem candidatos abaixo "
            "do threshold v5."
        )

    if invalid_band_overlap > 0:
        raise ValueError(
            "Evento não pode pertencer "
            "simultaneamente às faixas "
            "v4 e nova v5."
        )

    if new_band_mismatch > 0:
        raise ValueError(
            "Flag newly_visible_in_v5_band "
            "inconsistente."
        )

    confirmed = dataframe[
        dataframe[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
    ].copy()

    if not confirmed.empty:
        validate_reviews(
            confirmed[
                REVIEW_COLUMNS
            ].copy()
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Specific regression checks
# ============================================================

def print_v5_regression_checks(
    dataframe: pd.DataFrame,
) -> None:
    """
    Verifica explicitamente os episódios
    que motivaram a evolução da v4 -> v5.
    """

    focus_tickers = [
        "KNPR11",
        "MFII11",
    ]

    focus = dataframe[
        dataframe[
            "ticker"
        ].isin(
            focus_tickers
        )
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Regression Check - v5 Blind Spot"
    )
    print(
        "======================================"
    )

    if focus.empty:
        print(
            "KNPR11/MFII11 não apareceram "
            "entre os candidatos."
        )

        return

    display_columns = [
        "ticker",
        "event_date",
        "price_before",
        "price_after",
        "daily_return_pct",
        "classification",
        "factor_match",
        "confidence",
        "review_status",
        "detected_by_v4_threshold",
        "newly_visible_in_v5_band",
    ]

    print(
        focus[
            display_columns
        ]
        .sort_values(
            [
                "event_date",
                "ticker",
            ]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# Summary
# ============================================================

def print_summary(
    dataframe: pd.DataFrame,
    silver_file_count: int,
) -> None:
    """
    Resumo operacional e de governança.
    """

    print(
        "\n======================================"
    )
    print(
        "Resumo - Price Discontinuities"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{DISCONTINUITY_VERSION}"
    )

    print(
        f"Source: "
        f"{DISCONTINUITY_SOURCE}"
    )

    print(
        "Candidate threshold: "
        f"{MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN * 100:.1f}%"
    )

    print(
        f"Detection policy: "
        f"{DETECTION_POLICY}"
    )

    print(
        f"Review policy: "
        f"{REVIEW_POLICY}"
    )

    print(
        f"Partições Silver: "
        f"{silver_file_count:,}"
    )

    print(
        f"Eventos: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    legacy_candidates = int(
        dataframe[
            "detected_by_v4_threshold"
        ].sum()
    )

    new_v5_candidates = int(
        dataframe[
            "newly_visible_in_v5_band"
        ].sum()
    )

    print(
        "\nCobertura por threshold:"
    )

    print(
        "  Detectáveis pela v4 "
        "(|return| >= 50%): "
        f"{legacy_candidates:,}"
    )

    print(
        "  Novos na v5 "
        "(30% <= |return| < 50%): "
        f"{new_v5_candidates:,}"
    )

    print(
        "\nClassificações:"
    )

    for value, count in (
        dataframe[
            "classification"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nCandidate Reasons:"
    )

    for value, count in (
        dataframe[
            "candidate_reason"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nConfidence:"
    )

    for value, count in (
        dataframe[
            "confidence"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nReview Status:"
    )

    for value, count in (
        dataframe[
            "review_status"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nEvent Types:"
    )

    for value, count in (
        dataframe[
            "event_type"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    confirmed = dataframe[
        dataframe[
            "is_confirmed_corporate_action"
        ]
    ]

    in_kind_confirmed = confirmed[
        confirmed[
            "in_kind_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        .gt(
            0.0
        )
    ]

    print(
        "\nCorporate Actions confirmados: "
        f"{len(confirmed):,}"
    )

    print(
        "Corporate Actions com componente "
        f"in-kind: {len(in_kind_confirmed):,}"
    )

    pending = dataframe[
        dataframe[
            "review_status"
        ]
        == "PENDING_REVIEW"
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Pendentes de revisão"
    )
    print(
        "======================================"
    )

    if pending.empty:
        print(
            "Nenhum evento pendente."
        )

    else:
        display = pending[
            [
                "ticker",
                "event_date",
                "price_before",
                "price_after",
                "daily_return_pct",
                "observed_factor",
                "nearest_common_factor",
                "factor_relative_error",
                "factor_match",
                "classification",
                "confidence",
                "candidate_reason",
                "newly_visible_in_v5_band",
            ]
        ].sort_values(
            [
                "event_date",
                "ticker",
            ]
        )

        print(
            display.to_string(
                index=False
            )
        )

    print(
        "\nArquivo de reviews:"
    )

    print(
        REVIEW_PATH
    )

    print(
        "\nArquivo de saída:"
    )

    print(
        OUTPUT_PATH
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    print(
        "Construindo camada de "
        "FII Price Discontinuities..."
    )

    print(
        f"Version: "
        f"{DISCONTINUITY_VERSION}"
    )

    print(
        f"Source: "
        f"{DISCONTINUITY_SOURCE}"
    )

    print(
        "Candidate threshold: "
        f"{MIN_CANDIDATE_ABSOLUTE_DAILY_RETURN * 100:.1f}%"
    )

    print(
        "Policy: detector gera candidatos; "
        "registry governado toma decisões."
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

    dataframe = load_silver_prices(
        silver_files
    )

    validate_source(
        dataframe
    )

    reviews = load_reviews()

    discontinuities = (
        build_discontinuities(
            dataframe
        )
    )

    validate_review_coverage(
        discontinuities=discontinuities,
        reviews=reviews,
    )

    discontinuities = apply_reviews(
        discontinuities=discontinuities,
        reviews=reviews,
    )

    validate_output(
        discontinuities
    )

    print_v5_regression_checks(
        discontinuities
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    discontinuities.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print_summary(
        dataframe=discontinuities,
        silver_file_count=len(
            silver_files
        ),
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "A fonte continua diretamente "
        "a Silver FII Daily Prices."
    )

    print(
        "Nenhuma dependência de "
        "FII Price History foi adicionada."
    )

    print(
        "Nenhum candidato novo foi "
        "confirmado ou descartado "
        "automaticamente."
    )

    print(
        "Decisões governadas existentes "
        "foram reaplicadas e validadas."
    )

    print(
        "Registry v2 foi propagado para "
        "o payload das Corporate Actions."
    )

    print(
        "Movimentos entre 30% e 50% agora "
        "entram explicitamente na fila "
        "de revisão."
    )

    print(
        "Nenhum preço bruto foi alterado."
    )


if __name__ == "__main__":
    main()