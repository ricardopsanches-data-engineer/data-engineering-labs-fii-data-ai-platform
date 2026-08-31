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


DISCONTINUITY_VERSION = "v3"


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

MIN_ABSOLUTE_DAILY_RETURN = 0.50


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
    "confirmation_source",
    "confirmation_date",
    "review_notes",
]


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

    return dataframe


def validate_source(
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


def load_reviews() -> pd.DataFrame:
    """
    Carrega decisões auditadas.

    Nenhum corporate action é confirmado
    automaticamente pelo detector.
    """

    if not REVIEW_PATH.exists():
        print(
            "\nArquivo de reviews não encontrado."
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
            "schema incompatível."
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
        "event_date"
    ] = pd.to_datetime(
        reviews[
            "event_date"
        ],
        errors="coerce",
    )

    reviews[
        "confirmation_date"
    ] = pd.to_datetime(
        reviews[
            "confirmation_date"
        ],
        errors="coerce",
    )

    numeric_columns = [
        "quantity_multiplier",
        "price_adjustment_factor",
        "cash_amount_per_unit",
    ]

    for column in numeric_columns:
        reviews[
            column
        ] = pd.to_numeric(
            reviews[
                column
            ],
            errors="coerce",
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

    return reviews


def validate_reviews(
    reviews: pd.DataFrame,
) -> None:
    if reviews.empty:
        return

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
        == "CONFIRMED"
    ].copy()

    if confirmed.empty:
        return

    invalid_unknown = confirmed[
        "event_type"
    ].eq(
        "UNKNOWN"
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

    if confirmed[
        "confirmation_date"
    ].isna().any():
        raise ValueError(
            "Reviews CONFIRMED exigem "
            "confirmation_date."
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
        == "AMORTIZATION"
    ]

    if not amortizations.empty:
        invalid_cash = (
            amortizations[
                "cash_amount_per_unit"
            ].isna()
            |
            (
                amortizations[
                    "cash_amount_per_unit"
                ]
                <= 0
            )
        )

        if invalid_cash.any():
            raise ValueError(
                "AMORTIZATION CONFIRMED exige "
                "cash_amount_per_unit > 0."
            )


def nearest_common_factor(
    factor: float,
) -> tuple[
    float,
    float,
]:
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
        float(nearest),
        float(relative_error),
    )


def calculate_price_movements(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
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
        - 1
    )

    return ordered


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
]:
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
        >= MIN_ABSOLUTE_DAILY_RETURN
        and factor_match
    ):
        classification = (
            "POSSIBLE_CORPORATE_FACTOR"
        )

        confidence = (
            "HIGH"
            if relative_error <= 0.05
            else "MEDIUM"
        )

        review_status = (
            "PENDING_REVIEW"
        )

    elif (
        absolute_return
        >= MIN_ABSOLUTE_DAILY_RETURN
    ):
        classification = (
            "LARGE_SINGLE_DAY_MOVE"
        )

        confidence = "LOW"

        review_status = (
            "NOT_APPLICABLE"
        )

    else:
        classification = (
            "NORMAL_PRICE_MOVE"
        )

        confidence = "NONE"

        review_status = (
            "NOT_APPLICABLE"
        )

    return (
        nearest_factor,
        relative_error,
        factor_match,
        classification,
        confidence,
        review_status,
    )


def build_discontinuities(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    movements = calculate_price_movements(
        dataframe
    )

    movements = movements[
        movements[
            "previous_close_price"
        ].notna()
    ].copy()

    records = []

    created_at = datetime.now(
        timezone.utc
    )

    for row in movements.itertuples(
        index=False
    ):
        (
            nearest_factor,
            relative_error,
            factor_match,
            classification,
            confidence,
            review_status,
        ) = classify_candidate(
            factor=float(
                row.price_factor
            ),
            daily_return=float(
                row.daily_return
            ),
        )

        if classification == (
            "NORMAL_PRICE_MOVE"
        ):
            continue

        records.append(
            {
                "ticker": row.ticker,
                "cnpj": row.cnpj,
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
                "daily_return": float(
                    row.daily_return
                ),
                "daily_return_pct": float(
                    row.daily_return
                    * 100
                ),
                "observed_factor": float(
                    row.price_factor
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
                "confirmation_source": (
                    None
                ),
                "confirmation_date": (
                    pd.NaT
                ),
                "review_notes": (
                    None
                ),
                "is_confirmed_corporate_action": (
                    False
                ),
                "discontinuity_version": (
                    DISCONTINUITY_VERSION
                ),
                "created_at": (
                    created_at
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def apply_reviews(
    discontinuities: pd.DataFrame,
    reviews: pd.DataFrame,
) -> pd.DataFrame:
    if reviews.empty:
        return discontinuities

    merge_columns = [
        "ticker",
        "event_date",
        "review_status",
        "event_type",
        "quantity_multiplier",
        "price_adjustment_factor",
        "cash_amount_per_unit",
        "confirmation_source",
        "confirmation_date",
        "review_notes",
    ]

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
        "review_status",
        "event_type",
        "quantity_multiplier",
        "price_adjustment_factor",
        "cash_amount_per_unit",
        "confirmation_source",
        "confirmation_date",
        "review_notes",
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
        == "CONFIRMED"
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


def validate_output(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "ticker",
        "cnpj",
        "codigo_cvm",
        "previous_trade_date",
        "event_date",
        "price_before",
        "price_after",
        "daily_return",
        "observed_factor",
        "classification",
        "confidence",
        "review_status",
        "event_type",
        "is_confirmed_corporate_action",
        "discontinuity_version",
    ]

    if dataframe.empty:
        raise ValueError(
            "Nenhuma descontinuidade "
            "foi encontrada."
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "event_date",
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
        f"Nulos obrigatórios: "
        f"{null_count:,}"
    )

    print(
        "Inconsistências status x flag: "
        f"{flag_mismatch:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Eventos duplicados."
        )

    if null_count > 0:
        raise ValueError(
            "Campos obrigatórios nulos."
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

    confirmed = dataframe[
        dataframe[
            "review_status"
        ]
        == "CONFIRMED"
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


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
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
        f"Eventos: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
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

    print(
        "\nCorporate Actions confirmados: "
        f"{len(confirmed):,}"
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
                "confidence",
            ]
        ].sort_values(
            [
                "confidence",
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


def main() -> None:
    print(
        "Construindo camada de "
        "FII Price Discontinuities..."
    )

    print(
        f"Version: "
        f"{DISCONTINUITY_VERSION}"
    )

    dataframe = (
        load_price_history()
    )

    validate_source(
        dataframe
    )

    reviews = (
        load_reviews()
    )

    discontinuities = (
        build_discontinuities(
            dataframe
        )
    )

    discontinuities = apply_reviews(
        discontinuities=discontinuities,
        reviews=reviews,
    )

    validate_output(
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
        discontinuities
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "Nenhum evento foi confirmado "
        "automaticamente."
    )

    print(
        "Nenhum preço bruto foi alterado."
    )


if __name__ == "__main__":
    main()