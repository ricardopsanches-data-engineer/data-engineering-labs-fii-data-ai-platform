from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
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


FEATURE_VERSION = "v6"

EXPECTED_PRICE_HISTORY_VERSION = "v2"

EXPECTED_PRICE_HISTORY_SOURCE = (
    "FII_CORPORATE_ACTION_ADJUSTED_PRICES"
)

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)


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
            "a coluna feature_windows."
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
        "Carregando histórico analítico: "
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
            "Gold Analytics: "
            f"{discovered_windows}"
        )

        return discovered_windows

    override_windows = normalize_windows(
        override_windows
    )

    print(
        "Janelas da Gold Analytics: "
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
            "Disponíveis: "
            f"{discovered_windows}"
        )

    return override_windows


def validate_history_semantics(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida explicitamente a versão e
    semântica econômica do Price History.

    O ML Features v6 não aceita o histórico
    RAW antigo.
    """

    required_metadata_columns = [
        "price_history_version",
        "price_history_source",
        "price_semantics",
        "return_semantics",
    ]

    missing_columns = [
        column
        for column in required_metadata_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price History não possui "
            "metadados semânticos necessários "
            "para ML Features v6: "
            f"{missing_columns}"
        )

    versions = sorted(
        dataframe[
            "price_history_version"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    sources = sorted(
        dataframe[
            "price_history_source"
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

    expected_versions = [
        EXPECTED_PRICE_HISTORY_VERSION,
    ]

    expected_sources = [
        EXPECTED_PRICE_HISTORY_SOURCE,
    ]

    expected_price_semantics = [
        EXPECTED_PRICE_SEMANTICS,
    ]

    expected_return_semantics = [
        EXPECTED_RETURN_SEMANTICS,
    ]

    print(
        "\n======================================"
    )
    print(
        "Contrato Semântico - Price History"
    )
    print(
        "======================================"
    )

    print(
        f"Version: {versions}"
    )

    print(
        f"Source: {sources}"
    )

    print(
        f"Price semantics: "
        f"{price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{return_semantics}"
    )

    if versions != expected_versions:
        raise ValueError(
            "ML Features v6 exige "
            f"Price History "
            f"{EXPECTED_PRICE_HISTORY_VERSION}. "
            f"Encontrado: {versions}"
        )

    if sources != expected_sources:
        raise ValueError(
            "Price History possui "
            "source incompatível: "
            f"{sources}"
        )

    if (
        price_semantics
        != expected_price_semantics
    ):
        raise ValueError(
            "Price History possui "
            "price_semantics incompatível: "
            f"{price_semantics}"
        )

    if (
        return_semantics
        != expected_return_semantics
    ):
        raise ValueError(
            "Price History possui "
            "return_semantics incompatível: "
            f"{return_semantics}"
        )

    print(
        "\nContrato semântico aprovado."
    )


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
        "close_price_raw",
        "close_price_adjusted",

        "trades_quantity",

        "daily_return",
        "daily_return_raw",
        "daily_return_economic",

        "daily_return_pct",

        "observations_count",
        "feature_windows",

        "price_history_version",
        "price_history_source",
        "price_semantics",
        "return_semantics",
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

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    identity_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
    ]

    identity_nulls = int(
        dataframe[
            identity_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    close_alias_mismatch = int(
        (
            ~np.isclose(
                dataframe[
                    "close_price"
                ],
                dataframe[
                    "close_price_adjusted"
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    return_mask = (
        dataframe[
            "daily_return"
        ].notna()
        &
        dataframe[
            "daily_return_economic"
        ].notna()
    )

    return_alias_mismatch = int(
        (
            ~np.isclose(
                dataframe.loc[
                    return_mask,
                    "daily_return",
                ],
                dataframe.loc[
                    return_mask,
                    "daily_return_economic",
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Price History Input"
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
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Nulos de identidade: "
        f"{identity_nulls:,}"
    )

    print(
        "close_price != "
        "close_price_adjusted: "
        f"{close_alias_mismatch:,}"
    )

    print(
        "daily_return != "
        "daily_return_economic: "
        f"{return_alias_mismatch:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price History possui duplicidades."
        )

    if identity_nulls > 0:
        raise ValueError(
            "Price History possui "
            "identidade nula."
        )

    if close_alias_mismatch > 0:
        raise ValueError(
            "Price History possui "
            "close_price fora da "
            "semântica ajustada."
        )

    if return_alias_mismatch > 0:
        raise ValueError(
            "Price History possui "
            "daily_return fora da "
            "semântica econômica."
        )

    print(
        "\nData Quality do input aprovada."
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
    """

    result = dataframe.copy()

    if len(windows) < 2:
        return result

    for short_window, long_window in zip(
        windows,
        windows[1:],
    ):

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
    Constrói o dataset ML.

    As colunas usadas como features
    continuam compatíveis com o contrato
    anterior, porém agora derivam do
    Price History econômico v2.

    Colunas RAW adicionais permanecem
    apenas para auditoria.
    """

    base_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",

        "close_price",
        "close_price_raw",
        "close_price_adjusted",

        "trades_quantity",

        "daily_return",
        "daily_return_raw",
        "daily_return_economic",
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

    features = (
        calculate_cross_window_features(
            dataframe=features,
            windows=windows,
        )
    )

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
        "\nDuplicidades "
        "(feature_date + ticker): "
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
        raise ValueError(
            "Nenhuma linha feature_ready "
            "encontrada."
        )

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
                "com menos de "
                f"{minimum_observations} "
                "observações para a janela "
                f"{window}."
            )

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
            available = int(
                ready[
                    column
                ]
                .notna()
                .sum()
            )

            missing = int(
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

    numeric_feature_columns = [
        "daily_return",
    ]

    for window in windows:
        numeric_feature_columns.extend(
            [
                f"return_{window}d",
                f"ma_{window}",
                f"volatility_{window}d",
                f"trades_avg_{window}d",
                f"price_to_ma{window}",
            ]
        )

    numeric_feature_columns.extend(
        build_cross_window_feature_columns(
            windows
        )
    )

    non_finite_counts = {}

    for column in numeric_feature_columns:

        if column not in ready.columns:
            continue

        non_finite_count = int(
            (
                ready[
                    column
                ].notna()
                &
                ~np.isfinite(
                    ready[
                        column
                    ]
                )
            ).sum()
        )

        non_finite_counts[
            column
        ] = non_finite_count

    total_non_finite = sum(
        non_finite_counts.values()
    )

    print(
        "\nValores não finitos "
        "em linhas feature_ready:"
    )

    print(
        f"  Total: "
        f"{total_non_finite:,}"
    )

    if total_non_finite > 0:
        offenders = {
            column: count
            for column, count
            in non_finite_counts.items()
            if count > 0
        }

        raise ValueError(
            "Features ML possuem valores "
            "não finitos: "
            f"{offenders}"
        )

    print(
        "\nData Quality ML aprovada."
    )


def add_metadata(
    dataframe: pd.DataFrame,
    history: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Adiciona metadados técnicos e
    semânticos.

    A semântica é herdada do Price History
    e persistida explicitamente na Gold ML.
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

    result[
        "source_price_history_version"
    ] = EXPECTED_PRICE_HISTORY_VERSION

    result[
        "source_price_history_source"
    ] = EXPECTED_PRICE_HISTORY_SOURCE

    result[
        "price_semantics"
    ] = EXPECTED_PRICE_SEMANTICS

    result[
        "return_semantics"
    ] = EXPECTED_RETURN_SEMANTICS

    result[
        "feature_price_semantics"
    ] = (
        "STRUCTURALLY_ADJUSTED_PRICE"
    )

    result[
        "feature_return_semantics"
    ] = (
        "ECONOMIC_RETURN"
    )

    return result


def validate_feature_metadata(
    dataframe: pd.DataFrame,
) -> None:
    """
    Confirma que a semântica econômica
    foi persistida no artefato ML.
    """

    expected_values = {
        "feature_version": FEATURE_VERSION,
        "source_price_history_version": (
            EXPECTED_PRICE_HISTORY_VERSION
        ),
        "source_price_history_source": (
            EXPECTED_PRICE_HISTORY_SOURCE
        ),
        "price_semantics": (
            EXPECTED_PRICE_SEMANTICS
        ),
        "return_semantics": (
            EXPECTED_RETURN_SEMANTICS
        ),
        "feature_price_semantics": (
            "STRUCTURALLY_ADJUSTED_PRICE"
        ),
        "feature_return_semantics": (
            "ECONOMIC_RETURN"
        ),
    }

    print(
        "\n======================================"
    )
    print(
        "Validação - Metadata ML"
    )
    print(
        "======================================"
    )

    for column, expected in (
        expected_values.items()
    ):
        if column not in dataframe.columns:
            raise ValueError(
                "Metadata ausente: "
                f"{column}"
            )

        values = (
            dataframe[
                column
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        print(
            f"{column}: "
            f"{values}"
        )

        if values != [
            str(expected)
        ]:
            raise ValueError(
                f"{column} possui valor "
                "incompatível. "
                f"Esperado: {expected}. "
                f"Encontrado: {values}"
            )

    print(
        "\nMetadata ML aprovada."
    )


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
        "Source Price History: "
        f"{EXPECTED_PRICE_HISTORY_VERSION}"
    )

    print(
        "Price semantics: "
        f"{EXPECTED_PRICE_SEMANTICS}"
    )

    print(
        "Return semantics: "
        f"{EXPECTED_RETURN_SEMANTICS}"
    )

    print(
        f"Janelas: "
        f"{windows}"
    )

    print(
        f"Período total: "
        f"{dataframe['feature_date'].min().date()} "
        "-> "
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
        "uma linha pronta: "
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
            "FII Features v6."
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

    print(
        f"Feature version: "
        f"{FEATURE_VERSION}"
    )

    history = load_price_history(
        PRICE_HISTORY_PATH
    )

    print(
        "\nHistórico carregado: "
        f"{len(history):,} linhas"
    )

    validate_history_semantics(
        history
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
        history=history,
        windows=windows,
    )

    validate_feature_metadata(
        features
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

    print(
        "As features agora herdam "
        "explicitamente a semântica econômica "
        "do Price History v2."
    )

    print(
        "close_price usado pelo ML é "
        "estruturalmente ajustado."
    )

    print(
        "daily_return e retornos rolling "
        "possuem semântica econômica."
    )

    print(
        "Colunas RAW foram preservadas "
        "somente para auditoria."
    )


if __name__ == "__main__":
    main()