from __future__ import annotations

import json

import pytest

from src.observability import (
    gold_recovery_observability,
)


def test_build_assessment_event_for_complete() -> None:
    result = (
        gold_recovery_observability
        .build_assessment_event(
            {
                "run_date": "2026-09-24",
                "status": "COMPLETE",
                "action": "NO_ACTION",
                "reason": "GOLD_OBJECT_EXISTS",
                "gold_exists": True,
            }
        )
    )

    assert result == {
        "event": "GOLD_RECOVERY_COMPLETE",
        "status": "INFO",
        "run_date": "2026-09-24",
        "assessment_status": "COMPLETE",
        "action": "NO_ACTION",
        "reason": "GOLD_OBJECT_EXISTS",
        "gold_exists": True,
    }


def test_build_assessment_event_for_waiting() -> None:
    result = (
        gold_recovery_observability
        .build_assessment_event(
            {
                "run_date": "2026-09-24",
                "status": "IN_PROGRESS",
                "action": "WAIT_FOR_COMPLETION",
                "reason": "STARTED_EXECUTION_ACTIVE",
            }
        )
    )

    assert result["event"] == (
        "GOLD_RECOVERY_WAITING"
    )

    assert result["status"] == "INFO"

    assert result[
        "assessment_status"
    ] == "IN_PROGRESS"


def test_build_assessment_event_for_stale_execution() -> None:
    result = (
        gold_recovery_observability
        .build_assessment_event(
            {
                "run_date": "2026-09-24",
                "status": (
                    "GOLD_RETRY_REQUIRED"
                ),
                "action": "RETRY_GOLD",
                "reason": (
                    "STARTED_EXECUTION_STALE"
                ),
            }
        )
    )

    assert result["event"] == (
        "GOLD_EXECUTION_STALE"
    )

    assert result["status"] == "WARN"


def test_build_assessment_event_for_inconsistent_state() -> None:
    result = (
        gold_recovery_observability
        .build_assessment_event(
            {
                "run_date": "2026-09-24",
                "status": "RECOVERY_BLOCKED",
                "action": "BLOCK",
                "reason": (
                    "EXECUTION_SUCCEEDED_"
                    "BUT_GOLD_OBJECT_MISSING"
                ),
            }
        )
    )

    assert result["event"] == (
        "GOLD_INCONSISTENT_STATE"
    )

    assert result["status"] == "ERROR"


def test_build_assessment_event_for_previous_failure() -> None:
    result = (
        gold_recovery_observability
        .build_assessment_event(
            {
                "run_date": "2026-09-24",
                "status": (
                    "GOLD_RETRY_REQUIRED"
                ),
                "action": "RETRY_GOLD",
                "reason": (
                    "PREVIOUS_EXECUTION_FAILED"
                ),
            }
        )
    )

    assert result["event"] == (
        "GOLD_PREVIOUS_EXECUTION_FAILED"
    )

    assert result["status"] == "ERROR"


@pytest.mark.parametrize(
    (
        "execution_status",
        "expected_event",
        "expected_severity",
    ),
    [
        (
            "DISPATCHED",
            "GOLD_RECOVERY_DISPATCHED",
            "WARN",
        ),
        (
            "WAITING",
            "GOLD_RECOVERY_WAITING",
            "INFO",
        ),
        (
            "BLOCKED",
            "GOLD_RECOVERY_BLOCKED",
            "ERROR",
        ),
        (
            "SKIPPED",
            "GOLD_RECOVERY_SKIPPED",
            "INFO",
        ),
    ],
)
def test_build_execution_result_event(
    execution_status: str,
    expected_event: str,
    expected_severity: str,
) -> None:
    result = (
        gold_recovery_observability
        .build_execution_result_event(
            {
                "status": execution_status,
                "run_date": "2026-09-24",
                "action": "TEST_ACTION",
            }
        )
    )

    assert result[
        "event"
    ] == expected_event

    assert result[
        "status"
    ] == expected_severity

    assert result[
        "execution_status"
    ] == execution_status


@pytest.mark.parametrize(
    (
        "execution_status",
        "expected_event",
        "expected_severity",
    ),
    [
        (
            "STARTED",
            "GOLD_EXECUTION_STARTED",
            "INFO",
        ),
        (
            "SUCCEEDED",
            "GOLD_EXECUTION_SUCCEEDED",
            "INFO",
        ),
        (
            "FAILED",
            "GOLD_EXECUTION_FAILED",
            "ERROR",
        ),
    ],
)
def test_build_gold_execution_state_event(
    execution_status: str,
    expected_event: str,
    expected_severity: str,
) -> None:
    result = (
        gold_recovery_observability
        .build_gold_execution_state_event(
            {
                "status": execution_status,
                "run_date": "2026-09-24",
                "trigger": "RECOVERY",
                "request_id": "request-123",
            }
        )
    )

    assert result[
        "event"
    ] == expected_event

    assert result[
        "status"
    ] == expected_severity

    assert result[
        "execution_status"
    ] == execution_status


def test_build_missing_cycle_event() -> None:
    result = (
        gold_recovery_observability
        .build_missing_cycle_event(
            run_date="2026-09-24"
        )
    )

    assert result == {
        "event": "GOLD_MISSING_CYCLE",
        "status": "ERROR",
        "run_date": "2026-09-24",
        "reason": (
            "EXPECTED_CYCLE_NOT_OBSERVED"
        ),
    }


def test_build_recovery_summary_event_with_blocks() -> None:
    result = (
        gold_recovery_observability
        .build_recovery_summary_event(
            {
                "status": (
                    "EXECUTED_WITH_BLOCKS"
                ),
                "total_results": 3,
                "dispatched": 1,
                "waiting": 0,
                "blocked": 1,
                "skipped": 1,
            }
        )
    )

    assert result["status"] == "ERROR"

    assert result["event"] == (
        "GOLD_RECOVERY_EXECUTION_SUMMARY"
    )

    assert result["blocked"] == 1


def test_build_recovery_summary_event_with_waiting() -> None:
    result = (
        gold_recovery_observability
        .build_recovery_summary_event(
            {
                "status": (
                    "EXECUTED_WITH_WAITING"
                ),
                "total_results": 2,
                "dispatched": 0,
                "waiting": 1,
                "blocked": 0,
                "skipped": 1,
            }
        )
    )

    assert result["status"] == "WARN"

    assert result["waiting"] == 1


def test_build_recovery_summary_event_success() -> None:
    result = (
        gold_recovery_observability
        .build_recovery_summary_event(
            {
                "status": "EXECUTED",
                "total_results": 1,
                "dispatched": 1,
                "waiting": 0,
                "blocked": 0,
                "skipped": 0,
            }
        )
    )

    assert result["status"] == "INFO"


def test_emit_assessment_event_outputs_structured_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = (
        gold_recovery_observability
        .emit_assessment_event(
            {
                "run_date": "2026-09-24",
                "status": "RECOVERY_BLOCKED",
                "action": "BLOCK",
                "reason": "RAW_MISSING",
            }
        )
    )

    captured = capsys.readouterr()

    payload = json.loads(
        captured.out.strip()
    )

    assert payload[
        "event"
    ] == "GOLD_RECOVERY_BLOCKED"

    assert payload[
        "pipeline"
    ] == "gold-recovery"

    assert payload[
        "status"
    ] == "ERROR"

    assert payload[
        "run_date"
    ] == "2026-09-24"

    assert result[
        "event"
    ] == "GOLD_RECOVERY_BLOCKED"


def test_emit_gold_execution_state_event_outputs_structured_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = (
        gold_recovery_observability
        .emit_gold_execution_state_event(
            {
                "status": "FAILED",
                "run_date": "2026-09-24",
                "trigger": "RECOVERY",
                "error_type": "RuntimeError",
                "error_message": (
                    "controlled failure"
                ),
            }
        )
    )

    captured = capsys.readouterr()

    payload = json.loads(
        captured.out.strip()
    )

    assert payload[
        "event"
    ] == "GOLD_EXECUTION_FAILED"

    assert payload[
        "status"
    ] == "ERROR"

    assert payload[
        "pipeline"
    ] == "gold-recovery"

    assert payload[
        "error_type"
    ] == "RuntimeError"

    assert result[
        "event"
    ] == "GOLD_EXECUTION_FAILED"


def test_build_gold_execution_state_event_accepts_wrapped_state(
) -> None:
    result = (
        gold_recovery_observability
        .build_gold_execution_state_event(
            {
                "state_key": (
                    "control/gold-execution/"
                    "run_date=2026-09-24/"
                    "state.json"
                ),
                "state_uri": (
                    "s3://test-bucket/"
                    "control/gold-execution/"
                    "run_date=2026-09-24/"
                    "state.json"
                ),
                "payload": {
                    "status": "SUCCEEDED",
                    "run_date": (
                        "2026-09-24"
                    ),
                    "trigger": (
                        "MANUAL_TEST"
                    ),
                    "records": 388,
                },
            }
        )
    )

    assert result[
        "event"
    ] == "GOLD_EXECUTION_SUCCEEDED"

    assert result[
        "status"
    ] == "INFO"

    assert result[
        "execution_status"
    ] == "SUCCEEDED"

    assert result[
        "run_date"
    ] == "2026-09-24"

    assert result[
        "trigger"
    ] == "MANUAL_TEST"

    assert result[
        "records"
    ] == 388