from __future__ import annotations

import pytest

import src.pipelines.phase5_daily_serving as pipeline


def test_run_phase5_daily_serving(
    monkeypatch,
) -> None:
    calls = []

    monkeypatch.setattr(
        pipeline,
        "run_daily_consumption",
        lambda force=False: (
            calls.append(
                (
                    "daily",
                    force,
                )
            )
        ),
    )

    monkeypatch.setattr(
        pipeline,
        "run_ml_inference_serving",
        lambda force=False: (
            calls.append(
                (
                    "ml",
                    force,
                )
            )
        ),
    )

    monkeypatch.setattr(
        pipeline,
        "run_ai_structured_retrieval",
        lambda force=False: (
            calls.append(
                (
                    "ai",
                    force,
                )
            )
        ),
    )

    monkeypatch.setattr(
        pipeline,
        "get_product_status",
        lambda: {
            "status": "READY",
            "business_date": (
                "2026-08-28"
            ),
            "ticker_count": 267,
        },
    )

    result = (
        pipeline.run_phase5_daily_serving(
            force=True
        )
    )

    assert calls == [
        (
            "daily",
            True,
        ),
        (
            "ml",
            True,
        ),
        (
            "ai",
            True,
        ),
    ]

    assert result[
        "status"
    ] == "READY"

    assert result[
        "business_date"
    ] == "2026-08-28"


def test_chain_stops_when_daily_fails(
    monkeypatch,
) -> None:
    calls = []

    def fail_daily(
        force=False,
    ):
        calls.append(
            "daily"
        )

        raise RuntimeError(
            "daily failed"
        )

    monkeypatch.setattr(
        pipeline,
        "run_daily_consumption",
        fail_daily,
    )

    monkeypatch.setattr(
        pipeline,
        "run_ml_inference_serving",
        lambda force=False: (
            calls.append(
                "ml"
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="daily failed",
    ):
        pipeline.run_phase5_daily_serving()

    assert calls == [
        "daily"
    ]


def test_chain_stops_when_ml_fails(
    monkeypatch,
) -> None:
    calls = []

    monkeypatch.setattr(
        pipeline,
        "run_daily_consumption",
        lambda force=False: (
            calls.append(
                "daily"
            )
        ),
    )

    def fail_ml(
        force=False,
    ):
        calls.append(
            "ml"
        )

        raise RuntimeError(
            "ml failed"
        )

    monkeypatch.setattr(
        pipeline,
        "run_ml_inference_serving",
        fail_ml,
    )

    monkeypatch.setattr(
        pipeline,
        "run_ai_structured_retrieval",
        lambda force=False: (
            calls.append(
                "ai"
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="ml failed",
    ):
        pipeline.run_phase5_daily_serving()

    assert calls == [
        "daily",
        "ml",
    ]


def test_chain_stops_when_ai_fails(
    monkeypatch,
) -> None:
    calls = []

    monkeypatch.setattr(
        pipeline,
        "run_daily_consumption",
        lambda force=False: (
            calls.append(
                "daily"
            )
        ),
    )

    monkeypatch.setattr(
        pipeline,
        "run_ml_inference_serving",
        lambda force=False: (
            calls.append(
                "ml"
            )
        ),
    )

    def fail_ai(
        force=False,
    ):
        calls.append(
            "ai"
        )

        raise RuntimeError(
            "ai failed"
        )

    monkeypatch.setattr(
        pipeline,
        "run_ai_structured_retrieval",
        fail_ai,
    )

    with pytest.raises(
        RuntimeError,
        match="ai failed",
    ):
        pipeline.run_phase5_daily_serving()

    assert calls == [
        "daily",
        "ml",
        "ai",
    ]


def test_product_must_be_ready(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_daily_consumption",
        lambda force=False: None,
    )

    monkeypatch.setattr(
        pipeline,
        "run_ml_inference_serving",
        lambda force=False: None,
    )

    monkeypatch.setattr(
        pipeline,
        "run_ai_structured_retrieval",
        lambda force=False: None,
    )

    monkeypatch.setattr(
        pipeline,
        "get_product_status",
        lambda: {
            "status": "NOT_READY",
            "business_date": (
                "2026-08-28"
            ),
            "ticker_count": 267,
        },
    )

    with pytest.raises(
        RuntimeError,
        match="not READY",
    ):
        pipeline.run_phase5_daily_serving()