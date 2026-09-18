from __future__ import annotations

import argparse
import os
from datetime import date

from src.ingestion.b3.fingerprint import (
    calculate_b3_instruments_content_sha256,
)
from src.ingestion.b3.instruments_client import (
    download_latest_instrument_report,
)
from src.storage.s3 import upload_file


BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)


def build_s3_key(
    capture_date: date,
) -> str:
    """
    Chave RAW do B3 Instruments.

    A partição representa a data da captura.
    """

    return (
        "raw/b3-instruments/"
        f"year={capture_date.year}/"
        f"month={capture_date.month:02d}/"
        f"day={capture_date.day:02d}/"
        "pesquisa-pregao.zip"
    )


def ingest_daily(
    force: bool = False,
) -> dict:
    """
    Executa a captura diária do
    B3 Instrument Report e envia ao S3.
    """

    capture_date = date.today()

    print("======================================")
    print("B3 INSTRUMENTS RAW -> S3 | DAILY")
    print("======================================")
    print(f"Data de captura: {capture_date}")
    print(f"Force: {force}")
    print()

    (
        local_path,
        reference_date,
    ) = download_latest_instrument_report(
        capture_date=capture_date,
        overwrite=force,
    )

    content_sha256 = (
        calculate_b3_instruments_content_sha256(
            local_path
        )
    )

    print(
        "Fingerprint lógico B3 Instruments | "
        f"content_sha256={content_sha256}"
    )

    s3_key = build_s3_key(
        capture_date
    )

    s3_uri = upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        content_sha256=content_sha256,
        force=force,
    )

    print()
    print(
        "B3 Instruments RAW concluído | "
        f"capture_date={capture_date} | "
        f"reference_date={reference_date} | "
        f"s3_uri={s3_uri}"
    )

    return {
        "source": "b3-instruments",
        "capture_date": (
            capture_date.isoformat()
        ),
        "reference_date": (
            reference_date.isoformat()
        ),
        "local_path": str(local_path),
        "s3_key": s3_key,
        "s3_uri": s3_uri,
        "content_sha256": content_sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline diária do B3 Instrument "
            "Report para RAW no S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Força novo download e uma nova "
            "versão do objeto RAW no S3."
        ),
    )

    args = parser.parse_args()

    ingest_daily(
        force=args.force,
    )


if __name__ == "__main__":
    main()