from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

B3_RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "b3"
)

B3_PARSER_PATH = (
    PROJECT_ROOT
    / "src"
    / "ingestion"
    / "b3"
    / "parser.py"
)

FII_MASTER_PATH = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "fii_master"
    / "fii_master.parquet"
)

SILVER_PRICES_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "fii_daily_prices"
)

B3_FILENAME_PATTERN = re.compile(
    r"b3_download_(\d{4})(\d{2})(\d{2})\.zip$"
)


def load_b3_parser():
    """
    Carrega dinamicamente o parser B3 já existente.

    Assim reutilizamos a ingestão que já foi
    desenvolvida e validada anteriormente.
    """

    spec = importlib.util.spec_from_file_location(
        "b3_parser",
        B3_PARSER_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Não foi possível carregar "
            f"{B3_PARSER_PATH}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def extract_date_from_b3_filename(
    path: Path,
) -> tuple[int, int, int]:
    """
    Extrai ano, mês e dia do nome:

    b3_download_20260827.zip
    """

    match = B3_FILENAME_PATTERN.search(
        path.name
    )

    if match is None:
        raise ValueError(
            f"Data não encontrada no nome "
            f"do arquivo: {path.name}"
        )

    year = int(
        match.group(1)
    )

    month = int(
        match.group(2)
    )

    day = int(
        match.group(3)
    )

    return (
        year,
        month,
        day,
    )


def find_latest_b3_download(
    base_directory: Path,
) -> Path:
    """
    Localiza o pregão RAW mais recente.
    """

    files = list(
        base_directory.rglob(
            "b3_download_*.zip"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo B3 encontrado "
            f"em {base_directory}"
        )

    files = sorted(
        files,
        key=lambda path: (
            extract_date_from_b3_filename(
                path
            )
        ),
        reverse=True,
    )

    return files[0]


def load_fii_master(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega o FII Master Silver.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"FII Master não encontrado: "
            f"{path}"
        )

    print(
        f"Carregando FII Master: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    required_columns = [
        "cnpj",
        "codigo_cvm",
        "ticker_current_candidate",
        "ticker_resolution_status",
        "market_evidence_confidence",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"no FII Master: "
            f"{missing_columns}"
        )

    dataframe[
        "ticker_current_candidate"
    ] = (
        dataframe[
            "ticker_current_candidate"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return dataframe


def load_b3_dataframe(
    path: Path,
) -> tuple[
    pd.DataFrame,
    dict[str, str],
]:
    """
    Reutiliza parse_b3_download() para
    transformar o ZIP RAW em DataFrame.
    """

    print(
        f"Carregando B3: "
        f"{path}"
    )

    parser = load_b3_parser()

    (
        dataframe,
        metadata,
    ) = parser.parse_b3_download(
        path
    )

    required_columns = [
        "trade_date",
        "ticker",
        "instrument_id",
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
        "trades_quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"na B3: {missing_columns}"
        )

    dataframe[
        "ticker"
    ] = (
        dataframe[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return (
        dataframe,
        metadata,
    )


def build_fii_daily_prices(
    b3: pd.DataFrame,
    master: pd.DataFrame,
) -> pd.DataFrame:
    """
    Mantém somente instrumentos B3 cujo ticker
    corresponde ao candidato atual do FII Master.
    """

    active_master = master[
        master[
            "ticker_current_candidate"
        ].notna()
    ].copy()

    master_mapping = active_master[
        [
            "cnpj",
            "codigo_cvm",
            "ticker_current_candidate",
            "ticker_resolution_status",
            "market_evidence_confidence",
        ]
    ].rename(
        columns={
            "ticker_current_candidate": (
                "ticker"
            ),
        }
    )

    if master_mapping[
        "ticker"
    ].duplicated().any():

        duplicates = master_mapping[
            master_mapping[
                "ticker"
            ].duplicated(
                keep=False
            )
        ].sort_values(
            by="ticker"
        )

        print(
            "\nTickers duplicados no FII Master:"
        )

        print(
            duplicates.to_string(
                index=False
            )
        )

        raise ValueError(
            "O FII Master contém ticker "
            "associado a mais de um CNPJ."
        )

    prices = b3.merge(
        master_mapping,
        how="inner",
        on="ticker",
        validate="many_to_one",
    )

    return prices


def select_silver_columns(
    dataframe: pd.DataFrame,
    source_file_name: str,
) -> pd.DataFrame:
    """
    Define o contrato da Silver de preços.
    """

    silver = dataframe[
        [
            "trade_date",
            "ticker",
            "cnpj",
            "codigo_cvm",
            "instrument_id",
            "open_price",
            "low_price",
            "high_price",
            "average_price",
            "close_price",
            "trades_quantity",
            "ticker_resolution_status",
            "market_evidence_confidence",
        ]
    ].copy()

    silver[
        "source"
    ] = "b3"

    silver[
        "source_file_name"
    ] = source_file_name

    silver[
        "ingestion_timestamp"
    ] = datetime.now(
        timezone.utc
    )

    return silver


def validate_fii_daily_prices(
    dataframe: pd.DataFrame,
) -> None:
    """
    Executa Data Quality antes da persistência.

    Não corrige silenciosamente problemas:
    qualquer violação crítica interrompe
    a criação da Silver.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - FII Daily Prices"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers únicos: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"CNPJs únicos: "
        f"{dataframe['cnpj'].nunique():,}"
    )

    # -----------------------------------------
    # Campos obrigatórios
    # -----------------------------------------

    null_ticker = dataframe[
        "ticker"
    ].isna().sum()

    null_trade_date = dataframe[
        "trade_date"
    ].isna().sum()

    null_cnpj = dataframe[
        "cnpj"
    ].isna().sum()

    print(
        f"Ticker nulo: "
        f"{null_ticker:,}"
    )

    print(
        f"Trade date nula: "
        f"{null_trade_date:,}"
    )

    print(
        f"CNPJ nulo: "
        f"{null_cnpj:,}"
    )

    if (
        null_ticker > 0
        or null_trade_date > 0
        or null_cnpj > 0
    ):
        raise ValueError(
            "Campos obrigatórios nulos "
            "encontrados."
        )

    # -----------------------------------------
    # Duplicidade da granularidade
    # -----------------------------------------

    duplicate_mask = dataframe.duplicated(
        subset=[
            "trade_date",
            "ticker",
        ],
        keep=False,
    )

    duplicate_count = (
        duplicate_mask.sum()
    )

    print(
        f"Duplicidades "
        f"(trade_date + ticker): "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:

        duplicates = dataframe[
            duplicate_mask
        ][
            [
                "trade_date",
                "ticker",
                "instrument_id",
                "open_price",
                "close_price",
            ]
        ].sort_values(
            by=[
                "trade_date",
                "ticker",
            ]
        )

        print(
            "\nRegistros duplicados:"
        )

        print(
            duplicates.to_string(
                index=False
            )
        )

        raise ValueError(
            "Granularidade ticker + trade_date "
            "não é única. Necessária investigação."
        )

    # -----------------------------------------
    # Preços
    # -----------------------------------------

    price_columns = [
        "open_price",
        "low_price",
        "high_price",
        "average_price",
        "close_price",
    ]

    invalid_price_mask = (
        dataframe[
            price_columns
        ]
        .le(0)
        .any(
            axis=1
        )
    )

    invalid_price_count = (
        invalid_price_mask.sum()
    )

    print(
        f"Linhas com preço <= 0: "
        f"{invalid_price_count:,}"
    )

    if invalid_price_count > 0:

        print(
            dataframe[
                invalid_price_mask
            ][
                [
                    "trade_date",
                    "ticker",
                    *price_columns,
                ]
            ].head(
                20
            ).to_string(
                index=False
            )
        )

        raise ValueError(
            "Preços inválidos encontrados."
        )

    # -----------------------------------------
    # Close dentro de low/high
    # -----------------------------------------

    invalid_range_mask = (
        (
            dataframe[
                "close_price"
            ]
            < dataframe[
                "low_price"
            ]
        )
        |
        (
            dataframe[
                "close_price"
            ]
            > dataframe[
                "high_price"
            ]
        )
    )

    invalid_range_count = (
        invalid_range_mask.sum()
    )

    print(
        f"Close fora de low/high: "
        f"{invalid_range_count:,}"
    )

    if invalid_range_count > 0:

        print(
            dataframe[
                invalid_range_mask
            ][
                [
                    "trade_date",
                    "ticker",
                    "low_price",
                    "close_price",
                    "high_price",
                ]
            ].head(
                20
            ).to_string(
                index=False
            )
        )

        raise ValueError(
            "Close price fora do intervalo "
            "low/high."
        )

    print(
        "\nData Quality aprovada."
    )


def validate_trade_date_against_file(
    dataframe: pd.DataFrame,
    b3_path: Path,
) -> None:
    """
    Confere se a data encontrada nos registros
    corresponde à data do arquivo RAW.
    """

    (
        year,
        month,
        day,
    ) = extract_date_from_b3_filename(
        b3_path
    )

    expected_date = pd.Timestamp(
        year=year,
        month=month,
        day=day,
    )

    trade_dates = (
        pd.to_datetime(
            dataframe[
                "trade_date"
            ]
        )
        .dt.normalize()
        .dropna()
        .unique()
    )

    if len(
        trade_dates
    ) != 1:

        raise ValueError(
            "Mais de uma trade_date encontrada "
            "na Silver."
        )

    actual_date = pd.Timestamp(
        trade_dates[0]
    )

    print(
        f"Data arquivo B3: "
        f"{expected_date.date()}"
    )

    print(
        f"Trade date dataset: "
        f"{actual_date.date()}"
    )

    if actual_date != expected_date:
        raise ValueError(
            "trade_date não corresponde "
            "à data do arquivo B3."
        )


def build_destination_path(
    b3_path: Path,
) -> Path:
    """
    Cria caminho Silver particionado:

    year=YYYY/month=MM/day=DD/
    """

    (
        year,
        month,
        day,
    ) = extract_date_from_b3_filename(
        b3_path
    )

    return (
        SILVER_PRICES_BASE_DIR
        / f"year={year}"
        / f"month={month:02d}"
        / f"day={day:02d}"
        / "fii_daily_prices.parquet"
    )


def save_silver(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste a Silver em Parquet.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        destination,
        index=False,
    )


def main() -> None:
    print(
        "Construindo Silver "
        "de preços diários de FIIs..."
    )

    # -----------------------------------------
    # 1. Último pregão B3
    # -----------------------------------------

    b3_path = find_latest_b3_download(
        B3_RAW_DIR
    )

    print(
        f"\nÚltimo pregão encontrado: "
        f"{b3_path.name}"
    )

    # -----------------------------------------
    # 2. FII Master
    # -----------------------------------------

    master = load_fii_master(
        FII_MASTER_PATH
    )

    master_with_ticker = master[
        master[
            "ticker_current_candidate"
        ].notna()
    ]

    print(
        f"FIIs no Master: "
        f"{len(master):,}"
    )

    print(
        f"FIIs com ticker candidato: "
        f"{len(master_with_ticker):,}"
    )

    # -----------------------------------------
    # 3. B3
    # -----------------------------------------

    (
        b3,
        metadata,
    ) = load_b3_dataframe(
        b3_path
    )

    print(
        f"Registros B3: "
        f"{len(b3):,}"
    )

    print(
        f"Tickers únicos B3: "
        f"{b3['ticker'].nunique():,}"
    )

    # -----------------------------------------
    # 4. Join B3 x Master
    # -----------------------------------------

    prices = build_fii_daily_prices(
        b3=b3,
        master=master,
    )

    print(
        "\nResultado B3 x FII Master:"
    )

    print(
        f"Linhas encontradas: "
        f"{len(prices):,}"
    )

    print(
        f"Tickers FIIs encontrados: "
        f"{prices['ticker'].nunique():,}"
    )

    # -----------------------------------------
    # 5. Contrato Silver
    # -----------------------------------------

    silver = select_silver_columns(
        dataframe=prices,
        source_file_name=(
            metadata[
                "xml_file"
            ]
        ),
    )

    # -----------------------------------------
    # 6. Data Quality
    # -----------------------------------------

    validate_trade_date_against_file(
        dataframe=silver,
        b3_path=b3_path,
    )

    validate_fii_daily_prices(
        silver
    )

    # -----------------------------------------
    # 7. Persistência
    # -----------------------------------------

    destination = build_destination_path(
        b3_path
    )

    save_silver(
        dataframe=silver,
        destination=destination,
    )

    print(
        "\n======================================"
    )

    print(
        "Silver FII Daily Prices criada"
    )

    print(
        "======================================"
    )

    print(
        f"Arquivo: "
        f"{destination}"
    )

    print(
        f"Linhas: "
        f"{len(silver):,}"
    )

    print(
        f"Tickers: "
        f"{silver['ticker'].nunique():,}"
    )


if __name__ == "__main__":
    main()