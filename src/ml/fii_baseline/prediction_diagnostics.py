from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


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

RANDOM_STATE = 42
RF_ESTIMATORS = 200


def load_dataset(
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

    print(
        f"{name}: {len(dataframe):,} linhas"
    )

    return dataframe


def discover_target(
    dataframe: pd.DataFrame,
) -> str:
    if "target_name" not in dataframe.columns:
        raise ValueError(
            "target_name não encontrada."
        )

    targets = (
        dataframe["target_name"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(targets) != 1:
        raise ValueError(
            f"Target ambíguo: {targets.tolist()}"
        )

    target = targets[0]

    if target not in dataframe.columns:
        raise ValueError(
            f"Target não encontrado: {target}"
        )

    return target


def build_models() -> dict[str, object]:
    return {
        "LinearRegression": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median",
                    ),
                ),
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "model",
                    LinearRegression(),
                ),
            ]
        ),
        "RandomForestRegressor": Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median",
                    ),
                ),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=RF_ESTIMATORS,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def print_distribution(
    name: str,
    values: np.ndarray | pd.Series,
) -> None:
    series = pd.Series(
        np.asarray(values, dtype=float)
    )

    print(
        f"\n{name}"
    )

    print(
        f"  min:    {series.min() * 100:.4f}%"
    )

    print(
        f"  p01:    {series.quantile(0.01) * 100:.4f}%"
    )

    print(
        f"  p05:    {series.quantile(0.05) * 100:.4f}%"
    )

    print(
        f"  median: {series.median() * 100:.4f}%"
    )

    print(
        f"  p95:    {series.quantile(0.95) * 100:.4f}%"
    )

    print(
        f"  p99:    {series.quantile(0.99) * 100:.4f}%"
    )

    print(
        f"  max:    {series.max() * 100:.4f}%"
    )


def print_large_prediction_counts(
    predictions: np.ndarray,
) -> None:
    absolute_predictions = np.abs(
        predictions
    )

    thresholds = [
        0.05,
        0.10,
        0.20,
        0.50,
        1.00,
    ]

    print(
        "\nPrevisões absolutas acima de:"
    )

    for threshold in thresholds:
        count = int(
            (
                absolute_predictions
                >= threshold
            ).sum()
        )

        percentage = (
            count
            / len(predictions)
            * 100
        )

        print(
            f"  {threshold * 100:>6.1f}%: "
            f"{count:,} "
            f"({percentage:.2f}%)"
        )


def print_worst_errors(
    validation: pd.DataFrame,
    target: str,
    predictions: np.ndarray,
    model_name: str,
) -> None:
    diagnostic = validation[
        [
            "feature_date",
            "ticker",
            target,
        ]
    ].copy()

    diagnostic[
        "prediction"
    ] = predictions

    diagnostic[
        "absolute_error"
    ] = (
        diagnostic[
            "prediction"
        ]
        - diagnostic[
            target
        ]
    ).abs()

    diagnostic = diagnostic.sort_values(
        "absolute_error",
        ascending=False,
    )

    print(
        "\n======================================"
    )

    print(
        f"20 maiores erros - {model_name}"
    )

    print(
        "======================================"
    )

    display = diagnostic.head(
        20
    ).copy()

    display[
        "target_pct"
    ] = (
        display[target]
        * 100
    )

    display[
        "prediction_pct"
    ] = (
        display["prediction"]
        * 100
    )

    display[
        "absolute_error_pct"
    ] = (
        display["absolute_error"]
        * 100
    )

    print(
        display[
            [
                "feature_date",
                "ticker",
                "target_pct",
                "prediction_pct",
                "absolute_error_pct",
            ]
        ].to_string(
            index=False
        )
    )


def print_rf_feature_importance(
    model: Pipeline,
    feature_columns: list[str],
) -> None:
    random_forest = model.named_steps[
        "model"
    ]

    importance = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": (
                random_forest.feature_importances_
            ),
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    print(
        "\n======================================"
    )

    print(
        "RandomForest Feature Importance"
    )

    print(
        "======================================"
    )

    for _, row in importance.iterrows():
        print(
            f"{row['feature']:<35} "
            f"{row['importance']:.6f}"
        )


def main() -> None:
    print(
        "Executando diagnóstico "
        "das previsões..."
    )

    train = load_dataset(
        TRAIN_PATH,
        "train",
    )

    validation = load_dataset(
        VALIDATION_PATH,
        "validation",
    )

    target = discover_target(
        train
    )

    contract = get_feature_contract(
        train
    )

    feature_columns = list(
        contract.features
    )

    x_train = train[
        feature_columns
    ]

    y_train = train[
        target
    ].astype(float)

    x_validation = validation[
        feature_columns
    ]

    y_validation = validation[
        target
    ].astype(float)

    print(
        "\n======================================"
    )

    print(
        "Target"
    )

    print(
        "======================================"
    )

    print(
        f"Target: {target}"
    )

    print(
        f"Feature Contract: {contract.version}"
    )

    print(
        f"Features: {len(feature_columns)}"
    )

    print_distribution(
        "TRAIN target",
        y_train,
    )

    print_distribution(
        "VALIDATION target",
        y_validation,
    )

    models = build_models()

    for model_name, model in models.items():
        print(
            "\n======================================"
        )

        print(
            f"Modelo: {model_name}"
        )

        print(
            "======================================"
        )

        model.fit(
            x_train,
            y_train,
        )

        predictions = model.predict(
            x_validation
        )

        print_distribution(
            "Predictions",
            predictions,
        )

        print_large_prediction_counts(
            predictions
        )

        print_worst_errors(
            validation=validation,
            target=target,
            predictions=predictions,
            model_name=model_name,
        )

        if (
            model_name
            == "RandomForestRegressor"
        ):
            print_rf_feature_importance(
                model=model,
                feature_columns=(
                    feature_columns
                ),
            )

    print(
        "\nDiagnóstico de previsões "
        "concluído."
    )


if __name__ == "__main__":
    main()