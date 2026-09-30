from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.orchestration import (
    gold_recovery_state,
)


BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)

RUN_DATE = "2026-09-22"

NOW = datetime(
    2026,
    9,
    22,
    10,
    30,
    0,
    tzinfo=timezone.utc,
)


def build_started_state(
    *,
    started_at: str = (
        "2026-09-22T10:20:00+00:00"
    ),
    updated_at: str = (
        "2026-09-22T10:20:00+00:00"
    ),
) -> dict:
    return {
        "run_date": RUN_DATE,
        "status": "STARTED",
        "started_at": started_at,
        "updated_at": updated_at,
    }


def test_parse_iso_datetime() -> None:
    result = (
        gold_recovery_state
        .parse_iso_datetime(
            "2026-09-22T10:00:00+00:00"
        )
    )

    assert result == datetime(
        2026,
        9,
        22,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )


def test_parse_iso_datetime_requires_value() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "datetime value is required"
        ),
    ):
        (
            gold_recovery_state
            .parse_iso_datetime(
                ""
            )
        )


def test_parse_iso_datetime_rejects_invalid_value() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Invalid ISO datetime"
        ),
    ):
        (
            gold_recovery_state
            .parse_iso_datetime(
                "22/09/2026 10:00"
            )
        )


def test_parse_iso_datetime_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Datetime must include timezone"
        ),
    ):
        (
            gold_recovery_state
            .parse_iso_datetime(
                "2026-09-22T10:00:00"
            )
        )


def test_execution_started_at() -> None:
    state = (
        build_started_state()
    )

    result = (
        gold_recovery_state
        .execution_started_at(
            state=state
        )
    )

    assert result == datetime(
        2026,
        9,
        22,
        10,
        20,
        0,
        tzinfo=timezone.utc,
    )


def test_execution_started_at_returns_none() -> None:
    result = (
        gold_recovery_state
        .execution_started_at(
            state={}
        )
    )

    assert result is None


def test_execution_updated_at() -> None:
    state = {
        "updated_at": (
            "2026-09-22T10:25:00+00:00"
        )
    }

    result = (
        gold_recovery_state
        .execution_updated_at(
            state=state
        )
    )

    assert result == datetime(
        2026,
        9,
        22,
        10,
        25,
        0,
        tzinfo=timezone.utc,
    )


def test_execution_reference_time_prefers_started_at() -> None:
    state = {
        "started_at": (
            "2026-09-22T10:10:00+00:00"
        ),
        "updated_at": (
            "2026-09-22T10:20:00+00:00"
        ),
    }

    result = (
        gold_recovery_state
        .execution_reference_time(
            state=state
        )
    )

    assert result == datetime(
        2026,
        9,
        22,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    )


def test_execution_reference_time_uses_updated_at_fallback() -> None:
    state = {
        "updated_at": (
            "2026-09-22T10:20:00+00:00"
        )
    }

    result = (
        gold_recovery_state
        .execution_reference_time(
            state=state
        )
    )

    assert result == datetime(
        2026,
        9,
        22,
        10,
        20,
        0,
        tzinfo=timezone.utc,
    )


def test_is_execution_stale_false_when_active() -> None:
    state = (
        build_started_state(
            started_at=(
                "2026-09-22T10:20:00+00:00"
            )
        )
    )

    result = (
        gold_recovery_state
        .is_execution_stale(
            state=state,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result is False


def test_is_execution_stale_true_when_threshold_reached() -> None:
    state = (
        build_started_state(
            started_at=(
                "2026-09-22T10:15:00+00:00"
            )
        )
    )

    result = (
        gold_recovery_state
        .is_execution_stale(
            state=state,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result is True


def test_is_execution_stale_true_without_reference_time() -> None:
    state = {
        "status": "STARTED",
    }

    result = (
        gold_recovery_state
        .is_execution_stale(
            state=state,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result is True


def test_is_execution_stale_false_for_non_started_status() -> None:
    state = {
        "status": "FAILED",
        "started_at": (
            "2026-09-22T09:00:00+00:00"
        ),
    }

    result = (
        gold_recovery_state
        .is_execution_stale(
            state=state,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result is False


def test_is_execution_stale_validates_minutes() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "stale_after_minutes "
            "must be >= 1"
        ),
    ):
        (
            gold_recovery_state
            .is_execution_stale(
                state={
                    "status": "STARTED",
                },
                now=NOW,
                stale_after_minutes=0,
            )
        )


def test_is_execution_stale_requires_timezone_in_now() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "now must include timezone"
        ),
    ):
        (
            gold_recovery_state
            .is_execution_stale(
                state={
                    "status": "STARTED",
                },
                now=datetime(
                    2026,
                    9,
                    22,
                    10,
                    30,
                    0,
                ),
                stale_after_minutes=15,
            )
        )


def test_classify_complete_when_gold_exists() -> None:
    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=True,
            state={
                "status": "FAILED",
            },
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": "COMPLETE",
        "reason": (
            "GOLD_OBJECT_EXISTS"
        ),
        "retry_allowed": False,
    }


def test_classify_no_state() -> None:
    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=False,
            state=None,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": "NO_STATE",
        "reason": (
            "GOLD_OBJECT_MISSING_"
            "AND_NO_EXECUTION_STATE"
        ),
        "retry_allowed": False,
    }


def test_classify_failed_allows_retry() -> None:
    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=False,
            state={
                "status": "FAILED",
            },
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": "RETRY_ALLOWED",
        "reason": (
            "PREVIOUS_EXECUTION_FAILED"
        ),
        "execution_status": "FAILED",
        "retry_allowed": True,
    }


def test_classify_succeeded_without_gold_is_inconsistent() -> None:
    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=False,
            state={
                "status": "SUCCEEDED",
            },
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": (
            "INCONSISTENT_STATE"
        ),
        "reason": (
            "EXECUTION_SUCCEEDED_"
            "BUT_GOLD_OBJECT_MISSING"
        ),
        "execution_status": (
            "SUCCEEDED"
        ),
        "retry_allowed": False,
    }


def test_classify_started_active_is_in_progress() -> None:
    state = (
        build_started_state(
            started_at=(
                "2026-09-22T10:20:00+00:00"
            )
        )
    )

    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=False,
            state=state,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": "IN_PROGRESS",
        "reason": (
            "STARTED_EXECUTION_ACTIVE"
        ),
        "execution_status": (
            "STARTED"
        ),
        "retry_allowed": False,
    }


def test_classify_started_stale_allows_retry() -> None:
    state = (
        build_started_state(
            started_at=(
                "2026-09-22T10:00:00+00:00"
            )
        )
    )

    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=False,
            state=state,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": "RETRY_ALLOWED",
        "reason": (
            "STARTED_EXECUTION_STALE"
        ),
        "execution_status": (
            "STARTED"
        ),
        "retry_allowed": True,
    }


def test_classify_unknown_state() -> None:
    result = (
        gold_recovery_state
        .classify_gold_execution_state(
            gold_exists=False,
            state={
                "status": "ALIEN",
            },
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result == {
        "status": "UNKNOWN_STATE",
        "reason": (
            "UNSUPPORTED_EXECUTION_STATUS"
        ),
        "execution_status": "ALIEN",
        "retry_allowed": False,
    }


def test_classify_validates_stale_minutes() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "stale_after_minutes "
            "must be >= 1"
        ),
    ):
        (
            gold_recovery_state
            .classify_gold_execution_state(
                gold_exists=False,
                state=None,
                now=NOW,
                stale_after_minutes=0,
            )
        )


def test_classify_requires_timezone_in_now() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "now must include timezone"
        ),
    ):
        (
            gold_recovery_state
            .classify_gold_execution_state(
                gold_exists=False,
                state=None,
                now=datetime(
                    2026,
                    9,
                    22,
                    10,
                    30,
                    0,
                ),
                stale_after_minutes=15,
            )
        )


def test_assess_gold_recovery_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        "run_date": RUN_DATE,
        "status": "FAILED",
        "updated_at": (
            "2026-09-22T10:10:00+00:00"
        ),
    }

    monkeypatch.setattr(
        gold_recovery_state,
        "read_execution_state",
        lambda **kwargs: state,
    )

    result = (
        gold_recovery_state
        .assess_gold_recovery_state(
            bucket=BUCKET,
            run_date=RUN_DATE,
            gold_exists=False,
            now=NOW,
            stale_after_minutes=15,
        )
    )

    assert result[
        "run_date"
    ] == RUN_DATE

    assert result[
        "gold_exists"
    ] is False

    assert result[
        "execution_state"
    ] == state

    assert result[
        "classification"
    ] == {
        "status": "RETRY_ALLOWED",
        "reason": (
            "PREVIOUS_EXECUTION_FAILED"
        ),
        "execution_status": "FAILED",
        "retry_allowed": True,
    }