from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


import numpy as np
import pandas as pd

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.ml.common.feature_contract import (
    get_feature_contract,
)


SPLIT_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
)

TRAIN_PATH = (
    SPLIT_BASE_DIR
    / "train.parquet"
)

VALIDATION_PATH = (
    SPLIT_BASE_DIR
    / "validation.parquet"
)

TEST_PATH = (
    SPLIT_BASE_DIR
    / "test.parquet"
)

DEFAULT_RANDOM_STATE = 42
DEFAULT_RF_ESTIMATORS = 200

BASELINE_VERSION = "v3"


@dataclass
class ModelResult:
    name: str
    mae: float
    rmse: float
    r2: float
    directional_accuracy: float
    directional_lift: float


def load_split(
    path: Path,
    split_name: str,
) -> pd.DataFrame:
    """
    Carrega um split temporal.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Split {split_name} não encontrado: {path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    print(
        f"{split_name}: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def discover_target_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Descobre dinamicamente o target.
    """

    if "target_name" not in dataframe.columns:
        raise ValueError(
            "Coluna target_name não encontrada."
        )

    values = (
        dataframe[
            "target_name"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    if len(values) == 0:
        raise ValueError(
            "Nenhum target_name encontrado."
        )

    if len(values) > 1:
        raise ValueError(
            "Mais de um target_name encontrado: "
            f"{values.tolist()}"
        )

    target_column = values[0]

    if target_column not in dataframe.columns:
        raise ValueError(
            f"Target {target_column} "
            "não existe no dataset."
        )

    return target_column


def validate_target_semantics(
    dataframe: pd.DataFrame,
) -> None:
    """
    Garante que o baseline está usando
    o contrato v2 do training dataset.
    """

    required_columns = [
        "training_dataset_version",
        "target_horizon_semantics",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Metadata do target ausente: "
            f"{missing_columns}"
        )

    versions = (
        dataframe[
            "training_dataset_version"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(versions) != 1:
        raise ValueError(
            "Training dataset version "
            f"ambígua: {versions.tolist()}"
        )

    semantics = (
        dataframe[
            "target_horizon_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(semantics) != 1:
        raise ValueError(
            "Target semantics ambígua: "
            f"{semantics.tolist()}"
        )

    if semantics[0] != (
        "GLOBAL_B3_TRADING_DAYS"
    ):
        raise ValueError(
            "Baseline exige target baseado "
            "em pregões globais B3."
        )


def validate_split_contract(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    target_column: str,
) -> None:
    """
    Valida contrato mínimo dos splits.
    """

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "feature_ready",
        target_column,
    ]

    for split_name, dataframe in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:
        missing_columns = [
            column
            for column in required_columns
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(
                f"{split_name} possui colunas "
                f"ausentes: {missing_columns}"
            )

        if dataframe.empty:
            raise ValueError(
                f"{split_name} está vazio."
            )

        if dataframe[
            target_column
        ].isna().any():
            raise ValueError(
                f"{split_name} possui target nulo."
            )

        if not dataframe[
            "feature_ready"
        ].all():
            raise ValueError(
                f"{split_name} possui linhas "
                "feature_ready=False."
            )


def prepare_xy(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> tuple[
    pd.DataFrame,
    pd.Series,
]:
    """
    Separa X e y.
    """

    x = dataframe[
        feature_columns
    ].copy()

    y = dataframe[
        target_column
    ].astype(float).copy()

    return x, y


def build_models(
    random_state: int,
    rf_estimators: int,
) -> dict[str, object]:
    """
    Modelos baseline.
    """

    models: dict[
        str,
        object,
    ] = {}

    models[
        "DummyRegressor"
    ] = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "model",
                DummyRegressor(
                    strategy="mean"
                ),
            ),
        ]
    )

    models[
        "LinearRegression"
    ] = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
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
    )

    models[
        "RandomForestRegressor"
    ] = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=rf_estimators,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    return models


def calculate_majority_direction_baseline(
    y_true: pd.Series,
) -> tuple[
    float,
    str,
]:
    """
    Baseline ingênuo para direção.
    """

    positive_rate = float(
        (
            y_true
            > 0
        ).mean()
    )

    non_positive_rate = (
        1.0
        - positive_rate
    )

    if (
        positive_rate
        > non_positive_rate
    ):
        return (
            positive_rate,
            "POSITIVE",
        )

    return (
        non_positive_rate,
        "NON_POSITIVE",
    )


def calculate_directional_accuracy(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> float:
    """
    Mede se o modelo acertou
    o sinal do retorno.
    """

    true_direction = (
        np.asarray(
            y_true
        )
        > 0
    )

    predicted_direction = (
        np.asarray(
            y_pred
        )
        > 0
    )

    accuracy = (
        true_direction
        == predicted_direction
    ).mean()

    return float(
        accuracy
    )


def calculate_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
    majority_direction_accuracy: float,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
]:
    """
    Calcula métricas de regressão
    e direção.
    """

    mae = mean_absolute_error(
        y_true,
        y_pred,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred,
        )
    )

    r2 = r2_score(
        y_true,
        y_pred,
    )

    directional_accuracy = (
        calculate_directional_accuracy(
            y_true=y_true,
            y_pred=y_pred,
        )
    )

    directional_lift = (
        directional_accuracy
        - majority_direction_accuracy
    )

    return (
        float(mae),
        float(rmse),
        float(r2),
        float(directional_accuracy),
        float(directional_lift),
    )


def evaluate_models(
    models: dict[str, object],
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_validation: pd.DataFrame,
    y_validation: pd.Series,
    majority_direction_accuracy: float,
) -> list[ModelResult]:
    """
    Treina no TRAIN e avalia somente
    no VALIDATION.
    """

    results: list[
        ModelResult
    ] = []

    print(
        "\n======================================"
    )
    print(
        "Treinamento e Validation"
    )
    print(
        "======================================"
    )

    for name, model in models.items():
        print(
            f"\nTreinando: {name}"
        )

        model.fit(
            x_train,
            y_train,
        )

        predictions = model.predict(
            x_validation
        )

        (
            mae,
            rmse,
            r2,
            directional_accuracy,
            directional_lift,
        ) = calculate_metrics(
            y_true=y_validation,
            y_pred=predictions,
            majority_direction_accuracy=(
                majority_direction_accuracy
            ),
        )

        results.append(
            ModelResult(
                name=name,
                mae=mae,
                rmse=rmse,
                r2=r2,
                directional_accuracy=(
                    directional_accuracy
                ),
                directional_lift=(
                    directional_lift
                ),
            )
        )

        print(
            f"  MAE:  "
            f"{mae:.8f} "
            f"({mae * 100:.4f}%)"
        )

        print(
            f"  RMSE: "
            f"{rmse:.8f} "
            f"({rmse * 100:.4f}%)"
        )

        print(
            f"  R²:   "
            f"{r2:.8f}"
        )

        print(
            "  Directional Accuracy: "
            f"{directional_accuracy:.4f} "
            f"({directional_accuracy * 100:.2f}%)"
        )

        print(
            "  Directional Lift: "
            f"{directional_lift * 100:+.2f} p.p."
        )

    return results


def results_to_dataframe(
    results: list[ModelResult],
) -> pd.DataFrame:
    """
    Converte resultados para DataFrame.
    """

    return pd.DataFrame(
        [
            {
                "model": result.name,
                "mae": result.mae,
                "rmse": result.rmse,
                "r2": result.r2,
                "directional_accuracy": (
                    result.directional_accuracy
                ),
                "directional_lift": (
                    result.directional_lift
                ),
            }
            for result in results
        ]
    )


def print_feature_contract_summary(
    version: str,
    windows: tuple[int, ...],
    features: tuple[str, ...],
) -> None:
    """
    Mostra o Feature Contract usado.
    """

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
        f"{version}"
    )

    print(
        f"Windows: "
        f"{windows}"
    )

    print(
        f"Features: "
        f"{len(features):,}"
    )

    for feature in features:
        print(
            f"  {feature}"
        )


def print_target_summary(
    y_train: pd.Series,
    y_validation: pd.Series,
) -> None:
    """
    Exibe distribuição do target.
    """

    print(
        "\n======================================"
    )
    print(
        "Distribuição do target"
    )
    print(
        "======================================"
    )

    for name, target in [
        ("Train", y_train),
        ("Validation", y_validation),
    ]:
        positive_rate = (
            target
            > 0
        ).mean()

        print(
            f"\n{name}:"
        )

        print(
            f"  Média: "
            f"{target.mean() * 100:.4f}%"
        )

        print(
            f"  Mediana: "
            f"{target.median() * 100:.4f}%"
        )

        print(
            f"  Desvio padrão: "
            f"{target.std() * 100:.4f}%"
        )

        print(
            f"  Positivos: "
            f"{positive_rate * 100:.2f}%"
        )

        print(
            f"  Não positivos: "
            f"{(1 - positive_rate) * 100:.2f}%"
        )


def print_majority_baseline(
    accuracy: float,
    direction: str,
) -> None:
    """
    Exibe baseline direcional majoritário.
    """

    print(
        "\n======================================"
    )
    print(
        "Majority Direction Baseline"
    )
    print(
        "======================================"
    )

    print(
        f"Direção majoritária: "
        f"{direction}"
    )

    print(
        f"Accuracy ingênua: "
        f"{accuracy * 100:.2f}%"
    )


def print_metric_rankings(
    results: pd.DataFrame,
) -> None:
    """
    Exibe rankings separados.
    """

    rankings = [
        (
            "MAE",
            "mae",
            True,
            "%",
        ),
        (
            "RMSE",
            "rmse",
            True,
            "%",
        ),
        (
            "R²",
            "r2",
            False,
            "r2",
        ),
        (
            "Directional Accuracy",
            "directional_accuracy",
            False,
            "%",
        ),
        (
            "Directional Lift",
            "directional_lift",
            False,
            "pp",
        ),
    ]

    for (
        title,
        column,
        ascending,
        display_type,
    ) in rankings:

        print(
            "\n======================================"
        )

        print(
            f"Ranking por {title}"
        )

        print(
            "======================================"
        )

        ranking = results.sort_values(
            by=column,
            ascending=ascending,
        )

        for position, (_, row) in enumerate(
            ranking.iterrows(),
            start=1,
        ):
            value = row[
                column
            ]

            if display_type == "%":
                display = (
                    f"{value * 100:.4f}%"
                )

            elif display_type == "pp":
                display = (
                    f"{value * 100:+.2f} p.p."
                )

            else:
                display = (
                    f"{value:.6f}"
                )

            print(
                f"{position}. "
                f"{row['model']} | "
                f"{display}"
            )


def print_best_by_metric(
    results: pd.DataFrame,
) -> None:
    """
    Resume melhor modelo por métrica.
    """

    best_mae = (
        results.sort_values(
            "mae"
        )
        .iloc[0]
    )

    best_rmse = (
        results.sort_values(
            "rmse"
        )
        .iloc[0]
    )

    best_r2 = (
        results.sort_values(
            "r2",
            ascending=False,
        )
        .iloc[0]
    )

    best_direction = (
        results.sort_values(
            "directional_accuracy",
            ascending=False,
        )
        .iloc[0]
    )

    best_lift = (
        results.sort_values(
            "directional_lift",
            ascending=False,
        )
        .iloc[0]
    )

    print(
        "\n======================================"
    )
    print(
        "Melhores por métrica"
    )
    print(
        "======================================"
    )

    print(
        f"MAE: "
        f"{best_mae['model']} "
        f"({best_mae['mae'] * 100:.4f}%)"
    )

    print(
        f"RMSE: "
        f"{best_rmse['model']} "
        f"({best_rmse['rmse'] * 100:.4f}%)"
    )

    print(
        f"R²: "
        f"{best_r2['model']} "
        f"({best_r2['r2']:.6f})"
    )

    print(
        "Directional Accuracy: "
        f"{best_direction['model']} "
        f"({best_direction['directional_accuracy'] * 100:.2f}%)"
    )

    print(
        "Directional Lift: "
        f"{best_lift['model']} "
        f"({best_lift['directional_lift'] * 100:+.2f} p.p.)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Executa baseline de ML para "
            "previsão de retorno futuro "
            "de FIIs."
        )
    )

    parser.add_argument(
        "--rf-estimators",
        type=int,
        default=DEFAULT_RF_ESTIMATORS,
        help=(
            "Quantidade de árvores do "
            "RandomForest. Default: 200."
        ),
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=DEFAULT_RANDOM_STATE,
        help=(
            "Seed para reprodutibilidade. "
            "Default: 42."
        ),
    )

    args = parser.parse_args()

    if args.rf_estimators <= 0:
        raise ValueError(
            "--rf-estimators deve ser "
            "maior que zero."
        )

    print(
        "Executando FII ML Baseline..."
    )

    print(
        f"Baseline version: "
        f"{BASELINE_VERSION}"
    )

    train = load_split(
        TRAIN_PATH,
        "train",
    )

    validation = load_split(
        VALIDATION_PATH,
        "validation",
    )

    test = load_split(
        TEST_PATH,
        "test",
    )

    validate_target_semantics(
        train
    )

    target_column = (
        discover_target_column(
            train
        )
    )

    print(
        f"\nTarget: "
        f"{target_column}"
    )

    validate_split_contract(
        train=train,
        validation=validation,
        test=test,
        target_column=target_column,
    )

    feature_contract = (
        get_feature_contract(
            train
        )
    )

    feature_columns = list(
        feature_contract.features
    )

    print_feature_contract_summary(
        version=(
            feature_contract.version
        ),
        windows=(
            feature_contract.windows
        ),
        features=(
            feature_contract.features
        ),
    )

    x_train, y_train = prepare_xy(
        dataframe=train,
        feature_columns=feature_columns,
        target_column=target_column,
    )

    x_validation, y_validation = (
        prepare_xy(
            dataframe=validation,
            feature_columns=feature_columns,
            target_column=target_column,
        )
    )

    print(
        "\n======================================"
    )
    print(
        "Datasets"
    )
    print(
        "======================================"
    )

    print(
        f"Train: "
        f"{len(x_train):,}"
    )

    print(
        f"Validation: "
        f"{len(x_validation):,}"
    )

    print(
        f"Test reservado: "
        f"{len(test):,}"
    )

    print_target_summary(
        y_train=y_train,
        y_validation=y_validation,
    )

    (
        majority_direction_accuracy,
        majority_direction,
    ) = calculate_majority_direction_baseline(
        y_validation
    )

    print_majority_baseline(
        accuracy=(
            majority_direction_accuracy
        ),
        direction=(
            majority_direction
        ),
    )

    models = build_models(
        random_state=args.random_state,
        rf_estimators=args.rf_estimators,
    )

    results = evaluate_models(
        models=models,
        x_train=x_train,
        y_train=y_train,
        x_validation=x_validation,
        y_validation=y_validation,
        majority_direction_accuracy=(
            majority_direction_accuracy
        ),
    )

    results_dataframe = (
        results_to_dataframe(
            results
        )
    )

    print_metric_rankings(
        results_dataframe
    )

    print_best_by_metric(
        results_dataframe
    )

    print(
        "\n======================================"
    )
    print(
        "Conclusão do baseline"
    )
    print(
        "======================================"
    )

    print(
        "Feature Contract: "
        f"{feature_contract.version}"
    )

    print(
        "Os modelos foram comparados apenas "
        "no VALIDATION."
    )

    print(
        "O conjunto TEST continua reservado "
        "para avaliação final futura."
    )

    print(
        "Directional Lift mede o ganho "
        "sobre a estratégia ingênua de "
        "sempre prever a direção majoritária."
    )


if __name__ == "__main__":
    main()