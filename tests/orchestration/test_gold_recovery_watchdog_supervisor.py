from __future__ import annotations



from datetime import date

import pytest



from src.orchestration import (

    gold_recovery_supervisor,

)





BUCKET = (

    "fii-data-ai-platform-dev-"

    "datalake-test"

)



TOPIC_ARN = (

    "arn:aws:sns:sa-east-1:"

    "123456789012:"

    "gold-operational-alerts"

)



GOLD_FUNCTION_NAME = (

    "fii-data-ai-platform-dev-"

    "fii-master-gold"

)



RAW_TO_SILVER_FUNCTIONS = {

    "b3": "b3-raw-to-silver",

    "cvm": "cvm-raw-to-silver",

    "b3_instruments": (

        "b3-instruments-raw-to-silver"

    ),

}





def build_configuration(

) -> dict:

    return {

        "bucket": BUCKET,

        "gold_function_name": (

            GOLD_FUNCTION_NAME

        ),

        "raw_to_silver_functions": (

            RAW_TO_SILVER_FUNCTIONS

        ),

        "end_date": date(

            2026,

            9,

            25,

        ),

        "lookback_days": 1,

    }





def build_watchdog_event(

    *,

    attempt: int,

    check_hour: int,

    final_attempt: bool,

    verification_only: bool = False,

) -> dict:

    return {

        "trigger": "watchdog",

        "attempt": attempt,

        "max_attempts": 3,

        "final_attempt": final_attempt,

        "check_hour": check_hour,

        "verification_only": (

            verification_only

        ),

    }





def install_topic_environment(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    monkeypatch.setenv(

        (

            gold_recovery_supervisor

            .WATCHDOG_NOTIFICATION_TOPIC_ENV

        ),

        TOPIC_ARN,

    )





def test_is_watchdog_event(

) -> None:

    assert (

        gold_recovery_supervisor

        .is_watchdog_event(

            event={

                "trigger": "watchdog"

            }

        )

        is True

    )



    assert (

        gold_recovery_supervisor

        .is_watchdog_event(

            event={}

        )

        is False

    )





def test_resolve_watchdog_configuration(

) -> None:

    result = (

        gold_recovery_supervisor

        .resolve_watchdog_configuration(

            event=(

                build_watchdog_event(

                    attempt=2,

                    check_hour=14,

                    final_attempt=False,

                )

            )

        )

    )



    assert result == {

        "attempt": 2,

        "max_attempts": 3,

        "final_attempt": False,

        "check_hour": 14,

        "verification_only": False,

    }



@pytest.mark.parametrize(

    (

        "check_hour",

        "expected",

    ),

    [

        (

            10,

            14,

        ),

        (

            14,

            18,

        ),

        (

            18,

            20,

        ),

        (

            20,

            None,

        ),

    ],

)

def test_resolve_next_check_hour(

    check_hour: int,

    expected: int | None,

) -> None:

    assert (

        gold_recovery_supervisor

        .resolve_next_check_hour(

            check_hour=check_hour

        )

        == expected

    )





def test_watchdog_success_at_10_closes_day(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: None,

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: {

            "status": "EXECUTED",

            "supervisor": "gold-recovery",

            "plan_status": "COMPLETE",

            "actionable_cycles": 0,

            "blocked_cycles": 0,

            "recovery_plan": {

                "status": "COMPLETE",

                "assessments": [

                    {

                        "status": "COMPLETE",

                        "action": "NO_ACTION",

                        "run_date": (

                            "2026-09-25"

                        ),

                    }

                ],

            },

            "execution": {

                "status": "EXECUTED",

                "dispatched": 0,

                "waiting": 0,

                "blocked": 0,

                "skipped": 1,

                "results": [

                    {

                        "status": "SKIPPED",

                        "action": "NO_ACTION",

                        "run_date": (

                            "2026-09-25"

                        ),

                    }

                ],

            },

        },

    )



    def fake_write(

        **kwargs,

    ):

        writes.append(

            kwargs

        )



        return {

            "payload": kwargs,

        }



    def fake_publish(

        **kwargs,

    ):

        notifications.append(

            kwargs

        )



        return {

            "message_id": (

                "message-1"

            ),

        }



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        fake_write,

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        fake_publish,

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=1,

                    check_hour=10,

                    final_attempt=False,

                )

            ),

        )

    )



    assert (

        result["watchdog"][

            "outcome"

        ]

        == "PIPELINE_COMPLETE"

    )



    assert len(

        writes

    ) == 1



    assert (

        writes[0]["status"]

        == "CLOSED_SUCCESS"

    )



    assert (

        writes[0]["outcome"]

        == "PIPELINE_COMPLETE"

    )



    assert len(

        notifications

    ) == 1



    assert (

        notifications[0][

            "result_status"

        ]

        == "SUCCESS"

    )



    assert (

        notifications[0][

            "next_check_hour"

        ]

        is None

    )





def test_watchdog_recovery_at_10_keeps_day_open(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: None,

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: {

            "status": "EXECUTED",

            "supervisor": "gold-recovery",

            "plan_status": (

                "RECOVERY_REQUIRED"

            ),

            "actionable_cycles": 1,

            "blocked_cycles": 0,

            "recovery_plan": {

                "status": (

                    "RECOVERY_REQUIRED"

                ),

                "assessments": [

                    {

                        "status": (

                            "RAW_REBUILD_REQUIRED"

                        ),

                        "action": (

                            "REBUILD_SILVER_FROM_RAW"

                        ),

                        "run_date": (

                            "2026-09-25"

                        ),

                    }

                ],

            },

            "execution": {

                "status": "EXECUTED",

                "dispatched": 1,

                "waiting": 0,

                "blocked": 0,

                "skipped": 0,

                "results": [

                    {

                        "status": (

                            "DISPATCHED"

                        ),

                        "action": (

                            "REBUILD_SILVER_FROM_RAW"

                        ),

                        "run_date": (

                            "2026-09-25"

                        ),

                    }

                ],

            },

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        lambda **kwargs: (

            writes.append(

                kwargs

            )

            or {

                "payload": kwargs

            }

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: (

            notifications.append(

                kwargs

            )

            or {

                "message_id": (

                    "message-2"

                )

            }

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=1,

                    check_hour=10,

                    final_attempt=False,

                )

            ),

        )

    )



    assert (

        result["watchdog"][

            "outcome"

        ]

        == "RECOVERY_DISPATCHED"

    )



    assert (

        writes[0]["status"]

        == "OPEN"

    )



    assert (

        notifications[0][

            "next_check_hour"

        ]

        == 14

    )



    assert (

        notifications[0][

            "pipeline_stage"

        ]

        == "RAW_REBUILD_REQUIRED"

    )





def test_watchdog_closed_day_at_14_is_silent(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    existing_state = {

        "status": (

            "CLOSED_SUCCESS"

        ),

        "attempt": 1,

    }



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: (

            existing_state

        ),

    )



    standard_calls = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: (

            standard_calls.append(

                kwargs

            )

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=2,

                    check_hour=14,

                    final_attempt=False,

                )

            ),

        )

    )



    assert (

        result["status"]

        == "NO_ACTION"

    )



    assert (

        result["reason"]

        == "DAY_ALREADY_CLOSED"

    )



    assert standard_calls == []





def test_watchdog_final_attempt_at_18_marks_final_dispatch(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: {

            "status": "OPEN",

            "attempt": 2,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: {

            "status": "EXECUTED",

            "supervisor": "gold-recovery",

            "plan_status": (

                "RECOVERY_REQUIRED"

            ),

            "actionable_cycles": 1,

            "blocked_cycles": 0,

            "recovery_plan": {

                "status": (

                    "RECOVERY_REQUIRED"

                ),

                "assessments": [

                    {

                        "status": (

                            "GOLD_RETRY_REQUIRED"

                        ),

                        "action": (

                            "RETRY_GOLD"

                        ),

                        "run_date": (

                            "2026-09-25"

                        ),

                    }

                ],

            },

            "execution": {

                "status": "EXECUTED",

                "dispatched": 1,

                "waiting": 0,

                "blocked": 0,

                "skipped": 0,

                "results": [

                    {

                        "status": (

                            "DISPATCHED"

                        ),

                        "action": (

                            "RETRY_GOLD"

                        ),

                        "run_date": (

                            "2026-09-25"

                        ),

                    }

                ],

            },

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        lambda **kwargs: (

            writes.append(

                kwargs

            )

            or {

                "payload": kwargs

            }

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: (

            notifications.append(

                kwargs

            )

            or {

                "message_id": (

                    "message-3"

                )

            }

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=3,

                    check_hour=18,

                    final_attempt=True,

                )

            ),

        )

    )



    assert (

        result["watchdog"][

            "outcome"

        ]

        == (

            "FINAL_RECOVERY_DISPATCHED"

        )

    )



    assert (

        writes[0]["status"]

        == (

            "FINAL_RECOVERY_DISPATCHED"

        )

    )



    assert (

        notifications[0][

            "next_check_hour"

        ]

        == 20

    )



    assert (

        notifications[0][

            "recovery_action"

        ]

        == "RETRY_GOLD"

    )



    assert (

        notifications[0][

            "pipeline_stage"

        ]

        == "GOLD_RETRY_REQUIRED"

    )





def test_final_verification_at_20_closes_success(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: {

            "status": (

                "FINAL_RECOVERY_DISPATCHED"

            ),

            "attempt": 3,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "build_recovery_plan",

        lambda **kwargs: {

            "status": "COMPLETE",

            "actionable_cycles": 0,

            "blocked_cycles": 0,

            "assessments": [

                {

                    "status": "COMPLETE",

                    "action": "NO_ACTION",

                    "run_date": (

                        "2026-09-25"

                    ),

                }

            ],

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "execute_recovery_plan",

        lambda **kwargs: pytest.fail(

            "Final verification must not "

            "execute recovery."

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        lambda **kwargs: (

            writes.append(

                kwargs

            )

            or {

                "payload": kwargs

            }

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: (

            notifications.append(

                kwargs

            )

            or {

                "message_id": (

                    "final-success"

                )

            }

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=3,

                    check_hour=20,

                    final_attempt=True,

                    verification_only=True,

                )

            ),

        )

    )



    assert (

        result["watchdog"][

            "outcome"

        ]

        == "FINAL_SUCCESS"

    )



    assert (

        writes[0]["status"]

        == "CLOSED_SUCCESS"

    )



    assert (

        notifications[0][

            "recovery_action"

        ]

        == "NO_ACTION"

    )



    assert (

        notifications[0][

            "result_status"

        ]

        == "SUCCESS"

    )





def test_final_verification_at_20_closes_failure_without_recovery(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: {

            "status": (

                "FINAL_RECOVERY_DISPATCHED"

            ),

            "attempt": 3,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "build_recovery_plan",

        lambda **kwargs: {

            "status": (

                "RECOVERY_REQUIRED"

            ),

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

                        "2026-09-25"

                    ),

                }

            ],

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "execute_recovery_plan",

        lambda **kwargs: pytest.fail(

            "Final verification must not "

            "execute recovery."

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        lambda **kwargs: (

            writes.append(

                kwargs

            )

            or {

                "payload": kwargs

            }

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: (

            notifications.append(

                kwargs

            )

            or {

                "message_id": (

                    "final-failed"

                )

            }

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=3,

                    check_hour=20,

                    final_attempt=True,

                    verification_only=True,

                )

            ),

        )

    )



    assert (

        result["watchdog"][

            "outcome"

        ]

        == "FINAL_FAILED"

    )



    assert (

        writes[0]["status"]

        == "CLOSED_FAILED"

    )



    assert (

        notifications[0][

            "recovery_action"

        ]

        == "NO_ACTION"

    )



    assert (

        notifications[0][

            "pipeline_stage"

        ]

        == "GOLD_RETRY_REQUIRED"

    )



    assert (

        notifications[0][

            "result_status"

        ]

        == "FAILED"

    )


def test_watchdog_non_trading_day_is_silent(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    configuration = build_configuration()

    configuration["end_date"] = date(

        2026,

        9,

        7,

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "classify_date",

        lambda value: {

            "date": value.isoformat(),

            "expected": False,

            "status": "B3_HOLIDAY",

            "reason": "Independence Day",

            "special": False,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: pytest.fail(

            "Non-trading day must not read watchdog state."

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: pytest.fail(

            "Non-trading day must not run recovery."

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: pytest.fail(

            "Non-trading day must be silent."

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=configuration,

            event=(

                build_watchdog_event(

                    attempt=1,

                    check_hour=10,

                    final_attempt=False,

                )

            ),

        )

    )



    assert result["status"] == "NO_ACTION"

    assert result["reason"] == "NON_TRADING_DAY"

    assert (

        result["calendar"]["status"]

        == "B3_HOLIDAY"

    )



def test_watchdog_duplicate_same_check_is_silent(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    monkeypatch.setattr(

        gold_recovery_supervisor,

        "classify_date",

        lambda value: {

            "date": value.isoformat(),

            "expected": True,

            "status": "TRADING_DAY",

            "reason": "Regular B3 trading day",

            "special": False,

        },

    )



    existing_state = {

        "status": "OPEN",

        "attempt": 1,

        "check_hour": 10,

        "outcome": "RECOVERY_PENDING",

    }



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: existing_state,

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: pytest.fail(

            "Duplicate check must not run recovery again."

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: pytest.fail(

            "Duplicate check must not notify again."

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=1,

                    check_hour=10,

                    final_attempt=False,

                )

            ),

        )

    )



    assert result["status"] == "NO_ACTION"

    assert (

        result["reason"]

        == "CHECK_ALREADY_PROCESSED"

    )

    assert result["state"] == existing_state



def test_watchdog_recovery_pending_at_10(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "classify_date",

        lambda value: {

            "date": value.isoformat(),

            "expected": True,

            "status": "TRADING_DAY",

            "reason": "Regular B3 trading day",

            "special": False,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: None,

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: {

            "status": "EXECUTED",

            "supervisor": "gold-recovery",

            "plan_status": "RECOVERY_REQUIRED",

            "actionable_cycles": 1,

            "blocked_cycles": 0,

            "recovery_plan": {

                "status": "RECOVERY_REQUIRED",

                "assessments": [

                    {

                        "status": "GOLD_RETRY_REQUIRED",

                        "action": "RETRY_GOLD",

                        "run_date": "2026-09-25",

                    }

                ],

            },

            "execution": {

                "status": "EXECUTED",

                "dispatched": 0,

                "waiting": 1,

                "blocked": 0,

                "skipped": 0,

                "results": [],

            },

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        lambda **kwargs: (

            writes.append(kwargs)

            or {"payload": kwargs}

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: (

            notifications.append(kwargs)

            or {"message_id": "pending-10"}

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=1,

                    check_hour=10,

                    final_attempt=False,

                )

            ),

        )

    )



    assert (

        result["watchdog"]["outcome"]

        == "RECOVERY_PENDING"

    )

    assert writes[0]["status"] == "OPEN"

    assert notifications[0]["result_status"] == "PENDING"

    assert notifications[0]["next_check_hour"] == 14



def test_watchdog_final_attempt_pending_at_18(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    install_topic_environment(

        monkeypatch

    )



    writes = []

    notifications = []



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "classify_date",

        lambda value: {

            "date": value.isoformat(),

            "expected": True,

            "status": "TRADING_DAY",

            "reason": "Regular B3 trading day",

            "special": False,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "read_watchdog_state",

        lambda **kwargs: {

            "status": "OPEN",

            "attempt": 2,

            "check_hour": 14,

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "run_standard_supervisor",

        lambda **kwargs: {

            "status": "EXECUTED",

            "supervisor": "gold-recovery",

            "plan_status": "RECOVERY_REQUIRED",

            "actionable_cycles": 1,

            "blocked_cycles": 0,

            "recovery_plan": {

                "status": "RECOVERY_REQUIRED",

                "assessments": [

                    {

                        "status": "GOLD_RETRY_REQUIRED",

                        "action": "RETRY_GOLD",

                        "run_date": "2026-09-25",

                    }

                ],

            },

            "execution": {

                "status": "EXECUTED",

                "dispatched": 0,

                "waiting": 1,

                "blocked": 0,

                "skipped": 0,

                "results": [],

            },

        },

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "write_watchdog_state",

        lambda **kwargs: (

            writes.append(kwargs)

            or {"payload": kwargs}

        ),

    )



    monkeypatch.setattr(

        gold_recovery_supervisor,

        "publish_watchdog_notification",

        lambda **kwargs: (

            notifications.append(kwargs)

            or {"message_id": "pending-18"}

        ),

    )



    result = (

        gold_recovery_supervisor

        .run_watchdog_supervisor(

            configuration=(

                build_configuration()

            ),

            event=(

                build_watchdog_event(

                    attempt=3,

                    check_hour=18,

                    final_attempt=True,

                )

            ),

        )

    )



    assert (

        result["watchdog"]["outcome"]

        == "FINAL_ATTEMPT_PENDING"

    )

    assert (

        writes[0]["status"]

        == "FINAL_RECOVERY_DISPATCHED"

    )

    assert notifications[0]["result_status"] == "PENDING"

    assert notifications[0]["next_check_hour"] == 20
