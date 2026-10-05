from __future__ import annotations

from pathlib import Path

import pandas as pd

import src.pipelines.ml_inference_serving_to_s3 as pipeline


def build_dataframe() -> pd.DataFrame:
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


def build_manifest(
    generated_at: str,
    feature_date: str = "2026-08-28",
) -> dict[str, object]:
    return {
        "dataset": (
            "latest_inference_features"
        ),
        "status": "READY",
        "feature_date": feature_date,
        "row_count": 2,
        "ticker_count": 2,
        "feature_count": 2,
        "feature_contract_version": "v3",
        "feature_version": "v7",
        "source_price_history_version": "v3",
        "dataset_path": (
            "data/serving/ml/"
            "latest_inference_features.parquet"
        ),
        "generated_at": generated_at,
    }


def test_dataframe_sha_is_order_independent() -> None:
    first = build_dataframe()

    second = (
        first.iloc[::-1]
        .reset_index(
            drop=True
        )
    )

    first_sha = (
        pipeline.calculate_dataframe_content_sha256(
            first
        )
    )

    second_sha = (
        pipeline.calculate_dataframe_content_sha256(
            second
        )
    )

    assert first_sha == second_sha


def test_dataframe_sha_changes_when_feature_changes() -> None:
    first = build_dataframe()

    second = build_dataframe()

    second.loc[
        second["ticker"] == "HGLG11",
        "feature_a",
    ] = 999.0

    first_sha = (
        pipeline.calculate_dataframe_content_sha256(
            first
        )
    )

    second_sha = (
        pipeline.calculate_dataframe_content_sha256(
            second
        )
    )

    assert first_sha != second_sha


def test_manifest_sha_ignores_generated_at() -> None:
    first = build_manifest(
        "2026-10-05T10:00:00+00:00"
    )

    second = build_manifest(
        "2026-10-05T11:00:00+00:00"
    )

    first_sha = (
        pipeline.calculate_manifest_content_sha256(
            first
        )
    )

    second_sha = (
        pipeline.calculate_manifest_content_sha256(
            second
        )
    )

    assert first_sha == second_sha


def test_manifest_sha_changes_when_feature_date_changes() -> None:
    first = build_manifest(
        "2026-10-05T10:00:00+00:00",
        feature_date="2026-08-28",
    )

    second = build_manifest(
        "2026-10-05T11:00:00+00:00",
        feature_date="2026-08-29",
    )

    first_sha = (
        pipeline.calculate_manifest_content_sha256(
            first
        )
    )

    second_sha = (
        pipeline.calculate_manifest_content_sha256(
            second
        )
    )

    assert first_sha != second_sha


def test_publish_dataset_uses_expected_s3_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataframe = build_dataframe()

    local_path = (
        tmp_path
        / "latest_inference_features.parquet"
    )

    dataframe.to_parquet(
        local_path,
        index=False,
    )

    captured: dict[str, object] = {}

    def fake_upload_file(
        *,
        local_path,
        bucket_name,
        s3_key,
        content_sha256,
        force,
    ):
        captured["local_path"] = local_path
        captured["bucket_name"] = bucket_name
        captured["s3_key"] = s3_key
        captured["content_sha256"] = (
            content_sha256
        )
        captured["force"] = force

        return (
            f"s3://{bucket_name}/{s3_key}"
        )

    monkeypatch.setattr(
        pipeline,
        "upload_file",
        fake_upload_file,
    )

    result = pipeline.publish_dataset(
        dataframe=dataframe,
        local_path=local_path,
    )

    assert captured["s3_key"] == (
        "serving/ml/"
        "latest_inference_features.parquet"
    )

    assert captured["force"] is False

    assert result == (
        f"s3://{pipeline.BUCKET_NAME}/"
        "serving/ml/"
        "latest_inference_features.parquet"
    )


def test_publish_manifest_uses_expected_s3_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = build_manifest(
        "2026-10-05T10:00:00+00:00"
    )

    local_path = (
        tmp_path
        / "latest_inference_features.json"
    )

    local_path.write_text(
        "{}",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_upload_file(
        *,
        local_path,
        bucket_name,
        s3_key,
        content_sha256,
        force,
    ):
        captured["local_path"] = local_path
        captured["bucket_name"] = bucket_name
        captured["s3_key"] = s3_key
        captured["content_sha256"] = (
            content_sha256
        )
        captured["force"] = force

        return (
            f"s3://{bucket_name}/{s3_key}"
        )

    monkeypatch.setattr(
        pipeline,
        "upload_file",
        fake_upload_file,
    )

    result = pipeline.publish_manifest(
        manifest=manifest,
        local_path=local_path,
    )

    assert captured["s3_key"] == (
        "serving/ml/"
        "latest_inference_features.json"
    )

    assert captured["force"] is False

    assert result == (
        f"s3://{pipeline.BUCKET_NAME}/"
        "serving/ml/"
        "latest_inference_features.json"
    )