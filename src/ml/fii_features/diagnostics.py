from __future__ import annotations

import argparse
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

DEFAULT_TICKERS = [
    "HGLG11",
    "MXRF11",
    "GARE11",
]


def parse_tickers(
    values: list[str] | None,
) -> list[str]:
    """
    Normaliza tickers recebidos pela CLI.
    """

    if not values:
        return DEFAULT_TICKERS.copy()

    tickers = [
        value.strip().upper()
        for value in values
        if value.strip()
    ]

    if not tickers:
        raise ValueError(
            "Nenhum ticker válido informado."
        )

    return list(
        dict.fromkeys(
            tickers
        )
    )


def load_features(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega a Gold ML.
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


def discover_windows(
    dataframe: pd.DataFrame,
) -> list[int]:
    """
    Descobre as janelas gravadas
    no próprio dataset ML.
    """

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
            "feature_windows não encontrada."
        )

    if len(values) > 1:
        raise ValueError(
            "Mais de uma configuração de "
            "feature_windows encontrada: "
            f"{values.tolist()}"
        )

    try:
        windows = sorted(
            {
                int(value.strip())
                for value in values[0].split(",")
                if value.strip()
            }
        )

    except ValueError as error:
        raise ValueError(
            "feature_windows inválida: "
            f"{values[0]}"
        ) from error

    if not windows:
        raise ValueError(
            "Nenhuma janela válida encontrada."
        )

    return windows


def build_diagnostic_columns(
    windows: list[int],
) -> list[str]:
    """
    Monta dinamicamente as colunas
    utilizadas no diagnóstico.
    """

    columns = [
        "feature_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        "daily_return",
        "daily_return_pct",
    ]

    for window in windows:
        columns.extend(
            [
                f"return_{window}d",
                f"return_{window}d_pct",
                f"ma_{window}",
                f"price_to_ma{window}",
                f"volatility_{window}d",
                f"volatility_{window}d_pct",
                f"trades_avg_{window}d",
            ]
        )

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

    columns.extend(
        [
            "observations_count",
            "feature_ready",
            "feature_version",
            "feature_windows",
        ]
    )

    return list(
        dict.fromkeys(
            columns
        )
    )


def validate_diagnostic_schema(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """
    Confirma que todas as features
    esperadas existem.
    """

    missing_columns = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas necessárias ao diagnóstico "
            f"não encontradas: {missing_columns}"
        )


def get_latest_date(
    dataframe: pd.DataFrame,
) -> pd.Timestamp:
    """
    Última feature_date disponível.
    """

    latest_date = dataframe[
        "feature_date"
    ].max()

    if pd.isna(
        latest_date
    ):
        raise ValueError(
            "Nenhuma feature_date válida."
        )

    return latest_date


def get_latest_ticker_rows(
    dataframe: pd.DataFrame,
    tickers: list[str],
    latest_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Seleciona os tickers pedidos
    na data mais recente.
    """

    result = dataframe[
        (
            dataframe[
                "feature_date"
            ]
            == latest_date
        )
        &
        (
            dataframe[
                "ticker"
            ].isin(
                tickers
            )
        )
    ].copy()

    return result.sort_values(
        "ticker"
    )


def print_dataset_summary(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Resumo geral da Gold ML.
    """

    print(
        "\n======================================"
    )
    print(
        "Diagnóstico Gold ML"
    )
    print(
        "======================================"
    )

    print(
        f"Feature version: "
        f"{dataframe['feature_version'].iloc[0]}"
    )

    print(
        f"Janelas: {windows}"
    )

    print(
        f"Período: "
        f"{dataframe['feature_date'].min().date()} "
        f"-> "
        f"{dataframe['feature_date'].max().date()}"
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
        f"{dataframe['feature_ready'].sum():,}"
    )


def print_ticker_diagnostic(
    row: pd.Series,
    windows: list[int],
) -> None:
    """
    Imprime diagnóstico legível
    de um único FII.
    """

    ticker = row[
        "ticker"
    ]

    print(
        "\n======================================"
    )

    print(
        f"{ticker}"
    )

    print(
        "======================================"
    )

    print(
        f"Data: "
        f"{row['feature_date'].date()}"
    )

    print(
        f"CNPJ: "
        f"{row['cnpj']}"
    )

    print(
        f"Código CVM: "
        f"{row['codigo_cvm']}"
    )

    print(
        f"Close: "
        f"{row['close_price']:.4f}"
    )

    print(
        f"Daily return: "
        f"{row['daily_return_pct']:.4f}%"
    )

    print(
        f"Observações: "
        f"{row['observations_count']}"
    )

    print(
        f"Feature ready: "
        f"{row['feature_ready']}"
    )

    print(
        "\n--- Janelas temporais ---"
    )

    for window in windows:
        print(
            f"\nJanela {window}:"
        )

        print(
            f"  return_{window}d: "
            f"{row[f'return_{window}d_pct']:.4f}%"
        )

        print(
            f"  ma_{window}: "
            f"{row[f'ma_{window}']:.4f}"
        )

        print(
            f"  price_to_ma{window}: "
            f"{row[f'price_to_ma{window}']:.6f}"
        )

        print(
            f"  volatility_{window}d: "
            f"{row[f'volatility_{window}d_pct']:.4f}%"
        )

        print(
            f"  trades_avg_{window}d: "
            f"{row[f'trades_avg_{window}d']:.2f}"
        )

    if len(
        windows
    ) >= 2:
        print(
            "\n--- Relações entre janelas ---"
        )

    for short_window, long_window in zip(
        windows,
        windows[1:],
    ):
        return_spread = row[
            (
                f"return_spread_"
                f"{short_window}d_"
                f"{long_window}d"
            )
        ]

        ma_ratio = row[
            (
                f"ma_ratio_"
                f"{short_window}_"
                f"{long_window}"
            )
        ]

        volatility_ratio = row[
            (
                f"volatility_ratio_"
                f"{short_window}d_"
                f"{long_window}d"
            )
        ]

        trades_ratio = row[
            (
                f"trades_ratio_"
                f"{short_window}d_"
                f"{long_window}d"
            )
        ]

        print(
            f"\n{short_window} vs "
            f"{long_window}:"
        )

        print(
            f"  return spread: "
            f"{return_spread * 100:.4f}%"
        )

        print(
            f"  MA ratio: "
            f"{ma_ratio:.6f}"
        )

        if pd.isna(
            volatility_ratio
        ):
            print(
                "  volatility ratio: NaN"
            )

        else:
            print(
                f"  volatility ratio: "
                f"{volatility_ratio:.6f}"
            )

        if pd.isna(
            trades_ratio
        ):
            print(
                "  trades ratio: NaN"
            )

        else:
            print(
                f"  trades ratio: "
                f"{trades_ratio:.6f}"
            )


def print_interpretation(
    row: pd.Series,
    windows: list[int],
) -> None:
    """
    Gera interpretação descritiva simples,
    sem fazer previsão nem recomendação.
    """

    ticker = row[
        "ticker"
    ]

    print(
        "\n--- Leitura descritiva ---"
    )

    for short_window, long_window in zip(
        windows,
        windows[1:],
    ):
        ma_ratio = row[
            (
                f"ma_ratio_"
                f"{short_window}_"
                f"{long_window}"
            )
        ]

        volatility_ratio = row[
            (
                f"volatility_ratio_"
                f"{short_window}d_"
                f"{long_window}d"
            )
        ]

        trades_ratio = row[
            (
                f"trades_ratio_"
                f"{short_window}d_"
                f"{long_window}d"
            )
        ]

        return_spread = row[
            (
                f"return_spread_"
                f"{short_window}d_"
                f"{long_window}d"
            )
        ]

        print(
            f"\n{ticker} | "
            f"{short_window} vs {long_window}"
        )

        if ma_ratio > 1:
            print(
                "  Média curta acima "
                "da média longa."
            )

        elif ma_ratio < 1:
            print(
                "  Média curta abaixo "
                "da média longa."
            )

        else:
            print(
                "  Médias praticamente iguais."
            )

        if return_spread > 0:
            print(
                "  Retorno curto relativamente "
                "mais forte que o longo."
            )

        elif return_spread < 0:
            print(
                "  Retorno curto relativamente "
                "mais fraco que o longo."
            )

        else:
            print(
                "  Retornos relativos equivalentes."
            )

        if pd.isna(
            volatility_ratio
        ):
            print(
                "  Regime relativo de volatilidade "
                "indefinido."
            )

        elif volatility_ratio > 1:
            print(
                "  Volatilidade recente acima "
                "da janela longa."
            )

        elif volatility_ratio < 1:
            print(
                "  Volatilidade recente abaixo "
                "da janela longa."
            )

        else:
            print(
                "  Volatilidades equivalentes."
            )

        if pd.isna(
            trades_ratio
        ):
            print(
                "  Regime relativo de atividade "
                "indefinido."
            )

        elif trades_ratio > 1:
            print(
                "  Atividade recente acima "
                "da média longa."
            )

        elif trades_ratio < 1:
            print(
                "  Atividade recente abaixo "
                "da média longa."
            )

        else:
            print(
                "  Atividade equivalente "
                "entre as janelas."
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnóstico das features "
            "da Gold ML."
        )
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help=(
            "Tickers para inspeção. "
            "Exemplo: --tickers "
            "HGLG11 MXRF11 GARE11"
        ),
    )

    args = parser.parse_args()

    tickers = parse_tickers(
        args.tickers
    )

    dataframe = load_features(
        ML_FEATURES_PATH
    )

    windows = discover_windows(
        dataframe
    )

    diagnostic_columns = (
        build_diagnostic_columns(
            windows
        )
    )

    validate_diagnostic_schema(
        dataframe=dataframe,
        columns=diagnostic_columns,
    )

    print_dataset_summary(
        dataframe=dataframe,
        windows=windows,
    )

    latest_date = get_latest_date(
        dataframe
    )

    print(
        f"\nData mais recente disponível: "
        f"{latest_date.date()}"
    )

    print(
        f"Tickers solicitados: "
        f"{tickers}"
    )

    rows = get_latest_ticker_rows(
        dataframe=dataframe,
        tickers=tickers,
        latest_date=latest_date,
    )

    found_tickers = set(
        rows[
            "ticker"
        ].tolist()
    )

    missing_tickers = [
        ticker
        for ticker in tickers
        if ticker not in found_tickers
    ]

    if missing_tickers:
        print(
            "\nTickers não encontrados "
            "na data mais recente:"
        )

        for ticker in missing_tickers:
            print(
                f"  {ticker}"
            )

    if rows.empty:
        raise ValueError(
            "Nenhum dos tickers solicitados "
            "foi encontrado."
        )

    for _, row in rows.iterrows():
        print_ticker_diagnostic(
            row=row,
            windows=windows,
        )

        print_interpretation(
            row=row,
            windows=windows,
        )

    print(
        "\n======================================"
    )

    print(
        "Diagnóstico concluído."
    )

    print(
        "======================================"
    )


if __name__ == "__main__":
    main()