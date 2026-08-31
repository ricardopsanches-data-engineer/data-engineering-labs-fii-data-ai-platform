from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ML_FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_features"
    / "fii_features.parquet"
)

TRAINING_DATASET_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
)

TRAINING_DATASET_PATH = (
    TRAINING_DATASET_DIR
    / "fii_training_dataset.parquet"
)

DEFAULT_TARGET_HORIZON = 5

TRAINING_DATASET_VERSION = "v1"


def validate_target_horizon(
    target_horizon: int,
) -> int:
    """
    Valida o horizonte futuro utilizado
    na construção do target.
    """

    if target_horizon <= 0:
        raise ValueError(
            "target_horizon deve ser "
            "maior que zero."
        )

    return target_horizon


def load_ml_features(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega a Gold ML já validada.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Gold ML não encontrada: {path}"
        )

    print(
        f"Carregando Gold ML: {path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        "feature_ready",
        "feature_version",
        "feature_windows",
        "observations_count",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"na Gold ML: {missing_columns}"
        )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
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

    return dataframe


def validate_source_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """
    Data Quality da Gold ML antes
    da criação do target.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Fonte Gold ML"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers únicos: "
        f"{dataframe['ticker'].nunique():,}"
    )

    duplicate_mask = dataframe.duplicated(
        subset=[
            "feature_date",
            "ticker",
        ],
        keep=False,
    )

    duplicate_count = int(
        duplicate_mask.sum()
    )

    print(
        f"Duplicidades "
        f"(feature_date + ticker): "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Gold ML contém duplicidade "
            "feature_date + ticker."
        )

    identity_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
    ]

    null_counts = (
        dataframe[
            identity_columns
        ]
        .isna()
        .sum()
    )

    print(
        "\nCampos obrigatórios nulos:"
    )

    for column, count in null_counts.items():
        print(
            f"  {column}: "
            f"{count:,}"
        )

    if (
        null_counts
        > 0
    ).any():
        raise ValueError(
            "Gold ML contém campos "
            "obrigatórios nulos."
        )

    print(
        "\nData Quality da fonte aprovada."
    )


def build_future_target(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Cria o target futuro por ticker.

    Exemplo para horizonte 5:

        target_return_next_5d =
            close(t+5) / close(t) - 1

    Também registra:

        target_price_next_5d
        target_date_next_5d

    O target utiliza somente dados futuros
    para a coluna de label.

    Nenhuma dessas informações deve ser
    utilizada como feature.
    """

    result = dataframe.copy()

    result = result.sort_values(
        by=[
            "ticker",
            "feature_date",
        ]
    ).reset_index(
        drop=True
    )

    grouped = result.groupby(
        "ticker",
        group_keys=False,
    )

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"target_return_next_"
        f"{target_horizon}d_pct"
    )

    result[
        target_price_column
    ] = grouped[
        "close_price"
    ].shift(
        -target_horizon
    )

    result[
        target_date_column
    ] = grouped[
        "feature_date"
    ].shift(
        -target_horizon
    )

    result[
        target_return_column
    ] = (
        result[
            target_price_column
        ]
        / result[
            "close_price"
        ]
        - 1
    )

    result[
        target_return_pct_column
    ] = (
        result[
            target_return_column
        ]
        * 100
    )

    return result


def select_training_rows(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Mantém somente linhas:

    - feature_ready = True
    - com target futuro disponível

    Isso forma o dataset supervisionado.
    """

    target_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    training = dataframe[
        (
            dataframe[
                "feature_ready"
            ]
        )
        &
        (
            dataframe[
                target_column
            ].notna()
        )
        &
        (
            dataframe[
                target_date_column
            ].notna()
        )
    ].copy()

    return training


def validate_no_target_leakage(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Valida a separação temporal básica
    entre feature_date e target_date.

    O target obrigatoriamente deve estar
    no futuro em relação à feature_date.
    """

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    invalid_rows = dataframe[
        dataframe[
            target_date_column
        ]
        <= dataframe[
            "feature_date"
        ]
    ]

    invalid_count = len(
        invalid_rows
    )

    print(
        f"Targets com data <= feature_date: "
        f"{invalid_count:,}"
    )

    if invalid_count > 0:
        raise ValueError(
            "Possível leakage temporal: "
            "target_date não está no futuro."
        )


def validate_training_dataset(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Data Quality do dataset supervisionado.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Training Dataset"
    )
    print(
        "======================================"
    )

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"target_return_next_"
        f"{target_horizon}d_pct"
    )

    print(
        f"Linhas supervisionadas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"Período das features: "
        f"{dataframe['feature_date'].min().date()} "
        f"-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        f"Período dos targets: "
        f"{dataframe[target_date_column].min().date()} "
        f"-> "
        f"{dataframe[target_date_column].max().date()}"
    )

    duplicate_mask = dataframe.duplicated(
        subset=[
            "feature_date",
            "ticker",
        ],
        keep=False,
    )

    duplicate_count = int(
        duplicate_mask.sum()
    )

    print(
        f"\nDuplicidades "
        f"(feature_date + ticker): "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Training dataset contém "
            "duplicidades."
        )

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        target_price_column,
        target_date_column,
        target_return_column,
        target_return_pct_column,
    ]

    null_counts = (
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
    )

    print(
        "\nCampos obrigatórios nulos:"
    )

    for column, count in null_counts.items():
        print(
            f"  {column}: "
            f"{count:,}"
        )

    if (
        null_counts
        > 0
    ).any():
        raise ValueError(
            "Training dataset contém "
            "campos obrigatórios nulos."
        )

    invalid_target_prices = (
        dataframe[
            target_price_column
        ]
        <= 0
    ).sum()

    print(
        f"\nTarget prices inválidos: "
        f"{invalid_target_prices:,}"
    )

    if invalid_target_prices > 0:
        raise ValueError(
            "Training dataset possui "
            "target_price inválido."
        )

    validate_no_target_leakage(
        dataframe=dataframe,
        target_horizon=target_horizon,
    )

    print(
        "\nData Quality do "
        "training dataset aprovada."
    )


def add_training_metadata(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Adiciona metadados técnicos
    do dataset supervisionado.
    """

    result = dataframe.copy()

    result[
        "training_dataset_created_at"
    ] = datetime.now(
        timezone.utc
    )

    result[
        "training_dataset_version"
    ] = TRAINING_DATASET_VERSION

    result[
        "target_horizon"
    ] = target_horizon

    result[
        "target_name"
    ] = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    return result


def save_training_dataset(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste o dataset supervisionado.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )


def print_summary(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Resumo do dataset de treinamento.
    """

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"target_return_next_"
        f"{target_horizon}d_pct"
    )

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo FII Training Dataset"
    )
    print(
        "======================================"
    )

    print(
        f"Dataset version: "
        f"{TRAINING_DATASET_VERSION}"
    )

    print(
        f"Target horizon: "
        f"{target_horizon} pregões"
    )

    print(
        f"Target: "
        f"{target_return_column}"
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
        f"Feature date: "
        f"{dataframe['feature_date'].min().date()} "
        f"-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        f"Target date: "
        f"{dataframe[target_date_column].min().date()} "
        f"-> "
        f"{dataframe[target_date_column].max().date()}"
    )

    print(
        f"Target médio: "
        f"{dataframe[target_return_pct_column].mean():.4f}%"
    )

    print(
        f"Target mediano: "
        f"{dataframe[target_return_pct_column].median():.4f}%"
    )

    positive_targets = (
        dataframe[
            target_return_column
        ]
        > 0
    ).sum()

    negative_or_zero_targets = (
        dataframe[
            target_return_column
        ]
        <= 0
    ).sum()

    print(
        f"Targets positivos: "
        f"{positive_targets:,}"
    )

    print(
        f"Targets <= 0: "
        f"{negative_or_zero_targets:,}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói dataset supervisionado "
            "para ML de FIIs."
        )
    )

    parser.add_argument(
        "--target-horizon",
        type=int,
        default=DEFAULT_TARGET_HORIZON,
        help=(
            "Horizonte futuro em pregões "
            "para o target. "
            "Default: 5."
        ),
    )

    args = parser.parse_args()

    target_horizon = (
        validate_target_horizon(
            args.target_horizon
        )
    )

    print(
        "Construindo FII "
        "Training Dataset..."
    )

    print(
        f"Target horizon: "
        f"{target_horizon} pregões"
    )

    features = load_ml_features(
        ML_FEATURES_PATH
    )

    print(
        f"\nGold ML carregada: "
        f"{len(features):,} linhas"
    )

    validate_source_dataset(
        features
    )

    dataset = build_future_target(
        dataframe=features,
        target_horizon=target_horizon,
    )

    training = select_training_rows(
        dataframe=dataset,
        target_horizon=target_horizon,
    )

    validate_training_dataset(
        dataframe=training,
        target_horizon=target_horizon,
    )

    training = add_training_metadata(
        dataframe=training,
        target_horizon=target_horizon,
    )

    save_training_dataset(
        dataframe=training,
        destination=TRAINING_DATASET_PATH,
    )

    print_summary(
        dataframe=training,
        target_horizon=target_horizon,
    )

    print(
        "\nArquivo:"
    )

    print(
        TRAINING_DATASET_PATH
    )

    print(
        "\nFII Training Dataset "
        "criado com sucesso."
    )


if __name__ == "__main__":
    main()