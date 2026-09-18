from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError


CONTROL_PREFIX = "control/gold-readiness"

REQUIRED_MARKERS = {
    "b3": "b3_SUCCESS.json",
    "cvm": "cvm_SUCCESS.json",
    "b3_instruments": (
        "b3_instruments_SUCCESS.json"
    ),
}

RUN_DATE_PATTERN = re.compile(
    r"^control/gold-readiness/"
    r"run_date=(\d{4}-\d{2}-\d{2})/"
    r".+$"
)


def extract_run_date_from_key(
    key: str,
) -> date:
    match = RUN_DATE_PATTERN.fullmatch(
        key
    )

    if match is None:
        raise ValueError(
            "Could not extract run_date "
            f"from readiness key: {key}"
        )

    return date.fromisoformat(
        match.group(1)
    )


def build_marker_key(
    run_date: date,
    marker_filename: str,
) -> str:
    return (
        f"{CONTROL_PREFIX}/"
        f"run_date={run_date.isoformat()}/"
        f"{marker_filename}"
    )


def read_marker(
    *,
    bucket: str,
    key: str,
) -> dict:
    s3 = boto3.client(
        "s3"
    )

    response = s3.get_object(
        Bucket=bucket,
        Key=key,
    )

    body = response[
        "Body"
    ].read()

    marker = json.loads(
        body.decode(
            "utf-8"
        )
    )

    if marker.get(
        "status"
    ) != "SUCCESS":
        raise ValueError(
            "Readiness marker is not SUCCESS | "
            f"key={key}"
        )

    return marker


def load_required_markers(
    *,
    bucket: str,
    run_date: date,
) -> dict | None:
    s3 = boto3.client(
        "s3"
    )

    markers: dict[
        str,
        dict,
    ] = {}

    for (
        source_name,
        marker_filename,
    ) in REQUIRED_MARKERS.items():
        marker_key = build_marker_key(
            run_date=run_date,
            marker_filename=marker_filename,
        )

        try:
            s3.head_object(
                Bucket=bucket,
                Key=marker_key,
            )
        except ClientError as exc:
            error_code = (
                exc.response
                .get(
                    "Error",
                    {},
                )
                .get(
                    "Code"
                )
            )

            if error_code in {
                "404",
                "NoSuchKey",
                "NotFound",
            }:
                print(
                    "Gold readiness WAITING | "
                    f"missing={marker_key}"
                )

                return None

            raise

        marker = read_marker(
            bucket=bucket,
            key=marker_key,
        )

        markers[
            source_name
        ] = marker

    return markers


def validate_marker_run_dates(
    *,
    run_date: date,
    markers: dict,
) -> None:
    expected_run_date = (
        run_date.isoformat()
    )

    for (
        source_name,
        marker,
    ) in markers.items():
        marker_run_date = marker.get(
            "run_date"
        )

        if (
            marker_run_date
            != expected_run_date
        ):
            raise ValueError(
                "Readiness marker run_date "
                "does not match coordinator "
                "run_date | "
                f"source={source_name} | "
                f"marker={marker_run_date} | "
                f"expected="
                f"{expected_run_date}"
            )


def validate_marker_fields(
    markers: dict,
) -> None:
    required_fields = {
        "reference_date",
        "silver_key",
        "records",
    }

    for (
        source_name,
        marker,
    ) in markers.items():
        missing_fields = [
            field
            for field in required_fields
            if marker.get(
                field
            ) is None
        ]

        if missing_fields:
            raise ValueError(
                "Readiness marker has missing "
                "required fields | "
                f"source={source_name} | "
                f"missing={missing_fields}"
            )


def build_gold_payload(
    *,
    run_date: date,
    markers: dict,
) -> dict:
    return {
        "run_date": (
            run_date.isoformat()
        ),
        "inputs": {
            "b3_trades": {
                "reference_date": (
                    markers[
                        "b3"
                    ][
                        "reference_date"
                    ]
                ),
                "key": (
                    markers[
                        "b3"
                    ][
                        "silver_key"
                    ]
                ),
            },
            "cvm": {
                "reference_date": (
                    markers[
                        "cvm"
                    ][
                        "reference_date"
                    ]
                ),
                "key": (
                    markers[
                        "cvm"
                    ][
                        "silver_key"
                    ]
                ),
            },
            "b3_instruments": {
                "reference_date": (
                    markers[
                        "b3_instruments"
                    ][
                        "reference_date"
                    ]
                ),
                "key": (
                    markers[
                        "b3_instruments"
                    ][
                        "silver_key"
                    ]
                ),
            },
        },
    }


def build_readiness_fingerprint(
    *,
    run_date: date,
    markers: dict,
) -> str:
    fingerprint_data = {
        "run_date": (
            run_date.isoformat()
        ),
        "sources": {
            "b3": {
                "reference_date": (
                    markers[
                        "b3"
                    ][
                        "reference_date"
                    ]
                ),
                "silver_key": (
                    markers[
                        "b3"
                    ][
                        "silver_key"
                    ]
                ),
                "records": (
                    markers[
                        "b3"
                    ][
                        "records"
                    ]
                ),
            },
            "cvm": {
                "reference_date": (
                    markers[
                        "cvm"
                    ][
                        "reference_date"
                    ]
                ),
                "silver_key": (
                    markers[
                        "cvm"
                    ][
                        "silver_key"
                    ]
                ),
                "records": (
                    markers[
                        "cvm"
                    ][
                        "records"
                    ]
                ),
            },
            "b3_instruments": {
                "reference_date": (
                    markers[
                        "b3_instruments"
                    ][
                        "reference_date"
                    ]
                ),
                "silver_key": (
                    markers[
                        "b3_instruments"
                    ][
                        "silver_key"
                    ]
                ),
                "records": (
                    markers[
                        "b3_instruments"
                    ][
                        "records"
                    ]
                ),
            },
        },
    }

    canonical = json.dumps(
        fingerprint_data,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        canonical
    ).hexdigest()


def build_dispatch_lock_key(
    *,
    run_date: date,
    fingerprint: str,
) -> str:
    return (
        f"{CONTROL_PREFIX}/"
        f"run_date={run_date.isoformat()}/"
        "dispatches/"
        f"{fingerprint}.json"
    )


def acquire_dispatch_lock(
    *,
    bucket: str,
    run_date: date,
    fingerprint: str,
    payload: dict,
) -> tuple[bool, str]:
    s3 = boto3.client(
        "s3"
    )

    lock_key = build_dispatch_lock_key(
        run_date=run_date,
        fingerprint=fingerprint,
    )

    lock_payload = {
        "status": "CLAIMED",
        "run_date": (
            run_date.isoformat()
        ),
        "fingerprint": fingerprint,
        "claimed_at": (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        ),
        "gold_payload": payload,
    }

    try:
        s3.put_object(
            Bucket=bucket,
            Key=lock_key,
            Body=json.dumps(
                lock_payload,
                sort_keys=True,
            ).encode(
                "utf-8"
            ),
            ContentType=(
                "application/json"
            ),
            IfNoneMatch="*",
        )

        print(
            "Gold dispatch lock ACQUIRED | "
            f"key={lock_key}"
        )

        return (
            True,
            lock_key,
        )

    except ClientError as exc:
        error_code = (
            exc.response
            .get(
                "Error",
                {},
            )
            .get(
                "Code"
            )
        )

        status_code = (
            exc.response
            .get(
                "ResponseMetadata",
                {},
            )
            .get(
                "HTTPStatusCode"
            )
        )

        if (
            error_code
            in {
                "PreconditionFailed",
                "ConditionalRequestConflict",
            }
            or status_code
            in {
                409,
                412,
            }
        ):
            print(
                "Gold dispatch lock already "
                "exists | duplicate ignored | "
                f"key={lock_key}"
            )

            return (
                False,
                lock_key,
            )

        raise


def release_dispatch_lock(
    *,
    bucket: str,
    key: str,
) -> None:
    boto3.client(
        "s3"
    ).delete_object(
        Bucket=bucket,
        Key=key,
    )

    print(
        "Gold dispatch lock RELEASED | "
        f"key={key}"
    )


def invoke_gold(
    *,
    function_name: str,
    payload: dict,
) -> dict:
    lambda_client = boto3.client(
        "lambda"
    )

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="Event",
        Payload=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
    )

    status_code = response.get(
        "StatusCode"
    )

    if status_code != 202:
        raise RuntimeError(
            "Gold Lambda async invocation "
            "did not return HTTP 202 | "
            f"status_code={status_code}"
        )

    return {
        "status_code": (
            status_code
        ),
    }


def extract_trigger_key(
    event: dict,
) -> str:
    records = event.get(
        "Records",
        [],
    )

    if not records:
        raise ValueError(
            "No S3 records found "
            "in coordinator event."
        )

    first_record = records[
        0
    ]

    if (
        first_record.get(
            "eventSource"
        )
        != "aws:s3"
    ):
        raise ValueError(
            "Unsupported coordinator "
            "event source."
        )

    encoded_key = (
        first_record[
            "s3"
        ][
            "object"
        ][
            "key"
        ]
    )

    return unquote_plus(
        encoded_key
    )


def lambda_handler(
    event,
    context,
):
    bucket = os.environ.get(
        "FII_DATA_LAKE_BUCKET"
    )

    gold_function_name = os.environ.get(
        "FII_MASTER_GOLD_FUNCTION_NAME"
    )

    if not bucket:
        raise RuntimeError(
            "Environment variable "
            "FII_DATA_LAKE_BUCKET "
            "is required."
        )

    if not gold_function_name:
        raise RuntimeError(
            "Environment variable "
            "FII_MASTER_GOLD_FUNCTION_NAME "
            "is required."
        )

    trigger_key = extract_trigger_key(
        event
    )

    run_date = extract_run_date_from_key(
        trigger_key
    )

    print(
        "Gold readiness coordinator | "
        f"run_date={run_date.isoformat()} | "
        f"trigger={trigger_key}"
    )

    markers = load_required_markers(
        bucket=bucket,
        run_date=run_date,
    )

    if markers is None:
        return {
            "status": "waiting",
            "run_date": (
                run_date.isoformat()
            ),
        }

    validate_marker_run_dates(
        run_date=run_date,
        markers=markers,
    )

    validate_marker_fields(
        markers
    )

    payload = build_gold_payload(
        run_date=run_date,
        markers=markers,
    )

    fingerprint = (
        build_readiness_fingerprint(
            run_date=run_date,
            markers=markers,
        )
    )

    (
        lock_acquired,
        lock_key,
    ) = acquire_dispatch_lock(
        bucket=bucket,
        run_date=run_date,
        fingerprint=fingerprint,
        payload=payload,
    )

    if not lock_acquired:
        return {
            "status": (
                "duplicate_ignored"
            ),
            "run_date": (
                run_date.isoformat()
            ),
            "fingerprint": (
                fingerprint
            ),
            "dispatch_lock": (
                lock_key
            ),
        }

    try:
        invoke_result = invoke_gold(
            function_name=(
                gold_function_name
            ),
            payload=payload,
        )
    except Exception:
        release_dispatch_lock(
            bucket=bucket,
            key=lock_key,
        )

        raise

    print(
        "Gold readiness COMPLETE | "
        "Gold invocation accepted | "
        f"run_date={run_date.isoformat()} | "
        f"fingerprint={fingerprint}"
    )

    return {
        "status": "gold_invoked",
        "run_date": (
            run_date.isoformat()
        ),
        "fingerprint": (
            fingerprint
        ),
        "dispatch_lock": (
            lock_key
        ),
        "gold_function": (
            gold_function_name
        ),
        "invoke_status_code": (
            invoke_result[
                "status_code"
            ]
        ),
        "payload": payload,
    }