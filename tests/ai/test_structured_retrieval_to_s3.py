from __future__ import annotations

import json
from pathlib import Path

import src.pipelines.ai_structured_retrieval_to_s3 as pipeline


def test_jsonl_sha_is_stable(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "context.jsonl"
    )

    path.write_text(
        '{"ticker":"HGLG11"}\n'
        '{"ticker":"KNRI11"}\n',
        encoding="utf-8",
    )

    first = (
        pipeline.calculate_jsonl_content_sha256(
            path
        )
    )

    second = (
        pipeline.calculate_jsonl_content_sha256(
            path
        )
    )

    assert first == second


def test_jsonl_sha_changes_when_content_changes(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "context.jsonl"
    )

    path.write_text(
        '{"ticker":"HGLG11"}\n',
        encoding="utf-8",
    )

    first = (
        pipeline.calculate_jsonl_content_sha256(
            path
        )
    )

    path.write_text(
        '{"ticker":"KNRI11"}\n',
        encoding="utf-8",
    )

    second = (
        pipeline.calculate_jsonl_content_sha256(
            path
        )
    )

    assert first != second


def test_manifest_sha_ignores_generated_at() -> None:
    first = {
        "dataset": "fii_structured_context",
        "status": "READY",
        "trade_date": "2026-08-28",
        "generated_at": (
            "2026-10-05T10:00:00+00:00"
        ),
    }

    second = {
        "dataset": "fii_structured_context",
        "status": "READY",
        "trade_date": "2026-08-28",
        "generated_at": (
            "2026-10-05T11:00:00+00:00"
        ),
    }

    assert (
        pipeline.calculate_manifest_content_sha256(
            first
        )
        ==
        pipeline.calculate_manifest_content_sha256(
            second
        )
    )


def test_manifest_sha_changes_when_state_changes() -> None:
    first = {
        "dataset": "fii_structured_context",
        "status": "READY",
        "trade_date": "2026-08-28",
        "generated_at": (
            "2026-10-05T10:00:00+00:00"
        ),
    }

    second = {
        "dataset": "fii_structured_context",
        "status": "READY",
        "trade_date": "2026-08-29",
        "generated_at": (
            "2026-10-05T11:00:00+00:00"
        ),
    }

    assert (
        pipeline.calculate_manifest_content_sha256(
            first
        )
        !=
        pipeline.calculate_manifest_content_sha256(
            second
        )
    )


def test_publish_context_uses_expected_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = (
        tmp_path
        / "context.jsonl"
    )

    path.write_text(
        '{"ticker":"HGLG11"}\n',
        encoding="utf-8",
    )

    captured = {}

    def fake_upload_file(
        *,
        local_path,
        bucket_name,
        s3_key,
        content_sha256,
        force,
    ):
        captured["s3_key"] = s3_key
        captured["force"] = force

        return (
            f"s3://{bucket_name}/{s3_key}"
        )

    monkeypatch.setattr(
        pipeline,
        "upload_file",
        fake_upload_file,
    )

    result = pipeline.publish_context(
        local_path=path,
    )

    assert captured["s3_key"] == (
        "serving/ai/"
        "fii_structured_context.jsonl"
    )

    assert captured["force"] is False

    assert result == (
        f"s3://{pipeline.BUCKET_NAME}/"
        "serving/ai/"
        "fii_structured_context.jsonl"
    )


def test_publish_manifest_uses_expected_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = (
        tmp_path
        / "manifest.json"
    )

    path.write_text(
        json.dumps(
            {
                "dataset": (
                    "fii_structured_context"
                )
            }
        ),
        encoding="utf-8",
    )

    manifest = {
        "dataset": (
            "fii_structured_context"
        ),
        "status": "READY",
        "trade_date": "2026-08-28",
        "generated_at": (
            "2026-10-05T10:00:00+00:00"
        ),
    }

    captured = {}

    def fake_upload_file(
        *,
        local_path,
        bucket_name,
        s3_key,
        content_sha256,
        force,
    ):
        captured["s3_key"] = s3_key
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
        local_path=path,
    )

    assert captured["s3_key"] == (
        "serving/ai/"
        "fii_structured_context.json"
    )

    assert captured["force"] is False

    assert result == (
        f"s3://{pipeline.BUCKET_NAME}/"
        "serving/ai/"
        "fii_structured_context.json"
    )