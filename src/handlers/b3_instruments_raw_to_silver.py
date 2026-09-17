import os
import re
from pathlib import Path
from urllib.parse import unquote_plus

import boto3

from src.pipelines.b3_instruments_raw_to_silver import (
    transform_b3_instruments_raw_to_silver,
)


TMP_RAW_ROOT = Path(
    "/tmp/raw/b3-instruments"
)

TMP_SILVER_ROOT = Path(
    "/tmp/silver/b3-instruments"
)

B3_INSTRUMENTS_RAW_FILE_PATTERN = re.compile(
    r"^pesquisa-pregao\.zip$",
    re.IGNORECASE,
)


def extract_s3_objects(
    event: dict,
) -> list[tuple[str, str]]:
    if "Records" in event:
        objects: list[
            tuple[str, str]
        ] = []

        for record in event["Records"]:
            if (
                record.get(
                    "eventSource"
                )
                != "aws:s3"
            ):
                continue

            s3_data = record.get(
                "s3",
                {},
            )

            bucket = (
                s3_data
                .get(
                    "bucket",
                    {},
                )
                .get(
                    "name"
                )
            )

            key = (
                s3_data
                .get(
                    "object",
                    {},
                )
                .get(
                    "key"
                )
            )

            if not bucket or not key:
                raise ValueError(
                    "Invalid S3 event: "
                    "bucket or key is missing."
                )

            objects.append(
                (
                    bucket,
                    unquote_plus(
                        key
                    ),
                )
            )

        if not objects:
            raise ValueError(
                "No valid S3 records "
                "found in event."
            )

        return objects

    bucket = event.get(
        "bucket"
    )

    key = event.get(
        "key"
    )

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
        "{'bucket': '...', "
        "'key': '...'}."
    )


def validate_raw_key(
    key: str,
) -> None:
    if not key.startswith(
        "raw/b3-instruments/"
    ):
        raise ValueError(
            "Invalid B3 Instruments "
            f"RAW key: {key}. "
            "Expected prefix "
            "'raw/b3-instruments/'."
        )

    filename = Path(
        key
    ).name

    if not (
        B3_INSTRUMENTS_RAW_FILE_PATTERN
        .fullmatch(
            filename
        )
    ):
        raise ValueError(
            "Invalid B3 Instruments "
            f"RAW filename: {filename}. "
            "Expected "
            "'pesquisa-pregao.zip'."
        )


def build_local_raw_path(
    key: str,
) -> Path:
    return (
        TMP_RAW_ROOT
        / Path(
            key
        ).name
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

    s3 = boto3.client(
        "s3"
    )

    s3.download_file(
        bucket,
        key,
        str(
            local_path
        ),
    )


def run_b3_instruments_raw_to_silver(
    bucket: str,
    key: str,
) -> dict:
    validate_raw_key(
        key
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

    (
        silver_file,
        silver_metadata,
    ) = (
        transform_b3_instruments_raw_to_silver(
            raw_zip_path=(
                local_raw_path
            ),
            silver_root=(
                TMP_SILVER_ROOT
            ),
            upload_to_s3=True,
            force=False,
        )
    )

    return {
        "status": "success",
        "source": (
            "b3-instruments"
        ),
        "bucket": bucket,
        "raw_key": key,
        "silver_file": str(
            silver_file
        ),
        "silver_key": (
            silver_metadata[
                "s3_key"
            ]
        ),
        "records": (
            silver_metadata[
                "records"
            ]
        ),
        "reference_date": (
            silver_metadata[
                "reference_date"
            ]
        ),
        "inner_zip": (
            silver_metadata[
                "inner_zip"
            ]
        ),
        "selected_xml": (
            silver_metadata[
                "selected_xml"
            ]
        ),
        "xml_count": (
            silver_metadata[
                "xml_count"
            ]
        ),
        "duplicates_removed": (
            silver_metadata[
                "duplicates_removed"
            ]
        ),
        "s3_uri": (
            silver_metadata.get(
                "s3_uri"
            )
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
        run_b3_instruments_raw_to_silver(
            bucket=bucket,
            key=key,
        )
        for bucket, key
        in objects
    ]

    if len(
        results
    ) == 1:
        return results[0]

    return {
        "status": "success",
        "source": (
            "b3-instruments"
        ),
        "processed_objects": len(
            results
        ),
        "results": results,
    }