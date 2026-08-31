from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


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


PRICE_HISTORY_VERSION = "v2"

PRICE_HISTORY_SOURCE = (
    "FII_CORPORATE_ACTION_ADJUSTED_PRICES"
)

EXPECTED_ADJUSTED_PRICES_VERSION = "v2"

DEFAULT_WINDOWS = [
    5,
    10,
    20,
]


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


def load_adjusted_prices() -> pd.DataFrame:
    """
    Carrega a camada governada de preços
    ajustados.

    Esta é a fonte oficial do Price History v2.
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


def validate_source(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida o contrato de entrada.

    A fonte deve ser necessariamente
    Adjusted Prices v2.

    Os três retornos diários possuem
    NULL estrutural esperado somente
    na primeira observação de cada ticker.
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

        "open_price_adjusted",
        "low_price_adjusted",
        "high_price_adjusted",
        "average_price_adjusted",
        "close_price_adjusted",

        "trades_quantity",

        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

        "review_status_on_date",
        "event_type_on_date",
        "confirmed_action_on_date",
        "pending_review_on_date",

        "ticker_resolution_status",
        "market_evidence_confidence",

        "adjusted_prices_version",
        "adjusted_prices_source",
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
        for column in structural_nullable_columns
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
            "SILVER_FII_DAILY_PRICES",
        }
    )

    pending_count = int(
        dataframe[
            "pending_review_on_date"
        ].sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Adjusted Source"
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
        f"close_price_adjusted inválidos: "
        f"{invalid_adjusted_prices:,}"
    )

    print(
        "daily_return_economic "
        "não finitos: "
        f"{non_finite_economic_returns:,}"
    )

    print(
        "PENDING_REVIEW: "
        f"{pending_count:,}"
    )

    print(
        "Versões adjusted inválidas: "
        f"{len(invalid_versions):,}"
    )

    print(
        "Sources adjusted inválidos: "
        f"{len(invalid_sources):,}"
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

    if non_finite_economic_returns > 0:
        raise ValueError(
            "Adjusted Prices possui "
            "daily_return_economic "
            "não finito."
        )

    if invalid_versions:
        raise ValueError(
            "Price History v2 exige "
            "Adjusted Prices v2."
        )

    if invalid_sources:
        raise ValueError(
            "Adjusted Prices possui "
            "source inesperado: "
            f"{invalid_sources}"
        )

    if pending_count > 0:
        raise ValueError(
            "Price History v2 não será "
            "construído enquanto existirem "
            "Corporate Actions "
            "PENDING_REVIEW."
        )

    print(
        "\nData Quality aprovada."
    )


def build_analytics_base(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói aliases semânticos usados
    pelo contrato histórico.

    As colunas legadas permanecem para
    compatibilidade downstream, mas passam
    a representar a série corrigida.

    close_price
        = close_price_adjusted

    daily_return
        = daily_return_economic
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

    #
    # Contrato principal da Analytics.
    #
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
    # A partir da v2, daily_return significa
    # retorno econômico.
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
            "ticker",
            sort=False,
        )
        .cumcount()
        + 1
    )

    return result


def compound_returns(
    series: pd.Series,
    window: int,
) -> pd.Series:
    """
    Composição geométrica de N retornos
    econômicos consecutivos.

    (1+r1)*(1+r2)*...*(1+rN)-1

    Diferentemente de close_t / close_t-N,
    esta fórmula incorpora cash flows
    econômicos registrados no período.
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
        # Retorno econômico acumulado.
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
        # Média móvel sobre preço ajustado.
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
        # Volatilidade dos retornos
        # econômicos.
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
        # Liquidez continua sendo observada
        # diretamente da negociação B3.
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


def select_gold_columns(
    dataframe: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """
    Monta o contrato Gold v2.

    Mantém o contrato principal antigo
    e adiciona trilha de auditoria.
    """

    identity_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "instrument_id",
    ]

    #
    # Contrato compatível com a camada
    # de features já existente.
    #
    analytics_price_columns = [
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
    ]

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

        "cash_flow_per_unit_raw",
        "cash_flow_per_unit_adjusted",

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
        "confirmed_action_source",
        "confirmed_action_confirmation_date",
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
    ]

    columns = (
        identity_columns
        + analytics_price_columns
        + audit_price_columns
        + feature_columns
        + governance_columns
        + metadata_columns
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
        # MA e média de trades:
        # N preços/observações.
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
        # N retornos econômicos exigem
        # N+1 observações de preço.
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

    print(
        "\nData Quality das features aprovada."
    )


def validate_semantic_aliases(
    dataframe: pd.DataFrame,
) -> None:
    """
    Garante que o contrato principal
    realmente aponta para a série
    econômica/ajustada.
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

    print(
        "\n======================================"
    )
    print(
        "Validação - Semântica v2"
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

    print(
        "\nSemântica v2 aprovada."
    )


def validate_known_corporate_actions(
    dataframe: pd.DataFrame,
) -> None:
    """
    Exibe os oito eventos governados para
    permitir comparação direta entre RAW
    e série econômica.
    """

    event_rows = dataframe[
        dataframe[
            "confirmed_action_on_date"
        ]
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
        f"Eventos confirmados encontrados: "
        f"{len(event_rows):,}"
    )

    if event_rows.empty:
        return

    display_columns = [
        "ticker",
        "trade_date",
        "confirmed_event_type",
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
                "daily_return_raw_pct",
                "daily_return_adjusted_price_pct",
                "daily_return_economic_pct",
            ]
        ].to_string(
            index=False
        )
    )


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

    cash_flow_rows = int(
        (
            dataframe[
                "cash_flow_per_unit_adjusted"
            ]
            > 0
        ).sum()
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
        f"Tickers presentes em todos "
        f"os pregões: "
        f"{(observations == total_trading_days).sum():,}"
    )

    print(
        "Linhas estruturalmente ajustadas: "
        f"{structural_adjusted_rows:,}"
    )

    print(
        "Linhas com cash flow corporativo: "
        f"{cash_flow_rows:,}"
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói Gold Analytics "
            "FII Price History v2."
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
        "FII Price History v2 criada "
        "com sucesso."
    )

    print(
        "A camada usa exclusivamente "
        "Corporate Action Adjusted Prices."
    )

    print(
        "O contrato legado foi preservado "
        "para compatibilidade downstream."
    )

    print(
        "Os retornos rolling agora possuem "
        "semântica econômica."
    )

    print(
        "Preços RAW e informações de "
        "governança permanecem auditáveis."
    )


if __name__ == "__main__":
    main()