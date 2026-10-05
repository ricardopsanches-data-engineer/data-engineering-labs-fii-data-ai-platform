from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.fii_daily_snapshot.builder import PROJECT_ROOT

DAILY_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "serving"
    / "daily"
    / "latest_snapshot.json"
)

ML_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "serving"
    / "ml"
    / "latest_inference_features.json"
)

AI_SERVING_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "serving"
    / "ai"
)

CONTEXT_DATASET_PATH = (
    AI_SERVING_BASE_DIR
    / "fii_structured_context.jsonl"
)

CONTEXT_MANIFEST_PATH = (
    AI_SERVING_BASE_DIR
    / "fii_structured_context.json"
)

CONTEXT_VERSION = "v1"

DAILY_REQUIRED_COLUMNS = [
    "trade_date",
    "ticker",
    "cnpj",
    "codigo_cvm",
    "denominacao_social",
    "situacao_cvm",
    "open_price",
    "low_price",
    "high_price",
    "average_price",
    "close_price",
    "trades_quantity",
    "intraday_variation",
    "intraday_variation_pct",
    "price_range",
    "price_range_pct",
    "ticker_resolution_status",
    "market_evidence_confidence",
]

ML_METADATA_COLUMNS = [
    "feature_date",
    "ticker",
    "feature_version",
    "source_price_history_version",
]


def load_json_manifest(
    path: Path,
) -> dict[str, Any]:
    """
    Carrega e valida um serving manifest.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Manifest não encontrado: {path}"
        )

    manifest = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if manifest.get("status") != "READY":
        raise ValueError(
            f"Manifest não está READY: {path}"
        )

    return manifest


def validate_manifest_dates(
    daily_manifest: dict[str, Any],
    ml_manifest: dict[str, Any],
) -> pd.Timestamp:
    """
    Garante que Data Serving e ML Serving
    representam o mesmo estado temporal.
    """

    daily_date = pd.to_datetime(
        daily_manifest["trade_date"],
        errors="raise",
    ).normalize()

    ml_date = pd.to_datetime(
        ml_manifest["feature_date"],
        errors="raise",
    ).normalize()

    if daily_date != ml_date:
        raise ValueError(
            "AI Retrieval freshness mismatch. "
            f"trade_date={daily_date.date()} "
            f"feature_date={ml_date.date()}"
        )

    return pd.Timestamp(
        daily_date
    )


def load_daily_snapshot(
    daily_manifest: dict[str, Any],
) -> pd.DataFrame:
    """
    Carrega o snapshot diário apontado pelo
    contrato da Phase 5.2.
    """

    local_path = PROJECT_ROOT / str(
        daily_manifest["local_path"]
    )

    if not local_path.exists():
        raise FileNotFoundError(
            "Daily Snapshot não encontrado: "
            f"{local_path}"
        )

    dataframe = pd.read_parquet(
        local_path
    )

    missing_columns = [
        column
        for column in DAILY_REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Daily Snapshot não possui "
            "colunas obrigatórias: "
            f"{missing_columns}"
        )

    return dataframe


def load_ml_serving_dataset(
    ml_manifest: dict[str, Any],
) -> pd.DataFrame:
    """
    Carrega o Latest Inference Dataset
    apontado pela Phase 5.3.
    """

    dataset_path = PROJECT_ROOT / str(
        ml_manifest["dataset_path"]
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            "ML Serving Dataset não encontrado: "
            f"{dataset_path}"
        )

    dataframe = pd.read_parquet(
        dataset_path
    )

    missing_columns = [
        column
        for column in ML_METADATA_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "ML Serving Dataset não possui "
            "metadata obrigatória: "
            f"{missing_columns}"
        )

    return dataframe


def validate_unique_ticker(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> None:
    """
    Structured Retrieval trabalha com um
    estado atual único por ticker.
    """

    if dataframe["ticker"].isna().any():
        raise ValueError(
            f"{dataset_name} possui ticker nulo."
        )

    duplicated = int(
        dataframe.duplicated(
            subset=["ticker"],
            keep=False,
        ).sum()
    )

    if duplicated > 0:
        raise ValueError(
            f"{dataset_name} possui "
            "ticker duplicado."
        )


def validate_source_alignment(
    daily: pd.DataFrame,
    ml: pd.DataFrame,
    serving_date: pd.Timestamp,
) -> None:
    """
    Valida alinhamento temporal e de entidades
    entre Data Serving e ML Serving.
    """

    validate_unique_ticker(
        daily,
        "Daily Snapshot",
    )

    validate_unique_ticker(
        ml,
        "ML Serving Dataset",
    )

    daily_dates = pd.to_datetime(
        daily["trade_date"],
        errors="coerce",
    ).dt.normalize()

    ml_dates = pd.to_datetime(
        ml["feature_date"],
        errors="coerce",
    ).dt.normalize()

    if daily_dates.isna().any():
        raise ValueError(
            "Daily Snapshot possui "
            "trade_date inválida."
        )

    if ml_dates.isna().any():
        raise ValueError(
            "ML Serving Dataset possui "
            "feature_date inválida."
        )

    if not (
        daily_dates
        == serving_date.normalize()
    ).all():
        raise ValueError(
            "Daily Snapshot contém data "
            "diferente da serving date."
        )

    if not (
        ml_dates
        == serving_date.normalize()
    ).all():
        raise ValueError(
            "ML Serving Dataset contém data "
            "diferente da serving date."
        )

    daily_tickers = set(
        daily["ticker"].astype(str)
    )

    ml_tickers = set(
        ml["ticker"].astype(str)
    )

    if daily_tickers != ml_tickers:
        only_daily = sorted(
            daily_tickers - ml_tickers
        )

        only_ml = sorted(
            ml_tickers - daily_tickers
        )

        raise ValueError(
            "Daily Snapshot e ML Serving "
            "possuem conjuntos diferentes "
            "de tickers. "
            f"only_daily={only_daily[:10]} "
            f"only_ml={only_ml[:10]}"
        )


def resolve_ml_feature_columns(
    ml: pd.DataFrame,
    ml_manifest: dict[str, Any],
) -> list[str]:
    """
    Descobre as features expostas pela camada
    de ML Serving.

    Não usa novamente o dataset histórico.
    """

    feature_columns = [
        column
        for column in ml.columns
        if column
        not in ML_METADATA_COLUMNS
    ]

    expected_count = int(
        ml_manifest["feature_count"]
    )

    if len(feature_columns) != expected_count:
        raise ValueError(
            "Quantidade de ML features "
            "incompatível com o manifest. "
            f"expected={expected_count} "
            f"actual={len(feature_columns)}"
        )

    return feature_columns


def to_json_value(
    value: Any,
) -> Any:
    """
    Converte valores pandas/numpy em tipos
    seguros para JSON.
    """

    if pd.isna(value):
        return None

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if hasattr(
        value,
        "item",
    ):
        try:
            return value.item()
        except ValueError:
            pass

    return value


def build_context_record(
    daily_row: pd.Series,
    ml_row: pd.Series,
    feature_columns: list[str],
    daily_manifest: dict[str, Any],
    ml_manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    Constrói um contexto governado por ticker.

    O registro contém fatos estruturados,
    não texto gerado por LLM.
    """

    ml_features = {
        column: to_json_value(
            ml_row[column]
        )
        for column in feature_columns
    }

    return {
        "context_version": CONTEXT_VERSION,
        "ticker": str(
            daily_row["ticker"]
        ),
        "identity": {
            "cnpj": str(
                daily_row["cnpj"]
            ),
            "codigo_cvm": str(
                daily_row["codigo_cvm"]
            ),
            "denominacao_social": str(
                daily_row[
                    "denominacao_social"
                ]
            ),
            "situacao_cvm": str(
                daily_row[
                    "situacao_cvm"
                ]
            ),
        },
        "market_state": {
            "trade_date": (
                pd.Timestamp(
                    daily_row["trade_date"]
                )
                .date()
                .isoformat()
            ),
            "open_price": to_json_value(
                daily_row["open_price"]
            ),
            "low_price": to_json_value(
                daily_row["low_price"]
            ),
            "high_price": to_json_value(
                daily_row["high_price"]
            ),
            "average_price": to_json_value(
                daily_row["average_price"]
            ),
            "close_price": to_json_value(
                daily_row["close_price"]
            ),
            "trades_quantity": to_json_value(
                daily_row[
                    "trades_quantity"
                ]
            ),
            "intraday_variation": to_json_value(
                daily_row[
                    "intraday_variation"
                ]
            ),
            "intraday_variation_pct": (
                to_json_value(
                    daily_row[
                        "intraday_variation_pct"
                    ]
                )
            ),
            "price_range": to_json_value(
                daily_row["price_range"]
            ),
            "price_range_pct": to_json_value(
                daily_row[
                    "price_range_pct"
                ]
            ),
            "ticker_resolution_status": str(
                daily_row[
                    "ticker_resolution_status"
                ]
            ),
            "market_evidence_confidence": str(
                daily_row[
                    "market_evidence_confidence"
                ]
            ),
        },
        "ml_state": {
            "feature_date": (
                pd.Timestamp(
                    ml_row["feature_date"]
                )
                .date()
                .isoformat()
            ),
            "feature_contract_version": str(
                ml_manifest[
                    "feature_contract_version"
                ]
            ),
            "feature_version": str(
                ml_row["feature_version"]
            ),
            "source_price_history_version": str(
                ml_row[
                    "source_price_history_version"
                ]
            ),
            "features": ml_features,
        },
        "provenance": {
            "daily_dataset": str(
                daily_manifest["dataset"]
            ),
            "daily_source": str(
                daily_manifest["local_path"]
            ),
            "ml_dataset": str(
                ml_manifest["dataset"]
            ),
            "ml_source": str(
                ml_manifest["dataset_path"]
            ),
        },
    }


def build_context_records(
    daily: pd.DataFrame,
    ml: pd.DataFrame,
    feature_columns: list[str],
    daily_manifest: dict[str, Any],
    ml_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Constrói um registro estruturado por ticker.
    """

    daily_indexed = (
        daily.set_index(
            "ticker",
            drop=False,
        )
    )

    ml_indexed = (
        ml.set_index(
            "ticker",
            drop=False,
        )
    )

    tickers = sorted(
        daily_indexed.index.astype(str)
    )

    records = []

    for ticker in tickers:
        daily_row = daily_indexed.loc[
            ticker
        ]

        ml_row = ml_indexed.loc[
            ticker
        ]

        record = build_context_record(
            daily_row=daily_row,
            ml_row=ml_row,
            feature_columns=feature_columns,
            daily_manifest=daily_manifest,
            ml_manifest=ml_manifest,
        )

        records.append(
            record
        )

    return records


def validate_context_records(
    records: list[dict[str, Any]],
) -> None:
    """
    Valida o contrato final do contexto.
    """

    if not records:
        raise ValueError(
            "AI Structured Context vazio."
        )

    tickers = [
        record["ticker"]
        for record in records
    ]

    if len(tickers) != len(set(tickers)):
        raise ValueError(
            "AI Structured Context possui "
            "ticker duplicado."
        )

    required_sections = [
        "identity",
        "market_state",
        "ml_state",
        "provenance",
    ]

    for record in records:
        missing_sections = [
            section
            for section in required_sections
            if section not in record
        ]

        if missing_sections:
            raise ValueError(
                "AI Structured Context possui "
                "seções ausentes: "
                f"{missing_sections}"
            )


def save_context_dataset(
    records: list[dict[str, Any]],
    destination: Path = (
        CONTEXT_DATASET_PATH
    ),
) -> None:
    """
    Persiste um JSONL determinístico,
    com uma linha por ticker.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

            file.write("\n")


def build_manifest(
    records: list[dict[str, Any]],
    serving_date: pd.Timestamp,
    feature_count: int,
) -> dict[str, Any]:
    """
    Constrói manifesto da camada de
    structured retrieval.
    """

    return {
        "dataset": (
            "fii_structured_context"
        ),
        "context_version": (
            CONTEXT_VERSION
        ),
        "status": "READY",
        "trade_date": (
            serving_date
            .date()
            .isoformat()
        ),
        "feature_date": (
            serving_date
            .date()
            .isoformat()
        ),
        "row_count": len(
            records
        ),
        "ticker_count": len(
            {
                record["ticker"]
                for record in records
            }
        ),
        "ml_feature_count": (
            feature_count
        ),
        "generated_at": (
            datetime.now(
                UTC
            ).isoformat()
        ),
        "dataset_path": (
            "data/serving/ai/"
            "fii_structured_context.jsonl"
        ),
    }


def save_manifest(
    manifest: dict[str, Any],
    destination: Path = (
        CONTEXT_MANIFEST_PATH
    ),
) -> None:
    """
    Persiste manifesto do AI Structured Context.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def retrieve_by_ticker(
    ticker: str,
    dataset_path: Path = (
        CONTEXT_DATASET_PATH
    ),
) -> dict[str, Any]:
    """
    Recuperação estruturada exata por ticker.

    Não usa similarity search.
    Não usa embeddings.
    """

    normalized_ticker = (
        ticker.strip().upper()
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            "AI Structured Context não "
            f"encontrado: {dataset_path}"
        )

    with dataset_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(
                line
            )

            if (
                str(
                    record.get(
                        "ticker",
                        "",
                    )
                ).upper()
                == normalized_ticker
            ):
                return record

    raise KeyError(
        "Ticker não encontrado no "
        f"structured context: {normalized_ticker}"
    )


def build_structured_retrieval_layer(
    daily_manifest_path: Path = (
        DAILY_MANIFEST_PATH
    ),
    ml_manifest_path: Path = (
        ML_MANIFEST_PATH
    ),
    dataset_destination: Path = (
        CONTEXT_DATASET_PATH
    ),
    manifest_destination: Path = (
        CONTEXT_MANIFEST_PATH
    ),
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    """
    Constrói a AI Structured Retrieval Foundation.
    """

    print(
        "======================================"
    )
    print(
        "AI STRUCTURED RETRIEVAL"
    )
    print(
        "======================================"
    )

    daily_manifest = load_json_manifest(
        daily_manifest_path
    )

    ml_manifest = load_json_manifest(
        ml_manifest_path
    )

    serving_date = validate_manifest_dates(
        daily_manifest=daily_manifest,
        ml_manifest=ml_manifest,
    )

    daily = load_daily_snapshot(
        daily_manifest
    )

    ml = load_ml_serving_dataset(
        ml_manifest
    )

    validate_source_alignment(
        daily=daily,
        ml=ml,
        serving_date=serving_date,
    )

    feature_columns = (
        resolve_ml_feature_columns(
            ml=ml,
            ml_manifest=ml_manifest,
        )
    )

    records = build_context_records(
        daily=daily,
        ml=ml,
        feature_columns=feature_columns,
        daily_manifest=daily_manifest,
        ml_manifest=ml_manifest,
    )

    validate_context_records(
        records
    )

    save_context_dataset(
        records=records,
        destination=dataset_destination,
    )

    manifest = build_manifest(
        records=records,
        serving_date=serving_date,
        feature_count=len(
            feature_columns
        ),
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
        "AI STRUCTURED CONTEXT READY"
    )
    print(
        "======================================"
    )

    print(
        f"Trade date:   "
        f"{manifest['trade_date']}"
    )

    print(
        f"Rows:         "
        f"{manifest['row_count']:,}"
    )

    print(
        f"Tickers:      "
        f"{manifest['ticker_count']:,}"
    )

    print(
        f"ML features:  "
        f"{manifest['ml_feature_count']}"
    )

    print(
        f"Context ver:  "
        f"{manifest['context_version']}"
    )

    print(
        f"Dataset:      "
        f"{dataset_destination}"
    )

    print(
        f"Manifest:     "
        f"{manifest_destination}"
    )

    return (
        records,
        manifest,
    )


def main() -> None:
    build_structured_retrieval_layer()


if __name__ == "__main__":
    main()