from __future__ import annotations

from pathlib import Path

import src.pipelines.daily_consumption_to_s3 as pipeline


def build_manifest(
    generated_at: str,
    trade_date: str = "2026-08-28",
) -> dict[str, object]:
    return {
        "dataset": "fii_daily_snapshot",
        "status": "READY",
        "trade_date": trade_date,
        "row_count": 267,
        "ticker_count": 267,
        "local_path": (
            "data/gold/analytics/"
            "fii_daily_snapshot/"
            "year=2026/month=08/day=28/"
            "fii_daily_snapshot.parquet"
        ),
        "s3_key": (
            "gold/analytics/"
            "fii_daily_snapshot/"
            "year=2026/month=08/day=28/"
            "fii_daily_snapshot.parquet"
        ),
        "generated_at": generated_at,
    }


def test_content_sha_ignores_generated_at() -> None:
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


def test_content_sha_changes_when_trade_date_changes() -> None:
    first = build_manifest(
        "2026-10-05T10:00:00+00:00",
        trade_date="2026-08-28",
    )

    second = build_manifest(
        "2026-10-05T11:00:00+00:00",
        trade_date="2026-08-29",
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


def test_publish_manifest_uses_serving_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = build_manifest(
        "2026-10-05T10:00:00+00:00"
    )

    local_path = (
        tmp_path
        / "latest_snapshot.json"
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
        "serving/daily/latest_snapshot.json"
    )

    assert captured["force"] is False

    assert result == (
        f"s3://{pipeline.BUCKET_NAME}/"
        "serving/daily/latest_snapshot.json"
    )