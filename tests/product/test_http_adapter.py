from __future__ import annotations

import json

import src.product.http_adapter as adapter


def decode_body(
    response: dict,
) -> dict:
    return json.loads(
        response["body"]
    )


def test_json_response() -> None:
    response = adapter.json_response(
        status_code=200,
        body={
            "status": "READY",
        },
    )

    assert response[
        "statusCode"
    ] == 200

    assert (
        response["headers"][
            "content-type"
        ]
        ==
        "application/json; charset=utf-8"
    )

    assert decode_body(
        response
    ) == {
        "status": "READY",
    }


def test_handle_health(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "get_product_status",
        lambda: {
            "status": "READY",
            "business_date": (
                "2026-08-28"
            ),
        },
    )

    response = adapter.handle_health()

    assert response[
        "statusCode"
    ] == 200

    assert decode_body(
        response
    )[
        "status"
    ] == "READY"


def test_handle_health_not_ready(
    monkeypatch,
) -> None:
    def fail():
        raise ValueError(
            "not ready"
        )

    monkeypatch.setattr(
        adapter,
        "get_product_status",
        fail,
    )

    response = adapter.handle_health()

    assert response[
        "statusCode"
    ] == 503

    assert decode_body(
        response
    )[
        "status"
    ] == "NOT_READY"


def test_handle_fii(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "get_fii_context",
        lambda ticker: {
            "status": "READY",
            "data": {
                "ticker": ticker.upper(),
            },
        },
    )

    response = adapter.handle_fii(
        "ggrc11"
    )

    assert response[
        "statusCode"
    ] == 200

    assert decode_body(
        response
    )[
        "data"
    ][
        "ticker"
    ] == "GGRC11"


def test_handle_fii_not_found(
    monkeypatch,
) -> None:
    def fail(ticker):
        raise KeyError(
            ticker
        )

    monkeypatch.setattr(
        adapter,
        "get_fii_context",
        fail,
    )

    response = adapter.handle_fii(
        "INVALID11"
    )

    assert response[
        "statusCode"
    ] == 404

    assert decode_body(
        response
    )[
        "status"
    ] == "NOT_FOUND"


def test_handler_health_route(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "handle_health",
        lambda: {
            "statusCode": 200,
            "body": "{}",
        },
    )

    response = adapter.handler(
        {
            "requestContext": {
                "http": {
                    "method": "GET",
                }
            },
            "rawPath": "/health",
        }
    )

    assert response[
        "statusCode"
    ] == 200


def test_handler_fii_route(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "handle_fii",
        lambda ticker: {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "ticker": ticker,
                }
            ),
        },
    )

    response = adapter.handler(
        {
            "requestContext": {
                "http": {
                    "method": "GET",
                }
            },
            "rawPath": (
                "/fii/GGRC11"
            ),
        }
    )

    assert response[
        "statusCode"
    ] == 200

    assert decode_body(
        response
    )[
        "ticker"
    ] == "GGRC11"


def test_handler_unknown_route() -> None:
    response = adapter.handler(
        {
            "requestContext": {
                "http": {
                    "method": "GET",
                }
            },
            "rawPath": "/unknown",
        }
    )

    assert response[
        "statusCode"
    ] == 404