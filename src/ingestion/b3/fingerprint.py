from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import BinaryIO


B3_INSTRUMENT_REPORT_PREFIX = "BVBG.028.02"

HASH_CHUNK_SIZE = 1024 * 1024


def calculate_sha256(
    content: bytes,
) -> str:
    """
    Calcula o SHA-256 de um conteúdo em bytes.
    """

    return hashlib.sha256(
        content
    ).hexdigest()


def calculate_stream_sha256(
    stream: BinaryIO,
) -> str:
    """
    Calcula SHA-256 de forma incremental.

    O conteúdo é lido em blocos para evitar
    carregar arquivos grandes inteiros
    na memória.
    """

    sha256 = hashlib.sha256()

    while True:
        chunk = stream.read(
            HASH_CHUNK_SIZE
        )

        if not chunk:
            break

        sha256.update(
            chunk
        )

    return sha256.hexdigest()


def calculate_b3_content_sha256(
    local_path: str | Path,
) -> str:
    """
    Calcula o checksum lógico do RAW da B3.

    Estrutura esperada:

        ZIP externo
            ->
        ZIP interno SPREYYMMDD.zip
            ->
        XML

    Quando existir apenas um XML, o checksum
    lógico será o SHA-256 desse XML.

    Caso existam múltiplos XMLs, é calculado
    um checksum determinístico sobre o conjunto
    ordenado dos XMLs.
    """

    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(
            f"Arquivo B3 não encontrado: {local_path}"
        )

    if not local_path.is_file():
        raise ValueError(
            "O caminho informado não é um arquivo: "
            f"{local_path}"
        )

    outer_content = local_path.read_bytes()

    try:
        with zipfile.ZipFile(
            io.BytesIO(outer_content)
        ) as outer_zip:
            inner_zip_members = [
                member
                for member in outer_zip.namelist()
                if (
                    not member.endswith("/")
                    and member.lower().endswith(".zip")
                )
            ]

            if not inner_zip_members:
                raise ValueError(
                    "ZIP externo da B3 não contém "
                    "ZIP interno."
                )

            if len(inner_zip_members) != 1:
                raise ValueError(
                    "Estrutura inesperada da B3: "
                    "esperado exatamente um ZIP interno. "
                    f"Encontrados: {len(inner_zip_members)}."
                )

            inner_content = outer_zip.read(
                inner_zip_members[0]
            )

    except zipfile.BadZipFile as error:
        raise ValueError(
            "ZIP externo da B3 inválido."
        ) from error

    try:
        with zipfile.ZipFile(
            io.BytesIO(inner_content)
        ) as inner_zip:
            xml_members = sorted(
                member
                for member in inner_zip.namelist()
                if (
                    not member.endswith("/")
                    and member.lower().endswith(".xml")
                )
            )

            if not xml_members:
                raise ValueError(
                    "ZIP interno da B3 não contém XML."
                )

            if len(xml_members) == 1:
                xml_content = inner_zip.read(
                    xml_members[0]
                )

                if not xml_content:
                    raise ValueError(
                        "XML da B3 está vazio."
                    )

                return calculate_sha256(
                    xml_content
                )

            combined_sha256 = hashlib.sha256()

            for xml_member in xml_members:
                xml_content = inner_zip.read(
                    xml_member
                )

                if not xml_content:
                    raise ValueError(
                        "XML vazio encontrado na B3: "
                        f"{xml_member}"
                    )

                xml_sha256 = calculate_sha256(
                    xml_content
                )

                combined_sha256.update(
                    xml_sha256.encode("ascii")
                )

            return combined_sha256.hexdigest()

    except zipfile.BadZipFile as error:
        raise ValueError(
            "ZIP interno da B3 inválido."
        ) from error


def calculate_b3_instruments_content_sha256(
    local_path: str | Path,
) -> str:
    """
    Calcula o checksum lógico do
    B3 Instrument Report.

    Estrutura esperada:

        ZIP externo pesquisa-pregao.zip
            ->
        ZIP interno INYYMMDD.zip
            ->
        um ou mais XMLs BVBG.028.02

    Regra idêntica à utilizada pela Silver:

    1. localizar o ZIP interno com prefixo IN;
    2. localizar os XMLs BVBG.028.02;
    3. ordenar os XMLs pelo nome;
    4. selecionar o último snapshot;
    5. calcular SHA-256 desse XML.

    O XML selecionado é processado em streaming
    para evitar carregá-lo inteiro na memória.
    """

    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(
            "Arquivo B3 Instruments não encontrado: "
            f"{local_path}"
        )

    if not local_path.is_file():
        raise ValueError(
            "O caminho informado não é um arquivo: "
            f"{local_path}"
        )

    try:
        with zipfile.ZipFile(
            local_path
        ) as outer_zip:
            instrument_zip_members = [
                member
                for member in outer_zip.namelist()
                if (
                    not member.endswith("/")
                    and member.lower().endswith(".zip")
                    and Path(member)
                    .name
                    .upper()
                    .startswith("IN")
                )
            ]

            if not instrument_zip_members:
                raise ValueError(
                    "ZIP externo da B3 não contém "
                    "Instrument Report com prefixo IN."
                )

            selected_inner_zip = (
                instrument_zip_members[0]
            )

            inner_content = outer_zip.read(
                selected_inner_zip
            )

    except zipfile.BadZipFile as error:
        raise ValueError(
            "ZIP externo de B3 Instruments inválido."
        ) from error

    try:
        with zipfile.ZipFile(
            io.BytesIO(inner_content)
        ) as inner_zip:
            instrument_xml_members = sorted(
                member
                for member in inner_zip.namelist()
                if (
                    not member.endswith("/")
                    and member.lower().endswith(".xml")
                    and Path(member)
                    .name
                    .upper()
                    .startswith(
                        B3_INSTRUMENT_REPORT_PREFIX
                    )
                )
            )

            if not instrument_xml_members:
                raise ValueError(
                    "ZIP interno de B3 Instruments "
                    "não contém XML BVBG.028.02."
                )

            selected_xml = (
                instrument_xml_members[-1]
            )

            xml_info = inner_zip.getinfo(
                selected_xml
            )

            if xml_info.file_size == 0:
                raise ValueError(
                    "Snapshot XML de B3 Instruments "
                    f"está vazio: {selected_xml}"
                )

            with inner_zip.open(
                selected_xml,
                mode="r",
            ) as xml_stream:
                return calculate_stream_sha256(
                    xml_stream
                )

    except zipfile.BadZipFile as error:
        raise ValueError(
            "ZIP interno de B3 Instruments inválido."
        ) from error