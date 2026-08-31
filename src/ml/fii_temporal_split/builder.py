from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
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


SPLIT_VERSION = "v2"


EXPECTED_TRAINING_DATASET_VERSION = "v3"

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)

EXPECTED_TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_FEATURE_VERSION = "v6"

EXPECTED_ELIGIBILITY_VERSION = "v2"

EXPECTED_PRICE_HISTORY_VERSION = "v2"

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)


def load_training_dataset(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega Training Dataset v3.

    O dataset contém tanto samples
    elegíveis quanto inelegíveis para
    preservar auditoria.

    O split v2 filtrará explicitamente
    somente ml_eligible=True.
    """

    if not path.exists():
        raise FileNotFoundError(
            "Training dataset não encontrado: "
            f"{path}"
        )

    print(
        "Carregando training dataset: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    required_columns = [
        "feature_date",
        "target_date",

        "ticker",
        "cnpj",
        "codigo_cvm",

        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",
        "target_name",

        "feature_ready",

        "ml_eligible",
        "ml_ineligibility_reason",

        "training_dataset_version",

        "source_feature_version",
        "source_ml_eligibility_version",
        "source_price_history_version",

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
            "Colunas obrigatórias ausentes "
            "no Training Dataset: "
            f"{missing_columns}"
        )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
        ]
    )

    dataframe[
        "target_date"
    ] = pd.to_datetime(
        dataframe[
            "target_date"
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


def validate_training_dataset_contract(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida o contrato semântico completo
    recebido pelo Temporal Split v2.
    """

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    required_identity_columns = [
        "feature_date",
        "target_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
    ]

    identity_null_count = int(
        dataframe[
            required_identity_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    versions = sorted(
        dataframe[
            "training_dataset_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    horizons = sorted(
        dataframe[
            "target_horizon"
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    horizon_semantics = sorted(
        dataframe[
            "target_horizon_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    target_return_semantics = sorted(
        dataframe[
            "target_return_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    feature_versions = sorted(
        dataframe[
            "source_feature_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    eligibility_versions = sorted(
        dataframe[
            "source_ml_eligibility_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_history_versions = sorted(
        dataframe[
            "source_price_history_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    price_semantics = sorted(
        dataframe[
            "price_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return_semantics = sorted(
        dataframe[
            "return_semantics"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    feature_ready_count = int(
        dataframe[
            "feature_ready"
        ]
        .fillna(
            False
        )
        .sum()
    )

    eligible_count = int(
        dataframe[
            "ml_eligible"
        ]
        .fillna(
            False
        )
        .sum()
    )

    ineligible_count = (
        len(dataframe)
        - eligible_count
    )

    invalid_target_dates = int(
        (
            dataframe[
                "target_date"
            ]
            <= dataframe[
                "feature_date"
            ]
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Training Dataset"
    )
    print(
        "======================================"
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
        f"Feature ready: "
        f"{feature_ready_count:,}"
    )

    print(
        f"ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"ML ineligible: "
        f"{ineligible_count:,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Nulos de identidade: "
        f"{identity_null_count:,}"
    )

    print(
        "Target dates <= feature_date: "
        f"{invalid_target_dates:,}"
    )

    print(
        "Training Dataset versions: "
        f"{versions}"
    )

    print(
        f"Target horizons: "
        f"{horizons}"
    )

    print(
        "Target horizon semantics: "
        f"{horizon_semantics}"
    )

    print(
        "Target return semantics: "
        f"{target_return_semantics}"
    )

    print(
        "Source feature versions: "
        f"{feature_versions}"
    )

    print(
        "Source eligibility versions: "
        f"{eligibility_versions}"
    )

    print(
        "Source Price History versions: "
        f"{price_history_versions}"
    )

    print(
        "Price semantics: "
        f"{price_semantics}"
    )

    print(
        "Return semantics: "
        f"{return_semantics}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Training Dataset possui "
            "duplicidades."
        )

    if identity_null_count > 0:
        raise ValueError(
            "Training Dataset possui "
            "campos de identidade nulos."
        )

    if invalid_target_dates > 0:
        raise ValueError(
            "Training Dataset possui "
            "target_date inválida."
        )

    if versions != [
        EXPECTED_TRAINING_DATASET_VERSION
    ]:
        raise ValueError(
            "Temporal Split v2 exige "
            "Training Dataset v3."
        )

    if horizons != [
        EXPECTED_TARGET_HORIZON
    ]:
        raise ValueError(
            "Temporal Split v2 exige "
            f"target_horizon="
            f"{EXPECTED_TARGET_HORIZON}. "
            f"Encontrado: {horizons}"
        )

    if horizon_semantics != [
        EXPECTED_TARGET_HORIZON_SEMANTICS
    ]:
        raise ValueError(
            "target_horizon_semantics "
            "incompatível."
        )

    if target_return_semantics != [
        EXPECTED_TARGET_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "target_return_semantics "
            "incompatível."
        )

    if feature_versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "Temporal Split v2 exige "
            "Features v6."
        )

    if eligibility_versions != [
        EXPECTED_ELIGIBILITY_VERSION
    ]:
        raise ValueError(
            "Temporal Split v2 exige "
            "ML Eligibility v2."
        )

    if price_history_versions != [
        EXPECTED_PRICE_HISTORY_VERSION
    ]:
        raise ValueError(
            "Temporal Split v2 exige "
            "Price History v2."
        )

    if price_semantics != [
        EXPECTED_PRICE_SEMANTICS
    ]:
        raise ValueError(
            "price_semantics incompatível."
        )

    if return_semantics != [
        EXPECTED_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "return_semantics incompatível."
        )

    print(
        "\nData Quality aprovada."
    )


def filter_ml_eligible(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Somente samples governadas como
    ml_eligible=True podem entrar nos
    splits usados pelo modelo.

    As samples inelegíveis permanecem no
    Training Dataset v3 original e não
    são fisicamente destruídas.
    """

    eligible_mask = (
        dataframe[
            "ml_eligible"
        ]
        .astype(
            "boolean"
        )
        .fillna(
            False
        )
    )

    eligible = dataframe[
        eligible_mask
    ].copy()

    ineligible = dataframe[
        ~eligible_mask
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Filtro - ML Eligibility"
    )
    print(
        "======================================"
    )

    print(
        f"Samples supervisionáveis: "
        f"{len(dataframe):,}"
    )

    print(
        f"Samples elegíveis: "
        f"{len(eligible):,}"
    )

    print(
        f"Samples inelegíveis excluídas "
        f"dos splits: "
        f"{len(ineligible):,}"
    )

    if eligible.empty:
        raise ValueError(
            "Nenhuma sample ML eligible "
            "disponível."
        )

    ineligible_inside_eligible = int(
        (
            ~eligible[
                "ml_eligible"
            ]
        ).sum()
    )

    if ineligible_inside_eligible > 0:
        raise ValueError(
            "Filtro de eligibility falhou."
        )

    return eligible


def get_sorted_feature_dates(
    dataframe: pd.DataFrame,
) -> list[pd.Timestamp]:
    """
    Lista as feature_dates presentes no
    universo ML elegível.
    """

    dates = (
        dataframe[
            "feature_date"
        ]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
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
    Resolve as fronteiras do split sobre
    as feature_dates disponíveis no universo
    ML elegível.

    validation_days e test_days representam
    número de datas globais de feature
    reservadas para cada bloco.
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

    if len(
        feature_dates
    ) < minimum_required_dates:
        raise ValueError(
            "Datas insuficientes para "
            "train/validation/test. "
            f"Disponíveis: "
            f"{len(feature_dates)}, "
            "mínimo necessário: "
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
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Constrói split temporal purgado.

    TRAIN
    -----
    feature_date < validation_start

    E

    target_date < validation_start


    VALIDATION
    ----------
    feature_date >= validation_start

    E

    feature_date < test_start

    E

    target_date < test_start


    TEST
    ----
    feature_date >= test_start


    Os filtros de target_date removem samples
    que carregariam informação da janela
    temporal seguinte.
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
                "target_date"
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
                "target_date"
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


def calculate_purge_diagnostics(
    dataframe: pd.DataFrame,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
) -> dict[str, int]:
    """
    Quantifica quais samples ML elegíveis
    foram deliberadamente removidas pelo
    purge nas fronteiras temporais.
    """

    train_region = dataframe[
        dataframe[
            "feature_date"
        ]
        < validation_start
    ]

    validation_region = dataframe[
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
    ]

    test_region = dataframe[
        dataframe[
            "feature_date"
        ]
        >= test_start
    ]

    train_purged = (
        len(train_region)
        - len(train)
    )

    validation_purged = (
        len(validation_region)
        - len(validation)
    )

    test_purged = (
        len(test_region)
        - len(test)
    )

    assigned_count = (
        len(train)
        + len(validation)
        + len(test)
    )

    total_purged = (
        len(dataframe)
        - assigned_count
    )

    diagnostics = {
        "eligible_total": (
            len(dataframe)
        ),
        "train_region_before_purge": (
            len(train_region)
        ),
        "validation_region_before_purge": (
            len(validation_region)
        ),
        "test_region_before_purge": (
            len(test_region)
        ),
        "train_purged": (
            train_purged
        ),
        "validation_purged": (
            validation_purged
        ),
        "test_purged": (
            test_purged
        ),
        "total_purged": (
            total_purged
        ),
        "assigned_total": (
            assigned_count
        ),
    }

    return diagnostics


def validate_split_not_empty(
    name: str,
    dataframe: pd.DataFrame,
) -> None:
    """
    Nenhum split pode ficar vazio.
    """

    if dataframe.empty:
        raise ValueError(
            f"Split {name} ficou vazio."
        )


def validate_all_rows_eligible(
    name: str,
    dataframe: pd.DataFrame,
) -> None:
    """
    Nenhuma sample inelegível pode entrar
    em qualquer split.
    """

    if "ml_eligible" not in dataframe.columns:
        raise ValueError(
            f"{name} não possui ml_eligible."
        )

    ineligible_count = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
        ).sum()
    )

    print(
        f"  {name}: "
        f"{ineligible_count:,} inelegíveis"
    )

    if ineligible_count > 0:
        raise ValueError(
            f"Split {name} contém "
            "samples ML inelegíveis."
        )


def validate_split_overlap(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    """
    Confirma que a mesma sample não aparece
    em múltiplos splits.
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
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
) -> None:
    """
    Valida ausência de leakage através das
    fronteiras temporais.
    """

    invalid_train_feature = train[
        train[
            "feature_date"
        ]
        >= validation_start
    ]

    invalid_train_target = train[
        train[
            "target_date"
        ]
        >= validation_start
    ]

    invalid_validation_feature_before = (
        validation[
            validation[
                "feature_date"
            ]
            < validation_start
        ]
    )

    invalid_validation_feature_after = (
        validation[
            validation[
                "feature_date"
            ]
            >= test_start
        ]
    )

    invalid_validation_target = (
        validation[
            validation[
                "target_date"
            ]
            >= test_start
        ]
    )

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
        "  train features invadindo validation: "
        f"{len(invalid_train_feature):,}"
    )

    print(
        "  train targets invadindo validation: "
        f"{len(invalid_train_target):,}"
    )

    print(
        "  validation features antes do início: "
        f"{len(invalid_validation_feature_before):,}"
    )

    print(
        "  validation features invadindo test: "
        f"{len(invalid_validation_feature_after):,}"
    )

    print(
        "  validation targets invadindo test: "
        f"{len(invalid_validation_target):,}"
    )

    print(
        "  test features antes do test_start: "
        f"{len(invalid_test):,}"
    )

    if not invalid_train_feature.empty:
        raise ValueError(
            "Train possui feature_date dentro "
            "da janela de validation."
        )

    if not invalid_train_target.empty:
        raise ValueError(
            "Train possui target dentro "
            "da janela de validation."
        )

    if not invalid_validation_feature_before.empty:
        raise ValueError(
            "Validation possui feature_date "
            "anterior à fronteira."
        )

    if not invalid_validation_feature_after.empty:
        raise ValueError(
            "Validation possui feature_date "
            "dentro da janela de test."
        )

    if not invalid_validation_target.empty:
        raise ValueError(
            "Validation possui target "
            "dentro da janela de test."
        )

    if not invalid_test.empty:
        raise ValueError(
            "Test possui feature_date antes "
            "da fronteira correta."
        )


def validate_chronological_order(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    """
    Confirma a ordem cronológica geral dos
    três conjuntos.
    """

    train_max_feature = (
        train[
            "feature_date"
        ].max()
    )

    validation_min_feature = (
        validation[
            "feature_date"
        ].min()
    )

    validation_max_feature = (
        validation[
            "feature_date"
        ].max()
    )

    test_min_feature = (
        test[
            "feature_date"
        ].min()
    )

    train_max_target = (
        train[
            "target_date"
        ].max()
    )

    validation_max_target = (
        validation[
            "target_date"
        ].max()
    )

    print(
        "\nOrdem cronológica:"
    )

    print(
        "  train max feature: "
        f"{train_max_feature.date()}"
    )

    print(
        "  train max target: "
        f"{train_max_target.date()}"
    )

    print(
        "  validation min feature: "
        f"{validation_min_feature.date()}"
    )

    print(
        "  validation max feature: "
        f"{validation_max_feature.date()}"
    )

    print(
        "  validation max target: "
        f"{validation_max_target.date()}"
    )

    print(
        "  test min feature: "
        f"{test_min_feature.date()}"
    )

    if (
        train_max_target
        >= validation_min_feature
    ):
        raise ValueError(
            "Último target de train alcança "
            "a primeira feature da validation."
        )

    if (
        validation_max_target
        >= test_min_feature
    ):
        raise ValueError(
            "Último target da validation alcança "
            "a primeira feature do test."
        )

    print(
        "\nOrdem cronológica aprovada."
    )


def add_split_metadata(
    dataframe: pd.DataFrame,
    split_name: str,
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
    validation_days: int,
    test_days: int,
) -> pd.DataFrame:
    """
    Adiciona metadata técnica e de linhagem.
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
        "validation_days"
    ] = validation_days

    result[
        "test_days"
    ] = test_days

    result[
        "split_source_training_dataset_version"
    ] = (
        EXPECTED_TRAINING_DATASET_VERSION
    )

    result[
        "split_requires_ml_eligible"
    ] = True

    result[
        "split_purge_semantics"
    ] = (
        "TARGET_DATE_BEFORE_NEXT_SPLIT"
    )

    result[
        "test_holdout_policy"
    ] = (
        "RESERVED_UNTOUCHED_FOR_MODEL_SELECTION"
    )

    result[
        "split_created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


def validate_split_metadata(
    dataframe: pd.DataFrame,
    expected_name: str,
) -> None:
    """
    Valida metadata persistida.
    """

    names = (
        dataframe[
            "split_name"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    versions = (
        dataframe[
            "split_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    source_versions = (
        dataframe[
            "split_source_training_dataset_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    eligibility_policy = (
        dataframe[
            "split_requires_ml_eligible"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    if names != [
        expected_name
    ]:
        raise ValueError(
            f"split_name inválido em "
            f"{expected_name}: {names}"
        )

    if versions != [
        SPLIT_VERSION
    ]:
        raise ValueError(
            f"split_version inválido em "
            f"{expected_name}: {versions}"
        )

    if source_versions != [
        EXPECTED_TRAINING_DATASET_VERSION
    ]:
        raise ValueError(
            "Versão de Training Dataset "
            f"incompatível em {expected_name}."
        )

    if eligibility_policy != [
        True
    ]:
        raise ValueError(
            f"{expected_name} não registra "
            "política ml_eligible=True."
        )


def print_split_summary(
    name: str,
    dataframe: pd.DataFrame,
) -> None:
    """
    Resumo de um split.
    """

    target_column = (
        dataframe[
            "target_name"
        ]
        .iloc[0]
    )

    target_mean = (
        dataframe[
            target_column
        ]
        .mean()
    )

    target_median = (
        dataframe[
            target_column
        ]
        .median()
    )

    positive_count = int(
        (
            dataframe[
                target_column
            ]
            > 0
        ).sum()
    )

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
        "-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        f"Target date: "
        f"{dataframe['target_date'].min().date()} "
        "-> "
        f"{dataframe['target_date'].max().date()}"
    )

    print(
        f"Target médio: "
        f"{target_mean * 100:.4f}%"
    )

    print(
        f"Target mediano: "
        f"{target_median * 100:.4f}%"
    )

    print(
        f"Targets positivos: "
        f"{positive_count:,}"
    )

    print(
        f"Targets <= 0: "
        f"{len(dataframe) - positive_count:,}"
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
            "Constrói FII Temporal Split v2 "
            "purgado usando somente "
            "samples ML eligible."
        )
    )

    parser.add_argument(
        "--validation-days",
        type=int,
        default=DEFAULT_VALIDATION_DAYS,
        help=(
            "Quantidade de feature dates "
            "reservadas para validation. "
            "Default: 10."
        ),
    )

    parser.add_argument(
        "--test-days",
        type=int,
        default=DEFAULT_TEST_DAYS,
        help=(
            "Quantidade de feature dates "
            "reservadas para test. "
            "Default: 10."
        ),
    )

    args = parser.parse_args()

    if args.validation_days <= 0:
        raise ValueError(
            "--validation-days deve ser "
            "maior que zero."
        )

    if args.test_days <= 0:
        raise ValueError(
            "--test-days deve ser "
            "maior que zero."
        )

    print(
        "Construindo FII Temporal Split..."
    )

    print(
        f"Version: "
        f"{SPLIT_VERSION}"
    )

    print(
        "Source: Training Dataset "
        f"{EXPECTED_TRAINING_DATASET_VERSION}"
    )

    print(
        "Eligibility policy: "
        "ml_eligible=True"
    )

    print(
        "Test policy: "
        "reserved holdout"
    )

    dataframe = load_training_dataset(
        TRAINING_DATASET_PATH
    )

    print(
        "\nTraining dataset carregado: "
        f"{len(dataframe):,} linhas"
    )

    validate_training_dataset_contract(
        dataframe
    )

    eligible = filter_ml_eligible(
        dataframe
    )

    (
        validation_start,
        test_start,
    ) = resolve_split_boundaries(
        dataframe=eligible,
        validation_days=(
            args.validation_days
        ),
        test_days=(
            args.test_days
        ),
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
        "Target horizon: "
        f"{EXPECTED_TARGET_HORIZON} "
        "pregões B3 globais"
    )

    print(
        "Validation feature dates: "
        f"{args.validation_days}"
    )

    print(
        "Test feature dates: "
        f"{args.test_days}"
    )

    print(
        "Validation start: "
        f"{validation_start.date()}"
    )

    print(
        "Test start: "
        f"{test_start.date()}"
    )

    (
        train,
        validation,
        test,
    ) = build_temporal_split(
        dataframe=eligible,
        validation_start=validation_start,
        test_start=test_start,
    )

    purge_diagnostics = (
        calculate_purge_diagnostics(
            dataframe=eligible,
            train=train,
            validation=validation,
            test=test,
            validation_start=validation_start,
            test_start=test_start,
        )
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

    print(
        "\nML Eligibility dentro dos splits:"
    )

    validate_all_rows_eligible(
        "train",
        train,
    )

    validate_all_rows_eligible(
        "validation",
        validation,
    )

    validate_all_rows_eligible(
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
        validation_start=validation_start,
        test_start=test_start,
    )

    validate_chronological_order(
        train=train,
        validation=validation,
        test=test,
    )

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico - Purge Temporal"
    )
    print(
        "======================================"
    )

    print(
        "Universo ML eligible: "
        f"{purge_diagnostics['eligible_total']:,}"
    )

    print(
        "\nAntes do purge:"
    )

    print(
        "  Train region: "
        f"{purge_diagnostics['train_region_before_purge']:,}"
    )

    print(
        "  Validation region: "
        f"{purge_diagnostics['validation_region_before_purge']:,}"
    )

    print(
        "  Test region: "
        f"{purge_diagnostics['test_region_before_purge']:,}"
    )

    print(
        "\nRemovidas pelo purge:"
    )

    print(
        "  Train: "
        f"{purge_diagnostics['train_purged']:,}"
    )

    print(
        "  Validation: "
        f"{purge_diagnostics['validation_purged']:,}"
    )

    print(
        "  Test: "
        f"{purge_diagnostics['test_purged']:,}"
    )

    print(
        "  Total: "
        f"{purge_diagnostics['total_purged']:,}"
    )

    print(
        "\nAtribuídas aos splits: "
        f"{purge_diagnostics['assigned_total']:,}"
    )

    reconciliation = (
        purge_diagnostics[
            "assigned_total"
        ]
        + purge_diagnostics[
            "total_purged"
        ]
    )

    if reconciliation != len(
        eligible
    ):
        raise ValueError(
            "Reconciliação do purge falhou."
        )

    train = add_split_metadata(
        dataframe=train,
        split_name="train",
        validation_start=validation_start,
        test_start=test_start,
        validation_days=(
            args.validation_days
        ),
        test_days=(
            args.test_days
        ),
    )

    validation = add_split_metadata(
        dataframe=validation,
        split_name="validation",
        validation_start=validation_start,
        test_start=test_start,
        validation_days=(
            args.validation_days
        ),
        test_days=(
            args.test_days
        ),
    )

    test = add_split_metadata(
        dataframe=test,
        split_name="test",
        validation_start=validation_start,
        test_start=test_start,
        validation_days=(
            args.validation_days
        ),
        test_days=(
            args.test_days
        ),
    )

    validate_split_metadata(
        dataframe=train,
        expected_name="train",
    )

    validate_split_metadata(
        dataframe=validation,
        expected_name="validation",
    )

    validate_split_metadata(
        dataframe=test,
        expected_name="test",
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

    print(
        f"Split version: "
        f"{SPLIT_VERSION}"
    )

    print(
        "Training Dataset source: "
        f"{EXPECTED_TRAINING_DATASET_VERSION}"
    )

    print(
        "Universo supervisionável original: "
        f"{len(dataframe):,}"
    )

    print(
        "Universo ML eligible: "
        f"{len(eligible):,}"
    )

    print(
        "Samples removidas por eligibility: "
        f"{len(dataframe) - len(eligible):,}"
    )

    print(
        "Samples removidas por purge: "
        f"{purge_diagnostics['total_purged']:,}"
    )

    print(
        "Samples finais nos splits: "
        f"{len(train) + len(validation) + len(test):,}"
    )

    print_split_summary(
        name="train",
        dataframe=train,
    )

    print_split_summary(
        name="validation",
        dataframe=validation,
    )

    print_split_summary(
        name="test",
        dataframe=test,
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
        f"Train: "
        f"{TRAIN_PATH}"
    )

    print(
        f"Validation: "
        f"{VALIDATION_PATH}"
    )

    print(
        f"Test: "
        f"{TEST_PATH}"
    )

    print(
        "\nFII Temporal Split "
        f"{SPLIT_VERSION} "
        "criado com sucesso."
    )

    print(
        "Somente ml_eligible=True "
        "entrou nos splits."
    )

    print(
        "Targets que atravessariam "
        "fronteiras foram removidos "
        "pelo purge."
    )

    print(
        "O conjunto test permanece "
        "reservado como holdout."
    )
    

if __name__ == "__main__":
    main()