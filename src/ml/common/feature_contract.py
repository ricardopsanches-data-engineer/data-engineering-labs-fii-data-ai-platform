from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ============================================================
# Feature Contract
# ============================================================

FEATURE_CONTRACT_VERSION = "v3"


# ============================================================
# Upstream semantic contract
# ============================================================

EXPECTED_FEATURE_VERSION = "v7"

EXPECTED_PRICE_SEMANTICS = (
    "STRUCTURALLY_ADJUSTED_PRICE"
)

EXPECTED_RETURN_SEMANTICS = (
    "COMPOUNDED_DAILY_RETURN_ECONOMIC"
)

EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS = (
    "TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND"
)

EXPECTED_FEATURE_CORPORATE_ACTION_POLICY = (
    "ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_"
    "NO_DIRECT_CA_PAYLOAD_FEATURES"
)


# ============================================================
# Feature Contract data structure
# ============================================================

@dataclass(frozen=True)
class FeatureContract:
    """
    Contrato oficial das features
    utilizadas pelos modelos.

    O contrato define:

    - versão do contrato;
    - janelas temporais;
    - allowlist explícita de features;
    - versão da Gold ML Features;
    - semântica de preço;
    - semântica de retorno;
    - semântica econômica de
      Corporate Actions;
    - política de uso de Corporate Actions
      nas features.

    O contrato é imutável depois de criado.
    """

    version: str

    windows: tuple[int, ...]

    features: tuple[str, ...]

    source_feature_version: str

    price_semantics: str

    return_semantics: str

    corporate_action_value_semantics: str

    corporate_action_policy: str


# ============================================================
# Feature windows discovery
# ============================================================

def discover_feature_windows(
    dataframe: pd.DataFrame,
) -> list[int]:
    """
    Descobre as janelas temporais declaradas
    pela Gold ML Features.

    Exemplo esperado:

        feature_windows = "5,10,20"

    O contrato não fixa artificialmente
    as janelas.

    Elas são herdadas do artefato upstream,
    desde que exista uma única configuração
    consistente no dataset.
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


# ============================================================
# Official predictive feature allowlist
# ============================================================

def build_feature_names(
    windows: list[int],
) -> list[str]:
    """
    Constrói a allowlist oficial
    das features preditivas.

    Princípios do Feature Contract v3:

    - allowlist explícita;
    - evita duplicações decimal/percentual;
    - evita preço absoluto;
    - evita médias móveis absolutas;
    - evita colunas RAW de auditoria;
    - evita qualquer target;
    - evita governança e metadata;
    - evita payload direto de
      Corporate Actions;
    - privilegia retornos econômicos,
      volatilidade e relações normalizadas;
    - mantém relações entre janelas.

    A evolução para v3 NÃO altera
    matematicamente a seleção das features
    existente no v2.

    Para [5, 10, 20], permanecem
    exatamente 18 features.
    """

    if not windows:
        raise ValueError(
            "Lista de janelas vazia."
        )

    features: list[str] = [
        "daily_return",
    ]

    #
    # Features por janela
    #

    for window in windows:
        features.extend(
            [
                f"return_{window}d",
                f"volatility_{window}d",
                f"price_to_ma{window}",
            ]
        )

    #
    # Relações entre janelas consecutivas
    #

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


# ============================================================
# Upstream semantic validation
# ============================================================

def validate_feature_semantics(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida a linhagem semântica das
    features.

    Feature Contract v3 aceita somente
    Features v7 produzidas pela arquitetura
    econômica atual.

    Isso impede que um dataset antigo,
    mesmo contendo os mesmos nomes físicos
    de colunas, seja usado silenciosamente
    pelo modelo.
    """

    required_metadata_columns = [
        "feature_version",

        "price_semantics",
        "return_semantics",

        "corporate_action_value_semantics",
        "feature_corporate_action_policy",
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

    corporate_action_value_semantics = sorted(
        dataframe[
            "corporate_action_value_semantics"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    corporate_action_policies = sorted(
        dataframe[
            "feature_corporate_action_policy"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    print(
        "\n======================================"
    )
    print(
        "Feature Contract - Semantics"
    )
    print(
        "======================================"
    )

    print(
        "Feature version: "
        f"{feature_versions}"
    )

    print(
        "Price semantics: "
        f"{price_semantics}"
    )

    print(
        "Return semantics: "
        f"{return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{corporate_action_value_semantics}"
    )

    print(
        "Corporate Action feature policy: "
        f"{corporate_action_policies}"
    )

    if feature_versions != [
        EXPECTED_FEATURE_VERSION
    ]:
        raise ValueError(
            "Feature Contract v3 exige "
            f"feature_version="
            f"{EXPECTED_FEATURE_VERSION}. "
            "Encontrado: "
            f"{feature_versions}"
        )

    if price_semantics != [
        EXPECTED_PRICE_SEMANTICS
    ]:
        raise ValueError(
            "Feature Contract v3 exige "
            "price_semantics="
            f"{EXPECTED_PRICE_SEMANTICS}. "
            "Encontrado: "
            f"{price_semantics}"
        )

    if return_semantics != [
        EXPECTED_RETURN_SEMANTICS
    ]:
        raise ValueError(
            "Feature Contract v3 exige "
            "return_semantics="
            f"{EXPECTED_RETURN_SEMANTICS}. "
            "Encontrado: "
            f"{return_semantics}"
        )

    if corporate_action_value_semantics != [
        EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
    ]:
        raise ValueError(
            "Feature Contract v3 exige "
            "corporate_action_value_semantics="
            f"{EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS}. "
            "Encontrado: "
            f"{corporate_action_value_semantics}"
        )

    if corporate_action_policies != [
        EXPECTED_FEATURE_CORPORATE_ACTION_POLICY
    ]:
        raise ValueError(
            "Feature Contract v3 exige "
            "feature_corporate_action_policy="
            f"{EXPECTED_FEATURE_CORPORATE_ACTION_POLICY}. "
            "Encontrado: "
            f"{corporate_action_policies}"
        )

    print(
        "\nSemântica upstream aprovada."
    )


# ============================================================
# Leakage protection
# ============================================================

def is_forbidden_feature(
    column: str,
) -> bool:
    """
    Detecta categorias de colunas que
    jamais devem entrar no vetor X.

    Esta função funciona como uma
    segunda barreira de segurança.

    A barreira principal continua sendo
    a allowlist explícita construída por
    build_feature_names().
    """

    normalized = (
        str(column)
        .strip()
        .lower()
    )

    #
    # --------------------------------------------------------
    # Future target / labels
    # --------------------------------------------------------
    #

    if normalized.startswith(
        "target_"
    ):
        return True

    if "next_" in normalized:
        return True

    if normalized in {
        "target",
        "target_date",
        "target_name",
    }:
        return True

    #
    # --------------------------------------------------------
    # Percent duplicate representations
    # --------------------------------------------------------
    #

    if normalized.endswith(
        "_pct"
    ):
        return True

    #
    # --------------------------------------------------------
    # Raw / audit data
    # --------------------------------------------------------
    #

    if "_raw" in normalized:
        return True

    #
    # --------------------------------------------------------
    # Identity
    # --------------------------------------------------------
    #

    if normalized in {
        "feature_date",
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
    }:
        return True

    #
    # --------------------------------------------------------
    # Absolute prices / absolute levels
    # --------------------------------------------------------
    #

    if normalized in {
        "close_price",
        "close_price_raw",
        "close_price_adjusted",
        "trades_quantity",
        "observations_count",
    }:
        return True

    #
    # --------------------------------------------------------
    # Audit return aliases
    # --------------------------------------------------------
    #

    if normalized in {
        "daily_return_raw",
        "daily_return_adjusted_price",
        "daily_return_economic",
    }:
        return True

    #
    # --------------------------------------------------------
    # Corporate Action payload
    # --------------------------------------------------------
    #

    corporate_action_payload_tokens = [
        "cash_amount",
        "cash_flow",
        "in_kind_amount",
        "corporate_action_value",
        "confirmed_cash",
        "confirmed_in_kind",
        "confirmed_total_economic",
        "quantity_multiplier",
        "price_adjustment_factor",
        "asset_ticker",
        "quantity_per_unit",
    ]

    if any(
        token in normalized
        for token
        in corporate_action_payload_tokens
    ):
        return True

    #
    # --------------------------------------------------------
    # Governance / eligibility / review
    # --------------------------------------------------------
    #

    governance_tokens = [
        "ml_eligible",
        "eligibility",
        "quality_status",
        "review_status",
        "review_",
        "confirmed_action",
        "pending_",
        "blocking_",
        "ineligibility",
    ]

    if any(
        token in normalized
        for token
        in governance_tokens
    ):
        return True

    #
    # --------------------------------------------------------
    # Split metadata
    # --------------------------------------------------------
    #

    if normalized.startswith(
        "split_"
    ):
        return True

    #
    # --------------------------------------------------------
    # Generic technical metadata
    # --------------------------------------------------------
    #

    metadata_tokens = [
        "_version",
        "_semantics",
        "_policy",
        "_created_at",
        "created_at",
        "feature_windows",
    ]

    if any(
        token in normalized
        for token
        in metadata_tokens
    ):
        return True

    return False


# ============================================================
# Feature allowlist validation
# ============================================================

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

    NULL pode existir em determinadas
    features relacionais quando a operação
    matemática é estruturalmente indefinida,
    por exemplo:

        volatility_short / volatility_long

    quando:

        volatility_long == 0

    O tratamento desses NULLs pertence ao
    pipeline/modelo consumidor e não deve
    ser convertido artificialmente em
    infinito ou número arbitrário aqui.
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

    forbidden_columns = [
        column
        for column in feature_columns
        if is_forbidden_feature(
            column
        )
    ]

    if forbidden_columns:
        raise ValueError(
            "Features proibidas ou suspeitas "
            "no contrato: "
            f"{forbidden_columns}"
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

    print(
        "\n======================================"
    )
    print(
        "Feature Contract - Allowlist"
    )
    print(
        "======================================"
    )

    print(
        f"Features aprovadas: "
        f"{len(feature_columns)}"
    )

    for column in feature_columns:
        null_count = int(
            dataframe[
                column
            ]
            .isna()
            .sum()
        )

        print(
            f"  {column}: "
            f"{null_count:,} NULL"
        )

    print(
        "\nAllowlist aprovada."
    )


# ============================================================
# Structural feature-count validation
# ============================================================

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
          consecutivo de janelas

    Para [5, 10, 20]:

        1
        + (3 * 3)
        + (4 * 2)

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


# ============================================================
# Contract creation
# ============================================================

def get_feature_contract(
    dataframe: pd.DataFrame,
) -> FeatureContract:
    """
    Retorna o Feature Contract oficial
    completo.

    Ordem de validação:

    1. semântica upstream;
    2. descoberta das janelas;
    3. construção da allowlist;
    4. validação da quantidade;
    5. proteção contra leakage;
    6. validação numérica;
    7. criação do contrato imutável.
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

    contract = FeatureContract(
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

        corporate_action_value_semantics=(
            EXPECTED_CORPORATE_ACTION_VALUE_SEMANTICS
        ),

        corporate_action_policy=(
            EXPECTED_FEATURE_CORPORATE_ACTION_POLICY
        ),
    )

    print(
        "\n======================================"
    )
    print(
        "Feature Contract"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{contract.version}"
    )

    print(
        "Source Features: "
        f"{contract.source_feature_version}"
    )

    print(
        "Windows: "
        f"{list(contract.windows)}"
    )

    print(
        "Feature count: "
        f"{len(contract.features)}"
    )

    print(
        "Price semantics: "
        f"{contract.price_semantics}"
    )

    print(
        "Return semantics: "
        f"{contract.return_semantics}"
    )

    print(
        "Corporate Action value semantics: "
        f"{contract.corporate_action_value_semantics}"
    )

    print(
        "Corporate Action policy: "
        f"{contract.corporate_action_policy}"
    )

    return contract