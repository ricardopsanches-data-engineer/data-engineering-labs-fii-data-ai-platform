from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ai.structured_retrieval.builder import (
    CONTEXT_DATASET_PATH,
    retrieve_by_ticker,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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

AI_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "serving"
    / "ai"
    / "fii_structured_context.json"
)

PRODUCT_VERSION = "v1"


def load_manifest(
    path: Path,
) -> dict[str, Any]:
    """
    Load a governed serving manifest.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Serving manifest not found: {path}"
        )

    manifest = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if manifest.get("status") != "READY":
        raise ValueError(
            "Serving manifest is not READY: "
            f"{path}"
        )

    return manifest


def validate_serving_alignment(
    daily_manifest: dict[str, Any],
    ml_manifest: dict[str, Any],
    ai_manifest: dict[str, Any],
) -> str:
    """
    Ensure all product-facing serving layers
    represent the same trusted business date.
    """

    daily_date = str(
        daily_manifest["trade_date"]
    )

    ml_date = str(
        ml_manifest["feature_date"]
    )

    ai_trade_date = str(
        ai_manifest["trade_date"]
    )

    ai_feature_date = str(
        ai_manifest["feature_date"]
    )

    dates = {
        daily_date,
        ml_date,
        ai_trade_date,
        ai_feature_date,
    }

    if len(dates) != 1:
        raise ValueError(
            "Serving contracts are not aligned. "
            f"daily={daily_date} "
            f"ml={ml_date} "
            f"ai_trade={ai_trade_date} "
            f"ai_feature={ai_feature_date}"
        )

    return daily_date


def validate_ticker_counts(
    daily_manifest: dict[str, Any],
    ml_manifest: dict[str, Any],
    ai_manifest: dict[str, Any],
) -> int:
    """
    Ensure product-facing serving contracts
    expose the same ticker population.
    """

    daily_count = int(
        daily_manifest["ticker_count"]
    )

    ml_count = int(
        ml_manifest["ticker_count"]
    )

    ai_count = int(
        ai_manifest["ticker_count"]
    )

    counts = {
        daily_count,
        ml_count,
        ai_count,
    }

    if len(counts) != 1:
        raise ValueError(
            "Serving ticker counts are not aligned. "
            f"daily={daily_count} "
            f"ml={ml_count} "
            f"ai={ai_count}"
        )

    return daily_count


def get_product_status() -> dict[str, Any]:
    """
    Return the governed product serving status.

    Consumers do not need to know internal
    storage paths or serving implementation
    details.
    """

    daily_manifest = load_manifest(
        DAILY_MANIFEST_PATH
    )

    ml_manifest = load_manifest(
        ML_MANIFEST_PATH
    )

    ai_manifest = load_manifest(
        AI_MANIFEST_PATH
    )

    business_date = (
        validate_serving_alignment(
            daily_manifest=daily_manifest,
            ml_manifest=ml_manifest,
            ai_manifest=ai_manifest,
        )
    )

    ticker_count = (
        validate_ticker_counts(
            daily_manifest=daily_manifest,
            ml_manifest=ml_manifest,
            ai_manifest=ai_manifest,
        )
    )

    return {
        "product_version": PRODUCT_VERSION,
        "status": "READY",
        "business_date": business_date,
        "ticker_count": ticker_count,
        "daily": {
            "dataset": daily_manifest[
                "dataset"
            ],
            "row_count": int(
                daily_manifest[
                    "row_count"
                ]
            ),
        },
        "ml": {
            "dataset": ml_manifest[
                "dataset"
            ],
            "feature_contract_version": (
                ml_manifest[
                    "feature_contract_version"
                ]
            ),
            "feature_version": (
                ml_manifest[
                    "feature_version"
                ]
            ),
            "feature_count": int(
                ml_manifest[
                    "feature_count"
                ]
            ),
        },
        "ai": {
            "dataset": ai_manifest[
                "dataset"
            ],
            "context_version": (
                ai_manifest[
                    "context_version"
                ]
            ),
            "ml_feature_count": int(
                ai_manifest[
                    "ml_feature_count"
                ]
            ),
        },
    }


def get_fii_context(
    ticker: str,
) -> dict[str, Any]:
    """
    Product-facing exact FII lookup.

    The consumer is isolated from JSONL,
    S3 paths, and internal retrieval logic.
    """

    status = get_product_status()

    record = retrieve_by_ticker(
        ticker=ticker,
        dataset_path=CONTEXT_DATASET_PATH,
    )

    return {
        "product_version": PRODUCT_VERSION,
        "status": "READY",
        "business_date": status[
            "business_date"
        ],
        "data": record,
    }