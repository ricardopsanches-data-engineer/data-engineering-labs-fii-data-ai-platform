from __future__ import annotations

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

PARTITION_PATTERN = re.compile(
    r"year=(\d{4}).*month=(\d{2}).*day=(\d{2})"
)


def extract_partition_date(
    path: Path,
) -> tuple[int, int, int]:
    """
    Extrai YYYY/MM/DD do caminho particionado.
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
    de preços disponíveis.
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
    Valida contrato mínimo das Silvers.
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
    Lê e concatena todas as partições Silver.
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
    Valida histórico consolidado.
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


def calculate_time_series_features(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula features temporais por ticker.
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

    grouped = result.groupby(
        "ticker",
        group_keys=False,
    )

    # -----------------------------------------
    # Retorno diário close-to-close
    # -----------------------------------------

    result[
        "daily_return"
    ] = grouped[
        "close_price"
    ].pct_change(
        fill_method=None
    )

    result[
        "daily_return_pct"
    ] = (
        result[
            "daily_return"
        ]
        * 100
    )

    # -----------------------------------------
    # Retorno acumulado de 5 pregões
    #
    # close_t / close_t-5 - 1
    #
    # Precisa de 6 preços.
    # -----------------------------------------

    result[
        "return_5d"
    ] = grouped[
        "close_price"
    ].pct_change(
        periods=5,
        fill_method=None,
    )

    result[
        "return_5d_pct"
    ] = (
        result[
            "return_5d"
        ]
        * 100
    )

    # -----------------------------------------
    # Média móvel 5 pregões
    # -----------------------------------------

    result[
        "ma_5"
    ] = (
        grouped[
            "close_price"
        ]
        .rolling(
            window=5,
            min_periods=5,
        )
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    # -----------------------------------------
    # Volatilidade 5 pregões
    #
    # 5 retornos diários dentro da janela.
    # -----------------------------------------

    result[
        "volatility_5d"
    ] = (
        result.groupby(
            "ticker"
        )[
            "daily_return"
        ]
        .rolling(
            window=5,
            min_periods=5,
        )
        .std()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    result[
        "volatility_5d_pct"
    ] = (
        result[
            "volatility_5d"
        ]
        * 100
    )

    # -----------------------------------------
    # Liquidez proxy:
    # média de quantidade de negócios
    # em 5 pregões.
    # -----------------------------------------

    result[
        "trades_avg_5d"
    ] = (
        grouped[
            "trades_quantity"
        ]
        .rolling(
            window=5,
            min_periods=5,
        )
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    # -----------------------------------------
    # Preço relativo à MA5
    # -----------------------------------------

    result[
        "price_to_ma5"
    ] = (
        result[
            "close_price"
        ]
        / result[
            "ma_5"
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


def select_gold_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Contrato da Gold histórica.
    """

    columns = [
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
        "daily_return",
        "daily_return_pct",
        "return_5d",
        "return_5d_pct",
        "ma_5",
        "volatility_5d",
        "volatility_5d_pct",
        "trades_avg_5d",
        "price_to_ma5",
        "observations_count",
        "ticker_resolution_status",
        "market_evidence_confidence",
    ]

    gold = dataframe[
        columns
    ].copy()

    gold[
        "gold_created_at"
    ] = datetime.now(
        timezone.utc
    )

    return gold


def validate_calculated_history(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida disponibilidade das features.
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

    feature_columns = [
        "daily_return",
        "return_5d",
        "ma_5",
        "volatility_5d",
        "trades_avg_5d",
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
            f"{column} disponível: "
            f"{available:,}"
        )

    # -----------------------------------------
    # Consistência estrutural
    # -----------------------------------------

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

    # -----------------------------------------
    # return_5d não pode existir antes da
    # sexta observação.
    # -----------------------------------------

    invalid_return_5d = dataframe[
        (
            dataframe[
                "observations_count"
            ]
            < 6
        )
        &
        dataframe[
            "return_5d"
        ].notna()
    ]

    if not invalid_return_5d.empty:
        raise ValueError(
            "return_5d encontrado antes "
            "da sexta observação."
        )

    # -----------------------------------------
    # volatility_5d também exige cinco
    # retornos, portanto pelo menos 6 preços.
    # -----------------------------------------

    invalid_volatility = dataframe[
        (
            dataframe[
                "observations_count"
            ]
            < 6
        )
        &
        dataframe[
            "volatility_5d"
        ].notna()
    ]

    if not invalid_volatility.empty:
        raise ValueError(
            "volatility_5d encontrada antes "
            "da sexta observação."
        )

    print(
        "\nData Quality das features aprovada."
    )


def save_gold(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste histórico Gold em Parquet.
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
) -> None:
    """
    Resumo final.
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
        f"{dataframe['trade_date'].nunique():,}"
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
        f"{(observations == dataframe['trade_date'].nunique()).sum():,}"
    )

    print(
        f"Linhas com return_5d: "
        f"{dataframe['return_5d'].notna().sum():,}"
    )

    print(
        f"Linhas com volatility_5d: "
        f"{dataframe['volatility_5d'].notna().sum():,}"
    )


def main() -> None:
    print(
        "Construindo Gold Analytics "
        "FII Price History..."
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

    history = (
        calculate_time_series_features(
            history
        )
    )

    history = (
        calculate_observation_count(
            history
        )
    )

    gold = select_gold_columns(
        history
    )

    validate_calculated_history(
        gold
    )

    save_gold(
        dataframe=gold,
        destination=GOLD_HISTORY_PATH,
    )

    print_history_summary(
        gold
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