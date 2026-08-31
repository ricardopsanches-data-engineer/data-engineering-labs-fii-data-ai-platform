from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


FEATURE_CONTRACT_VERSION = "v1"


@dataclass(frozen=True)
class FeatureContract:
    version: str
    windows: tuple[int, ...]
    features: tuple[str, ...]


def discover_feature_windows(
    dataframe: pd.DataFrame,
) -> list[int]:
    """
    Descobre as janelas temporais declaradas
    pela Gold ML.

    Esperado:
        feature_windows = "5,10,20"
    """

    if "feature_windows" not in dataframe.columns:
        raise ValueError(
            "Coluna feature_windows não encontrada."
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
                int(value.strip())
                for value in raw_windows.split(",")
                if value.strip()
            }
        )

    except ValueError as error:
        raise ValueError(
            "feature_windows possui formato inválido: "
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
    Constrói a allowlist oficial de features.

    Princípios do contrato v1:
    - evita duplicações decimal / percentual;
    - evita preço absoluto;
    - evita médias móveis absolutas;
    - privilegia retornos, volatilidade
      e relações normalizadas;
    - mantém relações entre janelas.
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


def validate_feature_contract(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> None:
    """
    Valida se todas as features oficiais
    existem no dataset.

    Também bloqueia qualquer coluna
    suspeita de leakage.
    """

    missing_columns = [
        column
        for column in feature_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Features do contrato ausentes "
            f"no dataset: {missing_columns}"
        )

    suspicious_columns = [
        column
        for column in feature_columns
        if (
            column.startswith("target_")
            or "next_" in column
            or column.endswith("_pct")
            or column
            in {
                "feature_date",
                "ticker",
                "cnpj",
                "codigo_cvm",
                "close_price",
                "trades_quantity",
                "observations_count",
            }
        )
    ]

    if suspicious_columns:
        raise ValueError(
            "Features proibidas ou suspeitas "
            f"no contrato: {suspicious_columns}"
        )


def get_feature_contract(
    dataframe: pd.DataFrame,
) -> FeatureContract:
    """
    Retorna o contrato completo pronto
    para ser utilizado pelos modelos.
    """

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
    )