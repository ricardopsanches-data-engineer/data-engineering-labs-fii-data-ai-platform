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

FEATURE_VERSION = "v5"


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
        "5,10,20"
        ->
        [5, 10, 20]
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
    Retorna as features temporais
    pertencentes a uma janela.
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
    temporais produzidas pela Analytics.
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


def build_cross_window_feature_columns(
    windows: list[int],
) -> list[str]:
    """
    Retorna os nomes das features
    derivadas entre janelas consecutivas.

    Exemplo:

        windows = [5, 10, 20]

    Relações criadas:

        5 vs 10
        10 vs 20
    """

    columns: list[str] = []

    if len(windows) < 2:
        return columns

    for short_window, long_window in zip(
        windows,
        windows[1:],
    ):
        columns.extend(
            [
                (
                    f"return_spread_"
                    f"{short_window}d_"
                    f"{long_window}d"
                ),
                (
                    f"ma_ratio_"
                    f"{short_window}_"
                    f"{long_window}"
                ),
                (
                    f"volatility_ratio_"
                    f"{short_window}d_"
                    f"{long_window}d"
                ),
                (
                    f"trades_ratio_"
                    f"{short_window}d_"
                    f"{long_window}d"
                ),
            ]
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

    if "trade_date" not in dataframe.columns:
        raise ValueError(
            "A Gold Analytics não possui "
            "a coluna trade_date."
        )

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
        ]
    )

    return dataframe


def resolve_windows(
    dataframe: pd.DataFrame,
    override_windows: list[int] | None,
) -> list[int]:
    """
    Resolve as janelas utilizadas pelo ML.

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

    override_windows = normalize_windows(
        override_windows
    )

    print(
        f"Janelas da Gold Analytics: "
        f"{discovered_windows}"
    )

    print(
        f"Override solicitado: "
        f"{override_windows}"
    )

    unavailable_windows = [
        window
        for window in override_windows
        if window not in discovered_windows
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


def validate_history_contract(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Valida o contrato da Gold Analytics
    necessário para produzir a Gold ML.
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
            "na Gold Analytics: "
            f"{missing_columns}"
        )


def calculate_cross_window_features(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Calcula features relacionais entre
    janelas consecutivas.

    Todas utilizam somente informações
    conhecidas até a feature_date.

    Exemplos para [5, 10, 20]:

        return_spread_5d_10d
        ma_ratio_5_10
        volatility_ratio_5d_10d
        trades_ratio_5d_10d

        return_spread_10d_20d
        ma_ratio_10_20
        volatility_ratio_10d_20d
        trades_ratio_10d_20d
    """

    result = dataframe.copy()

    if len(windows) < 2:
        return result

    for short_window, long_window in zip(
        windows,
        windows[1:],
    ):
        # -------------------------------------
        # Momentum relativo
        #
        # retorno curto - retorno longo
        # -------------------------------------

        return_spread_column = (
            f"return_spread_"
            f"{short_window}d_"
            f"{long_window}d"
        )

        result[
            return_spread_column
        ] = (
            result[
                f"return_{short_window}d"
            ]
            - result[
                f"return_{long_window}d"
            ]
        )

        # -------------------------------------
        # Relação entre médias móveis
        #
        # > 1:
        # média curta acima da longa
        #
        # < 1:
        # média curta abaixo da longa
        # -------------------------------------

        ma_ratio_column = (
            f"ma_ratio_"
            f"{short_window}_"
            f"{long_window}"
        )

        long_ma = result[
            f"ma_{long_window}"
        ].where(
            result[
                f"ma_{long_window}"
            ]
            != 0
        )

        result[
            ma_ratio_column
        ] = (
            result[
                f"ma_{short_window}"
            ]
            / long_ma
        )

        # -------------------------------------
        # Regime relativo de volatilidade
        #
        # > 1:
        # volatilidade recente maior
        #
        # < 1:
        # volatilidade recente menor
        #
        # Quando a volatilidade longa é zero,
        # a razão não é matematicamente
        # definida e permanece nula.
        # -------------------------------------

        volatility_ratio_column = (
            f"volatility_ratio_"
            f"{short_window}d_"
            f"{long_window}d"
        )

        long_volatility = result[
            f"volatility_{long_window}d"
        ].where(
            result[
                f"volatility_{long_window}d"
            ]
            != 0
        )

        result[
            volatility_ratio_column
        ] = (
            result[
                f"volatility_{short_window}d"
            ]
            / long_volatility
        )

        # -------------------------------------
        # Regime relativo de atividade
        #
        # > 1:
        # atividade recente acima da média
        # de prazo mais longo
        # -------------------------------------

        trades_ratio_column = (
            f"trades_ratio_"
            f"{short_window}d_"
            f"{long_window}d"
        )

        long_trades = result[
            f"trades_avg_{long_window}d"
        ].where(
            result[
                f"trades_avg_{long_window}d"
            ]
            != 0
        )

        result[
            trades_ratio_column
        ] = (
            result[
                f"trades_avg_{short_window}d"
            ]
            / long_trades
        )

    return result


def build_ml_features(
    history: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Constrói o dataset ML dinamicamente.
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

    # -----------------------------------------
    # Features derivadas entre janelas
    # -----------------------------------------

    features = (
        calculate_cross_window_features(
            dataframe=features,
            windows=windows,
        )
    )

    # -----------------------------------------
    # Feature readiness
    #
    # Uma linha é considerada madura quando
    # todas as features temporais necessárias
    # às janelas solicitadas estão disponíveis.
    #
    # Features de razão derivadas não entram
    # obrigatoriamente no readiness porque
    # algumas razões podem ser matematicamente
    # indefinidas quando o denominador é zero.
    # -----------------------------------------

    ready_mask = pd.Series(
        True,
        index=features.index,
        dtype=bool,
    )

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
    # Linhas feature_ready
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
        "\nNulos obrigatórios em "
        "linhas feature_ready:"
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

    # -----------------------------------------
    # Features derivadas entre janelas
    #
    # Spread e MA ratio devem estar
    # disponíveis nas linhas maduras.
    #
    # Volatility ratio e trades ratio podem
    # ficar nulos se houver denominador zero.
    # Por isso são monitoradas, mas não
    # invalidam automaticamente o dataset.
    # -----------------------------------------

    cross_columns = (
        build_cross_window_feature_columns(
            windows
        )
    )

    if cross_columns:
        print(
            "\nFeatures derivadas "
            "entre janelas:"
        )

        for column in cross_columns:
            available = (
                ready[
                    column
                ]
                .notna()
                .sum()
            )

            missing = (
                ready[
                    column
                ]
                .isna()
                .sum()
            )

            print(
                f"  {column}: "
                f"{available:,} disponíveis | "
                f"{missing:,} nulas"
            )

        mandatory_cross_columns = [
            column
            for column in cross_columns
            if (
                column.startswith(
                    "return_spread_"
                )
                or column.startswith(
                    "ma_ratio_"
                )
            )
        ]

        mandatory_cross_nulls = (
            ready[
                mandatory_cross_columns
            ]
            .isna()
            .sum()
        )

        if (
            mandatory_cross_nulls
            > 0
        ).any():
            raise ValueError(
                "Features derivadas obrigatórias "
                "possuem valores nulos em "
                "linhas feature_ready."
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
    Persiste a Gold ML em Parquet.
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

    cross_columns = (
        build_cross_window_feature_columns(
            windows
        )
    )

    if cross_columns:
        print(
            "\nFeatures entre janelas:"
        )

        for column in cross_columns:
            print(
                f"  {column}: "
                f"{dataframe[column].notna().sum():,}"
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
        f"FII Features {FEATURE_VERSION} "
        "criada com sucesso."
    )


if __name__ == "__main__":
    main()