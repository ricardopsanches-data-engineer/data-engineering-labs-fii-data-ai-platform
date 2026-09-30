from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd

from src.analytics.fii_daily_snapshot.builder import (
    FII_DAILY_PRICES_BASE_DIR,
    FII_MASTER_PATH,
    PROJECT_ROOT,
    build_daily_snapshot,
    build_destination_path,
    calculate_analytical_columns,
    find_latest_daily_prices,
    load_daily_prices,
    load_fii_master,
    save_gold,
    select_gold_columns,
    validate_gold,
)
from src.storage.s3 import upload_file


BUCKET_NAME = os.environ.get(
    "FII_DATA_LAKE_BUCKET",
    "fii-data-ai-platform-dev-datalake-625685670804",
)


def build_s3_key(
    local_path: str | Path,
) -> str:
    """
    Converte o caminho local da camada Gold
    na chave equivalente do Data Lake S3.

    Exemplo:

        data/gold/analytics/fii_daily_snapshot/
        year=2026/month=08/day=27/
        fii_daily_snapshot.parquet

    vira:

        gold/analytics/fii_daily_snapshot/
        year=2026/month=08/day=27/
        fii_daily_snapshot.parquet
    """

    local_path = Path(local_path)

    data_root = (
        PROJECT_ROOT
        / "data"
    )

    try:
        relative_path = (
            local_path.relative_to(
                data_root
            )
        )

    except ValueError as error:
        raise ValueError(
            "O arquivo Gold precisa estar "
            f"dentro de {data_root}."
        ) from error

    return relative_path.as_posix()


def calculate_gold_content_sha256(
    dataframe: pd.DataFrame,
) -> str:
    """
    Calcula fingerprint lógico da Gold.

    O campo gold_created_at é excluído porque
    representa metadata operacional da execução
    e muda a cada processamento mesmo quando
    o conteúdo analítico permanece idêntico.

    O fingerprint considera:

    - nomes das colunas;
    - tipos das colunas;
    - valores das linhas;
    - ordenação determinística.
    """

    canonical = dataframe.copy()

    canonical = canonical.drop(
        columns=[
            "gold_created_at",
        ],
        errors="ignore",
    )

    sort_columns = [
        column
        for column in [
            "trade_date",
            "ticker",
        ]
        if column in canonical.columns
    ]

    if sort_columns:
        canonical = (
            canonical.sort_values(
                by=sort_columns,
                kind="stable",
            )
            .reset_index(
                drop=True
            )
        )

    schema_text = "|".join(
        f"{column}:{canonical[column].dtype}"
        for column in canonical.columns
    )

    row_hashes = (
        pd.util.hash_pandas_object(
            canonical,
            index=False,
        )
        .values
        .tobytes()
    )

    sha256 = hashlib.sha256()

    sha256.update(
        schema_text.encode(
            "utf-8"
        )
    )

    sha256.update(
        row_hashes
    )

    return sha256.hexdigest()


def build_gold_dataset() -> tuple[
    pd.DataFrame,
    Path,
]:
    """
    Executa a construção local da Gold
    FII Daily Snapshot reaproveitando
    integralmente o builder existente.
    """

    print(
        "======================================"
    )
    print(
        "FII DAILY SNAPSHOT -> S3"
    )
    print(
        "======================================"
    )

    prices_path = (
        find_latest_daily_prices(
            FII_DAILY_PRICES_BASE_DIR
        )
    )

    print(
        "\nSilver de preços mais recente: "
        f"{prices_path}"
    )

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

    snapshot = build_daily_snapshot(
        prices=prices,
        master=master,
    )

    print(
        "Snapshot após JOIN: "
        f"{len(snapshot):,} linhas"
    )

    snapshot = (
        calculate_analytical_columns(
            snapshot
        )
    )

    gold = select_gold_columns(
        snapshot
    )

    validate_gold(
        gold
    )

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
        "\nGold local criada: "
        f"{destination}"
    )

    return (
        gold,
        destination,
    )


def publish_gold(
    dataframe: pd.DataFrame,
    local_path: Path,
    force: bool = False,
) -> str:
    """
    Publica a Gold Analytics no Data Lake S3.

    O SHA físico continua sendo calculado
    automaticamente por src.storage.s3.

    O content_sha256 representa o conteúdo
    analítico lógico e permite distinguir:

    - nova execução do mesmo conteúdo;
    - mudança real nos dados Gold.
    """

    s3_key = build_s3_key(
        local_path
    )

    content_sha256 = (
        calculate_gold_content_sha256(
            dataframe
        )
    )

    print(
        "\nFingerprint lógico Gold | "
        f"content_sha256={content_sha256}"
    )

    print(
        "Destino S3 | "
        f"s3://{BUCKET_NAME}/{s3_key}"
    )

    return upload_file(
        local_path=local_path,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        content_sha256=content_sha256,
        force=force,
    )


def run(
    force: bool = False,
) -> str:
    """
    Constrói, valida e publica o
    FII Daily Snapshot no S3.
    """

    dataframe, local_path = (
        build_gold_dataset()
    )

    s3_uri = publish_gold(
        dataframe=dataframe,
        local_path=local_path,
        force=force,
    )

    print()
    print(
        "======================================"
    )
    print(
        "FII DAILY SNAPSHOT PUBLICADO"
    )
    print(
        "======================================"
    )

    print(
        f"Arquivo local: {local_path}"
    )

    print(
        f"Destino S3:   {s3_uri}"
    )

    print(
        f"Linhas:       {len(dataframe):,}"
    )

    print(
        "Tickers:      "
        f"{dataframe['ticker'].nunique():,}"
    )

    return s3_uri


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói e publica a Gold Analytics "
            "FII Daily Snapshot no Data Lake S3."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Permite explicitamente criar nova "
            "versão do objeto S3 mesmo quando "
            "já existe conteúdo publicado."
        ),
    )

    args = parser.parse_args()

    run(
        force=args.force,
    )


if __name__ == "__main__":
    main()