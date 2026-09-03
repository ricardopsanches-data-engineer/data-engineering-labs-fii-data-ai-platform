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


DIAGNOSTICS_VERSION = "v2"

EXPECTED_SPLIT_VERSION = "v2"

EXPECTED_TRAINING_DATASET_VERSION = "v3"

EXPECTED_FEATURE_VERSION = "v6"

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)

EXPECTED_TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)


LOSS_THRESHOLDS = [
    0.05,
    0.10,
    0.20,
    0.30,
    0.50,
]

GAIN_THRESHOLDS = [
    0.05,
    0.10,
    0.20,
    0.30,
    0.50,
    1.00,
]


TOP_N_EXTREMES = [
    1,
    5,
    10,
    25,
    50,
    100,
]


def load_dataset(
    path: Path,
    split_name: str,
) -> pd.DataFrame:
    """
    Carrega um split temporal.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"{split_name} não encontrado: "
            f"{path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    required_date_columns = [
        "feature_date",
        "target_date",
    ]

    for column in required_date_columns:
        if column not in dataframe.columns:
            raise ValueError(
                f"{split_name}: "
                f"coluna {column} ausente."
            )

        dataframe[
            column
        ] = pd.to_datetime(
            dataframe[
                column
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
        f"{split_name}: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def get_unique_string(
    dataframe: pd.DataFrame,
    column: str,
    split_name: str,
) -> str:
    """
    Obtém exatamente um valor textual.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"{split_name}: "
            f"coluna {column} ausente."
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
            f"{split_name}: "
            f"{column} ambígua: "
            f"{values}"
        )

    return values[0]


def get_unique_int(
    dataframe: pd.DataFrame,
    column: str,
    split_name: str,
) -> int:
    """
    Obtém exatamente um valor inteiro.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"{split_name}: "
            f"coluna {column} ausente."
        )

    values = (
        dataframe[
            column
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if len(values) != 1:
        raise ValueError(
            f"{split_name}: "
            f"{column} ambígua: "
            f"{values}"
        )

    return int(
        values[0]
    )


def discover_target_column(
    dataframe: pd.DataFrame,
    split_name: str,
) -> str:
    """
    Descobre o target oficial.
    """

    target_name = get_unique_string(
        dataframe=dataframe,
        column="target_name",
        split_name=split_name,
    )

    if target_name not in dataframe.columns:
        raise ValueError(
            f"{split_name}: "
            f"target {target_name} "
            "não existe."
        )

    return target_name


def validate_split_contract(
    dataframe: pd.DataFrame,
    split_name: str,
    target_column: str,
) -> None:
    """
    Valida que o diagnóstico está
    trabalhando sobre a arquitetura
    econômica atual.
    """

    required_columns = [
        "feature_date",
        "target_date",

        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price",
        "close_price_raw",
        "close_price_adjusted",

        "target_price_next_5d",
        "target_price_raw",
        "target_price_return_next_5d",
        "target_economic_vs_price_difference",

        target_column,

        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",

        "feature_ready",
        "ml_eligible",

        "split_name",
        "split_version",

        "training_dataset_version",
        "source_feature_version",

        "price_semantics",
        "return_semantics",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{split_name}: "
            "colunas obrigatórias ausentes: "
            f"{missing_columns}"
        )

    split_value = get_unique_string(
        dataframe,
        "split_name",
        split_name,
    )

    split_version = get_unique_string(
        dataframe,
        "split_version",
        split_name,
    )

    training_version = get_unique_string(
        dataframe,
        "training_dataset_version",
        split_name,
    )

    feature_version = get_unique_string(
        dataframe,
        "source_feature_version",
        split_name,
    )

    target_horizon = get_unique_int(
        dataframe,
        "target_horizon",
        split_name,
    )

    horizon_semantics = get_unique_string(
        dataframe,
        "target_horizon_semantics",
        split_name,
    )

    target_semantics = get_unique_string(
        dataframe,
        "target_return_semantics",
        split_name,
    )

    price_semantics = get_unique_string(
        dataframe,
        "price_semantics",
        split_name,
    )

    return_semantics = get_unique_string(
        dataframe,
        "return_semantics",
        split_name,
    )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    target_nulls = int(
        dataframe[
            target_column
        ]
        .isna()
        .sum()
    )

    target_non_finite = int(
        (
            dataframe[
                target_column
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    target_column
                ]
            )
        ).sum()
    )

    invalid_dates = int(
        (
            dataframe[
                "target_date"
            ]
            <= dataframe[
                "feature_date"
            ]
        ).sum()
    )

    feature_ready_false = int(
        (
            ~dataframe[
                "feature_ready"
            ]
        ).sum()
    )

    ml_eligible_false = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
        ).sum()
    )

    print(
        f"\nContrato {split_name}:"
    )

    print(
        f"  split_version: "
        f"{split_version}"
    )

    print(
        f"  training_dataset_version: "
        f"{training_version}"
    )

    print(
        f"  source_feature_version: "
        f"{feature_version}"
    )

    print(
        f"  target_horizon: "
        f"{target_horizon}"
    )

    print(
        f"  target_return_semantics: "
        f"{target_semantics}"
    )

    print(
        f"  duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"  target nulo: "
        f"{target_nulls:,}"
    )

    print(
        f"  target não finito: "
        f"{target_non_finite:,}"
    )

    print(
        f"  target_date inválida: "
        f"{invalid_dates:,}"
    )

    print(
        f"  feature_ready=False: "
        f"{feature_ready_false:,}"
    )

    print(
        f"  ml_eligible=False: "
        f"{ml_eligible_false:,}"
    )

    if split_value != split_name.lower():
        raise ValueError(
            f"{split_name}: "
            f"split_name incompatível: "
            f"{split_value}"
        )

    if split_version != EXPECTED_SPLIT_VERSION:
        raise ValueError(
            "Target Diagnostics v2 exige "
            f"Temporal Split "
            f"{EXPECTED_SPLIT_VERSION}."
        )

    if (
        training_version
        != EXPECTED_TRAINING_DATASET_VERSION
    ):
        raise ValueError(
            "Target Diagnostics v2 exige "
            f"Training Dataset "
            f"{EXPECTED_TRAINING_DATASET_VERSION}."
        )

    if (
        feature_version
        != EXPECTED_FEATURE_VERSION
    ):
        raise ValueError(
            "Target Diagnostics v2 exige "
            f"Features "
            f"{EXPECTED_FEATURE_VERSION}."
        )

    if (
        target_horizon
        != EXPECTED_TARGET_HORIZON
    ):
        raise ValueError(
            "Target horizon incompatível."
        )

    if (
        horizon_semantics
        != EXPECTED_TARGET_HORIZON_SEMANTICS
    ):
        raise ValueError(
            "Target horizon semantics "
            "incompatível."
        )

    if (
        target_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Target econômico obrigatório."
        )

    if (
        price_semantics
        != EXPECTED_PRICE_SEMANTICS
    ):
        raise ValueError(
            "Price semantics incompatível."
        )

    if (
        return_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Return semantics incompatível."
        )

    if duplicate_count > 0:
        raise ValueError(
            f"{split_name} possui duplicidades."
        )

    if target_nulls > 0:
        raise ValueError(
            f"{split_name} possui target nulo."
        )

    if target_non_finite > 0:
        raise ValueError(
            f"{split_name} possui target "
            "não finito."
        )

    if invalid_dates > 0:
        raise ValueError(
            f"{split_name} possui "
            "target_date inválida."
        )

    if feature_ready_false > 0:
        raise ValueError(
            f"{split_name} possui "
            "feature_ready=False."
        )

    if ml_eligible_false > 0:
        raise ValueError(
            f"{split_name} possui "
            "ml_eligible=False."
        )


def print_target_distribution(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
) -> None:
    """
    Distribuição geral do target.
    """

    target = dataframe[
        target_column
    ].astype(float)

    quantiles = target.quantile(
        [
            0.01,
            0.05,
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
            0.99,
        ]
    )

    print(
        "\n======================================"
    )
    print(
        f"Distribuição do target - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(target):,}"
    )

    print(
        f"Média: "
        f"{target.mean() * 100:.4f}%"
    )

    print(
        f"Mediana: "
        f"{target.median() * 100:.4f}%"
    )

    print(
        f"Desvio padrão: "
        f"{target.std() * 100:.4f}%"
    )

    print(
        f"Mínimo: "
        f"{target.min() * 100:.4f}%"
    )

    print(
        f"Máximo: "
        f"{target.max() * 100:.4f}%"
    )

    print(
        "\nQuantis:"
    )

    for quantile, value in (
        quantiles.items()
    ):
        print(
            f"  q{int(quantile * 100):02d}: "
            f"{value * 100:.4f}%"
        )


def print_directional_thresholds(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
) -> None:
    """
    Conta perdas e ganhos extremos
    separadamente.

    Isso é melhor que usar somente
    |target| porque preserva direção.
    """

    target = dataframe[
        target_column
    ].astype(float)

    print(
        "\n======================================"
    )
    print(
        f"Perdas extremas - {split_name}"
    )
    print(
        "======================================"
    )

    for threshold in LOSS_THRESHOLDS:
        count = int(
            (
                target
                <= -threshold
            ).sum()
        )

        percentage = (
            count
            / len(target)
            * 100
        )

        print(
            f"target <= "
            f"-{threshold * 100:>5.1f}%: "
            f"{count:,} "
            f"({percentage:.4f}%)"
        )

    print(
        "\n======================================"
    )
    print(
        f"Ganhos extremos - {split_name}"
    )
    print(
        "======================================"
    )

    for threshold in GAIN_THRESHOLDS:
        count = int(
            (
                target
                >= threshold
            ).sum()
        )

        percentage = (
            count
            / len(target)
            * 100
        )

        print(
            f"target >= "
            f"+{threshold * 100:>5.1f}%: "
            f"{count:,} "
            f"({percentage:.4f}%)"
        )


def calculate_trimmed_mean(
    target: pd.Series,
    remove_n: int,
    direction: str,
) -> float:
    """
    Remove os N retornos mais extremos
    de uma direção e recalcula a média.

    direction:
        "negative"
        "positive"
        "absolute"
    """

    if remove_n <= 0:
        return float(
            target.mean()
        )

    if remove_n >= len(target):
        return np.nan

    if direction == "negative":
        ordered = target.sort_values(
            ascending=True
        )

    elif direction == "positive":
        ordered = target.sort_values(
            ascending=False
        )

    elif direction == "absolute":
        ordered_index = (
            target
            .abs()
            .sort_values(
                ascending=False
            )
            .index
        )

        remaining = target.drop(
            ordered_index[
                :remove_n
            ]
        )

        return float(
            remaining.mean()
        )

    else:
        raise ValueError(
            f"Direção inválida: "
            f"{direction}"
        )

    remaining = ordered.iloc[
        remove_n:
    ]

    return float(
        remaining.mean()
    )


def print_mean_sensitivity(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
) -> None:
    """
    Mede quanto a média depende de
    poucos casos extremos.
    """

    target = dataframe[
        target_column
    ].astype(float)

    original_mean = float(
        target.mean()
    )

    print(
        "\n======================================"
    )
    print(
        f"Sensibilidade da média - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    print(
        f"Média original: "
        f"{original_mean * 100:.4f}%"
    )

    for remove_n in TOP_N_EXTREMES:
        if remove_n >= len(target):
            continue

        without_negative = (
            calculate_trimmed_mean(
                target=target,
                remove_n=remove_n,
                direction="negative",
            )
        )

        without_positive = (
            calculate_trimmed_mean(
                target=target,
                remove_n=remove_n,
                direction="positive",
            )
        )

        without_absolute = (
            calculate_trimmed_mean(
                target=target,
                remove_n=remove_n,
                direction="absolute",
            )
        )

        print(
            f"\nRemovendo TOP {remove_n}:"
        )

        print(
            "  piores negativos: "
            f"{without_negative * 100:.4f}%"
        )

        print(
            "  maiores positivos: "
            f"{without_positive * 100:.4f}%"
        )

        print(
            "  maiores |retornos|: "
            f"{without_absolute * 100:.4f}%"
        )


def print_worst_rows(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
    limit: int = 20,
) -> None:
    """
    Mostra as maiores perdas.
    """

    worst = (
        dataframe
        .sort_values(
            target_column,
            ascending=True,
        )
        .head(
            limit
        )
        .copy()
    )

    worst[
        "target_pct"
    ] = (
        worst[
            target_column
        ]
        * 100
    )

    worst[
        "price_return_pct"
    ] = (
        worst[
            "target_price_return_next_5d"
        ]
        * 100
    )

    worst[
        "economic_price_diff_pp"
    ] = (
        worst[
            "target_economic_vs_price_difference"
        ]
        * 100
    )

    display_columns = [
        "ticker",
        "feature_date",
        "target_date",

        "close_price",
        "target_price_next_5d",

        "target_pct",
        "price_return_pct",
        "economic_price_diff_pp",
    ]

    print(
        "\n======================================"
    )
    print(
        f"20 maiores perdas - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    print(
        worst[
            display_columns
        ].to_string(
            index=False
        )
    )


def print_best_rows(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
    limit: int = 10,
) -> None:
    """
    Mostra os maiores ganhos.
    """

    best = (
        dataframe
        .sort_values(
            target_column,
            ascending=False,
        )
        .head(
            limit
        )
        .copy()
    )

    best[
        "target_pct"
    ] = (
        best[
            target_column
        ]
        * 100
    )

    best[
        "price_return_pct"
    ] = (
        best[
            "target_price_return_next_5d"
        ]
        * 100
    )

    best[
        "economic_price_diff_pp"
    ] = (
        best[
            "target_economic_vs_price_difference"
        ]
        * 100
    )

    print(
        "\n======================================"
    )
    print(
        f"10 maiores ganhos - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    print(
        best[
            [
                "ticker",
                "feature_date",
                "target_date",
                "close_price",
                "target_price_next_5d",
                "target_pct",
                "price_return_pct",
                "economic_price_diff_pp",
            ]
        ].to_string(
            index=False
        )
    )


def print_negative_concentration_by_ticker(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
    threshold: float = 0.10,
    limit: int = 20,
) -> None:
    """
    Mede concentração das perdas relevantes
    por ticker.
    """

    losses = dataframe[
        dataframe[
            target_column
        ]
        <= -threshold
    ].copy()

    print(
        "\n======================================"
    )
    print(
        f"Concentração target <= "
        f"-{threshold * 100:.0f}% - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    if losses.empty:
        print(
            "Nenhuma ocorrência."
        )
        return

    summary = (
        losses
        .groupby(
            "ticker"
        )
        .agg(
            occurrences=(
                target_column,
                "size",
            ),
            mean_target=(
                target_column,
                "mean",
            ),
            min_target=(
                target_column,
                "min",
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
        "share_of_loss_events"
    ] = (
        summary[
            "occurrences"
        ]
        / len(losses)
    )

    summary = (
        summary
        .sort_values(
            [
                "occurrences",
                "min_target",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .head(
            limit
        )
    )

    summary[
        "mean_target_pct"
    ] = (
        summary[
            "mean_target"
        ]
        * 100
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
        "share_pct"
    ] = (
        summary[
            "share_of_loss_events"
        ]
        * 100
    )

    print(
        f"Total de eventos: "
        f"{len(losses):,}"
    )

    print(
        f"Tickers distintos: "
        f"{losses['ticker'].nunique():,}"
    )

    print(
        "\nTop tickers:"
    )

    print(
        summary[
            [
                "ticker",
                "occurrences",
                "share_pct",
                "mean_target_pct",
                "min_target_pct",
                "first_feature_date",
                "last_feature_date",
            ]
        ].to_string(
            index=False
        )
    )


def print_ticker_distribution_summary(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
) -> None:
    """
    Resume comportamento médio por FII.
    """

    ticker_summary = (
        dataframe
        .groupby(
            "ticker"
        )
        .agg(
            observations=(
                target_column,
                "size",
            ),
            mean_target=(
                target_column,
                "mean",
            ),
            median_target=(
                target_column,
                "median",
            ),
        )
        .reset_index()
    )

    negative_mean_tickers = int(
        (
            ticker_summary[
                "mean_target"
            ]
            < 0
        ).sum()
    )

    positive_mean_tickers = int(
        (
            ticker_summary[
                "mean_target"
            ]
            > 0
        ).sum()
    )

    zero_mean_tickers = (
        len(ticker_summary)
        - negative_mean_tickers
        - positive_mean_tickers
    )

    print(
        "\n======================================"
    )
    print(
        f"Distribuição por ticker - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    print(
        f"Tickers: "
        f"{len(ticker_summary):,}"
    )

    print(
        "Tickers com target médio < 0: "
        f"{negative_mean_tickers:,} "
        f"("
        f"{negative_mean_tickers / len(ticker_summary) * 100:.2f}%"
        f")"
    )

    print(
        "Tickers com target médio > 0: "
        f"{positive_mean_tickers:,} "
        f"("
        f"{positive_mean_tickers / len(ticker_summary) * 100:.2f}%"
        f")"
    )

    print(
        "Tickers com target médio = 0: "
        f"{zero_mean_tickers:,}"
    )


def build_split_summary(
    dataframe: pd.DataFrame,
    target_column: str,
    split_name: str,
) -> dict[str, object]:
    """
    Cria resumo usado na comparação
    TRAIN x VALIDATION.
    """

    target = dataframe[
        target_column
    ].astype(float)

    return {
        "split": split_name,

        "rows": len(dataframe),

        "tickers": (
            dataframe[
                "ticker"
            ].nunique()
        ),

        "mean": float(
            target.mean()
        ),

        "median": float(
            target.median()
        ),

        "std": float(
            target.std()
        ),

        "positive_rate": float(
            (
                target
                > 0
            ).mean()
        ),

        "loss_5_rate": float(
            (
                target
                <= -0.05
            ).mean()
        ),

        "loss_10_rate": float(
            (
                target
                <= -0.10
            ).mean()
        ),

        "loss_20_rate": float(
            (
                target
                <= -0.20
            ).mean()
        ),
    }


def print_train_validation_comparison(
    train_summary: dict[str, object],
    validation_summary: dict[str, object],
) -> None:
    """
    Comparação direta entre os splits.
    """

    print(
        "\n======================================"
    )
    print(
        "Comparação TRAIN -> VALIDATION"
    )
    print(
        "======================================"
    )

    metrics = [
        (
            "Média",
            "mean",
            True,
        ),
        (
            "Mediana",
            "median",
            True,
        ),
        (
            "Desvio padrão",
            "std",
            True,
        ),
        (
            "Taxa positiva",
            "positive_rate",
            True,
        ),
        (
            "Taxa <= -5%",
            "loss_5_rate",
            True,
        ),
        (
            "Taxa <= -10%",
            "loss_10_rate",
            True,
        ),
        (
            "Taxa <= -20%",
            "loss_20_rate",
            True,
        ),
    ]

    for (
        label,
        key,
        percentage,
    ) in metrics:

        train_value = float(
            train_summary[
                key
            ]
        )

        validation_value = float(
            validation_summary[
                key
            ]
        )

        delta = (
            validation_value
            - train_value
        )

        if percentage:
            print(
                f"{label}:"
            )

            print(
                f"  TRAIN:      "
                f"{train_value * 100:.4f}%"
            )

            print(
                f"  VALIDATION: "
                f"{validation_value * 100:.4f}%"
            )

            print(
                f"  Delta:      "
                f"{delta * 100:+.4f} p.p."
            )


def run_split_diagnostics(
    dataframe: pd.DataFrame,
    split_name: str,
) -> tuple[
    str,
    dict[str, object],
]:
    """
    Executa todos os diagnósticos
    de um split.
    """

    target_column = (
        discover_target_column(
            dataframe,
            split_name,
        )
    )

    validate_split_contract(
        dataframe=dataframe,
        split_name=split_name,
        target_column=target_column,
    )

    print_target_distribution(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_directional_thresholds(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_mean_sensitivity(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_worst_rows(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_best_rows(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    print_negative_concentration_by_ticker(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
        threshold=0.10,
    )

    print_negative_concentration_by_ticker(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
        threshold=0.20,
    )

    print_ticker_distribution_summary(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    summary = build_split_summary(
        dataframe=dataframe,
        target_column=target_column,
        split_name=split_name,
    )

    return (
        target_column,
        summary,
    )


def main() -> None:
    print(
        "Executando FII Target "
        "Outlier Diagnostics..."
    )

    print(
        f"Diagnostics version: "
        f"{DIAGNOSTICS_VERSION}"
    )

    print(
        "Scope: TRAIN vs VALIDATION"
    )

    print(
        "TEST não será carregado."
    )

    train = load_dataset(
        TRAIN_PATH,
        "train",
    )

    validation = load_dataset(
        VALIDATION_PATH,
        "validation",
    )

    (
        train_target,
        train_summary,
    ) = run_split_diagnostics(
        dataframe=train,
        split_name="train",
    )

    (
        validation_target,
        validation_summary,
    ) = run_split_diagnostics(
        dataframe=validation,
        split_name="validation",
    )

    if train_target != validation_target:
        raise ValueError(
            "TRAIN e VALIDATION possuem "
            "targets diferentes."
        )

    print_train_validation_comparison(
        train_summary=train_summary,
        validation_summary=(
            validation_summary
        ),
    )

    print(
        "\n======================================"
    )
    print(
        "Conclusão técnica"
    )
    print(
        "======================================"
    )

    print(
        "Este diagnóstico NÃO remove, "
        "clipa ou altera targets."
    )

    print(
        "Ele mede se a distribuição da "
        "VALIDATION é dominada por poucos "
        "extremos ou por deterioração mais "
        "ampla do universo."
    )

    print(
        "Targets econômicos e retornos "
        "de preço são mantidos separados "
        "para auditoria."
    )

    print(
        "O TEST permaneceu completamente "
        "fora desta análise."
    )

    print(
        "\nDiagnóstico concluído."
    )


if __name__ == "__main__":
    main()