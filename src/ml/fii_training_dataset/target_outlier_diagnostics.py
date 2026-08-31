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


SPLIT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
)

TRAIN_PATH = (
    SPLIT_DIR
    / "train.parquet"
)

VALIDATION_PATH = (
    SPLIT_DIR
    / "validation.parquet"
)


OUTLIER_THRESHOLDS = [
    0.10,
    0.20,
    0.30,
    0.50,
    1.00,
    2.00,
    5.00,
]


COMMON_PRICE_FACTORS = [
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


def load_dataset(
    path: Path,
    split_name: str,
) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"{split_name} não encontrado: {path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
        ]
    )

    print(
        f"{split_name}: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def discover_target_contract(
    dataframe: pd.DataFrame,
) -> tuple[
    str,
    str,
    str,
]:

    if "target_name" not in dataframe.columns:
        raise ValueError(
            "target_name não encontrada."
        )

    target_names = (
        dataframe[
            "target_name"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(target_names) != 1:
        raise ValueError(
            "Esperado exatamente um target. "
            f"Encontrados: {target_names.tolist()}"
        )

    target_column = (
        target_names[0]
    )

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
            "Esperado exatamente um horizonte. "
            f"Encontrados: {horizons.tolist()}"
        )

    horizon = int(
        horizons[0]
    )

    target_price_column = (
        f"target_price_next_{horizon}d"
    )

    target_date_column = (
        f"target_date_next_{horizon}d"
    )

    required_columns = [
        target_column,
        target_price_column,
        target_date_column,
        "close_price",
        "ticker",
        "feature_date",
    ]

    missing = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing:
        raise ValueError(
            "Colunas necessárias ausentes: "
            f"{missing}"
        )

    return (
        target_column,
        target_price_column,
        target_date_column,
    )


def nearest_common_factor(
    price_factor: float,
) -> tuple[
    float,
    float,
]:

    nearest = min(
        COMMON_PRICE_FACTORS,
        key=lambda factor: abs(
            price_factor
            - factor
        ),
    )

    relative_error = abs(
        price_factor
        - nearest
    ) / nearest

    return (
        nearest,
        relative_error,
    )


def enrich_outliers(
    dataframe: pd.DataFrame,
    target_column: str,
    target_price_column: str,
) -> pd.DataFrame:

    enriched = dataframe.copy()

    enriched[
        "price_factor"
    ] = (
        enriched[
            target_price_column
        ]
        / enriched[
            "close_price"
        ]
    )

    nearest_values = []

    relative_errors = []

    for factor in enriched[
        "price_factor"
    ]:
        (
            nearest,
            relative_error,
        ) = nearest_common_factor(
            float(factor)
        )

        nearest_values.append(
            nearest
        )

        relative_errors.append(
            relative_error
        )

    enriched[
        "nearest_common_factor"
    ] = nearest_values

    enriched[
        "factor_relative_error"
    ] = relative_errors

    enriched[
        "looks_like_common_factor"
    ] = (
        enriched[
            "factor_relative_error"
        ]
        <= 0.10
    )

    enriched[
        "absolute_target"
    ] = enriched[
        target_column
    ].abs()

    return enriched


def print_threshold_counts(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
) -> None:

    absolute_target = dataframe[
        target_column
    ].abs()

    print(
        "\n======================================"
    )

    print(
        f"Outliers por magnitude - {split_name}"
    )

    print(
        "======================================"
    )

    for threshold in OUTLIER_THRESHOLDS:

        count = int(
            (
                absolute_target
                >= threshold
            ).sum()
        )

        percentage = (
            count
            / len(dataframe)
            * 100
        )

        print(
            f"|target| >= "
            f"{threshold * 100:>6.1f}%: "
            f"{count:,} "
            f"({percentage:.4f}%)"
        )


def print_extreme_rows(
    dataframe: pd.DataFrame,
    target_column: str,
    target_price_column: str,
    target_date_column: str,
    split_name: str,
    limit: int = 30,
) -> None:

    enriched = enrich_outliers(
        dataframe=dataframe,
        target_column=target_column,
        target_price_column=(
            target_price_column
        ),
    )

    extreme = (
        enriched
        .sort_values(
            "absolute_target",
            ascending=False,
        )
        .head(
            limit
        )
        .copy()
    )

    extreme[
        "close_price_display"
    ] = extreme[
        "close_price"
    ]

    extreme[
        "target_price_display"
    ] = extreme[
        target_price_column
    ]

    extreme[
        "target_pct"
    ] = (
        extreme[
            target_column
        ]
        * 100
    )

    print(
        "\n======================================"
    )

    print(
        f"Targets mais extremos - {split_name}"
    )

    print(
        "======================================"
    )

    display_columns = [
        "ticker",
        "feature_date",
        target_date_column,
        "close_price_display",
        "target_price_display",
        "target_pct",
        "price_factor",
        "nearest_common_factor",
        "factor_relative_error",
        "looks_like_common_factor",
    ]

    print(
        extreme[
            display_columns
        ].to_string(
            index=False,
        )
    )


def print_extreme_tickers(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
    threshold: float = 0.50,
) -> None:

    extreme = dataframe[
        dataframe[
            target_column
        ].abs()
        >= threshold
    ].copy()

    print(
        "\n======================================"
    )

    print(
        f"Tickers com |target| >= "
        f"{threshold * 100:.0f}% - "
        f"{split_name}"
    )

    print(
        "======================================"
    )

    if extreme.empty:
        print(
            "Nenhum ticker encontrado."
        )

        return

    summary = (
        extreme
        .groupby(
            "ticker"
        )
        .agg(
            occurrences=(
                target_column,
                "size",
            ),
            min_target=(
                target_column,
                "min",
            ),
            max_target=(
                target_column,
                "max",
            ),
            first_feature_date=(
                "feature_date",
                "min",
            ),
            last_feature_date=(
                "feature_date",
                "max",
            ),
        )
        .reset_index()
    )

    summary[
        "max_absolute_target"
    ] = np.maximum(
        summary[
            "min_target"
        ].abs(),
        summary[
            "max_target"
        ].abs(),
    )

    summary = summary.sort_values(
        [
            "max_absolute_target",
            "occurrences",
        ],
        ascending=[
            False,
            False,
        ],
    )

    summary[
        "min_target_pct"
    ] = (
        summary[
            "min_target"
        ]
        * 100
    )

    summary[
        "max_target_pct"
    ] = (
        summary[
            "max_target"
        ]
        * 100
    )

    print(
        summary[
            [
                "ticker",
                "occurrences",
                "min_target_pct",
                "max_target_pct",
                "first_feature_date",
                "last_feature_date",
            ]
        ].to_string(
            index=False,
        )
    )


def print_common_factor_summary(
    dataframe: pd.DataFrame,
    target_column: str,
    target_price_column: str,
    split_name: str,
    threshold: float = 0.50,
) -> None:

    extreme = dataframe[
        dataframe[
            target_column
        ].abs()
        >= threshold
    ].copy()

    print(
        "\n======================================"
    )

    print(
        f"Possíveis fatores corporativos - "
        f"{split_name}"
    )

    print(
        "======================================"
    )

    if extreme.empty:
        print(
            "Nenhum target extremo."
        )

        return

    enriched = enrich_outliers(
        dataframe=extreme,
        target_column=target_column,
        target_price_column=(
            target_price_column
        ),
    )

    suspicious = enriched[
        enriched[
            "looks_like_common_factor"
        ]
    ]

    print(
        f"Targets |retorno| >= "
        f"{threshold * 100:.0f}%: "
        f"{len(enriched):,}"
    )

    print(
        "Próximos de fatores comuns "
        "(tolerância 10%): "
        f"{len(suspicious):,}"
    )

    if suspicious.empty:
        return

    factor_summary = (
        suspicious[
            "nearest_common_factor"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        "\nDistribuição:"
    )

    for factor, count in (
        factor_summary.items()
    ):
        print(
            f"  fator ~{factor:g}x: "
            f"{count:,}"
        )


def run_split_diagnostics(
    dataframe: pd.DataFrame,
    split_name: str,
) -> None:

    (
        target_column,
        target_price_column,
        target_date_column,
    ) = discover_target_contract(
        dataframe
    )

    print_threshold_counts(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_extreme_rows(
        dataframe=dataframe,
        target_column=target_column,
        target_price_column=(
            target_price_column
        ),
        target_date_column=(
            target_date_column
        ),
        split_name=split_name,
    )

    print_extreme_tickers(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_common_factor_summary(
        dataframe=dataframe,
        target_column=target_column,
        target_price_column=(
            target_price_column
        ),
        split_name=split_name,
    )


def main() -> None:

    print(
        "Executando diagnóstico "
        "de outliers do target..."
    )

    train = load_dataset(
        TRAIN_PATH,
        "TRAIN",
    )

    validation = load_dataset(
        VALIDATION_PATH,
        "VALIDATION",
    )

    run_split_diagnostics(
        dataframe=train,
        split_name="TRAIN",
    )

    run_split_diagnostics(
        dataframe=validation,
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
        "Este diagnóstico NÃO remove, "
        "clipa ou altera nenhum dado."
    )

    print(
        "Ele apenas identifica retornos "
        "extremos e possíveis saltos de "
        "preço compatíveis com eventos "
        "corporativos."
    )

    print(
        "\nDiagnóstico concluído."
    )


if __name__ == "__main__":
    main()