from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.product.service as service


def write_manifest(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )


def daily_manifest() -> dict:
    return {
        "dataset": "fii_daily_snapshot",
        "status": "READY",
        "trade_date": "2026-08-28",
        "row_count": 267,
        "ticker_count": 267,
    }


def ml_manifest() -> dict:
    return {
        "dataset": (
            "latest_inference_features"
        ),
        "status": "READY",
        "feature_date": "2026-08-28",
        "feature_contract_version": "v3",
        "feature_version": "v7",
        "feature_count": 18,
        "row_count": 267,
        "ticker_count": 267,
    }


def ai_manifest() -> dict:
    return {
        "dataset": (
            "fii_structured_context"
        ),
        "context_version": "v1",
        "status": "READY",
        "trade_date": "2026-08-28",
        "feature_date": "2026-08-28",
        "ml_feature_count": 18,
        "row_count": 267,
        "ticker_count": 267,
    }


def test_validate_serving_alignment() -> None:
    result = (
        service.validate_serving_alignment(
            daily_manifest=daily_manifest(),
            ml_manifest=ml_manifest(),
            ai_manifest=ai_manifest(),
        )
    )

    assert result == "2026-08-28"


def test_validate_serving_alignment_rejects_mismatch() -> None:
    ml = ml_manifest()

    ml["feature_date"] = (
        "2026-08-27"
    )

    with pytest.raises(
        ValueError,
        match="not aligned",
    ):
        service.validate_serving_alignment(
            daily_manifest=daily_manifest(),
            ml_manifest=ml,
            ai_manifest=ai_manifest(),
        )


def test_validate_ticker_counts() -> None:
    result = service.validate_ticker_counts(
        daily_manifest=daily_manifest(),
        ml_manifest=ml_manifest(),
        ai_manifest=ai_manifest(),
    )

    assert result == 267


def test_validate_ticker_counts_rejects_mismatch() -> None:
    ai = ai_manifest()

    ai["ticker_count"] = 266

    with pytest.raises(
        ValueError,
        match="ticker counts",
    ):
        service.validate_ticker_counts(
            daily_manifest=daily_manifest(),
            ml_manifest=ml_manifest(),
            ai_manifest=ai,
        )


def test_load_manifest_requires_ready(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "manifest.json"
    )

    write_manifest(
        path,
        {
            "status": "NOT_READY",
        },
    )

    with pytest.raises(
        ValueError,
        match="not READY",
    ):
        service.load_manifest(
            path
        )


def test_get_product_status(
    tmp_path: Path,
    monkeypatch,
) -> None:
    daily_path = (
        tmp_path
        / "daily.json"
    )

    ml_path = (
        tmp_path
        / "ml.json"
    )

    ai_path = (
        tmp_path
        / "ai.json"
    )

    write_manifest(
        daily_path,
        daily_manifest(),
    )

    write_manifest(
        ml_path,
        ml_manifest(),
    )

    write_manifest(
        ai_path,
        ai_manifest(),
    )

    monkeypatch.setattr(
        service,
        "DAILY_MANIFEST_PATH",
        daily_path,
    )

    monkeypatch.setattr(
        service,
        "ML_MANIFEST_PATH",
        ml_path,
    )

    monkeypatch.setattr(
        service,
        "AI_MANIFEST_PATH",
        ai_path,
    )

    result = (
        service.get_product_status()
    )

    assert result[
        "product_version"
    ] == "v1"

    assert result[
        "status"
    ] == "READY"

    assert result[
        "business_date"
    ] == "2026-08-28"

    assert result[
        "ticker_count"
    ] == 267

    assert result[
        "ml"
    ][
        "feature_count"
    ] == 18

    assert result[
        "ai"
    ][
        "context_version"
    ] == "v1"


def test_get_fii_context(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        service,
        "get_product_status",
        lambda: {
            "product_version": "v1",
            "status": "READY",
            "business_date": (
                "2026-08-28"
            ),
        },
    )

    monkeypatch.setattr(
        service,
        "retrieve_by_ticker",
        lambda ticker, dataset_path: {
            "ticker": ticker.upper(),
            "context_version": "v1",
        },
    )

    result = service.get_fii_context(
        "ggrc11"
    )

    assert result[
        "product_version"
    ] == "v1"

    assert result[
        "business_date"
    ] == "2026-08-28"

    assert result[
        "data"
    ][
        "ticker"
    ] == "GGRC11"