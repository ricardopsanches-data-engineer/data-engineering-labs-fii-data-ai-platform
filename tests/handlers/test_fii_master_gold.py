from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.handlers import fii_master_gold


BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)

RUN_DATE = "2026-09-22"

GOLD_KEY = (
    "gold/fii-master/"
    "year=2026/"
    "month=09/"
    "day=22/"
    "fii_master.parquet"
)


def test_resolve_execution_run_date_explicit() -> None:
    result = (
        fii_master_gold
        .resolve_execution_run_date(
            {
                "run_date": (
                    "2026-09-22"
                )
            }
        )
    )

    assert result == (
        "2026-09-22"
    )


def test_resolve_execution_run_date_rejects_invalid() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Invalid Gold run_date"
        ),
    ):
        (
            fii_master_gold
            .resolve_execution_run_date(
                {
                    "run_date": (
                        "22/09/2026"
                    )
                }
            )
        )


def test_resolve_execution_trigger_defaults_to_normal() -> None:
    result = (
        fii_master_gold
        .resolve_execution_trigger(
            {}
        )
    )

    assert result == "NORMAL"


def test_resolve_execution_trigger_normalizes_value() -> None:
    result = (
        fii_master_gold
        .resolve_execution_trigger(
            {
                "trigger": (
                    " recovery "
                )
            }
        )
    )

    assert result == "RECOVERY"


def test_get_request_id() -> None:
    context = SimpleNamespace(
        aws_request_id=(
            "request-123"
        )
    )

    assert (
        fii_master_gold
        .get_request_id(
            context
        )
        == "request-123"
    )

    assert (
        fii_master_gold
        .get_request_id(
            None
        )
        is None
    )


def test_lambda_handler_marks_started_and_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        BUCKET,
    )

    calls = []

    explicit_inputs = {
        "b3_trades": {
            "reference_date": (
                "2026-09-21"
            ),
            "key": (
                "silver/b3/"
                "year=2026/"
                "month=09/"
                "day=21/"
                "b3_trades.parquet"
            ),
        }
    }

    monkeypatch.setattr(
        fii_master_gold,
        "resolve_explicit_inputs",
        lambda *, bucket, event: (
            explicit_inputs
        ),
    )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_started",
        lambda **kwargs: (
            calls.append(
                (
                    "STARTED",
                    kwargs,
                )
            )
        ),
    )

    monkeypatch.setattr(
        fii_master_gold,
        "run_fii_master_gold",
        lambda *,
        bucket,
        explicit_inputs,
        run_date: {
            "status": "success",
            "run_date": run_date,
            "reference_date": (
                "2026-09-22"
            ),
            "records": 388,
            "gold_key": GOLD_KEY,
            "gold_uri": (
                f"s3://{BUCKET}/"
                f"{GOLD_KEY}"
            ),
            "inputs": {},
        },
    )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_succeeded",
        lambda **kwargs: (
            calls.append(
                (
                    "SUCCEEDED",
                    kwargs,
                )
            )
        ),
    )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_failed",
        lambda **kwargs: (
            calls.append(
                (
                    "FAILED",
                    kwargs,
                )
            )
        ),
    )

    event = {
        "run_date": RUN_DATE,
        "trigger": "RECOVERY",
        "inputs": {
            "dummy": "value",
        },
    }

    context = SimpleNamespace(
        aws_request_id=(
            "request-success"
        )
    )

    result = (
        fii_master_gold
        .lambda_handler(
            event,
            context,
        )
    )

    assert result[
        "status"
    ] == "success"

    assert result[
        "run_date"
    ] == RUN_DATE

    assert [
        item[0]
        for item in calls
    ] == [
        "STARTED",
        "SUCCEEDED",
    ]

    started = calls[0][1]

    assert started[
        "bucket"
    ] == BUCKET

    assert started[
        "run_date"
    ] == RUN_DATE

    assert started[
        "trigger"
    ] == "RECOVERY"

    assert started[
        "details"
    ] == {
        "request_id": (
            "request-success"
        ),
        "has_explicit_inputs": True,
    }

    succeeded = calls[1][1]

    assert succeeded[
        "bucket"
    ] == BUCKET

    assert succeeded[
        "run_date"
    ] == RUN_DATE

    assert succeeded[
        "trigger"
    ] == "RECOVERY"

    assert succeeded[
        "gold_key"
    ] == GOLD_KEY

    assert succeeded[
        "details"
    ] == {
        "request_id": (
            "request-success"
        ),
        "reference_date": (
            "2026-09-22"
        ),
        "records": 388,
    }


def test_lambda_handler_marks_failed_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        BUCKET,
    )

    calls = []

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_started",
        lambda **kwargs: (
            calls.append(
                (
                    "STARTED",
                    kwargs,
                )
            )
        ),
    )

    monkeypatch.setattr(
        fii_master_gold,
        "resolve_explicit_inputs",
        lambda **kwargs: (
            (_ for _ in ())
            .throw(
                ValueError(
                    "bad explicit input"
                )
            )
        ),
    )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_failed",
        lambda **kwargs: (
            calls.append(
                (
                    "FAILED",
                    kwargs,
                )
            )
        ),
    )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_succeeded",
        lambda **kwargs: (
            calls.append(
                (
                    "SUCCEEDED",
                    kwargs,
                )
            )
        ),
    )

    event = {
        "run_date": RUN_DATE,
        "trigger": "NORMAL",
        "inputs": {
            "dummy": "value",
        },
    }

    context = SimpleNamespace(
        aws_request_id=(
            "request-failed"
        )
    )

    with pytest.raises(
        ValueError,
        match="bad explicit input",
    ):
        (
            fii_master_gold
            .lambda_handler(
                event,
                context,
            )
        )

    assert [
        item[0]
        for item in calls
    ] == [
        "STARTED",
        "FAILED",
    ]

    failed = calls[1][1]

    assert failed[
        "bucket"
    ] == BUCKET

    assert failed[
        "run_date"
    ] == RUN_DATE

    assert failed[
        "trigger"
    ] == "NORMAL"

    assert failed[
        "error_type"
    ] == "ValueError"

    assert failed[
        "error_message"
    ] == "bad explicit input"

    assert failed[
        "details"
    ] == {
        "request_id": (
            "request-failed"
        )
    }


def test_lambda_handler_state_failure_does_not_mask_original_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        BUCKET,
    )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_started",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        fii_master_gold,
        "resolve_explicit_inputs",
        lambda **kwargs: (
            (_ for _ in ())
            .throw(
                ValueError(
                    "original failure"
                )
            )
        ),
    )

    def fail_to_write_state(
        **kwargs,
    ):
        raise RuntimeError(
            "state persistence failed"
        )

    monkeypatch.setattr(
        fii_master_gold,
        "mark_execution_failed",
        fail_to_write_state,
    )

    with pytest.raises(
        ValueError,
        match="original failure",
    ):
        (
            fii_master_gold
            .lambda_handler(
                {
                    "run_date": RUN_DATE,
                },
                None,
            )
        )


def test_lambda_handler_requires_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "FII_DATA_LAKE_BUCKET",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "FII_DATA_LAKE_BUCKET "
            "is required"
        ),
    ):
        (
            fii_master_gold
            .lambda_handler(
                {
                    "run_date": RUN_DATE,
                },
                None,
            )
        )