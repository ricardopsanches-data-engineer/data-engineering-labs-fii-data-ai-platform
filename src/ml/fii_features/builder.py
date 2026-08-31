from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

ML_FEATURES_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_features"
)

ML_FEATURES_PATH = (
    ML_FEATURES_DIR
    / "fii_features.parquet"
)

DEFAULT_WINDOWS = [5, 10]

FEATURE_VERSION = "v3"


def normalize_windows(
    windows: list[int],
) -> list[int]:
    """
    Valida, remove duplicidades e ordena
    as janelas temporais.
    """

    if not windows:
        raise ValueError(
            "Pelo menos uma janela temporal "
            "deve ser informada."
        )

    if any(
        window <= 0
        for window in windows
    ):
        raise ValueError(
            "Todas as janelas devem ser "
            "maiores que zero."
        )

    return sorted(
        set(windows)
    )


def build_window_feature_columns(
    window: int,
) -> list[str]:
    """
    Retorna as features obrigatórias
    de uma determinada janela temporal.
    """

    return [
        f"return_{window}d",
        f"return_{window}d_pct",
        f"ma_{window}",
        f"volatility_{window}d",
        f"volatility_{window}d_pct",
        f"trades_avg_{window}d",
        f"price_to_ma{window}",
    ]


def build_dynamic_feature_columns(
    windows: list[int],
) -> list[str]:
    """
    Constrói dinamicamente a lista
    completa de features.
    """

    columns = [
        "daily_return",
        "daily_return_pct",
    ]

    for window in windows:
        columns.extend(
            build_window_feature_columns(
                window
            )
        )

    return columns


def load_price_history(
    path: Path,
    windows: list[int],
) -> pd.DataFrame:
    """
    Carrega o histórico Gold Analytics
    e valida se as features solicitadas
    existem.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Histórico não encontrado: {path}"
        )

    print(
        f"Carregando histórico analítico: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    base_required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        "trades_quantity",
        "daily_return",
        "daily_return_pct",
        "observations_count",
    ]

    dynamic_required_columns = (
        build_dynamic_feature_columns(
            windows
        )
    )

    required_columns = (
        base_required_columns
        + dynamic_required_columns
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"no histórico: {missing_columns}. "
            "Verifique se a Gold Analytics foi "
            "gerada com as mesmas --windows."
        )

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
        ]
    )

    return dataframe


def build_ml_features(
    history: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Constrói dataset de features ML
    dinamicamente.

    Todas as features utilizam somente
    informações disponíveis até a
    feature_date.
    """

    base_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        "trades_quantity",
        "daily_return",
        "daily_return_pct",
        "observations_count",
    ]

    dynamic_columns = (
        build_dynamic_feature_columns(
            windows
        )
    )

    columns = (
        base_columns
        + [
            column
            for column in dynamic_columns
            if column not in base_columns
        ]
    )

    features = history[
        columns
    ].copy()

    features = features.rename(
        columns={
            "trade_date": "feature_date",
        }
    )

    # -----------------------------------------
    # Feature readiness dinâmica
    #
    # Começamos assumindo True.
    # Cada janela adiciona suas condições.
    # -----------------------------------------

    ready_mask = pd.Series(
        True,
        index=features.index,
        dtype=bool,
    )

    # Retorno diário também é obrigatório.
    ready_mask &= (
        features[
            "daily_return"
        ].notna()
    )

    for window in windows:

        minimum_observations = (
            window + 1
        )

        ready_mask &= (
            features[
                "observations_count"
            ]
            >= minimum_observations
        )

        required_window_columns = [
            f"return_{window}d",
            f"ma_{window}",
            f"volatility_{window}d",
            f"trades_avg_{window}d",
            f"price_to_ma{window}",
        ]

        for column in required_window_columns:
            ready_mask &= (
                features[
                    column
                ].notna()
            )

    features[
        "feature_ready"
    ] = ready_mask

    return features


def validate_ml_features(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Data Quality dinâmica da Gold ML.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - FII ML Features"
    )
    print(
        "======================================"
    )

    print(
        f"Janelas: {windows}"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers únicos: "
        f"{dataframe['ticker'].nunique():,}"
    )

    ready_count = int(
        dataframe[
            "feature_ready"
        ].sum()
    )

    immature_count = (
        len(dataframe)
        - ready_count
    )

    print(
        f"Feature rows prontas: "
        f"{ready_count:,}"
    )

    print(
        f"Feature rows ainda imaturas: "
        f"{immature_count:,}"
    )

    # -----------------------------------------
    # Identidade
    # -----------------------------------------

    required_identity_columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
    ]

    null_identity = (
        dataframe[
            required_identity_columns
        ]
        .isna()
        .sum()
    )

    print(
        "\nCampos de identidade nulos:"
    )

    for column, count in null_identity.items():
        print(
            f"  {column}: "
            f"{count:,}"
        )

    if (
        null_identity
        > 0
    ).any():
        raise ValueError(
            "Dataset ML contém campos "
            "de identidade nulos."
        )

    # -----------------------------------------
    # Granularidade
    # -----------------------------------------

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
            "Dataset ML contém duplicidade "
            "na granularidade de features."
        )

    # -----------------------------------------
    # Linhas prontas
    # -----------------------------------------

    ready = dataframe[
        dataframe[
            "feature_ready"
        ]
    ]

    if ready.empty:
        print(
            "\nAviso: nenhuma linha "
            "feature_ready encontrada."
        )

        return

    required_ready_columns = [
        "close_price",
        "trades_quantity",
        "daily_return",
    ]

    for window in windows:
        required_ready_columns.extend(
            [
                f"return_{window}d",
                f"ma_{window}",
                f"volatility_{window}d",
                f"trades_avg_{window}d",
                f"price_to_ma{window}",
            ]
        )

    ready_nulls = (
        ready[
            required_ready_columns
        ]
        .isna()
        .sum()
    )

    print(
        "\nNulos em linhas feature_ready:"
    )

    for column, count in ready_nulls.items():
        print(
            f"  {column}: "
            f"{count:,}"
        )

    if (
        ready_nulls
        > 0
    ).any():
        raise ValueError(
            "Linhas feature_ready possuem "
            "features obrigatórias nulas."
        )

    # -----------------------------------------
    # Validação estrutural por janela
    # -----------------------------------------

    for window in windows:

        minimum_observations = (
            window + 1
        )

        invalid_ready = ready[
            ready[
                "observations_count"
            ]
            < minimum_observations
        ]

        if not invalid_ready.empty:
            raise ValueError(
                "feature_ready=True encontrado "
                f"com menos de "
                f"{minimum_observations} "
                f"observações para a janela "
                f"{window}."
            )

    print(
        "\nData Quality ML aprovada."
    )


def add_metadata(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Adiciona metadados técnicos
    e de configuração.
    """

    result = dataframe.copy()

    result[
        "features_created_at"
    ] = datetime.now(
        timezone.utc
    )

    result[
        "feature_version"
    ] = FEATURE_VERSION

    result[
        "feature_windows"
    ] = ",".join(
        str(window)
        for window in windows
    )

    return result


def save_features(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste dataset de features.
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
    windows: list[int],
) -> None:
    """
    Exibe resumo final.
    """

    ready = dataframe[
        dataframe[
            "feature_ready"
        ]
    ]

    print(
        "\n======================================"
    )
    print(
        "Resumo Gold ML - FII Features"
    )
    print(
        "======================================"
    )

    print(
        f"Feature version: "
        f"{FEATURE_VERSION}"
    )

    print(
        f"Janelas: "
        f"{windows}"
    )

    print(
        f"Período total: "
        f"{dataframe['feature_date'].min().date()} "
        f"-> "
        f"{dataframe['feature_date'].max().date()}"
    )

    print(
        f"Linhas totais: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers totais: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"Linhas prontas para ML: "
        f"{len(ready):,}"
    )

    print(
        f"Tickers com pelo menos "
        f"uma linha pronta: "
        f"{ready['ticker'].nunique():,}"
    )

    for window in windows:

        return_column = (
            f"return_{window}d"
        )

        volatility_column = (
            f"volatility_{window}d"
        )

        print(
            f"\nJanela {window}:"
        )

        print(
            f"  {return_column} disponível: "
            f"{dataframe[return_column].notna().sum():,}"
        )

        print(
            f"  {volatility_column} disponível: "
            f"{dataframe[volatility_column].notna().sum():,}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói Gold ML "
            "FII Features."
        )
    )

    parser.add_argument(
        "--windows",
        nargs="+",
        type=int,
        default=DEFAULT_WINDOWS,
        help=(
            "Janelas temporais em pregões. "
            "Devem ser iguais às utilizadas "
            "na Gold Analytics. "
            "Exemplo: --windows 5 10"
        ),
    )

    args = parser.parse_args()

    windows = normalize_windows(
        args.windows
    )

    print(
        "Construindo Gold ML "
        "FII Features..."
    )

    print(
        f"Janelas temporais: "
        f"{windows}"
    )

    history = load_price_history(
        path=PRICE_HISTORY_PATH,
        windows=windows,
    )

    print(
        f"\nHistórico carregado: "
        f"{len(history):,} linhas"
    )

    features = build_ml_features(
        history=history,
        windows=windows,
    )

    validate_ml_features(
        dataframe=features,
        windows=windows,
    )

    features = add_metadata(
        dataframe=features,
        windows=windows,
    )

    save_features(
        dataframe=features,
        destination=ML_FEATURES_PATH,
    )

    print_summary(
        dataframe=features,
        windows=windows,
    )

    print(
        "\nArquivo:"
    )

    print(
        ML_FEATURES_PATH
    )

    print(
        "\nGold ML "
        "FII Features criada "
        "com sucesso."
    )


if __name__ == "__main__":
    main()