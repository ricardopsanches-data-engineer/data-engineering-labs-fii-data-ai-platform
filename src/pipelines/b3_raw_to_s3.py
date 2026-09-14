from __future__ import annotations

import argparse
from datetime import date, timedelta

from src.ingestion.b3.client import (
    create_session,
    download_b3_file,
    download_latest_trading_days,
)
from src.storage.s3 import upload_file

BUCKET_NAME = "fii-data-ai-platform-dev-datalake-625685670804"


def ingest_daily(
    force: bool = False,
) -> None:
    """
    Executa a carga diária da B3.

    Procura o pregão válido mais recente,
    grava o RAW localmente e envia ao S3.
    """

    print("======================================")
    print("B3 RAW -> S3 | DAILY")
    print("======================================")

    files = download_latest_trading_days(
        days=1,
        overwrite=force,
    )

    for local_path in files:
        upload_file(
            local_path=local_path,
            bucket_name=BUCKET_NAME,
            force=force,
        )


def ingest_single_date(
    trade_date: date,
    force: bool = False,
) -> None:
    """
    Reprocessa uma data específica da B3.
    """

    print("======================================")
    print("B3 RAW -> S3 | SINGLE DATE")
    print("======================================")
    print(f"Data: {trade_date}")
    print(f"Force: {force}")
    print()

    session = create_session()

    local_path = download_b3_file(
        trade_date=trade_date,
        session=session,
        overwrite=force,
    )

    if local_path is None:
        raise RuntimeError(
            "Não foi possível obter um arquivo B3 válido "
            f"para {trade_date}."
        )

    upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        force=force,
    )


def ingest_backfill(
    start_date: date,
    end_date: date,
    force: bool = False,
) -> None:
    """
    Executa backfill da B3 em um intervalo de datas.

    Finais de semana são ignorados.

    Datas sem pregão ou sem arquivo válido
    também são ignoradas sem interromper
    todo o backfill.
    """

    if start_date > end_date:
        raise ValueError(
            "--start-date não pode ser maior que --end-date."
        )

    print("======================================")
    print("B3 RAW -> S3 | BACKFILL")
    print("======================================")
    print(f"Início: {start_date}")
    print(f"Fim:    {end_date}")
    print(f"Force:  {force}")
    print()

    session = create_session()

    current_date = start_date

    processed = 0
    skipped_weekend = 0
    unavailable = 0

    while current_date <= end_date:
        if current_date.weekday() >= 5:
            print(
                f"{current_date} | "
                "fim de semana | ignorado"
            )

            skipped_weekend += 1
            current_date += timedelta(days=1)
            continue

        local_path = download_b3_file(
            trade_date=current_date,
            session=session,
            overwrite=force,
        )

        if local_path is None:
            print(
                f"{current_date} | "
                "sem pregão/arquivo válido | ignorado"
            )

            unavailable += 1
            current_date += timedelta(days=1)
            continue

        upload_file(
            local_path=local_path,
            bucket_name=BUCKET_NAME,
            force=force,
        )

        processed += 1
        current_date += timedelta(days=1)

    print()
    print("======================================")
    print("Resumo do backfill")
    print("======================================")
    print(f"Arquivos processados: {processed}")
    print(
        "Finais de semana ignorados: "
        f"{skipped_weekend}"
    )
    print(
        "Datas sem arquivo válido: "
        f"{unavailable}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline B3 RAW para S3 com suporte "
            "a daily, data específica e backfill."
        )
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--daily",
        action="store_true",
        help=(
            "Executa a ingestão do pregão válido "
            "mais recente."
        ),
    )

    mode.add_argument(
        "--date",
        type=date.fromisoformat,
        help=(
            "Executa uma data específica. "
            "Formato YYYY-MM-DD."
        ),
    )

    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        help=(
            "Data inicial do backfill. "
            "Formato YYYY-MM-DD."
        ),
    )

    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        help=(
            "Data final do backfill. "
            "Formato YYYY-MM-DD."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Força novo download e nova versão "
            "do objeto no S3."
        ),
    )

    args = parser.parse_args()

    has_start_date = args.start_date is not None
    has_end_date = args.end_date is not None

    if has_start_date != has_end_date:
        parser.error(
            "--start-date e --end-date "
            "devem ser informados juntos."
        )

    if args.date is not None and has_start_date:
        parser.error(
            "--date não pode ser combinado "
            "com --start-date/--end-date."
        )

    if args.daily and has_start_date:
        parser.error(
            "--daily não pode ser combinado "
            "com --start-date/--end-date."
        )

    if has_start_date and has_end_date:
        ingest_backfill(
            start_date=args.start_date,
            end_date=args.end_date,
            force=args.force,
        )

        return

    if args.date is not None:
        ingest_single_date(
            trade_date=args.date,
            force=args.force,
        )

        return

    ingest_daily(
        force=args.force,
    )


if __name__ == "__main__":
    main()