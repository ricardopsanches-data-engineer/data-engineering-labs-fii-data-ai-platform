from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import src.serving.ml_inference.builder as builder


class FakeFeatureContract:
    version = "v-test"
    features = (
        "feature_a",
        "feature_b",
    )


def build_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature_date": pd.to_datetime(
                [
                    "2026-08-27",
                    "2026-08-28",
                    "2026-08-28",
                ]
            ),
            "ticker": [
                "HGLG11",
                "HGLG11",
                "KNRI11",
            ],
            "feature_ready": [
                True,
                True,
                True,
            ],
            "feature_version": [
                "v7",
                "v7",
                "v7",
            ],
            "source_price_history_version": [
                "v3",
                "v3",
                "v3",
            ],
            "feature_a": [
                1.0,
                2.0,
                3.0,
            ],
            "feature_b": [
                10.0,
                20.0,
                30.0,
            ],
            "target_return_next_5d": [
                0.1,
                0.2,
                0.3,
            ],
            "ml_eligible": [
                True,
                False,
                False,
            ],
        }
    )


def test_resolve_serving_date() -> None:
    manifest = {
        "dataset": "fii_daily_snapshot",
        "status": "READY",
        "trade_date": "2026-08-28",
    }

    result = builder.resolve_serving_date(
        manifest
    )

    assert result == pd.Timestamp(
        "2026-08-28"
    )


def test_validate_feature_freshness_accepts_match() -> None:
    features = build_features()

    builder.validate_feature_freshness(
        features=features,
        serving_date=pd.Timestamp(
            "2026-08-28"
        ),
    )


def test_validate_feature_freshness_rejects_mismatch() -> None:
    features = build_features()

    with pytest.raises(
        ValueError,
        match="freshness mismatch",
    ):
        builder.validate_feature_freshness(
            features=features,
            serving_date=pd.Timestamp(
                "2026-08-29"
            ),
        )


def test_select_latest_features() -> None:
    features = build_features()

    result = builder.select_latest_features(
        features=features,
        serving_date=pd.Timestamp(
            "2026-08-28"
        ),
    )

    assert len(result) == 2

    assert (
        result["feature_date"]
        == pd.Timestamp(
            "2026-08-28"
        )
    ).all()


def test_inference_readiness_does_not_use_ml_eligibility() -> None:
    features = build_features()

    latest = builder.select_latest_features(
        features=features,
        serving_date=pd.Timestamp(
            "2026-08-28"
        ),
    )

    result = (
        builder.select_inference_ready_rows(
            latest
        )
    )

    assert len(result) == 2

    assert (
        result["feature_ready"]
        .all()
    )

    assert (
        result["ml_eligible"]
        .sum()
        == 0
    )


def test_build_inference_dataset_uses_allowlist() -> None:
    features = build_features()

    latest = builder.select_latest_features(
        features=features,
        serving_date=pd.Timestamp(
            "2026-08-28"
        ),
    )

    ready = (
        builder.select_inference_ready_rows(
            latest
        )
    )

    result = builder.build_inference_dataset(
        inference_ready=ready,
        contract=FakeFeatureContract(),
    )

    assert result.columns.tolist() == [
        "feature_date",
        "ticker",
        "feature_version",
        "source_price_history_version",
        "feature_a",
        "feature_b",
    ]

    assert (
        "target_return_next_5d"
        not in result.columns
    )

    assert (
        "ml_eligible"
        not in result.columns
    )


def test_validate_inference_keys_rejects_duplicates() -> None:
    features = build_features()

    duplicated = pd.concat(
        [
            features.iloc[[1]],
            features.iloc[[1]],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicidade",
    ):
        builder.validate_inference_keys(
            duplicated
        )


def test_build_manifest() -> None:
    dataframe = pd.DataFrame(
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

    manifest = builder.build_manifest(
        dataframe=dataframe,
        contract=FakeFeatureContract(),
        serving_date=pd.Timestamp(
            "2026-08-28"
        ),
    )

    assert manifest["status"] == "READY"
    assert manifest["feature_date"] == (
        "2026-08-28"
    )
    assert manifest["row_count"] == 2
    assert manifest["ticker_count"] == 2
    assert manifest["feature_count"] == 2
    assert manifest["feature_version"] == "v7"


def test_full_local_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features_path = (
        tmp_path
        / "fii_features.parquet"
    )

    manifest_path = (
        tmp_path
        / "latest_snapshot.json"
    )

    output_path = (
        tmp_path
        / "latest_inference_features.parquet"
    )

    output_manifest_path = (
        tmp_path
        / "latest_inference_features.json"
    )

    features = build_features()

    features.to_parquet(
        features_path,
        index=False,
    )

    manifest_path.write_text(
        json.dumps(
            {
                "dataset": (
                    "fii_daily_snapshot"
                ),
                "status": "READY",
                "trade_date": "2026-08-28",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        builder,
        "get_feature_contract",
        lambda dataframe: (
            FakeFeatureContract()
        ),
    )

    dataset, manifest = (
        builder.build_ml_serving_layer(
            features_path=features_path,
            daily_manifest_path=manifest_path,
            dataset_destination=output_path,
            manifest_destination=(
                output_manifest_path
            ),
        )
    )

    assert output_path.exists()
    assert output_manifest_path.exists()

    assert len(dataset) == 2

    assert dataset.columns.tolist() == [
        "feature_date",
        "ticker",
        "feature_version",
        "source_price_history_version",
        "feature_a",
        "feature_b",
    ]

    assert manifest["status"] == "READY"
    assert manifest["feature_date"] == (
        "2026-08-28"
    )