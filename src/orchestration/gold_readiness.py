import json

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import boto3


CONTROL_PREFIX = "control/gold-readiness"
PLATFORM_TIMEZONE = ZoneInfo(
    "America/Sao_Paulo"
)


def build_success_marker_key(
    run_date: date,
    source: str,
) -> str:
    normalized_source = (
        source
        .strip()
        .lower()
        .replace("-", "_")
    )

    return (
        f"{CONTROL_PREFIX}/"
        f"run_date={run_date.isoformat()}/"
        f"{normalized_source}_SUCCESS.json"
    )


def get_s3_object_run_date(
    *,
    bucket: str,
    key: str,
) -> date:
    s3 = boto3.client("s3")

    response = s3.head_object(
        Bucket=bucket,
        Key=key,
    )

    last_modified = response[
        "LastModified"
    ]

    return (
        last_modified
        .astimezone(
            PLATFORM_TIMEZONE
        )
        .date()
    )


def write_success_marker(
    *,
    bucket: str,
    run_date: date,
    source: str,
    reference_date: str,
    silver_key: str,
    records: int,
    extra: dict | None = None,
) -> dict:
    marker_key = build_success_marker_key(
        run_date=run_date,
        source=source,
    )

    payload = {
        "status": "SUCCESS",
        "source": source,
        "run_date": run_date.isoformat(),
        "reference_date": str(
            reference_date
        ),
        "silver_key": silver_key,
        "records": int(records),
        "completed_at": (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        ),
    }

    if extra:
        payload.update(extra)

    s3 = boto3.client("s3")

    s3.put_object(
        Bucket=bucket,
        Key=marker_key,
        Body=json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8"),
        ContentType="application/json",
    )

    print(
        "Gold readiness SUCCESS marker written | "
        f"s3://{bucket}/{marker_key}"
    )

    return {
        "marker_key": marker_key,
        "marker_uri": (
            f"s3://{bucket}/{marker_key}"
        ),
        "payload": payload,
    }