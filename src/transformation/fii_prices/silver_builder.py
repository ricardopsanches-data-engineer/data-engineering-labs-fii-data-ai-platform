from __future__ import annotations

import argparse
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

DEFAULT_DAYS = 5

B3_FILENAME_PATTERN = re.compile(
    r"b3_download_(\d{4})(\d{2})(\d{2})\.zip$"
)


def load_b3_parser():
    """
    Carrega dinamicamente o parser B3
    já existente no projeto.
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

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def format_b3_date(
    path: Path,
) -> str:
    """
    Retorna a data do arquivo no formato YYYY-MM-DD.
    """

    year, month, day = (
        extract_date_from_b3_filename(
            path
        )
    )

    return (
        f"{year:04d}-"
        f"{month:02d}-"
        f"{day:02d}"
    )


def find_latest_b3_downloads(
    base_directory: Path,
    limit: int,
) -> list[Path]:
    """
    Localiza os N arquivos RAW B3
    mais recentes disponíveis.
    """

    if limit <= 0:
        raise ValueError(
            "--days deve ser maior que zero."
        )

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
        key=extract_date_from_b3_filename,
        reverse=True,
    )

    return files[:limit]


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
    b3_parser,
) -> tuple[
    pd.DataFrame,
    dict[str, str],
]:
    """
    Reutiliza parse_b3_download()
    para transformar o RAW B3
    em DataFrame.
    """

    (
        dataframe,
        metadata,
    ) = b3_parser.parse_b3_download(
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
    Mantém somente instrumentos B3
    presentes no FII Master.
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

    duplicate_ticker_mask = (
        master_mapping[
            "ticker"
        ].duplicated(
            keep=False
        )
    )

    if duplicate_ticker_mask.any():

        duplicates = (
            master_mapping[
                duplicate_ticker_mask
            ]
            .sort_values(
                by="ticker"
            )
        )

        print(
            "\nTickers duplicados "
            "no FII Master:"
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
    Define o contrato da Silver
    de preços diários.
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


def validate_trade_date_against_file(
    dataframe: pd.DataFrame,
    b3_path: Path,
) -> None:
    """
    Confere se trade_date corresponde
    à data representada pelo arquivo RAW.
    """

    year, month, day = (
        extract_date_from_b3_filename(
            b3_path
        )
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
            "Mais de uma trade_date "
            "encontrada na Silver."
        )

    actual_date = pd.Timestamp(
        trade_dates[0]
    )

    if actual_date != expected_date:
        raise ValueError(
            "trade_date não corresponde "
            "à data do arquivo B3."
        )


def validate_fii_daily_prices(
    dataframe: pd.DataFrame,
) -> None:
    """
    Executa Data Quality antes
    da persistência.
    """

    null_ticker = (
        dataframe[
            "ticker"
        ]
        .isna()
        .sum()
    )

    null_trade_date = (
        dataframe[
            "trade_date"
        ]
        .isna()
        .sum()
    )

    null_cnpj = (
        dataframe[
            "cnpj"
        ]
        .isna()
        .sum()
    )

    if (
        null_ticker > 0
        or null_trade_date > 0
        or null_cnpj > 0
    ):
        raise ValueError(
            "Campos obrigatórios nulos."
        )

    duplicate_mask = dataframe.duplicated(
        subset=[
            "trade_date",
            "ticker",
        ],
        keep=False,
    )

    if duplicate_mask.any():

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
        ]

        print(
            "\nDuplicidades encontradas:"
        )

        print(
            duplicates.to_string(
                index=False
            )
        )

        raise ValueError(
            "Granularidade "
            "trade_date + ticker "
            "não é única."
        )

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

    if invalid_price_mask.any():

        print(
            dataframe[
                invalid_price_mask
            ][
                [
                    "trade_date",
                    "ticker",
                    *price_columns,
                ]
            ]
            .head(20)
            .to_string(
                index=False
            )
        )

        raise ValueError(
            "Preços <= 0 encontrados."
        )

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

    if invalid_range_mask.any():

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
            ]
            .head(20)
            .to_string(
                index=False
            )
        )

        raise ValueError(
            "Close price fora "
            "do intervalo low/high."
        )


def build_destination_path(
    b3_path: Path,
) -> Path:
    """
    Cria a partição Silver correspondente
    ao pregão processado.
    """

    year, month, day = (
        extract_date_from_b3_filename(
            b3_path
        )
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


def process_b3_file(
    b3_path: Path,
    master: pd.DataFrame,
    b3_parser,
) -> dict[str, object]:
    """
    Executa o fluxo completo para
    um único pregão.
    """

    reference_date = format_b3_date(
        b3_path
    )

    print(
        "\n--------------------------------------"
    )

    print(
        f"Processando pregão: "
        f"{reference_date}"
    )

    print(
        "--------------------------------------"
    )

    b3, metadata = load_b3_dataframe(
        path=b3_path,
        b3_parser=b3_parser,
    )

    print(
        f"Registros B3: "
        f"{len(b3):,}"
    )

    prices = build_fii_daily_prices(
        b3=b3,
        master=master,
    )

    print(
        f"FIIs encontrados: "
        f"{len(prices):,}"
    )

    silver = select_silver_columns(
        dataframe=prices,
        source_file_name=(
            metadata[
                "xml_file"
            ]
        ),
    )

    validate_trade_date_against_file(
        dataframe=silver,
        b3_path=b3_path,
    )

    validate_fii_daily_prices(
        silver
    )

    destination = build_destination_path(
        b3_path
    )

    save_silver(
        dataframe=silver,
        destination=destination,
    )

    print(
        "Data Quality: OK"
    )

    print(
        f"Silver salva em: "
        f"{destination}"
    )

    return {
        "trade_date": reference_date,
        "raw_records": len(b3),
        "fii_records": len(silver),
        "fii_tickers": (
            silver[
                "ticker"
            ].nunique()
        ),
        "destination": str(
            destination
        ),
        "status": "SUCCESS",
    }


def print_execution_summary(
    results: list[
        dict[str, object]
    ],
) -> None:
    """
    Exibe resumo da execução em lote.
    """

    print(
        "\n======================================"
    )

    print(
        "Resumo da materialização Silver"
    )

    print(
        "======================================"
    )

    for result in sorted(
        results,
        key=lambda item: str(
            item[
                "trade_date"
            ]
        ),
    ):

        print(
            f"{result['trade_date']} | "
            f"B3: {result['raw_records']:,} | "
            f"FIIs: {result['fii_records']:,} | "
            f"Tickers: {result['fii_tickers']:,} | "
            f"{result['status']}"
        )

    print(
        "\nPregões processados: "
        f"{len(results):,}"
    )


def main() -> None:
    cli_parser = argparse.ArgumentParser(
        description=(
            "Materializa a camada Silver "
            "de preços dos FIIs para os "
            "N pregões B3 mais recentes."
        )
    )

    cli_parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=(
            "Quantidade de pregões RAW B3 "
            "mais recentes a processar. "
            f"Padrão: {DEFAULT_DAYS}."
        ),
    )

    args = cli_parser.parse_args()

    print(
        "Construindo Silver "
        "de preços diários de FIIs..."
    )

    print(
        f"Quantidade solicitada: "
        f"{args.days} pregões"
    )

    b3_files = find_latest_b3_downloads(
        base_directory=B3_RAW_DIR,
        limit=args.days,
    )

    print(
        f"Arquivos RAW encontrados: "
        f"{len(b3_files)}"
    )

    print(
        "\nPregões selecionados:"
    )

    for path in reversed(
        b3_files
    ):
        print(
            f"  {format_b3_date(path)}"
        )

    master = load_fii_master(
        FII_MASTER_PATH
    )

    master_with_ticker = master[
        master[
            "ticker_current_candidate"
        ].notna()
    ]

    print(
        f"\nFIIs no Master: "
        f"{len(master):,}"
    )

    print(
        f"FIIs com ticker candidato: "
        f"{len(master_with_ticker):,}"
    )

    b3_parser = load_b3_parser()

    results: list[
        dict[str, object]
    ] = []

    # Ordenamos do pregão mais antigo
    # para o mais recente apenas para
    # facilitar leitura dos logs.
    files_to_process = sorted(
        b3_files,
        key=extract_date_from_b3_filename,
    )

    for b3_path in files_to_process:

        result = process_b3_file(
            b3_path=b3_path,
            master=master,
            b3_parser=b3_parser,
        )

        results.append(
            result
        )

    print_execution_summary(
        results
    )

    print(
        "\nMaterialização Silver "
        "concluída com sucesso."
    )


if __name__ == "__main__":
    main()