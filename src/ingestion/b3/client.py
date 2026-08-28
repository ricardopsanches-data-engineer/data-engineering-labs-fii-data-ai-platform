from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import requests


B3_DOWNLOAD_URL = "https://www.b3.com.br/pesquisapregao/download"


def get_previous_business_day(
    reference_date: date | None = None,
) -> date:
    """
    Retorna uma data candidata ao último dia útil anterior.

    Nesta primeira versão:
    - sábado e domingo são ignorados;
    - feriados da B3 ainda não são tratados.
    """

    current_date = reference_date or date.today()

    previous_day = current_date - timedelta(days=1)

    while previous_day.weekday() >= 5:
        previous_day -= timedelta(days=1)

    return previous_day


def build_b3_filename(trade_date: date) -> str:
    """
    Constrói o nome do arquivo esperado pela B3.

    Formato:
        SPRE + YYMMDD + .zip

    Exemplo:
        2026-08-27 -> SPRE260827.zip
    """

    return f"SPRE{trade_date.strftime('%y%m%d')}.zip"


def build_download_url(trade_date: date) -> str:
    """
    Constrói a URL de download do relatório diário da B3.
    """

    b3_filename = build_b3_filename(trade_date)

    return f"{B3_DOWNLOAD_URL}?filelist={b3_filename}"


def build_local_filename(trade_date: date) -> str:
    """
    Constrói o nome usado para salvar o ZIP externo na camada RAW.

    Esse nome é propositalmente diferente do SPRE*.zip,
    pois o arquivo baixado pela B3 contém outro ZIP interno
    chamado SPRE*.zip.
    """

    return f"b3_download_{trade_date.strftime('%Y%m%d')}.zip"


def download_b3_daily_file(
    trade_date: date,
    output_dir: str | Path = "data/raw/b3",
) -> Path:
    """
    Faz o download do relatório diário da B3 e salva o
    arquivo original na camada RAW local.

    Parameters
    ----------
    trade_date:
        Data do pregão desejado.

    output_dir:
        Diretório raiz da camada RAW.

    Returns
    -------
    Path
        Caminho do arquivo salvo.
    """

    b3_filename = build_b3_filename(trade_date)
    local_filename = build_local_filename(trade_date)

    url = build_download_url(trade_date)

    output_dir = Path(output_dir)

    destination_dir = (
        output_dir
        / f"year={trade_date.year}"
        / f"month={trade_date.month:02d}"
        / f"day={trade_date.day:02d}"
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_file = destination_dir / local_filename

    print(f"Data do pregão: {trade_date:%Y-%m-%d}")
    print(f"Arquivo solicitado à B3: {b3_filename}")
    print(f"URL: {url}")

    response = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; fii-data-ai-platform/1.0)"
            )
        },
    )

    if response.status_code == 404:
        raise FileNotFoundError(
            f"Arquivo não encontrado na B3 para "
            f"{trade_date:%Y-%m-%d}: {b3_filename}"
        )

    response.raise_for_status()

    if not response.content:
        raise ValueError(
            "A B3 retornou uma resposta vazia."
        )

    destination_file.write_bytes(
        response.content
    )

    print("\nDownload concluído.")
    print(f"Arquivo salvo em: {destination_file}")
    print(
        f"Tamanho: "
        f"{destination_file.stat().st_size:,} bytes"
    )

    return destination_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download do Simplified Price Report "
            "diário da B3."
        )
    )

    parser.add_argument(
        "--date",
        required=False,
        help=(
            "Data do pregão no formato YYYY-MM-DD. "
            "Se não informada, utiliza D-1 útil."
        ),
    )

    args = parser.parse_args()

    if args.date:
        trade_date = date.fromisoformat(
            args.date
        )
    else:
        trade_date = get_previous_business_day()

    download_b3_daily_file(
        trade_date
    )


if __name__ == "__main__":
    main()