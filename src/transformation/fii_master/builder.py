from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd


CVM_FII_CLASS_TYPE = "Classes de Cotas de Fundos FII"

DEFAULT_CVM_RAW_DIR = Path("data/raw/cvm")
DEFAULT_FUNDS_EXPLORER_BRONZE_DIR = Path(
    "data/bronze/fundsexplorer"
)


def normalize_cnpj(
    value: object,
) -> str | None:
    """
    Normaliza um CNPJ para exatamente 14 dígitos.

    Exemplos:
        36.771.692/0001-19 -> 36771692000119
        36771692000119     -> 36771692000119
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    digits = re.sub(
        r"\D",
        "",
        text,
    )

    if len(digits) != 14:
        return None

    return digits


def find_latest_file(
    base_directory: Path,
    filename: str,
) -> Path:
    """
    Procura recursivamente o arquivo mais recente.

    As partições seguem o padrão:

        year=YYYY/
        month=MM/
        day=DD/
    """

    files = list(
        base_directory.rglob(
            filename
        )
    )

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo '{filename}' "
            f"encontrado em {base_directory}."
        )

    files = sorted(
        files,
        key=lambda path: str(path),
    )

    return files[-1]


def read_csv_with_encoding_fallback(
    file_object,
    separator: str = ";",
) -> pd.DataFrame:
    """
    Lê CSV tentando encodings conhecidos
    utilizados pelos arquivos da CVM.
    """

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    ]

    raw_data = file_object.read()

    for encoding in encodings:
        try:
            text = raw_data.decode(
                encoding
            )

            from io import StringIO

            return pd.read_csv(
                StringIO(text),
                sep=separator,
                dtype=str,
            )

        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        "Não foi possível identificar "
        "o encoding do arquivo CVM.",
    )


def load_cvm_fii_classes(
    cvm_zip_path: Path,
) -> pd.DataFrame:
    """
    Carrega registro_classe.csv da CVM
    e mantém somente classes oficialmente FII.
    """

    print(
        f"Carregando CVM: "
        f"{cvm_zip_path}"
    )

    with zipfile.ZipFile(
        cvm_zip_path,
        "r",
    ) as archive:

        csv_filename = None

        for filename in archive.namelist():
            if filename.endswith(
                "registro_classe.csv"
            ):
                csv_filename = filename
                break

        if csv_filename is None:
            raise FileNotFoundError(
                "registro_classe.csv "
                "não encontrado no ZIP da CVM."
            )

        with archive.open(
            csv_filename
        ) as file_object:
            dataframe = (
                read_csv_with_encoding_fallback(
                    file_object
                )
            )

    required_columns = [
        "CNPJ_Classe",
        "Codigo_CVM",
        "Tipo_Classe",
        "Denominacao_Social",
        "Situacao",
        "Patrimonio_Liquido",
        "Data_Patrimonio_Liquido",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"na CVM: {missing_columns}"
        )

    fii_dataframe = dataframe[
        dataframe["Tipo_Classe"]
        == CVM_FII_CLASS_TYPE
    ].copy()

    fii_dataframe[
        "cnpj"
    ] = fii_dataframe[
        "CNPJ_Classe"
    ].apply(
        normalize_cnpj
    )

    fii_dataframe[
        "Patrimonio_Liquido"
    ] = pd.to_numeric(
        fii_dataframe[
            "Patrimonio_Liquido"
        ],
        errors="coerce",
    )

    fii_dataframe[
        "Data_Patrimonio_Liquido"
    ] = pd.to_datetime(
        fii_dataframe[
            "Data_Patrimonio_Liquido"
        ],
        format="%Y-%m-%d",
        errors="coerce",
    )

    return fii_dataframe


def load_funds_explorer_mapping(
    mapping_path: Path,
) -> pd.DataFrame:
    """
    Carrega o mapping Bronze do Funds Explorer.
    """

    print(
        f"Carregando Funds Explorer: "
        f"{mapping_path}"
    )

    dataframe = pd.read_csv(
        mapping_path,
        dtype={
            "ticker": "string",
            "cnpj": "string",
        },
    )

    required_columns = [
        "ticker",
        "cnpj",
        "fund_name",
        "category_status",
        "source",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"no Funds Explorer: "
            f"{missing_columns}"
        )

    dataframe[
        "ticker"
    ] = (
        dataframe["ticker"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    dataframe[
        "cnpj"
    ] = dataframe[
        "cnpj"
    ].apply(
        normalize_cnpj
    )

    return dataframe


def validate_sources(
    cvm_dataframe: pd.DataFrame,
    funds_explorer_dataframe: pd.DataFrame,
) -> None:
    """
    Exibe métricas de qualidade antes do JOIN.
    """

    cvm_total = len(
        cvm_dataframe
    )

    funds_explorer_total = len(
        funds_explorer_dataframe
    )

    cvm_null_cnpj = (
        cvm_dataframe[
            "cnpj"
        ]
        .isna()
        .sum()
    )

    funds_explorer_null_cnpj = (
        funds_explorer_dataframe[
            "cnpj"
        ]
        .isna()
        .sum()
    )

    cvm_duplicate_cnpj = (
        cvm_dataframe[
            "cnpj"
        ]
        .dropna()
        .duplicated()
        .sum()
    )

    funds_explorer_duplicate_cnpj = (
        funds_explorer_dataframe[
            "cnpj"
        ]
        .dropna()
        .duplicated()
        .sum()
    )

    funds_explorer_duplicate_ticker = (
        funds_explorer_dataframe[
            "ticker"
        ]
        .dropna()
        .duplicated()
        .sum()
    )

    print(
        "\nQualidade das fontes:"
    )

    print(
        f"CVM FIIs: "
        f"{cvm_total:,}"
    )

    print(
        f"Funds Explorer mappings: "
        f"{funds_explorer_total:,}"
    )

    print(
        f"CVM CNPJ nulo/inválido: "
        f"{cvm_null_cnpj:,}"
    )

    print(
        f"Funds Explorer CNPJ "
        f"nulo/inválido: "
        f"{funds_explorer_null_cnpj:,}"
    )

    print(
        f"CVM CNPJ duplicado: "
        f"{cvm_duplicate_cnpj:,}"
    )

    print(
        f"Funds Explorer CNPJ duplicado: "
        f"{funds_explorer_duplicate_cnpj:,}"
    )

    print(
        f"Funds Explorer ticker duplicado: "
        f"{funds_explorer_duplicate_ticker:,}"
    )


def build_fii_master(
    cvm_dataframe: pd.DataFrame,
    funds_explorer_dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Constrói o FII Master através do CNPJ.

    Retorna:

    1. FII Master com matches
    2. CVM FIIs sem ticker
    3. Funds Explorer sem correspondência FII na CVM
    """

    master = cvm_dataframe.merge(
        funds_explorer_dataframe,
        how="inner",
        on="cnpj",
        suffixes=(
            "_cvm",
            "_fundsexplorer",
        ),
        validate="many_to_many",
    )

    matched_cnpjs = set(
        master[
            "cnpj"
        ]
        .dropna()
    )

    cvm_unmatched = (
        cvm_dataframe[
            ~cvm_dataframe[
                "cnpj"
            ].isin(
                matched_cnpjs
            )
        ]
        .copy()
    )

    funds_explorer_unmatched = (
        funds_explorer_dataframe[
            ~funds_explorer_dataframe[
                "cnpj"
            ].isin(
                matched_cnpjs
            )
        ]
        .copy()
    )

    selected_columns = {
        "ticker": "ticker",
        "cnpj": "cnpj",
        "Codigo_CVM": "codigo_cvm",
        "Denominacao_Social": (
            "denominacao_social"
        ),
        "fund_name": (
            "fund_name_commercial"
        ),
        "Situacao": "situacao_cvm",
        "category_status": (
            "status_fundsexplorer"
        ),
        "Patrimonio_Liquido": (
            "patrimonio_liquido"
        ),
        "Data_Patrimonio_Liquido": (
            "data_patrimonio_liquido"
        ),
        "source": "source_ticker",
    }

    master = (
        master[
            list(
                selected_columns.keys()
            )
        ]
        .rename(
            columns=selected_columns
        )
        .copy()
    )

    master = master.sort_values(
        by=[
            "ticker",
            "cnpj",
        ]
    ).reset_index(
        drop=True
    )

    return (
        master,
        cvm_unmatched,
        funds_explorer_unmatched,
    )


def print_join_metrics(
    master: pd.DataFrame,
    cvm_dataframe: pd.DataFrame,
    funds_explorer_dataframe: pd.DataFrame,
    cvm_unmatched: pd.DataFrame,
    funds_explorer_unmatched: pd.DataFrame,
) -> None:
    """
    Exibe métricas do cruzamento.
    """

    cvm_total = len(
        cvm_dataframe
    )

    funds_total = len(
        funds_explorer_dataframe
    )

    master_total = len(
        master
    )

    unique_master_cnpjs = (
        master[
            "cnpj"
        ]
        .nunique()
    )

    unique_master_tickers = (
        master[
            "ticker"
        ]
        .nunique()
    )

    cvm_coverage = (
        unique_master_cnpjs
        / cvm_dataframe[
            "cnpj"
        ].nunique()
        * 100
        if cvm_total
        else 0
    )

    funds_match_rate = (
        len(
            funds_explorer_dataframe
        )
        - len(
            funds_explorer_unmatched
        )
    )

    funds_match_rate = (
        funds_match_rate
        / funds_total
        * 100
        if funds_total
        else 0
    )

    print(
        "\nResultado do JOIN:"
    )

    print(
        f"CVM FIIs: "
        f"{cvm_total:,}"
    )

    print(
        f"Funds Explorer: "
        f"{funds_total:,}"
    )

    print(
        f"Linhas no FII Master: "
        f"{master_total:,}"
    )

    print(
        f"CNPJs únicos no Master: "
        f"{unique_master_cnpjs:,}"
    )

    print(
        f"Tickers únicos no Master: "
        f"{unique_master_tickers:,}"
    )

    print(
        f"CVM FIIs sem ticker: "
        f"{len(cvm_unmatched):,}"
    )

    print(
        f"Funds Explorer sem match CVM FII: "
        f"{len(funds_explorer_unmatched):,}"
    )

    print(
        f"Cobertura CVM por CNPJ: "
        f"{cvm_coverage:.2f}%"
    )

    print(
        f"Taxa de match Funds Explorer: "
        f"{funds_match_rate:.2f}%"
    )


def main() -> None:
    print(
        "Construindo FII Master..."
    )

    cvm_zip_path = find_latest_file(
        base_directory=(
            DEFAULT_CVM_RAW_DIR
        ),
        filename=(
            "registro_fundo_classe.zip"
        ),
    )

    funds_explorer_mapping_path = (
        find_latest_file(
            base_directory=(
                DEFAULT_FUNDS_EXPLORER_BRONZE_DIR
            ),
            filename=(
                "ticker_cnpj_mapping.csv"
            ),
        )
    )

    cvm_dataframe = (
        load_cvm_fii_classes(
            cvm_zip_path
        )
    )

    funds_explorer_dataframe = (
        load_funds_explorer_mapping(
            funds_explorer_mapping_path
        )
    )

    validate_sources(
        cvm_dataframe=(
            cvm_dataframe
        ),
        funds_explorer_dataframe=(
            funds_explorer_dataframe
        ),
    )

    (
        master,
        cvm_unmatched,
        funds_explorer_unmatched,
    ) = build_fii_master(
        cvm_dataframe=(
            cvm_dataframe
        ),
        funds_explorer_dataframe=(
            funds_explorer_dataframe
        ),
    )

    print_join_metrics(
        master=master,
        cvm_dataframe=(
            cvm_dataframe
        ),
        funds_explorer_dataframe=(
            funds_explorer_dataframe
        ),
        cvm_unmatched=(
            cvm_unmatched
        ),
        funds_explorer_unmatched=(
            funds_explorer_unmatched
        ),
    )

    print(
        "\nFII Master construído "
        "em memória com sucesso."
    )

    print(
        "Nenhum arquivo Silver "
        "foi persistido ainda."
    )


if __name__ == "__main__":
    main()