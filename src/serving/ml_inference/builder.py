from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.fii_daily_snapshot.builder import PROJECT_ROOT
from src.ml.common.feature_contract import (
    FeatureContract,
    get_feature_contract,
)
from src.serving.daily_consumption.builder import (
    LATEST_SNAPSHOT_PATH,
)

FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_features"
    / "fii_features.parquet"
)

ML_SERVING_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "serving"
    / "ml"
)

LATEST_INFERENCE_DATASET_PATH = (
    ML_SERVING_BASE_DIR
    / "latest_inference_features.parquet"
)

LATEST_INFERENCE_MANIFEST_PATH = (
    ML_SERVING_BASE_DIR
    / "latest_inference_features.json"
)

REQUIRED_FEATURE_METADATA = [
    "feature_date",
    "ticker",
    "feature_ready",
    "feature_version",
    "source_price_history_version",
]


def load_daily_consumption_manifest(
    path: Path = LATEST_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """
    Carrega o contrato de consumo diário.

    A trade_date declarada READY pela camada
    diária é a referência temporal oficial
    para ML Serving.
    """

    if not path.exists():
        raise FileNotFoundError(
            "Daily Consumption manifest "
            f"não encontrado: {path}"
        )

    manifest = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    required_fields = [
        "dataset",
        "status",
        "trade_date",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in manifest
    ]

    if missing_fields:
        raise ValueError(
            "Daily Consumption manifest "
            "incompleto: "
            f"{missing_fields}"
        )

    if manifest["status"] != "READY":
        raise ValueError(
            "Daily Consumption Layer "
            "não está READY."
        )

    return manifest


def load_features(
    path: Path = FEATURES_PATH,
) -> pd.DataFrame:
    """
    Carrega o histórico governado de features.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"FII Features não encontrado: {path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    missing_columns = [
        column
        for column in REQUIRED_FEATURE_METADATA
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "FII Features não possui "
            "metadata obrigatória: "
            f"{missing_columns}"
        )

    if dataframe.empty:
        raise ValueError(
            "FII Features está vazio."
        )

    return dataframe


def resolve_serving_date(
    daily_manifest: dict[str, Any],
) -> pd.Timestamp:
    """
    Resolve a data oficial para serving.

    Não usa datetime.now(), calendário civil
    ou max(feature_date) isoladamente.

    A referência vem da Daily Consumption Layer.
    """

    serving_date = pd.to_datetime(
        daily_manifest["trade_date"],
        errors="raise",
    ).normalize()

    return pd.Timestamp(
        serving_date
    )


def validate_feature_freshness(
    features: pd.DataFrame,
    serving_date: pd.Timestamp,
) -> None:
    """
    Garante reconciliação temporal entre
    Gold ML e Daily Consumption.
    """

    feature_dates = pd.to_datetime(
        features["feature_date"],
        errors="coerce",
    ).dt.normalize()

    if feature_dates.isna().any():
        raise ValueError(
            "FII Features possui "
            "feature_date inválida."
        )

    latest_feature_date = pd.Timestamp(
        feature_dates.max()
    )

    if latest_feature_date != (
        serving_date.normalize()
    ):
        raise ValueError(
            "ML Serving freshness mismatch. "
            f"daily_serving_date={serving_date.date()} "
            f"latest_feature_date="
            f"{latest_feature_date.date()}"
        )


def select_latest_features(
    features: pd.DataFrame,
    serving_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Seleciona somente o estado de features
    correspondente à data oficial de serving.
    """

    feature_dates = pd.to_datetime(
        features["feature_date"],
        errors="raise",
    ).dt.normalize()

    latest = features.loc[
        feature_dates
        == serving_date.normalize()
    ].copy()

    if latest.empty:
        raise ValueError(
            "Nenhuma feature encontrada para "
            "a data oficial de serving."
        )

    return latest


def select_inference_ready_rows(
    latest_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Seleciona somente linhas prontas para
    inferência.

    Training eligibility não é usada aqui.

    feature_ready representa disponibilidade
    contemporânea das features.
    """

    feature_ready = (
        latest_features["feature_ready"]
        .fillna(False)
        .astype(bool)
    )

    inference_ready = (
        latest_features.loc[
            feature_ready
        ]
        .copy()
    )

    if inference_ready.empty:
        raise ValueError(
            "Nenhuma linha inference-ready "
            "na data de serving."
        )

    return inference_ready


def validate_inference_keys(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida granularidade operacional do
    dataset de inferência.
    """

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Latest Inference Dataset possui "
            "duplicidade em "
            "(feature_date, ticker)."
        )

    if dataframe["ticker"].isna().any():
        raise ValueError(
            "Latest Inference Dataset possui "
            "ticker nulo."
        )


def build_inference_dataset(
    inference_ready: pd.DataFrame,
    contract: FeatureContract,
) -> pd.DataFrame:
    """
    Materializa somente:

    - feature_date;
    - ticker;
    - metadata mínima de contrato;
    - allowlist oficial de features.

    Nenhum target ou metadata de treinamento
    é exposto ao consumidor de inferência.
    """

    output_columns = [
        "feature_date",
        "ticker",
        "feature_version",
        "source_price_history_version",
        *contract.features,
    ]

    missing_columns = [
        column
        for column in output_columns
        if column not in inference_ready.columns
    ]

    if missing_columns:
        raise ValueError(
            "Latest Inference Dataset possui "
            "colunas obrigatórias ausentes: "
            f"{missing_columns}"
        )

    inference_dataset = (
        inference_ready[
            output_columns
        ]
        .copy()
        .sort_values(
            by=[
                "feature_date",
                "ticker",
            ],
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )

    return inference_dataset


def validate_inference_dataset(
    dataframe: pd.DataFrame,
    contract: FeatureContract,
) -> None:
    """
    Valida o contrato final de serving ML.
    """

    if dataframe.empty:
        raise ValueError(
            "Latest Inference Dataset vazio."
        )

    validate_inference_keys(
        dataframe
    )

    feature_dates = (
        pd.to_datetime(
            dataframe["feature_date"],
            errors="coerce",
        )
        .dt.normalize()
        .dropna()
        .unique()
    )

    if len(feature_dates) != 1:
        raise ValueError(
            "Latest Inference Dataset deve "
            "conter uma única feature_date."
        )

    forbidden_tokens = [
        "target",
        "ml_eligible",
        "eligibility",
        "split_",
        "prediction",
    ]

    forbidden_columns = [
        column
        for column in dataframe.columns
        if any(
            token in column.lower()
            for token in forbidden_tokens
        )
    ]

    if forbidden_columns:
        raise ValueError(
            "Latest Inference Dataset contém "
            "colunas proibidas: "
            f"{forbidden_columns}"
        )

    missing_features = [
        feature
        for feature in contract.features
        if feature not in dataframe.columns
    ]

    if missing_features:
        raise ValueError(
            "Feature Contract incompleto no "
            "dataset de inferência: "
            f"{missing_features}"
        )


def save_inference_dataset(
    dataframe: pd.DataFrame,
    destination: Path = (
        LATEST_INFERENCE_DATASET_PATH
    ),
) -> None:
    """
    Persiste Latest Inference Dataset.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )


def build_manifest(
    dataframe: pd.DataFrame,
    contract: FeatureContract,
    serving_date: pd.Timestamp,
) -> dict[str, Any]:
    """
    Constrói metadata operacional do
    Latest Inference Dataset.
    """

    feature_version_values = (
        dataframe["feature_version"]
        .dropna()
        .astype(str)
        .unique()
    )

    source_version_values = (
        dataframe[
            "source_price_history_version"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(feature_version_values) != 1:
        raise ValueError(
            "Mais de uma feature_version "
            "no Latest Inference Dataset."
        )

    if len(source_version_values) != 1:
        raise ValueError(
            "Mais de uma "
            "source_price_history_version "
            "no Latest Inference Dataset."
        )

    return {
        "dataset": (
            "latest_inference_features"
        ),
        "status": "READY",
        "feature_date": (
            serving_date
            .date()
            .isoformat()
        ),
        "row_count": int(
            len(dataframe)
        ),
        "ticker_count": int(
            dataframe["ticker"].nunique()
        ),
        "feature_count": int(
            len(contract.features)
        ),
        "feature_contract_version": (
            contract.version
        ),
        "feature_version": str(
            feature_version_values[0]
        ),
        "source_price_history_version": str(
            source_version_values[0]
        ),
        "generated_at": (
            datetime.now(
                UTC
            ).isoformat()
        ),
        "dataset_path": (
            "data/serving/ml/"
            "latest_inference_features.parquet"
        ),
    }


def save_manifest(
    manifest: dict[str, Any],
    destination: Path = (
        LATEST_INFERENCE_MANIFEST_PATH
    ),
) -> None:
    """
    Persiste manifesto ML Serving.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_ml_serving_layer(
    features_path: Path = FEATURES_PATH,
    daily_manifest_path: Path = (
        LATEST_SNAPSHOT_PATH
    ),
    dataset_destination: Path = (
        LATEST_INFERENCE_DATASET_PATH
    ),
    manifest_destination: Path = (
        LATEST_INFERENCE_MANIFEST_PATH
    ),
) -> tuple[
    pd.DataFrame,
    dict[str, Any],
]:
    """
    Constrói a fundação de ML Serving.

    Fluxo:

    Daily Consumption date
            +
    governed historical features
            +
    official Feature Contract
            |
            v
    Latest Inference Dataset
    """

    print(
        "======================================"
    )
    print(
        "ML SERVING FOUNDATION"
    )
    print(
        "======================================"
    )

    daily_manifest = (
        load_daily_consumption_manifest(
            daily_manifest_path
        )
    )

    serving_date = resolve_serving_date(
        daily_manifest
    )

    features = load_features(
        features_path
    )

    validate_feature_freshness(
        features=features,
        serving_date=serving_date,
    )

    contract = get_feature_contract(
        features
    )

    latest_features = (
        select_latest_features(
            features=features,
            serving_date=serving_date,
        )
    )

    inference_ready = (
        select_inference_ready_rows(
            latest_features
        )
    )

    validate_inference_keys(
        inference_ready
    )

    inference_dataset = (
        build_inference_dataset(
            inference_ready=inference_ready,
            contract=contract,
        )
    )

    validate_inference_dataset(
        dataframe=inference_dataset,
        contract=contract,
    )

    save_inference_dataset(
        dataframe=inference_dataset,
        destination=dataset_destination,
    )

    manifest = build_manifest(
        dataframe=inference_dataset,
        contract=contract,
        serving_date=serving_date,
    )

    save_manifest(
        manifest=manifest,
        destination=manifest_destination,
    )

    print()
    print(
        "======================================"
    )
    print(
        "LATEST INFERENCE DATASET READY"
    )
    print(
        "======================================"
    )

    print(
        f"Feature date:   "
        f"{manifest['feature_date']}"
    )

    print(
        f"Rows:           "
        f"{manifest['row_count']:,}"
    )

    print(
        f"Tickers:        "
        f"{manifest['ticker_count']:,}"
    )

    print(
        f"Features:       "
        f"{manifest['feature_count']}"
    )

    print(
        "Feature contract: "
        f"{manifest['feature_contract_version']}"
    )

    print(
        f"Dataset:        "
        f"{dataset_destination}"
    )

    print(
        f"Manifest:       "
        f"{manifest_destination}"
    )

    return (
        inference_dataset,
        manifest,
    )


def main() -> None:
    build_ml_serving_layer()


if __name__ == "__main__":
    main()