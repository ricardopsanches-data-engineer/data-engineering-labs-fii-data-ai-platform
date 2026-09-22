from __future__ import annotations

from datetime import date, datetime, timezone

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


def build_source_states() -> dict:
    return {
        "b3": {
            "source": "b3",
            "silver_objects": [
                {
                    "key": (
                        "silver/b3/"
                        "year=2026/month=09/day=21/"
                        "b3_trades.parquet"
                    ),
                    "last_modified": (
                        "2026-09-22T10:01:13+00:00"
                    ),
                }
            ],
            "raw_objects": [
                {
                    "key": (
                        "raw/b3/"
                        "year=2026/month=09/day=21/"
                        "b3_download_20260921.zip"
                    ),
                    "last_modified": (
                        "2026-09-22T10:00:54+00:00"
                    ),
                }
            ],
        },
        "cvm": {
            "source": "cvm",
            "silver_objects": [
                {
                    "key": (
                        "silver/cvm/"
                        "year=2026/month=09/day=22/"
                        "cvm_fund_classes.parquet"
                    ),
                    "last_modified": (
                        "2026-09-22T10:00:58+00:00"
                    ),
                }
            ],
            "raw_objects": [
                {
                    "key": (
                        "raw/cvm/"
                        "year=2026/month=09/day=22/"
                        "registro_fundo_classe.zip"
                    ),
                    "last_modified": (
                        "2026-09-22T10:00:55+00:00"
                    ),
                }
            ],
        },
        "b3_instruments": {
            "source": "b3_instruments",
            "silver_objects": [
                {
                    "key": (
                        "silver/b3-instruments/"
                        "year=2026/month=09/day=22/"
                        "b3_instruments.parquet"
                    ),
                    "last_modified": (
                        "2026-09-22T10:02:07+00:00"
                    ),
                }
            ],
            "raw_objects": [
                {
                    "key": (
                        "raw/b3-instruments/"
                        "year=2026/month=09/day=22/"
                        "pesquisa-pregao.zip"
                    ),
                    "last_modified": (
                        "2026-09-22T10:00:56+00:00"
                    ),
                }
            ],
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


def test_object_matches_run_date() -> None:
    last_modified = datetime(
        2026,
        9,
        22,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    assert gold_recovery.object_matches_run_date(
        last_modified=last_modified,
        run_date=RUN_DATE,
    )


def test_extract_reference_date_from_silver_key() -> None:
    result = (
        gold_recovery
        .extract_reference_date_from_silver_key(
            source="b3",
            key=(
                "silver/b3/"
                "year=2026/month=09/day=21/"
                "b3_trades.parquet"
            ),
        )
    )

    assert result == date(
        2026,
        9,
        21,
    )


def test_build_gold_payload_from_silver() -> None:
    source_states = build_source_states()

    result = (
        gold_recovery
        .build_gold_payload_from_silver(
            run_date=RUN_DATE,
            source_states=source_states,
        )
    )

    assert result == {
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

    assert result["status"] == "COMPLETE"

    assert result["gold_key"] == (
        "gold/fii-master/"
        "year=2026/"
        "month=09/"
        "day=22/"
        "fii_master.parquet"
    )


def test_assess_run_date_gold_retry_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_states = build_source_states()

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_source_state",
        lambda *, bucket, source, run_date: (
            source_states[source]
        ),
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "GOLD_RETRY_REQUIRED"
    )

    assert result["gold_payload"][
        "run_date"
    ] == "2026-09-22"


def test_assess_run_date_raw_rebuild_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_states = build_source_states()

    source_states["cvm"][
        "silver_objects"
    ] = []

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_source_state",
        lambda *, bucket, source, run_date: (
            source_states[source]
        ),
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "RAW_REBUILD_REQUIRED"
    )

    assert result["rebuild_sources"] == [
        "cvm"
    ]


def test_assess_run_date_blocked_when_raw_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_states = build_source_states()

    source_states["cvm"][
        "silver_objects"
    ] = []

    source_states["cvm"][
        "raw_objects"
    ] = []

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_source_state",
        lambda *, bucket, source, run_date: (
            source_states[source]
        ),
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "RECOVERY_BLOCKED"
    )

    assert result["reason"] == (
        "RAW_UNAVAILABLE"
    )

    assert result[
        "blocked_sources"
    ] == [
        {
            "source": "cvm",
            "raw_count": 0,
            "reason": "RAW_MISSING",
        }
    ]


def test_assess_run_date_blocked_when_silver_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_states = build_source_states()

    source_states["b3"][
        "silver_objects"
    ].append(
        {
            "key": (
                "silver/b3/"
                "year=2026/month=09/day=20/"
                "b3_trades.parquet"
            ),
            "last_modified": (
                "2026-09-22T10:03:00+00:00"
            ),
        }
    )

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_source_state",
        lambda *, bucket, source, run_date: (
            source_states[source]
        ),
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "RECOVERY_BLOCKED"
    )

    assert result["reason"] == (
        "AMBIGUOUS_SILVER"
    )

    assert result["sources"] == [
        "b3"
    ]


def test_assess_run_date_blocked_when_raw_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_states = build_source_states()

    source_states["cvm"][
        "silver_objects"
    ] = []

    source_states["cvm"][
        "raw_objects"
    ].append(
        {
            "key": (
                "raw/cvm/"
                "year=2026/month=09/day=21/"
                "registro_fundo_classe.zip"
            ),
            "last_modified": (
                "2026-09-22T10:04:00+00:00"
            ),
        }
    )

    monkeypatch.setattr(
        gold_recovery,
        "object_exists",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        gold_recovery,
        "discover_source_state",
        lambda *, bucket, source, run_date: (
            source_states[source]
        ),
    )

    result = gold_recovery.assess_run_date(
        bucket=BUCKET,
        run_date=RUN_DATE,
    )

    assert result["status"] == (
        "RECOVERY_BLOCKED"
    )

    assert result["reason"] == (
        "RAW_UNAVAILABLE"
    )

    assert result[
        "blocked_sources"
    ][0][
        "reason"
    ] == "AMBIGUOUS_RAW"