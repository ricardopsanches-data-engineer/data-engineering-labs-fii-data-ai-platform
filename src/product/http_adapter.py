from __future__ import annotations

import json
from typing import Any

from src.product.service import (
    get_fii_context,
    get_product_status,
)


def json_response(
    status_code: int,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Build an API Gateway-compatible
    HTTP response.
    """

    return {
        "statusCode": status_code,
        "headers": {
            "content-type": (
                "application/json; charset=utf-8"
            ),
        },
        "body": json.dumps(
            body,
            ensure_ascii=False,
        ),
    }


def handle_health() -> dict[str, Any]:
    """
    Product health endpoint.
    """

    try:
        status = get_product_status()

        return json_response(
            status_code=200,
            body=status,
        )

    except Exception as exc:
        return json_response(
            status_code=503,
            body={
                "status": "NOT_READY",
                "error": str(exc),
            },
        )


def handle_fii(
    ticker: str,
) -> dict[str, Any]:
    """
    Exact ticker product endpoint.
    """

    try:
        result = get_fii_context(
            ticker=ticker,
        )

        return json_response(
            status_code=200,
            body=result,
        )

    except KeyError:
        return json_response(
            status_code=404,
            body={
                "status": "NOT_FOUND",
                "ticker": ticker.upper(),
            },
        )

    except Exception as exc:
        return json_response(
            status_code=503,
            body={
                "status": "NOT_READY",
                "error": str(exc),
            },
        )


def handler(
    event: dict[str, Any],
    context: Any = None,
) -> dict[str, Any]:
    """
    Lambda-compatible HTTP adapter.

    Supports API Gateway HTTP API v2-like
    request events.
    """

    del context

    request_context = event.get(
        "requestContext",
        {}
    )

    http = request_context.get(
        "http",
        {}
    )

    method = str(
        http.get(
            "method",
            event.get(
                "httpMethod",
                "GET",
            ),
        )
    ).upper()

    raw_path = str(
        event.get(
            "rawPath",
            event.get(
                "path",
                "/",
            ),
        )
    )

    if (
        method == "GET"
        and raw_path == "/health"
    ):
        return handle_health()

    if (
        method == "GET"
        and raw_path.startswith(
            "/fii/"
        )
    ):
        ticker = raw_path.removeprefix(
            "/fii/"
        ).strip()

        if not ticker:
            return json_response(
                status_code=400,
                body={
                    "status": "BAD_REQUEST",
                    "error": (
                        "Ticker is required."
                    ),
                },
            )

        return handle_fii(
            ticker=ticker,
        )

    return json_response(
        status_code=404,
        body={
            "status": "NOT_FOUND",
            "path": raw_path,
        },
    )