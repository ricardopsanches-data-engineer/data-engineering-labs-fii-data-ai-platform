from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# Paths
# ============================================================

ADJUSTED_PRICES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_corporate_action_adjusted_prices"
    / "fii_corporate_action_adjusted_prices.parquet"
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


# ============================================================
# Version / upstream contract
# ============================================================

PRICE_HISTORY_VERSION = "v3"

PRICE_HISTORY_SOURCE = (
    "FII_CORPORATE_ACTION_ADJUSTED_PRICES_V3"
)

EXPECTED_ADJUSTED_PRICES_VERSION = "v3"

EXPECTED_ADJUSTED_PRICES_SOURCE = (
    "SILVER_FII_DAILY_PRICES"
)

EXPECTED_CORPORATE_ACTION_SOURCE = (
    "FII_PRICE_DISCONTINUITIES_V5_REGISTRY_V2"
)


# ============================================================
# Feature windows
# ============================================================

DEFAULT_WINDOWS = [
    5,
    10,
    20,
]


# ============================================================
# Window normalization
# ============================================================

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


# ============================================================
# Source loading
# ============================================================

def load_adjusted_prices() -> pd.DataFrame:
    """
    Carrega Corporate Action Adjusted
    Prices v3.

    Esta é a fonte oficial do
    Price History v3.
    """

    if not ADJUSTED_PRICES_PATH.exists():
        raise FileNotFoundError(
            "FII Corporate Action Adjusted "
            "Prices não encontrado: "
            f"{ADJUSTED_PRICES_PATH}"
        )

    print(
        "Carregando FII Corporate Action "
        "Adjusted Prices..."
    )

    dataframe = pd.read_parquet(
        ADJUSTED_PRICES_PATH
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


# ============================================================
# Source validation
# ============================================================

def validate_source(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida integralmente o contrato
    Adjusted Prices v3.

    Os retornos diários possuem NULL
    estrutural esperado somente na primeira
    observação de cada ticker.

    Price History v3 também valida a nova
    semântica econômica:

        cash
        +
        in-kind
        =
        total economic value
    """

    strictly_required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",

        "open_price_raw",
        "low_price_raw",
        "high_price_raw",
        "average_price_raw",
        "close_price_raw",

        "structural_adjustment_factor",

        "open_price_adjusted",
        "low_price_adjusted",
        "high_price_adjusted",
        "average_price_adjusted",
        "close_price_adjusted",

        "trades_quantity",

        #
        # Economic contract v3
        #
        "cash_amount_per_unit_raw",
        "cash_amount_per_unit_adjusted",

        "in_kind_amount_per_unit_raw",
        "in_kind_amount_per_unit_adjusted",

        "corporate_action_value_per_unit_raw",
        "corporate_action_value_per_unit_adjusted",

        #
        # Legacy aliases: cash only
        #
        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        #
        # Detector / governance
        #
        "review_status_on_date",
        "event_type_on_date",
        "discontinuity_confidence_on_date",

        "confirmed_action_on_date",
        "pending_review_on_date",

        #
        # Identity / evidence
        #
        "ticker_resolution_status",
        "market_evidence_confidence",

        #
        # Upstream metadata
        #
        "adjusted_prices_version",
        "adjusted_prices_source",
        "corporate_action_source",
    ]

    structural_nullable_columns = [
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
    ]

    required_schema_columns = (
        strictly_required_columns
        + structural_nullable_columns
    )

    missing_columns = [
        column
        for column in required_schema_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Adjusted Prices possui "
            "colunas ausentes: "
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

    strictly_required_null_count = int(
        dataframe[
            strictly_required_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    ordered = dataframe.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    first_observation_mask = (
        ordered
        .groupby(
            "ticker",
            sort=False,
        )
        .cumcount()
        == 0
    )

    expected_first_observations = int(
        first_observation_mask.sum()
    )

    structural_null_counts = {
        column: int(
            ordered[
                column
            ]
            .isna()
            .sum()
        )
        for column
        in structural_nullable_columns
    }

    unexpected_structural_null_counts = {}

    unexpected_structural_non_null_counts = {}

    for column in structural_nullable_columns:

        unexpected_nulls = int(
            (
                ~first_observation_mask
                &
                ordered[
                    column
                ].isna()
            ).sum()
        )

        unexpected_non_nulls = int(
            (
                first_observation_mask
                &
                ordered[
                    column
                ].notna()
            ).sum()
        )

        unexpected_structural_null_counts[
            column
        ] = unexpected_nulls

        unexpected_structural_non_null_counts[
            column
        ] = unexpected_non_nulls

    invalid_raw_prices = int(
        (
            dataframe[
                "close_price_raw"
            ]
            <= 0
        ).sum()
    )

    invalid_adjusted_prices = int(
        (
            dataframe[
                "close_price_adjusted"
            ]
            <= 0
        ).sum()
    )

    invalid_structural_factor = int(
        (
            dataframe[
                "structural_adjustment_factor"
            ]
            <= 0
        ).sum()
    )

    non_finite_raw_returns = int(
        (
            dataframe[
                "daily_return_raw"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "daily_return_raw"
                ]
            )
        ).sum()
    )

    non_finite_adjusted_returns = int(
        (
            dataframe[
                "daily_return_adjusted_price"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "daily_return_adjusted_price"
                ]
            )
        ).sum()
    )

    non_finite_economic_returns = int(
        (
            dataframe[
                "daily_return_economic"
            ].notna()
            &
            ~np.isfinite(
                dataframe[
                    "daily_return_economic"
                ]
            )
        ).sum()
    )

    negative_cash = int(
        (
            dataframe[
                "cash_amount_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    negative_in_kind = int(
        (
            dataframe[
                "in_kind_amount_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    negative_total_value = int(
        (
            dataframe[
                "corporate_action_value_per_unit_raw"
            ]
            < 0
        ).sum()
    )

    economic_component_mismatch = int(
        (
            ~np.isclose(
                (
                    dataframe[
                        "cash_amount_per_unit_raw"
                    ]
                    +
                    dataframe[
                        "in_kind_amount_per_unit_raw"
                    ]
                ),
                dataframe[
                    "corporate_action_value_per_unit_raw"
                ],
                rtol=1e-8,
                atol=1e-8,
            )
        ).sum()
    )

    legacy_cash_alias_mismatch = int(
        (
            ~np.isclose(
                dataframe[
                    "cash_flow_per_unit_raw"
                ],
                dataframe[
                    "cash_amount_per_unit_raw"
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    invalid_versions = sorted(
        set(
            dataframe[
                "adjusted_prices_version"
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        - {
            EXPECTED_ADJUSTED_PRICES_VERSION,
        }
    )

    invalid_sources = sorted(
        set(
            dataframe[
                "adjusted_prices_source"
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        - {
            EXPECTED_ADJUSTED_PRICES_SOURCE,
        }
    )

    invalid_corporate_action_sources = sorted(
        set(
            dataframe[
                "corporate_action_source"
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        - {
            EXPECTED_CORPORATE_ACTION_SOURCE,
        }
    )

    pending_count = int(
        dataframe[
            "pending_review_on_date"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    confirmed_count = int(
        dataframe[
            "confirmed_action_on_date"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    economic_event_count = int(
        dataframe[
            "corporate_action_value_per_unit_raw"
        ]
        .gt(0)
        .sum()
    )

    in_kind_event_count = int(
        dataframe[
            "in_kind_amount_per_unit_raw"
        ]
        .gt(0)
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Adjusted Source v3"
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
        f"Pregões: "
        f"{dataframe['trade_date'].nunique():,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Nulos obrigatórios reais: "
        f"{strictly_required_null_count:,}"
    )

    print(
        "\nNULLs estruturais esperados:"
    )

    print(
        "  Primeiras observações: "
        f"{expected_first_observations:,}"
    )

    for column in structural_nullable_columns:
        print(
            f"  {column}: "
            f"{structural_null_counts[column]:,}"
        )

    print(
        "\nNULLs estruturais inesperados:"
    )

    for column in structural_nullable_columns:
        print(
            f"  {column}: "
            f"{unexpected_structural_null_counts[column]:,}"
        )

    print(
        "\nValores inesperados "
        "na primeira observação:"
    )

    for column in structural_nullable_columns:
        print(
            f"  {column}: "
            f"{unexpected_structural_non_null_counts[column]:,}"
        )

    print(
        f"\nclose_price_raw inválidos: "
        f"{invalid_raw_prices:,}"
    )

    print(
        "close_price_adjusted inválidos: "
        f"{invalid_adjusted_prices:,}"
    )

    print(
        "structural_adjustment_factor "
        f"inválidos: "
        f"{invalid_structural_factor:,}"
    )

    print(
        "daily_return_raw não finitos: "
        f"{non_finite_raw_returns:,}"
    )

    print(
        "daily_return_adjusted_price "
        f"não finitos: "
        f"{non_finite_adjusted_returns:,}"
    )

    print(
        "daily_return_economic "
        "não finitos: "
        f"{non_finite_economic_returns:,}"
    )

    print(
        f"Cash negativo: "
        f"{negative_cash:,}"
    )

    print(
        f"In-kind negativo: "
        f"{negative_in_kind:,}"
    )

    print(
        "Valor econômico negativo: "
        f"{negative_total_value:,}"
    )

    print(
        "Mismatch cash + in-kind != total: "
        f"{economic_component_mismatch:,}"
    )

    print(
        "Mismatch legacy cash alias: "
        f"{legacy_cash_alias_mismatch:,}"
    )

    print(
        "\nCorporate Actions:"
    )

    print(
        f"  Confirmados: "
        f"{confirmed_count:,}"
    )

    print(
        f"  Econômicos: "
        f"{economic_event_count:,}"
    )

    print(
        f"  In-kind: "
        f"{in_kind_event_count:,}"
    )

    print(
        f"  PENDING_REVIEW: "
        f"{pending_count:,}"
    )

    print(
        "\nUpstream contract:"
    )

    print(
        "  Versões adjusted inválidas: "
        f"{len(invalid_versions):,}"
    )

    print(
        "  Sources adjusted inválidos: "
        f"{len(invalid_sources):,}"
    )

    print(
        "  Corporate Action Sources "
        f"inválidos: "
        f"{len(invalid_corporate_action_sources):,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "duplicidades."
        )

    if strictly_required_null_count > 0:
        raise ValueError(
            "Adjusted Prices possui NULL "
            "em campo realmente obrigatório."
        )

    if any(
        count > 0
        for count
        in unexpected_structural_null_counts.values()
    ):
        raise ValueError(
            "Adjusted Prices possui NULL "
            "estrutural fora da primeira "
            "observação do ticker."
        )

    if any(
        count > 0
        for count
        in unexpected_structural_non_null_counts.values()
    ):
        raise ValueError(
            "Adjusted Prices possui retorno "
            "preenchido indevidamente na "
            "primeira observação do ticker."
        )

    if invalid_raw_prices > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "close_price_raw inválido."
        )

    if invalid_adjusted_prices > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "close_price_adjusted inválido."
        )

    if invalid_structural_factor > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "structural_adjustment_factor "
            "inválido."
        )

    if non_finite_raw_returns > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "daily_return_raw não finito."
        )

    if non_finite_adjusted_returns > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "daily_return_adjusted_price "
            "não finito."
        )

    if non_finite_economic_returns > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "daily_return_economic "
            "não finito."
        )

    if negative_cash > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "cash negativo."
        )

    if negative_in_kind > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "in-kind negativo."
        )

    if negative_total_value > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "valor econômico negativo."
        )

    if economic_component_mismatch > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "inconsistência "
            "cash + in-kind != total."
        )

    if legacy_cash_alias_mismatch > 0:
        raise ValueError(
            "cash_flow_per_unit_raw deixou "
            "de representar cash puro."
        )

    if invalid_versions:
        raise ValueError(
            "Price History v3 exige "
            "Adjusted Prices v3."
        )

    if invalid_sources:
        raise ValueError(
            "Adjusted Prices possui "
            "source inesperado: "
            f"{invalid_sources}"
        )

    if invalid_corporate_action_sources:
        raise ValueError(
            "Adjusted Prices possui "
            "Corporate Action Source "
            "inesperado: "
            f"{invalid_corporate_action_sources}"
        )

    if pending_count > 0:
        raise ValueError(
            "Price History v3 não será "
            "construído enquanto existirem "
            "Corporate Actions "
            "PENDING_REVIEW."
        )

    print(
        "\nData Quality aprovada."
    )


# ============================================================
# Analytics semantic aliases
# ============================================================

def build_analytics_base(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói aliases semânticos usados
    pelo contrato histórico.

    close_price
        = close_price_adjusted

    daily_return
        = daily_return_economic

    A camada continua mantendo RAW,
    adjusted e economic separados para
    auditoria.
    """

    result = dataframe.copy()

    result = result.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).reset_index(
        drop=True
    )

    result[
        "open_price"
    ] = result[
        "open_price_adjusted"
    ]

    result[
        "low_price"
    ] = result[
        "low_price_adjusted"
    ]

    result[
        "high_price"
    ] = result[
        "high_price_adjusted"
    ]

    result[
        "average_price"
    ] = result[
        "average_price_adjusted"
    ]

    result[
        "close_price"
    ] = result[
        "close_price_adjusted"
    ]

    #
    # Contrato analítico principal:
    #
    # daily_return representa retorno
    # econômico total.
    #
    result[
        "daily_return"
    ] = result[
        "daily_return_economic"
    ]

    result[
        "daily_return_pct"
    ] = (
        result[
            "daily_return"
        ]
        * 100
    )

    return result


# ============================================================
# Observation count
# ============================================================

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
        result
        .groupby(
            "ticker",
            sort=False,
        )
        .cumcount()
        + 1
    )

    return result


# ============================================================
# Economic rolling return
# ============================================================

def compound_returns(
    series: pd.Series,
    window: int,
) -> pd.Series:
    """
    Composição geométrica de N retornos
    econômicos consecutivos.

    (1+r1)*(1+r2)*...*(1+rN)-1

    Esta fórmula incorpora o valor
    econômico das Corporate Actions
    já contabilizado em
    daily_return_economic.
    """

    return (
        series
        .rolling(
            window=window,
            min_periods=window,
        )
        .apply(
            lambda values: (
                np.prod(
                    1.0 + values
                )
                - 1.0
            ),
            raw=True,
        )
    )


# ============================================================
# Temporal features
# ============================================================

def calculate_window_features(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Cria features temporais com
    semântica econômica.

    return_Nd
        composição dos N
        daily_return_economic.

    ma_N
        média do close_price_adjusted.

    volatility_Nd
        std dos N retornos econômicos.

    trades_avg_Nd
        média de trades_quantity.

    price_to_maN
        close_price_adjusted / ma_N.
    """

    result = dataframe.copy()

    for window in windows:

        print(
            f"Calculando janela "
            f"{window} pregões..."
        )

        return_column = (
            f"return_{window}d"
        )

        return_pct_column = (
            f"return_{window}d_pct"
        )

        ma_column = (
            f"ma_{window}"
        )

        volatility_column = (
            f"volatility_{window}d"
        )

        volatility_pct_column = (
            f"volatility_{window}d_pct"
        )

        trades_avg_column = (
            f"trades_avg_{window}d"
        )

        price_to_ma_column = (
            f"price_to_ma{window}"
        )

        #
        # Economic cumulative return
        #
        result[
            return_column
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
            )[
                "daily_return"
            ]
            .transform(
                lambda series: (
                    compound_returns(
                        series=series,
                        window=window,
                    )
                )
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

        #
        # Moving average:
        # structurally adjusted price
        #
        result[
            ma_column
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
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

        #
        # Economic return volatility
        #
        result[
            volatility_column
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
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

        #
        # B3 observed trading activity
        #
        result[
            trades_avg_column
        ] = (
            result
            .groupby(
                "ticker",
                sort=False,
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


# ============================================================
# Dynamic feature contract
# ============================================================

def build_dynamic_feature_columns(
    windows: list[int],
) -> list[str]:
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


# ============================================================
# Gold output contract
# ============================================================

def select_gold_columns(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Monta o contrato Gold Analytics
    Price History v3.

    Mantém compatibilidade das colunas
    analíticas principais e adiciona o
    contrato econômico completo do
    Registry v2 / Adjusted Prices v3.
    """

    identity_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",
    ]

    #
    # Main analytics contract
    #
    analytics_price_columns = [
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
    ]

    #
    # Raw / adjusted audit trail
    #
    audit_price_columns = [
        "open_price_raw",
        "low_price_raw",
        "high_price_raw",
        "average_price_raw",
        "close_price_raw",

        "open_price_adjusted",
        "low_price_adjusted",
        "high_price_adjusted",
        "average_price_adjusted",
        "close_price_adjusted",

        "structural_adjustment_factor",

        #
        # Economic contract v3
        #
        "cash_amount_per_unit_raw",
        "cash_amount_per_unit_adjusted",

        "in_kind_amount_per_unit_raw",
        "in_kind_amount_per_unit_adjusted",

        "corporate_action_value_per_unit_raw",
        "corporate_action_value_per_unit_adjusted",

        #
        # Legacy aliases:
        # cash only
        #
        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        #
        # Returns
        #
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
    ]

    governance_columns = [
        "review_status_on_date",
        "event_type_on_date",
        "discontinuity_confidence_on_date",

        "confirmed_action_on_date",
        "pending_review_on_date",

        "confirmed_event_type",
        "confirmed_quantity_multiplier",
        "confirmed_price_adjustment_factor",

        "confirmed_cash_amount_per_unit",
        "confirmed_in_kind_amount_per_unit",
        "confirmed_total_economic_value_per_unit",

        "confirmed_in_kind_asset_ticker",
        "confirmed_in_kind_quantity_per_unit",

        "confirmed_corporate_action_record_date",
        "confirmed_corporate_action_effective_date",
        "confirmed_cash_payment_date",
        "confirmed_in_kind_delivery_date",
        "confirmed_first_post_event_trade_date",

        "confirmed_action_source",
        "confirmed_action_confirmation_date",
        "confirmed_governance_review_date",
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

        "adjusted_prices_version",
        "adjusted_prices_source",
        "corporate_action_source",
    ]

    columns = (
        identity_columns
        + analytics_price_columns
        + audit_price_columns
        + feature_columns
        + governance_columns
        + metadata_columns
    )

    missing_columns = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price History v3 não consegue "
            "montar o contrato Gold. "
            "Colunas ausentes: "
            f"{missing_columns}"
        )

    gold = dataframe[
        columns
    ].copy()

    gold[
        "price_history_version"
    ] = PRICE_HISTORY_VERSION

    gold[
        "price_history_source"
    ] = PRICE_HISTORY_SOURCE

    gold[
        "return_semantics"
    ] = (
        "COMPOUNDED_DAILY_RETURN_ECONOMIC"
    )

    gold[
        "price_semantics"
    ] = (
        "STRUCTURALLY_ADJUSTED_PRICE"
    )

    gold[
        "corporate_action_value_semantics"
    ] = (
        "TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND"
    )

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


# ============================================================
# Dynamic feature validation
# ============================================================

def validate_dynamic_features(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Valida disponibilidade temporal
    e consistência das features.
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

    daily_return_count = int(
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

    invalid_observation_count = int(
        (
            dataframe[
                "observations_count"
            ]
            <= 0
        ).sum()
    )

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

            available = int(
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

        #
        # MA and trades average:
        # require N observations.
        #
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

        #
        # N economic returns require
        # N+1 price observations.
        #
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

        non_finite_return = int(
            (
                dataframe[
                    return_column
                ].notna()
                &
                ~np.isfinite(
                    dataframe[
                        return_column
                    ]
                )
            ).sum()
        )

        non_finite_volatility = int(
            (
                dataframe[
                    volatility_column
                ].notna()
                &
                ~np.isfinite(
                    dataframe[
                        volatility_column
                    ]
                )
            ).sum()
        )

        non_finite_ma = int(
            (
                dataframe[
                    ma_column
                ].notna()
                &
                ~np.isfinite(
                    dataframe[
                        ma_column
                    ]
                )
            ).sum()
        )

        non_finite_price_to_ma = int(
            (
                dataframe[
                    price_to_ma_column
                ].notna()
                &
                ~np.isfinite(
                    dataframe[
                        price_to_ma_column
                    ]
                )
            ).sum()
        )

        if non_finite_return > 0:
            raise ValueError(
                f"{return_column} possui "
                "valor não finito."
            )

        if non_finite_volatility > 0:
            raise ValueError(
                f"{volatility_column} possui "
                "valor não finito."
            )

        if non_finite_ma > 0:
            raise ValueError(
                f"{ma_column} possui "
                "valor não finito."
            )

        if non_finite_price_to_ma > 0:
            raise ValueError(
                f"{price_to_ma_column} possui "
                "valor não finito."
            )

    print(
        "\nData Quality das features aprovada."
    )


# ============================================================
# Semantic alias validation
# ============================================================

def validate_semantic_aliases(
    dataframe: pd.DataFrame,
) -> None:
    """
    Garante que o contrato principal
    aponta para a série econômica e
    estruturalmente ajustada.
    """

    close_mismatch = int(
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

    daily_mask = (
        dataframe[
            "daily_return"
        ].notna()
        &
        dataframe[
            "daily_return_economic"
        ].notna()
    )

    daily_return_mismatch = int(
        (
            ~np.isclose(
                dataframe.loc[
                    daily_mask,
                    "daily_return",
                ],
                dataframe.loc[
                    daily_mask,
                    "daily_return_economic",
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    cash_alias_mismatch = int(
        (
            ~np.isclose(
                dataframe[
                    "cash_flow_per_unit_raw"
                ],
                dataframe[
                    "cash_amount_per_unit_raw"
                ],
                rtol=0.0,
                atol=1e-12,
            )
        ).sum()
    )

    economic_component_mismatch = int(
        (
            ~np.isclose(
                (
                    dataframe[
                        "cash_amount_per_unit_raw"
                    ]
                    +
                    dataframe[
                        "in_kind_amount_per_unit_raw"
                    ]
                ),
                dataframe[
                    "corporate_action_value_per_unit_raw"
                ],
                rtol=1e-8,
                atol=1e-8,
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Validação - Semântica v3"
    )
    print(
        "======================================"
    )

    print(
        "close_price != "
        "close_price_adjusted: "
        f"{close_mismatch:,}"
    )

    print(
        "daily_return != "
        "daily_return_economic: "
        f"{daily_return_mismatch:,}"
    )

    print(
        "cash_flow != cash_amount: "
        f"{cash_alias_mismatch:,}"
    )

    print(
        "cash + in-kind != total economic: "
        f"{economic_component_mismatch:,}"
    )

    if close_mismatch > 0:
        raise ValueError(
            "close_price não representa "
            "close_price_adjusted."
        )

    if daily_return_mismatch > 0:
        raise ValueError(
            "daily_return não representa "
            "daily_return_economic."
        )

    if cash_alias_mismatch > 0:
        raise ValueError(
            "cash_flow_per_unit_raw não "
            "representa cash puro."
        )

    if economic_component_mismatch > 0:
        raise ValueError(
            "Valor econômico total não "
            "corresponde a cash + in-kind."
        )

    print(
        "\nSemântica v3 aprovada."
    )


# ============================================================
# Corporate Action validation
# ============================================================

def validate_known_corporate_actions(
    dataframe: pd.DataFrame,
) -> None:
    """
    Exibe todos os eventos governados
    confirmados para comparação direta
    entre RAW, adjusted-price e retorno
    econômico.

    Não existe quantidade hardcoded:
    o Registry é a fonte de verdade.
    """

    event_rows = dataframe[
        dataframe[
            "confirmed_action_on_date"
        ]
        .fillna(False)
        .astype(bool)
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Validação - Corporate Actions"
    )
    print(
        "======================================"
    )

    print(
        "Eventos confirmados encontrados: "
        f"{len(event_rows):,}"
    )

    if event_rows.empty:
        return

    display_columns = [
        "ticker",
        "trade_date",
        "confirmed_event_type",

        "cash_amount_per_unit_raw",
        "in_kind_amount_per_unit_raw",
        "corporate_action_value_per_unit_raw",

        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
    ]

    display = event_rows[
        display_columns
    ].sort_values(
        [
            "trade_date",
            "ticker",
        ]
    ).copy()

    display[
        "daily_return_raw_pct"
    ] = (
        display[
            "daily_return_raw"
        ]
        * 100
    )

    display[
        "daily_return_adjusted_price_pct"
    ] = (
        display[
            "daily_return_adjusted_price"
        ]
        * 100
    )

    display[
        "daily_return_economic_pct"
    ] = (
        display[
            "daily_return_economic"
        ]
        * 100
    )

    print(
        display[
            [
                "ticker",
                "trade_date",
                "confirmed_event_type",

                "cash_amount_per_unit_raw",
                "in_kind_amount_per_unit_raw",
                "corporate_action_value_per_unit_raw",

                "daily_return_raw_pct",
                "daily_return_adjusted_price_pct",
                "daily_return_economic_pct",
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# VIUR regression validation
# ============================================================

def validate_viur11_semantics(
    dataframe: pd.DataFrame,
) -> None:
    """
    Regression check para impedir que
    Price History volte a representar
    VIUR11 como 100% cash.
    """

    viur_rows = dataframe[
        dataframe[
            "ticker"
        ].eq(
            "VIUR11"
        )
        &
        dataframe[
            "confirmed_action_on_date"
        ]
        .fillna(False)
        .astype(bool)
        &
        dataframe[
            "confirmed_event_type"
        ]
        .fillna("")
        .eq(
            "AMORTIZATION"
        )
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Regression Check - VIUR11"
    )
    print(
        "======================================"
    )

    if viur_rows.empty:
        print(
            "Nenhum evento VIUR11 confirmado."
        )
        return

    if len(viur_rows) != 1:
        raise ValueError(
            "Quantidade inesperada de "
            "eventos VIUR11 confirmados."
        )

    row = viur_rows.iloc[0]

    cash = float(
        row[
            "cash_amount_per_unit_raw"
        ]
    )

    in_kind = float(
        row[
            "in_kind_amount_per_unit_raw"
        ]
    )

    total = float(
        row[
            "corporate_action_value_per_unit_raw"
        ]
    )

    asset = row[
        "confirmed_in_kind_asset_ticker"
    ]

    print(
        f"Cash: "
        f"{cash:.9f}"
    )

    print(
        f"In-kind: "
        f"{in_kind:.9f}"
    )

    print(
        f"Total economic value: "
        f"{total:.9f}"
    )

    print(
        f"In-kind asset: "
        f"{asset}"
    )

    if cash <= 0:
        raise ValueError(
            "VIUR11 deveria possuir "
            "componente cash positivo."
        )

    if in_kind <= 0:
        raise ValueError(
            "VIUR11 deveria possuir "
            "componente in-kind positivo."
        )

    if asset != "TRXF11":
        raise ValueError(
            "VIUR11 deveria possuir "
            "TRXF11 como ativo in-kind."
        )

    if not np.isclose(
        cash + in_kind,
        total,
        rtol=1e-8,
        atol=1e-8,
    ):
        raise ValueError(
            "VIUR11 possui contrato "
            "econômico inconsistente."
        )

    print(
        "\nSemântica VIUR11 aprovada."
    )


# ============================================================
# Gold output validation
# ============================================================

def validate_gold_output(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
    """
    Validação final do contrato físico
    Price History v3.
    """

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",

        "close_price",
        "close_price_raw",
        "close_price_adjusted",

        "cash_amount_per_unit_raw",
        "in_kind_amount_per_unit_raw",
        "corporate_action_value_per_unit_raw",

        "daily_return",
        "daily_return_economic",

        "confirmed_action_on_date",
        "pending_review_on_date",

        "observations_count",

        "price_history_version",
        "price_history_source",
        "return_semantics",
        "price_semantics",
        "corporate_action_value_semantics",
        "feature_windows",
    ]

    required_columns.extend(
        build_dynamic_feature_columns(
            windows
        )
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price History v3 possui "
            "colunas ausentes: "
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

    invalid_version = int(
        (
            dataframe[
                "price_history_version"
            ]
            != PRICE_HISTORY_VERSION
        ).sum()
    )

    invalid_source = int(
        (
            dataframe[
                "price_history_source"
            ]
            != PRICE_HISTORY_SOURCE
        ).sum()
    )

    invalid_return_semantics = int(
        (
            dataframe[
                "return_semantics"
            ]
            != (
                "COMPOUNDED_"
                "DAILY_RETURN_ECONOMIC"
            )
        ).sum()
    )

    invalid_price_semantics = int(
        (
            dataframe[
                "price_semantics"
            ]
            != (
                "STRUCTURALLY_"
                "ADJUSTED_PRICE"
            )
        ).sum()
    )

    invalid_value_semantics = int(
        (
            dataframe[
                "corporate_action_value_semantics"
            ]
            != (
                "TOTAL_ECONOMIC_VALUE_"
                "CASH_PLUS_IN_KIND"
            )
        ).sum()
    )

    pending_count = int(
        dataframe[
            "pending_review_on_date"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Price History v3"
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
        f"Versões inválidas: "
        f"{invalid_version:,}"
    )

    print(
        f"Sources inválidos: "
        f"{invalid_source:,}"
    )

    print(
        "Return semantics inválidas: "
        f"{invalid_return_semantics:,}"
    )

    print(
        "Price semantics inválidas: "
        f"{invalid_price_semantics:,}"
    )

    print(
        "Corporate Action value semantics "
        f"inválidas: "
        f"{invalid_value_semantics:,}"
    )

    print(
        f"PENDING_REVIEW: "
        f"{pending_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price History v3 possui "
            "duplicidades."
        )

    if invalid_version > 0:
        raise ValueError(
            "price_history_version inválida."
        )

    if invalid_source > 0:
        raise ValueError(
            "price_history_source inválida."
        )

    if invalid_return_semantics > 0:
        raise ValueError(
            "return_semantics inválida."
        )

    if invalid_price_semantics > 0:
        raise ValueError(
            "price_semantics inválida."
        )

    if invalid_value_semantics > 0:
        raise ValueError(
            "corporate_action_value_semantics "
            "inválida."
        )

    if pending_count > 0:
        raise ValueError(
            "Price History v3 contém "
            "Corporate Action pendente."
        )

    print(
        "\nData Quality final aprovada."
    )


# ============================================================
# Save
# ============================================================

def save_gold(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )


# ============================================================
# Summary
# ============================================================

def print_history_summary(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> None:
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

    total_trading_days = int(
        dataframe[
            "trade_date"
        ]
        .nunique()
    )

    structural_adjusted_rows = int(
        (
            ~np.isclose(
                dataframe[
                    "structural_adjustment_factor"
                ],
                1.0,
            )
        ).sum()
    )

    cash_rows = int(
        dataframe[
            "cash_amount_per_unit_raw"
        ]
        .gt(0)
        .sum()
    )

    in_kind_rows = int(
        dataframe[
            "in_kind_amount_per_unit_raw"
        ]
        .gt(0)
        .sum()
    )

    economic_rows = int(
        dataframe[
            "corporate_action_value_per_unit_raw"
        ]
        .gt(0)
        .sum()
    )

    confirmed_actions = int(
        dataframe[
            "confirmed_action_on_date"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
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
        f"Version: "
        f"{PRICE_HISTORY_VERSION}"
    )

    print(
        f"Source: "
        f"{PRICE_HISTORY_SOURCE}"
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
        "Tickers presentes em todos "
        f"os pregões: "
        f"{(observations == total_trading_days).sum():,}"
    )

    print(
        "Linhas estruturalmente ajustadas: "
        f"{structural_adjusted_rows:,}"
    )

    print(
        "Corporate Actions confirmados: "
        f"{confirmed_actions:,}"
    )

    print(
        "Linhas com componente cash: "
        f"{cash_rows:,}"
    )

    print(
        "Linhas com componente in-kind: "
        f"{in_kind_rows:,}"
    )

    print(
        "Linhas com valor econômico "
        f"corporativo: "
        f"{economic_rows:,}"
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
            f"  Linhas com "
            f"{volatility_column}: "
            f"{dataframe[volatility_column].notna().sum():,}"
        )

    print(
        "\nSemântica:"
    )

    print(
        "  close_price = "
        "close_price_adjusted"
    )

    print(
        "  daily_return = "
        "daily_return_economic"
    )

    print(
        "  corporate_action_value = "
        "cash + in-kind"
    )

    print(
        "  return_Nd = composição dos "
        "retornos econômicos"
    )

    print(
        "  ma_N = média do preço ajustado"
    )

    print(
        "  volatility_Nd = std dos "
        "retornos econômicos"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói Gold Analytics "
            "FII Price History v3."
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
        f"Version: "
        f"{PRICE_HISTORY_VERSION}"
    )

    print(
        f"Source: "
        f"{PRICE_HISTORY_SOURCE}"
    )

    print(
        f"Janelas temporais: "
        f"{windows}"
    )

    history = load_adjusted_prices()

    validate_source(
        history
    )

    history = build_analytics_base(
        history
    )

    history = calculate_observation_count(
        history
    )

    history = calculate_window_features(
        dataframe=history,
        windows=windows,
    )

    gold = select_gold_columns(
        dataframe=history,
        windows=windows,
    )

    validate_semantic_aliases(
        gold
    )

    validate_dynamic_features(
        dataframe=gold,
        windows=windows,
    )

    validate_known_corporate_actions(
        gold
    )

    validate_viur11_semantics(
        gold
    )

    validate_gold_output(
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
        "FII Price History v3 criada "
        "com sucesso."
    )

    print(
        "A camada usa exclusivamente "
        "Corporate Action Adjusted "
        "Prices v3."
    )

    print(
        "O contrato analítico principal "
        "foi preservado para downstream."
    )

    print(
        "Os retornos rolling possuem "
        "semântica econômica."
    )

    print(
        "Cash, in-kind e valor econômico "
        "total permanecem separados."
    )

    print(
        "Preços RAW, adjusted e informações "
        "de governança permanecem "
        "auditáveis."
    )

    print(
        "VIUR11 permanece protegido por "
        "regression check específico."
    )


if __name__ == "__main__":
    main()