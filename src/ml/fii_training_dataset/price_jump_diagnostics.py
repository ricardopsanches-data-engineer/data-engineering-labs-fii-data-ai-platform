from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ============================================================
# Paths
# ============================================================

VALIDATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_temporal_split"
    / "validation.parquet"
)

PRICE_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_history"
    / "fii_price_history.parquet"
)

ADJUSTED_PRICES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
    / "fii_corporate_action_adjusted_prices.parquet"
)

DISCONTINUITIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_price_discontinuities"
    / "fii_price_discontinuities.parquet"
)

PRICE_QUALITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "quality"
    / "fii_price_quality"
    / "fii_price_quality.parquet"
)


# ============================================================
# Contract
# ============================================================

DIAGNOSTICS_VERSION = "v2"

EXPECTED_SPLIT_VERSION = "v2"

EXPECTED_TRAINING_DATASET_VERSION = "v3"

EXPECTED_PRICE_HISTORY_VERSION = "v2"

EXPECTED_TARGET_HORIZON = 5

EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)

EXPECTED_TARGET_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)


# ============================================================
# Audit policy
# ============================================================

FOCUS_TICKERS = [
    "KNPR11",
    "MFII11",
]

AUDIT_NEGATIVE_THRESHOLD = -0.20

CONTEXT_TRADING_ROWS = 5

LARGE_DAILY_MOVE_THRESHOLD = 0.20


# ============================================================
# Generic helpers
# ============================================================

def get_unique_string(
    dataframe: pd.DataFrame,
    column: str,
    dataset_name: str,
) -> str:
    """
    Obtém exatamente um valor textual
    de metadata.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"{dataset_name}: "
            f"coluna {column} ausente."
        )

    values = (
        dataframe[
            column
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    if len(values) != 1:
        raise ValueError(
            f"{dataset_name}: "
            f"{column} ambígua: "
            f"{values}"
        )

    return values[0]


def get_unique_int(
    dataframe: pd.DataFrame,
    column: str,
    dataset_name: str,
) -> int:
    """
    Obtém exatamente um inteiro
    de metadata.
    """

    if column not in dataframe.columns:
        raise ValueError(
            f"{dataset_name}: "
            f"coluna {column} ausente."
        )

    values = (
        dataframe[
            column
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if len(values) != 1:
        raise ValueError(
            f"{dataset_name}: "
            f"{column} ambígua: "
            f"{values}"
        )

    return int(
        values[0]
    )


def normalize_ticker(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza ticker.
    """

    result = dataframe.copy()

    if "ticker" in result.columns:
        result[
            "ticker"
        ] = (
            result[
                "ticker"
            ]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    return result


def resolve_date_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    dataset_name: str,
) -> str:
    """
    Localiza coluna temporal entre
    nomes conhecidos.
    """

    for column in candidates:
        if column in dataframe.columns:
            return column

    raise ValueError(
        f"{dataset_name}: nenhuma coluna "
        "temporal encontrada entre "
        f"{candidates}."
    )


def available_columns(
    dataframe: pd.DataFrame,
    requested: list[str],
) -> list[str]:
    """
    Retorna somente colunas existentes.

    Útil em camadas de auditoria que podem
    possuir metadata adicional.
    """

    return [
        column
        for column in requested
        if column in dataframe.columns
    ]


# ============================================================
# Loaders
# ============================================================

def load_validation() -> pd.DataFrame:
    """
    Carrega somente VALIDATION.

    TEST deliberadamente não é carregado.
    """

    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            "Validation não encontrada: "
            f"{VALIDATION_PATH}"
        )

    dataframe = pd.read_parquet(
        VALIDATION_PATH
    )

    dataframe = normalize_ticker(
        dataframe
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

    print(
        "Validation: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def load_price_history() -> pd.DataFrame:
    """
    Price History v2.

    Esta é a fonte canônica das features
    temporais econômicas.
    """

    if not PRICE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "Price History não encontrado: "
            f"{PRICE_HISTORY_PATH}"
        )

    dataframe = pd.read_parquet(
        PRICE_HISTORY_PATH
    )

    dataframe = normalize_ticker(
        dataframe
    )

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
        ]
    )

    print(
        "Price History: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def load_adjusted_prices() -> pd.DataFrame:
    """
    Carrega a camada de preços RAW,
    estruturalmente ajustados e econômicos.
    """

    if not ADJUSTED_PRICES_PATH.exists():
        raise FileNotFoundError(
            "Adjusted Prices não encontrado: "
            f"{ADJUSTED_PRICES_PATH}"
        )

    dataframe = pd.read_parquet(
        ADJUSTED_PRICES_PATH
    )

    dataframe = normalize_ticker(
        dataframe
    )

    date_column = resolve_date_column(
        dataframe=dataframe,
        candidates=[
            "trade_date",
            "date",
        ],
        dataset_name="Adjusted Prices",
    )

    dataframe[
        date_column
    ] = pd.to_datetime(
        dataframe[
            date_column
        ]
    )

    if date_column != "trade_date":
        dataframe = dataframe.rename(
            columns={
                date_column: "trade_date",
            }
        )

    print(
        "Adjusted Prices: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


def load_discontinuities() -> pd.DataFrame:
    """
    Carrega registro governado de
    descontinuidades.

    O schema é mantido inteiro para
    auditoria.
    """

    if not DISCONTINUITIES_PATH.exists():
        raise FileNotFoundError(
            "Discontinuities não encontrado: "
            f"{DISCONTINUITIES_PATH}"
        )

    dataframe = pd.read_parquet(
        DISCONTINUITIES_PATH
    )

    dataframe = normalize_ticker(
        dataframe
    )

    date_column = resolve_date_column(
        dataframe=dataframe,
        candidates=[
            "trade_date",
            "event_date",
            "date",
        ],
        dataset_name="Discontinuities",
    )

    dataframe[
        date_column
    ] = pd.to_datetime(
        dataframe[
            date_column
        ]
    )

    if date_column != "trade_date":
        dataframe = dataframe.rename(
            columns={
                date_column: "trade_date",
            }
        )

    print(
        "Discontinuities: "
        f"{len(dataframe):,} eventos"
    )

    return dataframe


def load_price_quality() -> pd.DataFrame:
    """
    Carrega camada governada de
    qualidade de preço.
    """

    if not PRICE_QUALITY_PATH.exists():
        raise FileNotFoundError(
            "Price Quality não encontrado: "
            f"{PRICE_QUALITY_PATH}"
        )

    dataframe = pd.read_parquet(
        PRICE_QUALITY_PATH
    )

    dataframe = normalize_ticker(
        dataframe
    )

    date_column = resolve_date_column(
        dataframe=dataframe,
        candidates=[
            "trade_date",
            "feature_date",
            "date",
        ],
        dataset_name="Price Quality",
    )

    dataframe[
        date_column
    ] = pd.to_datetime(
        dataframe[
            date_column
        ]
    )

    if date_column != "trade_date":
        dataframe = dataframe.rename(
            columns={
                date_column: "trade_date",
            }
        )

    print(
        "Price Quality: "
        f"{len(dataframe):,} linhas"
    )

    return dataframe


# ============================================================
# Contract validation
# ============================================================

def discover_target_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Descobre target econômico oficial.
    """

    target_name = get_unique_string(
        dataframe=dataframe,
        column="target_name",
        dataset_name="VALIDATION",
    )

    if target_name not in dataframe.columns:
        raise ValueError(
            "Target declarado não existe: "
            f"{target_name}"
        )

    return target_name


def validate_validation_contract(
    dataframe: pd.DataFrame,
    target_column: str,
) -> None:
    """
    Valida VALIDATION atual.
    """

    required_columns = [
        "feature_date",
        "target_date",
        "ticker",

        target_column,

        "target_horizon",
        "target_horizon_semantics",
        "target_return_semantics",

        "split_name",
        "split_version",

        "training_dataset_version",

        "feature_ready",
        "ml_eligible",

        "price_semantics",
        "return_semantics",
    ]

    missing = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing:
        raise ValueError(
            "VALIDATION possui colunas "
            f"ausentes: {missing}"
        )

    split_name = get_unique_string(
        dataframe,
        "split_name",
        "VALIDATION",
    )

    split_version = get_unique_string(
        dataframe,
        "split_version",
        "VALIDATION",
    )

    training_version = get_unique_string(
        dataframe,
        "training_dataset_version",
        "VALIDATION",
    )

    horizon = get_unique_int(
        dataframe,
        "target_horizon",
        "VALIDATION",
    )

    horizon_semantics = get_unique_string(
        dataframe,
        "target_horizon_semantics",
        "VALIDATION",
    )

    target_semantics = get_unique_string(
        dataframe,
        "target_return_semantics",
        "VALIDATION",
    )

    price_semantics = get_unique_string(
        dataframe,
        "price_semantics",
        "VALIDATION",
    )

    return_semantics = get_unique_string(
        dataframe,
        "return_semantics",
        "VALIDATION",
    )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    target_non_finite = int(
        (
            ~np.isfinite(
                dataframe[
                    target_column
                ]
                .astype(float)
            )
        ).sum()
    )

    feature_ready_false = int(
        (
            ~dataframe[
                "feature_ready"
            ]
        ).sum()
    )

    ml_eligible_false = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Contrato VALIDATION"
    )
    print(
        "======================================"
    )

    print(
        f"Split: {split_name}"
    )

    print(
        f"Split version: {split_version}"
    )

    print(
        "Training Dataset: "
        f"{training_version}"
    )

    print(
        f"Target horizon: {horizon}"
    )

    print(
        "Target semantics: "
        f"{target_semantics}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Target não finito: "
        f"{target_non_finite:,}"
    )

    print(
        "feature_ready=False: "
        f"{feature_ready_false:,}"
    )

    print(
        "ml_eligible=False: "
        f"{ml_eligible_false:,}"
    )

    if split_name != "validation":
        raise ValueError(
            "Arquivo não representa "
            "split validation."
        )

    if split_version != EXPECTED_SPLIT_VERSION:
        raise ValueError(
            "Price Jump Diagnostics v2 exige "
            f"Temporal Split "
            f"{EXPECTED_SPLIT_VERSION}."
        )

    if (
        training_version
        != EXPECTED_TRAINING_DATASET_VERSION
    ):
        raise ValueError(
            "Price Jump Diagnostics v2 exige "
            f"Training Dataset "
            f"{EXPECTED_TRAINING_DATASET_VERSION}."
        )

    if horizon != EXPECTED_TARGET_HORIZON:
        raise ValueError(
            "Target horizon incompatível."
        )

    if (
        horizon_semantics
        != EXPECTED_TARGET_HORIZON_SEMANTICS
    ):
        raise ValueError(
            "Target horizon semantics "
            "incompatível."
        )

    if (
        target_semantics
        != EXPECTED_TARGET_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Target econômico obrigatório."
        )

    if (
        price_semantics
        != EXPECTED_PRICE_SEMANTICS
    ):
        raise ValueError(
            "Price semantics incompatível."
        )

    if (
        return_semantics
        != EXPECTED_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Return semantics incompatível."
        )

    if duplicate_count > 0:
        raise ValueError(
            "VALIDATION possui duplicidades."
        )

    if target_non_finite > 0:
        raise ValueError(
            "VALIDATION possui targets "
            "não finitos."
        )

    if feature_ready_false > 0:
        raise ValueError(
            "VALIDATION possui "
            "feature_ready=False."
        )

    if ml_eligible_false > 0:
        raise ValueError(
            "VALIDATION possui "
            "ml_eligible=False."
        )


def validate_price_history_contract(
    dataframe: pd.DataFrame,
) -> None:
    """
    Confirma Price History v2 econômico.
    """

    version = get_unique_string(
        dataframe,
        "price_history_version",
        "Price History",
    )

    source = get_unique_string(
        dataframe,
        "price_history_source",
        "Price History",
    )

    price_semantics = get_unique_string(
        dataframe,
        "price_semantics",
        "Price History",
    )

    return_semantics = get_unique_string(
        dataframe,
        "return_semantics",
        "Price History",
    )

    print(
        "\n======================================"
    )
    print(
        "Contrato Price History"
    )
    print(
        "======================================"
    )

    print(
        f"Version: {version}"
    )

    print(
        f"Source: {source}"
    )

    print(
        f"Price semantics: "
        f"{price_semantics}"
    )

    print(
        f"Return semantics: "
        f"{return_semantics}"
    )

    if version != EXPECTED_PRICE_HISTORY_VERSION:
        raise ValueError(
            "Price History v2 obrigatório."
        )

    if (
        price_semantics
        != EXPECTED_PRICE_SEMANTICS
    ):
        raise ValueError(
            "Price History possui "
            "price semantics incompatível."
        )

    if (
        return_semantics
        != EXPECTED_RETURN_SEMANTICS
    ):
        raise ValueError(
            "Price History possui "
            "return semantics incompatível."
        )


# ============================================================
# Audit sample selection
# ============================================================

def build_audit_samples(
    validation: pd.DataFrame,
    target_column: str,
) -> pd.DataFrame:
    """
    Seleciona:

    1. KNPR11 e MFII11;
    2. qualquer outro sample
       com target <= -20%.

    Remove duplicações.
    """

    focus_mask = (
        validation[
            "ticker"
        ]
        .isin(
            FOCUS_TICKERS
        )
    )

    extreme_mask = (
        validation[
            target_column
        ]
        <= AUDIT_NEGATIVE_THRESHOLD
    )

    samples = validation[
        focus_mask
        | extreme_mask
    ].copy()

    samples = (
        samples
        .sort_values(
            [
                "ticker",
                "feature_date",
            ]
        )
        .drop_duplicates(
            subset=[
                "ticker",
                "feature_date",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    print(
        "\n======================================"
    )
    print(
        "Universo da auditoria"
    )
    print(
        "======================================"
    )

    print(
        f"Samples: "
        f"{len(samples):,}"
    )

    print(
        f"Tickers: "
        f"{samples['ticker'].nunique():,}"
    )

    print(
        "Focus tickers:"
    )

    for ticker in FOCUS_TICKERS:
        count = int(
            (
                samples[
                    "ticker"
                ]
                == ticker
            ).sum()
        )

        print(
            f"  {ticker}: "
            f"{count:,}"
        )

    extreme_count = int(
        (
            samples[
                target_column
            ]
            <= AUDIT_NEGATIVE_THRESHOLD
        ).sum()
    )

    print(
        "Samples target <= -20%: "
        f"{extreme_count:,}"
    )

    return samples


# ============================================================
# Context path
# ============================================================

def build_ticker_context(
    price_history: pd.DataFrame,
    ticker: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Inclui algumas observações antes
    e depois da janela supervisionada.

    Isso evita olhar apenas feature_date
    -> target_date isoladamente.
    """

    ticker_history = (
        price_history[
            price_history[
                "ticker"
            ]
            == ticker
        ]
        .sort_values(
            "trade_date"
        )
        .reset_index(
            drop=True
        )
    )

    if ticker_history.empty:
        return ticker_history

    inside_mask = (
        (
            ticker_history[
                "trade_date"
            ]
            >= start_date
        )
        &
        (
            ticker_history[
                "trade_date"
            ]
            <= end_date
        )
    )

    positions = np.flatnonzero(
        inside_mask.to_numpy()
    )

    if len(positions) == 0:
        return ticker_history.iloc[
            0:0
        ].copy()

    first_position = max(
        int(
            positions.min()
        )
        - CONTEXT_TRADING_ROWS,
        0,
    )

    last_position = min(
        int(
            positions.max()
        )
        + CONTEXT_TRADING_ROWS
        + 1,
        len(
            ticker_history
        ),
    )

    return (
        ticker_history
        .iloc[
            first_position:
            last_position
        ]
        .copy()
    )


# ============================================================
# Layer filtering
# ============================================================

def filter_period(
    dataframe: pd.DataFrame,
    ticker: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Filtra ticker + período.
    """

    return (
        dataframe[
            (
                dataframe[
                    "ticker"
                ]
                == ticker
            )
            &
            (
                dataframe[
                    "trade_date"
                ]
                >= start_date
            )
            &
            (
                dataframe[
                    "trade_date"
                ]
                <= end_date
            )
        ]
        .sort_values(
            "trade_date"
        )
        .copy()
    )


# ============================================================
# Diagnostics
# ============================================================

def print_price_history_path(
    dataframe: pd.DataFrame,
    feature_date: pd.Timestamp,
    target_date: pd.Timestamp,
) -> None:
    """
    Mostra trajetória econômica canônica.
    """

    requested = [
        "trade_date",

        "close_price",

        "close_price_raw",
        "close_price_adjusted",

        "daily_return",
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        "return_5d",
        "return_10d",
        "return_20d",

        "volatility_5d",
        "volatility_10d",
        "volatility_20d",
    ]

    columns = available_columns(
        dataframe,
        requested,
    )

    display = dataframe[
        columns
    ].copy()

    if "trade_date" in display.columns:
        display[
            "inside_target_window"
        ] = (
            (
                display[
                    "trade_date"
                ]
                > feature_date
            )
            &
            (
                display[
                    "trade_date"
                ]
                <= target_date
            )
        )

    return_columns = [
        column
        for column in display.columns
        if (
            "return" in column
            and column
            != "return_semantics"
        )
    ]

    for column in return_columns:
        if pd.api.types.is_numeric_dtype(
            display[
                column
            ]
        ):
            display[
                column
            ] = (
                display[
                    column
                ]
                * 100
            )

    print(
        "\nPrice History v2:"
    )

    print(
        display.to_string(
            index=False,
        )
    )


def print_adjusted_price_path(
    dataframe: pd.DataFrame,
) -> None:
    """
    Mostra diferenças RAW x ajustado
    x econômico diretamente na camada
    de corporate actions.
    """

    requested = [
        "trade_date",

        "open_price_raw",
        "high_price_raw",
        "low_price_raw",
        "average_price_raw",
        "close_price_raw",

        "open_price_adjusted",
        "high_price_adjusted",
        "low_price_adjusted",
        "average_price_adjusted",
        "close_price_adjusted",

        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",

        "structural_adjustment_factor",

        "corporate_action_applied",
        "event_type",
        "review_status",
    ]

    columns = available_columns(
        dataframe,
        requested,
    )

    print(
        "\nAdjusted Prices:"
    )

    if dataframe.empty:
        print(
            "  Nenhuma linha no período."
        )
        return

    if not columns:
        print(
            "  Nenhuma coluna de auditoria "
            "reconhecida."
        )
        return

    print(
        dataframe[
            columns
        ].to_string(
            index=False,
        )
    )


def print_discontinuity_events(
    dataframe: pd.DataFrame,
) -> None:
    """
    Mostra candidatos/eventos governados
    existentes no período.
    """

    print(
        "\nDiscontinuities:"
    )

    if dataframe.empty:
        print(
            "  Nenhum evento registrado "
            "no período."
        )
        return

    preferred_columns = [
        "trade_date",
        "ticker",

        "previous_close",
        "close_price",

        "daily_return",
        "daily_return_pct",

        "price_factor",
        "nearest_common_factor",
        "factor_relative_error",

        "event_type",
        "review_status",

        "quantity_factor",
        "adjustment_factor",
        "cash_flow_per_unit",

        "review_note",
        "review_reason",
    ]

    columns = available_columns(
        dataframe,
        preferred_columns,
    )

    if not columns:
        columns = list(
            dataframe.columns
        )

    print(
        dataframe[
            columns
        ].to_string(
            index=False,
        )
    )


def print_quality_path(
    dataframe: pd.DataFrame,
) -> None:
    """
    Mostra governança de qualidade
    no período.
    """

    print(
        "\nPrice Quality:"
    )

    if dataframe.empty:
        print(
            "  Nenhuma linha no período."
        )
        return

    preferred_columns = [
        "trade_date",
        "ticker",

        "ml_quality_status",
        "review_status_on_date",

        "extreme_return_flag",
        "low_price_flag",

        "short_gap_flag",
        "medium_gap_flag",
        "long_gap_flag",

        "pending_corporate_action_flag",
        "confirmed_corporate_action_flag",

        "micro_liquidity_flag",
    ]

    columns = available_columns(
        dataframe,
        preferred_columns,
    )

    if not columns:
        columns = list(
            dataframe.columns
        )

    print(
        dataframe[
            columns
        ].to_string(
            index=False,
        )
    )


def calculate_path_metrics(
    path: pd.DataFrame,
) -> dict[str, float | int]:
    """
    Resume comportamento do caminho
    econômico.
    """

    result: dict[
        str,
        float | int
    ] = {
        "rows": len(path),
        "large_raw_moves": 0,
        "large_economic_moves": 0,
        "max_abs_raw_return": np.nan,
        "max_abs_economic_return": np.nan,
    }

    if path.empty:
        return result

    if (
        "daily_return_raw"
        in path.columns
    ):
        raw = pd.to_numeric(
            path[
                "daily_return_raw"
            ],
            errors="coerce",
        )

        finite_raw = raw[
            raw.notna()
            &
            np.isfinite(
                raw
            )
        ]

        if not finite_raw.empty:
            result[
                "large_raw_moves"
            ] = int(
                (
                    finite_raw.abs()
                    >= LARGE_DAILY_MOVE_THRESHOLD
                ).sum()
            )

            result[
                "max_abs_raw_return"
            ] = float(
                finite_raw.abs().max()
            )

    if (
        "daily_return_economic"
        in path.columns
    ):
        economic = pd.to_numeric(
            path[
                "daily_return_economic"
            ],
            errors="coerce",
        )

        finite_economic = economic[
            economic.notna()
            &
            np.isfinite(
                economic
            )
        ]

        if not finite_economic.empty:
            result[
                "large_economic_moves"
            ] = int(
                (
                    finite_economic.abs()
                    >= LARGE_DAILY_MOVE_THRESHOLD
                ).sum()
            )

            result[
                "max_abs_economic_return"
            ] = float(
                finite_economic.abs().max()
            )

    return result


def classify_audit(
    adjusted_path: pd.DataFrame,
    discontinuities: pd.DataFrame,
    quality: pd.DataFrame,
) -> str:
    """
    Classificação operacional.

    Ela NÃO altera dados e NÃO substitui
    revisão humana.
    """

    confirmed_event = False
    pending_event = False
    rejected_event = False

    review_columns = [
        column
        for column in [
            "review_status",
            "review_status_on_date",
        ]
        if column in (
            set(
                discontinuities.columns
            )
            | set(
                quality.columns
            )
        )
    ]

    for dataframe in [
        discontinuities,
        quality,
    ]:
        for column in review_columns:
            if column not in dataframe.columns:
                continue

            statuses = (
                dataframe[
                    column
                ]
                .dropna()
                .astype(str)
                .str.upper()
                .tolist()
            )

            confirmed_event = (
                confirmed_event
                or "CONFIRMED" in statuses
            )

            pending_event = (
                pending_event
                or "PENDING_REVIEW" in statuses
            )

            rejected_event = (
                rejected_event
                or "REJECTED" in statuses
            )

    if pending_event:
        return "REVIEW_REQUIRED_PENDING_EVENT"

    if confirmed_event:
        return "KNOWN_CORPORATE_ACTION"

    metrics = calculate_path_metrics(
        adjusted_path
    )

    if (
        metrics[
            "large_economic_moves"
        ]
        > 0
    ):
        return "LARGE_ECONOMIC_MARKET_MOVE"

    if (
        metrics[
            "large_raw_moves"
        ]
        > 0
    ):
        if rejected_event:
            return (
                "LARGE_RAW_MOVE_REJECTED_AS_"
                "CORPORATE_ACTION"
            )

        return (
            "LARGE_RAW_MOVE_WITHOUT_"
            "CONFIRMED_ACTION"
        )

    return "NO_SINGLE_LARGE_DAILY_MOVE"


# ============================================================
# Per-sample audit
# ============================================================

def audit_sample(
    row: pd.Series,
    target_column: str,
    price_history: pd.DataFrame,
    adjusted_prices: pd.DataFrame,
    discontinuities: pd.DataFrame,
    price_quality: pd.DataFrame,
) -> str:
    """
    Audita uma sample supervisionada.
    """

    ticker = str(
        row[
            "ticker"
        ]
    )

    feature_date = pd.Timestamp(
        row[
            "feature_date"
        ]
    )

    target_date = pd.Timestamp(
        row[
            "target_date"
        ]
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        f"{ticker} | "
        f"{feature_date.date()} "
        f"-> "
        f"{target_date.date()}"
    )

    print(
        "============================================================"
    )

    print(
        f"Target econômico T+5: "
        f"{row[target_column] * 100:.4f}%"
    )

    if (
        "target_price_return_next_5d"
        in row.index
    ):
        print(
            "Retorno somente de preço T+5: "
            f"{row['target_price_return_next_5d'] * 100:.4f}%"
        )

    if (
        "target_economic_vs_price_difference"
        in row.index
    ):
        print(
            "Diferença economic - price: "
            f"{row['target_economic_vs_price_difference'] * 100:+.4f} p.p."
        )

    history_context = build_ticker_context(
        price_history=price_history,
        ticker=ticker,
        start_date=feature_date,
        end_date=target_date,
    )

    if history_context.empty:
        print(
            "\nPrice History:"
        )

        print(
            "  Sem trajetória disponível."
        )

    else:
        print_price_history_path(
            dataframe=history_context,
            feature_date=feature_date,
            target_date=target_date,
        )

    adjusted_context = filter_period(
        dataframe=adjusted_prices,
        ticker=ticker,
        start_date=(
            history_context[
                "trade_date"
            ].min()
            if not history_context.empty
            else feature_date
        ),
        end_date=(
            history_context[
                "trade_date"
            ].max()
            if not history_context.empty
            else target_date
        ),
    )

    print_adjusted_price_path(
        adjusted_context
    )

    discontinuity_context = filter_period(
        dataframe=discontinuities,
        ticker=ticker,
        start_date=(
            history_context[
                "trade_date"
            ].min()
            if not history_context.empty
            else feature_date
        ),
        end_date=(
            history_context[
                "trade_date"
            ].max()
            if not history_context.empty
            else target_date
        ),
    )

    print_discontinuity_events(
        discontinuity_context
    )

    quality_context = filter_period(
        dataframe=price_quality,
        ticker=ticker,
        start_date=(
            history_context[
                "trade_date"
            ].min()
            if not history_context.empty
            else feature_date
        ),
        end_date=(
            history_context[
                "trade_date"
            ].max()
            if not history_context.empty
            else target_date
        ),
    )

    print_quality_path(
        quality_context
    )

    classification = classify_audit(
        adjusted_path=adjusted_context,
        discontinuities=(
            discontinuity_context
        ),
        quality=quality_context,
    )

    metrics = calculate_path_metrics(
        adjusted_context
    )

    print(
        "\nResumo do episódio:"
    )

    print(
        "  Classificação: "
        f"{classification}"
    )

    if np.isfinite(
        metrics[
            "max_abs_raw_return"
        ]
    ):
        print(
            "  Maior |daily_return_raw|: "
            f"{metrics['max_abs_raw_return'] * 100:.4f}%"
        )

    if np.isfinite(
        metrics[
            "max_abs_economic_return"
        ]
    ):
        print(
            "  Maior |daily_return_economic|: "
            f"{metrics['max_abs_economic_return'] * 100:.4f}%"
        )

    return classification


# ============================================================
# Episode summary
# ============================================================

def print_episode_summary(
    samples: pd.DataFrame,
    target_column: str,
) -> None:
    """
    Mostra que targets consecutivos
    podem representar o mesmo episódio
    econômico sobreposto.
    """

    print(
        "\n======================================"
    )
    print(
        "Resumo dos episódios supervisionados"
    )
    print(
        "======================================"
    )

    summary = (
        samples
        .groupby(
            "ticker"
        )
        .agg(
            samples=(
                target_column,
                "size",
            ),
            first_feature_date=(
                "feature_date",
                "min",
            ),
            last_feature_date=(
                "feature_date",
                "max",
            ),
            first_target_date=(
                "target_date",
                "min",
            ),
            last_target_date=(
                "target_date",
                "max",
            ),
            mean_target=(
                target_column,
                "mean",
            ),
            min_target=(
                target_column,
                "min",
            ),
            max_target=(
                target_column,
                "max",
            ),
        )
        .reset_index()
    )

    summary[
        "mean_target_pct"
    ] = (
        summary[
            "mean_target"
        ]
        * 100
    )

    summary[
        "min_target_pct"
    ] = (
        summary[
            "min_target"
        ]
        * 100
    )

    summary[
        "max_target_pct"
    ] = (
        summary[
            "max_target"
        ]
        * 100
    )

    print(
        summary[
            [
                "ticker",
                "samples",

                "first_feature_date",
                "last_feature_date",

                "first_target_date",
                "last_target_date",

                "mean_target_pct",
                "min_target_pct",
                "max_target_pct",
            ]
        ]
        .sort_values(
            "min_target_pct"
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    print(
        "Executando FII Price Jump "
        "Diagnostics..."
    )

    print(
        f"Diagnostics version: "
        f"{DIAGNOSTICS_VERSION}"
    )

    print(
        "Scope: VALIDATION ONLY"
    )

    print(
        "TEST não será carregado."
    )

    validation = load_validation()

    target_column = (
        discover_target_column(
            validation
        )
    )

    validate_validation_contract(
        dataframe=validation,
        target_column=target_column,
    )

    price_history = (
        load_price_history()
    )

    validate_price_history_contract(
        price_history
    )

    adjusted_prices = (
        load_adjusted_prices()
    )

    discontinuities = (
        load_discontinuities()
    )

    price_quality = (
        load_price_quality()
    )

    samples = build_audit_samples(
        validation=validation,
        target_column=target_column,
    )

    if samples.empty:
        raise ValueError(
            "Nenhuma sample selecionada "
            "para auditoria."
        )

    print_episode_summary(
        samples=samples,
        target_column=target_column,
    )

    classifications: list[
        str
    ] = []

    for _, row in samples.iterrows():
        classification = audit_sample(
            row=row,

            target_column=target_column,

            price_history=price_history,

            adjusted_prices=adjusted_prices,

            discontinuities=discontinuities,

            price_quality=price_quality,
        )

        classifications.append(
            classification
        )

    print(
        "\n======================================"
    )
    print(
        "Classificações finais"
    )
    print(
        "======================================"
    )

    classification_summary = (
        pd.Series(
            classifications,
            dtype="string",
        )
        .value_counts()
    )

    for classification, count in (
        classification_summary.items()
    ):
        print(
            f"{classification}: "
            f"{count:,}"
        )

    print(
        "\n======================================"
    )
    print(
        "Conclusão técnica"
    )
    print(
        "======================================"
    )

    print(
        "Nenhum dado foi alterado."
    )

    print(
        "Este diagnóstico cruza "
        "targets supervisionados com "
        "Price History, Adjusted Prices, "
        "Discontinuities e Price Quality."
    )

    print(
        "Targets T+5 consecutivos podem "
        "representar o mesmo episódio "
        "econômico e não devem ser "
        "interpretados como eventos "
        "independentes."
    )

    print(
        "Corporate actions já governadas "
        "não são inferidas novamente "
        "somente por fatores de preço."
    )

    print(
        "O TEST permaneceu completamente "
        "fora da auditoria."
    )

    print(
        "\nDiagnóstico concluído."
    )


if __name__ == "__main__":
    main()