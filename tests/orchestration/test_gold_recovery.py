from __future__ import annotations

from datetime import date

import pytest

from src.orchestration import gold_recovery


RUN_DATE = date(
    2026,
    9,
    22,
)

BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)


def build_markers() -> dict:
    return {
        "b3": {
            "status": "SUCCESS",
            "run_date": "2026-09-22",
            "reference_date": "2026-09-21",
            "silver_key": (
                "silver/b3/"
                "year=2026/month=09/day=21/"
                "b3_trades.parquet"
            ),
            "records": 44201,
        },
        "cvm": {
            "status": "SUCCESS",
            "run_date": "2026-09-22",
            "reference_date": "2026-09-22",
            "silver_key": (
                "silver/cvm/"
                "year=2026/month=09/day=22/"
                "cvm_fund_classes.parquet"
            ),
            "records": 36722,
        },
        "b3_instruments": {
            "status": "SUCCESS",
            "run_date": "2026-09-22",
            "reference_date": "2026-09-22",
            "silver_key": (
                "silver/b3-instruments/"
                "year=2026/month=09/day=22/"
                "b3_instruments.parquet"
            ),
            "records": 152724,
        },
    }


def test_build_gold_key() -> None:
    result = gold_recovery.build_gold_key(
        RUN_DATE
    )

    assert result == (
        "gold/fii-master/"
        "year=2026/"
        "month=09/"
        "day=22/"
        "fii_master.parquet"
    )


def test_assess_run_date_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: True,
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result == {
        "status": "COMPLETE",
        "run_date": "2026-09-22",
        "gold_key": (
            "gold/fii-master/"
            "year=2026/"
            "month=09/"
            "day=22/"
            "fii_master.parquet"
        ),
    }


def test_assess_run_date_requires_silver_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "load_required_markers",
        lambda **kwargs: None,
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "SILVER_RECOVERY_REQUIRED"
    )

    assert result["run_date"] == (
        "2026-09-22"
    )


def test_assess_run_date_gold_retry_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markers = build_markers()

    object_calls = []

    def fake_object_exists(
        *,
        bucket: str,
        key: str,
    ) -> bool:
        object_calls.append(
            (
                bucket,
                key,
            )
        )

        if key.startswith(
            "gold/fii-master/"
        ):
            return False

        return True

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        fake_object_exists,
    )

    monkeypatch.setattr(
        gold_recovery,
        "load_required_markers",
        lambda **kwargs: markers,
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "GOLD_RETRY_REQUIRED"
    )

    assert result["silver_objects"] == {
        "b3": True,
        "cvm": True,
        "b3_instruments": True,
    }

    assert result["gold_payload"] == {
        "run_date": "2026-09-22",
        "inputs": {
            "b3_trades": {
                "reference_date": (
                    "2026-09-21"
                ),
                "key": (
                    "silver/b3/"
                    "year=2026/"
                    "month=09/"
                    "day=21/"
                    "b3_trades.parquet"
                ),
            },
            "cvm": {
                "reference_date": (
                    "2026-09-22"
                ),
                "key": (
                    "silver/cvm/"
                    "year=2026/"
                    "month=09/"
                    "day=22/"
                    "cvm_fund_classes.parquet"
                ),
            },
            "b3_instruments": {
                "reference_date": (
                    "2026-09-22"
                ),
                "key": (
                    "silver/"
                    "b3-instruments/"
                    "year=2026/"
                    "month=09/"
                    "day=22/"
                    "b3_instruments.parquet"
                ),
            },
        },
    }

    assert len(
        object_calls
    ) == 4


def test_assess_run_date_detects_missing_silver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markers = build_markers()

    def fake_object_exists(
        *,
        bucket: str,
        key: str,
    ) -> bool:
        if key.startswith(
            "gold/fii-master/"
        ):
            return False

        if key.startswith(
            "silver/cvm/"
        ):
            return False

        return True

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        fake_object_exists,
    )

    monkeypatch.setattr(
        gold_recovery,
        "load_required_markers",
        lambda **kwargs: markers,
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "SILVER_OBJECT_MISSING"
    )

    assert result["missing_sources"] == [
        "cvm"
    ]

    assert result["silver_objects"] == {
        "b3": True,
        "cvm": False,
        "b3_instruments": True,
    }


def test_validate_marker_silver_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markers = build_markers()

    existing_keys = {
        markers["b3"]["silver_key"],
        markers["b3_instruments"][
            "silver_key"
        ],
    }

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda *, bucket, key: (
            key in existing_keys
        ),
    )

    result = (
        gold_recovery
        .validate_marker_silver_objects(
            bucket=BUCKET,
            markers=markers,
        )
    )

    assert result == {
        "b3": True,
        "cvm": False,
        "b3_instruments": True,
    }


def test_marker_validation_is_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markers = build_markers()

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "load_required_markers",
        lambda **kwargs: markers,
    )

    def raise_invalid_run_date(
        **kwargs,
    ) -> None:
        raise ValueError(
            "invalid marker run date"
        )

    monkeypatch.setattr(
        gold_recovery,
        "validate_marker_run_dates",
        raise_invalid_run_date,
    )

    with pytest.raises(
        ValueError,
        match="invalid marker run date",
    ):
        gold_recovery.assess_run_date(
            bucket=BUCKET,
            run_date=RUN_DATE,
        )