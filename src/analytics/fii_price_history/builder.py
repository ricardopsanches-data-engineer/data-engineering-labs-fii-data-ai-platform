from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

SILVER_PRICES_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "fii_daily_prices"
)

GOLD_HISTORY_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
)

GOLD_HISTORY_PATH = (
    GOLD_HISTORY_DIR
    / "fii_price_history.parquet"
)

DEFAULT_WINDOWS = [5, 10]

PARTITION_PATTERN = re.compile(
    r"year=(\d{4}).*month=(\d{2}).*day=(\d{2})"
)


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


def extract_partition_date(
    path: Path,
) -> tuple[int, int, int]:
    """
    Extrai YYYY/MM/DD do caminho
    particionado da Silver.
    """

    match = PARTITION_PATTERN.search(
        str(path.parent)
    )

    if match is None:
        raise ValueError(
            "Não foi possível identificar "
            f"a data da partição: {path}"
        )

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def find_all_silver_price_files(
    base_directory: Path,
) -> list[Path]:
    """
    Localiza todas as partições Silver
    disponíveis.
    """

    files = list(
        base_directory.rglob(
            "fii_daily_prices.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            "Nenhuma Silver de preços encontrada "
            f"em {base_directory}"
        )

    return sorted(
        files,
        key=extract_partition_date,
    )


def validate_source_schema(
    dataframe: pd.DataFrame,
    source_path: Path,
) -> None:
    """
    Valida o contrato mínimo de cada
    partição Silver.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
        "ticker_resolution_status",
        "market_evidence_confidence",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Arquivo {source_path} possui "
            f"colunas ausentes: {missing_columns}"
        )


def load_price_history(
    silver_files: list[Path],
) -> pd.DataFrame:
    """
    Carrega e consolida todas as
    partições Silver.
    """

    dataframes: list[pd.DataFrame] = []

    print(
        "\n======================================"
    )
    print(
        "Carregando partições Silver"
    )
    print(
        "======================================"
    )

    for index, path in enumerate(
        silver_files,
        start=1,
    ):
        year, month, day = (
            extract_partition_date(
                path
            )
        )

        print(
            f"[{index}/{len(silver_files)}] "
            f"{year:04d}-{month:02d}-{day:02d}"
        )

        dataframe = pd.read_parquet(
            path
        )

        validate_source_schema(
            dataframe=dataframe,
            source_path=path,
        )

        dataframes.append(
            dataframe
        )

    history = pd.concat(
        dataframes,
        ignore_index=True,
    )

    history[
        "trade_date"
    ] = pd.to_datetime(
        history[
            "trade_date"
        ]
    )

    history[
        "ticker"
    ] = (
        history[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return history


def validate_base_history(
    dataframe: pd.DataFrame,
) -> None:
    """
    Data Quality do histórico antes
    do cálculo das features.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Histórico Base"
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
        f"Pregões únicos: "
        f"{dataframe['trade_date'].nunique():,}"
    )

    duplicate_mask = dataframe.duplicated(
        subset=[
            "ticker",
            "trade_date",
        ],
        keep=False,
    )

    duplicate_count = int(
        duplicate_mask.sum()
    )

    print(
        f"Duplicidades ticker + trade_date: "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Histórico contém duplicidade "
            "ticker + trade_date."
        )

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "close_price",
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
            "Histórico contém campos "
            "obrigatórios nulos."
        )


def calculate_daily_return(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula retorno diário close-to-close.
    """

    result = dataframe.copy()

    result = result.sort_values(
        by=[
            "ticker",
            "trade_date",
        ]
    ).reset_index(
        drop=True
    )

    result[
        "daily_return"
    ] = (
        result.groupby(
            "ticker"
        )[
            "close_price"
        ]
        .pct_change(
            fill_method=None
        )
    )

    result[
        "daily_return_pct"
    ] = (
        result[
            "daily_return"
        ]
        * 100
    )

    return result


def calculate_window_features(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Cria dinamicamente as features
    temporais para cada janela.

    Para window=5, por exemplo:

    return_5d
    return_5d_pct
    ma_5
    volatility_5d
    volatility_5d_pct
    trades_avg_5d
    price_to_ma5
    """

    result = dataframe.copy()

    for window in windows:

        print(
            f"Calculando janela "
            f"{window} pregões..."
        )

        # -------------------------------------
        # Retorno acumulado
        #
        # close_t / close_t-N - 1
        # -------------------------------------

        return_column = (
            f"return_{window}d"
        )

        return_pct_column = (
            f"return_{window}d_pct"
        )

        result[
            return_column
        ] = (
            result.groupby(
                "ticker"
            )[
                "close_price"
            ]
            .pct_change(
                periods=window,
                fill_method=None,
            )
        )

        result[
            return_pct_column
        ] = (
            result[
                return_column
            ]
            * 100
        )

        # -------------------------------------
        # Média móvel
        # -------------------------------------

        ma_column = (
            f"ma_{window}"
        )

        result[
            ma_column
        ] = (
            result.groupby(
                "ticker"
            )[
                "close_price"
            ]
            .rolling(
                window=window,
                min_periods=window,
            )
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
        )

        # -------------------------------------
        # Volatilidade
        #
        # Desvio padrão dos últimos
        # N retornos diários.
        # -------------------------------------

        volatility_column = (
            f"volatility_{window}d"
        )

        volatility_pct_column = (
            f"volatility_{window}d_pct"
        )

        result[
            volatility_column
        ] = (
            result.groupby(
                "ticker"
            )[
                "daily_return"
            ]
            .rolling(
                window=window,
                min_periods=window,
            )
            .std()
            .reset_index(
                level=0,
                drop=True,
            )
        )

        result[
            volatility_pct_column
        ] = (
            result[
                volatility_column
            ]
            * 100
        )

        # -------------------------------------
        # Liquidez proxy
        # -------------------------------------

        trades_avg_column = (
            f"trades_avg_{window}d"
        )

        result[
            trades_avg_column
        ] = (
            result.groupby(
                "ticker"
            )[
                "trades_quantity"
            ]
            .rolling(
                window=window,
                min_periods=window,
            )
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
        )

        # -------------------------------------
        # Relação preço / média móvel
        # -------------------------------------

        price_to_ma_column = (
            f"price_to_ma{window}"
        )

        result[
            price_to_ma_column
        ] = (
            result[
                "close_price"
            ]
            / result[
                ma_column
            ]
        )

    return result


def calculate_observation_count(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Número acumulado de observações
    disponíveis por ticker.
    """

    result = dataframe.copy()

    result[
        "observations_count"
    ] = (
        result.groupby(
            "ticker"
        )
        .cumcount()
        + 1
    )

    return result


def build_dynamic_feature_columns(
    windows: list[int],
) -> list[str]:
    """
    Constrói dinamicamente o contrato
    das features temporais.
    """

    columns: list[str] = [
        "daily_return",
        "daily_return_pct",
    ]

    for window in windows:
        columns.extend(
            [
                f"return_{window}d",
                f"return_{window}d_pct",
                f"ma_{window}",
                f"volatility_{window}d",
                f"volatility_{window}d_pct",
                f"trades_avg_{window}d",
                f"price_to_ma{window}",
            ]
        )

    return columns


def select_gold_columns(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Monta o contrato Gold dinamicamente.
    """

    identity_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
    ]

    feature_columns = (
        build_dynamic_feature_columns(
            windows
        )
    )

    metadata_columns = [
        "observations_count",
        "ticker_resolution_status",
        "market_evidence_confidence",
    ]

    columns = (
        identity_columns
        + feature_columns
        + metadata_columns
    )

    gold = dataframe[
        columns
    ].copy()

    gold[
        "gold_created_at"
    ] = datetime.now(
        timezone.utc
    )

    gold[
        "feature_windows"
    ] = ",".join(
        str(window)
        for window in windows
    )

    return gold


def validate_dynamic_features(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Data Quality dinâmica das features.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Features Temporais"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    daily_return_count = (
        dataframe[
            "daily_return"
        ]
        .notna()
        .sum()
    )

    print(
        f"daily_return disponível: "
        f"{daily_return_count:,}"
    )

    invalid_observation_count = (
        dataframe[
            "observations_count"
        ]
        <= 0
    ).sum()

    if invalid_observation_count > 0:
        raise ValueError(
            "observations_count inválido."
        )

    for window in windows:

        print(
            f"\nJanela {window}:"
        )

        return_column = (
            f"return_{window}d"
        )

        ma_column = (
            f"ma_{window}"
        )

        volatility_column = (
            f"volatility_{window}d"
        )

        trades_avg_column = (
            f"trades_avg_{window}d"
        )

        price_to_ma_column = (
            f"price_to_ma{window}"
        )

        feature_columns = [
            return_column,
            ma_column,
            volatility_column,
            trades_avg_column,
            price_to_ma_column,
        ]

        for column in feature_columns:

            available = (
                dataframe[
                    column
                ]
                .notna()
                .sum()
            )

            print(
                f"  {column}: "
                f"{available:,}"
            )

        # -------------------------------------
        # MA e trades_avg precisam de
        # N observações.
        # -------------------------------------

        invalid_ma = dataframe[
            (
                dataframe[
                    "observations_count"
                ]
                < window
            )
            &
            dataframe[
                ma_column
            ].notna()
        ]

        if not invalid_ma.empty:
            raise ValueError(
                f"{ma_column} encontrado "
                f"antes de {window} observações."
            )

        invalid_trades_avg = dataframe[
            (
                dataframe[
                    "observations_count"
                ]
                < window
            )
            &
            dataframe[
                trades_avg_column
            ].notna()
        ]

        if not invalid_trades_avg.empty:
            raise ValueError(
                f"{trades_avg_column} encontrado "
                f"antes de {window} observações."
            )

        # -------------------------------------
        # Return_Nd precisa comparar
        # T com T-N.
        #
        # Portanto precisa de N+1 preços.
        # -------------------------------------

        minimum_return_observations = (
            window + 1
        )

        invalid_return = dataframe[
            (
                dataframe[
                    "observations_count"
                ]
                < minimum_return_observations
            )
            &
            dataframe[
                return_column
            ].notna()
        ]

        if not invalid_return.empty:
            raise ValueError(
                f"{return_column} encontrado "
                f"antes de "
                f"{minimum_return_observations} "
                f"observações."
            )

        # -------------------------------------
        # Volatilidade de N retornos também
        # exige N+1 preços.
        # -------------------------------------

        invalid_volatility = dataframe[
            (
                dataframe[
                    "observations_count"
                ]
                < minimum_return_observations
            )
            &
            dataframe[
                volatility_column
            ].notna()
        ]

        if not invalid_volatility.empty:
            raise ValueError(
                f"{volatility_column} encontrada "
                f"antes de "
                f"{minimum_return_observations} "
                f"observações."
            )

        # -------------------------------------
        # price_to_maN não pode existir
        # sem ma_N.
        # -------------------------------------

        invalid_price_to_ma = dataframe[
            dataframe[
                price_to_ma_column
            ].notna()
            &
            dataframe[
                ma_column
            ].isna()
        ]

        if not invalid_price_to_ma.empty:
            raise ValueError(
                f"{price_to_ma_column} existe "
                f"sem {ma_column}."
            )

    print(
        "\nData Quality das features aprovada."
    )


def save_gold(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste a Gold Analytics em Parquet.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )


def print_history_summary(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Exibe resumo final.
    """

    min_date = (
        dataframe[
            "trade_date"
        ]
        .min()
        .date()
    )

    max_date = (
        dataframe[
            "trade_date"
        ]
        .max()
        .date()
    )

    observations = (
        dataframe.groupby(
            "ticker"
        )
        .size()
    )

    total_trading_days = (
        dataframe[
            "trade_date"
        ]
        .nunique()
    )

    print(
        "\n======================================"
    )
    print(
        "Resumo Gold FII Price History"
    )
    print(
        "======================================"
    )

    print(
        f"Período: "
        f"{min_date} -> {max_date}"
    )

    print(
        f"Pregões: "
        f"{total_trading_days:,}"
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
        f"Máximo de observações por ticker: "
        f"{observations.max():,}"
    )

    print(
        f"Tickers presentes em todos "
        f"os pregões: "
        f"{(observations == total_trading_days).sum():,}"
    )

    print(
        f"Janelas calculadas: "
        f"{windows}"
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
            f"  Linhas com {return_column}: "
            f"{dataframe[return_column].notna().sum():,}"
        )

        print(
            f"  Linhas com {volatility_column}: "
            f"{dataframe[volatility_column].notna().sum():,}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói Gold Analytics "
            "FII Price History."
        )
    )

    parser.add_argument(
        "--windows",
        nargs="+",
        type=int,
        default=DEFAULT_WINDOWS,
        help=(
            "Janelas temporais em pregões. "
            "Exemplo: --windows 5 10 20"
        ),
    )

    args = parser.parse_args()

    windows = normalize_windows(
        args.windows
    )

    print(
        "Construindo Gold Analytics "
        "FII Price History..."
    )

    print(
        f"Janelas temporais: "
        f"{windows}"
    )

    silver_files = (
        find_all_silver_price_files(
            SILVER_PRICES_BASE_DIR
        )
    )

    print(
        f"\nPartições Silver encontradas: "
        f"{len(silver_files):,}"
    )

    history = load_price_history(
        silver_files
    )

    validate_base_history(
        history
    )

    history = calculate_daily_return(
        history
    )

    history = calculate_window_features(
        dataframe=history,
        windows=windows,
    )

    history = calculate_observation_count(
        history
    )

    gold = select_gold_columns(
        dataframe=history,
        windows=windows,
    )

    validate_dynamic_features(
        dataframe=gold,
        windows=windows,
    )

    save_gold(
        dataframe=gold,
        destination=GOLD_HISTORY_PATH,
    )

    print_history_summary(
        dataframe=gold,
        windows=windows,
    )

    print(
        "\nArquivo:"
    )

    print(
        GOLD_HISTORY_PATH
    )

    print(
        "\nGold Analytics "
        "FII Price History criada "
        "com sucesso."
    )


if __name__ == "__main__":
    main()