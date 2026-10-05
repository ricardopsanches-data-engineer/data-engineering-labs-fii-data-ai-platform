from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.ai.structured_retrieval.builder import (
    CONTEXT_DATASET_PATH,
    CONTEXT_MANIFEST_PATH,
    build_structured_retrieval_layer,
)
from src.storage.s3 import upload_file

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

CONTEXT_S3_KEY = (
    "serving/ai/"
    "fii_structured_context.jsonl"
)

MANIFEST_S3_KEY = (
    "serving/ai/"
    "fii_structured_context.json"
)


def calculate_jsonl_content_sha256(
    path: Path,
) -> str:
    """
    Calcula fingerprint lógico do JSONL.

    O builder já garante ordenação
    determinística por ticker e chaves JSON
    ordenadas.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Structured Context não encontrado: {path}"
        )

    sha256 = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            sha256.update(
                chunk
            )

    return sha256.hexdigest()


def calculate_manifest_content_sha256(
    manifest: dict[str, Any],
) -> str:
    """
    Calcula fingerprint lógico do manifest.

    generated_at não participa da identidade
    lógica do estado servido.
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


def publish_context(
    local_path: Path = CONTEXT_DATASET_PATH,
    force: bool = False,
) -> str:
    """
    Publica o contexto estruturado no S3.
    """

    content_sha256 = (
        calculate_jsonl_content_sha256(
            local_path
        )
    )

    print(
        "\nFingerprint lógico AI context | "
        f"content_sha256={content_sha256}"
    )

    print(
        "Destino S3 | "
        f"s3://{BUCKET_NAME}/{CONTEXT_S3_KEY}"
    )

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=CONTEXT_S3_KEY,
        content_sha256=content_sha256,
        force=force,
    )


def publish_manifest(
    manifest: dict[str, Any],
    local_path: Path = CONTEXT_MANIFEST_PATH,
    force: bool = False,
) -> str:
    """
    Publica o manifest do structured retrieval.
    """

    content_sha256 = (
        calculate_manifest_content_sha256(
            manifest
        )
    )

    print(
        "\nFingerprint lógico AI manifest | "
        f"content_sha256={content_sha256}"
    )

    print(
        "Destino S3 | "
        f"s3://{BUCKET_NAME}/{MANIFEST_S3_KEY}"
    )

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=MANIFEST_S3_KEY,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> tuple[
    str,
    str,
]:
    """
    Constrói e publica a Structured Retrieval
    Foundation.
    """

    records, manifest = (
        build_structured_retrieval_layer()
    )

    context_uri = publish_context(
        local_path=CONTEXT_DATASET_PATH,
        force=force,
    )

    manifest_uri = publish_manifest(
        manifest=manifest,
        local_path=CONTEXT_MANIFEST_PATH,
        force=force,
    )

    print()
    print(
        "======================================"
    )
    print(
        "AI STRUCTURED RETRIEVAL PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Trade date:  "
        f"{manifest['trade_date']}"
    )

    print(
        f"Rows:        "
        f"{len(records):,}"
    )

    print(
        f"Context S3:  "
        f"{context_uri}"
    )

    print(
        f"Manifest S3: "
        f"{manifest_uri}"
    )

    return (
        context_uri,
        manifest_uri,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói e publica o AI "
            "Structured Retrieval Context."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite criar explicitamente "
            "nova versão no S3."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()