from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.orchestration.gold_execution_state import (
    read_execution_state,
)


DEFAULT_STALE_AFTER_MINUTES = 15


def parse_iso_datetime(
    value: str,
) -> datetime:
    """
    Converte timestamp ISO-8601 para datetime.

    Aceita timestamps com timezone.

    Exemplo:
    2026-09-22T10:00:00+00:00
    """

    if not value:
        raise ValueError(
            "datetime value is required."
        )

    try:
        parsed = (
            datetime.fromisoformat(
                str(
                    value
                )
            )
        )

    except ValueError as exc:
        raise ValueError(
            "Invalid ISO datetime: "
            f"{value}"
        ) from exc

    if parsed.tzinfo is None:
        raise ValueError(
            "Datetime must include timezone: "
            f"{value}"
        )

    return parsed


def execution_started_at(
    *,
    state: dict[str, Any],
) -> datetime | None:
    """
    Retorna started_at como datetime.

    Retorna None quando o estado não possui
    started_at.
    """

    value = state.get(
        "started_at"
    )

    if not value:
        return None

    return parse_iso_datetime(
        value
    )


def execution_updated_at(
    *,
    state: dict[str, Any],
) -> datetime | None:
    """
    Retorna updated_at como datetime.

    Retorna None quando o estado não possui
    updated_at.
    """

    value = state.get(
        "updated_at"
    )

    if not value:
        return None

    return parse_iso_datetime(
        value
    )


def execution_reference_time(
    *,
    state: dict[str, Any],
) -> datetime | None:
    """
    Define o timestamp principal usado
    para avaliar stale.

    Prioridade:

    1. started_at
    2. updated_at
    """

    started_at = (
        execution_started_at(
            state=state
        )
    )

    if started_at is not None:
        return started_at

    return execution_updated_at(
        state=state
    )


def is_execution_stale(
    *,
    state: dict[str, Any],
    now: datetime,
    stale_after_minutes: int,
) -> bool:
    """
    Verifica se uma execução STARTED já pode
    ser considerada stale.

    A decisão é configurável por
    stale_after_minutes.

    Não existe valor de timeout escondido
    nesta função.
    """

    if stale_after_minutes < 1:
        raise ValueError(
            "stale_after_minutes "
            "must be >= 1."
        )

    if now.tzinfo is None:
        raise ValueError(
            "now must include timezone."
        )

    status = (
        str(
            state.get(
                "status",
                "",
            )
        )
        .strip()
        .upper()
    )

    if status != "STARTED":
        return False

    reference_time = (
        execution_reference_time(
            state=state
        )
    )

    if reference_time is None:
        return True

    stale_threshold = (
        reference_time
        + timedelta(
            minutes=(
                stale_after_minutes
            )
        )
    )

    return (
        now
        >= stale_threshold
    )


def classify_gold_execution_state(
    *,
    gold_exists: bool,
    state: dict[str, Any] | None,
    now: datetime,
    stale_after_minutes: int,
) -> dict[str, Any]:
    """
    Interpreta o estado operacional da Gold.

    Esta função NÃO acessa AWS.

    Ela combina:

    - existência física da Gold;
    - estado de execução persistido;
    - stale timeout configurável.

    Resultado possível:

    COMPLETE
        Gold física existe.

    NO_STATE
        Gold ausente e não existe estado.

    IN_PROGRESS
        Gold ausente e execução STARTED
        ainda não está stale.

    RETRY_ALLOWED
        Gold ausente e:
        - estado FAILED; ou
        - STARTED stale.

    INCONSISTENT_STATE
        Estado SUCCEEDED existe,
        mas objeto Gold não existe.

    UNKNOWN_STATE
        Estado persistido possui status
        desconhecido.
    """

    if stale_after_minutes < 1:
        raise ValueError(
            "stale_after_minutes "
            "must be >= 1."
        )

    if now.tzinfo is None:
        raise ValueError(
            "now must include timezone."
        )

    if gold_exists:
        return {
            "status": "COMPLETE",
            "reason": (
                "GOLD_OBJECT_EXISTS"
            ),
            "retry_allowed": False,
        }

    if not state:
        return {
            "status": "NO_STATE",
            "reason": (
                "GOLD_OBJECT_MISSING_"
                "AND_NO_EXECUTION_STATE"
            ),
            "retry_allowed": False,
        }

    execution_status = (
        str(
            state.get(
                "status",
                "",
            )
        )
        .strip()
        .upper()
    )

    if execution_status == (
        "FAILED"
    ):
        return {
            "status": "RETRY_ALLOWED",
            "reason": (
                "PREVIOUS_EXECUTION_FAILED"
            ),
            "execution_status": (
                execution_status
            ),
            "retry_allowed": True,
        }

    if execution_status == (
        "SUCCEEDED"
    ):
        return {
            "status": (
                "INCONSISTENT_STATE"
            ),
            "reason": (
                "EXECUTION_SUCCEEDED_"
                "BUT_GOLD_OBJECT_MISSING"
            ),
            "execution_status": (
                execution_status
            ),
            "retry_allowed": False,
        }

    if execution_status == (
        "STARTED"
    ):
        stale = (
            is_execution_stale(
                state=state,
                now=now,
                stale_after_minutes=(
                    stale_after_minutes
                ),
            )
        )

        if stale:
            return {
                "status": (
                    "RETRY_ALLOWED"
                ),
                "reason": (
                    "STARTED_EXECUTION_STALE"
                ),
                "execution_status": (
                    execution_status
                ),
                "retry_allowed": True,
            }

        return {
            "status": (
                "IN_PROGRESS"
            ),
            "reason": (
                "STARTED_EXECUTION_ACTIVE"
            ),
            "execution_status": (
                execution_status
            ),
            "retry_allowed": False,
        }

    return {
        "status": "UNKNOWN_STATE",
        "reason": (
            "UNSUPPORTED_EXECUTION_STATUS"
        ),
        "execution_status": (
            execution_status
        ),
        "retry_allowed": False,
    }


def assess_gold_recovery_state(
    *,
    bucket: str,
    run_date: str,
    gold_exists: bool,
    now: datetime,
    stale_after_minutes: int,
) -> dict[str, Any]:
    """
    Carrega o execution state da Gold e
    devolve sua interpretação operacional.

    Esta é a função de integração entre:

    gold_execution_state.py
        -> leitura física do state.json

    gold_recovery_state.py
        -> decisão operacional

    gold_recovery.py
        -> usa essa decisão no plano
    """

    state = (
        read_execution_state(
            bucket=bucket,
            run_date=run_date,
        )
    )

    classification = (
        classify_gold_execution_state(
            gold_exists=(
                gold_exists
            ),
            state=state,
            now=now,
            stale_after_minutes=(
                stale_after_minutes
            ),
        )
    )

    return {
        "run_date": run_date,
        "gold_exists": (
            gold_exists
        ),
        "execution_state": state,
        "classification": (
            classification
        ),
    }