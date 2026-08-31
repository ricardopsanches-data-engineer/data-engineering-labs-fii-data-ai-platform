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


THRESHOLDS = [
    0.10,
    0.20,
    0.50,
    1.00,
]


RETURN_COLUMNS = {
    "RAW": "daily_return_raw",
    "ADJUSTED_PRICE": "daily_return_adjusted_price",
    "ECONOMIC": "daily_return_economic",
}


def load_data() -> pd.DataFrame:
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
        "confirmed_action_on_date",
        "pending_review_on_date",
        "confirmed_event_type",
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
                "ticker",
                "trade_date",
            ]
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

    if duplicate_count > 0:
        raise ValueError(
            "Fonte possui duplicidades."
        )

    for label, column in RETURN_COLUMNS.items():
        non_finite = int(
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

        print(
            f"Não finitos {label}: "
            f"{non_finite:,}"
        )

        if non_finite > 0:
            raise ValueError(
                f"{column} possui valores "
                "não finitos."
            )

    print(
        "\nData Quality aprovada."
    )


def count_extremes(
    series: pd.Series,
    threshold: float,
) -> int:
    valid = series.dropna()

    return int(
        (
            valid.abs()
            >= threshold
        ).sum()
    )


def build_threshold_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    records = []

    for threshold in THRESHOLDS:
        raw_count = count_extremes(
            dataframe[
                "daily_return_raw"
            ],
            threshold,
        )

        adjusted_count = count_extremes(
            dataframe[
                "daily_return_adjusted_price"
            ],
            threshold,
        )

        economic_count = count_extremes(
            dataframe[
                "daily_return_economic"
            ],
            threshold,
        )

        records.append(
            {
                "threshold_pct": (
                    threshold
                    * 100
                ),
                "raw_count": (
                    raw_count
                ),
                "adjusted_price_count": (
                    adjusted_count
                ),
                "economic_count": (
                    economic_count
                ),
                "removed_by_price_adjustment": (
                    raw_count
                    - adjusted_count
                ),
                "removed_by_economic_adjustment": (
                    raw_count
                    - economic_count
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def build_event_comparison(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    confirmed = dataframe[
        dataframe[
            "confirmed_action_on_date"
        ]
    ].copy()

    if confirmed.empty:
        return pd.DataFrame()

    columns = [
        "ticker",
        "trade_date",
        "confirmed_event_type",
        "close_price_raw",
        "close_price_adjusted",
        "cash_flow_per_unit_raw",
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
    ]

    return confirmed[
        columns
    ].sort_values(
        [
            "trade_date",
            "ticker",
        ]
    )


def build_changed_return_rows(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    valid = dataframe[
        dataframe[
            "daily_return_raw"
        ].notna()
        &
        dataframe[
            "daily_return_economic"
        ].notna()
    ].copy()

    changed_mask = (
        ~np.isclose(
            valid[
                "daily_return_raw"
            ],
            valid[
                "daily_return_economic"
            ],
            rtol=0.0,
            atol=1e-12,
        )
    )

    changed = valid[
        changed_mask
    ].copy()

    changed[
        "return_difference"
    ] = (
        changed[
            "daily_return_economic"
        ]
        - changed[
            "daily_return_raw"
        ]
    )

    columns = [
        "ticker",
        "trade_date",
        "review_status_on_date",
        "confirmed_action_on_date",
        "confirmed_event_type",
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
        "return_difference",
    ]

    return changed[
        columns
    ].sort_values(
        "return_difference",
        key=lambda series: (
            series.abs()
        ),
        ascending=False,
    )


def build_pending_review_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    pending = dataframe[
        dataframe[
            "pending_review_on_date"
        ]
    ].copy()

    if pending.empty:
        return pd.DataFrame()

    pending[
        "absolute_raw_return"
    ] = pending[
        "daily_return_raw"
    ].abs()

    columns = [
        "ticker",
        "trade_date",
        "discontinuity_confidence_on_date",
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
        "absolute_raw_return",
    ]

    return pending[
        columns
    ].sort_values(
        [
            "absolute_raw_return",
            "trade_date",
            "ticker",
        ],
        ascending=[
            False,
            True,
            True,
        ],
    )


def print_distribution(
    dataframe: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Distribuição dos retornos"
    )
    print(
        "======================================"
    )

    quantiles = [
        0.00,
        0.01,
        0.05,
        0.50,
        0.95,
        0.99,
        1.00,
    ]

    for label, column in RETURN_COLUMNS.items():
        series = (
            dataframe[
                column
            ]
            .dropna()
        )

        print(
            f"\n{label}"
        )

        print(
            f"  Observações: "
            f"{len(series):,}"
        )

        print(
            f"  Média: "
            f"{series.mean() * 100:.4f}%"
        )

        print(
            f"  Desvio padrão: "
            f"{series.std() * 100:.4f}%"
        )

        for quantile in quantiles:
            value = series.quantile(
                quantile
            )

            print(
                f"  p{quantile * 100:05.1f}: "
                f"{value * 100:.4f}%"
            )


def print_threshold_summary(
    summary: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Retornos extremos"
    )
    print(
        "======================================"
    )

    display = summary.copy()

    display[
        "threshold"
    ] = display[
        "threshold_pct"
    ].map(
        lambda value: (
            f">= {value:.0f}%"
        )
    )

    display = display[
        [
            "threshold",
            "raw_count",
            "adjusted_price_count",
            "economic_count",
            "removed_by_price_adjustment",
            "removed_by_economic_adjustment",
        ]
    ]

    print(
        display.to_string(
            index=False
        )
    )


def print_confirmed_events(
    event_comparison: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Impacto nos Corporate Actions "
        "confirmados"
    )
    print(
        "======================================"
    )

    if event_comparison.empty:
        print(
            "Nenhum evento confirmado."
        )

        return

    display = event_comparison.copy()

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


def print_changed_rows(
    changed_rows: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Linhas cujo retorno econômico mudou"
    )
    print(
        "======================================"
    )

    print(
        f"Total: "
        f"{len(changed_rows):,}"
    )

    if changed_rows.empty:
        return

    display = changed_rows.copy()

    for column in [
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
        "return_difference",
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
        "\nMaiores diferenças:"
    )

    print(
        display.head(
            20
        ).to_string(
            index=False
        )
    )


def print_pending_reviews(
    pending: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "PENDING_REVIEW ainda não corrigidos"
    )
    print(
        "======================================"
    )

    print(
        f"Eventos: "
        f"{len(pending):,}"
    )

    if pending.empty:
        return

    display = pending.copy()

    for column in [
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
        "absolute_raw_return",
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


def main() -> None:
    print(
        "Diagnosticando impacto dos "
        "Corporate Actions nos retornos..."
    )

    dataframe = load_data()

    validate_source(
        dataframe
    )

    threshold_summary = (
        build_threshold_summary(
            dataframe
        )
    )

    event_comparison = (
        build_event_comparison(
            dataframe
        )
    )

    changed_rows = (
        build_changed_return_rows(
            dataframe
        )
    )

    pending_reviews = (
        build_pending_review_summary(
            dataframe
        )
    )

    print_distribution(
        dataframe
    )

    print_threshold_summary(
        threshold_summary
    )

    print_confirmed_events(
        event_comparison
    )

    print_changed_rows(
        changed_rows
    )

    print_pending_reviews(
        pending_reviews
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
        "Este script é somente diagnóstico."
    )


if __name__ == "__main__":
    main()