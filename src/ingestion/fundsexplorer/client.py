from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


FUNDS_EXPLORER_BASE_URL = "https://www.fundsexplorer.com.br"
FUNDS_LIST_URL = f"{FUNDS_EXPLORER_BASE_URL}/funds"


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
    Cria uma sessão HTTP reutilizável com retry controlado.
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
        allowed_methods=["GET"],
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


def build_fund_url(
    ticker: str,
) -> str:
    """
    Constrói a URL da página individual de um FII.
    """

    normalized_ticker = (
        ticker
        .strip()
        .lower()
    )

    return (
        f"{FUNDS_EXPLORER_BASE_URL}"
        f"/funds/{normalized_ticker}"
    )


def request_html(
    url: str,
    session: requests.Session | None = None,
) -> str:
    """
    Executa uma requisição GET e retorna o HTML.
    """

    http_session = session or create_session()

    response = http_session.get(
        url,
        timeout=60,
    )

    if response.status_code == 404:
        raise FileNotFoundError(
            f"Página não encontrada: {url}"
        )

    response.raise_for_status()

    html = response.text

    if not html.strip():
        raise ValueError(
            f"Resposta vazia: {url}"
        )

    return html


def download_funds_list_page(
    session: requests.Session | None = None,
) -> str:
    """
    Baixa a página contendo a listagem de FIIs.
    """

    print(
        f"Consultando lista de FIIs: "
        f"{FUNDS_LIST_URL}"
    )

    return request_html(
        FUNDS_LIST_URL,
        session=session,
    )


def download_fund_page(
    ticker: str,
    session: requests.Session | None = None,
    delay_seconds: float = 0.0,
) -> str:
    """
    Baixa a página individual de um FII.

    O delay pode ser utilizado durante coleta em lote.
    """

    if delay_seconds > 0:
        time.sleep(
            delay_seconds
        )

    url = build_fund_url(
        ticker
    )

    return request_html(
        url,
        session=session,
    )