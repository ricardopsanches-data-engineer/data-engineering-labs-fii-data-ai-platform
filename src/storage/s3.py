from __future__ import annotations

import hashlib
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

RAW_ROOT = Path("data/raw")


def build_s3_key_from_raw_path(
    local_path: str | Path,
) -> str:
    """
    Converte um caminho RAW local em uma chave S3.

    Exemplo:
        data/raw/b3/year=2026/month=08/day=28/file.zip

    vira:
        raw/b3/year=2026/month=08/day=28/file.zip
    """

    local_path = Path(local_path)

    try:
        relative_path = local_path.relative_to(
            RAW_ROOT
        )

    except ValueError as error:
        raise ValueError(
            "O arquivo precisa estar dentro de "
            f"{RAW_ROOT}."
        ) from error

    return (
        Path("raw")
        / relative_path
    ).as_posix()


def calculate_sha256(
    local_path: Path,
) -> str:
    """
    Calcula o SHA-256 físico de um arquivo local.
    """

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
    """
    Retorna os metadados do objeto no S3.

    Retorna None caso o objeto não exista.
    """

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
    raw_sha256: str,
    content_sha256: str | None,
) -> dict[str, str]:
    """
    Monta os metadados gravados no objeto S3.

    sha256:
        checksum físico do arquivo RAW.

    content_sha256:
        checksum lógico do conteúdo da fonte,
        quando disponível.
    """

    metadata = {
        "sha256": raw_sha256,
    }

    if content_sha256 is not None:
        metadata["content_sha256"] = (
            content_sha256
        )

    return metadata


def upload_file(
    local_path: str | Path,
    bucket_name: str,
    s3_key: str | None = None,
    content_sha256: str | None = None,
    force: bool = False,
) -> str:
    """
    Faz upload de um arquivo local para o S3.

    O SHA-256 físico do arquivo é sempre
    armazenado nos metadados.

    Opcionalmente, também pode ser informado
    um content_sha256 representando o conteúdo
    lógico da fonte.

    Regras:

    1. Objeto inexistente:
       realiza upload.

    2. SHA físico idêntico:
       ignora o upload.

    3. SHA físico diferente, mas
       content_sha256 idêntico:
       considera reempacotamento sem alteração
       lógica e ignora o upload.

    4. SHA físico diferente e conteúdo lógico
       diferente:
       bloqueia por padrão.

    5. Não é possível comprovar equivalência
       lógica:
       bloqueia por padrão.

    6. force=True:
       permite explicitamente nova versão.
    """

    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(
            f"Arquivo local não encontrado: {local_path}"
        )

    if not local_path.is_file():
        raise ValueError(
            f"O caminho informado não é um arquivo: {local_path}"
        )

    if s3_key is None:
        s3_key = build_s3_key_from_raw_path(
            local_path
        )

    s3_uri = (
        f"s3://{bucket_name}/{s3_key}"
    )

    local_raw_sha256 = calculate_sha256(
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

        remote_raw_sha256 = (
            remote_metadata
            .get("sha256")
        )

        remote_content_sha256 = (
            remote_metadata
            .get("content_sha256")
        )

        if remote_raw_sha256 == local_raw_sha256:
            if force:
                print(
                    "Force habilitado | "
                    "SHA-256 físico idêntico | "
                    "nova versão será criada | "
                    f"{s3_uri}"
                )

            else:
                print(
                    "Upload S3 ignorado | "
                    "SHA-256 físico idêntico | "
                    f"{s3_uri}"
                )

                return s3_uri

        elif (
            content_sha256 is not None
            and remote_content_sha256 is not None
            and (
                remote_content_sha256
                == content_sha256
            )
        ):
            if force:
                print(
                    "Force habilitado | "
                    "RAW físico diferente, "
                    "conteúdo lógico idêntico | "
                    "nova versão será criada | "
                    f"{s3_uri}"
                )

            else:
                print(
                    "Upload S3 ignorado | "
                    "reempacotamento detectado | "
                    "RAW físico diferente, "
                    "conteúdo lógico idêntico | "
                    f"{s3_uri}"
                )

                return s3_uri

        elif not force:
            remote_raw_display = (
                remote_raw_sha256
                if remote_raw_sha256 is not None
                else "ausente"
            )

            remote_content_display = (
                remote_content_sha256
                if remote_content_sha256 is not None
                else "ausente"
            )

            local_content_display = (
                content_sha256
                if content_sha256 is not None
                else "ausente"
            )

            raise RuntimeError(
                "Upload S3 bloqueado | "
                "não foi possível comprovar "
                "equivalência do objeto | "
                f"{s3_uri} | "
                f"local_raw_sha256="
                f"{local_raw_sha256} | "
                f"remote_raw_sha256="
                f"{remote_raw_display} | "
                f"local_content_sha256="
                f"{local_content_display} | "
                f"remote_content_sha256="
                f"{remote_content_display} | "
                "use force=True somente após "
                "validação explícita"
            )

        else:
            remote_raw_display = (
                remote_raw_sha256
                if remote_raw_sha256 is not None
                else "ausente"
            )

            remote_content_display = (
                remote_content_sha256
                if remote_content_sha256 is not None
                else "ausente"
            )

            local_content_display = (
                content_sha256
                if content_sha256 is not None
                else "ausente"
            )

            print(
                "Force habilitado | "
                "divergência aceita explicitamente | "
                f"{s3_uri} | "
                f"local_raw_sha256="
                f"{local_raw_sha256} | "
                f"remote_raw_sha256="
                f"{remote_raw_display} | "
                f"local_content_sha256="
                f"{local_content_display} | "
                f"remote_content_sha256="
                f"{remote_content_display}"
            )

    upload_metadata = build_upload_metadata(
        raw_sha256=local_raw_sha256,
        content_sha256=content_sha256,
    )

    s3_client = boto3.client("s3")

    s3_client.upload_file(
        Filename=str(local_path),
        Bucket=bucket_name,
        Key=s3_key,
        ExtraArgs={
            "Metadata": upload_metadata,
        },
    )

    print(
        "Upload S3 concluído | "
        f"{s3_uri} | "
        f"sha256={local_raw_sha256}"
    )

    if content_sha256 is not None:
        print(
            "Conteúdo lógico registrado | "
            f"content_sha256={content_sha256}"
        )

    return s3_uri