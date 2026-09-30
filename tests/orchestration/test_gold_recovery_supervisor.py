from __future__ import annotations

from datetime import date

import pytest

from src.orchestration import (
    gold_recovery_supervisor,
)


BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)

GOLD_FUNCTION_NAME = (
    "fii-data-ai-platform-dev-"
    "fii-master-gold"
)

RAW_TO_SILVER_FUNCTIONS = {
    "b3": (
        "fii-data-ai-platform-dev-"
        "b3-raw-to-silver"
    ),
    "cvm": (
        "fii-data-ai-platform-dev-"
        "cvm-raw-to-silver"
    ),
    "b3_instruments": (
        "fii-data-ai-platform-dev-"
        "b3-instruments-raw-to-silver"
    ),
}


def set_required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FII_DATA_LAKE_BUCKET",
        BUCKET,
    )

    monkeypatch.setenv(
        "FII_MASTER_GOLD_FUNCTION_NAME",
        GOLD_FUNCTION_NAME,
    )

    monkeypatch.setenv(
        "FII_B3_RAW_TO_SILVER_FUNCTION_NAME",
        RAW_TO_SILVER_FUNCTIONS[
            "b3"
        ],
    )

    monkeypatch.setenv(
        "FII_CVM_RAW_TO_SILVER_FUNCTION_NAME",
        RAW_TO_SILVER_FUNCTIONS[
            "cvm"
        ],
    )

    monkeypatch.setenv(
        (
            "FII_B3_INSTRUMENTS_"
            "RAW_TO_SILVER_FUNCTION_NAME"
        ),
        RAW_TO_SILVER_FUNCTIONS[
            "b3_instruments"
        ],
    )


def test_require_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TEST_REQUIRED_VARIABLE",
        "value",
    )

    result = (
        gold_recovery_supervisor
        .require_environment_variable(
            "TEST_REQUIRED_VARIABLE"
        )
    )

    assert result == "value"


def test_require_environment_variable_rejects_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "TEST_REQUIRED_VARIABLE",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Required environment "
            "variable is missing"
        ),
    ):
        (
            gold_recovery_supervisor
            .require_environment_variable(
                "TEST_REQUIRED_VARIABLE"
            )
        )


def test_parse_positive_integer() -> None:
    result = (
        gold_recovery_supervisor
        .parse_positive_integer(
            value="30",
            field_name="lookback_days",
        )
    )

    assert result == 30


def test_parse_positive_integer_rejects_zero() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Expected positive integer"
        ),
    ):
        (
            gold_recovery_supervisor
            .parse_positive_integer(
                value=0,
                field_name=(
                    "lookback_days"
                ),
            )
        )


def test_parse_iso_date() -> None:
    result = (
        gold_recovery_supervisor
        .parse_iso_date(
            value="2026-09-25",
            field_name="end_date",
        )
    )

    assert result == date(
        2026,
        9,
        25,
    )


def test_parse_iso_date_rejects_invalid_value() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid ISO date",
    ):
        (
            gold_recovery_supervisor
            .parse_iso_date(
                value="25-09-2026",
                field_name="end_date",
            )
        )


def test_resolve_lookback_days_prefers_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FII_GOLD_RECOVERY_LOOKBACK_DAYS",
        "30",
    )

    result = (
        gold_recovery_supervisor
        .resolve_lookback_days(
            event={
                "lookback_days": 5,
            }
        )
    )

    assert result == 5


def test_resolve_lookback_days_uses_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FII_GOLD_RECOVERY_LOOKBACK_DAYS",
        "14",
    )

    result = (
        gold_recovery_supervisor
        .resolve_lookback_days(
            event={}
        )
    )

    assert result == 14


def test_resolve_lookback_days_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "FII_GOLD_RECOVERY_LOOKBACK_DAYS",
        raising=False,
    )

    result = (
        gold_recovery_supervisor
        .resolve_lookback_days(
            event={}
        )
    )

    assert (
        result
        == (
            gold_recovery_supervisor
            .DEFAULT_LOOKBACK_DAYS
        )
    )


def test_resolve_raw_to_silver_functions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(
        monkeypatch
    )

    result = (
        gold_recovery_supervisor
        .resolve_raw_to_silver_functions()
    )

    assert (
        result
        == RAW_TO_SILVER_FUNCTIONS
    )


def test_build_supervisor_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(
        monkeypatch
    )

    result = (
        gold_recovery_supervisor
        .build_supervisor_configuration(
            event={
                "end_date": (
                    "2026-09-25"
                ),
                "lookback_days": 5,
            }
        )
    )

    assert result[
        "bucket"
    ] == BUCKET

    assert (
        result[
            "gold_function_name"
        ]
        == GOLD_FUNCTION_NAME
    )

    assert (
        result[
            "raw_to_silver_functions"
        ]
        == RAW_TO_SILVER_FUNCTIONS
    )

    assert (
        result[
            "end_date"
        ]
        == date(
            2026,
            9,
            25,
        )
    )

    assert (
        result[
            "lookback_days"
        ]
        == 5
    )

    assert (
        "expected_weekdays"
        not in result
    )

    assert (
        "excluded_dates"
        not in result
    )


def test_build_supervisor_configuration_ignores_legacy_calendar_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(
        monkeypatch
    )

    result = (
        gold_recovery_supervisor
        .build_supervisor_configuration(
            event={
                "end_date": (
                    "2026-09-25"
                ),
                "lookback_days": 5,
                "expected_weekdays": [
                    0,
                    1,
                    2,
                    3,
                    4,
                ],
                "excluded_dates": [
                    "2026-09-07",
                ],
            }
        )
    )

    assert (
        "expected_weekdays"
        not in result
    )

    assert (
        "excluded_dates"
        not in result
    )


def test_run_gold_recovery_supervisor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(
        monkeypatch
    )

    captured_plan_arguments = {}
    captured_execution_arguments = {}

    recovery_plan = {
        "status": (
            "RECOVERY_REQUIRED"
        ),
        "window": {
            "start_date": (
                "2026-09-21"
            ),
            "end_date": (
                "2026-09-25"
            ),
            "lookback_days": 5,
        },
        "status_counts": {
            "COMPLETE": 3,
            (
                "GOLD_RETRY_REQUIRED"
            ): 1,
        },
        "action_counts": {
            "NO_ACTION": 3,
            "RETRY_GOLD": 1,
        },
        "actionable_cycles": 1,
        "blocked_cycles": 0,
        "assessments": [
            {
                "status": (
                    "GOLD_RETRY_REQUIRED"
                ),
                "action": (
                    "RETRY_GOLD"
                ),
                "run_date": (
                    "2026-09-24"
                ),
            },
        ],
        "total_assessments": 4,
    }

    execution_result = {
        "status": "EXECUTED",
        "total_results": 4,
        "dispatched": 1,
        "waiting": 0,
        "blocked": 0,
        "skipped": 3,
        "results": [],
    }

    def fake_build_recovery_plan(
        **kwargs,
    ):
        captured_plan_arguments.update(
            kwargs
        )

        return recovery_plan

    def fake_execute_recovery_plan(
        **kwargs,
    ):
        captured_execution_arguments.update(
            kwargs
        )

        return execution_result

    monkeypatch.setattr(
        gold_recovery_supervisor,
        "build_recovery_plan",
        fake_build_recovery_plan,
    )

    monkeypatch.setattr(
        gold_recovery_supervisor,
        "execute_recovery_plan",
        fake_execute_recovery_plan,
    )

    result = (
        gold_recovery_supervisor
        .run_gold_recovery_supervisor(
            event={
                "end_date": (
                    "2026-09-25"
                ),
                "lookback_days": 5,
            }
        )
    )

    assert (
        captured_plan_arguments[
            "bucket"
        ]
        == BUCKET
    )

    assert (
        captured_plan_arguments[
            "end_date"
        ]
        == date(
            2026,
            9,
            25,
        )
    )

    assert (
        captured_plan_arguments[
            "lookback_days"
        ]
        == 5
    )

    assert (
        "expected_weekdays"
        not in captured_plan_arguments
    )

    assert (
        "excluded_dates"
        not in captured_plan_arguments
    )

    assert (
        captured_execution_arguments[
            "recovery_plan"
        ]
        is recovery_plan
    )

    assert (
        captured_execution_arguments[
            "gold_function_name"
        ]
        == GOLD_FUNCTION_NAME
    )

    assert (
        captured_execution_arguments[
            "raw_to_silver_functions"
        ]
        == RAW_TO_SILVER_FUNCTIONS
    )

    assert (
        captured_execution_arguments[
            "bucket"
        ]
        == BUCKET
    )

    assert result[
        "status"
    ] == "EXECUTED"

    assert (
        result[
            "supervisor"
        ]
        == "gold-recovery"
    )

    assert (
        result[
            "plan_status"
        ]
        == "RECOVERY_REQUIRED"
    )

    assert (
        result[
            "actionable_cycles"
        ]
        == 1
    )

    assert (
        result[
            "blocked_cycles"
        ]
        == 0
    )

    assert (
        result[
            "execution"
        ]
        is execution_result
    )


def test_run_gold_recovery_supervisor_ignores_legacy_calendar_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(
        monkeypatch
    )

    captured_plan_arguments = {}

    def fake_build_recovery_plan(
        **kwargs,
    ):
        captured_plan_arguments.update(
            kwargs
        )

        return {
            "status": "COMPLETE",
            "window": {
                "start_date": (
                    "2026-09-25"
                ),
                "end_date": (
                    "2026-09-25"
                ),
                "lookback_days": 1,
            },
            "status_counts": {
                "COMPLETE": 1,
            },
            "action_counts": {
                "NO_ACTION": 1,
            },
            "actionable_cycles": 0,
            "blocked_cycles": 0,
            "assessments": [],
            "total_assessments": 1,
        }

    monkeypatch.setattr(
        gold_recovery_supervisor,
        "build_recovery_plan",
        fake_build_recovery_plan,
    )

    monkeypatch.setattr(
        gold_recovery_supervisor,
        "execute_recovery_plan",
        lambda **kwargs: {
            "status": "EXECUTED",
            "results": [],
        },
    )

    (
        gold_recovery_supervisor
        .run_gold_recovery_supervisor(
            event={
                "end_date": (
                    "2026-09-25"
                ),
                "lookback_days": 1,
                "expected_weekdays": (
                    "0,1,2,3,4"
                ),
                "excluded_dates": [
                    "2026-09-07",
                ],
            }
        )
    )

    assert (
        "expected_weekdays"
        not in captured_plan_arguments
    )

    assert (
        "excluded_dates"
        not in captured_plan_arguments
    )


def test_lambda_handler_normalizes_non_dict_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_event = {}

    def fake_run_gold_recovery_supervisor(
        *,
        event,
    ):
        captured_event.update(
            event
        )

        return {
            "status": "EXECUTED",
        }

    monkeypatch.setattr(
        gold_recovery_supervisor,
        "run_gold_recovery_supervisor",
        fake_run_gold_recovery_supervisor,
    )

    result = (
        gold_recovery_supervisor
        .lambda_handler(
            None,
            object(),
        )
    )

    assert captured_event == {}

    assert result == {
        "status": "EXECUTED",
    }