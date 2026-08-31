from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

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

    Feriados da B3 são tratados
    posteriormente pela tentativa
    de download.
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

    Evitamos usar SPRE...zip localmente
    porque o arquivo baixado é um ZIP
    externo que contém outro ZIP interno.
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


def is_valid_zip_response(
    content: bytes,
) -> bool:
    """
    Faz uma validação simples para evitar
    persistir HTML ou resposta inválida
    como se fosse ZIP.

    Arquivos ZIP começam normalmente com
    assinatura PK.
    """

    if not content:
        return False

    return content.startswith(
        b"PK"
    )


def download_b3_file(
    trade_date: date,
    session: requests.Session,
    overwrite: bool = False,
) -> Path | None:
    """
    Tenta baixar um pregão específico.

    Retorna:
        Path -> download válido
        None -> pregão indisponível

    Não derruba o modo em lote quando
    um dia não possui arquivo válido.
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
        print(
            f"{trade_date} | "
            f"já existe | "
            f"{destination}"
        )

        return destination

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
            f"sem pregão"
        )

        return None

    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        print(
            f"{trade_date} | "
            f"erro HTTP "
            f"{response.status_code} | "
            f"{error}"
        )

        return None

    content = response.content

    if not is_valid_zip_response(
        content
    ):
        print(
            f"{trade_date} | "
            f"arquivo inválido ou indisponível"
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
        f"SUCCESS | "
        f"{requested_filename} | "
        f"{len(content):,} bytes"
    )

    return destination


def download_single_date(
    trade_date: date,
    overwrite: bool = False,
) -> None:
    """
    Modo compatível com execução por
    uma data específica.
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
        f"Data do pregão: "
        f"{trade_date}"
    )

    print(
        f"Arquivo solicitado à B3: "
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
            f"Não foi possível baixar "
            f"o pregão {trade_date}."
        )

    print(
        "\nDownload concluído."
    )

    print(
        f"Arquivo salvo em: "
        f"{result}"
    )

    print(
        f"Tamanho: "
        f"{result.stat().st_size:,} bytes"
    )


def download_latest_trading_days(
    days: int,
    reference_date: date | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """
    Obtém os N pregões mais recentes.

    A função percorre o calendário para trás
    e só contabiliza datas cujo arquivo
    B3 existe ou já está armazenado no RAW.

    Isso permite lidar naturalmente com:
    - fins de semana;
    - feriados;
    - datas sem arquivo.
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

    downloaded_files: list[
        Path
    ] = []

    checked_dates = 0

    # Proteção para impedir loop infinito
    # em caso de indisponibilidade prolongada.
    max_dates_to_check = (
        days * 4
        + 30
    )

    print(
        f"Buscando os últimos "
        f"{days} pregões B3..."
    )

    print(
        f"Data inicial da busca: "
        f"{candidate_date}"
    )

    print()

    while (
        len(downloaded_files)
        < days
        and checked_dates
        < max_dates_to_check
    ):
        checked_dates += 1

        # Evita requisição aos fins de semana.
        if candidate_date.weekday() < 5:

            result = download_b3_file(
                trade_date=candidate_date,
                session=session,
                overwrite=overwrite,
            )

            if result is not None:
                downloaded_files.append(
                    result
                )

        candidate_date -= timedelta(
            days=1
        )

    if len(downloaded_files) < days:
        raise RuntimeError(
            "Não foi possível encontrar "
            f"{days} pregões válidos. "
            f"Encontrados: "
            f"{len(downloaded_files)}."
        )

    return downloaded_files


def print_batch_summary(
    files: list[Path],
) -> None:
    """
    Resumo do modo --days.
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
        f"\nPregões disponíveis: "
        f"{len(files):,}"
    )

    print(
        "\nDownload B3 "
        "concluído com sucesso."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download do relatório diário "
            "Simplified Price Report da B3."
        )
    )

    mode = parser.add_mutually_exclusive_group()

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
            "pregões B3 mais recentes."
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