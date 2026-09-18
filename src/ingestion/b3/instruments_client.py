from __future__ import annotations

import zipfile
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import requests

from src.ingestion.b3.client import create_session


B3_DOWNLOAD_URL = (
    "https://www.b3.com.br/"
    "pesquisapregao/download"
)

RAW_BASE_DIR = Path(
    "data/raw/b3-instruments"
)

LOCAL_FILENAME = "pesquisa-pregao.zip"

DEFAULT_LOOKBACK_DAYS = 10


def build_instrument_filename(
    reference_date: date,
) -> str:
    """
    Constrói o nome do Instrument Report esperado pela B3.

    Exemplo:
        2026-09-11
        ->
        IN260911.zip
    """

    return (
        "IN"
        f"{reference_date:%y%m%d}"
        ".zip"
    )


def build_download_url(
    reference_date: date,
) -> str:
    """
    Constrói a URL do Instrument Report.
    """

    filename = build_instrument_filename(
        reference_date
    )

    return (
        f"{B3_DOWNLOAD_URL}"
        f"?filelist={filename}"
    )


def build_destination_path(
    capture_date: date,
) -> Path:
    """
    Caminho RAW local.

    A partição representa a data de captura,
    e não a data de referência interna
    do relatório da B3.
    """

    return (
        RAW_BASE_DIR
        / f"year={capture_date.year}"
        / f"month={capture_date.month:02d}"
        / f"day={capture_date.day:02d}"
        / LOCAL_FILENAME
    )


def validate_instrument_archive(
    content: bytes,
    expected_reference_date: date,
) -> tuple[bool, str]:
    """
    Valida estruturalmente o download do
    B3 Instrument Report.

    Contrato esperado:

        ZIP externo
            -> INYYMMDD.zip
                -> um ou mais XMLs

    O ZIP interno deve corresponder à data
    solicitada.
    """

    expected_inner_zip = (
        build_instrument_filename(
            expected_reference_date
        )
    )

    try:
        outer_buffer = BytesIO(content)

        with zipfile.ZipFile(
            outer_buffer
        ) as outer_zip:
            outer_members = [
                member
                for member in outer_zip.namelist()
                if not member.endswith("/")
            ]

            matching_inner = [
                member
                for member in outer_members
                if Path(member).name.upper()
                == expected_inner_zip.upper()
            ]

            if len(matching_inner) != 1:
                return (
                    False,
                    (
                        "ZIP externo não contém exatamente "
                        f"um {expected_inner_zip}. "
                        f"Encontrados: {outer_members}"
                    ),
                )

            inner_content = outer_zip.read(
                matching_inner[0]
            )

        with zipfile.ZipFile(
            BytesIO(inner_content)
        ) as inner_zip:
            xml_members = [
                member
                for member in inner_zip.namelist()
                if (
                    not member.endswith("/")
                    and member.lower().endswith(".xml")
                )
            ]

            if not xml_members:
                return (
                    False,
                    (
                        "Instrument Report sem XML "
                        "no ZIP interno."
                    ),
                )

    except zipfile.BadZipFile as error:
        return (
            False,
            f"Arquivo ZIP inválido: {error}",
        )

    return (
        True,
        (
            f"Instrument Report válido | "
            f"inner_zip={expected_inner_zip}"
        ),
    )


def download_instrument_report(
    reference_date: date,
    capture_date: date,
    session: requests.Session,
    overwrite: bool = False,
) -> Path | None:
    """
    Baixa um Instrument Report específico.

    Retorna:
        Path -> RAW estruturalmente válido
        None -> relatório indisponível/inválido
    """

    destination = build_destination_path(
        capture_date
    )

    requested_filename = (
        build_instrument_filename(
            reference_date
        )
    )

    url = build_download_url(
        reference_date
    )

    if (
        destination.exists()
        and not overwrite
    ):
        existing_content = destination.read_bytes()

        (
            existing_is_valid,
            existing_reason,
        ) = validate_instrument_archive(
            content=existing_content,
            expected_reference_date=reference_date,
        )

        if existing_is_valid:
            print(
                "B3 Instruments | "
                "arquivo local já existente e válido | "
                f"{destination}"
            )

            return destination

        print(
            "B3 Instruments | "
            "arquivo local existente inválido | "
            f"{existing_reason} | "
            "novo download será realizado"
        )

    print(
        "B3 Instruments | "
        f"reference_date={reference_date} | "
        f"arquivo={requested_filename}"
    )

    print(
        "B3 Instruments | "
        f"URL={url}"
    )

    try:
        response = session.get(
            url,
            timeout=60,
        )

    except requests.RequestException as error:
        print(
            "B3 Instruments | "
            f"{reference_date} | "
            f"erro HTTP | {error}"
        )

        return None

    if response.status_code == 404:
        print(
            "B3 Instruments | "
            f"{reference_date} | "
            "relatório indisponível"
        )

        return None

    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        print(
            "B3 Instruments | "
            f"{reference_date} | "
            f"HTTP {response.status_code} | "
            f"{error}"
        )

        return None

    content = response.content

    (
        is_valid,
        validation_reason,
    ) = validate_instrument_archive(
        content=content,
        expected_reference_date=reference_date,
    )

    if not is_valid:
        print(
            "B3 Instruments | "
            f"{reference_date} | "
            "arquivo inválido | "
            f"{validation_reason}"
        )

        return None

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(content)

    print(
        "B3 Instruments | SUCCESS | "
        f"reference_date={reference_date} | "
        f"capture_date={capture_date} | "
        f"{requested_filename} | "
        f"{len(content):,} bytes"
    )

    return destination


def download_latest_instrument_report(
    capture_date: date | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    overwrite: bool = False,
) -> tuple[Path, date]:
    """
    Procura o Instrument Report mais recente
    disponível na B3.

    A captura é particionada pela data atual,
    enquanto a data de referência encontrada
    é retornada separadamente.
    """

    if lookback_days < 1:
        raise ValueError(
            "lookback_days deve ser >= 1."
        )

    if capture_date is None:
        capture_date = date.today()

    session = create_session()

    for offset in range(lookback_days):
        candidate_date = (
            capture_date
            - timedelta(days=offset)
        )

        if candidate_date.weekday() >= 5:
            continue

        local_path = download_instrument_report(
            reference_date=candidate_date,
            capture_date=capture_date,
            session=session,
            overwrite=overwrite,
        )

        if local_path is not None:
            print(
                "B3 Instruments | "
                "snapshot mais recente encontrado | "
                f"reference_date={candidate_date}"
            )

            return (
                local_path,
                candidate_date,
            )

    raise RuntimeError(
        "Nenhum B3 Instrument Report válido "
        f"encontrado nos últimos {lookback_days} dias."
    )