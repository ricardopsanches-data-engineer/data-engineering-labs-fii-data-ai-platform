from __future__ import annotations

import argparse
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from client import (
    create_session,
    download_fund_page,
    download_funds_list_page,
)


TICKER_PATTERN = re.compile(
    r"^[A-Z0-9]{4,8}\d{1,2}[A-Z]?$"
)


def normalize_cnpj(
    cnpj: str | None,
) -> str | None:
    """
    Remove a máscara do CNPJ.

    Exemplo:
        36.771.692/0001-19
        ->
        36771692000119
    """

    if not cnpj:
        return None

    digits = re.sub(
        r"\D",
        "",
        cnpj,
    )

    if len(digits) != 14:
        return None

    return digits


def extract_meta_block(
    html: str,
) -> str:
    """
    Localiza o bloco 'meta' dentro do objeto
    dataLayer_content presente no HTML.
    """

    start_pattern = r'"meta"\s*:\s*\{'

    match = re.search(
        start_pattern,
        html,
        flags=re.IGNORECASE,
    )

    if match is None:
        raise ValueError(
            "Bloco 'meta' não encontrado no HTML."
        )

    start_position = match.end()

    brace_level = 1
    position = start_position

    in_string = False
    escaped = False

    while position < len(html):
        character = html[position]

        if escaped:
            escaped = False

        elif character == "\\":
            escaped = True

        elif character == '"':
            in_string = not in_string

        elif not in_string:
            if character == "{":
                brace_level += 1

            elif character == "}":
                brace_level -= 1

                if brace_level == 0:
                    return html[
                        start_position:position
                    ]

        position += 1

    raise ValueError(
        "Não foi possível determinar "
        "o final do bloco 'meta'."
    )


def extract_field(
    content: str,
    field_name: str,
) -> str | None:
    """
    Extrai um campo textual do bloco meta.
    """

    pattern = (
        rf'"{re.escape(field_name)}"'
        rf'\s*:\s*"([^"]*)"'
    )

    match = re.search(
        pattern,
        content,
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    value = match.group(1)

    value = value.replace(
        r"\/",
        "/",
    )

    return value.strip()


def parse_fund_page(
    html: str,
) -> dict[str, str | None]:
    """
    Extrai ticker, CNPJ, nome e status
    da página individual de um ativo.
    """

    meta_block = extract_meta_block(
        html
    )

    ticker = extract_field(
        meta_block,
        "codigo",
    )

    fund_name = extract_field(
        meta_block,
        "name",
    )

    cnpj_raw = extract_field(
        meta_block,
        "cnpj",
    )

    category_status = extract_field(
        meta_block,
        "categorystatus",
    )

    cnpj = normalize_cnpj(
        cnpj_raw
    )

    if ticker is None:
        raise ValueError(
            "Ticker não encontrado."
        )

    if cnpj is None:
        raise ValueError(
            f"CNPJ não encontrado para {ticker}."
        )

    return {
        "ticker": ticker.upper(),
        "cnpj": cnpj,
        "fund_name": fund_name,
        "category_status": category_status,
        "source": "fundsexplorer",
    }


def extract_tickers_from_list_page(
    html: str,
) -> list[str]:
    """
    Extrai os tickers existentes nos links
    da página /funds.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    tickers: set[str] = set()

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = anchor.get(
            "href"
        )

        if not href:
            continue

        match = re.search(
            r"/funds/([a-zA-Z0-9]+)",
            href,
        )

        if match is None:
            continue

        ticker = (
            match
            .group(1)
            .upper()
            .strip()
        )

        if TICKER_PATTERN.match(
            ticker
        ):
            tickers.add(
                ticker
            )

    return sorted(
        tickers
    )


def collect_fund_details(
    tickers: list[str],
    delay_seconds: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Consulta as páginas individuais.

    Retorna:
    - registros extraídos com sucesso;
    - erros encontrados durante a coleta.
    """

    session = create_session()

    records: list[
        dict[str, str | None]
    ] = []

    errors: list[
        dict[str, str]
    ] = []

    total = len(
        tickers
    )

    ingestion_timestamp = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    for index, ticker in enumerate(
        tickers,
        start=1,
    ):
        try:
            html = download_fund_page(
                ticker=ticker,
                session=session,
                delay_seconds=delay_seconds,
            )

            record = parse_fund_page(
                html
            )

            record[
                "ingestion_timestamp"
            ] = ingestion_timestamp

            records.append(
                record
            )

            print(
                f"[{index}/{total}] "
                f"{ticker}: OK"
            )

        except Exception as error:
            print(
                f"[{index}/{total}] "
                f"{ticker}: ERROR"
            )

            errors.append(
                {
                    "ticker": ticker,
                    "error": str(error),
                    "ingestion_timestamp": (
                        ingestion_timestamp
                    ),
                }
            )

    funds_dataframe = pd.DataFrame(
        records
    )

    errors_dataframe = pd.DataFrame(
        errors
    )

    return (
        funds_dataframe,
        errors_dataframe,
    )


def build_bronze_directory(
    reference_date: date,
    output_dir: str | Path = (
        "data/bronze/fundsexplorer"
    ),
) -> Path:
    """
    Cria o caminho particionado da camada Bronze.

    Exemplo:

    data/bronze/fundsexplorer/
        year=2026/
        month=08/
        day=28/
    """

    output_dir = Path(
        output_dir
    )

    destination_dir = (
        output_dir
        / f"year={reference_date.year}"
        / f"month={reference_date.month:02d}"
        / f"day={reference_date.day:02d}"
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return destination_dir


def save_bronze_results(
    funds_dataframe: pd.DataFrame,
    errors_dataframe: pd.DataFrame,
    reference_date: date | None = None,
    output_dir: str | Path = (
        "data/bronze/fundsexplorer"
    ),
) -> tuple[Path, Path | None]:
    """
    Persiste o resultado da coleta na Bronze.

    Os arquivos são gravados em CSV UTF-8 com BOM,
    facilitando também inspeção manual no Windows/Excel.
    """

    reference_date = (
        reference_date
        or date.today()
    )

    destination_dir = (
        build_bronze_directory(
            reference_date=reference_date,
            output_dir=output_dir,
        )
    )

    mapping_file = (
        destination_dir
        / "ticker_cnpj_mapping.csv"
    )

    funds_dataframe.to_csv(
        mapping_file,
        index=False,
        encoding="utf-8-sig",
    )

    errors_file: Path | None = None

    if not errors_dataframe.empty:
        errors_file = (
            destination_dir
            / "collection_errors.csv"
        )

        errors_dataframe.to_csv(
            errors_file,
            index=False,
            encoding="utf-8-sig",
        )

    return (
        mapping_file,
        errors_file,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai tickers e respectivos CNPJs "
            "do Funds Explorer."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        required=False,
        help=(
            "Limita a quantidade de tickers. "
            "Útil para testes."
        ),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help=(
            "Intervalo em segundos entre "
            "requisições. Padrão: 1 segundo."
        ),
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help=(
            "Executa a coleta sem persistir "
            "os resultados na Bronze."
        ),
    )

    args = parser.parse_args()

    print(
        "Obtendo lista de ativos "
        "do Funds Explorer..."
    )

    session = create_session()

    list_html = download_funds_list_page(
        session=session
    )

    tickers = extract_tickers_from_list_page(
        list_html
    )

    total_discovered = len(
        tickers
    )

    print(
        f"\nTickers encontrados: "
        f"{total_discovered:,}"
    )

    if not tickers:
        raise RuntimeError(
            "Nenhum ticker foi encontrado "
            "na página /funds."
        )

    if args.limit is not None:
        tickers = tickers[
            : args.limit
        ]

        print(
            f"Modo teste: processando "
            f"{len(tickers)} tickers."
        )

    (
        funds_dataframe,
        errors_dataframe,
    ) = collect_fund_details(
        tickers=tickers,
        delay_seconds=args.delay,
    )

    processed = len(
        tickers
    )

    valid_records = len(
        funds_dataframe
    )

    error_records = len(
        errors_dataframe
    )

    success_rate = (
        valid_records / processed * 100
        if processed
        else 0
    )

    print(
        "\nColeta concluída."
    )

    print(
        f"Processados: "
        f"{processed:,}"
    )

    print(
        f"Registros válidos: "
        f"{valid_records:,}"
    )

    print(
        f"Erros: "
        f"{error_records:,}"
    )

    print(
        f"Taxa de sucesso: "
        f"{success_rate:.2f}%"
    )

    if not args.no_save:
        (
            mapping_file,
            errors_file,
        ) = save_bronze_results(
            funds_dataframe=(
                funds_dataframe
            ),
            errors_dataframe=(
                errors_dataframe
            ),
        )

        print(
            "\nArquivos Bronze:"
        )

        print(
            f"Mapping: "
            f"{mapping_file}"
        )

        if errors_file is not None:
            print(
                f"Erros:   "
                f"{errors_file}"
            )

    print(
        "\nParser Funds Explorer "
        "concluído com sucesso."
    )


if __name__ == "__main__":
    main()