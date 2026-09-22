from __future__ import annotations

import json

from typing import Any

import boto3


SUPPORTED_ACTIONS = {
    "NO_ACTION",
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

    Retorna somente confirmação de aceite
    pela API do Lambda.

    Importante:
    StatusCode=202 NÃO significa que a
    execução terminou com sucesso.
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


def execute_gold_retry(
    *,
    assessment: dict[str, Any],
    gold_function_name: str,
) -> dict[str, Any]:
    """
    Executa recovery de Gold diretamente.

    Não passa pelo Gold Readiness Coordinator.

    Isso é intencional:
    um dispatch lock antigo pode existir
    mesmo quando a execução assíncrona da
    Gold falhou depois do HTTP 202.

    O recovery usa o payload Gold explícito
    produzido pelo diagnóstico físico.
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

    invocation = (
        invoke_lambda_async(
            function_name=(
                gold_function_name
            ),
            payload=gold_payload,
        )
    )

    return {
        "status": (
            "DISPATCHED"
        ),
        "action": "RETRY_GOLD",
        "run_date": run_date,
        "function_name": (
            gold_function_name
        ),
        "invoke_status_code": (
            invocation[
                "invoke_status_code"
            ]
        ),
        "payload": (
            gold_payload
        ),
    }


def build_raw_to_silver_payload(
    *,
    assessment: dict[str, Any],
    source: str,
) -> dict[str, str]:
    """
    Constrói o payload direto para uma
    Lambda RAW->Silver existente.

    Cada handler atual aceita:

    {
        "bucket": "...",
        "key": "raw/..."
    }

    O bucket precisa estar presente no
    assessment durante a execução do
    plano ou ser injetado externamente.
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
    Dispara as Lambdas RAW->Silver já
    existentes para as fontes que precisam
    reconstrução.

    Não executa transformação diretamente.

    O fluxo normal permanece responsável
    por:
    RAW -> Silver -> readiness marker
    -> coordinator -> Gold.
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
    Executa uma única entrada do
    recovery plan.

    Somente ações explicitamente seguras
    são executadas automaticamente.

    NO_ACTION
        Não faz nada.

    RETRY_GOLD
        Invoca Gold diretamente.

    REBUILD_SILVER_FROM_RAW
        Invoca RAW->Silver existente.

    ALERT_AND_INVESTIGATE
    INVESTIGATE_MISSING_CYCLE
        Não tentam fabricar recuperação.
        Retornam estado bloqueado para
        observabilidade/alerta.
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
            or "MANUAL_INVESTIGATION_REQUIRED"
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
    por gold_recovery.build_recovery_plan().

    Esta função NÃO descobre dados e NÃO
    recalcula o plano.

    Ela executa exatamente o snapshot do
    plano recebido.

    Isso mantém separadas as fases:

        discover
        assess
        plan
        execute
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

    dispatched = [
        result
        for result in results
        if result[
            "status"
        ] == "DISPATCHED"
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

    return {
        "status": (
            "EXECUTED_WITH_BLOCKS"
            if blocked
            else "EXECUTED"
        ),
        "total_results": len(
            results
        ),
        "dispatched": len(
            dispatched
        ),
        "blocked": len(
            blocked
        ),
        "skipped": len(
            skipped
        ),
        "results": results,
    }