from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

GOLD_ML_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_features"
    / "fii_features.parquet"
)

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_training_dataset.parquet"
)

DEFAULT_TARGET_HORIZON = 5

TRAINING_DATASET_VERSION = "v2"

TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)


def load_gold_ml() -> pd.DataFrame:
    """
    Carrega a Gold ML.
    """

    if not GOLD_ML_PATH.exists():
        raise FileNotFoundError(
            "Gold ML não encontrada: "
            f"{GOLD_ML_PATH}"
        )

    print(
        f"Carregando Gold ML: "
        f"{GOLD_ML_PATH}"
    )

    dataframe = pd.read_parquet(
        GOLD_ML_PATH
    )

    dataframe[
        "feature_date"
    ] = pd.to_datetime(
        dataframe[
            "feature_date"
        ]
    )

    print(
        f"\nGold ML carregada: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def load_price_history() -> pd.DataFrame:
    """
    Carrega a Gold Analytics usada como
    calendário global B3 e fonte de preço
    do target.
    """

    if not PRICE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "Gold Analytics não encontrada: "
            f"{PRICE_HISTORY_PATH}"
        )

    print(
        f"Carregando calendário/preços: "
        f"{PRICE_HISTORY_PATH}"
    )

    dataframe = pd.read_parquet(
        PRICE_HISTORY_PATH,
        columns=[
            "trade_date",
            "ticker",
            "close_price",
        ],
    )

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
        ]
    )

    return dataframe


def validate_gold_ml_source(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida a fonte Gold ML.
    """

    required_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        "feature_ready",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas ausentes na Gold ML: "
            f"{missing_columns}"
        )

    duplicate_count = (
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        )
        .sum()
    )

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

    print(
        "Duplicidades "
        "(feature_date + ticker): "
        f"{duplicate_count:,}"
    )

    print(
        "\nCampos obrigatórios nulos:"
    )

    for column in [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
    ]:
        null_count = int(
            dataframe[
                column
            ].isna().sum()
        )

        print(
            f"  {column}: "
            f"{null_count:,}"
        )

        if null_count > 0:
            raise ValueError(
                f"Campo obrigatório nulo: "
                f"{column}"
            )

    if duplicate_count > 0:
        raise ValueError(
            "Duplicidades encontradas "
            "na Gold ML."
        )

    print(
        "\nData Quality da fonte aprovada."
    )


def validate_price_history_source(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida a fonte usada para calendário
    e preços futuros.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "close_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas ausentes no histórico: "
            f"{missing_columns}"
        )

    duplicate_count = (
        dataframe.duplicated(
            subset=[
                "trade_date",
                "ticker",
            ]
        )
        .sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Histórico possui duplicidade "
            "(trade_date + ticker)."
        )

    if dataframe[
        "trade_date"
    ].isna().any():
        raise ValueError(
            "Histórico possui trade_date nulo."
        )

    if dataframe[
        "ticker"
    ].isna().any():
        raise ValueError(
            "Histórico possui ticker nulo."
        )

    if dataframe[
        "close_price"
    ].isna().any():
        raise ValueError(
            "Histórico possui close_price nulo."
        )


def build_global_calendar(
    price_history: pd.DataFrame,
) -> list[pd.Timestamp]:
    """
    Constrói calendário global de pregões
    a partir das datas disponíveis na
    Gold Analytics.
    """

    calendar = (
        price_history[
            "trade_date"
        ]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if not calendar:
        raise ValueError(
            "Calendário global B3 vazio."
        )

    return [
        pd.Timestamp(
            value
        )
        for value in calendar
    ]


def build_target_date_map(
    global_calendar: list[pd.Timestamp],
    target_horizon: int,
) -> dict[pd.Timestamp, pd.Timestamp]:
    """
    Mapeia:

        T -> T + target_horizon pregões

    usando o calendário global da B3.
    """

    mapping: dict[
        pd.Timestamp,
        pd.Timestamp,
    ] = {}

    for index, feature_date in enumerate(
        global_calendar
    ):
        target_index = (
            index
            + target_horizon
        )

        if target_index >= len(
            global_calendar
        ):
            continue

        mapping[
            feature_date
        ] = global_calendar[
            target_index
        ]

    return mapping


def build_future_price_lookup(
    price_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara lookup exato de preço por:

        ticker + target_date
    """

    lookup = (
        price_history[
            [
                "trade_date",
                "ticker",
                "close_price",
            ]
        ]
        .rename(
            columns={
                "trade_date": (
                    "target_lookup_date"
                ),
                "close_price": (
                    "target_lookup_price"
                ),
            }
        )
        .copy()
    )

    return lookup


def build_training_dataset(
    gold_ml: pd.DataFrame,
    price_history: pd.DataFrame,
    target_horizon: int,
) -> pd.DataFrame:
    """
    Cria o dataset supervisionado usando
    horizonte GLOBAL de pregões B3.

    Exemplo:

        feature_date = T

        target_date =
            quinto pregão global após T

        target_price =
            close_price do mesmo ticker
            exatamente em target_date

    Se o ticker não tiver preço exatamente
    em T+horizon, a linha não entra no
    training dataset.
    """

    if target_horizon <= 0:
        raise ValueError(
            "target_horizon deve ser "
            "maior que zero."
        )

    global_calendar = (
        build_global_calendar(
            price_history
        )
    )

    target_date_map = (
        build_target_date_map(
            global_calendar=global_calendar,
            target_horizon=target_horizon,
        )
    )

    dataframe = gold_ml[
        gold_ml[
            "feature_ready"
        ]
    ].copy()

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"{target_return_column}_pct"
    )

    dataframe[
        target_date_column
    ] = dataframe[
        "feature_date"
    ].map(
        target_date_map
    )

    future_price_lookup = (
        build_future_price_lookup(
            price_history
        )
    )

    dataframe = dataframe.merge(
        future_price_lookup,
        how="left",
        left_on=[
            "ticker",
            target_date_column,
        ],
        right_on=[
            "ticker",
            "target_lookup_date",
        ],
        validate="many_to_one",
    )

    dataframe = dataframe.rename(
        columns={
            "target_lookup_price": (
                target_price_column
            )
        }
    )

    dataframe = dataframe.drop(
        columns=[
            "target_lookup_date",
        ],
        errors="ignore",
    )

    dataframe[
        target_return_column
    ] = (
        dataframe[
            target_price_column
        ]
        / dataframe[
            "close_price"
        ]
        - 1
    )

    dataframe[
        target_return_pct_column
    ] = (
        dataframe[
            target_return_column
        ]
        * 100
    )

    dataframe[
        "target_horizon"
    ] = target_horizon

    dataframe[
        "target_horizon_semantics"
    ] = (
        TARGET_HORIZON_SEMANTICS
    )

    dataframe[
        "target_name"
    ] = target_return_column

    dataframe[
        "training_dataset_version"
    ] = (
        TRAINING_DATASET_VERSION
    )

    dataframe[
        "training_dataset_created_at"
    ] = datetime.now(
        timezone.utc
    )

    before_filter = len(
        dataframe
    )

    no_global_target_date = int(
        dataframe[
            target_date_column
        ].isna().sum()
    )

    no_exact_target_price = int(
        (
            dataframe[
                target_date_column
            ].notna()
            &
            dataframe[
                target_price_column
            ].isna()
        ).sum()
    )

    dataframe = dataframe[
        dataframe[
            target_date_column
        ].notna()
        &
        dataframe[
            target_price_column
        ].notna()
        &
        dataframe[
            target_return_column
        ].notna()
    ].copy()

    removed_count = (
        before_filter
        - len(dataframe)
    )

    print(
        "\n======================================"
    )
    print(
        "Construção do Target Global"
    )
    print(
        "======================================"
    )

    print(
        f"Feature rows prontas: "
        f"{before_filter:,}"
    )

    print(
        "Sem data global futura disponível: "
        f"{no_global_target_date:,}"
    )

    print(
        "Sem preço do ticker exatamente "
        f"em T+{target_horizon}: "
        f"{no_exact_target_price:,}"
    )

    print(
        "Linhas removidas do dataset "
        f"supervisionado: "
        f"{removed_count:,}"
    )

    return dataframe


def validate_training_dataset(
    dataframe: pd.DataFrame,
    target_horizon: int,
    global_calendar: list[pd.Timestamp],
) -> None:
    """
    Valida o contrato v2.
    """

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    target_price_column = (
        f"target_price_next_"
        f"{target_horizon}d"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    target_return_pct_column = (
        f"{target_return_column}_pct"
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
        "target_horizon",
        "target_horizon_semantics",
        "target_name",
        "training_dataset_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas ausentes no training "
            f"dataset: {missing_columns}"
        )

    duplicate_count = (
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        )
        .sum()
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
        "Linhas supervisionadas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        "Período das features: "
        f"{dataframe['feature_date'].min().date()} "
        "-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        "Período dos targets: "
        f"{dataframe[target_date_column].min().date()} "
        "-> "
        f"{dataframe[target_date_column].max().date()}"
    )

    print(
        "\nDuplicidades "
        "(feature_date + ticker): "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Training dataset possui "
            "duplicidades."
        )

    print(
        "\nCampos obrigatórios nulos:"
    )

    for column in required_columns:
        null_count = int(
            dataframe[
                column
            ].isna().sum()
        )

        print(
            f"  {column}: "
            f"{null_count:,}"
        )

        if null_count > 0:
            raise ValueError(
                "Campo obrigatório nulo: "
                f"{column}"
            )

    invalid_target_prices = int(
        (
            dataframe[
                target_price_column
            ]
            <= 0
        ).sum()
    )

    invalid_target_dates = int(
        (
            dataframe[
                target_date_column
            ]
            <= dataframe[
                "feature_date"
            ]
        ).sum()
    )

    print(
        "\nTarget prices inválidos: "
        f"{invalid_target_prices:,}"
    )

    print(
        "Targets com data <= feature_date: "
        f"{invalid_target_dates:,}"
    )

    if invalid_target_prices > 0:
        raise ValueError(
            "Target prices inválidos."
        )

    if invalid_target_dates > 0:
        raise ValueError(
            "Target dates inválidas."
        )

    expected_target_dates = (
        build_target_date_map(
            global_calendar=global_calendar,
            target_horizon=target_horizon,
        )
    )

    expected_series = dataframe[
        "feature_date"
    ].map(
        expected_target_dates
    )

    exact_horizon_matches = (
        expected_series
        == dataframe[
            target_date_column
        ]
    )

    exact_matches = int(
        exact_horizon_matches.sum()
    )

    exact_total = len(
        dataframe
    )

    mismatch_count = (
        exact_total
        - exact_matches
    )

    print(
        "\nValidação semântica "
        "do horizonte:"
    )

    print(
        f"  Exatamente T+{target_horizon}: "
        f"{exact_matches:,} / "
        f"{exact_total:,}"
    )

    print(
        f"  Divergências: "
        f"{mismatch_count:,}"
    )

    if mismatch_count > 0:
        raise ValueError(
            "Target não respeita "
            "integralmente o calendário "
            "global B3."
        )

    semantics_values = (
        dataframe[
            "target_horizon_semantics"
        ]
        .unique()
        .tolist()
    )

    if semantics_values != [
        TARGET_HORIZON_SEMANTICS
    ]:
        raise ValueError(
            "Semântica de target inválida: "
            f"{semantics_values}"
        )

    print(
        "\nData Quality do training "
        "dataset aprovada."
    )


def print_summary(
    dataframe: pd.DataFrame,
    target_horizon: int,
) -> None:
    """
    Exibe resumo final.
    """

    target_date_column = (
        f"target_date_next_"
        f"{target_horizon}d"
    )

    target_return_column = (
        f"target_return_next_"
        f"{target_horizon}d"
    )

    positive_count = int(
        (
            dataframe[
                target_return_column
            ]
            > 0
        ).sum()
    )

    non_positive_count = (
        len(dataframe)
        - positive_count
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
        "Dataset version: "
        f"{TRAINING_DATASET_VERSION}"
    )

    print(
        "Target horizon: "
        f"{target_horizon} pregões B3 globais"
    )

    print(
        "Target semantics: "
        f"{TARGET_HORIZON_SEMANTICS}"
    )

    print(
        "Target: "
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
        "Feature date: "
        f"{dataframe['feature_date'].min().date()} "
        "-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        "Target date: "
        f"{dataframe[target_date_column].min().date()} "
        "-> "
        f"{dataframe[target_date_column].max().date()}"
    )

    print(
        "Target médio: "
        f"{dataframe[target_return_column].mean() * 100:.4f}%"
    )

    print(
        "Target mediano: "
        f"{dataframe[target_return_column].median() * 100:.4f}%"
    )

    print(
        "Targets positivos: "
        f"{positive_count:,}"
    )

    print(
        "Targets <= 0: "
        f"{non_positive_count:,}"
    )

    print(
        "\nArquivo:"
    )

    print(
        OUTPUT_PATH
    )

    print(
        "\nFII Training Dataset "
        f"{TRAINING_DATASET_VERSION} "
        "criado com sucesso."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cria dataset supervisionado "
            "de FIIs com target baseado no "
            "calendário global de pregões B3."
        )
    )

    parser.add_argument(
        "--target-horizon",
        type=int,
        default=DEFAULT_TARGET_HORIZON,
        help=(
            "Horizonte futuro em pregões "
            "globais B3. Default: 5."
        ),
    )

    args = parser.parse_args()

    if args.target_horizon <= 0:
        raise ValueError(
            "--target-horizon deve ser "
            "maior que zero."
        )

    print(
        "Construindo FII Training Dataset..."
    )

    print(
        "Target horizon: "
        f"{args.target_horizon} "
        "pregões B3 globais"
    )

    gold_ml = (
        load_gold_ml()
    )

    validate_gold_ml_source(
        gold_ml
    )

    price_history = (
        load_price_history()
    )

    validate_price_history_source(
        price_history
    )

    global_calendar = (
        build_global_calendar(
            price_history
        )
    )

    print(
        "\nCalendário global B3: "
        f"{len(global_calendar):,} pregões"
    )

    training_dataset = (
        build_training_dataset(
            gold_ml=gold_ml,
            price_history=price_history,
            target_horizon=(
                args.target_horizon
            ),
        )
    )

    validate_training_dataset(
        dataframe=training_dataset,
        target_horizon=(
            args.target_horizon
        ),
        global_calendar=global_calendar,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    training_dataset.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print_summary(
        dataframe=training_dataset,
        target_horizon=(
            args.target_horizon
        ),
    )


if __name__ == "__main__":
    main()