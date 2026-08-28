from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd


B3_PRICE_REPORT_NAMESPACE = "urn:bvmf.217.01.xsd"
PRICE_REPORT_TAG = f"{{{B3_PRICE_REPORT_NAMESPACE}}}PricRpt"


def _get_text(element: ET.Element, tag_name: str) -> str | None:
    """
    Retorna o texto de uma tag dentro de um registro PricRpt.
    """

    found = element.find(
        f".//{{{B3_PRICE_REPORT_NAMESPACE}}}{tag_name}"
    )

    if found is None:
        return None

    return found.text


def _find_inner_zip(outer_zip: zipfile.ZipFile) -> str:
    """
    Localiza o arquivo ZIP interno que contém o Price Report da B3.
    """

    zip_files = [
        name
        for name in outer_zip.namelist()
        if name.lower().endswith(".zip")
    ]

    if not zip_files:
        raise FileNotFoundError(
            "Nenhum arquivo ZIP interno foi encontrado "
            "dentro do arquivo pesquisa-pregao.zip."
        )

    # Para o relatório atual esperamos algo como SPRE260827.zip.
    spre_files = [
        name
        for name in zip_files
        if Path(name).name.upper().startswith("SPRE")
    ]

    if spre_files:
        return spre_files[0]

    return zip_files[0]


def _find_price_report_xml(inner_zip: zipfile.ZipFile) -> str:
    """
    Localiza o XML BVBG.186.01 dentro do ZIP interno.
    """

    xml_files = [
        name
        for name in inner_zip.namelist()
        if name.lower().endswith(".xml")
    ]

    if not xml_files:
        raise FileNotFoundError(
            "Nenhum arquivo XML foi encontrado "
            "dentro do ZIP interno da B3."
        )

    price_report_files = [
        name
        for name in xml_files
        if Path(name).name.upper().startswith("BVBG.186.01")
    ]

    if not price_report_files:
        raise FileNotFoundError(
            "O arquivo BVBG.186.01 não foi encontrado "
            "dentro do ZIP interno."
        )

    return price_report_files[0]


def extract_b3_xml_from_download(
    outer_zip_path: str | Path,
) -> tuple[bytes, str, str]:
    """
    Abre o ZIP baixado da B3, abre o ZIP interno em memória
    e retorna o conteúdo do XML BVBG.186.01.

    Returns
    -------
    tuple
        (
            conteúdo XML em bytes,
            nome do ZIP interno,
            nome do XML
        )
    """

    outer_zip_path = Path(outer_zip_path)

    if not outer_zip_path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {outer_zip_path}"
        )

    if not zipfile.is_zipfile(outer_zip_path):
        raise ValueError(
            f"O arquivo informado não é um ZIP válido: "
            f"{outer_zip_path}"
        )

    with zipfile.ZipFile(outer_zip_path, "r") as outer_zip:
        inner_zip_name = _find_inner_zip(outer_zip)

        inner_zip_bytes = outer_zip.read(inner_zip_name)

    with zipfile.ZipFile(
        io.BytesIO(inner_zip_bytes),
        "r",
    ) as inner_zip:
        xml_name = _find_price_report_xml(inner_zip)

        xml_bytes = inner_zip.read(xml_name)

    return xml_bytes, inner_zip_name, xml_name


def parse_b3_price_report_xml(
    xml_bytes: bytes,
) -> pd.DataFrame:
    """
    Faz o parse do XML BVBG.186.01 para DataFrame.

    O XML é processado de forma incremental usando iterparse.
    """

    records: list[dict[str, object]] = []

    xml_stream = io.BytesIO(xml_bytes)

    for _, element in ET.iterparse(
        xml_stream,
        events=("end",),
    ):
        if element.tag != PRICE_REPORT_TAG:
            continue

        records.append(
            {
                "trade_date": _get_text(element, "Dt"),
                "ticker": _get_text(element, "TckrSymb"),
                "instrument_id": _get_text(element, "Id"),
                "instrument_id_type": _get_text(element, "Prtry"),
                "market": _get_text(element, "MktIdrCd"),
                "open_price": _get_text(element, "FrstPric"),
                "low_price": _get_text(element, "MinPric"),
                "high_price": _get_text(element, "MaxPric"),
                "average_price": _get_text(
                    element,
                    "TradAvrgPric",
                ),
                "close_price": _get_text(element, "LastPric"),
                "trades_quantity": _get_text(
                    element,
                    "RglrTxsQty",
                ),
            }
        )

        # Libera memória após processar cada PricRpt.
        element.clear()

    return pd.DataFrame(records)


def normalize_types(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Converte colunas para tipos adequados.
    """

    dataframe = dataframe.copy()

    dataframe["trade_date"] = pd.to_datetime(
        dataframe["trade_date"],
        errors="coerce",
    )

    price_columns = [
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
    ]

    for column in price_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe["trades_quantity"] = pd.to_numeric(
        dataframe["trades_quantity"],
        errors="coerce",
    ).astype("Int64")

    return dataframe


def parse_b3_download(
    outer_zip_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Executa todo o fluxo:

    pesquisa-pregao.zip
        -> ZIP interno
        -> BVBG.186.01 XML
        -> DataFrame
    """

    (
        xml_bytes,
        inner_zip_name,
        xml_name,
    ) = extract_b3_xml_from_download(
        outer_zip_path
    )

    dataframe = parse_b3_price_report_xml(
        xml_bytes
    )

    dataframe = normalize_types(
        dataframe
    )

    metadata = {
        "outer_zip": Path(
            outer_zip_path
        ).name,
        "inner_zip": Path(
            inner_zip_name
        ).name,
        "xml_file": Path(
            xml_name
        ).name,
    }

    return dataframe, metadata


def show_fii_sample(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Filtra alguns FIIs conhecidos apenas para validar a POC.

    Esta NÃO é a regra definitiva para identificar FIIs.
    """

    sample_fiis = [
        "HGLG11",
        "MXRF11",
        "KNRI11",
        "XPML11",
        "VISC11",
    ]

    return dataframe[
        dataframe["ticker"].isin(
            sample_fiis
        )
    ].copy()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parser do BVBG.186.01 "
            "baixado pela Pesquisa por Pregão da B3."
        )
    )

    parser.add_argument(
        "zip_path",
        help=(
            "Caminho para o arquivo "
            "pesquisa-pregao.zip."
        ),
    )

    args = parser.parse_args()

    print("Iniciando leitura da B3...")

    dataframe, metadata = parse_b3_download(
        args.zip_path
    )

    print("\nArquivos encontrados:")
    print(
        f"  ZIP externo: {metadata['outer_zip']}"
    )
    print(
        f"  ZIP interno: {metadata['inner_zip']}"
    )
    print(
        f"  XML:         {metadata['xml_file']}"
    )

    print(
        f"\nRegistros encontrados: "
        f"{len(dataframe):,}"
    )

    print("\nColunas:")
    print(
        dataframe.columns.tolist()
    )

    print("\nTipos:")
    print(
        dataframe.dtypes
    )

    print("\nAmostra geral:")
    print(
        dataframe.head().to_string(
            index=False
        )
    )

    fii_sample = show_fii_sample(
        dataframe
    )

    print(
        "\nFIIs usados para validação:"
    )

    if fii_sample.empty:
        print(
            "Nenhum dos FIIs de exemplo "
            "foi encontrado."
        )
    else:
        print(
            fii_sample.to_string(
                index=False
            )
        )


if __name__ == "__main__":
    main()