from __future__ import annotations

from typing import Any

import boto3


SUPPORTED_OUTCOMES = {
    "PIPELINE_COMPLETE",
    "RECOVERY_DISPATCHED",
    "RECOVERY_PENDING",
    "FINAL_RECOVERY_DISPATCHED",
    "FINAL_ATTEMPT_PENDING",
    "FINAL_SUCCESS",
    "FINAL_FAILED",
}


def normalize_outcome(
    outcome: str,
) -> str:
    """
    Normaliza e valida o resultado operacional
    do watchdog usado nas notificações.
    """

    normalized = str(
        outcome
    ).strip().upper()

    if normalized not in SUPPORTED_OUTCOMES:
        raise ValueError(
            "Unsupported watchdog notification outcome | "
            f"outcome={outcome} | "
            f"supported={sorted(SUPPORTED_OUTCOMES)}"
        )

    return normalized


def build_notification_subject(
    *,
    outcome: str,
    attempt: int,
    max_attempts: int,
) -> str:
    """
    Constrói subject curto e operacional.
    """

    normalized_outcome = normalize_outcome(
        outcome
    )

    labels = {
        "PIPELINE_COMPLETE": "SUCCESS",
        "RECOVERY_DISPATCHED": "RECOVERY",
        "RECOVERY_PENDING": "PENDING",
        "FINAL_RECOVERY_DISPATCHED": (
            "FINAL RECOVERY"
        ),
        "FINAL_ATTEMPT_PENDING": (
            "FINAL PENDING"
        ),
        "FINAL_SUCCESS": "FINAL SUCCESS",
        "FINAL_FAILED": "FINAL FAILED",
    }

    label = labels[
        normalized_outcome
    ]

    return (
        "[FII Data Platform] "
        f"Watchdog {label} "
        f"({attempt}/{max_attempts})"
    )


def stringify_value(
    value: Any,
) -> str:
    """
    Converte valores para representação
    amigável no corpo do e-mail.
    """

    if value is None:
        return "-"

    if isinstance(
        value,
        bool,
    ):
        return (
            "YES"
            if value
            else "NO"
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return ", ".join(
            str(item)
            for item in value
        )

    return str(
        value
    )


def build_operational_footer(
    *,
    outcome: str,
) -> str:
    """
    Traduz o resultado em próxima ação
    operacional explícita.
    """

    normalized_outcome = normalize_outcome(
        outcome
    )

    footers = {
        "PIPELINE_COMPLETE": (
            "Daily watchdog cycle closed successfully. "
            "No further recovery action is required today."
        ),
        "RECOVERY_DISPATCHED": (
            "Recovery was dispatched. "
            "The daily watchdog cycle remains open."
        ),
        "RECOVERY_PENDING": (
            "The pipeline is still incomplete, but no new "
            "recovery dispatch was performed in this check. "
            "The daily watchdog cycle remains open."
        ),
        "FINAL_RECOVERY_DISPATCHED": (
            "The final automatic recovery was dispatched. "
            "No additional recovery attempts will be made today. "
            "A final verification will determine the result."
        ),
        "FINAL_ATTEMPT_PENDING": (
            "The final automatic recovery opportunity was consumed, "
            "but no new recovery dispatch was performed. "
            "No additional recovery attempts will be made today. "
            "A final verification will determine the result."
        ),
        "FINAL_SUCCESS": (
            "Final verification succeeded. "
            "The daily watchdog cycle is closed successfully."
        ),
        "FINAL_FAILED": (
            "Automatic recovery was exhausted and the pipeline "
            "is still incomplete. Manual intervention is required."
        ),
    }

    return footers[
        normalized_outcome
    ]


def build_notification_message(
    *,
    watchdog_date: str,
    attempt: int,
    max_attempts: int,
    check_hour: int,
    outcome: str,
    plan_status: str,
    recovery_action: str,
    pipeline_stage: str,
    result_status: str,
    final_attempt: bool,
    next_check_hour: int | None = None,
    details: dict[str, Any] | None = None,
) -> str:
    """
    Constrói o corpo textual da notificação
    operacional do watchdog.
    """

    normalized_outcome = normalize_outcome(
        outcome
    )

    lines = [
        "FII Data Platform - Gold Recovery Watchdog",
        "",
        f"Run date: {watchdog_date}",
        (
            "Attempt: "
            f"{attempt}/{max_attempts}"
        ),
        (
            "Check time: "
            f"{check_hour:02d}:00 "
            "America/Sao_Paulo"
        ),
        f"Outcome: {normalized_outcome}",
        f"Plan status: {plan_status}",
        f"Pipeline stage: {pipeline_stage}",
        f"Recovery action: {recovery_action}",
        f"Result: {result_status}",
        (
            "Final attempt: "
            f"{stringify_value(final_attempt)}"
        ),
    ]

    if next_check_hour is not None:
        lines.extend(
            [
                "",
                (
                    "Next automatic check: "
                    f"{next_check_hour:02d}:00 "
                    "America/Sao_Paulo"
                ),
            ]
        )

    if details:
        lines.extend(
            [
                "",
                "Details:",
            ]
        )

        for key in sorted(
            details
        ):
            lines.append(
                f"- {key}: "
                f"{stringify_value(details[key])}"
            )

    lines.extend(
        [
            "",
            build_operational_footer(
                outcome=normalized_outcome
            ),
        ]
    )

    return "\n".join(
        lines
    )


def publish_watchdog_notification(
    *,
    topic_arn: str,
    watchdog_date: str,
    attempt: int,
    max_attempts: int,
    check_hour: int,
    outcome: str,
    plan_status: str,
    recovery_action: str,
    pipeline_stage: str,
    result_status: str,
    final_attempt: bool,
    next_check_hour: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Publica notificação operacional via SNS.

    Esta função não decide se deve haver
    recovery. Ela apenas notifica o resultado
    já decidido pelo supervisor.
    """

    normalized_topic_arn = str(
        topic_arn
    ).strip()

    if not normalized_topic_arn:
        raise ValueError(
            "topic_arn is required."
        )

    subject = (
        build_notification_subject(
            outcome=outcome,
            attempt=attempt,
            max_attempts=max_attempts,
        )
    )

    message = (
        build_notification_message(
            watchdog_date=watchdog_date,
            attempt=attempt,
            max_attempts=max_attempts,
            check_hour=check_hour,
            outcome=outcome,
            plan_status=plan_status,
            recovery_action=recovery_action,
            pipeline_stage=pipeline_stage,
            result_status=result_status,
            final_attempt=final_attempt,
            next_check_hour=(
                next_check_hour
            ),
            details=details,
        )
    )

    sns_client = boto3.client(
        "sns"
    )

    response = sns_client.publish(
        TopicArn=normalized_topic_arn,
        Subject=subject,
        Message=message,
    )

    return {
        "topic_arn": (
            normalized_topic_arn
        ),
        "subject": subject,
        "message": message,
        "message_id": (
            response.get(
                "MessageId"
            )
        ),
    }