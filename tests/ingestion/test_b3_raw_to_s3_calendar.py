from datetime import date
from pathlib import Path

import pytest

from src.pipelines import b3_raw_to_s3


def test_ingest_backfill_skips_weekend_and_b3_holiday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Garante que o backfill consulte apenas
    datas em que existe pregão esperado
    segundo o calendário oficial da B3.

    Intervalo:

    2026-10-09 sexta-feira      -> pregão
    2026-10-10 sábado           -> ignorado
    2026-10-11 domingo          -> ignorado
    2026-10-12 feriado B3       -> ignorado
    2026-10-13 terça-feira      -> pregão
    """

    download_calls: list[
        date
    ] = []

    upload_calls: list[
        Path
    ] = []

    fake_session = object()

    monkeypatch.setattr(
        b3_raw_to_s3,
        "create_session",
        lambda: fake_session,
    )

    def fake_download_b3_file(
        *,
        trade_date: date,
        session,
        overwrite: bool = False,
    ) -> Path | None:
        assert session is fake_session
        assert overwrite is False

        download_calls.append(
            trade_date
        )

        return Path(
            f"b3_download_{trade_date:%Y%m%d}.zip"
        )

    monkeypatch.setattr(
        b3_raw_to_s3,
        "download_b3_file",
        fake_download_b3_file,
    )

    def fake_upload_b3_file(
        local_path,
        force: bool = False,
    ) -> None:
        assert force is False

        upload_calls.append(
            Path(local_path)
        )

    monkeypatch.setattr(
        b3_raw_to_s3,
        "upload_b3_file",
        fake_upload_b3_file,
    )

    b3_raw_to_s3.ingest_backfill(
        start_date=date(
            2026,
            10,
            9,
        ),
        end_date=date(
            2026,
            10,
            13,
        ),
    )

    assert download_calls == [
        date(
            2026,
            10,
            9,
        ),
        date(
            2026,
            10,
            13,
        ),
    ]

    assert upload_calls == [
        Path(
            "b3_download_20261009.zip"
        ),
        Path(
            "b3_download_20261013.zip"
        ),
    ]


def test_ingest_backfill_processes_special_b3_trading_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Garante que uma data especial que continua
    sendo pregão B3 não seja descartada pelo
    backfill.

    2026-07-09 é feriado estadual em SP,
    mas permanece como dia de negociação B3
    no calendário controlado do projeto.
    """

    download_calls: list[
        date
    ] = []

    upload_calls: list[
        Path
    ] = []

    fake_session = object()

    monkeypatch.setattr(
        b3_raw_to_s3,
        "create_session",
        lambda: fake_session,
    )

    def fake_download_b3_file(
        *,
        trade_date: date,
        session,
        overwrite: bool = False,
    ) -> Path | None:
        assert session is fake_session
        assert overwrite is False

        download_calls.append(
            trade_date
        )

        return Path(
            f"b3_download_{trade_date:%Y%m%d}.zip"
        )

    monkeypatch.setattr(
        b3_raw_to_s3,
        "download_b3_file",
        fake_download_b3_file,
    )

    def fake_upload_b3_file(
        local_path,
        force: bool = False,
    ) -> None:
        assert force is False

        upload_calls.append(
            Path(local_path)
        )

    monkeypatch.setattr(
        b3_raw_to_s3,
        "upload_b3_file",
        fake_upload_b3_file,
    )

    b3_raw_to_s3.ingest_backfill(
        start_date=date(
            2026,
            7,
            9,
        ),
        end_date=date(
            2026,
            7,
            9,
        ),
    )

    assert download_calls == [
        date(
            2026,
            7,
            9,
        )
    ]

    assert upload_calls == [
        Path(
            "b3_download_20260709.zip"
        )
    ]


def test_ingest_backfill_skips_non_trading_days_before_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Um intervalo composto somente por datas
    sem pregão esperado não deve executar
    nenhum download nem upload.
    """

    download_calls: list[
        date
    ] = []

    upload_calls: list[
        Path
    ] = []

    monkeypatch.setattr(
        b3_raw_to_s3,
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

        pytest.fail(
            "download_b3_file não deveria "
            "ser chamado para datas sem pregão."
        )

    monkeypatch.setattr(
        b3_raw_to_s3,
        "download_b3_file",
        fake_download_b3_file,
    )

    def fake_upload_b3_file(
        local_path,
        force: bool = False,
    ) -> None:
        upload_calls.append(
            Path(local_path)
        )

        pytest.fail(
            "upload_b3_file não deveria "
            "ser chamado sem download válido."
        )

    monkeypatch.setattr(
        b3_raw_to_s3,
        "upload_b3_file",
        fake_upload_b3_file,
    )

    b3_raw_to_s3.ingest_backfill(
        start_date=date(
            2026,
            10,
            10,
        ),
        end_date=date(
            2026,
            10,
            12,
        ),
    )

    assert download_calls == []
    assert upload_calls == []