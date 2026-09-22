from __future__ import annotations

import io
import json

import pytest
from botocore.exceptions import ClientError

from src.orchestration import (
    gold_execution_state,
)


BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)

RUN_DATE = "2026-09-22"

STATE_KEY = (
    "control/gold-execution/"
    "run_date=2026-09-22/"
    "state.json"
)


def test_build_state_key() -> None:
    result = (
        gold_execution_state
        .build_state_key(
            run_date=RUN_DATE,
        )
    )

    assert result == STATE_KEY


def test_build_state_key_requires_run_date() -> None:
    with pytest.raises(
        ValueError,
        match="run_date is required",
    ):
        (
            gold_execution_state
            .build_state_key(
                run_date="   ",
            )
        )


def test_read_execution_state_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeS3:
        def get_object(
            self,
            **kwargs,
        ):
            raise ClientError(
                {
                    "Error": {
                        "Code": (
                            "NoSuchKey"
                        )
                    }
                },
                "GetObject",
            )

    monkeypatch.setattr(
        gold_execution_state.boto3,
        "client",
        lambda service: FakeS3(),
    )

    result = (
        gold_execution_state
        .read_execution_state(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )
    )

    assert result is None


def test_read_execution_state_returns_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "run_date": RUN_DATE,
        "status": "SUCCEEDED",
    }

    class FakeS3:
        def get_object(
            self,
            **kwargs,
        ):
            return {
                "Body": io.BytesIO(
                    json.dumps(
                        payload
                    ).encode(
                        "utf-8"
                    )
                )
            }

    monkeypatch.setattr(
        gold_execution_state.boto3,
        "client",
        lambda service: FakeS3(),
    )

    result = (
        gold_execution_state
        .read_execution_state(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )
    )

    assert result == payload


def test_write_execution_state_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    puts = []

    monkeypatch.setattr(
        gold_execution_state,
        "read_execution_state",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        gold_execution_state,
        "utc_now_iso",
        lambda: (
            "2026-09-22T10:00:00+00:00"
        ),
    )

    class FakeS3:
        def put_object(
            self,
            **kwargs,
        ):
            puts.append(
                kwargs
            )

    monkeypatch.setattr(
        gold_execution_state.boto3,
        "client",
        lambda service: FakeS3(),
    )

    result = (
        gold_execution_state
        .write_execution_state(
            bucket=BUCKET,
            run_date=RUN_DATE,
            status="STARTED",
            trigger="normal",
        )
    )

    payload = result[
        "payload"
    ]

    assert payload[
        "status"
    ] == "STARTED"

    assert payload[
        "trigger"
    ] == "NORMAL"

    assert payload[
        "started_at"
    ] == (
        "2026-09-22T10:00:00+00:00"
    )

    assert payload[
        "completed_at"
    ] is None

    assert result[
        "state_key"
    ] == STATE_KEY

    assert len(
        puts
    ) == 1


def test_write_execution_state_succeeded_preserves_started_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_state = {
        "run_date": RUN_DATE,
        "status": "STARTED",
        "started_at": (
            "2026-09-22T10:00:00+00:00"
        ),
        "updated_at": (
            "2026-09-22T10:00:00+00:00"
        ),
    }

    monkeypatch.setattr(
        gold_execution_state,
        "read_execution_state",
        lambda **kwargs: (
            previous_state
        ),
    )

    monkeypatch.setattr(
        gold_execution_state,
        "utc_now_iso",
        lambda: (
            "2026-09-22T10:05:00+00:00"
        ),
    )

    class FakeS3:
        def put_object(
            self,
            **kwargs,
        ):
            pass

    monkeypatch.setattr(
        gold_execution_state.boto3,
        "client",
        lambda service: FakeS3(),
    )

    result = (
        gold_execution_state
        .write_execution_state(
            bucket=BUCKET,
            run_date=RUN_DATE,
            status="SUCCEEDED",
            trigger="normal",
        )
    )

    payload = result[
        "payload"
    ]

    assert payload[
        "started_at"
    ] == (
        "2026-09-22T10:00:00+00:00"
    )

    assert payload[
        "completed_at"
    ] == (
        "2026-09-22T10:05:00+00:00"
    )

    assert payload[
        "status"
    ] == "SUCCEEDED"


def test_write_execution_state_rejects_invalid_status() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Invalid Gold "
            "execution status"
        ),
    ):
        (
            gold_execution_state
            .write_execution_state(
                bucket=BUCKET,
                run_date=RUN_DATE,
                status="WHATEVER",
                trigger="normal",
            )
        )


def test_write_execution_state_requires_trigger() -> None:
    with pytest.raises(
        ValueError,
        match="trigger is required",
    ):
        (
            gold_execution_state
            .write_execution_state(
                bucket=BUCKET,
                run_date=RUN_DATE,
                status="STARTED",
                trigger="   ",
            )
        )


def test_mark_execution_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    monkeypatch.setattr(
        gold_execution_state,
        "write_execution_state",
        lambda **kwargs: (
            calls.append(
                kwargs
            )
            or {
                "payload": kwargs
            }
        ),
    )

    result = (
        gold_execution_state
        .mark_execution_started(
            bucket=BUCKET,
            run_date=RUN_DATE,
            trigger="NORMAL",
            details={
                "source": "coordinator",
            },
        )
    )

    assert calls[0][
        "status"
    ] == "STARTED"

    assert calls[0][
        "details"
    ] == {
        "source": "coordinator"
    }

    assert result[
        "payload"
    ][
        "run_date"
    ] == RUN_DATE


def test_mark_execution_succeeded_merges_gold_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    monkeypatch.setattr(
        gold_execution_state,
        "write_execution_state",
        lambda **kwargs: (
            calls.append(
                kwargs
            )
            or {
                "payload": kwargs
            }
        ),
    )

    gold_key = (
        "gold/fii-master/"
        "year=2026/"
        "month=09/"
        "day=22/"
        "fii_master.parquet"
    )

    (
        gold_execution_state
        .mark_execution_succeeded(
            bucket=BUCKET,
            run_date=RUN_DATE,
            trigger="NORMAL",
            gold_key=gold_key,
            details={
                "records": 388,
            },
        )
    )

    assert calls[0][
        "status"
    ] == "SUCCEEDED"

    assert calls[0][
        "details"
    ] == {
        "gold_key": gold_key,
        "records": 388,
    }


def test_mark_execution_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    monkeypatch.setattr(
        gold_execution_state,
        "write_execution_state",
        lambda **kwargs: (
            calls.append(
                kwargs
            )
            or {
                "payload": kwargs
            }
        ),
    )

    (
        gold_execution_state
        .mark_execution_failed(
            bucket=BUCKET,
            run_date=RUN_DATE,
            trigger="RECOVERY",
            error_type="ValueError",
            error_message="boom",
            details={
                "attempt": 2,
            },
        )
    )

    assert calls[0][
        "status"
    ] == "FAILED"

    assert calls[0][
        "details"
    ] == {
        "error_type": "ValueError",
        "error_message": "boom",
        "attempt": 2,
    }


def test_execution_succeeded_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_execution_state,
        "read_execution_state",
        lambda **kwargs: {
            "status": "SUCCEEDED"
        },
    )

    assert (
        gold_execution_state
        .execution_succeeded(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )
        is True
    )


def test_execution_succeeded_false_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_execution_state,
        "read_execution_state",
        lambda **kwargs: None,
    )

    assert (
        gold_execution_state
        .execution_succeeded(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )
        is False
    )


def test_execution_failed_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_execution_state,
        "read_execution_state",
        lambda **kwargs: {
            "status": "FAILED"
        },
    )

    assert (
        gold_execution_state
        .execution_failed(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )
        is True
    )


def test_execution_in_progress_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_execution_state,
        "read_execution_state",
        lambda **kwargs: {
            "status": "STARTED"
        },
    )

    assert (
        gold_execution_state
        .execution_in_progress(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )
        is True
    )