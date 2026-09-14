from __future__ import annotations

import argparse
from datetime import date

from src.ingestion.cvm.client import download_cvm_fund_register
from src.storage.s3 import upload_file

BUCKET_NAME = "fii-data-ai-platform-dev-datalake-625685670804"


def ingest_daily(
    force: bool = False,
) -> None:
    """
    Executa a carga diária da CVM.

    Usa a data atual como referência da partição.
    """

    reference_date = date.today()

    print("======================================")
    print("CVM RAW -> S3 | DAILY")
    print("======================================")
    print(f"Data de referência: {reference_date}")
    print(f"Force: {force}")
    print()

    local_path = download_cvm_fund_register(
        reference_date=reference_date,
    )

    upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        force=force,
    )


def ingest_single_date(
    reference_date: date,
    force: bool = False,
) -> None:
    """
    Executa a carga da CVM usando uma
    data de referência específica.
    """

    print("======================================")
    print("CVM RAW -> S3 | SINGLE DATE")
    print("======================================")
    print(f"Data de referência: {reference_date}")
    print(f"Force: {force}")
    print()

    local_path = download_cvm_fund_register(
        reference_date=reference_date,
    )

    upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        force=force,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline CVM RAW para S3 com suporte "
            "a daily, data específica e force."
        )
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--daily",
        action="store_true",
        help=(
            "Executa a carga atual da CVM "
            "usando a data de hoje."
        ),
    )

    mode.add_argument(
        "--date",
        type=date.fromisoformat,
        help=(
            "Executa a carga da CVM usando "
            "uma data de referência específica. "
            "Formato YYYY-MM-DD."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Força uma nova versão do objeto "
            "no S3 mesmo se o SHA-256 for idêntico."
        ),
    )

    args = parser.parse_args()

    if args.date is not None:
        ingest_single_date(
            reference_date=args.date,
            force=args.force,
        )

        return

    ingest_daily(
        force=args.force,
    )


if __name__ == "__main__":
    main()