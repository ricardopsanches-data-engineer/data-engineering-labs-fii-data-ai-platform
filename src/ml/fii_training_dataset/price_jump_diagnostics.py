from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


TRAIN_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
    / "train.parquet"
)

VALIDATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
    / "validation.parquet"
)

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)


TARGET_THRESHOLD = 0.50

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


def load_split(
    path: Path,
    name: str,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{name} não encontrado: {path}"
        )

    dataframe = pd.read_parquet(path)

    dataframe["feature_date"] = pd.to_datetime(
        dataframe["feature_date"]
    )

    return dataframe


def load_price_history() -> pd.DataFrame:
    if not PRICE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "Price History não encontrado: "
            f"{PRICE_HISTORY_PATH}"
        )

    dataframe = pd.read_parquet(
        PRICE_HISTORY_PATH,
        columns=[
            "trade_date",
            "ticker",
            "close_price",
        ],
    )

    dataframe["trade_date"] = pd.to_datetime(
        dataframe["trade_date"]
    )

    return dataframe


def discover_target_contract(
    dataframe: pd.DataFrame,
) -> tuple[str, str]:
    target_names = (
        dataframe["target_name"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(target_names) != 1:
        raise ValueError(
            f"Target ambíguo: {target_names.tolist()}"
        )

    horizons = (
        dataframe["target_horizon"]
        .dropna()
        .astype(int)
        .unique()
    )

    if len(horizons) != 1:
        raise ValueError(
            f"Horizonte ambíguo: {horizons.tolist()}"
        )

    horizon = int(horizons[0])

    target_column = target_names[0]

    target_date_column = (
        f"target_date_next_{horizon}d"
    )

    return (
        target_column,
        target_date_column,
    )


def nearest_common_factor(
    factor: float,
) -> tuple[float, float]:
    nearest = min(
        COMMON_FACTORS,
        key=lambda value: abs(
            factor - value
        ),
    )

    relative_error = (
        abs(factor - nearest)
        / nearest
    )

    return (
        nearest,
        relative_error,
    )


def build_path(
    price_history: pd.DataFrame,
    ticker: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    path = price_history[
        (price_history["ticker"] == ticker)
        & (
            price_history["trade_date"]
            >= start_date
        )
        & (
            price_history["trade_date"]
            <= end_date
        )
    ].copy()

    path = path.sort_values(
        "trade_date"
    )

    path["previous_close"] = (
        path["close_price"]
        .shift(1)
    )

    path["daily_factor"] = (
        path["close_price"]
        / path["previous_close"]
    )

    path["daily_return"] = (
        path["daily_factor"]
        - 1
    )

    nearest_factors = []
    relative_errors = []
    factor_matches = []

    for factor in path["daily_factor"]:
        if pd.isna(factor):
            nearest_factors.append(
                np.nan
            )

            relative_errors.append(
                np.nan
            )

            factor_matches.append(
                False
            )

            continue

        (
            nearest,
            error,
        ) = nearest_common_factor(
            float(factor)
        )

        nearest_factors.append(
            nearest
        )

        relative_errors.append(
            error
        )

        factor_matches.append(
            error
            <= FACTOR_TOLERANCE
        )

    path[
        "nearest_common_factor"
    ] = nearest_factors

    path[
        "factor_relative_error"
    ] = relative_errors

    path[
        "looks_like_factor_jump"
    ] = factor_matches

    return path


def classify_path(
    path: pd.DataFrame,
) -> str:
    comparable = path[
        path["daily_factor"].notna()
    ]

    if comparable.empty:
        return "INSUFFICIENT_DATA"

    factor_jumps = comparable[
        comparable[
            "looks_like_factor_jump"
        ]
    ]

    if not factor_jumps.empty:
        return "POSSIBLE_CORPORATE_FACTOR"

    max_abs_daily_return = (
        comparable[
            "daily_return"
        ]
        .abs()
        .max()
    )

    if max_abs_daily_return >= 0.30:
        return "LARGE_SINGLE_DAY_MOVE"

    return "GRADUAL_OR_MARKET_MOVE"


def diagnose_split(
    dataframe: pd.DataFrame,
    price_history: pd.DataFrame,
    split_name: str,
) -> None:
    (
        target_column,
        target_date_column,
    ) = discover_target_contract(
        dataframe
    )

    extreme = dataframe[
        dataframe[
            target_column
        ].abs()
        >= TARGET_THRESHOLD
    ].copy()

    extreme = extreme.sort_values(
        target_column,
        key=lambda series: series.abs(),
        ascending=False,
    )

    print(
        "\n======================================"
    )
    print(
        f"Price Jump Audit - {split_name}"
    )
    print(
        "======================================"
    )

    print(
        f"Targets |retorno| >= "
        f"{TARGET_THRESHOLD * 100:.0f}%: "
        f"{len(extreme):,}"
    )

    classifications = []

    for _, row in extreme.iterrows():
        ticker = row["ticker"]

        feature_date = pd.Timestamp(
            row["feature_date"]
        )

        target_date = pd.Timestamp(
            row[
                target_date_column
            ]
        )

        path = build_path(
            price_history=price_history,
            ticker=ticker,
            start_date=feature_date,
            end_date=target_date,
        )

        classification = classify_path(
            path
        )

        classifications.append(
            classification
        )

        print(
            "\n--------------------------------------"
        )

        print(
            f"{ticker} | "
            f"{feature_date.date()} "
            f"-> {target_date.date()}"
        )

        print(
            f"Target: "
            f"{row[target_column] * 100:.4f}%"
        )

        print(
            f"Classificação: "
            f"{classification}"
        )

        if path.empty:
            print(
                "Sem trajetória disponível."
            )

            continue

        display = path.copy()

        display[
            "close_price"
        ] = display[
            "close_price"
        ].round(
            4
        )

        display[
            "daily_return_pct"
        ] = (
            display[
                "daily_return"
            ]
            * 100
        ).round(
            4
        )

        display[
            "daily_factor"
        ] = display[
            "daily_factor"
        ].round(
            6
        )

        display[
            "nearest_common_factor"
        ] = display[
            "nearest_common_factor"
        ].round(
            4
        )

        display[
            "factor_relative_error"
        ] = display[
            "factor_relative_error"
        ].round(
            6
        )

        print(
            display[
                [
                    "trade_date",
                    "close_price",
                    "daily_return_pct",
                    "daily_factor",
                    "nearest_common_factor",
                    "factor_relative_error",
                    "looks_like_factor_jump",
                ]
            ].to_string(
                index=False
            )
        )

    print(
        "\n======================================"
    )
    print(
        f"Resumo - {split_name}"
    )
    print(
        "======================================"
    )

    if not classifications:
        print(
            "Nenhum target extremo encontrado."
        )

        return

    summary = (
        pd.Series(
            classifications
        )
        .value_counts()
    )

    for category, count in (
        summary.items()
    ):
        print(
            f"{category}: "
            f"{count:,}"
        )


def main() -> None:
    print(
        "Executando diagnóstico "
        "de saltos de preço..."
    )

    train = load_split(
        TRAIN_PATH,
        "TRAIN",
    )

    validation = load_split(
        VALIDATION_PATH,
        "VALIDATION",
    )

    price_history = (
        load_price_history()
    )

    diagnose_split(
        dataframe=train,
        price_history=price_history,
        split_name="TRAIN",
    )

    diagnose_split(
        dataframe=validation,
        price_history=price_history,
        split_name="VALIDATION",
    )

    print(
        "\n======================================"
    )
    print(
        "Conclusão"
    )
    print(
        "======================================"
    )

    print(
        "Nenhum dado foi alterado."
    )

    print(
        "O objetivo é distinguir "
        "saltos discretos de escala "
        "de movimentos graduais."
    )


if __name__ == "__main__":
    main()