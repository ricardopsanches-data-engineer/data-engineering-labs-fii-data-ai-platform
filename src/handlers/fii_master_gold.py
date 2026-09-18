from __future__ import annotations

import os
import re
from argparse import Namespace
from datetime import date
from pathlib import Path

import boto3
import pandas as pd

from src.pipelines.fii_master_gold import (
    DEFAULT_MIN_RESOLUTION_RATE,
    run_pipeline,
)
from src.storage.s3 import upload_file


TMP_ROOT = Path("/tmp/fii-master-gold")

TMP_CVM = (
    TMP_ROOT
    / "silver"
    / "cvm"
    / "cvm_fund_classes.parquet"
)

TMP_INSTRUMENTS = (
    TMP_ROOT
    / "silver"
    / "b3-instruments"
    / "b3_instruments.parquet"
)

TMP_TRADES = (
    TMP_ROOT
    / "silver"
    / "b3"
    / "b3_trades.parquet"
)

TMP_GOLD_ROOT = (
    TMP_ROOT
    / "gold"
    / "fii-master"
)


SILVER_PATTERNS = {
    "b3": re.compile(
        r"^silver/b3/"
        r"year=(\d{4})/"
        r"month=(\d{2})/"
        r"day=(\d{2})/"
        r"b3_trades\.parquet$"
    ),
    "cvm": re.compile(
        r"^silver/cvm/"
        r"year=(\d{4})/"
        r"month=(\d{2})/"
        r"day=(\d{2})/"
        r"cvm_fund_classes\.parquet$"
    ),
    "b3-instruments": re.compile(
        r"^silver/b3-instruments/"
        r"year=(\d{4})/"
        r"month=(\d{2})/"
        r"day=(\d{2})/"
        r"b3_instruments\.parquet$"
    ),
}


SILVER_PREFIXES = {
    "b3": "silver/b3/",
    "cvm": "silver/cvm/",
    "b3-instruments": (
        "silver/b3-instruments/"
    ),
}


def parse_partition_date(
    key: str,
    source: str,
) -> date | None:
    pattern = SILVER_PATTERNS[source]

    match = pattern.fullmatch(
        key
    )

    if match is None:
        return None

    year, month, day = (
        int(value)
        for value in match.groups()
    )

    return date(
        year,
        month,
        day,
    )


def list_partitioned_objects(
    bucket: str,
    source: str,
) -> list[tuple[date, str]]:
    s3 = boto3.client(
        "s3"
    )

    paginator = (
        s3.get_paginator(
            "list_objects_v2"
        )
    )

    objects: list[
        tuple[date, str]
    ] = []

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=SILVER_PREFIXES[
            source
        ],
    ):
        for item in page.get(
            "Contents",
            [],
        ):
            key = item["Key"]

            partition_date = (
                parse_partition_date(
                    key=key,
                    source=source,
                )
            )

            if partition_date is None:
                continue

            objects.append(
                (
                    partition_date,
                    key,
                )
            )

    return sorted(
        objects,
        key=lambda item: item[0],
    )


def find_latest_object(
    bucket: str,
    source: str,
    max_date: date | None = None,
) -> tuple[date, str]:
    objects = (
        list_partitioned_objects(
            bucket=bucket,
            source=source,
        )
    )

    if max_date is not None:
        objects = [
            item
            for item in objects
            if item[0] <= max_date
        ]

    if not objects:
        constraint = (
            f" <= {max_date.isoformat()}"
            if max_date is not None
            else ""
        )

        raise FileNotFoundError(
            f"No valid Silver object "
            f"found for {source}"
            f"{constraint}."
        )

    return objects[-1]


def download_object(
    bucket: str,
    key: str,
    local_path: Path,
) -> None:
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    boto3.client(
        "s3"
    ).download_file(
        bucket,
        key,
        str(
            local_path
        ),
    )


def build_gold_s3_key(
    reference_date: date,
) -> str:
    return (
        "gold/fii-master/"
        f"year={reference_date.year:04d}/"
        f"month={reference_date.month:02d}/"
        f"day={reference_date.day:02d}/"
        "fii_master.parquet"
    )


def run_fii_master_gold(
    bucket: str,
) -> dict:
    print(
        "======================================"
    )
    print(
        "FII MASTER GOLD | AWS"
    )
    print(
        "======================================"
    )

    (
        instruments_date,
        instruments_key,
    ) = find_latest_object(
        bucket=bucket,
        source="b3-instruments",
    )

    print(
        "B3 Instruments Silver selecionado | "
        f"reference_date="
        f"{instruments_date.isoformat()} | "
        f"key={instruments_key}"
    )

    (
        cvm_date,
        cvm_key,
    ) = find_latest_object(
        bucket=bucket,
        source="cvm",
        max_date=instruments_date,
    )

    print(
        "CVM Silver selecionado | "
        f"reference_date="
        f"{cvm_date.isoformat()} | "
        f"key={cvm_key}"
    )

    (
        trades_date,
        trades_key,
    ) = find_latest_object(
        bucket=bucket,
        source="b3",
        max_date=instruments_date,
    )

    print(
        "B3 Trades Silver selecionado | "
        f"reference_date="
        f"{trades_date.isoformat()} | "
        f"key={trades_key}"
    )

    download_object(
        bucket=bucket,
        key=cvm_key,
        local_path=TMP_CVM,
    )

    download_object(
        bucket=bucket,
        key=instruments_key,
        local_path=TMP_INSTRUMENTS,
    )

    download_object(
        bucket=bucket,
        key=trades_key,
        local_path=TMP_TRADES,
    )

    args = Namespace(
        cvm=TMP_CVM,
        instruments=TMP_INSTRUMENTS,
        trades=TMP_TRADES,
        output_root=TMP_GOLD_ROOT,
        min_resolution_rate=(
            DEFAULT_MIN_RESOLUTION_RATE
        ),
    )

    output_path = run_pipeline(
        args
    )

    gold_dataframe = (
        pd.read_parquet(
            output_path
        )
    )

    gold_reference_values = (
        gold_dataframe[
            "reference_date"
        ]
        .dropna()
    )

    if gold_reference_values.empty:
        raise RuntimeError(
            "Gold output has no "
            "reference_date."
        )

    gold_reference_date = (
        pd.Timestamp(
            gold_reference_values.iloc[0]
        )
        .date()
    )

    if (
        gold_reference_date
        != instruments_date
    ):
        raise RuntimeError(
            "Gold reference_date does not "
            "match the selected "
            "B3 Instruments partition. "
            f"gold="
            f"{gold_reference_date} | "
            f"instruments="
            f"{instruments_date}"
        )

    gold_key = build_gold_s3_key(
        gold_reference_date
    )

    upload_file(
        local_path=output_path,
        bucket_name=bucket,
        s3_key=gold_key,
        force=False,
    )

    print()
    print(
        "Gold FII Master publicado | "
        f"s3://{bucket}/{gold_key}"
    )

    return {
        "status": "success",
        "reference_date": (
            gold_reference_date.isoformat()
        ),
        "records": int(
            len(
                gold_dataframe
            )
        ),
        "inputs": {
            "cvm": {
                "reference_date":
                    cvm_date.isoformat(),
                "key": cvm_key,
            },
            "b3_instruments": {
                "reference_date":
                    instruments_date.isoformat(),
                "key": instruments_key,
            },
            "b3_trades": {
                "reference_date":
                    trades_date.isoformat(),
                "key": trades_key,
            },
        },
        "gold_key": gold_key,
        "gold_uri": (
            f"s3://{bucket}/{gold_key}"
        ),
    }


def lambda_handler(
    event,
    context,
):
    bucket = os.environ.get(
        "FII_DATA_LAKE_BUCKET"
    )

    if not bucket:
        raise RuntimeError(
            "Environment variable "
            "FII_DATA_LAKE_BUCKET "
            "is required."
        )

    return run_fii_master_gold(
        bucket=bucket
    )