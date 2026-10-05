from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from src.serving.ml_inference.builder import (
    LATEST_INFERENCE_DATASET_PATH,
    LATEST_INFERENCE_MANIFEST_PATH,
    build_ml_serving_layer,
)
from src.storage.s3 import upload_file

BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)

DATASET_S3_KEY = (
    "serving/ml/"
    "latest_inference_features.parquet"
)

MANIFEST_S3_KEY = (
    "serving/ml/"
    "latest_inference_features.json"
)


def calculate_dataframe_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico determinístico
    do Latest Inference Dataset.

    Considera:

    - nomes das colunas;
    - tipos;
    - valores;
    - ordenação determinística.

    Metadata física do Parquet não participa
    da identidade lógica.
    """

    canonical = dataframe.copy()

    sort_columns = [
        column
        for column in [
            "feature_date",
            "ticker",
        ]
        if column in canonical.columns
    ]

    if sort_columns:
        canonical = (
            canonical.sort_values(
                by=sort_columns,
                kind="stable",
            )
            .reset_index(
                drop=True
            )
        )

    schema_text = "|".join(
        f"{column}:{canonical[column].dtype}"
        for column in canonical.columns
    )

    row_hashes = (
        pd.util.hash_pandas_object(
            canonical,
            index=False,
        )
        .values
        .tobytes()
    )

    sha256 = hashlib.sha256()

    sha256.update(
        schema_text.encode(
            "utf-8"
        )
    )

    sha256.update(
        row_hashes
    )

    return sha256.hexdigest()


def calculate_manifest_content_sha256(
    manifest: dict[str, Any],
) -> str:
    """
    Calcula fingerprint lógico do manifesto.

    generated_at é ignorado porque representa
    metadata operacional da execução.
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


def publish_dataset(
    dataframe: pd.DataFrame,
    local_path: Path = (
        LATEST_INFERENCE_DATASET_PATH
    ),
    force: bool = False,
) -> str:
    """
    Publica o Latest Inference Dataset.
    """

    content_sha256 = (
        calculate_dataframe_content_sha256(
            dataframe
        )
    )

    print(
        "\nFingerprint lógico ML dataset | "
        f"content_sha256={content_sha256}"
    )

    print(
        "Destino S3 | "
        f"s3://{BUCKET_NAME}/{DATASET_S3_KEY}"
    )

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=DATASET_S3_KEY,
        content_sha256=content_sha256,
        force=force,
    )


def publish_manifest(
    manifest: dict[str, Any],
    local_path: Path = (
        LATEST_INFERENCE_MANIFEST_PATH
    ),
    force: bool = False,
) -> str:
    """
    Publica o manifesto do ML Serving.
    """

    content_sha256 = (
        calculate_manifest_content_sha256(
            manifest
        )
    )

    print(
        "\nFingerprint lógico ML manifest | "
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
    Constrói, valida e publica os artefatos
    da ML Serving Foundation.
    """

    dataframe, manifest = (
        build_ml_serving_layer()
    )

    dataset_uri = publish_dataset(
        dataframe=dataframe,
        local_path=(
            LATEST_INFERENCE_DATASET_PATH
        ),
        force=force,
    )

    manifest_uri = publish_manifest(
        manifest=manifest,
        local_path=(
            LATEST_INFERENCE_MANIFEST_PATH
        ),
        force=force,
    )

    print()
    print(
        "======================================"
    )
    print(
        "ML SERVING PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Feature date: "
        f"{manifest['feature_date']}"
    )

    print(
        f"Rows:         "
        f"{manifest['row_count']:,}"
    )

    print(
        f"Features:     "
        f"{manifest['feature_count']}"
    )

    print(
        f"Dataset S3:   "
        f"{dataset_uri}"
    )

    print(
        f"Manifest S3:  "
        f"{manifest_uri}"
    )

    return (
        dataset_uri,
        manifest_uri,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói e publica a ML "
            "Serving Foundation no S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar "
            "nova versão dos objetos S3."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()