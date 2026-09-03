from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

FII_MASTER_PATH = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "fii_master"
    / "fii_master.parquet"
)

FII_DAILY_PRICES_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "fii_daily_prices"
)

GOLD_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "analytics"
    / "fii_daily_snapshot"
)

PARTITION_PATTERN = re.compile(
    r"year=(\d{4}).*month=(\d{2}).*day=(\d{2})"
)


def find_latest_daily_prices(
    base_directory: Path,
) -> Path:
    """
    Localiza o parquet Silver de preços
    mais recente.
    """

    files = list(
        base_directory.rglob(
            "fii_daily_prices.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"Nenhum fii_daily_prices.parquet "
            f"encontrado em {base_directory}"
        )

    def extract_partition_date(
        path: Path,
    ) -> tuple[int, int, int]:
        path_text = str(
            path.parent
        )

        match = PARTITION_PATTERN.search(
            path_text
        )

        if match is None:
            raise ValueError(
                f"Não foi possível extrair "
                f"data da partição: {path}"
            )

        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

    files = sorted(
        files,
        key=extract_partition_date,
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
        "denominacao_social",
        "situacao_cvm",
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

    return dataframe


def load_daily_prices(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega a Silver de preços.
    """

    print(
        f"Carregando preços Silver: "
        f"{path}"
    )

    dataframe = pd.read_parquet(
        path
    )

    required_columns = [
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
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            f"na Silver de preços: "
            f"{missing_columns}"
        )

    return dataframe


def build_daily_snapshot(
    prices: pd.DataFrame,
    master: pd.DataFrame,
) -> pd.DataFrame:
    """
    Consolida identidade + preço em uma
    visão analítica diária.
    """

    master_dimension = master[
        [
            "cnpj",
            "codigo_cvm",
            "denominacao_social",
            "situacao_cvm",
            "ticker_current_candidate",
            "ticker_resolution_status",
            "market_evidence_confidence",
        ]
    ].copy()

    master_dimension = (
        master_dimension.rename(
            columns={
                "ticker_current_candidate": (
                    "ticker_master"
                ),
                "ticker_resolution_status": (
                    "ticker_resolution_status_master"
                ),
                "market_evidence_confidence": (
                    "market_evidence_confidence_master"
                ),
            }
        )
    )

    snapshot = prices.merge(
        master_dimension,
        how="left",
        on=[
            "cnpj",
            "codigo_cvm",
        ],
        validate="many_to_one",
    )

    return snapshot


def calculate_analytical_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adiciona métricas simples e úteis
    para consumo analítico.

    Ainda não estamos calculando retorno
    contra D-1 porque isso exige histórico
    diário acumulado.
    """

    result = dataframe.copy()

    result[
        "intraday_variation"
    ] = (
        result[
            "close_price"
        ]
        - result[
            "open_price"
        ]
    )

    result[
        "intraday_variation_pct"
    ] = (
        (
            result[
                "close_price"
            ]
            / result[
                "open_price"
            ]
        )
        - 1
    ) * 100

    result[
        "price_range"
    ] = (
        result[
            "high_price"
        ]
        - result[
            "low_price"
        ]
    )

    result[
        "price_range_pct"
    ] = (
        result[
            "price_range"
        ]
        / result[
            "low_price"
        ]
    ) * 100

    return result


def select_gold_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Define o contrato final da Gold
    analítica.
    """

    gold = dataframe[
        [
            "trade_date",
            "ticker",
            "cnpj",
            "codigo_cvm",
            "denominacao_social",
            "situacao_cvm",
            "instrument_id",
            "open_price",
            "low_price",
            "high_price",
            "average_price",
            "close_price",
            "trades_quantity",
            "intraday_variation",
            "intraday_variation_pct",
            "price_range",
            "price_range_pct",
            "ticker_resolution_status_master",
            "market_evidence_confidence_master",
        ]
    ].copy()

    gold = gold.rename(
        columns={
            "ticker_resolution_status_master": (
                "ticker_resolution_status"
            ),
            "market_evidence_confidence_master": (
                "market_evidence_confidence"
            ),
        }
    )

    gold[
        "gold_created_at"
    ] = datetime.now(
        timezone.utc
    )

    return gold


def validate_gold(
    dataframe: pd.DataFrame,
) -> None:
    """
    Data Quality da camada Gold.
    """

    print(
        "\n======================================"
    )
    print(
        "Data Quality - FII Daily Snapshot"
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

    required_columns = [
        "trade_date",
        "ticker",
        "cnpj",
        "codigo_cvm",
        "denominacao_social",
        "close_price",
    ]

    null_counts = (
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
    )

    print(
        "\nCampos obrigatórios nulos:"
    )

    for column, count in null_counts.items():
        print(
            f"  {column}: "
            f"{count:,}"
        )

    if (
        null_counts
        > 0
    ).any():
        raise ValueError(
            "Gold contém campos "
            "obrigatórios nulos."
        )

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
        f"\nDuplicidades "
        f"(trade_date + ticker): "
        f"{duplicate_count:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Gold contém duplicidade "
            "na granularidade diária."
        )

    invalid_intraday = (
        dataframe[
            "intraday_variation_pct"
        ]
        .isna()
        .sum()
    )

    invalid_range = (
        dataframe[
            "price_range_pct"
        ]
        .isna()
        .sum()
    )

    print(
        f"Intraday variation nula: "
        f"{invalid_intraday:,}"
    )

    print(
        f"Price range nulo: "
        f"{invalid_range:,}"
    )

    if (
        invalid_intraday > 0
        or invalid_range > 0
    ):
        raise ValueError(
            "Métricas analíticas nulas "
            "encontradas."
        )

    print(
        "\nData Quality aprovada."
    )


def build_destination_path(
    dataframe: pd.DataFrame,
) -> Path:
    """
    Define partição Gold com base
    na trade_date.
    """

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
            "A Gold diária deve conter "
            "uma única trade_date."
        )

    trade_date = pd.Timestamp(
        trade_dates[0]
    )

    return (
        GOLD_BASE_DIR
        / f"year={trade_date.year}"
        / f"month={trade_date.month:02d}"
        / f"day={trade_date.day:02d}"
        / "fii_daily_snapshot.parquet"
    )


def save_gold(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste a Gold em Parquet.
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
        "Construindo Gold "
        "FII Daily Snapshot..."
    )

    # -----------------------------------------
    # 1. Localizar Silver mais recente
    # -----------------------------------------

    prices_path = find_latest_daily_prices(
        FII_DAILY_PRICES_BASE_DIR
    )

    print(
        f"\nSilver de preços mais recente: "
        f"{prices_path}"
    )

    # -----------------------------------------
    # 2. Carregar datasets
    # -----------------------------------------

    master = load_fii_master(
        FII_MASTER_PATH
    )

    prices = load_daily_prices(
        prices_path
    )

    print(
        f"\nFII Master: "
        f"{len(master):,} linhas"
    )

    print(
        f"Silver preços: "
        f"{len(prices):,} linhas"
    )

    # -----------------------------------------
    # 3. Construir snapshot
    # -----------------------------------------

    snapshot = build_daily_snapshot(
        prices=prices,
        master=master,
    )

    print(
        f"Snapshot após JOIN: "
        f"{len(snapshot):,} linhas"
    )

    # -----------------------------------------
    # 4. Métricas analíticas
    # -----------------------------------------

    snapshot = (
        calculate_analytical_columns(
            snapshot
        )
    )

    # -----------------------------------------
    # 5. Contrato Gold
    # -----------------------------------------

    gold = select_gold_columns(
        snapshot
    )

    # -----------------------------------------
    # 6. Data Quality
    # -----------------------------------------

    validate_gold(
        gold
    )

    # -----------------------------------------
    # 7. Persistência
    # -----------------------------------------

    destination = (
        build_destination_path(
            gold
        )
    )

    save_gold(
        dataframe=gold,
        destination=destination,
    )

    print(
        "\n======================================"
    )
    print(
        "Gold FII Daily Snapshot criada"
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
        f"{len(gold):,}"
    )

    print(
        f"Tickers: "
        f"{gold['ticker'].nunique():,}"
    )


if __name__ == "__main__":
    main()