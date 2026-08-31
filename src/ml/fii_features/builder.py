from __future__ import annotations

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


def load_price_history(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega o histórico Gold Analytics,
    fonte das features de ML.
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

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "close_price",
        "daily_return",
        "daily_return_pct",
        "return_5d",
        "return_5d_pct",
        "ma_5",
        "volatility_5d",
        "volatility_5d_pct",
        "price_to_ma5",
        "trades_quantity",
        "trades_avg_5d",
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
            f"no histórico: {missing_columns}"
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
) -> pd.DataFrame:
    """
    Constrói dataset de features ML v2.

    Todas as features utilizam apenas
    informações conhecidas até a feature_date.
    """

    features = history[
        [
            "trade_date",
            "ticker",
            "cnpj",
            "codigo_cvm",
            "close_price",
            "daily_return",
            "daily_return_pct",
            "return_5d",
            "return_5d_pct",
            "ma_5",
            "volatility_5d",
            "volatility_5d_pct",
            "price_to_ma5",
            "trades_quantity",
            "trades_avg_5d",
            "observations_count",
        ]
    ].copy()

    features = features.rename(
        columns={
            "trade_date": "feature_date",
        }
    )

    # -----------------------------------------
    # Feature readiness v2
    #
    # return_5d e volatility_5d exigem
    # pelo menos 6 preços históricos.
    # -----------------------------------------

    features[
        "feature_ready"
    ] = (
        (
            features[
                "observations_count"
            ]
            >= 6
        )
        &
        features[
            "daily_return"
        ].notna()
        &
        features[
            "return_5d"
        ].notna()
        &
        features[
            "ma_5"
        ].notna()
        &
        features[
            "volatility_5d"
        ].notna()
        &
        features[
            "price_to_ma5"
        ].notna()
        &
        features[
            "trades_avg_5d"
        ].notna()
    )

    return features


def validate_ml_features(
    dataframe: pd.DataFrame,
) -> None:
    """
    Data Quality da Gold ML v2.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - FII ML Features v2"
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

    # -----------------------------------------
    # Nenhuma linha com menos de 6
    # observações pode estar pronta.
    # -----------------------------------------

    invalid_ready = dataframe[
        (
            dataframe[
                "feature_ready"
            ]
        )
        &
        (
            dataframe[
                "observations_count"
            ]
            < 6
        )
    ]

    if not invalid_ready.empty:
        raise ValueError(
            "feature_ready=True encontrado "
            "com menos de 6 observações."
        )

    ready = dataframe[
        dataframe[
            "feature_ready"
        ]
    ]

    ready_required_columns = [
        "close_price",
        "daily_return",
        "return_5d",
        "ma_5",
        "volatility_5d",
        "price_to_ma5",
        "trades_quantity",
        "trades_avg_5d",
    ]

    if not ready.empty:
        ready_nulls = (
            ready[
                ready_required_columns
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

    print(
        "\nData Quality ML v2 aprovada."
    )


def add_metadata(
    dataframe: pd.DataFrame,
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
    ] = "v2"

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
        "Resumo Gold ML - FII Features v2"
    )
    print(
        "======================================"
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

    print(
        f"Return 5d disponível: "
        f"{dataframe['return_5d'].notna().sum():,}"
    )

    print(
        f"Volatilidade 5d disponível: "
        f"{dataframe['volatility_5d'].notna().sum():,}"
    )


def main() -> None:
    print(
        "Construindo Gold ML "
        "FII Features v2..."
    )

    history = load_price_history(
        PRICE_HISTORY_PATH
    )

    print(
        f"\nHistórico carregado: "
        f"{len(history):,} linhas"
    )

    features = build_ml_features(
        history
    )

    validate_ml_features(
        features
    )

    features = add_metadata(
        features
    )

    save_features(
        dataframe=features,
        destination=ML_FEATURES_PATH,
    )

    print_summary(
        features
    )

    print(
        "\nArquivo:"
    )

    print(
        ML_FEATURES_PATH
    )

    print(
        "\nGold ML "
        "FII Features v2 criada "
        "com sucesso."
    )


if __name__ == "__main__":
    main()