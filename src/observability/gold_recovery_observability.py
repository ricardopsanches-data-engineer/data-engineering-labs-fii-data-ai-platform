from __future__ import annotations

from typing import Any

from src.observability.events import (
    emit_observability_event,
)


PIPELINE_NAME = "gold-recovery"


ASSESSMENT_EVENT_BY_STATUS = {
    "COMPLETE": (
        "GOLD_RECOVERY_COMPLETE",
        "INFO",
    ),
    "IN_PROGRESS": (
        "GOLD_RECOVERY_WAITING",
        "INFO",
    ),
    "GOLD_RETRY_REQUIRED": (
        "GOLD_RECOVERY_RETRY_REQUIRED",
        "WARN",
    ),
    "RAW_REBUILD_REQUIRED": (
        "GOLD_RAW_REBUILD_REQUIRED",
        "WARN",
    ),
    "RECOVERY_BLOCKED": (
        "GOLD_RECOVERY_BLOCKED",
        "ERROR",
    ),
}


ASSESSMENT_EVENT_BY_REASON = {
    "EXECUTION_SUCCEEDED_BUT_GOLD_OBJECT_MISSING": (
        "GOLD_INCONSISTENT_STATE",
        "ERROR",
    ),
    "STARTED_EXECUTION_STALE": (
        "GOLD_EXECUTION_STALE",
        "WARN",
    ),
    "PREVIOUS_EXECUTION_FAILED": (
        "GOLD_PREVIOUS_EXECUTION_FAILED",
        "ERROR",
    ),
}


EXECUTION_EVENT_BY_STATUS = {
    "DISPATCHED": (
        "GOLD_RECOVERY_DISPATCHED",
        "WARN",
    ),
    "WAITING": (
        "GOLD_RECOVERY_WAITING",
        "INFO",
    ),
    "BLOCKED": (
        "GOLD_RECOVERY_BLOCKED",
        "ERROR",
    ),
    "SKIPPED": (
        "GOLD_RECOVERY_SKIPPED",
        "INFO",
    ),
}


GOLD_STATE_EVENT_BY_STATUS = {
    "STARTED": (
        "GOLD_EXECUTION_STARTED",
        "INFO",
    ),
    "SUCCEEDED": (
        "GOLD_EXECUTION_SUCCEEDED",
        "INFO",
    ),
    "FAILED": (
        "GOLD_EXECUTION_FAILED",
        "ERROR",
    ),
}


def _compact_details(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Removes None values from event details.

    Empty strings, zero and False are
    intentionally preserved.
    """

    return {
        key: value
        for (
            key,
            value,
        )
        in payload.items()
        if value is not None
    }


def build_assessment_event(
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """
    Converts one Gold recovery assessment
    into an operational observability event.

    Recovery logic remains outside this
    module. This function only translates
    an already-decided assessment into
    telemetry.
    """

    status = str(
        assessment.get(
            "status",
            "UNKNOWN",
        )
    ).upper()

    reason = assessment.get(
        "reason"
    )

    reason_key = (
        str(reason).upper()
        if reason is not None
        else None
    )

    event_definition = None

    if reason_key is not None:
        event_definition = (
            ASSESSMENT_EVENT_BY_REASON.get(
                reason_key
            )
        )

    if event_definition is None:
        event_definition = (
            ASSESSMENT_EVENT_BY_STATUS.get(
                status,
                (
                    "GOLD_RECOVERY_ASSESSMENT",
                    "WARN",
                ),
            )
        )

    (
        event,
        severity,
    ) = event_definition

    details = _compact_details(
        {
            "run_date": assessment.get(
                "run_date"
            ),
            "assessment_status": status,
            "action": assessment.get(
                "action"
            ),
            "reason": reason,
            "gold_exists": assessment.get(
                "gold_exists"
            ),
            "reference_date": assessment.get(
                "reference_date"
            ),
        }
    )

    return {
        "event": event,
        "status": severity,
        **details,
    }


def emit_assessment_event(
    assessment: dict[str, Any],
) -> dict[str, Any]:
    event_payload = (
        build_assessment_event(
            assessment
        )
    )

    emit_observability_event(
        event_payload["event"],
        pipeline=PIPELINE_NAME,
        status=event_payload["status"],
        **{
            key: value
            for (
                key,
                value,
            )
            in event_payload.items()
            if key
            not in {
                "event",
                "status",
            }
        },
    )

    return event_payload


def build_execution_result_event(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Converts the result of one recovery
    action into an observability event.
    """

    status = str(
        result.get(
            "status",
            "UNKNOWN",
        )
    ).upper()

    (
        event,
        severity,
    ) = EXECUTION_EVENT_BY_STATUS.get(
        status,
        (
            "GOLD_RECOVERY_EXECUTION_RESULT",
            "WARN",
        ),
    )

    details = _compact_details(
        {
            "run_date": result.get(
                "run_date"
            ),
            "execution_status": status,
            "action": result.get(
                "action"
            ),
            "reason": result.get(
                "reason"
            ),
            "function_name": result.get(
                "function_name"
            ),
        }
    )

    return {
        "event": event,
        "status": severity,
        **details,
    }


def emit_execution_result_event(
    result: dict[str, Any],
) -> dict[str, Any]:
    event_payload = (
        build_execution_result_event(
            result
        )
    )

    emit_observability_event(
        event_payload["event"],
        pipeline=PIPELINE_NAME,
        status=event_payload["status"],
        **{
            key: value
            for (
                key,
                value,
            )
            in event_payload.items()
            if key
            not in {
                "event",
                "status",
            }
        },
    )

    return event_payload


def build_gold_execution_state_event(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Converts persisted Gold execution state
    into an operational observability event.

    Accepts either the persisted state payload
    itself or the result returned by
    write_execution_state(), which wraps the
    persisted state under "payload".

    Execution metadata may exist either at the
    top level or under "details".
    """

    wrapped_payload = state.get(
        "payload"
    )

    if isinstance(
        wrapped_payload,
        dict,
    ):
        execution_state = (
            wrapped_payload
        )
    else:
        execution_state = state

    nested_details = (
        execution_state.get(
            "details"
        )
    )

    if not isinstance(
        nested_details,
        dict,
    ):
        nested_details = {}

    def state_value(
        key: str,
    ) -> Any:
        value = execution_state.get(
            key
        )

        if value is not None:
            return value

        return nested_details.get(
            key
        )

    status = str(
        execution_state.get(
            "status",
            "UNKNOWN",
        )
    ).upper()

    (
        event,
        severity,
    ) = GOLD_STATE_EVENT_BY_STATUS.get(
        status,
        (
            "GOLD_EXECUTION_UNKNOWN_STATE",
            "WARN",
        ),
    )

    details = _compact_details(
        {
            "run_date": state_value(
                "run_date"
            ),
            "execution_status": status,
            "trigger": state_value(
                "trigger"
            ),
            "request_id": state_value(
                "request_id"
            ),
            "reference_date": state_value(
                "reference_date"
            ),
            "gold_key": state_value(
                "gold_key"
            ),
            "records": state_value(
                "records"
            ),
            "started_at": state_value(
                "started_at"
            ),
            "updated_at": state_value(
                "updated_at"
            ),
            "error_type": state_value(
                "error_type"
            ),
            "error_message": state_value(
                "error_message"
            ),
        }
    )

    return {
        "event": event,
        "status": severity,
        **details,
    }


def emit_gold_execution_state_event(
    state: dict[str, Any],
) -> dict[str, Any]:
    event_payload = (
        build_gold_execution_state_event(
            state
        )
    )

    emit_observability_event(
        event_payload["event"],
        pipeline=PIPELINE_NAME,
        status=event_payload["status"],
        **{
            key: value
            for (
                key,
                value,
            )
            in event_payload.items()
            if key
            not in {
                "event",
                "status",
            }
        },
    )

    return event_payload


def build_missing_cycle_event(
    *,
    run_date: str,
    reason: str = "EXPECTED_CYCLE_NOT_OBSERVED",
) -> dict[str, Any]:
    return {
        "event": "GOLD_MISSING_CYCLE",
        "status": "ERROR",
        "run_date": run_date,
        "reason": reason,
    }


def emit_missing_cycle_event(
    *,
    run_date: str,
    reason: str = "EXPECTED_CYCLE_NOT_OBSERVED",
) -> dict[str, Any]:
    event_payload = (
        build_missing_cycle_event(
            run_date=run_date,
            reason=reason,
        )
    )

    emit_observability_event(
        event_payload["event"],
        pipeline=PIPELINE_NAME,
        status=event_payload["status"],
        run_date=event_payload[
            "run_date"
        ],
        reason=event_payload[
            "reason"
        ],
    )

    return event_payload


def build_recovery_summary_event(
    execution_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds one summary event for the
    complete recovery executor run.
    """

    status = str(
        execution_result.get(
            "status",
            "UNKNOWN",
        )
    ).upper()

    blocked = int(
        execution_result.get(
            "blocked",
            0,
        )
    )

    waiting = int(
        execution_result.get(
            "waiting",
            0,
        )
    )

    if blocked > 0:
        severity = "ERROR"
    elif waiting > 0:
        severity = "WARN"
    else:
        severity = "INFO"

    return {
        "event": (
            "GOLD_RECOVERY_EXECUTION_SUMMARY"
        ),
        "status": severity,
        "execution_status": status,
        "total_results": int(
            execution_result.get(
                "total_results",
                0,
            )
        ),
        "dispatched": int(
            execution_result.get(
                "dispatched",
                0,
            )
        ),
        "waiting": waiting,
        "blocked": blocked,
        "skipped": int(
            execution_result.get(
                "skipped",
                0,
            )
        ),
    }


def emit_recovery_summary_event(
    execution_result: dict[str, Any],
) -> dict[str, Any]:
    event_payload = (
        build_recovery_summary_event(
            execution_result
        )
    )

    emit_observability_event(
        event_payload["event"],
        pipeline=PIPELINE_NAME,
        status=event_payload["status"],
        **{
            key: value
            for (
                key,
                value,
            )
            in event_payload.items()
            if key
            not in {
                "event",
                "status",
            }
        },
    )

    return event_payload