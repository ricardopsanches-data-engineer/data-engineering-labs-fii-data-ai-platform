from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
    / "quality"
    / "fii_corporate_action_review_queue"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_corporate_action_review_queue.parquet"
)


REVIEW_QUEUE_VERSION = "v1"

EXPECTED_DISCONTINUITY_VERSION = "v5"

EXPECTED_DISCONTINUITY_SOURCE = (
    "SILVER_FII_DAILY_PRICES"
)

EXPECTED_REVIEW_STATUS = (
    "PENDING_REVIEW"
)


VALID_PRIORITIES = {
    "P1",
    "P2",
    "P3",
    "P4",
}


def load_discontinuities() -> pd.DataFrame:
    """
    Carrega a camada Price Discontinuities v5.
    """

    if not DISCONTINUITIES_PATH.exists():
        raise FileNotFoundError(
            "Price Discontinuities não encontrado: "
            f"{DISCONTINUITIES_PATH}"
        )

    dataframe = pd.read_parquet(
        DISCONTINUITIES_PATH
    )

    dataframe[
        "event_date"
    ] = pd.to_datetime(
        dataframe[
            "event_date"
        ]
    )

    dataframe[
        "previous_trade_date"
    ] = pd.to_datetime(
        dataframe[
            "previous_trade_date"
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

    print(
        "Price Discontinuities: "
        f"{len(dataframe):,} eventos"
    )

    return dataframe


def get_unique_string(
    dataframe: pd.DataFrame,
    column: str,
) -> str:
    """
    Obtém exatamente um valor textual.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"Coluna ausente: {column}"
        )

    values = (
        dataframe[
            column
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    if len(values) != 1:
        raise ValueError(
            f"{column} ambígua: "
            f"{values}"
        )

    return values[0]


def validate_source_contract(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida o contrato mínimo da
    Price Discontinuities v5.
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

        "is_confirmed_corporate_action",

        "detected_by_v4_threshold",
        "newly_visible_in_v5_band",

        "candidate_threshold",
        "detection_policy",
        "review_policy",

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
            "colunas obrigatórias ausentes: "
            f"{missing_columns}"
        )

    version = get_unique_string(
        dataframe,
        "discontinuity_version",
    )

    source = get_unique_string(
        dataframe,
        "discontinuity_source",
    )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "event_date",
            ]
        ).sum()
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
        f"Version: {version}"
    )

    print(
        f"Source: {source}"
    )

    print(
        f"Eventos: "
        f"{len(dataframe):,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    if (
        version
        != EXPECTED_DISCONTINUITY_VERSION
    ):
        raise ValueError(
            "Review Queue v1 exige "
            "Price Discontinuities "
            f"{EXPECTED_DISCONTINUITY_VERSION}."
        )

    if (
        source
        != EXPECTED_DISCONTINUITY_SOURCE
    ):
        raise ValueError(
            "discontinuity_source "
            "incompatível."
        )

    if duplicate_count > 0:
        raise ValueError(
            "Price Discontinuities possui "
            "eventos duplicados."
        )


def calculate_review_priority(
    row: pd.Series,
) -> str:
    """
    Prioridade operacional.

    P1
        possível fator corporativo
        com confiança HIGH.

    P2
        possível fator corporativo
        com confiança MEDIUM.

    P3
        movimento absoluto >= 50%.

    P4
        demais candidatos entre
        30% e 50%.
    """

    classification = str(
        row[
            "classification"
        ]
    )

    confidence = str(
        row[
            "confidence"
        ]
    )

    absolute_return = float(
        row[
            "absolute_daily_return"
        ]
    )

    if (
        classification
        == "POSSIBLE_CORPORATE_FACTOR"
        and confidence
        == "HIGH"
    ):
        return "P1"

    if (
        classification
        == "POSSIBLE_CORPORATE_FACTOR"
        and confidence
        == "MEDIUM"
    ):
        return "P2"

    if absolute_return >= 0.50:
        return "P3"

    return "P4"


def calculate_priority_score(
    row: pd.Series,
) -> float:
    """
    Score auxiliar para ordenar eventos
    dentro da mesma prioridade.

    Não representa probabilidade de
    corporate action.
    """

    priority = str(
        row[
            "review_priority"
        ]
    )

    priority_base = {
        "P1": 400.0,
        "P2": 300.0,
        "P3": 200.0,
        "P4": 100.0,
    }[
        priority
    ]

    absolute_return = float(
        row[
            "absolute_daily_return"
        ]
    )

    factor_bonus = (
        20.0
        if bool(
            row[
                "factor_match"
            ]
        )
        else 0.0
    )

    new_band_bonus = (
        5.0
        if bool(
            row[
                "newly_visible_in_v5_band"
            ]
        )
        else 0.0
    )

    return float(
        priority_base
        + absolute_return
        * 100.0
        + factor_bonus
        + new_band_bonus
    )


def build_review_queue(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói somente a fila pendente.

    Nenhuma decisão governada é alterada.
    """

    pending = dataframe[
        dataframe[
            "review_status"
        ]
        == EXPECTED_REVIEW_STATUS
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Construindo Review Queue"
    )
    print(
        "======================================"
    )

    print(
        f"Candidatos pendentes: "
        f"{len(pending):,}"
    )

    if pending.empty:
        return pd.DataFrame()

    pending[
        "review_priority"
    ] = pending.apply(
        calculate_review_priority,
        axis=1,
    )

    pending[
        "priority_score"
    ] = pending.apply(
        calculate_priority_score,
        axis=1,
    )

    pending[
        "requires_manual_review"
    ] = True

    pending[
        "review_queue_version"
    ] = REVIEW_QUEUE_VERSION

    pending[
        "review_queue_source"
    ] = EXPECTED_DISCONTINUITY_VERSION

    output_columns = [
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

        "detected_by_v4_threshold",
        "newly_visible_in_v5_band",

        "review_priority",
        "priority_score",

        "review_status",
        "event_type",

        "requires_manual_review",

        "discontinuity_version",
        "discontinuity_source",

        "review_queue_version",
        "review_queue_source",
    ]

    pending = pending[
        output_columns
    ].copy()

    priority_order = pd.CategoricalDtype(
        categories=[
            "P1",
            "P2",
            "P3",
            "P4",
        ],
        ordered=True,
    )

    pending[
        "review_priority"
    ] = pending[
        "review_priority"
    ].astype(
        priority_order
    )

    pending = (
        pending
        .sort_values(
            [
                "review_priority",
                "priority_score",
                "event_date",
                "ticker",
            ],
            ascending=[
                True,
                False,
                True,
                True,
            ],
        )
        .reset_index(
            drop=True
        )
    )

    pending[
        "review_priority"
    ] = pending[
        "review_priority"
    ].astype(
        "string"
    )

    return pending


def validate_output(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida a Review Queue.
    """

    if dataframe.empty:
        raise ValueError(
            "Review Queue ficou vazia."
        )

    required_columns = [
        "ticker",
        "event_date",

        "daily_return",
        "absolute_daily_return",

        "classification",
        "confidence",

        "review_priority",
        "priority_score",

        "review_status",
        "requires_manual_review",

        "review_queue_version",
        "review_queue_source",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Review Queue possui "
            "colunas obrigatórias ausentes: "
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

    null_count = int(
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    invalid_status = int(
        (
            dataframe[
                "review_status"
            ]
            != EXPECTED_REVIEW_STATUS
        ).sum()
    )

    invalid_manual_flag = int(
        (
            ~dataframe[
                "requires_manual_review"
            ]
        ).sum()
    )

    invalid_priorities = sorted(
        set(
            dataframe[
                "review_priority"
            ]
            .dropna()
            .tolist()
        )
        - VALID_PRIORITIES
    )

    invalid_version = int(
        (
            dataframe[
                "review_queue_version"
            ]
            != REVIEW_QUEUE_VERSION
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "review_queue_source"
            ]
            != EXPECTED_DISCONTINUITY_VERSION
        ).sum()
    )

    non_finite_scores = int(
        (
            ~np.isfinite(
                dataframe[
                    "priority_score"
                ]
                .astype(float)
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Review Queue"
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
        f"Status inválido: "
        f"{invalid_status:,}"
    )

    print(
        f"Manual flag inválida: "
        f"{invalid_manual_flag:,}"
    )

    print(
        f"Scores não finitos: "
        f"{non_finite_scores:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Review Queue possui "
            "duplicidades."
        )

    if null_count > 0:
        raise ValueError(
            "Review Queue possui "
            "nulos obrigatórios."
        )

    if invalid_status > 0:
        raise ValueError(
            "Review Queue possui "
            "evento não pendente."
        )

    if invalid_manual_flag > 0:
        raise ValueError(
            "requires_manual_review "
            "inconsistente."
        )

    if invalid_priorities:
        raise ValueError(
            "Prioridades inválidas: "
            f"{invalid_priorities}"
        )

    if invalid_version > 0:
        raise ValueError(
            "Review Queue possui "
            "version inconsistente."
        )

    if invalid_source > 0:
        raise ValueError(
            "Review Queue possui "
            "source inconsistente."
        )

    if non_finite_scores > 0:
        raise ValueError(
            "Review Queue possui "
            "priority_score não finito."
        )

    print(
        "\nData Quality aprovada."
    )


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    """
    Resumo da fila.
    """

    print(
        "\n======================================"
    )
    print(
        "Resumo - Corporate Action Review Queue"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{REVIEW_QUEUE_VERSION}"
    )

    print(
        "Source: Price Discontinuities "
        f"{EXPECTED_DISCONTINUITY_VERSION}"
    )

    print(
        f"Eventos pendentes: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        "\nPrioridades:"
    )

    for priority in [
        "P1",
        "P2",
        "P3",
        "P4",
    ]:
        count = int(
            (
                dataframe[
                    "review_priority"
                ]
                == priority
            ).sum()
        )

        print(
            f"  {priority}: "
            f"{count:,}"
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
        "\n======================================"
    )
    print(
        "Top 20 para revisão"
    )
    print(
        "======================================"
    )

    display_columns = [
        "review_priority",
        "priority_score",

        "ticker",
        "event_date",

        "price_before",
        "price_after",

        "daily_return_pct",

        "classification",
        "confidence",

        "factor_match",

        "newly_visible_in_v5_band",
    ]

    print(
        dataframe[
            display_columns
        ]
        .head(
            20
        )
        .to_string(
            index=False
        )
    )

    print(
        "\nArquivo de saída:"
    )

    print(
        OUTPUT_PATH
    )


def main() -> None:
    print(
        "Construindo FII Corporate Action "
        "Review Queue..."
    )

    print(
        f"Version: "
        f"{REVIEW_QUEUE_VERSION}"
    )

    print(
        "Scope: candidatos "
        "PENDING_REVIEW apenas."
    )

    discontinuities = (
        load_discontinuities()
    )

    validate_source_contract(
        discontinuities
    )

    review_queue = (
        build_review_queue(
            discontinuities
        )
    )

    validate_output(
        review_queue
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    review_queue.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print_summary(
        review_queue
    )

    print(
        "\nReview Queue criada com sucesso."
    )

    print(
        "Nenhuma decisão governada "
        "foi alterada."
    )

    print(
        "Nenhum candidato foi confirmado "
        "ou descartado automaticamente."
    )

    print(
        "A fila apenas prioriza "
        "a revisão humana."
    )


if __name__ == "__main__":
    main()