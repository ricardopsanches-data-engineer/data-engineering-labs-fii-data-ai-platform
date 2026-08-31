from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

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


PROJECT_ROOT = Path(__file__).resolve().parents[3]

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

BASELINE_VERSION = "v2"


@dataclass
class ModelResult:
    name: str
    mae: float
    rmse: float
    r2: float
    directional_accuracy: float


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


def build_excluded_columns(
    dataframe: pd.DataFrame,
    target_column: str,
) -> set[str]:
    """
    Colunas que jamais devem entrar no X.
    """

    excluded = {
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "feature_ready",
        "feature_version",
        "feature_windows",
        "features_created_at",
        "training_dataset_created_at",
        "training_dataset_version",
        "target_horizon",
        "target_name",
        "split_name",
        "split_version",
        "validation_start",
        "test_start",
        "split_created_at",
        target_column,
    }

    for column in dataframe.columns:
        if column.startswith(
            "target_"
        ):
            excluded.add(
                column
            )

    return excluded


def discover_feature_columns(
    dataframe: pd.DataFrame,
    target_column: str,
) -> list[str]:
    """
    Descobre somente features numéricas
    elegíveis para o modelo.
    """

    excluded_columns = (
        build_excluded_columns(
            dataframe=dataframe,
            target_column=target_column,
        )
    )

    numeric_columns = (
        dataframe.select_dtypes(
            include=[
                "number",
                "bool",
            ]
        )
        .columns
        .tolist()
    )

    feature_columns = [
        column
        for column in numeric_columns
        if column not in excluded_columns
    ]

    if not feature_columns:
        raise ValueError(
            "Nenhuma feature numérica encontrada."
        )

    return feature_columns


def validate_no_future_columns(
    feature_columns: list[str],
) -> None:
    """
    Proteção adicional contra leakage.
    """

    suspicious_columns = [
        column
        for column in feature_columns
        if (
            column.startswith(
                "target_"
            )
            or "next_" in column
        )
    ]

    if suspicious_columns:
        raise ValueError(
            "Possível leakage detectado nas "
            f"features: {suspicious_columns}"
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

    models: dict[str, object] = {}

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


def calculate_directional_accuracy(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> float:
    """
    Mede se o modelo acertou o sinal
    do retorno futuro.

    positivo vs não positivo.
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
) -> tuple[
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

    return (
        float(mae),
        float(rmse),
        float(r2),
        float(directional_accuracy),
    )


def evaluate_models(
    models: dict[str, object],
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_validation: pd.DataFrame,
    y_validation: pd.Series,
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
        ) = calculate_metrics(
            y_true=y_validation,
            y_pred=predictions,
        )

        results.append(
            ModelResult(
                name=name,
                mae=mae,
                rmse=rmse,
                r2=r2,
                directional_accuracy=directional_accuracy,
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
            f"  Directional Accuracy: "
            f"{directional_accuracy:.4f} "
            f"({directional_accuracy * 100:.2f}%)"
        )

    return results


def results_to_dataframe(
    results: list[ModelResult],
) -> pd.DataFrame:
    """
    Resultado tabular.
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
            }
            for result in results
        ]
    )


def print_feature_summary(
    feature_columns: list[str],
) -> None:
    """
    Mostra as features efetivamente
    usadas.
    """

    print(
        "\n======================================"
    )
    print(
        "Features do baseline"
    )
    print(
        "======================================"
    )

    print(
        f"Quantidade: "
        f"{len(feature_columns):,}"
    )

    for column in feature_columns:
        print(
            f"  {column}"
        )


def print_target_summary(
    y_train: pd.Series,
    y_validation: pd.Series,
) -> None:
    """
    Ajuda a interpretar as métricas.
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


def print_metric_rankings(
    results: pd.DataFrame,
) -> None:
    """
    Exibe rankings separados.

    Não força um único vencedor quando
    métricas apontam para modelos diferentes.
    """

    print(
        "\n======================================"
    )
    print(
        "Ranking por MAE"
    )
    print(
        "======================================"
    )

    mae_ranking = results.sort_values(
        by="mae",
        ascending=True,
    )

    for position, (_, row) in enumerate(
        mae_ranking.iterrows(),
        start=1,
    ):
        print(
            f"{position}. "
            f"{row['model']} | "
            f"{row['mae'] * 100:.4f}%"
        )

    print(
        "\n======================================"
    )
    print(
        "Ranking por RMSE"
    )
    print(
        "======================================"
    )

    rmse_ranking = results.sort_values(
        by="rmse",
        ascending=True,
    )

    for position, (_, row) in enumerate(
        rmse_ranking.iterrows(),
        start=1,
    ):
        print(
            f"{position}. "
            f"{row['model']} | "
            f"{row['rmse'] * 100:.4f}%"
        )

    print(
        "\n======================================"
    )
    print(
        "Ranking por R²"
    )
    print(
        "======================================"
    )

    r2_ranking = results.sort_values(
        by="r2",
        ascending=False,
    )

    for position, (_, row) in enumerate(
        r2_ranking.iterrows(),
        start=1,
    ):
        print(
            f"{position}. "
            f"{row['model']} | "
            f"{row['r2']:.6f}"
        )

    print(
        "\n======================================"
    )
    print(
        "Ranking por Directional Accuracy"
    )
    print(
        "======================================"
    )

    direction_ranking = results.sort_values(
        by="directional_accuracy",
        ascending=False,
    )

    for position, (_, row) in enumerate(
        direction_ranking.iterrows(),
        start=1,
    ):
        print(
            f"{position}. "
            f"{row['model']} | "
            f"{row['directional_accuracy'] * 100:.2f}%"
        )


def print_best_by_metric(
    results: pd.DataFrame,
) -> None:
    """
    Resume o melhor modelo por métrica.
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
        f"Directional Accuracy: "
        f"{best_direction['model']} "
        f"({best_direction['directional_accuracy'] * 100:.2f}%)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Executa modelos baseline "
            "para previsão de retorno "
            "futuro de FIIs."
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

    # Test é carregado apenas para validar
    # o contrato. Não é usado nas métricas.
    test = load_split(
        TEST_PATH,
        "test",
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

    feature_columns = (
        discover_feature_columns(
            dataframe=train,
            target_column=target_column,
        )
    )

    validate_no_future_columns(
        feature_columns
    )

    print_feature_summary(
        feature_columns
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
        "Os modelos foram comparados apenas "
        "no VALIDATION."
    )

    print(
        "O conjunto TEST continua reservado "
        "para avaliação final futura."
    )

    print(
        "Não existe um único vencedor "
        "automático: métricas diferentes "
        "podem favorecer modelos diferentes."
    )


if __name__ == "__main__":
    main()