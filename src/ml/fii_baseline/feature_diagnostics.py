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

TRAIN_PATH = SPLIT_DIR / "train.parquet"
VALIDATION_PATH = SPLIT_DIR / "validation.parquet"


def load_dataset(
    path: Path,
    name: str,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{name} não encontrado: {path}"
        )

    dataframe = pd.read_parquet(path)

    print(
        f"{name}: {len(dataframe):,} linhas"
    )

    return dataframe


def calculate_statistics(
    dataframe: pd.DataFrame,
    features: list[str],
    split_name: str,
) -> pd.DataFrame:
    rows = []

    for feature in features:
        series = pd.to_numeric(
            dataframe[feature],
            errors="coerce",
        )

        finite_mask = np.isfinite(series)

        finite = series[
            finite_mask
        ]

        rows.append(
            {
                "split": split_name,
                "feature": feature,
                "rows": len(series),
                "nulls": int(series.isna().sum()),
                "non_finite": int(
                    (~finite_mask & series.notna()).sum()
                ),
                "min": (
                    float(finite.min())
                    if len(finite)
                    else np.nan
                ),
                "p01": (
                    float(finite.quantile(0.01))
                    if len(finite)
                    else np.nan
                ),
                "p05": (
                    float(finite.quantile(0.05))
                    if len(finite)
                    else np.nan
                ),
                "median": (
                    float(finite.median())
                    if len(finite)
                    else np.nan
                ),
                "p95": (
                    float(finite.quantile(0.95))
                    if len(finite)
                    else np.nan
                ),
                "p99": (
                    float(finite.quantile(0.99))
                    if len(finite)
                    else np.nan
                ),
                "max": (
                    float(finite.max())
                    if len(finite)
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows)


def print_ratio_extremes(
    dataframe: pd.DataFrame,
    features: list[str],
    split_name: str,
) -> None:
    ratio_features = [
        feature
        for feature in features
        if "ratio" in feature
    ]

    print(
        "\n======================================"
    )
    print(
        f"Extremos de ratios - {split_name}"
    )
    print(
        "======================================"
    )

    for feature in ratio_features:
        series = pd.to_numeric(
            dataframe[feature],
            errors="coerce",
        )

        finite = series[
            np.isfinite(series)
        ]

        if finite.empty:
            print(
                f"{feature}: sem valores finitos"
            )
            continue

        print(
            f"\n{feature}"
        )

        print(
            f"  min:    {finite.min():.6f}"
        )

        print(
            f"  p01:    {finite.quantile(0.01):.6f}"
        )

        print(
            f"  median: {finite.median():.6f}"
        )

        print(
            f"  p99:    {finite.quantile(0.99):.6f}"
        )

        print(
            f"  max:    {finite.max():.6f}"
        )


def compare_train_validation(
    train_stats: pd.DataFrame,
    validation_stats: pd.DataFrame,
) -> None:
    train = train_stats.set_index(
        "feature"
    )

    validation = validation_stats.set_index(
        "feature"
    )

    print(
        "\n======================================"
    )
    print(
        "Mudança Train -> Validation"
    )
    print(
        "======================================"
    )

    for feature in train.index:
        train_median = train.loc[
            feature,
            "median",
        ]

        validation_median = validation.loc[
            feature,
            "median",
        ]

        train_p99 = train.loc[
            feature,
            "p99",
        ]

        validation_p99 = validation.loc[
            feature,
            "p99",
        ]

        print(
            f"\n{feature}"
        )

        print(
            "  median "
            f"train={train_median:.6f} | "
            f"validation={validation_median:.6f}"
        )

        print(
            "  p99    "
            f"train={train_p99:.6f} | "
            f"validation={validation_p99:.6f}"
        )


def main() -> None:
    print(
        "Executando diagnóstico "
        "do Feature Contract..."
    )

    train = load_dataset(
        TRAIN_PATH,
        "train",
    )

    validation = load_dataset(
        VALIDATION_PATH,
        "validation",
    )

    contract = get_feature_contract(
        train
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
        f"Version: {contract.version}"
    )

    print(
        f"Features: {len(features)}"
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

    compare_train_validation(
        train_stats=train_stats,
        validation_stats=validation_stats,
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
        "TRAIN non-finite total: "
        f"{train_stats['non_finite'].sum():,}"
    )

    print(
        "VALIDATION non-finite total: "
        f"{validation_stats['non_finite'].sum():,}"
    )

    print(
        "\nDiagnóstico concluído."
    )


if __name__ == "__main__":
    main()