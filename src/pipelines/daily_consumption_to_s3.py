from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.serving.daily_consumption.builder import (
    LATEST_SNAPSHOT_PATH,
    build_daily_consumption_layer,
)
from src.storage.s3 import upload_file

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

SERVING_S3_KEY = (
    "serving/daily/latest_snapshot.json"
)


def calculate_manifest_content_sha256(
    manifest: dict[str, Any],
) -> str:
    """
    Calcula fingerprint lógico do manifesto.

    generated_at é deliberadamente ignorado,
    pois representa metadata operacional da
    execução e muda mesmo quando o snapshot
    de negócio continua idêntico.
    """

    logical_manifest = {
        key: value
        for key, value in manifest.items()
        if key != "generated_at"
    }

    canonical_json = json.dumps(
        logical_manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_json.encode(
            "utf-8"
        )
    ).hexdigest()


def publish_manifest(
    manifest: dict[str, Any],
    local_path: Path = LATEST_SNAPSHOT_PATH,
    force: bool = False,
) -> str:
    """
    Publica o latest pointer no S3.

    O objeto físico possui generated_at,
    enquanto content_sha256 representa apenas
    o estado lógico de negócio.
    """

    content_sha256 = (
        calculate_manifest_content_sha256(
            manifest
        )
    )

    print(
        "\nFingerprint lógico serving | "
        f"content_sha256={content_sha256}"
    )

    print(
        "Destino S3 | "
        f"s3://{BUCKET_NAME}/{SERVING_S3_KEY}"
    )

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=SERVING_S3_KEY,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> str:
    """
    Constrói, valida e publica a
    Daily Consumption Layer.
    """

    manifest = (
        build_daily_consumption_layer()
    )

    s3_uri = publish_manifest(
        manifest=manifest,
        local_path=LATEST_SNAPSHOT_PATH,
        force=force,
    )

    print()
    print(
        "======================================"
    )
    print(
        "DAILY CONSUMPTION PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Trade date:  "
        f"{manifest['trade_date']}"
    )

    print(
        f"Status:      "
        f"{manifest['status']}"
    )

    print(
        f"Destino S3:  "
        f"{s3_uri}"
    )

    return s3_uri


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói e publica a Daily "
            "Consumption Layer no Data Lake S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar nova "
            "versão do objeto S3."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()