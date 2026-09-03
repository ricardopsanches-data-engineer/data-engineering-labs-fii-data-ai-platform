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


from src.ml.common.feature_contract import (
    get_feature_contract,
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


EXPECTED_SPLIT_VERSION = "v2"

EXPECTED_TRAINING_DATASET_VERSION = "v3"

EXPECTED_FEATURE_CONTRACT_VERSION = "v2"

EXPECTED_FEATURE_VERSION = "v6"

EXPECTED_TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)


DIAGNOSTICS_VERSION = "v2"


def load_dataset(
    path: Path,
    name: str,
) -> pd.DataFrame:
    """
    Carrega um split temporal.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"{name} não encontrado: {path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    if "feature_date" in dataframe.columns:
        dataframe[
            "feature_date"
        ] = pd.to_datetime(
            dataframe[
                "feature_date"
            ]
        )

    print(
        f"{name}: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def get_unique_string(
    dataframe: pd.DataFrame,
    column: str,
    split_name: str,
) -> str:
    """
    Obtém metadata textual com
    exatamente um valor.
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


def validate_split_contract(
    dataframe: pd.DataFrame,
    split_name: str,
) -> None:
    """
    Garante que o diagnóstico está
    comparando artefatos atuais da
    arquitetura econômica.
    """

    required_columns = [
        "feature_date",
        "ticker",
        "feature_ready",
        "ml_eligible",
        "split_name",
        "split_version",
        "training_dataset_version",
        "source_feature_version",
        "price_semantics",
        "return_semantics",
        "target_return_semantics",
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

    if dataframe.empty:
        raise ValueError(
            f"{split_name} está vazio."
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

    target_semantics = get_unique_string(
        dataframe,
        "target_return_semantics",
        split_name,
    )

    feature_ready_invalid = int(
        (
            ~dataframe[
                "feature_ready"
            ].astype(bool)
        ).sum()
    )

    ml_eligible_invalid = int(
        (
            ~dataframe[
                "ml_eligible"
            ].astype(bool)
        ).sum()
    )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    print(
        f"\nContrato {split_name.upper()}:"
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
        f"  price_semantics: "
        f"{price_semantics}"
    )

    print(
        f"  return_semantics: "
        f"{return_semantics}"
    )

    print(
        f"  target_return_semantics: "
        f"{target_semantics}"
    )

    print(
        f"  feature_ready=False: "
        f"{feature_ready_invalid:,}"
    )

    print(
        f"  ml_eligible=False: "
        f"{ml_eligible_invalid:,}"
    )

    print(
        f"  duplicidades: "
        f"{duplicate_count:,}"
    )

    if split_value != split_name:
        raise ValueError(
            f"{split_name}: split_name "
            f"incompatível: {split_value}"
        )

    if split_version != EXPECTED_SPLIT_VERSION:
        raise ValueError(
            "Feature Diagnostics v2 exige "
            f"Temporal Split "
            f"{EXPECTED_SPLIT_VERSION}."
        )

    if (
        training_version
        != EXPECTED_TRAINING_DATASET_VERSION
    ):
        raise ValueError(
            "Feature Diagnostics v2 exige "
            f"Training Dataset "
            f"{EXPECTED_TRAINING_DATASET_VERSION}."
        )

    if (
        feature_version
        != EXPECTED_FEATURE_VERSION
    ):
        raise ValueError(
            "Feature Diagnostics v2 exige "
            f"Features "
            f"{EXPECTED_FEATURE_VERSION}."
        )

    if (
        price_semantics
        != EXPECTED_PRICE_SEMANTICS
    ):
        raise ValueError(
            "price_semantics incompatível."
        )

    if (
        return_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "return_semantics incompatível."
        )

    if (
        target_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "target_return_semantics "
            "incompatível."
        )

    if feature_ready_invalid > 0:
        raise ValueError(
            f"{split_name} possui "
            "feature_ready=False."
        )

    if ml_eligible_invalid > 0:
        raise ValueError(
            f"{split_name} possui "
            "ml_eligible=False."
        )

    if duplicate_count > 0:
        raise ValueError(
            f"{split_name} possui "
            "duplicidades."
        )


def calculate_statistics(
    dataframe: pd.DataFrame,
    features: list[str],
    split_name: str,
) -> pd.DataFrame:
    """
    Calcula estatísticas descritivas
    das features.
    """

    rows: list[
        dict[str, object]
    ] = []

    for feature in features:
        series = pd.to_numeric(
            dataframe[
                feature
            ],
            errors="coerce",
        )

        finite_mask = (
            series.notna()
            &
            np.isfinite(
                series
            )
        )

        finite = series[
            finite_mask
        ]

        row = {
            "split": split_name,
            "feature": feature,

            "rows": len(series),

            "nulls": int(
                series.isna().sum()
            ),

            "non_finite": int(
                (
                    series.notna()
                    &
                    ~np.isfinite(
                        series
                    )
                ).sum()
            ),

            "finite_rows": int(
                len(finite)
            ),

            "mean": (
                float(
                    finite.mean()
                )
                if len(finite)
                else np.nan
            ),

            "std": (
                float(
                    finite.std()
                )
                if len(finite) > 1
                else np.nan
            ),

            "min": (
                float(
                    finite.min()
                )
                if len(finite)
                else np.nan
            ),

            "p01": (
                float(
                    finite.quantile(
                        0.01
                    )
                )
                if len(finite)
                else np.nan
            ),

            "p05": (
                float(
                    finite.quantile(
                        0.05
                    )
                )
                if len(finite)
                else np.nan
            ),

            "p25": (
                float(
                    finite.quantile(
                        0.25
                    )
                )
                if len(finite)
                else np.nan
            ),

            "median": (
                float(
                    finite.median()
                )
                if len(finite)
                else np.nan
            ),

            "p75": (
                float(
                    finite.quantile(
                        0.75
                    )
                )
                if len(finite)
                else np.nan
            ),

            "p95": (
                float(
                    finite.quantile(
                        0.95
                    )
                )
                if len(finite)
                else np.nan
            ),

            "p99": (
                float(
                    finite.quantile(
                        0.99
                    )
                )
                if len(finite)
                else np.nan
            ),

            "max": (
                float(
                    finite.max()
                )
                if len(finite)
                else np.nan
            ),
        }

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


def calculate_standardized_mean_difference(
    train_mean: float,
    train_std: float,
    validation_mean: float,
    validation_std: float,
) -> float:
    """
    Calcula Standardized Mean Difference
    usando desvio padrão combinado.

    SMD próximo de zero:
        distribuições centrais semelhantes.

    Quanto maior |SMD|,
    maior a mudança de regime/distribuição.
    """

    values = [
        train_mean,
        train_std,
        validation_mean,
        validation_std,
    ]

    if not all(
        np.isfinite(
            value
        )
        for value in values
    ):
        return np.nan

    pooled_variance = (
        (
            train_std ** 2
            +
            validation_std ** 2
        )
        / 2.0
    )

    if pooled_variance <= 0:
        return np.nan

    pooled_std = np.sqrt(
        pooled_variance
    )

    return float(
        (
            validation_mean
            -
            train_mean
        )
        / pooled_std
    )


def build_distribution_comparison(
    train_stats: pd.DataFrame,
    validation_stats: pd.DataFrame,
) -> pd.DataFrame:
    """
    Consolida TRAIN e VALIDATION
    por feature.
    """

    train = (
        train_stats
        .set_index(
            "feature"
        )
    )

    validation = (
        validation_stats
        .set_index(
            "feature"
        )
    )

    rows: list[
        dict[str, object]
    ] = []

    for feature in train.index:
        train_mean = float(
            train.loc[
                feature,
                "mean",
            ]
        )

        validation_mean = float(
            validation.loc[
                feature,
                "mean",
            ]
        )

        train_std = float(
            train.loc[
                feature,
                "std",
            ]
        )

        validation_std = float(
            validation.loc[
                feature,
                "std",
            ]
        )

        smd = (
            calculate_standardized_mean_difference(
                train_mean=train_mean,
                train_std=train_std,
                validation_mean=(
                    validation_mean
                ),
                validation_std=(
                    validation_std
                ),
            )
        )

        std_ratio = np.nan

        if (
            np.isfinite(
                train_std
            )
            and train_std > 0
            and np.isfinite(
                validation_std
            )
        ):
            std_ratio = float(
                validation_std
                / train_std
            )

        rows.append(
            {
                "feature": feature,

                "train_mean": (
                    train_mean
                ),

                "validation_mean": (
                    validation_mean
                ),

                "mean_delta": (
                    validation_mean
                    - train_mean
                ),

                "train_median": float(
                    train.loc[
                        feature,
                        "median",
                    ]
                ),

                "validation_median": float(
                    validation.loc[
                        feature,
                        "median",
                    ]
                ),

                "median_delta": float(
                    validation.loc[
                        feature,
                        "median",
                    ]
                    -
                    train.loc[
                        feature,
                        "median",
                    ]
                ),

                "train_std": (
                    train_std
                ),

                "validation_std": (
                    validation_std
                ),

                "std_ratio": (
                    std_ratio
                ),

                "train_p01": float(
                    train.loc[
                        feature,
                        "p01",
                    ]
                ),

                "validation_p01": float(
                    validation.loc[
                        feature,
                        "p01",
                    ]
                ),

                "train_p99": float(
                    train.loc[
                        feature,
                        "p99",
                    ]
                ),

                "validation_p99": float(
                    validation.loc[
                        feature,
                        "p99",
                    ]
                ),

                "train_nulls": int(
                    train.loc[
                        feature,
                        "nulls",
                    ]
                ),

                "validation_nulls": int(
                    validation.loc[
                        feature,
                        "nulls",
                    ]
                ),

                "smd": (
                    smd
                ),

                "abs_smd": (
                    abs(
                        smd
                    )
                    if np.isfinite(
                        smd
                    )
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def classify_smd(
    abs_smd: float,
) -> str:
    """
    Classificação operacional simples.

    Não é um teste estatístico.

    < 0.10  = LOW
    < 0.25  = MODERATE
    < 0.50  = HIGH
    >=0.50  = VERY_HIGH
    """

    if not np.isfinite(
        abs_smd
    ):
        return "UNDEFINED"

    if abs_smd < 0.10:
        return "LOW"

    if abs_smd < 0.25:
        return "MODERATE"

    if abs_smd < 0.50:
        return "HIGH"

    return "VERY_HIGH"


def print_ratio_extremes(
    dataframe: pd.DataFrame,
    features: list[str],
    split_name: str,
) -> None:
    """
    Inspeciona especificamente ratios,
    porque ratios podem sofrer explosões
    quando o denominador se aproxima
    de zero.
    """

    ratio_features = [
        feature
        for feature in features
        if "ratio" in feature
    ]

    print(
        "\n======================================"
    )
    print(
        f"Extremos de ratios - "
        f"{split_name}"
    )
    print(
        "======================================"
    )

    for feature in ratio_features:
        series = pd.to_numeric(
            dataframe[
                feature
            ],
            errors="coerce",
        )

        finite = series[
            series.notna()
            &
            np.isfinite(
                series
            )
        ]

        if finite.empty:
            print(
                f"\n{feature}: "
                "sem valores finitos"
            )
            continue

        print(
            f"\n{feature}"
        )

        print(
            f"  min:    "
            f"{finite.min():.6f}"
        )

        print(
            f"  p01:    "
            f"{finite.quantile(0.01):.6f}"
        )

        print(
            f"  p05:    "
            f"{finite.quantile(0.05):.6f}"
        )

        print(
            f"  median: "
            f"{finite.median():.6f}"
        )

        print(
            f"  p95:    "
            f"{finite.quantile(0.95):.6f}"
        )

        print(
            f"  p99:    "
            f"{finite.quantile(0.99):.6f}"
        )

        print(
            f"  max:    "
            f"{finite.max():.6f}"
        )


def print_distribution_comparison(
    comparison: pd.DataFrame,
) -> None:
    """
    Exibe comparação feature a feature.
    """

    print(
        "\n======================================"
    )
    print(
        "Mudança TRAIN -> VALIDATION"
    )
    print(
        "======================================"
    )

    for _, row in comparison.iterrows():
        classification = classify_smd(
            row[
                "abs_smd"
            ]
        )

        print(
            f"\n{row['feature']}"
        )

        print(
            "  mean    "
            f"train={row['train_mean']:.6f} | "
            f"validation="
            f"{row['validation_mean']:.6f}"
        )

        print(
            "  median  "
            f"train={row['train_median']:.6f} | "
            f"validation="
            f"{row['validation_median']:.6f}"
        )

        print(
            "  std     "
            f"train={row['train_std']:.6f} | "
            f"validation="
            f"{row['validation_std']:.6f}"
        )

        print(
            "  p01     "
            f"train={row['train_p01']:.6f} | "
            f"validation="
            f"{row['validation_p01']:.6f}"
        )

        print(
            "  p99     "
            f"train={row['train_p99']:.6f} | "
            f"validation="
            f"{row['validation_p99']:.6f}"
        )

        if np.isfinite(
            row[
                "std_ratio"
            ]
        ):
            print(
                "  std ratio "
                f"validation/train="
                f"{row['std_ratio']:.4f}"
            )

        else:
            print(
                "  std ratio "
                "validation/train="
                "undefined"
            )

        if np.isfinite(
            row[
                "smd"
            ]
        ):
            print(
                "  SMD: "
                f"{row['smd']:+.4f} "
                f"| {classification}"
            )

        else:
            print(
                "  SMD: undefined"
            )


def print_shift_ranking(
    comparison: pd.DataFrame,
) -> None:
    """
    Mostra features ordenadas pela
    intensidade da mudança entre splits.
    """

    ranking = (
        comparison
        .sort_values(
            by="abs_smd",
            ascending=False,
            na_position="last",
        )
        .reset_index(
            drop=True
        )
    )

    print(
        "\n======================================"
    )
    print(
        "Ranking de mudança de regime"
    )
    print(
        "======================================"
    )

    for position, row in (
        ranking.iterrows()
    ):
        abs_smd = row[
            "abs_smd"
        ]

        classification = (
            classify_smd(
                abs_smd
            )
        )

        if np.isfinite(
            row[
                "smd"
            ]
        ):
            smd_display = (
                f"{row['smd']:+.4f}"
            )

        else:
            smd_display = (
                "undefined"
            )

        print(
            f"{position + 1:02d}. "
            f"{row['feature']} | "
            f"SMD={smd_display} | "
            f"{classification}"
        )


def print_shift_summary(
    comparison: pd.DataFrame,
) -> None:
    """
    Consolida quantas features estão
    em cada faixa operacional de shift.
    """

    classifications = (
        comparison[
            "abs_smd"
        ]
        .apply(
            classify_smd
        )
    )

    counts = (
        classifications
        .value_counts()
        .to_dict()
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo de mudança de regime"
    )
    print(
        "======================================"
    )

    for category in [
        "LOW",
        "MODERATE",
        "HIGH",
        "VERY_HIGH",
        "UNDEFINED",
    ]:
        print(
            f"{category}: "
            f"{counts.get(category, 0):,}"
        )

    meaningful_shift = int(
        (
            comparison[
                "abs_smd"
            ]
            >= 0.25
        ).sum()
    )

    print(
        "\nFeatures com |SMD| >= 0.25: "
        f"{meaningful_shift:,}"
        f"/{len(comparison):,}"
    )


def print_integrity_summary(
    train_stats: pd.DataFrame,
    validation_stats: pd.DataFrame,
) -> None:
    """
    Integridade técnica das features.
    """

    train_non_finite = int(
        train_stats[
            "non_finite"
        ].sum()
    )

    validation_non_finite = int(
        validation_stats[
            "non_finite"
        ].sum()
    )

    train_nulls = int(
        train_stats[
            "nulls"
        ].sum()
    )

    validation_nulls = int(
        validation_stats[
            "nulls"
        ].sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Integridade"
    )
    print(
        "======================================"
    )

    print(
        "TRAIN nulls total: "
        f"{train_nulls:,}"
    )

    print(
        "VALIDATION nulls total: "
        f"{validation_nulls:,}"
    )

    print(
        "TRAIN non-finite total: "
        f"{train_non_finite:,}"
    )

    print(
        "VALIDATION non-finite total: "
        f"{validation_non_finite:,}"
    )

    if train_non_finite > 0:
        raise ValueError(
            "TRAIN possui features "
            "não finitas."
        )

    if validation_non_finite > 0:
        raise ValueError(
            "VALIDATION possui features "
            "não finitas."
        )


def main() -> None:
    print(
        "Executando FII Feature Diagnostics..."
    )

    print(
        f"Diagnostics version: "
        f"{DIAGNOSTICS_VERSION}"
    )

    print(
        "Comparison: "
        "TRAIN vs VALIDATION"
    )

    train = load_dataset(
        TRAIN_PATH,
        "train",
    )

    validation = load_dataset(
        VALIDATION_PATH,
        "validation",
    )

    print(
        "\n======================================"
    )
    print(
        "Validação dos contratos"
    )
    print(
        "======================================"
    )

    validate_split_contract(
        dataframe=train,
        split_name="train",
    )

    validate_split_contract(
        dataframe=validation,
        split_name="validation",
    )

    contract = get_feature_contract(
        train
    )

    if (
        contract.version
        != EXPECTED_FEATURE_CONTRACT_VERSION
    ):
        raise ValueError(
            "Feature Diagnostics v2 exige "
            f"Feature Contract "
            f"{EXPECTED_FEATURE_CONTRACT_VERSION}."
        )

    features = list(
        contract.features
    )

    print(
        "\n======================================"
    )
    print(
        "Feature Contract"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{contract.version}"
    )

    print(
        f"Source feature version: "
        f"{contract.source_feature_version}"
    )

    print(
        f"Price semantics: "
        f"{contract.price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{contract.return_semantics}"
    )

    print(
        f"Windows: "
        f"{contract.windows}"
    )

    print(
        f"Features: "
        f"{len(features)}"
    )

    train_stats = calculate_statistics(
        dataframe=train,
        features=features,
        split_name="train",
    )

    validation_stats = calculate_statistics(
        dataframe=validation,
        features=features,
        split_name="validation",
    )

    print_integrity_summary(
        train_stats=train_stats,
        validation_stats=validation_stats,
    )

    print_ratio_extremes(
        dataframe=train,
        features=features,
        split_name="TRAIN",
    )

    print_ratio_extremes(
        dataframe=validation,
        features=features,
        split_name="VALIDATION",
    )

    comparison = (
        build_distribution_comparison(
            train_stats=train_stats,
            validation_stats=validation_stats,
        )
    )

    print_distribution_comparison(
        comparison
    )

    print_shift_ranking(
        comparison
    )

    print_shift_summary(
        comparison
    )

    print(
        "\n======================================"
    )
    print(
        "Interpretação operacional"
    )
    print(
        "======================================"
    )

    print(
        "|SMD| < 0.10: LOW"
    )

    print(
        "0.10 <= |SMD| < 0.25: MODERATE"
    )

    print(
        "0.25 <= |SMD| < 0.50: HIGH"
    )

    print(
        "|SMD| >= 0.50: VERY_HIGH"
    )

    print(
        "\nEssas faixas são usadas como "
        "heurística de diagnóstico de "
        "mudança de distribuição."
    )

    print(
        "Elas não constituem sozinhas "
        "evidência estatística causal."
    )

    print(
        "\nDiagnóstico concluído."
    )


if __name__ == "__main__":
    main()