from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
import zipfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


B3_DOWNLOAD_URL = (
    "https://www.b3.com.br/"
    "pesquisapregao/download"
)

RAW_BASE_DIR = Path(
    "data/raw/b3"
)

DEFAULT_DAYS = 10

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
}


def create_session() -> requests.Session:
    """
    Cria uma sessão HTTP com retry para
    erros transitórios.
    """

    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=[
            "GET",
        ],
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy
    )

    session = requests.Session()

    session.headers.update(
        DEFAULT_HEADERS
    )

    session.mount(
        "https://",
        adapter,
    )

    return session


def parse_date(
    value: str,
) -> date:
    """
    Converte YYYY-MM-DD para date.
    """

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()

    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Data inválida. "
            "Use o formato YYYY-MM-DD."
        ) from error


def get_previous_business_day(
    reference_date: date | None = None,
) -> date:
    """
    Retorna o último dia útil candidato.

    Esta função considera apenas
    sábado e domingo.

    Feriados e datas sem pregão da B3
    são tratados posteriormente pela
    validação do arquivo.
    """

    if reference_date is None:
        reference_date = date.today()

    candidate = (
        reference_date
        - timedelta(
            days=1
        )
    )

    while candidate.weekday() >= 5:
        candidate -= timedelta(
            days=1
        )

    return candidate


def build_b3_filename(
    trade_date: date,
) -> str:
    """
    Constrói o nome oficial esperado pela B3.

    Exemplo:
        2026-08-27
        ->
        SPRE260827.zip
    """

    return (
        "SPRE"
        f"{trade_date:%y%m%d}"
        ".zip"
    )


def build_download_url(
    trade_date: date,
) -> str:
    """
    Constrói URL completa de download.
    """

    filename = build_b3_filename(
        trade_date
    )

    return (
        f"{B3_DOWNLOAD_URL}"
        f"?filelist={filename}"
    )


def build_local_filename(
    trade_date: date,
) -> str:
    """
    Nome local do RAW.

    O arquivo recebido da B3 é um ZIP
    externo que normalmente contém outro
    ZIP, por isso usamos um nome próprio
    para o RAW externo.
    """

    return (
        "b3_download_"
        f"{trade_date:%Y%m%d}"
        ".zip"
    )


def build_destination_path(
    trade_date: date,
) -> Path:
    """
    Cria caminho RAW particionado.
    """

    return (
        RAW_BASE_DIR
        / f"year={trade_date.year}"
        / f"month={trade_date.month:02d}"
        / f"day={trade_date.day:02d}"
        / build_local_filename(
            trade_date
        )
    )


def validate_b3_archive(
    content: bytes,
    trade_date: date,
) -> tuple[bool, str]:
    """
    Valida estruturalmente o arquivo RAW da B3.

    Contrato esperado:

        ZIP externo
            ->
        SPREYYMMDD.zip
            ->
        pelo menos um XML não vazio

    Retorna:
        (True, mensagem)
        (False, motivo)
    """

    if not content:
        return (
            False,
            "arquivo vazio",
        )

    if not content.startswith(
        b"PK"
    ):
        return (
            False,
            "não possui assinatura ZIP PK",
        )

    expected_inner_zip = (
        build_b3_filename(
            trade_date
        )
    )

    try:
        outer_buffer = BytesIO(
            content
        )

        with zipfile.ZipFile(
            outer_buffer
        ) as outer_zip:

            outer_members = [
                member
                for member in outer_zip.namelist()
                if not member.endswith("/")
            ]

            if not outer_members:
                return (
                    False,
                    "ZIP externo vazio",
                )

            matching_members = [
                member
                for member in outer_members
                if Path(member).name.lower()
                == expected_inner_zip.lower()
            ]

            if not matching_members:
                return (
                    False,
                    (
                        "ZIP interno esperado "
                        f"{expected_inner_zip} "
                        "não encontrado"
                    ),
                )

            inner_member = (
                matching_members[0]
            )

            inner_content = (
                outer_zip.read(
                    inner_member
                )
            )

    except (
        zipfile.BadZipFile,
        KeyError,
        OSError,
    ) as error:
        return (
            False,
            (
                "ZIP externo inválido: "
                f"{error}"
            ),
        )

    if not inner_content:
        return (
            False,
            "ZIP interno vazio",
        )

    try:
        inner_buffer = BytesIO(
            inner_content
        )

        with zipfile.ZipFile(
            inner_buffer
        ) as inner_zip:

            inner_members = [
                member
                for member in inner_zip.namelist()
                if not member.endswith("/")
            ]

            if not inner_members:
                return (
                    False,
                    "ZIP interno sem arquivos",
                )

            xml_members = [
                member
                for member in inner_members
                if member.lower().endswith(
                    ".xml"
                )
            ]

            if not xml_members:
                return (
                    False,
                    "ZIP interno sem XML",
                )

            non_empty_xml_found = False

            for xml_member in xml_members:
                info = inner_zip.getinfo(
                    xml_member
                )

                if info.file_size > 0:
                    non_empty_xml_found = True
                    break

            if not non_empty_xml_found:
                return (
                    False,
                    "XML da B3 vazio",
                )

    except (
        zipfile.BadZipFile,
        KeyError,
        OSError,
    ) as error:
        return (
            False,
            (
                "ZIP interno inválido: "
                f"{error}"
            ),
        )

    return (
        True,
        "estrutura B3 válida",
    )


def validate_existing_raw(
    path: Path,
    trade_date: date,
) -> tuple[bool, str]:
    """
    Valida um RAW já armazenado localmente.
    """

    if not path.exists():
        return (
            False,
            "arquivo inexistente",
        )

    if not path.is_file():
        return (
            False,
            "caminho não é arquivo",
        )

    try:
        content = path.read_bytes()

    except OSError as error:
        return (
            False,
            (
                "erro ao ler RAW: "
                f"{error}"
            ),
        )

    return validate_b3_archive(
        content=content,
        trade_date=trade_date,
    )


def remove_invalid_raw(
    path: Path,
) -> None:
    """
    Remove RAW inválido encontrado
    durante a validação.
    """

    try:
        path.unlink(
            missing_ok=True
        )

    except OSError as error:
        raise RuntimeError(
            "Não foi possível remover "
            f"RAW inválido: {path}"
        ) from error

    # Remove diretórios de partição vazios,
    # começando pelo day=...
    parent = path.parent

    while (
        parent != RAW_BASE_DIR
        and RAW_BASE_DIR in parent.parents
    ):
        try:
            parent.rmdir()
        except OSError:
            break

        parent = parent.parent


def download_b3_file(
    trade_date: date,
    session: requests.Session,
    overwrite: bool = False,
) -> Path | None:
    """
    Tenta obter um pregão específico.

    Retorna:
        Path -> RAW B3 estruturalmente válido
        None -> pregão indisponível/inválido

    Arquivos existentes também são
    validados antes de serem contabilizados.
    """

    destination = (
        build_destination_path(
            trade_date
        )
    )

    requested_filename = (
        build_b3_filename(
            trade_date
        )
    )

    url = build_download_url(
        trade_date
    )

    if (
        destination.exists()
        and not overwrite
    ):
        (
            existing_is_valid,
            existing_reason,
        ) = validate_existing_raw(
            path=destination,
            trade_date=trade_date,
        )

        if existing_is_valid:
            print(
                f"{trade_date} | "
                "já existe e é válido | "
                f"{destination}"
            )

            return destination

        print(
            f"{trade_date} | "
            "RAW existente inválido | "
            f"{existing_reason}"
        )

        print(
            f"{trade_date} | "
            "removendo RAW inválido | "
            f"{destination}"
        )

        remove_invalid_raw(
            destination
        )

    try:
        response = session.get(
            url,
            timeout=60,
        )

    except requests.RequestException as error:
        print(
            f"{trade_date} | "
            f"erro HTTP | "
            f"{error}"
        )

        return None

    if response.status_code == 404:
        print(
            f"{trade_date} | "
            "sem pregão"
        )

        return None

    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        print(
            f"{trade_date} | "
            "erro HTTP "
            f"{response.status_code} | "
            f"{error}"
        )

        return None

    content = response.content

    (
        is_valid,
        validation_reason,
    ) = validate_b3_archive(
        content=content,
        trade_date=trade_date,
    )

    if not is_valid:
        print(
            f"{trade_date} | "
            "sem pregão / arquivo inválido | "
            f"{validation_reason} | "
            f"{len(content):,} bytes"
        )

        return None

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(
        content
    )

    print(
        f"{trade_date} | "
        "SUCCESS | "
        f"{requested_filename} | "
        f"{len(content):,} bytes"
    )

    return destination


def download_single_date(
    trade_date: date,
    overwrite: bool = False,
) -> None:
    """
    Modo para uma data específica.
    """

    session = create_session()

    requested_filename = (
        build_b3_filename(
            trade_date
        )
    )

    url = build_download_url(
        trade_date
    )

    print(
        "Data do pregão: "
        f"{trade_date}"
    )

    print(
        "Arquivo solicitado à B3: "
        f"{requested_filename}"
    )

    print(
        f"URL: {url}"
    )

    result = download_b3_file(
        trade_date=trade_date,
        session=session,
        overwrite=overwrite,
    )

    if result is None:
        raise RuntimeError(
            "Não foi possível obter um "
            "arquivo B3 válido para "
            f"{trade_date}."
        )

    print(
        "\nDownload concluído."
    )

    print(
        "Arquivo salvo em: "
        f"{result}"
    )

    print(
        "Tamanho: "
        f"{result.stat().st_size:,} bytes"
    )


def download_latest_trading_days(
    days: int,
    reference_date: date | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """
    Obtém os N pregões B3 válidos mais recentes.

    Uma data só é contabilizada quando
    passa pelo contrato estrutural:

        ZIP externo
        -> SPREYYMMDD.zip
        -> XML não vazio

    Isso permite lidar naturalmente com:
    - fins de semana;
    - feriados;
    - datas sem relatório;
    - ZIP vazio;
    - RAW antigo inválido.
    """

    if days <= 0:
        raise ValueError(
            "--days deve ser maior que zero."
        )

    if reference_date is None:
        candidate_date = (
            get_previous_business_day()
        )

    else:
        candidate_date = (
            reference_date
        )

    session = create_session()

    valid_files: list[
        Path
    ] = []

    checked_dates = 0

    # Folga ampla para finais de semana,
    # feriados e datas sem arquivo.
    max_dates_to_check = (
        days * 4
        + 30
    )

    print(
        "Buscando os últimos "
        f"{days} pregões B3 válidos..."
    )

    print(
        "Data inicial da busca: "
        f"{candidate_date}"
    )

    print()

    while (
        len(valid_files)
        < days
        and checked_dates
        < max_dates_to_check
    ):
        checked_dates += 1

        # Não faz requisição aos
        # finais de semana.
        if candidate_date.weekday() < 5:

            result = download_b3_file(
                trade_date=candidate_date,
                session=session,
                overwrite=overwrite,
            )

            if result is not None:
                valid_files.append(
                    result
                )

        candidate_date -= timedelta(
            days=1
        )

    if len(valid_files) < days:
        raise RuntimeError(
            "Não foi possível encontrar "
            f"{days} pregões B3 válidos. "
            "Encontrados: "
            f"{len(valid_files)}. "
            "Datas verificadas: "
            f"{checked_dates}."
        )

    return valid_files


def print_batch_summary(
    files: list[Path],
) -> None:
    """
    Resumo do modo --days.

    A lista recebida contém somente
    arquivos que passaram pela validação
    estrutural B3.
    """

    print(
        "\n======================================"
    )

    print(
        "Resumo B3 RAW"
    )

    print(
        "======================================"
    )

    files = sorted(
        files
    )

    for path in files:
        print(
            f"{path} | "
            f"{path.stat().st_size:,} bytes"
        )

    print(
        "\nPregões B3 válidos: "
        f"{len(files):,}"
    )

    if files:
        print(
            "Primeiro RAW válido: "
            f"{files[0]}"
        )

        print(
            "Último RAW válido: "
            f"{files[-1]}"
        )

    print(
        "\nDownload B3 "
        "concluído com sucesso."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download e validação do relatório "
            "Simplified Price Report da B3."
        )
    )

    mode = (
        parser.add_mutually_exclusive_group()
    )

    mode.add_argument(
        "--date",
        type=parse_date,
        help=(
            "Baixa uma data específica "
            "no formato YYYY-MM-DD."
        ),
    )

    mode.add_argument(
        "--days",
        type=int,
        help=(
            "Busca automaticamente os N "
            "pregões B3 válidos mais recentes."
        ),
    )

    parser.add_argument(
        "--reference-date",
        type=parse_date,
        help=(
            "Data inicial opcional para "
            "o modo --days. "
            "Formato YYYY-MM-DD."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Baixa novamente arquivos "
            "que já existem no RAW."
        ),
    )

    args = parser.parse_args()

    if args.date is not None:

        download_single_date(
            trade_date=args.date,
            overwrite=args.overwrite,
        )

        return

    days = (
        args.days
        if args.days is not None
        else DEFAULT_DAYS
    )

    files = download_latest_trading_days(
        days=days,
        reference_date=(
            args.reference_date
        ),
        overwrite=args.overwrite,
    )

    print_batch_summary(
        files
    )


if __name__ == "__main__":
    main()