from datetime import date
from pathlib import Path

import pytest

from src.ingestion.b3 import client


def test_download_latest_trading_days_skips_weekend_and_holiday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Garante que WEEKEND e B3_HOLIDAY
    nunca disparem tentativa de download.
    """

    download_calls: list[
        date
    ] = []

    monkeypatch.setattr(
        client,
        "create_session",
        lambda: object(),
    )

    def fake_download_b3_file(
        *,
        trade_date: date,
        session,
        overwrite: bool = False,
    ) -> Path | None:
        download_calls.append(
            trade_date
        )

        return Path(
            f"b3_download_{trade_date:%Y%m%d}.zip"
        )

    monkeypatch.setattr(
        client,
        "download_b3_file",
        fake_download_b3_file,
    )

    result = (
        client.download_latest_trading_days(
            days=1,
            reference_date=date(
                2026,
                10,
                12,
            ),
        )
    )

    assert result == [
        Path(
            "b3_download_20261009.zip"
        )
    ]

    assert download_calls == [
        date(
            2026,
            10,
            9,
        )
    ]


def test_download_latest_trading_days_uses_trading_day_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Uma data de pregão válida pode seguir
    normalmente para o download.
    """

    download_calls: list[
        date
    ] = []

    monkeypatch.setattr(
        client,
        "create_session",
        lambda: object(),
    )

    def fake_download_b3_file(
        *,
        trade_date: date,
        session,
        overwrite: bool = False,
    ) -> Path | None:
        download_calls.append(
            trade_date
        )

        return Path(
            f"b3_download_{trade_date:%Y%m%d}.zip"
        )

    monkeypatch.setattr(
        client,
        "download_b3_file",
        fake_download_b3_file,
    )

    result = (
        client.download_latest_trading_days(
            days=1,
            reference_date=date(
                2026,
                9,
                25,
            ),
        )
    )

    assert result == [
        Path(
            "b3_download_20260925.zip"
        )
    ]

    assert download_calls == [
        date(
            2026,
            9,
            25,
        )
    ]