from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TRAINING_DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
    / "fii_training_dataset.parquet"
)

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)


def load_training_dataset() -> pd.DataFrame:
    if not TRAINING_DATASET_PATH.exists():
        raise FileNotFoundError(
            "Training Dataset não encontrado: "
            f"{TRAINING_DATASET_PATH}"
        )

    dataframe = pd.read_parquet(
        TRAINING_DATASET_PATH
    )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe["feature_date"]
    )

    return dataframe


def load_global_trading_calendar() -> list[pd.Timestamp]:
    if not PRICE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "Gold Analytics não encontrada: "
            f"{PRICE_HISTORY_PATH}"
        )

    dataframe = pd.read_parquet(
        PRICE_HISTORY_PATH,
        columns=[
            "trade_date",
        ],
    )

    dates = (
        pd.to_datetime(
            dataframe["trade_date"]
        )
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return dates


def discover_target_contract(
    dataframe: pd.DataFrame,
) -> tuple[int, str]:
    if "target_horizon" not in dataframe.columns:
        raise ValueError(
            "target_horizon não encontrada."
        )

    horizons = (
        dataframe[
            "target_horizon"
        ]
        .dropna()
        .astype(int)
        .unique()
    )

    if len(horizons) != 1:
        raise ValueError(
            "Esperado exatamente um "
            f"target_horizon. Encontrados: {horizons}"
        )

    horizon = int(
        horizons[0]
    )

    target_date_column = (
        f"target_date_next_{horizon}d"
    )

    if target_date_column not in dataframe.columns:
        raise ValueError(
            "Coluna de target date não encontrada: "
            f"{target_date_column}"
        )

    return (
        horizon,
        target_date_column,
    )


def build_expected_target_dates(
    global_dates: list[pd.Timestamp],
    horizon: int,
) -> dict[pd.Timestamp, pd.Timestamp]:
    """
    Para cada pregão global T, calcula o pregão
    global T+horizon.

    Exemplo:
        horizonte 5
        posição 10 -> posição 15
    """

    expected_dates: dict[
        pd.Timestamp,
        pd.Timestamp,
    ] = {}

    for index, current_date in enumerate(
        global_dates
    ):
        target_index = (
            index
            + horizon
        )

        if target_index >= len(
            global_dates
        ):
            continue

        expected_dates[
            pd.Timestamp(
                current_date
            )
        ] = pd.Timestamp(
            global_dates[
                target_index
            ]
        )

    return expected_dates


def run_diagnostics() -> None:
    print(
        "Executando diagnóstico "
        "do horizonte do target..."
    )

    training = (
        load_training_dataset()
    )

    global_dates = (
        load_global_trading_calendar()
    )

    (
        horizon,
        target_date_column,
    ) = discover_target_contract(
        training
    )

    training[
        target_date_column
    ] = pd.to_datetime(
        training[
            target_date_column
        ]
    )

    expected_dates = (
        build_expected_target_dates(
            global_dates=global_dates,
            horizon=horizon,
        )
    )

    training[
        "expected_global_target_date"
    ] = training[
        "feature_date"
    ].map(
        expected_dates
    )

    comparable = training[
        training[
            "expected_global_target_date"
        ].notna()
    ].copy()

    comparable[
        "target_matches_global_horizon"
    ] = (
        comparable[
            target_date_column
        ]
        == comparable[
            "expected_global_target_date"
        ]
    )

    comparable[
        "calendar_delay_days"
    ] = (
        comparable[
            target_date_column
        ]
        - comparable[
            "expected_global_target_date"
        ]
    ).dt.days

    total = len(
        comparable
    )

    matches = int(
        comparable[
            "target_matches_global_horizon"
        ].sum()
    )

    mismatches = (
        total
        - matches
    )

    match_pct = (
        matches
        / total
        * 100
        if total
        else 0.0
    )

    mismatch_pct = (
        mismatches
        / total
        * 100
        if total
        else 0.0
    )

    print(
        "\n======================================"
    )
    print(
        "Contrato do target"
    )
    print(
        "======================================"
    )

    print(
        f"Target horizon declarado: "
        f"{horizon} pregões"
    )

    print(
        f"Coluna target date: "
        f"{target_date_column}"
    )

    print(
        f"Pregões no calendário global: "
        f"{len(global_dates):,}"
    )

    print(
        "\n======================================"
    )
    print(
        "Resultado"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas comparáveis: "
        f"{total:,}"
    )

    print(
        f"Target exatamente em T+{horizon}: "
        f"{matches:,} "
        f"({match_pct:.2f}%)"
    )

    print(
        f"Target diferente de T+{horizon}: "
        f"{mismatches:,} "
        f"({mismatch_pct:.2f}%)"
    )

    if mismatches > 0:
        mismatched = comparable[
            ~comparable[
                "target_matches_global_horizon"
            ]
        ].copy()

        print(
            "\n======================================"
        )
        print(
            "Atraso do target em relação "
            "ao calendário B3"
        )
        print(
            "======================================"
        )

        delay_distribution = (
            mismatched[
                "calendar_delay_days"
            ]
            .value_counts()
            .sort_index()
        )

        for delay, count in (
            delay_distribution.items()
        ):
            print(
                f"{int(delay):+d} dias corridos: "
                f"{count:,}"
            )

        print(
            "\nExemplos de divergência:"
        )

        sample_columns = [
            "ticker",
            "feature_date",
            "expected_global_target_date",
            target_date_column,
            "calendar_delay_days",
        ]

        sample = (
            mismatched[
                sample_columns
            ]
            .sort_values(
                [
                    "feature_date",
                    "ticker",
                ]
            )
            .head(
                20
            )
        )

        print(
            sample.to_string(
                index=False
            )
        )

        affected_tickers = (
            mismatched[
                "ticker"
            ]
            .nunique()
        )

        print(
            "\nTickers afetados: "
            f"{affected_tickers:,}"
        )

    print(
        "\n======================================"
    )
    print(
        "Interpretação"
    )
    print(
        "======================================"
    )

    if mismatches == 0:
        print(
            "O target atual coincide integralmente "
            f"com T+{horizon} pregões globais da B3."
        )

        print(
            "Nenhuma alteração no contrato "
            "do target é necessária."
        )

    else:
        print(
            "O target atual representa a "
            f"{horizon}ª observação futura "
            "por ticker em parte das linhas."
        )

        print(
            "Isso não é necessariamente um erro, "
            "mas é diferente de prever exatamente "
            f"o retorno em T+{horizon} pregões B3."
        )

        print(
            "Antes do Walk-Forward devemos decidir "
            "qual semântica será oficial."
        )


if __name__ == "__main__":
    run_diagnostics()