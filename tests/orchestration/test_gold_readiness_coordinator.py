from __future__ import annotations

import copy
import io
import json
from datetime import date

import pytest
from botocore.exceptions import ClientError

from src.orchestration import (
    gold_readiness_coordinator as coordinator,
)


RUN_DATE = date(
    2026,
    9,
    18,
)


def build_valid_markers() -> dict:
    return {
        "b3": {
            "status": "SUCCESS",
            "source": "b3",
            "run_date": "2026-09-18",
            "reference_date": "2026-09-17",
            "silver_key": (
                "silver/b3/"
                "year=2026/month=09/day=17/"
                "b3_trades.parquet"
            ),
            "records": 54573,
        },
        "cvm": {
            "status": "SUCCESS",
            "source": "cvm",
            "run_date": "2026-09-18",
            "reference_date": "2026-09-18",
            "silver_key": (
                "silver/cvm/"
                "year=2026/month=09/day=18/"
                "cvm_fund_classes.parquet"
            ),
            "records": 36722,
        },
        "b3_instruments": {
            "status": "SUCCESS",
            "source": "b3-instruments",
            "run_date": "2026-09-18",
            "reference_date": "2026-09-18",
            "silver_key": (
                "silver/b3-instruments/"
                "year=2026/month=09/day=18/"
                "b3_instruments.parquet"
            ),
            "records": 152724,
        },
    }


def build_s3_event(
    key: str = (
        "control/gold-readiness/"
        "run_date=2026-09-18/"
        "b3_instruments_SUCCESS.json"
    ),
) -> dict:
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "object": {
                        "key": key,
                    }
                },
            }
        ]
    }


def test_extract_run_date_from_key() -> None:
    result = (
        coordinator
        .extract_run_date_from_key(
            "control/gold-readiness/"
            "run_date=2026-09-18/"
            "b3_SUCCESS.json"
        )
    )

    assert result == RUN_DATE


def test_extract_trigger_key_decodes_url_encoding() -> None:
    event = build_s3_event(
        key=(
            "control%2Fgold-readiness%2F"
            "run_date%3D2026-09-18%2F"
            "b3_instruments_SUCCESS.json"
        )
    )

    result = coordinator.extract_trigger_key(
        event
    )

    assert result == (
        "control/gold-readiness/"
        "run_date=2026-09-18/"
        "b3_instruments_SUCCESS.json"
    )


def test_validate_marker_run_dates_passes() -> None:
    markers = build_valid_markers()

    coordinator.validate_marker_run_dates(
        run_date=RUN_DATE,
        markers=markers,
    )


def test_validate_marker_run_dates_rejects_mismatch() -> None:
    markers = build_valid_markers()

    markers[
        "cvm"
    ][
        "run_date"
    ] = "2026-09-17"

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        coordinator.validate_marker_run_dates(
            run_date=RUN_DATE,
            markers=markers,
        )


def test_validate_marker_fields_rejects_missing_field() -> None:
    markers = build_valid_markers()

    del markers[
        "b3"
    ][
        "silver_key"
    ]

    with pytest.raises(
        ValueError,
        match="missing",
    ):
        coordinator.validate_marker_fields(
            markers
        )


def test_build_gold_payload() -> None:
    markers = build_valid_markers()

    payload = coordinator.build_gold_payload(
        run_date=RUN_DATE,
        markers=markers,
    )

    assert (
        payload[
            "run_date"
        ]
        == "2026-09-18"
    )

    assert (
        payload[
            "inputs"
        ][
            "b3_trades"
        ][
            "reference_date"
        ]
        == "2026-09-17"
    )

    assert (
        payload[
            "inputs"
        ][
            "cvm"
        ][
            "reference_date"
        ]
        == "2026-09-18"
    )

    assert (
        payload[
            "inputs"
        ][
            "b3_instruments"
        ][
            "key"
        ]
        == (
            "silver/b3-instruments/"
            "year=2026/month=09/day=18/"
            "b3_instruments.parquet"
        )
    )


def test_fingerprint_is_deterministic() -> None:
    markers = build_valid_markers()

    first = (
        coordinator
        .build_readiness_fingerprint(
            run_date=RUN_DATE,
            markers=markers,
        )
    )

    second = (
        coordinator
        .build_readiness_fingerprint(
            run_date=RUN_DATE,
            markers=markers,
        )
    )

    assert first == second
    assert len(first) == 64


def test_fingerprint_changes_when_input_changes() -> None:
    original = build_valid_markers()

    changed = copy.deepcopy(
        original
    )

    changed[
        "b3"
    ][
        "records"
    ] += 1

    original_fingerprint = (
        coordinator
        .build_readiness_fingerprint(
            run_date=RUN_DATE,
            markers=original,
        )
    )

    changed_fingerprint = (
        coordinator
        .build_readiness_fingerprint(
            run_date=RUN_DATE,
            markers=changed,
        )
    )

    assert (
        original_fingerprint
        != changed_fingerprint
    )


def test_load_required_markers_reads_all_success_markers(
    monkeypatch,
) -> None:
    markers = build_valid_markers()

    marker_documents = {
        coordinator.build_marker_key(
            run_date=RUN_DATE,
            marker_filename=(
                "b3_SUCCESS.json"
            ),
        ): markers["b3"],
        coordinator.build_marker_key(
            run_date=RUN_DATE,
            marker_filename=(
                "cvm_SUCCESS.json"
            ),
        ): markers["cvm"],
        coordinator.build_marker_key(
            run_date=RUN_DATE,
            marker_filename=(
                "b3_instruments_SUCCESS.json"
            ),
        ): markers[
            "b3_instruments"
        ],
    }

    class FakeS3Client:
        def head_object(
            self,
            *,
            Bucket,
            Key,
        ):
            assert Bucket == "test-bucket"

            if Key not in marker_documents:
                raise AssertionError(
                    f"Unexpected key: {Key}"
                )

            return {}

        def get_object(
            self,
            *,
            Bucket,
            Key,
        ):
            assert Bucket == "test-bucket"

            document = marker_documents[
                Key
            ]

            return {
                "Body": io.BytesIO(
                    json.dumps(
                        document
                    ).encode(
                        "utf-8"
                    )
                )
            }

    fake_s3 = FakeS3Client()

    monkeypatch.setattr(
        coordinator.boto3,
        "client",
        lambda service_name: fake_s3,
    )

    result = (
        coordinator
        .load_required_markers(
            bucket="test-bucket",
            run_date=RUN_DATE,
        )
    )

    assert result is not None

    assert set(
        result.keys()
    ) == {
        "b3",
        "cvm",
        "b3_instruments",
    }

    assert (
        result[
            "b3"
        ][
            "status"
        ]
        == "SUCCESS"
    )


def test_acquire_dispatch_lock_succeeds(
    monkeypatch,
) -> None:
    captured = {}

    class FakeS3Client:
        def put_object(
            self,
            **kwargs,
        ):
            captured.update(
                kwargs
            )

            return {}

    fake_s3 = FakeS3Client()

    monkeypatch.setattr(
        coordinator.boto3,
        "client",
        lambda service_name: fake_s3,
    )

    acquired, key = (
        coordinator
        .acquire_dispatch_lock(
            bucket="test-bucket",
            run_date=RUN_DATE,
            fingerprint="abc123",
            payload={
                "run_date": "2026-09-18"
            },
        )
    )

    assert acquired is True

    assert key == (
        "control/gold-readiness/"
        "run_date=2026-09-18/"
        "dispatches/abc123.json"
    )

    assert (
        captured[
            "IfNoneMatch"
        ]
        == "*"
    )


def test_acquire_dispatch_lock_detects_duplicate(
    monkeypatch,
) -> None:
    class FakeS3Client:
        def put_object(
            self,
            **kwargs,
        ):
            raise ClientError(
                {
                    "Error": {
                        "Code": (
                            "PreconditionFailed"
                        ),
                        "Message": (
                            "Object already exists"
                        ),
                    },
                    "ResponseMetadata": {
                        "HTTPStatusCode": 412,
                    },
                },
                "PutObject",
            )

    fake_s3 = FakeS3Client()

    monkeypatch.setattr(
        coordinator.boto3,
        "client",
        lambda service_name: fake_s3,
    )

    acquired, key = (
        coordinator
        .acquire_dispatch_lock(
            bucket="test-bucket",
            run_date=RUN_DATE,
            fingerprint="abc123",
            payload={
                "run_date": "2026-09-18"
            },
        )
    )

    assert acquired is False

    assert key.endswith(
        "dispatches/abc123.json"
    )


def test_lambda_handler_waits_when_markers_are_missing(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        "test-bucket",
    )

    monkeypatch.setenv(
        "FII_MASTER_GOLD_FUNCTION_NAME",
        "gold-function",
    )

    monkeypatch.setattr(
        coordinator,
        "load_required_markers",
        lambda **kwargs: None,
    )

    result = coordinator.lambda_handler(
        build_s3_event(),
        None,
    )

    assert result == {
        "status": "waiting",
        "run_date": "2026-09-18",
    }


def test_lambda_handler_ignores_duplicate_dispatch(
    monkeypatch,
) -> None:
    markers = build_valid_markers()

    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        "test-bucket",
    )

    monkeypatch.setenv(
        "FII_MASTER_GOLD_FUNCTION_NAME",
        "gold-function",
    )

    monkeypatch.setattr(
        coordinator,
        "load_required_markers",
        lambda **kwargs: markers,
    )

    monkeypatch.setattr(
        coordinator,
        "acquire_dispatch_lock",
        lambda **kwargs: (
            False,
            "control/duplicate.json",
        ),
    )

    def fail_if_invoked(
        **kwargs,
    ):
        raise AssertionError(
            "Gold should not be invoked "
            "for duplicate dispatch."
        )

    monkeypatch.setattr(
        coordinator,
        "invoke_gold",
        fail_if_invoked,
    )

    result = coordinator.lambda_handler(
        build_s3_event(),
        None,
    )

    assert (
        result[
            "status"
        ]
        == "duplicate_ignored"
    )


def test_lambda_handler_invokes_gold_when_ready(
    monkeypatch,
) -> None:
    markers = build_valid_markers()

    captured_payload = {}

    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        "test-bucket",
    )

    monkeypatch.setenv(
        "FII_MASTER_GOLD_FUNCTION_NAME",
        "gold-function",
    )

    monkeypatch.setattr(
        coordinator,
        "load_required_markers",
        lambda **kwargs: markers,
    )

    monkeypatch.setattr(
        coordinator,
        "acquire_dispatch_lock",
        lambda **kwargs: (
            True,
            "control/dispatch.json",
        ),
    )

    def fake_invoke_gold(
        *,
        function_name,
        payload,
    ):
        assert (
            function_name
            == "gold-function"
        )

        captured_payload.update(
            payload
        )

        return {
            "status_code": 202,
        }

    monkeypatch.setattr(
        coordinator,
        "invoke_gold",
        fake_invoke_gold,
    )

    result = coordinator.lambda_handler(
        build_s3_event(),
        None,
    )

    assert (
        result[
            "status"
        ]
        == "gold_invoked"
    )

    assert (
        result[
            "invoke_status_code"
        ]
        == 202
    )

    assert (
        captured_payload[
            "inputs"
        ][
            "b3_trades"
        ][
            "reference_date"
        ]
        == "2026-09-17"
    )


def test_lambda_handler_releases_lock_when_invoke_fails(
    monkeypatch,
) -> None:
    markers = build_valid_markers()

    released = []

    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        "test-bucket",
    )

    monkeypatch.setenv(
        "FII_MASTER_GOLD_FUNCTION_NAME",
        "gold-function",
    )

    monkeypatch.setattr(
        coordinator,
        "load_required_markers",
        lambda **kwargs: markers,
    )

    monkeypatch.setattr(
        coordinator,
        "acquire_dispatch_lock",
        lambda **kwargs: (
            True,
            "control/dispatch.json",
        ),
    )

    def fail_invoke_gold(
        **kwargs,
    ):
        raise RuntimeError(
            "Lambda invoke failed"
        )

    def fake_release_dispatch_lock(
        *,
        bucket,
        key,
    ):
        released.append(
            (
                bucket,
                key,
            )
        )

    monkeypatch.setattr(
        coordinator,
        "invoke_gold",
        fail_invoke_gold,
    )

    monkeypatch.setattr(
        coordinator,
        "release_dispatch_lock",
        fake_release_dispatch_lock,
    )

    with pytest.raises(
        RuntimeError,
        match="Lambda invoke failed",
    ):
        coordinator.lambda_handler(
            build_s3_event(),
            None,
        )

    assert released == [
        (
            "test-bucket",
            "control/dispatch.json",
        )
    ]