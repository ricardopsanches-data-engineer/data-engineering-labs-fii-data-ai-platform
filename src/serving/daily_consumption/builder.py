from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.fii_daily_snapshot.builder import (
    GOLD_BASE_DIR,
    PROJECT_ROOT,
)

DATASET_NAME = "fii_daily_snapshot"

SERVING_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "serving"
    / "daily"
)

LATEST_SNAPSHOT_PATH = (
    SERVING_BASE_DIR
    / "latest_snapshot.json"
)

SNAPSHOT_FILENAME = "fii_daily_snapshot.parquet"

PARTITION_PATTERN = re.compile(
    r"year=(\d{4}).*month=(\d{2}).*day=(\d{2})"
)

REQUIRED_COLUMNS = [
    "trade_date",
    "ticker",
    "cnpj",
    "codigo_cvm",
    "denominacao_social",
    "close_price",
]


def extract_partition_date(
    path: Path,
) -> pd.Timestamp:
    """
    Extrai a data da partição física do snapshot.

    Esperado:

        year=YYYY/month=MM/day=DD
    """

    match = PARTITION_PATTERN.search(
        str(path.parent)
    )

    if match is None:
        raise ValueError(
            "Não foi possível extrair a data "
            f"da partição: {path}"
        )

    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))

    return pd.Timestamp(
        year=year,
        month=month,
        day=day,
    )


def find_latest_snapshot(
    base_directory: Path = GOLD_BASE_DIR,
) -> Path:
    """
    Localiza o snapshot Gold Analytics
    mais recente pela data da partição.

    Não usa timestamp do arquivo.

    A ordenação é feita exclusivamente pela
    data de negócio representada em:

        year=YYYY/month=MM/day=DD
    """

    files = list(
        base_directory.rglob(
            SNAPSHOT_FILENAME
        )
    )

    if not files:
        raise FileNotFoundError(
            "Nenhum FII Daily Snapshot "
            f"encontrado em {base_directory}"
        )

    files = sorted(
        files,
        key=extract_partition_date,
        reverse=True,
    )

    return files[0]


def load_snapshot(
    path: Path,
) -> pd.DataFrame:
    """
    Carrega o snapshot candidato à camada
    diária de serving.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Snapshot não encontrado: {path}"
        )

    dataframe = pd.read_parquet(
        path
    )

    return dataframe


def validate_required_columns(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida contrato mínimo necessário para
    consumo downstream.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Daily Consumption Layer recebeu "
            "snapshot sem colunas obrigatórias: "
            f"{missing_columns}"
        )


def resolve_trade_date(
    dataframe: pd.DataFrame,
) -> pd.Timestamp:
    """
    Resolve a única trade_date existente
    no snapshot.
    """

    trade_dates = (
        pd.to_datetime(
            dataframe["trade_date"],
            errors="coerce",
        )
        .dt.normalize()
        .dropna()
        .unique()
    )

    if len(trade_dates) != 1:
        raise ValueError(
            "O snapshot de consumo diário deve "
            "conter exatamente uma trade_date."
        )

    return pd.Timestamp(
        trade_dates[0]
    )


def validate_partition_matches_trade_date(
    path: Path,
    trade_date: pd.Timestamp,
) -> None:
    """
    Garante que a data física da partição
    corresponde à trade_date interna.
    """

    partition_date = extract_partition_date(
        path
    )

    if partition_date.normalize() != (
        trade_date.normalize()
    ):
        raise ValueError(
            "Partição física não corresponde "
            "à trade_date do snapshot. "
            f"partition_date={partition_date.date()} "
            f"trade_date={trade_date.date()}"
        )


def validate_snapshot(
    dataframe: pd.DataFrame,
    path: Path,
) -> pd.Timestamp:
    """
    Executa as validações mínimas necessárias
    antes de declarar o snapshot READY.
    """

    if dataframe.empty:
        raise ValueError(
            "Daily Consumption Layer recebeu "
            "snapshot vazio."
        )

    validate_required_columns(
        dataframe
    )

    required_nulls = (
        dataframe[
            REQUIRED_COLUMNS
        ]
        .isna()
        .sum()
    )

    if (
        required_nulls > 0
    ).any():
        raise ValueError(
            "Daily Consumption Layer encontrou "
            "campos obrigatórios nulos."
        )

    duplicate_count = (
        dataframe.duplicated(
            subset=[
                "trade_date",
                "ticker",
            ],
            keep=False,
        )
        .sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Daily Consumption Layer encontrou "
            "duplicidade em "
            "(trade_date, ticker)."
        )

    trade_date = resolve_trade_date(
        dataframe
    )

    validate_partition_matches_trade_date(
        path=path,
        trade_date=trade_date,
    )

    return trade_date


def build_relative_local_path(
    snapshot_path: Path,
) -> str:
    """
    Retorna caminho relativo ao root do projeto.
    """

    try:
        relative_path = (
            snapshot_path.resolve()
            .relative_to(
                PROJECT_ROOT.resolve()
            )
        )
    except ValueError as error:
        raise ValueError(
            "Snapshot precisa estar dentro "
            "do diretório do projeto."
        ) from error

    return relative_path.as_posix()


def build_s3_key(
    snapshot_path: Path,
) -> str:
    """
    Converte:

        data/gold/analytics/...

    em:

        gold/analytics/...
    """

    data_root = (
        PROJECT_ROOT
        / "data"
    )

    try:
        relative_path = (
            snapshot_path.resolve()
            .relative_to(
                data_root.resolve()
            )
        )
    except ValueError as error:
        raise ValueError(
            "Snapshot precisa estar dentro "
            f"de {data_root}."
        ) from error

    return relative_path.as_posix()


def build_manifest(
    dataframe: pd.DataFrame,
    snapshot_path: Path,
    trade_date: pd.Timestamp,
) -> dict[str, Any]:
    """
    Constrói o contrato da Daily Consumption Layer.

    O manifesto não duplica o dataset.
    Ele apenas referencia o último snapshot
    validado e pronto para consumo.
    """

    generated_at = datetime.now(
        UTC
    )

    return {
        "dataset": DATASET_NAME,
        "status": "READY",
        "trade_date": (
            trade_date
            .date()
            .isoformat()
        ),
        "row_count": int(
            len(dataframe)
        ),
        "ticker_count": int(
            dataframe["ticker"].nunique()
        ),
        "local_path": (
            build_relative_local_path(
                snapshot_path
            )
        ),
        "s3_key": (
            build_s3_key(
                snapshot_path
            )
        ),
        "generated_at": (
            generated_at.isoformat()
        ),
    }


def save_manifest(
    manifest: dict[str, Any],
    destination: Path = LATEST_SNAPSHOT_PATH,
) -> None:
    """
    Persiste o latest pointer de forma
    determinística em JSON.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_daily_consumption_layer(
    gold_base_directory: Path = GOLD_BASE_DIR,
    destination: Path = LATEST_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """
    Resolve o último snapshot Gold confiável,
    valida o contrato e materializa apenas
    o ponteiro de consumo diário.
    """

    print(
        "======================================"
    )
    print(
        "DAILY CONSUMPTION LAYER"
    )
    print(
        "======================================"
    )

    snapshot_path = find_latest_snapshot(
        gold_base_directory
    )

    print(
        "\nSnapshot candidato:"
    )
    print(
        snapshot_path
    )

    dataframe = load_snapshot(
        snapshot_path
    )

    trade_date = validate_snapshot(
        dataframe=dataframe,
        path=snapshot_path,
    )

    manifest = build_manifest(
        dataframe=dataframe,
        snapshot_path=snapshot_path,
        trade_date=trade_date,
    )

    save_manifest(
        manifest=manifest,
        destination=destination,
    )

    print()
    print(
        "======================================"
    )
    print(
        "DAILY CONSUMPTION READY"
    )
    print(
        "======================================"
    )

    print(
        f"Trade date:    "
        f"{manifest['trade_date']}"
    )

    print(
        f"Linhas:        "
        f"{manifest['row_count']:,}"
    )

    print(
        f"Tickers:       "
        f"{manifest['ticker_count']:,}"
    )

    print(
        f"Snapshot:      "
        f"{manifest['local_path']}"
    )

    print(
        f"Serving file:  "
        f"{destination}"
    )

    return manifest


def main() -> None:
    build_daily_consumption_layer()


if __name__ == "__main__":
    main()