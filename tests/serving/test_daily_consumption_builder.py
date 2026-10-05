from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import src.serving.daily_consumption.builder as daily_builder


def build_snapshot_dataframe(
    trade_date: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                [
                    trade_date,
                    trade_date,
                ]
            ),
            "ticker": [
                "HGLG11",
                "KNRI11",
            ],
            "cnpj": [
                "11111111000111",
                "22222222000122",
            ],
            "codigo_cvm": [
                "1001",
                "1002",
            ],
            "denominacao_social": [
                "FII TESTE 1",
                "FII TESTE 2",
            ],
            "close_price": [
                100.0,
                150.0,
            ],
        }
    )


def write_snapshot(
    base_directory: Path,
    trade_date: str,
) -> Path:
    timestamp = pd.Timestamp(
        trade_date
    )

    destination = (
        base_directory
        / f"year={timestamp.year}"
        / f"month={timestamp.month:02d}"
        / f"day={timestamp.day:02d}"
        / "fii_daily_snapshot.parquet"
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = build_snapshot_dataframe(
        trade_date
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )

    return destination


def test_find_latest_snapshot_uses_partition_date(
    tmp_path: Path,
) -> None:
    older = write_snapshot(
        tmp_path,
        "2026-08-27",
    )

    latest = write_snapshot(
        tmp_path,
        "2026-08-28",
    )

    result = daily_builder.find_latest_snapshot(
        tmp_path
    )

    assert result == latest
    assert result != older


def test_validate_snapshot_accepts_valid_dataset(
    tmp_path: Path,
) -> None:
    snapshot_path = write_snapshot(
        tmp_path,
        "2026-08-28",
    )

    dataframe = pd.read_parquet(
        snapshot_path
    )

    trade_date = daily_builder.validate_snapshot(
        dataframe=dataframe,
        path=snapshot_path,
    )

    assert trade_date == pd.Timestamp(
        "2026-08-28"
    )


def test_validate_snapshot_rejects_partition_mismatch(
    tmp_path: Path,
) -> None:
    snapshot_path = (
        tmp_path
        / "year=2026"
        / "month=08"
        / "day=28"
        / "fii_daily_snapshot.parquet"
    )

    snapshot_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = build_snapshot_dataframe(
        "2026-08-27"
    )

    dataframe.to_parquet(
        snapshot_path,
        index=False,
    )

    with pytest.raises(
        ValueError,
        match="Partição física não corresponde",
    ):
        daily_builder.validate_snapshot(
            dataframe=dataframe,
            path=snapshot_path,
        )


def test_validate_snapshot_rejects_duplicates(
    tmp_path: Path,
) -> None:
    snapshot_path = write_snapshot(
        tmp_path,
        "2026-08-28",
    )

    dataframe = pd.read_parquet(
        snapshot_path
    )

    dataframe = pd.concat(
        [
            dataframe,
            dataframe.iloc[[0]],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicidade",
    ):
        daily_builder.validate_snapshot(
            dataframe=dataframe,
            path=snapshot_path,
        )


def test_build_daily_consumption_layer_creates_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = (
        tmp_path
        / "project"
    )

    gold_directory = (
        project_root
        / "data"
        / "gold"
        / "analytics"
        / "fii_daily_snapshot"
    )

    write_snapshot(
        gold_directory,
        "2026-08-27",
    )

    write_snapshot(
        gold_directory,
        "2026-08-28",
    )

    destination = (
        project_root
        / "data"
        / "serving"
        / "daily"
        / "latest_snapshot.json"
    )

    monkeypatch.setattr(
        daily_builder,
        "PROJECT_ROOT",
        project_root,
    )

    manifest = (
        daily_builder.build_daily_consumption_layer(
            gold_base_directory=gold_directory,
            destination=destination,
        )
    )

    assert destination.exists()

    persisted_manifest = json.loads(
        destination.read_text(
            encoding="utf-8"
        )
    )

    assert manifest["dataset"] == (
        "fii_daily_snapshot"
    )
    assert manifest["status"] == "READY"
    assert manifest["trade_date"] == (
        "2026-08-28"
    )
    assert manifest["row_count"] == 2
    assert manifest["ticker_count"] == 2

    assert manifest["s3_key"] == (
        "gold/analytics/fii_daily_snapshot/"
        "year=2026/month=08/day=28/"
        "fii_daily_snapshot.parquet"
    )

    assert persisted_manifest == manifest