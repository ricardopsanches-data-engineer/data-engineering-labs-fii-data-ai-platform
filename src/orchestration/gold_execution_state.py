from __future__ import annotations

import json

from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError


CONTROL_PREFIX = (
    "control/gold-execution"
)

VALID_STATUSES = {
    "STARTED",
    "SUCCEEDED",
    "FAILED",
}


def build_state_key(
    *,
    run_date: str,
) -> str:
    """
    Constrói a chave do estado de execução
    da Gold para um run_date.

    Exemplo:

    control/gold-execution/
    run_date=2026-09-22/
    state.json
    """

    normalized_run_date = (
        str(
            run_date
        )
        .strip()
    )

    if not normalized_run_date:
        raise ValueError(
            "run_date is required."
        )

    return (
        f"{CONTROL_PREFIX}/"
        f"run_date="
        f"{normalized_run_date}/"
        "state.json"
    )


def utc_now_iso() -> str:
    """
    Retorna timestamp UTC em ISO-8601.

    Mantido em função separada para
    facilitar testes determinísticos.
    """

    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


def read_execution_state(
    *,
    bucket: str,
    run_date: str,
) -> dict[str, Any] | None:
    """
    Lê o estado atual da execução Gold.

    Retorna None quando o state.json
    ainda não existe.

    Outros erros AWS são propagados.
    """

    state_key = build_state_key(
        run_date=run_date,
    )

    s3 = boto3.client(
        "s3"
    )

    try:
        response = s3.get_object(
            Bucket=bucket,
            Key=state_key,
        )

    except ClientError as error:
        error_code = (
            error.response
            .get(
                "Error",
                {},
            )
            .get(
                "Code"
            )
        )

        if error_code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            return None

        raise

    body = response[
        "Body"
    ].read()

    if isinstance(
        body,
        bytes,
    ):
        body = body.decode(
            "utf-8"
        )

    payload = json.loads(
        body
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Gold execution state "
            "must be a JSON object."
        )

    return payload


def write_execution_state(
    *,
    bucket: str,
    run_date: str,
    status: str,
    trigger: str,
    details: (
        dict[str, Any]
        | None
    ) = None,
) -> dict[str, Any]:
    """
    Persiste o estado atual da Gold.

    Status válidos:

    STARTED
    SUCCEEDED
    FAILED

    O estado anterior é lido e seus
    timestamps relevantes são preservados
    quando aplicável.
    """

    normalized_status = (
        str(
            status
        )
        .strip()
        .upper()
    )

    if normalized_status not in (
        VALID_STATUSES
    ):
        raise ValueError(
            "Invalid Gold execution "
            "status | "
            f"status={status}"
        )

    normalized_trigger = (
        str(
            trigger
        )
        .strip()
        .upper()
    )

    if not normalized_trigger:
        raise ValueError(
            "trigger is required."
        )

    state_key = build_state_key(
        run_date=run_date,
    )

    previous_state = (
        read_execution_state(
            bucket=bucket,
            run_date=run_date,
        )
    )

    now = utc_now_iso()

    payload: dict[
        str,
        Any,
    ] = {
        "run_date": (
            str(
                run_date
            )
        ),
        "status": (
            normalized_status
        ),
        "trigger": (
            normalized_trigger
        ),
        "updated_at": now,
    }

    if previous_state:
        previous_started_at = (
            previous_state.get(
                "started_at"
            )
        )

        if previous_started_at:
            payload[
                "started_at"
            ] = (
                previous_started_at
            )

    if normalized_status == (
        "STARTED"
    ):
        payload[
            "started_at"
        ] = now

        payload[
            "completed_at"
        ] = None

    elif normalized_status in {
        "SUCCEEDED",
        "FAILED",
    }:
        if (
            "started_at"
            not in payload
        ):
            payload[
                "started_at"
            ] = (
                previous_state.get(
                    "updated_at"
                )
                if previous_state
                else now
            )

        payload[
            "completed_at"
        ] = now

    if details:
        payload[
            "details"
        ] = details

    s3 = boto3.client(
        "s3"
    )

    s3.put_object(
        Bucket=bucket,
        Key=state_key,
        Body=json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode(
            "utf-8"
        ),
        ContentType=(
            "application/json"
        ),
    )

    return {
        "state_key": (
            state_key
        ),
        "state_uri": (
            f"s3://{bucket}/"
            f"{state_key}"
        ),
        "payload": payload,
    }


def mark_execution_started(
    *,
    bucket: str,
    run_date: str,
    trigger: str,
    details: (
        dict[str, Any]
        | None
    ) = None,
) -> dict[str, Any]:
    """
    Marca início de execução da Gold.
    """

    return write_execution_state(
        bucket=bucket,
        run_date=run_date,
        status="STARTED",
        trigger=trigger,
        details=details,
    )


def mark_execution_succeeded(
    *,
    bucket: str,
    run_date: str,
    trigger: str,
    gold_key: str,
    details: (
        dict[str, Any]
        | None
    ) = None,
) -> dict[str, Any]:
    """
    Marca conclusão bem-sucedida da Gold.
    """

    merged_details = {
        "gold_key": gold_key,
    }

    if details:
        merged_details.update(
            details
        )

    return write_execution_state(
        bucket=bucket,
        run_date=run_date,
        status="SUCCEEDED",
        trigger=trigger,
        details=(
            merged_details
        ),
    )


def mark_execution_failed(
    *,
    bucket: str,
    run_date: str,
    trigger: str,
    error_type: str,
    error_message: str,
    details: (
        dict[str, Any]
        | None
    ) = None,
) -> dict[str, Any]:
    """
    Marca falha da execução Gold.

    Mantém informações resumidas do erro
    para observabilidade e recovery.
    """

    failure_details = {
        "error_type": (
            str(
                error_type
            )
        ),
        "error_message": (
            str(
                error_message
            )
        ),
    }

    if details:
        failure_details.update(
            details
        )

    return write_execution_state(
        bucket=bucket,
        run_date=run_date,
        status="FAILED",
        trigger=trigger,
        details=(
            failure_details
        ),
    )


def execution_succeeded(
    *,
    bucket: str,
    run_date: str,
) -> bool:
    """
    Retorna True somente quando existe
    estado SUCCEEDED para o run_date.
    """

    state = (
        read_execution_state(
            bucket=bucket,
            run_date=run_date,
        )
    )

    if not state:
        return False

    return (
        state.get(
            "status"
        )
        == "SUCCEEDED"
    )


def execution_failed(
    *,
    bucket: str,
    run_date: str,
) -> bool:
    """
    Retorna True somente quando existe
    estado FAILED para o run_date.
    """

    state = (
        read_execution_state(
            bucket=bucket,
            run_date=run_date,
        )
    )

    if not state:
        return False

    return (
        state.get(
            "status"
        )
        == "FAILED"
    )


def execution_in_progress(
    *,
    bucket: str,
    run_date: str,
) -> bool:
    """
    Retorna True somente quando existe
    estado STARTED para o run_date.

    Este helper ainda não decide se o
    STARTED está stale.

    A detecção de timeout/stale será
    responsabilidade da camada de
    observabilidade/recovery.
    """

    state = (
        read_execution_state(
            bucket=bucket,
            run_date=run_date,
        )
    )

    if not state:
        return False

    return (
        state.get(
            "status"
        )
        == "STARTED"
    )