from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


OBSERVABILITY_VERSION = "v1"


def utc_now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


def emit_observability_event(
    event: str,
    *,
    pipeline: str,
    status: str = "INFO",
    **details: Any,
) -> None:
    """
    Emits a vendor-neutral structured
    JSON event to stdout.

    stdout can later be collected by
    CloudWatch, OpenTelemetry, Loki,
    Prometheus-related agents, etc.
    """

    payload = {
        "timestamp": utc_now_iso(),
        "observability_version": (
            OBSERVABILITY_VERSION
        ),
        "event": event,
        "pipeline": pipeline,
        "status": status,
        **details,
    }

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            separators=(
                ",",
                ":",
            ),
        )
    )