from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import pandas as pd


CVM_CLASS_FILE = "registro_classe.csv"
FII_CLASS_TYPE = "Classes de Cotas de Fundos FII"


def read_csv_with_encoding_fallback(
    csv_bytes: bytes,
) -> pd.DataFrame:
    """
    Lê um CSV da CVM tentando encodings conhecidos
    de forma determinística.

    Ordem de tentativa:
    - utf-8-sig
    - utf-8
    - cp1252
    - latin1
    """

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    ]

    last_error: UnicodeDecodeError | None = None

    for encoding in encodings:
        try:
            dataframe = pd.read_csv(
                io.BytesIO(csv_bytes),
                sep=";",
                dtype=str,
                encoding=encoding,
                low_memory=False,
            )

            print(f"Encoding utilizado: {encoding}")

            return dataframe

        except UnicodeDecodeError as error:
            last_error = error

    if last_error is not None:
        raise UnicodeDecodeError(
            last_error.encoding,
            last_error.object,
            last_error.start,
            last_error.end,
            (
                "Não foi possível ler o CSV da CVM "
                "com os encodings suportados."
            ),
        )

    raise RuntimeError(
        "Falha inesperada ao tentar identificar "
        "o encoding do arquivo CVM."
    )


def read_cvm_class_register(
    zip_path: str | Path,
) -> pd.DataFrame:
    """
    Lê o arquivo registro_classe.csv diretamente
    do ZIP da CVM.

    Parameters
    ----------
    zip_path:
        Caminho para o arquivo ZIP baixado da CVM.

    Returns
    -------
    pd.DataFrame
        DataFrame com todas as classes cadastradas.
    """

    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {zip_path}"
        )

    if not zipfile.is_zipfile(zip_path):
        raise ValueError(
            f"O arquivo informado não é um ZIP válido: {zip_path}"
        )

    with zipfile.ZipFile(zip_path, "r") as zip_file:
        file_names = zip_file.namelist()

        if CVM_CLASS_FILE not in file_names:
            raise FileNotFoundError(
                f"{CVM_CLASS_FILE} não encontrado "
                "dentro do ZIP."
            )

        csv_bytes = zip_file.read(
            CVM_CLASS_FILE
        )

    dataframe = read_csv_with_encoding_fallback(
        csv_bytes
    )

    return dataframe


def filter_fii_classes(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Filtra somente classes identificadas
    oficialmente pela CVM como FIIs.
    """

    if "Tipo_Classe" not in dataframe.columns:
        raise KeyError(
            "A coluna 'Tipo_Classe' não foi encontrada."
        )

    fii_dataframe = dataframe[
        dataframe["Tipo_Classe"].eq(
            FII_CLASS_TYPE
        )
    ].copy()

    return fii_dataframe


def select_fii_master_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Seleciona as colunas iniciais candidatas
    ao FII Master.

    Essa seleção ainda poderá ser refinada
    conforme evoluirmos a modelagem.
    """

    desired_columns = [
        "ID_Registro_Fundo",
        "ID_Registro_Classe",
        "CNPJ_Classe",
        "Codigo_CVM",
        "Tipo_Classe",
        "Denominacao_Social",
        "Situacao",
        "Data_Registro",
        "Data_Constituicao",
        "Data_Inicio",
        "Classificacao",
        "Forma_Condominio",
        "Patrimonio_Liquido",
        "Data_Patrimonio_Liquido",
    ]

    existing_columns = [
        column
        for column in desired_columns
        if column in dataframe.columns
    ]

    return dataframe[
        existing_columns
    ].copy()


def normalize_fii_master(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza os tipos de dados do cadastro de FIIs.

    Regras:
    - remove espaços extras em campos textuais;
    - interpreta datas no formato YYYY-MM-DD;
    - converte patrimônio líquido para número.
    """

    dataframe = dataframe.copy()

    text_columns = [
        "CNPJ_Classe",
        "Codigo_CVM",
        "Tipo_Classe",
        "Denominacao_Social",
        "Situacao",
        "Classificacao",
        "Forma_Condominio",
    ]

    for column in text_columns:
        if column in dataframe.columns:
            dataframe[column] = (
                dataframe[column]
                .astype("string")
                .str.strip()
            )

    date_columns = [
        "Data_Registro",
        "Data_Constituicao",
        "Data_Inicio",
        "Data_Patrimonio_Liquido",
    ]

    for column in date_columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(
                dataframe[column],
                format="%Y-%m-%d",
                errors="coerce",
            )

    if "Patrimonio_Liquido" in dataframe.columns:
        dataframe["Patrimonio_Liquido"] = pd.to_numeric(
            dataframe["Patrimonio_Liquido"],
            errors="coerce",
        )

    return dataframe


def parse_cvm_fii_register(
    zip_path: str | Path,
) -> pd.DataFrame:
    """
    Executa o fluxo completo da CVM.

    ZIP
        -> registro_classe.csv
        -> leitura com encoding resiliente
        -> filtro oficial de FIIs
        -> seleção de colunas
        -> normalização
        -> DataFrame
    """

    dataframe = read_cvm_class_register(
        zip_path
    )

    dataframe = filter_fii_classes(
        dataframe
    )

    dataframe = select_fii_master_columns(
        dataframe
    )

    dataframe = normalize_fii_master(
        dataframe
    )

    return dataframe


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parser do cadastro de classes de fundos "
            "da CVM para identificação de FIIs."
        )
    )

    parser.add_argument(
        "zip_path",
        help="Caminho para o ZIP cadastral da CVM.",
    )

    args = parser.parse_args()

    print("Lendo cadastro da CVM...")

    all_classes = read_cvm_class_register(
        args.zip_path
    )

    print(
        f"\nTotal de classes encontradas: "
        f"{len(all_classes):,}"
    )

    if "Tipo_Classe" not in all_classes.columns:
        raise KeyError(
            "A coluna 'Tipo_Classe' não existe "
            "no arquivo da CVM."
        )

    print("\nTipos de classe encontrados:")

    class_counts = (
        all_classes["Tipo_Classe"]
        .value_counts(
            dropna=False
        )
    )

    print(
        class_counts.to_string()
    )

    fii_dataframe = parse_cvm_fii_register(
        args.zip_path
    )

    print(
        f"\nFIIs encontrados: "
        f"{len(fii_dataframe):,}"
    )

    print("\nColunas selecionadas:")

    for column in fii_dataframe.columns:
        print(f"  - {column}")

    print("\nSituações cadastrais:")

    if "Situacao" in fii_dataframe.columns:
        situation_counts = (
            fii_dataframe["Situacao"]
            .value_counts(
                dropna=False
            )
        )

        print(
            situation_counts.to_string()
        )

    print("\nParser CVM concluído com sucesso.")


if __name__ == "__main__":
    main()