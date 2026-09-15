from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path


def calculate_sha256(
    content: bytes,
) -> str:
    """
    Calcula o SHA-256 de um conteúdo em bytes.
    """

    return hashlib.sha256(
        content
    ).hexdigest()


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