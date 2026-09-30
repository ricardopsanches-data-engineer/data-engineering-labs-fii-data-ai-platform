from __future__ import annotations

import json

from datetime import UTC, date, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError


CONTROL_PREFIX = "control/gold-recovery-watchdog"

VALID_STATUSES = {
    "OPEN",
    "CLOSED_SUCCESS",
    "FINAL_RECOVERY_DISPATCHED",
    "CLOSED_FAILED",
}

CLOSED_STATUSES = {
    "CLOSED_SUCCESS",
    "CLOSED_FAILED",
}


def normalize_watchdog_date(
    value: date | str,
) -> str:
    """
    Normaliza a data operacional do watchdog
    para YYYY-MM-DD.
    """

    if isinstance(
        value,
        date,
    ):
        return value.isoformat()

    if isinstance(
        value,
        str,
    ):
        try:
            return date.fromisoformat(
                value
            ).isoformat()

        except ValueError as exc:
            raise ValueError(
                "Invalid watchdog date | "
                f"value={value}"
            ) from exc

    raise TypeError(
        "watchdog_date must be date or ISO string | "
        f"type={type(value).__name__}"
    )


def build_watchdog_state_key(
    *,
    watchdog_date: date | str,
) -> str:
    """
    Constrói a chave S3 do estado diário.

    Exemplo:

    control/gold-recovery-watchdog/
      watchdog_date=2026-09-25/
        state.json
    """

    normalized_date = (
        normalize_watchdog_date(
            watchdog_date
        )
    )

    return (
        f"{CONTROL_PREFIX}/"
        f"watchdog_date={normalized_date}/"
        "state.json"
    )


def utc_now_iso() -> str:
    """
    Timestamp UTC em ISO-8601.
    """

    return datetime.now(
        UTC
    ).isoformat()


def validate_status(
    status: str,
) -> str:
    """
    Valida status suportado pelo watchdog.
    """

    normalized_status = str(
        status
    ).strip().upper()

    if (
        normalized_status
        not in VALID_STATUSES
    ):
        raise ValueError(
            "Invalid watchdog status | "
            f"status={status} | "
            "valid="
            f"{sorted(VALID_STATUSES)}"
        )

    return normalized_status


def read_watchdog_state(
    *,
    bucket: str,
    watchdog_date: date | str,
) -> dict[str, Any] | None:
    """
    Lê o estado diário do watchdog.

    Retorna None quando o estado ainda
    não existe para a data.
    """

    state_key = (
        build_watchdog_state_key(
            watchdog_date=watchdog_date
        )
    )

    s3_client = boto3.client(
        "s3"
    )

    try:
        response = (
            s3_client.get_object(
                Bucket=bucket,
                Key=state_key,
            )
        )

    except ClientError as exc:
        error_code = (
            exc.response
            .get(
                "Error",
                {},
            )
            .get(
                "Code"
            )
        )

        if error_code in {
            "NoSuchKey",
            "404",
        }:
            return None

        raise

    body = response[
        "Body"
    ].read()

    if not body:
        raise RuntimeError(
            "Watchdog state object is empty | "
            f"s3://{bucket}/{state_key}"
        )

    try:
        payload = json.loads(
            body.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            "Invalid watchdog state JSON | "
            f"s3://{bucket}/{state_key}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "Watchdog state must be a JSON object | "
            f"s3://{bucket}/{state_key}"
        )

    status = payload.get(
        "status"
    )

    if status is None:
        raise RuntimeError(
            "Watchdog state missing status | "
            f"s3://{bucket}/{state_key}"
        )

    validate_status(
        str(status)
    )

    return payload


def write_watchdog_state(
    *,
    bucket: str,
    watchdog_date: date | str,
    status: str,
    attempt: int,
    max_attempts: int,
    final_attempt: bool,
    check_hour: int,
    outcome: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Persiste o estado atual do watchdog.

    O arquivo representa o estado da janela
    diária de autorreparo, não o estado da Gold.
    """

    if attempt < 1:
        raise ValueError(
            "attempt must be greater than zero."
        )

    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be greater than zero."
        )

    if attempt > max_attempts:
        raise ValueError(
            "attempt cannot be greater than "
            "max_attempts."
        )

    if (
        check_hour < 0
        or check_hour > 23
    ):
        raise ValueError(
            "check_hour must be between "
            "0 and 23."
        )

    normalized_date = (
        normalize_watchdog_date(
            watchdog_date
        )
    )

    normalized_status = (
        validate_status(
            status
        )
    )

    normalized_outcome = str(
        outcome
    ).strip().upper()

    if not normalized_outcome:
        raise ValueError(
            "outcome is required."
        )

    state_key = (
        build_watchdog_state_key(
            watchdog_date=normalized_date
        )
    )

    payload: dict[str, Any] = {
        "watchdog_date": (
            normalized_date
        ),
        "status": (
            normalized_status
        ),
        "attempt": attempt,
        "max_attempts": (
            max_attempts
        ),
        "final_attempt": bool(
            final_attempt
        ),
        "check_hour": (
            check_hour
        ),
        "outcome": (
            normalized_outcome
        ),
        "updated_at": (
            utc_now_iso()
        ),
    }

    if details:
        payload[
            "details"
        ] = details

    s3_client = boto3.client(
        "s3"
    )

    serialized_payload = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        .encode(
            "utf-8"
        )
    )

    s3_client.put_object(
        Bucket=bucket,
        Key=state_key,
        Body=serialized_payload,
        ContentType=(
            "application/json"
        ),
    )

    return {
        "state_key": state_key,
        "state_uri": (
            f"s3://{bucket}/"
            f"{state_key}"
        ),
        "payload": payload,
    }


def watchdog_day_is_closed(
    state: dict[str, Any] | None,
) -> bool:
    """
    Retorna True somente quando a janela
    diária já foi encerrada definitivamente.
    """

    if not state:
        return False

    return (
        state.get(
            "status"
        )
        in CLOSED_STATUSES
    )


def watchdog_day_succeeded(
    state: dict[str, Any] | None,
) -> bool:
    """
    Retorna True quando o watchdog já encerrou
    o dia com sucesso.
    """

    if not state:
        return False

    return (
        state.get(
            "status"
        )
        == "CLOSED_SUCCESS"
    )


def watchdog_day_failed(
    state: dict[str, Any] | None,
) -> bool:
    """
    Retorna True quando o watchdog já encerrou
    o dia após esgotar recovery e verificação.
    """

    if not state:
        return False

    return (
        state.get(
            "status"
        )
        == "CLOSED_FAILED"
    )