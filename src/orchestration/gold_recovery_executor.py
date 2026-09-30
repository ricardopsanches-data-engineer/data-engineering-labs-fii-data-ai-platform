from __future__ import annotations

import json

from typing import Any

import boto3

from src.observability.gold_recovery_observability import (
    emit_assessment_event,
    emit_execution_result_event,
    emit_missing_cycle_event,
    emit_recovery_summary_event,
)

SUPPORTED_ACTIONS = {
    "NO_ACTION",
    "WAIT_FOR_COMPLETION",
    "RETRY_GOLD",
    "REBUILD_SILVER_FROM_RAW",
    "ALERT_AND_INVESTIGATE",
    "INVESTIGATE_MISSING_CYCLE",
}


def invoke_lambda_async(
    *,
    function_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Invoca uma Lambda de forma assíncrona.

    StatusCode=202 significa somente que
    o evento foi aceito pela API Lambda.

    O sucesso real da execução é controlado
    pelo Gold execution state.
    """

    lambda_client = boto3.client(
        "lambda"
    )

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="Event",
        Payload=json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode(
            "utf-8"
        ),
    )

    status_code = response[
        "StatusCode"
    ]

    if status_code != 202:
        raise RuntimeError(
            "Unexpected Lambda async "
            "invoke response | "
            f"function={function_name} | "
            f"status_code={status_code}"
        )

    return {
        "function_name": (
            function_name
        ),
        "invoke_status_code": (
            status_code
        ),
        "payload": payload,
    }


def build_gold_recovery_payload(
    *,
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """
    Constrói o payload explícito usado
    pelo retry da Gold.

    O payload físico produzido pelo
    recovery plan é preservado, mas o
    trigger RECOVERY é acrescentado.

    Assim o handler Gold consegue
    distinguir execução normal de
    recuperação operacional.
    """

    gold_payload = assessment.get(
        "gold_payload"
    )

    if not isinstance(
        gold_payload,
        dict,
    ):
        raise ValueError(
            "Gold retry assessment "
            "must contain gold_payload."
        )

    run_date = assessment.get(
        "run_date"
    )

    payload_run_date = (
        gold_payload.get(
            "run_date"
        )
    )

    if (
        not run_date
        or payload_run_date
        != run_date
    ):
        raise ValueError(
            "Gold retry run_date "
            "mismatch | "
            f"assessment={run_date} | "
            f"payload={payload_run_date}"
        )

    return {
        **gold_payload,
        "trigger": "RECOVERY",
    }


def execute_gold_retry(
    *,
    assessment: dict[str, Any],
    gold_function_name: str,
) -> dict[str, Any]:
    """
    Executa recovery direto da Gold.

    Não passa pelo Gold Readiness
    Coordinator.

    Isso é intencional porque um dispatch
    lock antigo pode existir mesmo quando
    a execução Gold falhou após o aceite
    assíncrono HTTP 202.
    """

    status = assessment.get(
        "status"
    )

    action = assessment.get(
        "action"
    )

    if (
        status
        != "GOLD_RETRY_REQUIRED"
    ):
        raise ValueError(
            "Gold retry requires "
            "status="
            "GOLD_RETRY_REQUIRED | "
            f"received={status}"
        )

    if action != "RETRY_GOLD":
        raise ValueError(
            "Gold retry requires "
            "action=RETRY_GOLD | "
            f"received={action}"
        )

    recovery_payload = (
        build_gold_recovery_payload(
            assessment=assessment
        )
    )

    invocation = (
        invoke_lambda_async(
            function_name=(
                gold_function_name
            ),
            payload=(
                recovery_payload
            ),
        )
    )

    return {
        "status": (
            "DISPATCHED"
        ),
        "action": "RETRY_GOLD",
        "run_date": (
            assessment.get(
                "run_date"
            )
        ),
        "function_name": (
            gold_function_name
        ),
        "invoke_status_code": (
            invocation[
                "invoke_status_code"
            ]
        ),
        "payload": (
            recovery_payload
        ),
    }


def build_raw_to_silver_payload(
    *,
    assessment: dict[str, Any],
    source: str,
) -> dict[str, str]:
    """
    Constrói payload direto para a
    Lambda RAW->Silver existente.

    Contrato esperado pelo handler:

    {
        "bucket": "...",
        "key": "raw/..."
    }
    """

    source_states = assessment.get(
        "source_states"
    )

    if not isinstance(
        source_states,
        dict,
    ):
        raise ValueError(
            "RAW rebuild assessment "
            "must contain source_states."
        )

    source_state = (
        source_states.get(
            source
        )
    )

    if not isinstance(
        source_state,
        dict,
    ):
        raise ValueError(
            "Missing source state | "
            f"source={source}"
        )

    raw_objects = (
        source_state.get(
            "raw_objects"
        )
    )

    if (
        not isinstance(
            raw_objects,
            list,
        )
        or len(
            raw_objects
        )
        != 1
    ):
        raise ValueError(
            "RAW rebuild requires "
            "exactly one RAW object | "
            f"source={source}"
        )

    raw_key = (
        raw_objects[0]
        .get(
            "key"
        )
    )

    if not raw_key:
        raise ValueError(
            "RAW object is missing key | "
            f"source={source}"
        )

    bucket = assessment.get(
        "bucket"
    )

    if not bucket:
        raise ValueError(
            "RAW rebuild assessment "
            "must contain bucket."
        )

    return {
        "bucket": bucket,
        "key": raw_key,
    }


def execute_raw_rebuild(
    *,
    assessment: dict[str, Any],
    raw_to_silver_functions: (
        dict[str, str]
    ),
) -> dict[str, Any]:
    """
    Dispara as Lambdas RAW->Silver
    existentes para as fontes que
    precisam ser reconstruídas.

    O executor não duplica transformação.

    RAW->Silver existente continua
    responsável por reconstruir Silver
    e emitir readiness marker.
    """

    status = assessment.get(
        "status"
    )

    action = assessment.get(
        "action"
    )

    if (
        status
        != "RAW_REBUILD_REQUIRED"
    ):
        raise ValueError(
            "RAW rebuild requires "
            "status="
            "RAW_REBUILD_REQUIRED | "
            f"received={status}"
        )

    if (
        action
        != "REBUILD_SILVER_FROM_RAW"
    ):
        raise ValueError(
            "RAW rebuild requires "
            "action="
            "REBUILD_SILVER_FROM_RAW | "
            f"received={action}"
        )

    rebuild_sources = (
        assessment.get(
            "rebuild_sources"
        )
    )

    if (
        not isinstance(
            rebuild_sources,
            list,
        )
        or not rebuild_sources
    ):
        raise ValueError(
            "RAW rebuild assessment "
            "must contain rebuild_sources."
        )

    dispatches = []

    for source in rebuild_sources:
        function_name = (
            raw_to_silver_functions.get(
                source
            )
        )

        if not function_name:
            raise ValueError(
                "Missing RAW->Silver "
                "function mapping | "
                f"source={source}"
            )

        payload = (
            build_raw_to_silver_payload(
                assessment=assessment,
                source=source,
            )
        )

        invocation = (
            invoke_lambda_async(
                function_name=(
                    function_name
                ),
                payload=payload,
            )
        )

        dispatches.append(
            {
                "source": source,
                "function_name": (
                    function_name
                ),
                "invoke_status_code": (
                    invocation[
                        "invoke_status_code"
                    ]
                ),
                "payload": payload,
            }
        )

    return {
        "status": "DISPATCHED",
        "action": (
            "REBUILD_SILVER_FROM_RAW"
        ),
        "run_date": (
            assessment.get(
                "run_date"
            )
        ),
        "dispatches": dispatches,
    }


def execute_assessment(
    *,
    assessment: dict[str, Any],
    gold_function_name: str,
    raw_to_silver_functions: (
        dict[str, str]
    ),
    bucket: str,
) -> dict[str, Any]:
    """
    Executa uma entrada do recovery plan.

    Ações:

    NO_ACTION
        Nada precisa ser executado.

    WAIT_FOR_COMPLETION
        Existe execução Gold ativa.
        Nenhuma nova Lambda é disparada.

    RETRY_GOLD
        Invoca Gold diretamente com
        trigger RECOVERY.

    REBUILD_SILVER_FROM_RAW
        Invoca RAW->Silver existente.

    ALERT_AND_INVESTIGATE
    INVESTIGATE_MISSING_CYCLE
        Não fabricam dados.
        Permanecem bloqueadas para
        observabilidade e investigação.
    """

    action = assessment.get(
        "action"
    )

    if action not in SUPPORTED_ACTIONS:
        raise ValueError(
            "Unsupported recovery action: "
            f"{action}"
        )

    assessment_with_bucket = {
        **assessment,
        "bucket": bucket,
    }

    if action == "NO_ACTION":
        return {
            "status": "SKIPPED",
            "action": action,
            "run_date": (
                assessment.get(
                    "run_date"
                )
            ),
            "reason": (
                "NO_ACTION_REQUIRED"
            ),
        }

    if (
        action
        == "WAIT_FOR_COMPLETION"
    ):
        return {
            "status": "WAITING",
            "action": action,
            "run_date": (
                assessment.get(
                    "run_date"
                )
            ),
            "reason": (
                assessment.get(
                    "reason"
                )
                or
                "GOLD_EXECUTION_IN_PROGRESS"
            ),
        }

    if action == "RETRY_GOLD":
        return execute_gold_retry(
            assessment=(
                assessment_with_bucket
            ),
            gold_function_name=(
                gold_function_name
            ),
        )

    if (
        action
        == "REBUILD_SILVER_FROM_RAW"
    ):
        return execute_raw_rebuild(
            assessment=(
                assessment_with_bucket
            ),
            raw_to_silver_functions=(
                raw_to_silver_functions
            ),
        )

    return {
        "status": "BLOCKED",
        "action": action,
        "run_date": (
            assessment.get(
                "run_date"
            )
        ),
        "reason": (
            assessment.get(
                "reason"
            )
            or
            "MANUAL_INVESTIGATION_REQUIRED"
        ),
    }


def execute_recovery_plan(
    *,
    recovery_plan: dict[str, Any],
    gold_function_name: str,
    raw_to_silver_functions: (
        dict[str, str]
    ),
    bucket: str,
) -> dict[str, Any]:
    """
    Executa um recovery plan já produzido
    pelo gold_recovery.

    Esta função NÃO redescobre dados e
    NÃO recalcula decisões.

    Fases permanecem separadas:

        discover
        assess
        plan
        execute
        observe
    """

    assessments = (
        recovery_plan.get(
            "assessments"
        )
    )

    if not isinstance(
        assessments,
        list,
    ):
        raise ValueError(
            "Recovery plan must contain "
            "an assessments list."
        )

    results: list[
        dict[str, Any]
    ] = []

    for assessment in assessments:
        action = assessment.get(
            "action"
        )

        if (
            action
            == "INVESTIGATE_MISSING_CYCLE"
        ):
            emit_missing_cycle_event(
                run_date=str(
                    assessment.get(
                        "run_date",
                        "UNKNOWN",
                    )
                ),
                reason=str(
                    assessment.get(
                        "reason"
                    )
                    or
                    "EXPECTED_CYCLE_NOT_OBSERVED"
                ),
            )

        else:
            emit_assessment_event(
                assessment
            )

        result = (
            execute_assessment(
                assessment=assessment,
                gold_function_name=(
                    gold_function_name
                ),
                raw_to_silver_functions=(
                    raw_to_silver_functions
                ),
                bucket=bucket,
            )
        )

        results.append(
            result
        )

        emit_execution_result_event(
            result
        )

    dispatched = [
        result
        for result in results
        if result[
            "status"
        ] == "DISPATCHED"
    ]

    waiting = [
        result
        for result in results
        if result[
            "status"
        ] == "WAITING"
    ]

    blocked = [
        result
        for result in results
        if result[
            "status"
        ] == "BLOCKED"
    ]

    skipped = [
        result
        for result in results
        if result[
            "status"
        ] == "SKIPPED"
    ]

    if blocked:
        overall_status = (
            "EXECUTED_WITH_BLOCKS"
        )

    elif waiting:
        overall_status = (
            "EXECUTED_WITH_WAITING"
        )

    else:
        overall_status = "EXECUTED"

    execution_result = {
        "status": (
            overall_status
        ),
        "total_results": len(
            results
        ),
        "dispatched": len(
            dispatched
        ),
        "waiting": len(
            waiting
        ),
        "blocked": len(
            blocked
        ),
        "skipped": len(
            skipped
        ),
        "results": results,
    }

    emit_recovery_summary_event(
        execution_result
    )

    return execution_result