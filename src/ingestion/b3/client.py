from datetime import date, timedelta
from pathlib import Path

import requests


BASE_URL = "https://arquivos.b3.com.br/apinegocios/tickercsv"


def get_previous_business_day(reference_date: date | None = None) -> date:
    """
    Retorna uma data candidata ao pregão D-1.

    Neste primeiro MVP local, tratamos apenas sábado e domingo.
    Feriados da B3 serão tratados posteriormente.
    """
    current_date = reference_date or date.today()
    previous_day = current_date - timedelta(days=1)

    while previous_day.weekday() >= 5:
        previous_day -= timedelta(days=1)

    return previous_day


def download_b3_daily_file(
    trade_date: date,
    output_dir: str = "data/raw/b3",
) -> Path:
    """
    Faz o download do arquivo diário da B3 e salva na camada RAW local.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    trade_date_str = trade_date.strftime("%Y-%m-%d")

    url = f"{BASE_URL}/{trade_date_str}"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    file_path = output_path / f"b3_{trade_date.strftime('%Y%m%d')}.csv"

    file_path.write_bytes(response.content)

    return file_path


if __name__ == "__main__":
    trade_date = get_previous_business_day()

    print(f"Data de referência: {trade_date}")

    downloaded_file = download_b3_daily_file(trade_date)

    print(f"Arquivo salvo em: {downloaded_file}")