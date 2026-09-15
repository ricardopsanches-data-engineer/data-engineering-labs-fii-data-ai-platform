from __future__ import annotations

import hashlib
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


SILVER_ROOT = Path("data/silver")


def build_s3_key_from_silver_path(
    local_path: str | Path,
) -> str:
    local_path = Path(local_path)

    try:
        relative_path = local_path.relative_to(
            SILVER_ROOT
        )
    except ValueError as error:
        raise ValueError(
            "O arquivo precisa estar dentro de "
            f"{SILVER_ROOT}."
        ) from error

    return (
        Path("silver")
        / relative_path
    ).as_posix()


def calculate_sha256(
    local_path: Path,
) -> str:
    sha256 = hashlib.sha256()

    with local_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


def get_remote_object_metadata(
    bucket_name: str,
    s3_key: str,
) -> dict | None:
    s3_client = boto3.client("s3")

    try:
        return s3_client.head_object(
            Bucket=bucket_name,
            Key=s3_key,
        )
    except ClientError as error:
        error_code = (
            error.response
            .get("Error", {})
            .get("Code")
        )

        if error_code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            return None

        raise


def build_upload_metadata(
    sha256: str,
    records: int,
    source: str,
    raw_file: str,
    trade_date: str,
) -> dict[str, str]:
    return {
        "sha256": sha256,
        "records": str(records),
        "source": source,
        "raw_file": raw_file,
        "trade_date": trade_date,
    }


def upload_silver_file(
    local_path: str | Path,
    bucket_name: str,
    s3_key: str | None = None,
    records: int | None = None,
    source: str | None = None,
    raw_file: str | None = None,
    trade_date: str | None = None,
    force: bool = False,
) -> str:
    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(
            f"Arquivo local não encontrado: {local_path}"
        )

    if not local_path.is_file():
        raise ValueError(
            f"O caminho informado não é um arquivo: {local_path}"
        )

    if records is None:
        raise ValueError(
            "records é obrigatório para upload Silver."
        )

    if source is None:
        raise ValueError(
            "source é obrigatório para upload Silver."
        )

    if raw_file is None:
        raise ValueError(
            "raw_file é obrigatório para upload Silver."
        )

    if trade_date is None:
        raise ValueError(
            "trade_date é obrigatório para upload Silver."
        )

    if s3_key is None:
        s3_key = build_s3_key_from_silver_path(
            local_path
        )

    s3_uri = (
        f"s3://{bucket_name}/{s3_key}"
    )

    local_sha256 = calculate_sha256(
        local_path
    )

    remote_object = get_remote_object_metadata(
        bucket_name=bucket_name,
        s3_key=s3_key,
    )

    if remote_object is not None:
        remote_metadata = (
            remote_object
            .get("Metadata", {})
        )

        remote_sha256 = (
            remote_metadata
            .get("sha256")
        )

        if remote_sha256 == local_sha256:
            if force:
                print(
                    "Force habilitado | "
                    "SHA-256 Silver idêntico | "
                    "nova versão será criada | "
                    f"{s3_uri}"
                )
            else:
                print(
                    "Upload Silver ignorado | "
                    "SHA-256 idêntico | "
                    f"{s3_uri}"
                )

                return s3_uri

        elif not force:
            remote_sha_display = (
                remote_sha256
                if remote_sha256 is not None
                else "ausente"
            )

            raise RuntimeError(
                "Upload Silver bloqueado | "
                "já existe um objeto diferente "
                "no mesmo caminho | "
                f"{s3_uri} | "
                f"local_sha256={local_sha256} | "
                f"remote_sha256={remote_sha_display} | "
                "use force=True somente após "
                "validação explícita"
            )

        else:
            print(
                "Force habilitado | "
                "Silver diferente detectada | "
                "nova versão será criada | "
                f"{s3_uri}"
            )

    metadata = build_upload_metadata(
        sha256=local_sha256,
        records=records,
        source=source,
        raw_file=raw_file,
        trade_date=trade_date,
    )

    s3_client = boto3.client("s3")

    s3_client.upload_file(
        str(local_path),
        bucket_name,
        s3_key,
        ExtraArgs={
            "Metadata": metadata,
        },
    )

    print(
        "Upload Silver concluído | "
        f"{s3_uri}"
    )

    return s3_uri