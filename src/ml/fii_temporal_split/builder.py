from __future__ import annotations

import argparse
from datetime import datetime, timezone
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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
)

TRAIN_PATH = (
    OUTPUT_DIR
    / "train.parquet"
)

VALIDATION_PATH = (
    OUTPUT_DIR
    / "validation.parquet"
)

TEST_PATH = (
    OUTPUT_DIR
    / "test.parquet"
)

DEFAULT_VALIDATION_DAYS = 10

DEFAULT_TEST_DAYS = 10

SPLIT_VERSION = "v1"


def load_training_dataset(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega o dataset supervisionado.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Training dataset não encontrado: {path}"
        )

    print(
        f"Carregando training dataset: {path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "target_horizon",
        "target_name",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"no training dataset: {missing_columns}"
        )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
        ]
    )

    return dataframe


def discover_target_horizon(
    dataframe: pd.DataFrame,
) -> int:
    """
    Descobre o horizonte do target
    a partir do dataset.
    """

    values = (
        dataframe[
            "target_horizon"
        ]
        .dropna()
        .unique()
    )

    if len(values) == 0:
        raise ValueError(
            "target_horizon não encontrado."
        )

    if len(values) > 1:
        raise ValueError(
            "Mais de um target_horizon "
            f"encontrado: {values.tolist()}"
        )

    horizon = int(
        values[0]
    )

    if horizon <= 0:
        raise ValueError(
            "target_horizon inválido."
        )

    return horizon


def get_target_date_column(
    target_horizon: int,
) -> str:
    """
    Retorna o nome da coluna target_date.
    """

    return (
        f"target_date_next_"
        f"{target_horizon}d"
    )


def validate_base_dataset(
    dataframe: pd.DataFrame,
    target_date_column: str,
) -> None:
    """
    Data Quality antes do split.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Fonte do Split"
    )
    print(
        "======================================"
    )

    if (
        target_date_column
        not in dataframe.columns
    ):
        raise ValueError(
            f"Coluna {target_date_column} "
            "não encontrada."
        )

    dataframe[
        target_date_column
    ] = pd.to_datetime(
        dataframe[
            target_date_column
        ]
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

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ],
            keep=False,
        ).sum()
    )

    print(
        f"Duplicidades "
        f"(feature_date + ticker): "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Dataset contém duplicidades."
        )


def get_sorted_feature_dates(
    dataframe: pd.DataFrame,
) -> list[pd.Timestamp]:
    """
    Lista as datas de feature disponíveis.
    """

    dates = sorted(
        dataframe[
            "feature_date"
        ]
        .dropna()
        .unique()
    )

    dates = [
        pd.Timestamp(
            value
        )
        for value in dates
    ]

    if not dates:
        raise ValueError(
            "Nenhuma feature_date encontrada."
        )

    return dates


def resolve_split_boundaries(
    dataframe: pd.DataFrame,
    validation_days: int,
    test_days: int,
) -> tuple[
    pd.Timestamp,
    pd.Timestamp,
]:
    """
    Define as fronteiras usando número
    de pregões disponíveis no dataset.

    Retorna:

        validation_start
        test_start
    """

    if validation_days <= 0:
        raise ValueError(
            "validation_days deve ser "
            "maior que zero."
        )

    if test_days <= 0:
        raise ValueError(
            "test_days deve ser "
            "maior que zero."
        )

    feature_dates = (
        get_sorted_feature_dates(
            dataframe
        )
    )

    minimum_required_dates = (
        validation_days
        + test_days
        + 1
    )

    if (
        len(feature_dates)
        < minimum_required_dates
    ):
        raise ValueError(
            "Datas insuficientes para "
            "train/validation/test. "
            f"Disponíveis: {len(feature_dates)}, "
            f"mínimo necessário: "
            f"{minimum_required_dates}."
        )

    test_start_index = (
        len(feature_dates)
        - test_days
    )

    validation_start_index = (
        test_start_index
        - validation_days
    )

    validation_start = (
        feature_dates[
            validation_start_index
        ]
    )

    test_start = (
        feature_dates[
            test_start_index
        ]
    )

    return (
        validation_start,
        test_start,
    )


def build_temporal_split(
    dataframe: pd.DataFrame,
    target_date_column: str,
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Constrói split temporal com purge.

    TRAIN:
        feature_date < validation_start
        E target_date < validation_start

    VALIDATION:
        feature_date >= validation_start
        feature_date < test_start
        E target_date < test_start

    TEST:
        feature_date >= test_start

    O purge remove linhas cujo target
    atravessaria a fronteira seguinte.
    """

    train = dataframe[
        (
            dataframe[
                "feature_date"
            ]
            < validation_start
        )
        &
        (
            dataframe[
                target_date_column
            ]
            < validation_start
        )
    ].copy()

    validation = dataframe[
        (
            dataframe[
                "feature_date"
            ]
            >= validation_start
        )
        &
        (
            dataframe[
                "feature_date"
            ]
            < test_start
        )
        &
        (
            dataframe[
                target_date_column
            ]
            < test_start
        )
    ].copy()

    test = dataframe[
        dataframe[
            "feature_date"
        ]
        >= test_start
    ].copy()

    return (
        train,
        validation,
        test,
    )


def validate_split_not_empty(
    name: str,
    dataframe: pd.DataFrame,
) -> None:
    """
    Nenhum conjunto pode ficar vazio.
    """

    if dataframe.empty:
        raise ValueError(
            f"Split {name} ficou vazio."
        )


def validate_split_overlap(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    """
    Confirma que a mesma observação
    não aparece em múltiplos conjuntos.
    """

    def build_keys(
        dataframe: pd.DataFrame,
    ) -> set[tuple[object, object]]:
        return set(
            zip(
                dataframe[
                    "feature_date"
                ],
                dataframe[
                    "ticker"
                ],
            )
        )

    train_keys = build_keys(
        train
    )

    validation_keys = build_keys(
        validation
    )

    test_keys = build_keys(
        test
    )

    train_validation_overlap = (
        train_keys
        & validation_keys
    )

    train_test_overlap = (
        train_keys
        & test_keys
    )

    validation_test_overlap = (
        validation_keys
        & test_keys
    )

    print(
        "\nSobreposição entre splits:"
    )

    print(
        "  train x validation: "
        f"{len(train_validation_overlap):,}"
    )

    print(
        "  train x test: "
        f"{len(train_test_overlap):,}"
    )

    print(
        "  validation x test: "
        f"{len(validation_test_overlap):,}"
    )

    if (
        train_validation_overlap
        or train_test_overlap
        or validation_test_overlap
    ):
        raise ValueError(
            "Existe sobreposição entre splits."
        )


def validate_purged_boundaries(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    target_date_column: str,
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
) -> None:
    """
    Valida as fronteiras temporais.
    """

    invalid_train = train[
        train[
            target_date_column
        ]
        >= validation_start
    ]

    invalid_validation = validation[
        validation[
            target_date_column
        ]
        >= test_start
    ]

    invalid_test = test[
        test[
            "feature_date"
        ]
        < test_start
    ]

    print(
        "\nValidação das fronteiras:"
    )

    print(
        "  train targets invadindo validation: "
        f"{len(invalid_train):,}"
    )

    print(
        "  validation targets invadindo test: "
        f"{len(invalid_validation):,}"
    )

    print(
        "  test features antes do test_start: "
        f"{len(invalid_test):,}"
    )

    if not invalid_train.empty:
        raise ValueError(
            "Train possui targets dentro "
            "da janela de validation."
        )

    if not invalid_validation.empty:
        raise ValueError(
            "Validation possui targets "
            "dentro da janela de test."
        )

    if not invalid_test.empty:
        raise ValueError(
            "Test possui features antes "
            "da fronteira correta."
        )


def add_split_metadata(
    dataframe: pd.DataFrame,
    split_name: str,
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
) -> pd.DataFrame:
    """
    Adiciona metadados do split.
    """

    result = dataframe.copy()

    result[
        "split_name"
    ] = split_name

    result[
        "split_version"
    ] = SPLIT_VERSION

    result[
        "validation_start"
    ] = validation_start

    result[
        "test_start"
    ] = test_start

    result[
        "split_created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


def print_split_summary(
    name: str,
    dataframe: pd.DataFrame,
    target_date_column: str,
) -> None:
    """
    Resumo de um split.
    """

    print(
        f"\n{name.upper()}"
    )

    print(
        "-" * 38
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


def save_split(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste um split em Parquet.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói split temporal "
            "purgado para ML de FIIs."
        )
    )

    parser.add_argument(
        "--validation-days",
        type=int,
        default=DEFAULT_VALIDATION_DAYS,
        help=(
            "Quantidade de pregões "
            "reservados para validação. "
            "Default: 10."
        ),
    )

    parser.add_argument(
        "--test-days",
        type=int,
        default=DEFAULT_TEST_DAYS,
        help=(
            "Quantidade de pregões "
            "reservados para teste. "
            "Default: 10."
        ),
    )

    args = parser.parse_args()

    print(
        "Construindo FII "
        "Temporal Split..."
    )

    dataframe = load_training_dataset(
        TRAINING_DATASET_PATH
    )

    print(
        f"\nTraining dataset carregado: "
        f"{len(dataframe):,} linhas"
    )

    target_horizon = (
        discover_target_horizon(
            dataframe
        )
    )

    target_date_column = (
        get_target_date_column(
            target_horizon
        )
    )

    validate_base_dataset(
        dataframe=dataframe,
        target_date_column=target_date_column,
    )

    (
        validation_start,
        test_start,
    ) = resolve_split_boundaries(
        dataframe=dataframe,
        validation_days=args.validation_days,
        test_days=args.test_days,
    )

    print(
        "\n======================================"
    )
    print(
        "Fronteiras temporais"
    )
    print(
        "======================================"
    )

    print(
        f"Target horizon: "
        f"{target_horizon} pregões"
    )

    print(
        f"Validation start: "
        f"{validation_start.date()}"
    )

    print(
        f"Test start: "
        f"{test_start.date()}"
    )

    (
        train,
        validation,
        test,
    ) = build_temporal_split(
        dataframe=dataframe,
        target_date_column=target_date_column,
        validation_start=validation_start,
        test_start=test_start,
    )

    validate_split_not_empty(
        "train",
        train,
    )

    validate_split_not_empty(
        "validation",
        validation,
    )

    validate_split_not_empty(
        "test",
        test,
    )

    validate_split_overlap(
        train=train,
        validation=validation,
        test=test,
    )

    validate_purged_boundaries(
        train=train,
        validation=validation,
        test=test,
        target_date_column=target_date_column,
        validation_start=validation_start,
        test_start=test_start,
    )

    train = add_split_metadata(
        dataframe=train,
        split_name="train",
        validation_start=validation_start,
        test_start=test_start,
    )

    validation = add_split_metadata(
        dataframe=validation,
        split_name="validation",
        validation_start=validation_start,
        test_start=test_start,
    )

    test = add_split_metadata(
        dataframe=test,
        split_name="test",
        validation_start=validation_start,
        test_start=test_start,
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo Temporal Split"
    )
    print(
        "======================================"
    )

    print_split_summary(
        name="train",
        dataframe=train,
        target_date_column=target_date_column,
    )

    print_split_summary(
        name="validation",
        dataframe=validation,
        target_date_column=target_date_column,
    )

    print_split_summary(
        name="test",
        dataframe=test,
        target_date_column=target_date_column,
    )

    save_split(
        dataframe=train,
        destination=TRAIN_PATH,
    )

    save_split(
        dataframe=validation,
        destination=VALIDATION_PATH,
    )

    save_split(
        dataframe=test,
        destination=TEST_PATH,
    )

    print(
        "\nArquivos:"
    )

    print(
        f"Train: {TRAIN_PATH}"
    )

    print(
        f"Validation: {VALIDATION_PATH}"
    )

    print(
        f"Test: {TEST_PATH}"
    )

    print(
        "\nFII Temporal Split "
        "criado com sucesso."
    )


if __name__ == "__main__":
    main()