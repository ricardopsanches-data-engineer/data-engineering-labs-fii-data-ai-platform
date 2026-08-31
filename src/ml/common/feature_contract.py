from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


FEATURE_CONTRACT_VERSION = "v2"


EXPECTED_FEATURE_VERSION = "v6"

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)


@dataclass(frozen=True)
class FeatureContract:
    """
    Contrato oficial das features
    utilizadas pelos modelos.

    O contrato define:

    - versão do contrato;
    - janelas temporais;
    - allowlist explícita de features;
    - semântica esperada das features.
    """

    version: str

    windows: tuple[int, ...]

    features: tuple[str, ...]

    source_feature_version: str

    price_semantics: str

    return_semantics: str


def discover_feature_windows(
    dataframe: pd.DataFrame,
) -> list[int]:
    """
    Descobre as janelas temporais declaradas
    pela Gold ML.

    Esperado:

        feature_windows = "5,10,20"
    """

    if (
        "feature_windows"
        not in dataframe.columns
    ):
        raise ValueError(
            "Coluna feature_windows "
            "não encontrada."
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
            "Nenhuma configuração de "
            "feature_windows encontrada."
        )

    if len(values) > 1:
        raise ValueError(
            "Mais de uma configuração de "
            "feature_windows encontrada: "
            f"{values.tolist()}"
        )

    raw_windows = values[0]

    try:
        windows = sorted(
            {
                int(
                    value.strip()
                )
                for value
                in raw_windows.split(",")
                if value.strip()
            }
        )

    except ValueError as error:
        raise ValueError(
            "feature_windows possui "
            "formato inválido: "
            f"{raw_windows}"
        ) from error

    if not windows:
        raise ValueError(
            "Nenhuma janela válida encontrada."
        )

    if any(
        window <= 0
        for window in windows
    ):
        raise ValueError(
            "Todas as janelas devem ser "
            "maiores que zero."
        )

    return windows


def build_feature_names(
    windows: list[int],
) -> list[str]:
    """
    Constrói a allowlist oficial
    das features preditivas.

    Princípios do contrato v2:

    - evita duplicações decimal/percentual;
    - evita preço absoluto;
    - evita médias móveis absolutas;
    - evita colunas RAW de auditoria;
    - evita qualquer target;
    - privilegia retornos econômicos,
      volatilidade e relações normalizadas;
    - mantém relações entre janelas.

    Os nomes das 18 features permanecem
    compatíveis com o contrato v1.

    A mudança da v2 está na validação
    explícita da semântica upstream.
    """

    if not windows:
        raise ValueError(
            "Lista de janelas vazia."
        )

    features: list[str] = [
        "daily_return",
    ]

    for window in windows:
        features.extend(
            [
                f"return_{window}d",
                f"volatility_{window}d",
                f"price_to_ma{window}",
            ]
        )

    for short_window, long_window in zip(
        windows,
        windows[1:],
    ):
        features.extend(
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

    return features


def validate_feature_semantics(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida a linhagem semântica das features.

    O contrato v2 aceita somente features
    produzidas pela arquitetura econômica
    atual.

    Isso impede que datasets antigos,
    mesmo contendo os mesmos nomes de
    colunas, sejam usados silenciosamente
    pelo modelo.
    """

    required_metadata_columns = [
        "feature_version",
        "price_semantics",
        "return_semantics",
    ]

    missing_columns = [
        column
        for column
        in required_metadata_columns
        if column
        not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Metadados semânticos ausentes "
            "no dataset: "
            f"{missing_columns}"
        )

    feature_versions = sorted(
        dataframe[
            "feature_version"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    price_semantics = sorted(
        dataframe[
            "price_semantics"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return_semantics = sorted(
        dataframe[
            "return_semantics"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    if feature_versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "Feature Contract v2 exige "
            f"feature_version="
            f"{EXPECTED_FEATURE_VERSION}. "
            "Encontrado: "
            f"{feature_versions}"
        )

    if price_semantics != [
        EXPECTED_PRICE_SEMANTICS
    ]:
        raise ValueError(
            "Feature Contract v2 exige "
            "price_semantics="
            f"{EXPECTED_PRICE_SEMANTICS}. "
            "Encontrado: "
            f"{price_semantics}"
        )

    if return_semantics != [
        EXPECTED_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "Feature Contract v2 exige "
            "return_semantics="
            f"{EXPECTED_RETURN_SEMANTICS}. "
            "Encontrado: "
            f"{return_semantics}"
        )


def validate_feature_contract(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> None:
    """
    Valida a allowlist oficial.

    Confirma:

    - todas as features existem;
    - não há duplicidades;
    - nenhuma coluna proibida foi incluída;
    - todas as features são numéricas;
    - não existem valores infinitos
      nas features disponíveis.
    """

    missing_columns = [
        column
        for column in feature_columns
        if column
        not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Features do contrato ausentes "
            "no dataset: "
            f"{missing_columns}"
        )

    duplicate_features = sorted(
        {
            column
            for column in feature_columns
            if feature_columns.count(
                column
            ) > 1
        }
    )

    if duplicate_features:
        raise ValueError(
            "Feature Contract possui "
            "features duplicadas: "
            f"{duplicate_features}"
        )

    suspicious_columns = [
        column
        for column in feature_columns
        if (
            column.startswith(
                "target_"
            )
            or "next_" in column
            or column.endswith(
                "_pct"
            )
            or "_raw" in column
            or column
            in {
                "feature_date",
                "ticker",
                "cnpj",
                "codigo_cvm",
                "close_price",
                "close_price_raw",
                "close_price_adjusted",
                "trades_quantity",
                "observations_count",
                "daily_return_raw",
                "daily_return_adjusted_price",
                "daily_return_economic",
            }
        )
    ]

    if suspicious_columns:
        raise ValueError(
            "Features proibidas ou suspeitas "
            "no contrato: "
            f"{suspicious_columns}"
        )

    non_numeric_columns = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(
            dataframe[
                column
            ]
        )
    ]

    if non_numeric_columns:
        raise ValueError(
            "Features não numéricas "
            "encontradas: "
            f"{non_numeric_columns}"
        )

    non_finite_counts: dict[
        str,
        int,
    ] = {}

    for column in feature_columns:
        series = dataframe[
            column
        ]

        non_finite_count = int(
            (
                series.notna()
                &
                ~np.isfinite(
                    series
                )
            ).sum()
        )

        if non_finite_count > 0:
            non_finite_counts[
                column
            ] = non_finite_count

    if non_finite_counts:
        raise ValueError(
            "Features possuem valores "
            "não finitos: "
            f"{non_finite_counts}"
        )


def validate_expected_feature_count(
    windows: list[int],
    feature_columns: list[str],
) -> None:
    """
    Valida estruturalmente a quantidade
    esperada de features.

    Para N janelas:

        1 daily return

        + 3 features por janela

        + 4 relações para cada par
          de janelas consecutivas

    Para [5, 10, 20]:

        1 + (3 * 3) + (4 * 2)
        = 18 features
    """

    expected_count = (
        1
        + 3 * len(
            windows
        )
        + 4 * max(
            len(windows) - 1,
            0,
        )
    )

    actual_count = len(
        feature_columns
    )

    if actual_count != expected_count:
        raise ValueError(
            "Quantidade de features "
            "incompatível com o contrato. "
            f"Esperado: {expected_count}. "
            f"Encontrado: {actual_count}."
        )


def get_feature_contract(
    dataframe: pd.DataFrame,
) -> FeatureContract:
    """
    Retorna o Feature Contract completo.

    Ordem de validação:

    1. semântica upstream;
    2. descoberta das janelas;
    3. construção da allowlist;
    4. validação estrutural;
    5. criação do contrato imutável.
    """

    validate_feature_semantics(
        dataframe
    )

    windows = (
        discover_feature_windows(
            dataframe
        )
    )

    features = (
        build_feature_names(
            windows
        )
    )

    validate_expected_feature_count(
        windows=windows,
        feature_columns=features,
    )

    validate_feature_contract(
        dataframe=dataframe,
        feature_columns=features,
    )

    return FeatureContract(
        version=FEATURE_CONTRACT_VERSION,

        windows=tuple(
            windows
        ),

        features=tuple(
            features
        ),

        source_feature_version=(
            EXPECTED_FEATURE_VERSION
        ),

        price_semantics=(
            EXPECTED_PRICE_SEMANTICS
        ),

        return_semantics=(
            EXPECTED_RETURN_SEMANTICS
        ),
    )