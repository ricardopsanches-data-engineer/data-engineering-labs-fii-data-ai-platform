from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import requests


CVM_FUND_REGISTER_URL = (
    "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/"
    "registro_fundo_classe.zip"
)


def build_local_path(
    reference_date: date,
    output_dir: str | Path = "data/raw/cvm",
) -> Path:
    """
    Constrói o caminho local da camada RAW.

    Exemplo:
        data/raw/cvm/
        year=2026/
        month=08/
        day=28/
        registro_fundo_classe.zip
    """

    output_dir = Path(output_dir)

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

    return (
        destination_dir
        / "registro_fundo_classe.zip"
    )


def download_cvm_fund_register(
    reference_date: date | None = None,
    output_dir: str | Path = "data/raw/cvm",
) -> Path:
    """
    Faz download do cadastro de fundos/classes da CVM.

    O arquivo original é preservado na camada RAW.

    Parameters
    ----------
    reference_date:
        Data utilizada para particionar a RAW.
        Se não informada, utiliza a data atual.

    output_dir:
        Diretório raiz da camada RAW.

    Returns
    -------
    Path
        Caminho do arquivo salvo.
    """

    reference_date = reference_date or date.today()

    destination_file = build_local_path(
        reference_date,
        output_dir,
    )

    print(
        f"Data de referência: "
        f"{reference_date:%Y-%m-%d}"
    )

    print(
        f"URL CVM: "
        f"{CVM_FUND_REGISTER_URL}"
    )

    response = requests.get(
        CVM_FUND_REGISTER_URL,
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
            "Arquivo cadastral da CVM "
            "não foi encontrado."
        )

    response.raise_for_status()

    if not response.content:
        raise ValueError(
            "A CVM retornou uma resposta vazia."
        )

    destination_file.write_bytes(
        response.content
    )

    print("\nDownload concluído.")

    print(
        f"Arquivo salvo em: "
        f"{destination_file}"
    )

    print(
        f"Tamanho: "
        f"{destination_file.stat().st_size:,} bytes"
    )

    return destination_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download do cadastro de fundos "
            "e classes da CVM."
        )
    )

    parser.add_argument(
        "--date",
        required=False,
        help=(
            "Data de referência no formato YYYY-MM-DD. "
            "Se não informada, utiliza a data atual."
        ),
    )

    args = parser.parse_args()

    if args.date:
        reference_date = date.fromisoformat(
            args.date
        )
    else:
        reference_date = date.today()

    download_cvm_fund_register(
        reference_date
    )


if __name__ == "__main__":
    main()