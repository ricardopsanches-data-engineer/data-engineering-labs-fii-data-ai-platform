from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd


B3_PRICE_REPORT_NAMESPACE = "urn:bvmf.217.01.xsd"

PRICE_REPORT_TAG = (
    f"{{{B3_PRICE_REPORT_NAMESPACE}}}PricRpt"
)

B3_PRICE_REPORT_PREFIX = "BVBG.186.01"
B3_INSTRUMENT_REPORT_PREFIX = "BVBG.028.02"


def _local_name(tag: str) -> str:
    """
    Remove o namespace XML e retorna apenas
    o nome local da tag.
    """

    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def _get_text(
    element: ET.Element,
    tag_name: str,
) -> str | None:
    """
    Retorna o texto de uma tag dentro
    de um registro PricRpt.
    """

    found = element.find(
        f".//{{{B3_PRICE_REPORT_NAMESPACE}}}"
        f"{tag_name}"
    )

    if found is None:
        return None

    return found.text


def _find_descendant_text(
    element: ET.Element,
    tag_name: str,
) -> str | None:
    """
    Procura uma tag recursivamente,
    ignorando o namespace XML.
    """

    for descendant in element.iter():
        if _local_name(
            descendant.tag
        ) != tag_name:
            continue

        if descendant.text is None:
            return None

        value = descendant.text.strip()

        return value if value else None

    return None


def _find_direct_child(
    element: ET.Element,
    tag_name: str,
) -> ET.Element | None:
    """
    Procura apenas entre os filhos diretos.
    """

    for child in element:
        if _local_name(
            child.tag
        ) == tag_name:
            return child

    return None


def _find_inner_zip(
    outer_zip: zipfile.ZipFile,
) -> str:
    """
    Localiza o ZIP interno que contém
    o Price Report da B3.

    Exemplo:
        SPRE260911.zip
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

    spre_files = [
        name
        for name in zip_files
        if Path(name)
        .name
        .upper()
        .startswith("SPRE")
    ]

    if spre_files:
        return spre_files[0]

    return zip_files[0]


def _find_instrument_inner_zip(
    outer_zip: zipfile.ZipFile,
) -> str:
    """
    Localiza o ZIP interno do Cadastro
    de Instrumentos da B3.

    Exemplo:
        IN260911.zip
    """

    zip_files = [
        name
        for name in outer_zip.namelist()
        if name.lower().endswith(".zip")
    ]

    instrument_files = [
        name
        for name in zip_files
        if Path(name)
        .name
        .upper()
        .startswith("IN")
    ]

    if not instrument_files:
        raise FileNotFoundError(
            "Nenhum ZIP interno de Cadastro de "
            "Instrumentos com prefixo IN foi encontrado."
        )

    return instrument_files[0]


def _find_price_report_xml(
    inner_zip: zipfile.ZipFile,
) -> str:
    """
    Localiza o XML BVBG.186.01
    dentro do ZIP interno.
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
        if Path(name)
        .name
        .upper()
        .startswith(
            B3_PRICE_REPORT_PREFIX
        )
    ]

    if not price_report_files:
        raise FileNotFoundError(
            "O arquivo BVBG.186.01 não foi encontrado "
            "dentro do ZIP interno."
        )

    return price_report_files[0]


def _find_instrument_report_xmls(
    inner_zip: zipfile.ZipFile,
) -> list[str]:
    """
    Localiza todos os XMLs BVBG.028.02.

    Um mesmo pregão pode conter mais
    de um arquivo BVBG.028.02.
    """

    xml_files = [
        name
        for name in inner_zip.namelist()
        if (
            name.lower().endswith(".xml")
            and Path(name)
            .name
            .upper()
            .startswith(
                B3_INSTRUMENT_REPORT_PREFIX
            )
        )
    ]

    if not xml_files:
        raise FileNotFoundError(
            "Nenhum XML BVBG.028.02 foi encontrado "
            "dentro do ZIP interno."
        )

    return sorted(
        xml_files
    )


def extract_b3_xml_from_download(
    outer_zip_path: str | Path,
) -> tuple[bytes, str, str]:
    """
    Abre o ZIP baixado da B3, abre o ZIP interno
    e retorna o XML BVBG.186.01.
    """

    outer_zip_path = Path(
        outer_zip_path
    )

    if not outer_zip_path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: "
            f"{outer_zip_path}"
        )

    if not zipfile.is_zipfile(
        outer_zip_path
    ):
        raise ValueError(
            "O arquivo informado não é "
            f"um ZIP válido: {outer_zip_path}"
        )

    with zipfile.ZipFile(
        outer_zip_path,
        "r",
    ) as outer_zip:
        inner_zip_name = _find_inner_zip(
            outer_zip
        )

        inner_zip_bytes = outer_zip.read(
            inner_zip_name
        )

    with zipfile.ZipFile(
        io.BytesIO(
            inner_zip_bytes
        ),
        "r",
    ) as inner_zip:
        xml_name = _find_price_report_xml(
            inner_zip
        )

        xml_bytes = inner_zip.read(
            xml_name
        )

    return (
        xml_bytes,
        inner_zip_name,
        xml_name,
    )


def extract_b3_instrument_xmls_from_download(
    outer_zip_path: str | Path,
) -> tuple[
    list[tuple[str, bytes]],
    str,
]:
    """
    Abre pesquisa-pregao.zip,
    encontra INYYMMDD.zip e retorna
    todos os XMLs BVBG.028.02.
    """

    outer_zip_path = Path(
        outer_zip_path
    )

    if not outer_zip_path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: "
            f"{outer_zip_path}"
        )

    if not zipfile.is_zipfile(
        outer_zip_path
    ):
        raise ValueError(
            "O arquivo informado não é "
            f"um ZIP válido: {outer_zip_path}"
        )

    with zipfile.ZipFile(
        outer_zip_path,
        "r",
    ) as outer_zip:
        inner_zip_name = (
            _find_instrument_inner_zip(
                outer_zip
            )
        )

        inner_zip_bytes = outer_zip.read(
            inner_zip_name
        )

    with zipfile.ZipFile(
        io.BytesIO(
            inner_zip_bytes
        ),
        "r",
    ) as inner_zip:
        xml_names = (
            _find_instrument_report_xmls(
                inner_zip
            )
        )

        xml_files = [
            (
                xml_name,
                inner_zip.read(
                    xml_name
                ),
            )
            for xml_name in xml_names
        ]

    return (
        xml_files,
        inner_zip_name,
    )


def parse_b3_price_report_xml(
    xml_bytes: bytes,
) -> pd.DataFrame:
    """
    Faz o parse do XML BVBG.186.01.

    O XML é processado incrementalmente
    usando iterparse.
    """

    records: list[
        dict[str, object]
    ] = []

    xml_stream = io.BytesIO(
        xml_bytes
    )

    for _, element in ET.iterparse(
        xml_stream,
        events=("end",),
    ):
        if element.tag != PRICE_REPORT_TAG:
            continue

        records.append(
            {
                "trade_date": _get_text(
                    element,
                    "Dt",
                ),
                "ticker": _get_text(
                    element,
                    "TckrSymb",
                ),
                "instrument_id": _get_text(
                    element,
                    "Id",
                ),
                "instrument_id_type": _get_text(
                    element,
                    "Prtry",
                ),
                "market": _get_text(
                    element,
                    "MktIdrCd",
                ),
                "open_price": _get_text(
                    element,
                    "FrstPric",
                ),
                "low_price": _get_text(
                    element,
                    "MinPric",
                ),
                "high_price": _get_text(
                    element,
                    "MaxPric",
                ),
                "average_price": _get_text(
                    element,
                    "TradAvrgPric",
                ),
                "close_price": _get_text(
                    element,
                    "LastPric",
                ),
                "trades_quantity": _get_text(
                    element,
                    "RglrTxsQty",
                ),
            }
        )

        element.clear()

    return pd.DataFrame(
        records
    )


def _extract_underlying_fields(
    instrument_block: ET.Element,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    """
    Extrai dados do instrumento subjacente.
    """

    underlying = _find_direct_child(
        instrument_block,
        "UndrlygInstrmId",
    )

    if underlying is None:
        return (
            None,
            None,
            None,
        )

    underlying_id = (
        _find_descendant_text(
            underlying,
            "Id",
        )
    )

    underlying_id_type = (
        _find_descendant_text(
            underlying,
            "Prtry",
        )
    )

    underlying_market = (
        _find_descendant_text(
            underlying,
            "MktIdrCd",
        )
    )

    return (
        underlying_id,
        underlying_id_type,
        underlying_market,
    )


def _parse_instrument_record(
    instrm: ET.Element,
) -> dict[str, object] | None:
    """
    Converte um Instrm completo do BVBG.028.02
    em registro tabular.

    O nível Instrm é necessário porque os dados
    cadastrais estão distribuídos entre: RptParams,
    FinInstrmId, FinInstrmAttrCmon e InstrmInf.
    """

    rpt_params = _find_direct_child(
        instrm,
        "RptParams",
    )

    fin_instrm_id = _find_direct_child(
        instrm,
        "FinInstrmId",
    )

    fin_instrm_attr_cmon = _find_direct_child(
        instrm,
        "FinInstrmAttrCmon",
    )

    instrm_inf = _find_direct_child(
        instrm,
        "InstrmInf",
    )

    if instrm_inf is None:
        return None

    children = list(
        instrm_inf
    )

    if not children:
        return None

    instrument_block = children[0]

    instrument_type = _local_name(
        instrument_block.tag
    )

    (
        underlying_instrument_id,
        underlying_instrument_id_type,
        underlying_market,
    ) = _extract_underlying_fields(
        instrument_block
    )

    return {
        "report_date": (
            _find_descendant_text(
                rpt_params,
                "Dt",
            )
            if rpt_params is not None
            else None
        ),
        "update_type": (
            _find_descendant_text(
                rpt_params,
                "UpdTp",
            )
            if rpt_params is not None
            else None
        ),
        "instrument_id": (
            _find_descendant_text(
                fin_instrm_id,
                "Id",
            )
            if fin_instrm_id is not None
            else None
        ),
        "instrument_id_type": (
            _find_descendant_text(
                fin_instrm_id,
                "Prtry",
            )
            if fin_instrm_id is not None
            else None
        ),
        "listing_market": (
            _find_descendant_text(
                fin_instrm_id,
                "MktIdrCd",
            )
            if fin_instrm_id is not None
            else None
        ),
        "asset": (
            _find_descendant_text(
                fin_instrm_attr_cmon,
                "Asst",
            )
            if fin_instrm_attr_cmon is not None
            else None
        ),
        "asset_description": (
            _find_descendant_text(
                fin_instrm_attr_cmon,
                "AsstDesc",
            )
            if fin_instrm_attr_cmon is not None
            else None
        ),
        "b3_market": (
            _find_descendant_text(
                fin_instrm_attr_cmon,
                "Mkt",
            )
            if fin_instrm_attr_cmon is not None
            else None
        ),
        "b3_segment": (
            _find_descendant_text(
                fin_instrm_attr_cmon,
                "Sgmt",
            )
            if fin_instrm_attr_cmon is not None
            else None
        ),
        "instrument_description": (
            _find_descendant_text(
                fin_instrm_attr_cmon,
                "Desc",
            )
            if fin_instrm_attr_cmon is not None
            else None
        ),
        "instrument_type": instrument_type,
        "security_category": (
            _find_descendant_text(
                instrument_block,
                "SctyCtgy",
            )
        ),
        "ticker": (
            _find_descendant_text(
                instrument_block,
                "TckrSymb",
            )
        ),
        "isin": (
            _find_descendant_text(
                instrument_block,
                "ISIN",
            )
        ),
        "distribution_id": (
            _find_descendant_text(
                instrument_block,
                "DstrbtnId",
            )
        ),
        "cfi_code": (
            _find_descendant_text(
                instrument_block,
                "CFICd",
            )
        ),
        "specification_code": (
            _find_descendant_text(
                instrument_block,
                "SpcfctnCd",
            )
        ),
        "corporate_name": (
            _find_descendant_text(
                instrument_block,
                "CrpnNm",
            )
        ),
        "payment_type": (
            _find_descendant_text(
                instrument_block,
                "PmtTp",
            )
        ),
        "round_lot": (
            _find_descendant_text(
                instrument_block,
                "AllcnRndLot",
            )
        ),
        "price_factor": (
            _find_descendant_text(
                instrument_block,
                "PricFctr",
            )
        ),
        "trading_start_date": (
            _find_descendant_text(
                instrument_block,
                "TradgStartDt",
            )
        ),
        "trading_end_date": (
            _find_descendant_text(
                instrument_block,
                "TradgEndDt",
            )
        ),
        "corporate_action_start_date": (
            _find_descendant_text(
                instrument_block,
                "CorpActnStartDt",
            )
        ),
        "ex_distribution_number": (
            _find_descendant_text(
                instrument_block,
                "EXDstrbtnNb",
            )
        ),
        "custody_treatment_type": (
            _find_descendant_text(
                instrument_block,
                "CtdyTrtmntTp",
            )
        ),
        "trading_currency": (
            _find_descendant_text(
                instrument_block,
                "TradgCcy",
            )
        ),
        "market_capitalization": (
            _find_descendant_text(
                instrument_block,
                "MktCptlstn",
            )
        ),
        "last_price": (
            _find_descendant_text(
                instrument_block,
                "LastPric",
            )
        ),
        "first_price": (
            _find_descendant_text(
                instrument_block,
                "FrstPric",
            )
        ),
        "settlement_days": (
            _find_descendant_text(
                instrument_block,
                "DaysToSttlm",
            )
        ),
        "rights_issue_price": (
            _find_descendant_text(
                instrument_block,
                "RghtsIssePric",
            )
        ),
        "underlying_instrument_id": (
            underlying_instrument_id
        ),
        "underlying_instrument_id_type": (
            underlying_instrument_id_type
        ),
        "underlying_market": (
            underlying_market
        ),
    }

def parse_b3_instrument_report_xml(
    xml_bytes: bytes,
) -> pd.DataFrame:
    """
    Faz o parse incremental de um
    XML BVBG.028.02.

    O processamento ocorre no fechamento de cada
    elemento Instrm para preservar, no mesmo registro,
    os campos de RptParams, FinInstrmId,
    FinInstrmAttrCmon e InstrmInf.
    """

    records: list[
        dict[str, object]
    ] = []

    xml_stream = io.BytesIO(
        xml_bytes
    )

    for _, element in ET.iterparse(
        xml_stream,
        events=("end",),
    ):
        if _local_name(
            element.tag
        ) != "Instrm":
            continue

        record = (
            _parse_instrument_record(
                element
            )
        )

        if record is not None:
            records.append(
                record
            )

        element.clear()

    return pd.DataFrame(
        records
    )

def normalize_types(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Converte colunas do Price Report
    para tipos adequados.
    """

    dataframe = dataframe.copy()

    dataframe["trade_date"] = (
        pd.to_datetime(
            dataframe["trade_date"],
            errors="coerce",
        )
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

    dataframe["trades_quantity"] = (
        pd.to_numeric(
            dataframe[
                "trades_quantity"
            ],
            errors="coerce",
        )
        .astype("Int64")
    )

    return dataframe


def normalize_instrument_types(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza tipos do Cadastro
    de Instrumentos.
    """

    dataframe = dataframe.copy()

    string_columns = [
        "update_type",
        "instrument_id",
        "instrument_id_type",
        "listing_market",
        "asset",
        "asset_description",
        "b3_market",
        "b3_segment",
        "instrument_description",
        "instrument_type",
        "security_category",
        "ticker",
        "isin",
        "distribution_id",
        "cfi_code",
        "specification_code",
        "corporate_name",
        "payment_type",
        "custody_treatment_type",
        "trading_currency",
        "underlying_instrument_id",
        "underlying_instrument_id_type",
        "underlying_market",
        "source_xml",
    ]

    for column in string_columns:
        if column not in dataframe.columns:
            continue

        dataframe[column] = (
            dataframe[column]
            .astype("string")
            .str.strip()
        )

    date_columns = [
        "report_date",
        "trading_start_date",
        "trading_end_date",
        "corporate_action_start_date",
    ]

    for column in date_columns:
        if column not in dataframe.columns:
            continue

        dataframe[column] = (
            pd.to_datetime(
                dataframe[column],
                errors="coerce",
            )
        )

    numeric_columns = [
        "round_lot",
        "price_factor",
        "market_capitalization",
        "last_price",
        "first_price",
        "settlement_days",
        "rights_issue_price",
    ]

    for column in numeric_columns:
        if column not in dataframe.columns:
            continue

        dataframe[column] = (
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )
        )

    return dataframe

def parse_b3_download(
    outer_zip_path: str | Path,
) -> tuple[
    pd.DataFrame,
    dict[str, str],
]:
    """
    Fluxo atual do BVBG.186.01:

    pesquisa-pregao.zip
        -> SPREYYMMDD.zip
        -> BVBG.186.01
        -> DataFrame
    """

    (
        xml_bytes,
        inner_zip_name,
        xml_name,
    ) = extract_b3_xml_from_download(
        outer_zip_path
    )

    dataframe = (
        parse_b3_price_report_xml(
            xml_bytes
        )
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

    return (
        dataframe,
        metadata,
    )


def parse_b3_instrument_download(
    outer_zip_path: str | Path,
) -> tuple[
    pd.DataFrame,
    dict[str, object],
]:
    """
    Fluxo do BVBG.028.02:

    pesquisa-pregao.zip
        -> INYYMMDD.zip
        -> seleciona o snapshot canônico
        -> BVBG.028.02
        -> DataFrame consolidado

    Regra atual:
        quando houver mais de um XML BVBG.028.02
        no mesmo pregão, utiliza o último nome
        em ordem lexicográfica.

    Essa regra foi adotada após validação
    exploratória de snapshots sucessivos.
    """

    (
        xml_files,
        inner_zip_name,
    ) = (
        extract_b3_instrument_xmls_from_download(
            outer_zip_path
        )
    )

    if not xml_files:
        raise RuntimeError(
            "Nenhum XML BVBG.028.02 foi encontrado."
        )

    selected_xml_name, selected_xml_bytes = (
        sorted(
            xml_files,
            key=lambda item: item[0],
        )[-1]
    )

    print(
        "Snapshot Instrument Report selecionado: "
        f"{Path(selected_xml_name).name}"
    )

    dataframe = (
        parse_b3_instrument_report_xml(
            selected_xml_bytes
        )
    )

    dataframe["source_xml"] = (
        Path(selected_xml_name).name
    )

    dataframe = (
        normalize_instrument_types(
            dataframe
        )
    )

    records_before_dedup = len(
        dataframe
    )

    dataframe = (
        dataframe
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    records_after_dedup = len(
        dataframe
    )

    duplicates_removed = (
        records_before_dedup
        - records_after_dedup
    )

    metadata = {
        "outer_zip": Path(
            outer_zip_path
        ).name,
        "inner_zip": Path(
            inner_zip_name
        ).name,
        "available_xml_files": [
            Path(xml_name).name
            for xml_name, _ in xml_files
        ],
        "selected_xml": Path(
            selected_xml_name
        ).name,
        "xml_count": len(
            xml_files
        ),
        "records_before_dedup": (
            records_before_dedup
        ),
        "records": (
            records_after_dedup
        ),
        "duplicates_removed": (
            duplicates_removed
        ),
    }

    return (
        dataframe,
        metadata,
    )


def show_fii_sample(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Filtra alguns FIIs conhecidos
    apenas para validar a POC.

    Esta NÃO é a regra definitiva
    para identificar FIIs.
    """

    sample_fiis = [
        "HGLG11",
        "MXRF11",
        "KNRI11",
        "XPML11",
        "VISC11",
    ]

    return dataframe[
        dataframe[
            "ticker"
        ].isin(
            sample_fiis
        )
    ].copy()


def show_instrument_discovery(
    dataframe: pd.DataFrame,
) -> None:
    """
    Exibe métricas exploratórias do
    Cadastro de Instrumentos.
    """

    print()
    print(
        "======================================"
    )
    print(
        "B3 Instrument Report - Discovery"
    )
    print(
        "======================================"
    )

    print()
    print(
        "Registros: "
        f"{len(dataframe):,}"
    )

    print()
    print(
        "Tipos de instrumento:"
    )

    print(
        dataframe[
            "instrument_type"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "Security categories:"
    )

    print(
        dataframe[
            "security_category"
        ]
        .value_counts(
            dropna=False
        )
        .sort_index()
        .to_string()
    )

    print()

    print(
        "Tickers únicos: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        "ISINs únicos: "
        f"{dataframe['isin'].nunique():,}"
    )

    print(
        "Com underlying: "
        f"{dataframe['underlying_instrument_id'].notna().sum():,}"
    )

    print()
    print(
        "Amostra VGHF:"
    )

    vghf = dataframe[
        dataframe[
            "ticker"
        ]
        .fillna("")
        .str.startswith(
            "VGHF"
        )
    ]

    if vghf.empty:
        print(
            "Nenhum instrumento VGHF encontrado."
        )

        return

    columns = [
        "report_date",
        "instrument_id",
        "instrument_id_type",
        "listing_market",
        "asset",
        "instrument_type",
        "security_category",
        "ticker",
        "isin",
        "corporate_name",
        "underlying_instrument_id",
        "underlying_market",
    ]

    print(
        vghf[
            columns
        ].to_string(
            index=False
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parser de relatórios B3 "
            "baixados pela Pesquisa por Pregão."
        )
    )

    parser.add_argument(
        "zip_path",
        help=(
            "Caminho para o arquivo "
            "pesquisa-pregao.zip."
        ),
    )

    parser.add_argument(
        "--report",
        choices=[
            "price",
            "instruments",
        ],
        default="price",
        help=(
            "Tipo de relatório a processar: "
            "'price' para BVBG.186.01 ou "
            "'instruments' para BVBG.028.02."
        ),
    )

    args = parser.parse_args()

    if args.report == "instruments":
        print(
            "Iniciando leitura do "
            "Cadastro de Instrumentos B3..."
        )

        (
            dataframe,
            metadata,
        ) = (
            parse_b3_instrument_download(
                args.zip_path
            )
        )

        print()
        print(
            "Arquivos encontrados:"
        )

        print(
            "  ZIP externo: "
            f"{metadata['outer_zip']}"
        )

        print(
            "  ZIP interno: "
            f"{metadata['inner_zip']}"
        )

        print(
            "  XMLs:        "
            f"{metadata['xml_count']}"
        )

        for xml_file in metadata[
            "available_xml_files"
        ]:
            print(
                f"    - {xml_file}"
            )

        show_instrument_discovery(
            dataframe
        )

        return

    print(
        "Iniciando leitura da B3..."
    )

    (
        dataframe,
        metadata,
    ) = parse_b3_download(
        args.zip_path
    )

    print(
        "\nArquivos encontrados:"
    )

    print(
        "  ZIP externo: "
        f"{metadata['outer_zip']}"
    )

    print(
        "  ZIP interno: "
        f"{metadata['inner_zip']}"
    )

    print(
        "  XML:         "
        f"{metadata['xml_file']}"
    )

    print(
        "\nRegistros encontrados: "
        f"{len(dataframe):,}"
    )

    print(
        "\nColunas:"
    )

    print(
        dataframe.columns.tolist()
    )

    print(
        "\nTipos:"
    )

    print(
        dataframe.dtypes
    )

    print(
        "\nAmostra geral:"
    )

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