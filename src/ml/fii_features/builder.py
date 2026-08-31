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

FEATURE_VERSION = "v4"


def normalize_windows(
    windows: list[int],
) -> list[int]:
    """
    Valida, remove duplicidades
    e ordena as janelas.
    """

    if not windows:
        raise ValueError(
            "Nenhuma janela temporal informada."
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


def parse_feature_windows_value(
    value: object,
) -> list[int]:
    """
    Converte o metadata feature_windows
    salvo pela Gold Analytics.

    Exemplo:
        "5,10"
        ->
        [5, 10]
    """

    if value is None:
        raise ValueError(
            "feature_windows ausente "
            "na Gold Analytics."
        )

    text = str(
        value
    ).strip()

    if not text:
        raise ValueError(
            "feature_windows vazio "
            "na Gold Analytics."
        )

    try:
        windows = [
            int(part.strip())
            for part in text.split(",")
            if part.strip()
        ]

    except ValueError as error:
        raise ValueError(
            "feature_windows inválido "
            f"na Gold Analytics: {value}"
        ) from error

    return normalize_windows(
        windows
    )


def discover_windows_from_history(
    dataframe: pd.DataFrame,
) -> list[int]:
    """
    Descobre automaticamente as janelas
    utilizadas pela Gold Analytics.
    """

    if (
        "feature_windows"
        not in dataframe.columns
    ):
        raise ValueError(
            "A Gold Analytics não possui "
            "a coluna feature_windows. "
            "Reconstrua o histórico com "
            "o builder dinâmico."
        )

    values = (
        dataframe[
            "feature_windows"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    if len(values) == 0:
        raise ValueError(
            "Nenhum feature_windows válido "
            "encontrado na Gold Analytics."
        )

    if len(values) > 1:
        raise ValueError(
            "Gold Analytics contém mais de "
            "uma configuração feature_windows: "
            f"{values.tolist()}"
        )

    return parse_feature_windows_value(
        values[0]
    )


def build_window_feature_columns(
    window: int,
) -> list[str]:
    """
    Features geradas para uma janela.
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
    Lista completa das features
    temporais solicitadas.
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
) -> pd.DataFrame:
    """
    Carrega a Gold Analytics.
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

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
        ]
    )

    return dataframe


def validate_history_contract(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Valida se a Gold Analytics contém
    todas as colunas necessárias.
    """

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
        "feature_windows",
    ]

    dynamic_required_columns = (
        build_dynamic_feature_columns(
            windows
        )
    )

    required_columns = list(
        dict.fromkeys(
            base_required_columns
            + dynamic_required_columns
        )
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"na Gold Analytics: "
            f"{missing_columns}"
        )


def resolve_windows(
    dataframe: pd.DataFrame,
    override_windows: list[int] | None,
) -> list[int]:
    """
    Resolve janelas.

    Prioridade:
    1. --windows explícito
    2. feature_windows da Gold Analytics
    """

    discovered_windows = (
        discover_windows_from_history(
            dataframe
        )
    )

    if override_windows is None:
        print(
            "Janelas herdadas da "
            f"Gold Analytics: "
            f"{discovered_windows}"
        )

        return discovered_windows

    override_windows = (
        normalize_windows(
            override_windows
        )
    )

    print(
        f"Janelas da Gold Analytics: "
        f"{discovered_windows}"
    )

    print(
        f"Override solicitado: "
        f"{override_windows}"
    )

    # -----------------------------------------
    # O override só pode usar janelas
    # realmente disponíveis no histórico.
    # -----------------------------------------

    unavailable_windows = [
        window
        for window in override_windows
        if window
        not in discovered_windows
    ]

    if unavailable_windows:
        raise ValueError(
            "Override solicita janelas "
            "não disponíveis na "
            "Gold Analytics: "
            f"{unavailable_windows}. "
            f"Disponíveis: "
            f"{discovered_windows}"
        )

    return override_windows


def build_ml_features(
    history: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Constrói dataset ML dinamicamente.
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

    columns = list(
        dict.fromkeys(
            base_columns
            + dynamic_columns
        )
    )

    features = history[
        columns
    ].copy()

    features = features.rename(
        columns={
            "trade_date": "feature_date",
        }
    )

    ready_mask = pd.Series(
        True,
        index=features.index,
        dtype=bool,
    )

    # Retorno diário obrigatório.
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
    Adiciona metadados técnicos.
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
    Persiste Gold ML.
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
    Resumo final.
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
        default=None,
        help=(
            "Override opcional das janelas. "
            "Quando omitido, as janelas são "
            "herdadas automaticamente da "
            "Gold Analytics."
        ),
    )

    args = parser.parse_args()

    print(
        "Construindo Gold ML "
        "FII Features..."
    )

    history = load_price_history(
        PRICE_HISTORY_PATH
    )

    print(
        f"\nHistórico carregado: "
        f"{len(history):,} linhas"
    )

    windows = resolve_windows(
        dataframe=history,
        override_windows=args.windows,
    )

    validate_history_contract(
        dataframe=history,
        windows=windows,
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