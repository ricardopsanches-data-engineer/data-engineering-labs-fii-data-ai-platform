from __future__ import annotations



import pytest



from src.observability import (

    gold_recovery_watchdog_notifications,

)





TOPIC_ARN = (

    "arn:aws:sns:sa-east-1:123456789012:"

    "fii-data-ai-platform-dev-gold-operational-alerts"

)





class FakeSNSClient:

    def __init__(

        self,

    ) -> None:

        self.publish_calls: list[

            dict

        ] = []



    def publish(

        self,

        *,

        TopicArn: str,

        Subject: str,

        Message: str,

    ) -> dict:

        self.publish_calls.append(

            {

                "TopicArn": TopicArn,

                "Subject": Subject,

                "Message": Message,

            }

        )



        return {

            "MessageId": (

                "fake-message-id"

            )

        }





def install_fake_sns(

    monkeypatch: pytest.MonkeyPatch,

) -> FakeSNSClient:

    fake_sns = FakeSNSClient()



    monkeypatch.setattr(

        (

            gold_recovery_watchdog_notifications

            .boto3

        ),

        "client",

        lambda service_name: fake_sns,

    )



    return fake_sns





@pytest.mark.parametrize(

    (

        "value",

        "expected",

    ),

    [

        (

            "PIPELINE_COMPLETE",

            "PIPELINE_COMPLETE",

        ),

        (

            "recovery_dispatched",

            "RECOVERY_DISPATCHED",

        ),

        (

            " final_failed ",

            "FINAL_FAILED",

        ),

    ],

)

def test_normalize_outcome(

    value: str,

    expected: str,

) -> None:

    assert (

        gold_recovery_watchdog_notifications

        .normalize_outcome(

            value

        )

        == expected

    )





def test_normalize_outcome_rejects_unknown(

) -> None:

    with pytest.raises(

        ValueError,

        match=(

            "Unsupported watchdog "

            "notification outcome"

        ),

    ):

        (

            gold_recovery_watchdog_notifications

            .normalize_outcome(

                "UNKNOWN"

            )

        )





@pytest.mark.parametrize(

    (

        "outcome",

        "expected_label",

    ),

    [

        (

            "PIPELINE_COMPLETE",

            "SUCCESS",

        ),

        (

            "RECOVERY_DISPATCHED",

            "RECOVERY",

        ),

        (
            "RECOVERY_PENDING",
            "PENDING",
        ),

        (

            "FINAL_RECOVERY_DISPATCHED",

            "FINAL RECOVERY",

        ),

        (
            "FINAL_ATTEMPT_PENDING",
            "FINAL PENDING",
        ),

        (

            "FINAL_SUCCESS",

            "FINAL SUCCESS",

        ),

        (

            "FINAL_FAILED",

            "FINAL FAILED",

        ),

    ],

)

def test_build_notification_subject(

    outcome: str,

    expected_label: str,

) -> None:

    subject = (

        gold_recovery_watchdog_notifications

        .build_notification_subject(

            outcome=outcome,

            attempt=2,

            max_attempts=3,

        )

    )



    assert expected_label in subject

    assert "(2/3)" in subject

    assert len(subject) < 100





@pytest.mark.parametrize(

    (

        "value",

        "expected",

    ),

    [

        (

            None,

            "-",

        ),

        (

            True,

            "YES",

        ),

        (

            False,

            "NO",

        ),

        (

            [

                "b3",

                "cvm",

            ],

            "b3, cvm",

        ),

        (

            "Gold",

            "Gold",

        ),

        (

            3,

            "3",

        ),

    ],

)

def test_stringify_value(

    value,

    expected: str,

) -> None:

    assert (

        gold_recovery_watchdog_notifications

        .stringify_value(

            value

        )

        == expected

    )





def test_build_message_for_success(

) -> None:

    message = (

        gold_recovery_watchdog_notifications

        .build_notification_message(

            watchdog_date=(

                "2026-09-25"

            ),

            attempt=1,

            max_attempts=3,

            check_hour=10,

            outcome=(

                "PIPELINE_COMPLETE"

            ),

            plan_status="COMPLETE",

            recovery_action=(

                "NO_ACTION"

            ),

            pipeline_stage=(

                "PIPELINE"

            ),

            result_status="SUCCESS",

            final_attempt=False,

        )

    )



    assert (

        "Run date: 2026-09-25"

        in message

    )



    assert (

        "Attempt: 1/3"

        in message

    )



    assert (

        "Check time: 10:00"

        in message

    )



    assert (

        "Outcome: PIPELINE_COMPLETE"

        in message

    )



    assert (

        "Daily watchdog cycle "

        "closed successfully"

        in message

    )



    assert (

        "Next automatic check:"

        not in message

    )





def test_build_message_for_recovery_with_next_check(

) -> None:

    message = (

        gold_recovery_watchdog_notifications

        .build_notification_message(

            watchdog_date=(

                "2026-09-25"

            ),

            attempt=1,

            max_attempts=3,

            check_hour=10,

            outcome=(

                "RECOVERY_DISPATCHED"

            ),

            plan_status=(

                "RECOVERY_REQUIRED"

            ),

            recovery_action=(

                "REBUILD_SILVER_FROM_RAW"

            ),

            pipeline_stage=(

                "B3 RAW -> Silver"

            ),

            result_status=(

                "DISPATCHED"

            ),

            final_attempt=False,

            next_check_hour=14,

            details={

                "source": "b3",

                "blocked_cycles": 0,

            },

        )

    )



    assert (

        "Recovery action: "

        "REBUILD_SILVER_FROM_RAW"

        in message

    )



    assert (

        "Pipeline stage: "

        "B3 RAW -> Silver"

        in message

    )



    assert (

        "Next automatic check: "

        "14:00"

        in message

    )



    assert (

        "- source: b3"

        in message

    )



    assert (

        "- blocked_cycles: 0"

        in message

    )





def test_build_message_for_final_failure(

) -> None:

    message = (

        gold_recovery_watchdog_notifications

        .build_notification_message(

            watchdog_date=(

                "2026-09-25"

            ),

            attempt=3,

            max_attempts=3,

            check_hour=20,

            outcome="FINAL_FAILED",

            plan_status=(

                "RECOVERY_REQUIRED"

            ),

            recovery_action=(

                "NO_ACTION"

            ),

            pipeline_stage="Gold",

            result_status="FAILED",

            final_attempt=True,

        )

    )



    assert (

        "Final attempt: YES"

        in message

    )



    assert (

        "Manual intervention "

        "is required"

        in message

    )





@pytest.mark.parametrize(

    "outcome",

    [

        "PIPELINE_COMPLETE",

        "RECOVERY_DISPATCHED",

        "RECOVERY_PENDING",

        "FINAL_RECOVERY_DISPATCHED",

        "FINAL_ATTEMPT_PENDING",

        "FINAL_SUCCESS",

        "FINAL_FAILED",

    ],

)

def test_build_operational_footer_for_all_outcomes(

    outcome: str,

) -> None:

    footer = (

        gold_recovery_watchdog_notifications

        .build_operational_footer(

            outcome=outcome

        )

    )



    assert footer

    assert isinstance(

        footer,

        str,

    )





def test_publish_watchdog_notification(

    monkeypatch: pytest.MonkeyPatch,

) -> None:

    fake_sns = install_fake_sns(

        monkeypatch

    )



    result = (

        gold_recovery_watchdog_notifications

        .publish_watchdog_notification(

            topic_arn=TOPIC_ARN,

            watchdog_date=(

                "2026-09-25"

            ),

            attempt=2,

            max_attempts=3,

            check_hour=14,

            outcome=(

                "RECOVERY_DISPATCHED"

            ),

            plan_status=(

                "RECOVERY_REQUIRED"

            ),

            recovery_action=(

                "RETRY_GOLD"

            ),

            pipeline_stage="Gold",

            result_status=(

                "DISPATCHED"

            ),

            final_attempt=False,

            next_check_hour=18,

            details={

                "run_date": (

                    "2026-09-24"

                )

            },

        )

    )



    assert (

        result["message_id"]

        == "fake-message-id"

    )



    assert (

        result["topic_arn"]

        == TOPIC_ARN

    )



    assert len(

        fake_sns.publish_calls

    ) == 1



    publish_call = (

        fake_sns.publish_calls[

            0

        ]

    )



    assert (

        publish_call[

            "TopicArn"

        ]

        == TOPIC_ARN

    )



    assert (

        "Watchdog RECOVERY"

        in publish_call[

            "Subject"

        ]

    )



    assert (

        "Next automatic check: "

        "18:00"

        in publish_call[

            "Message"

        ]

    )





def test_publish_watchdog_notification_rejects_empty_topic(

) -> None:

    with pytest.raises(

        ValueError,

        match="topic_arn is required",

    ):

        (

            gold_recovery_watchdog_notifications

            .publish_watchdog_notification(

                topic_arn="   ",

                watchdog_date=(

                    "2026-09-25"

                ),

                attempt=1,

                max_attempts=3,

                check_hour=10,

                outcome=(

                    "PIPELINE_COMPLETE"

                ),

                plan_status=(

                    "COMPLETE"

                ),

                recovery_action=(

                    "NO_ACTION"

                ),

                pipeline_stage=(

                    "PIPELINE"

                ),

                result_status=(

                    "SUCCESS"

                ),

                final_attempt=False,

            )

        )