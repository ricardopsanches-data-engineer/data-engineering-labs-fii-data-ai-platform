from __future__ import annotations

from datetime import date

import pytest

from src.orchestration import gold_recovery


BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)

END_DATE = date(
    2026,
    9,
    25,
)


def test_build_window_start_date() -> None:
    result = (
        gold_recovery
        .build_window_start_date(
            end_date=END_DATE,
            lookback_days=5,
        )
    )

    assert result == date(
        2026,
        9,
        21,
    )


def test_build_window_start_date_single_day() -> None:
    result = (
        gold_recovery
        .build_window_start_date(
            end_date=END_DATE,
            lookback_days=1,
        )
    )

    assert result == END_DATE


def test_build_window_start_date_validates_lookback() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "lookback_days "
            "must be >= 1"
        ),
    ):
        (
            gold_recovery
            .build_window_start_date(
                end_date=END_DATE,
                lookback_days=0,
            )
        )


def test_build_missing_cycle_assessment() -> None:
    result = (
        gold_recovery
        .build_missing_cycle_assessment(
            run_date=date(
                2026,
                9,
                24,
            )
        )
    )

    assert result == {
        "status": "MISSING_CYCLE",
        "run_date": "2026-09-24",
        "action": (
            "INVESTIGATE_MISSING_CYCLE"
        ),
        "reason": (
            "NO_OBSERVED_RAW_EVIDENCE"
        ),
    }


def test_normalize_recovery_assessment() -> None:
    assessment = {
        "status": (
            "GOLD_RETRY_REQUIRED"
        ),
        "run_date": "2026-09-22",
    }

    result = (
        gold_recovery
        .normalize_recovery_assessment(
            assessment
        )
    )

    assert result == {
        "status": (
            "GOLD_RETRY_REQUIRED"
        ),
        "run_date": "2026-09-22",
        "action": "RETRY_GOLD",
    }


def test_normalize_recovery_assessment_rejects_unknown_status() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Unsupported "
            "recovery status"
        ),
    ):
        (
            gold_recovery
            .normalize_recovery_assessment(
                {
                    "status": (
                        "ALIEN_STATUS"
                    )
                }
            )
        )


def test_build_status_counts() -> None:
    assessments = [
        {
            "status": "COMPLETE",
            "action": "NO_ACTION",
        },
        {
            "status": "COMPLETE",
            "action": "NO_ACTION",
        },
        {
            "status": (
                "GOLD_RETRY_REQUIRED"
            ),
            "action": "RETRY_GOLD",
        },
    ]

    result = (
        gold_recovery
        .build_status_counts(
            assessments=assessments
        )
    )

    assert result == {
        "COMPLETE": 2,
        "GOLD_RETRY_REQUIRED": 1,
    }


def test_build_action_counts() -> None:
    assessments = [
        {
            "status": "COMPLETE",
            "action": "NO_ACTION",
        },
        {
            "status": (
                "RAW_REBUILD_REQUIRED"
            ),
            "action": (
                "REBUILD_SILVER_FROM_RAW"
            ),
        },
        {
            "status": (
                "MISSING_CYCLE"
            ),
            "action": (
                "INVESTIGATE_MISSING_CYCLE"
            ),
        },
    ]

    result = (
        gold_recovery
        .build_action_counts(
            assessments=assessments
        )
    )

    assert result == {
        "NO_ACTION": 1,
        "REBUILD_SILVER_FROM_RAW": 1,
        "INVESTIGATE_MISSING_CYCLE": 1,
    }


def test_build_recovery_plan_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    ]

    monkeypatch.setattr(
        gold_recovery,
        "generate_expected_run_dates",
        lambda **kwargs: expected_dates,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_observed_run_dates",
        lambda **kwargs: expected_dates,
    )

    monkeypatch.setattr(
        gold_recovery,
        "assess_run_date",
        lambda *, bucket, run_date: {
            "status": "COMPLETE",
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": (
                "gold/fii-master/"
                f"day={run_date.day:02d}/"
                "fii_master.parquet"
            ),
        },
    )

    result = (
        gold_recovery
        .build_recovery_plan(
            bucket=BUCKET,
            end_date=date(
                2026,
                9,
                22,
            ),
            lookback_days=2,
        )
    )

    assert result[
        "status"
    ] == "COMPLETE"

    assert result[
        "missing_run_dates"
    ] == []

    assert result[
        "unexpected_observed_run_dates"
    ] == []

    assert result[
        "actionable_cycles"
    ] == 0

    assert result[
        "blocked_cycles"
    ] == 0

    assert result[
        "status_counts"
    ] == {
        "COMPLETE": 2,
    }

    assert result[
        "action_counts"
    ] == {
        "NO_ACTION": 2,
    }


def test_build_recovery_plan_mixed_scenarios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
        date(
            2026,
            9,
            23,
        ),
        date(
            2026,
            9,
            24,
        ),
        date(
            2026,
            9,
            25,
        ),
    ]

    observed_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
        date(
            2026,
            9,
            23,
        ),
        date(
            2026,
            9,
            24,
        ),
        date(
            2026,
            9,
            26,
        ),
    ]

    monkeypatch.setattr(
        gold_recovery,
        "generate_expected_run_dates",
        lambda **kwargs: expected_dates,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_observed_run_dates",
        lambda **kwargs: observed_dates,
    )

    statuses = {
        "2026-09-21": "COMPLETE",
        "2026-09-22": (
            "GOLD_RETRY_REQUIRED"
        ),
        "2026-09-23": (
            "RAW_REBUILD_REQUIRED"
        ),
        "2026-09-24": (
            "RECOVERY_BLOCKED"
        ),
        "2026-09-26": "COMPLETE",
    }

    def fake_assess_run_date(
        *,
        bucket: str,
        run_date: date,
    ) -> dict:
        return {
            "status": statuses[
                run_date.isoformat()
            ],
            "run_date": (
                run_date.isoformat()
            ),
        }

    monkeypatch.setattr(
        gold_recovery,
        "assess_run_date",
        fake_assess_run_date,
    )

    result = (
        gold_recovery
        .build_recovery_plan(
            bucket=BUCKET,
            end_date=END_DATE,
            lookback_days=5,
        )
    )

    assert result[
        "status"
    ] == "RECOVERY_REQUIRED"

    assert result[
        "missing_run_dates"
    ] == [
        "2026-09-25"
    ]

    assert result[
        "unexpected_observed_run_dates"
    ] == [
        "2026-09-26"
    ]

    assert result[
        "status_counts"
    ] == {
        "COMPLETE": 2,
        "GOLD_RETRY_REQUIRED": 1,
        "RAW_REBUILD_REQUIRED": 1,
        "RECOVERY_BLOCKED": 1,
        "MISSING_CYCLE": 1,
    }

    assert result[
        "action_counts"
    ] == {
        "NO_ACTION": 2,
        "RETRY_GOLD": 1,
        "REBUILD_SILVER_FROM_RAW": 1,
        "ALERT_AND_INVESTIGATE": 1,
        "INVESTIGATE_MISSING_CYCLE": 1,
    }

    assert result[
        "actionable_cycles"
    ] == 4

    assert result[
        "blocked_cycles"
    ] == 2

    assessments_by_date = {
        item["run_date"]: item
        for item
        in result[
            "assessments"
        ]
    }

    assert (
        assessments_by_date[
            "2026-09-21"
        ][
            "calendar_status"
        ]
        == "EXPECTED"
    )

    assert (
        assessments_by_date[
            "2026-09-26"
        ][
            "calendar_status"
        ]
        == "UNEXPECTED_OBSERVED"
    )

    assert (
        assessments_by_date[
            "2026-09-25"
        ][
            "status"
        ]
        == "MISSING_CYCLE"
    )


def test_build_recovery_plan_respects_excluded_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    ]

    monkeypatch.setattr(
        gold_recovery,
        "discover_observed_run_dates",
        lambda **kwargs: observed_dates,
    )

    monkeypatch.setattr(
        gold_recovery,
        "assess_run_date",
        lambda *, bucket, run_date: {
            "status": "COMPLETE",
            "run_date": (
                run_date.isoformat()
            ),
        },
    )

    result = (
        gold_recovery
        .build_recovery_plan(
            bucket=BUCKET,
            end_date=date(
                2026,
                9,
                23,
            ),
            lookback_days=3,
            excluded_dates={
                date(
                    2026,
                    9,
                    23,
                )
            },
        )
    )

    assert result[
        "expected_run_dates"
    ] == [
        "2026-09-21",
        "2026-09-22",
    ]

    assert result[
        "missing_run_dates"
    ] == []

    assert result[
        "status"
    ] == "COMPLETE"