import os
import re

from datetime import date
from pathlib import Path
from urllib.parse import unquote_plus

import boto3

from src.orchestration.gold_readiness import (
    get_s3_object_run_date,
    write_success_marker,
)

from src.pipelines.cvm_raw_to_silver import (
    transform_cvm_raw_to_silver,
)


TMP_RAW_ROOT = Path("/tmp/raw/cvm")
TMP_SILVER_ROOT = Path("/tmp/silver/cvm")

CVM_RAW_FILE_PATTERN = re.compile(
    r"^registro_fundo_classe\.zip$"
)

CVM_RAW_KEY_PATTERN = re.compile(
    r"^raw/cvm/"
    r"year=(\d{4})/"
    r"month=(\d{2})/"
    r"day=(\d{2})/"
    r"registro_fundo_classe\.zip$"
)


def extract_s3_objects(
    event: dict,
) -> list[tuple[str, str]]:
    if "Records" in event:
        objects: list[tuple[str, str]] = []

        for record in event["Records"]:
            if record.get(
                "eventSource"
            ) != "aws:s3":
                continue

            s3_data = record.get(
                "s3",
                {},
            )

            bucket = (
                s3_data
                .get("bucket", {})
                .get("name")
            )

            key = (
                s3_data
                .get("object", {})
                .get("key")
            )

            if not bucket or not key:
                raise ValueError(
                    "Invalid S3 event: "
                    "bucket or key is missing."
                )

            objects.append(
                (
                    bucket,
                    unquote_plus(key),
                )
            )

        if not objects:
            raise ValueError(
                "No valid S3 records "
                "found in event."
            )

        return objects

    bucket = event.get("bucket")
    key = event.get("key")

    if bucket and key:
        return [
            (
                bucket,
                key,
            )
        ]

    raise ValueError(
        "Unsupported event format. "
        "Expected an S3 event or "
        "{'bucket': '...', 'key': '...'}."
    )


def validate_raw_key(
    key: str,
) -> None:
    if not key.startswith(
        "raw/cvm/"
    ):
        raise ValueError(
            f"Invalid CVM RAW key: {key}. "
            "Expected prefix 'raw/cvm/'."
        )

    filename = Path(
        key
    ).name

    if not CVM_RAW_FILE_PATTERN.fullmatch(
        filename
    ):
        raise ValueError(
            f"Invalid CVM RAW filename: {filename}."
        )

    if not CVM_RAW_KEY_PATTERN.fullmatch(
        key
    ):
        raise ValueError(
            f"Invalid CVM RAW key structure: {key}."
        )


def extract_reference_date(
    key: str,
) -> date:
    match = CVM_RAW_KEY_PATTERN.fullmatch(
        key
    )

    if match is None:
        raise ValueError(
            "Could not extract reference date "
            f"from key: {key}"
        )

    year, month, day = (
        int(value)
        for value in match.groups()
    )

    return date(
        year,
        month,
        day,
    )


def build_local_raw_path(
    key: str,
) -> Path:
    return (
        TMP_RAW_ROOT
        / Path(key).name
    )


def download_raw_from_s3(
    bucket: str,
    key: str,
    local_path: Path,
) -> None:
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    s3 = boto3.client("s3")

    s3.download_file(
        bucket,
        key,
        str(local_path),
    )


def run_cvm_raw_to_silver(
    bucket: str,
    key: str,
) -> dict:
    validate_raw_key(
        key
    )

    reference_date = extract_reference_date(
        key
    )

    run_date = get_s3_object_run_date(
        bucket=bucket,
        key=key,
    )

    local_raw_path = (
        build_local_raw_path(
            key
        )
    )

    download_raw_from_s3(
        bucket=bucket,
        key=key,
        local_path=local_raw_path,
    )

    os.environ[
        "FII_DATA_LAKE_BUCKET"
    ] = bucket

    silver_file, silver_metadata = (
        transform_cvm_raw_to_silver(
            raw_zip_path=local_raw_path,
            reference_date=reference_date,
            silver_root=TMP_SILVER_ROOT,
            upload_to_s3=True,
            force=False,
        )
    )

    readiness = write_success_marker(
        bucket=bucket,
        run_date=run_date,
        source="cvm",
        reference_date=str(
            silver_metadata[
                "reference_date"
            ]
        ),
        silver_key=silver_metadata[
            "s3_key"
        ],
        records=silver_metadata[
            "records"
        ],
        extra={
            "raw_key": key,
        },
    )

    return {
        "status": "success",
        "source": "cvm",
        "bucket": bucket,
        "raw_key": key,
        "silver_file": str(
            silver_file
        ),
        "silver_key": silver_metadata[
            "s3_key"
        ],
        "records": silver_metadata[
            "records"
        ],
        "reference_date": (
            silver_metadata[
                "reference_date"
            ]
        ),
        "s3_uri": silver_metadata.get(
            "s3_uri"
        ),
        "readiness_marker": (
            readiness[
                "marker_key"
            ]
        ),
    }


def lambda_handler(
    event,
    context,
):
    objects = extract_s3_objects(
        event
    )

    results = [
        run_cvm_raw_to_silver(
            bucket=bucket,
            key=key,
        )
        for bucket, key
        in objects
    ]

    if len(results) == 1:
        return results[0]

    return {
        "status": "success",
        "source": "cvm",
        "processed_objects": len(
            results
        ),
        "results": results,
    }