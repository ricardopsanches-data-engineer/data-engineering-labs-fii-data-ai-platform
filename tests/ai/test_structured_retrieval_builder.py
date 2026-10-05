from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import src.ai.structured_retrieval.builder as builder


def build_daily() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                [
                    "2026-08-28",
                    "2026-08-28",
                ]
            ),
            "ticker": [
                "HGLG11",
                "KNRI11",
            ],
            "cnpj": [
                "11111111000111",
                "22222222000122",
            ],
            "codigo_cvm": [
                "1001",
                "1002",
            ],
            "denominacao_social": [
                "FII HGLG",
                "FII KNRI",
            ],
            "situacao_cvm": [
                "Em Funcionamento Normal",
                "Em Funcionamento Normal",
            ],
            "open_price": [
                100.0,
                120.0,
            ],
            "low_price": [
                99.0,
                119.0,
            ],
            "high_price": [
                102.0,
                123.0,
            ],
            "average_price": [
                101.0,
                121.0,
            ],
            "close_price": [
                101.5,
                122.0,
            ],
            "trades_quantity": [
                1000,
                2000,
            ],
            "intraday_variation": [
                1.5,
                2.0,
            ],
            "intraday_variation_pct": [
                1.5,
                1.666,
            ],
            "price_range": [
                3.0,
                4.0,
            ],
            "price_range_pct": [
                3.03,
                3.36,
            ],
            "ticker_resolution_status": [
                "SINGLE_TICKER",
                "SINGLE_TICKER",
            ],
            "market_evidence_confidence": [
                "HIGH",
                "HIGH",
            ],
        }
    )


def build_ml() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature_date": pd.to_datetime(
                [
                    "2026-08-28",
                    "2026-08-28",
                ]
            ),
            "ticker": [
                "HGLG11",
                "KNRI11",
            ],
            "feature_version": [
                "v7",
                "v7",
            ],
            "source_price_history_version": [
                "v3",
                "v3",
            ],
            "feature_a": [
                1.0,
                2.0,
            ],
            "feature_b": [
                10.0,
                20.0,
            ],
        }
    )


def build_daily_manifest() -> dict[str, object]:
    return {
        "dataset": "fii_daily_snapshot",
        "status": "READY",
        "trade_date": "2026-08-28",
        "local_path": (
            "data/gold/analytics/"
            "fii_daily_snapshot/"
            "snapshot.parquet"
        ),
    }


def build_ml_manifest() -> dict[str, object]:
    return {
        "dataset": (
            "latest_inference_features"
        ),
        "status": "READY",
        "feature_date": "2026-08-28",
        "feature_count": 2,
        "feature_contract_version": "v3",
        "dataset_path": (
            "data/serving/ml/"
            "latest_inference_features.parquet"
        ),
    }


def test_validate_manifest_dates_accepts_match() -> None:
    result = builder.validate_manifest_dates(
        daily_manifest=(
            build_daily_manifest()
        ),
        ml_manifest=(
            build_ml_manifest()
        ),
    )

    assert result == pd.Timestamp(
        "2026-08-28"
    )


def test_validate_manifest_dates_rejects_mismatch() -> None:
    ml_manifest = build_ml_manifest()

    ml_manifest["feature_date"] = (
        "2026-08-27"
    )

    with pytest.raises(
        ValueError,
        match="freshness mismatch",
    ):
        builder.validate_manifest_dates(
            daily_manifest=(
                build_daily_manifest()
            ),
            ml_manifest=ml_manifest,
        )


def test_validate_source_alignment_accepts_match() -> None:
    builder.validate_source_alignment(
        daily=build_daily(),
        ml=build_ml(),
        serving_date=pd.Timestamp(
            "2026-08-28"
        ),
    )


def test_validate_source_alignment_rejects_ticker_difference() -> None:
    ml = build_ml()

    ml.loc[
        ml["ticker"] == "KNRI11",
        "ticker",
    ] = "XPML11"

    with pytest.raises(
        ValueError,
        match="conjuntos diferentes",
    ):
        builder.validate_source_alignment(
            daily=build_daily(),
            ml=ml,
            serving_date=pd.Timestamp(
                "2026-08-28"
            ),
        )


def test_resolve_ml_feature_columns() -> None:
    result = (
        builder.resolve_ml_feature_columns(
            ml=build_ml(),
            ml_manifest=(
                build_ml_manifest()
            ),
        )
    )

    assert result == [
        "feature_a",
        "feature_b",
    ]


def test_build_context_records() -> None:
    records = builder.build_context_records(
        daily=build_daily(),
        ml=build_ml(),
        feature_columns=[
            "feature_a",
            "feature_b",
        ],
        daily_manifest=(
            build_daily_manifest()
        ),
        ml_manifest=(
            build_ml_manifest()
        ),
    )

    assert len(records) == 2

    first = records[0]

    assert first["ticker"] == "HGLG11"

    assert (
        first["market_state"]["trade_date"]
        == "2026-08-28"
    )

    assert (
        first["ml_state"]["feature_date"]
        == "2026-08-28"
    )

    assert first["ml_state"]["features"] == {
        "feature_a": 1.0,
        "feature_b": 10.0,
    }


def test_context_contains_no_generated_text() -> None:
    records = builder.build_context_records(
        daily=build_daily(),
        ml=build_ml(),
        feature_columns=[
            "feature_a",
            "feature_b",
        ],
        daily_manifest=(
            build_daily_manifest()
        ),
        ml_manifest=(
            build_ml_manifest()
        ),
    )

    serialized = json.dumps(
        records,
        ensure_ascii=False,
    ).lower()

    assert "prompt" not in serialized
    assert "completion" not in serialized
    assert "answer" not in serialized


def test_retrieve_by_ticker(
    tmp_path: Path,
) -> None:
    dataset_path = (
        tmp_path
        / "context.jsonl"
    )

    records = builder.build_context_records(
        daily=build_daily(),
        ml=build_ml(),
        feature_columns=[
            "feature_a",
            "feature_b",
        ],
        daily_manifest=(
            build_daily_manifest()
        ),
        ml_manifest=(
            build_ml_manifest()
        ),
    )

    builder.save_context_dataset(
        records=records,
        destination=dataset_path,
    )

    result = builder.retrieve_by_ticker(
        "hglg11",
        dataset_path=dataset_path,
    )

    assert result["ticker"] == "HGLG11"


def test_retrieve_by_ticker_rejects_unknown(
    tmp_path: Path,
) -> None:
    dataset_path = (
        tmp_path
        / "context.jsonl"
    )

    records = builder.build_context_records(
        daily=build_daily(),
        ml=build_ml(),
        feature_columns=[
            "feature_a",
            "feature_b",
        ],
        daily_manifest=(
            build_daily_manifest()
        ),
        ml_manifest=(
            build_ml_manifest()
        ),
    )

    builder.save_context_dataset(
        records=records,
        destination=dataset_path,
    )

    with pytest.raises(
        KeyError,
        match="Ticker não encontrado",
    ):
        builder.retrieve_by_ticker(
            "INVALID11",
            dataset_path=dataset_path,
        )