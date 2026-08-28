from __future__ import annotations

import importlib.util
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from builder import (
    DEFAULT_CVM_RAW_DIR,
    DEFAULT_FUNDS_EXPLORER_BRONZE_DIR,
    find_latest_file,
    load_cvm_fii_classes,
    load_funds_explorer_mapping,
)


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

SILVER_BASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "silver"
)

B3_FILENAME_PATTERN = re.compile(
    r"b3_download_(\d{8})\.zip$"
)


def load_b3_parser():
    """
    Carrega o parser da B3 já existente.
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
) -> str:
    """
    Extrai YYYYMMDD de:

    b3_download_20260827.zip
    """

    match = B3_FILENAME_PATTERN.search(
        path.name
    )

    if match is None:
        raise ValueError(
            f"Data não encontrada em "
            f"{path.name}"
        )

    return match.group(1)


def find_latest_b3_downloads(
    base_directory: Path,
    limit: int = 5,
) -> list[Path]:
    """
    Retorna os N pregões RAW mais recentes.
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
        key=extract_date_from_b3_filename,
        reverse=True,
    )

    return files[:limit]


def normalize_b3_tickers(
    dataframe: pd.DataFrame,
) -> set[str]:
    """
    Retorna os tickers únicos de um pregão.
    """

    if "ticker" not in dataframe.columns:
        raise ValueError(
            "Coluna 'ticker' ausente "
            "no DataFrame B3."
        )

    tickers = (
        dataframe["ticker"]
        .dropna()
        .astype("string")
        .str.strip()
        .str.upper()
    )

    tickers = tickers[
        tickers != ""
    ]

    return set(
        tickers.tolist()
    )


def build_market_evidence(
    b3_files: list[Path],
) -> tuple[
    dict[str, int],
    dict[str, list[str]],
]:
    """
    Calcula em quantos pregões cada ticker
    apareceu.
    """

    parser = load_b3_parser()

    ticker_days: dict[
        str,
        int
    ] = defaultdict(int)

    ticker_dates: dict[
        str,
        list[str]
    ] = defaultdict(list)

    print(
        "\nProcessando evidência B3..."
    )

    for index, path in enumerate(
        b3_files,
        start=1,
    ):
        reference_date = (
            extract_date_from_b3_filename(
                path
            )
        )

        print(
            f"[{index}/{len(b3_files)}] "
            f"Pregão {reference_date}"
        )

        (
            dataframe,
            _,
        ) = parser.parse_b3_download(
            path
        )

        tickers = normalize_b3_tickers(
            dataframe
        )

        for ticker in tickers:
            ticker_days[
                ticker
            ] += 1

            ticker_dates[
                ticker
            ].append(
                reference_date
            )

    return (
        dict(ticker_days),
        dict(ticker_dates),
    )


def get_cvm_conflicts(
    cvm: pd.DataFrame,
) -> pd.DataFrame:
    """
    Identifica CNPJs repetidos na CVM.

    Esses registros não serão resolvidos
    silenciosamente.
    """

    conflicts = cvm[
        cvm["cnpj"].duplicated(
            keep=False
        )
    ].copy()

    return conflicts.sort_values(
        by=[
            "cnpj",
            "Codigo_CVM",
        ]
    ).reset_index(
        drop=True
    )


def remove_cvm_conflicts(
    cvm: pd.DataFrame,
    conflicts: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove temporariamente CNPJs conflitantes
    do conjunto apto para construir a Silver.
    """

    if conflicts.empty:
        return cvm.copy()

    conflicting_cnpjs = set(
        conflicts[
            "cnpj"
        ].dropna()
    )

    return cvm[
        ~cvm[
            "cnpj"
        ].isin(
            conflicting_cnpjs
        )
    ].copy()


def build_ticker_history(
    cvm: pd.DataFrame,
    funds: pd.DataFrame,
    ticker_days: dict[str, int],
    ticker_dates: dict[str, list[str]],
    window_size: int,
) -> pd.DataFrame:
    """
    Constrói todas as relações conhecidas
    entre identidade legal e ticker.
    """

    joined = cvm.merge(
        funds,
        how="inner",
        on="cnpj",
        validate="one_to_many",
    )

    history = joined[
        [
            "cnpj",
            "Codigo_CVM",
            "Denominacao_Social",
            "Situacao",
            "ticker",
            "fund_name",
            "category_status",
            "source",
        ]
    ].copy()

    history[
        "market_evidence_days"
    ] = (
        history[
            "ticker"
        ]
        .map(
            ticker_days
        )
        .fillna(0)
        .astype(int)
    )

    history[
        "market_evidence_window"
    ] = window_size

    history[
        "market_evidence_ratio"
    ] = (
        history[
            "market_evidence_days"
        ]
        / window_size
    )

    history[
        "market_evidence_dates"
    ] = history[
        "ticker"
    ].map(
        lambda ticker: ",".join(
            ticker_dates.get(
                ticker,
                [],
            )
        )
    )

    return history.sort_values(
        by=[
            "cnpj",
            "ticker",
        ]
    ).reset_index(
        drop=True
    )


def confidence_from_days(
    days: int,
    window_size: int,
) -> str:
    """
    Classificação simples da evidência B3.
    """

    if days == 0:
        return "NO_EVIDENCE"

    ratio = (
        days
        / window_size
    )

    if ratio >= 0.8:
        return "HIGH"

    if ratio >= 0.4:
        return "MEDIUM"

    return "LOW"


def resolve_current_tickers(
    history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Define o candidato de ticker atual
    para cada CNPJ.

    Regras:

    1 ticker conhecido:
        SINGLE_TICKER

    múltiplos tickers e somente um com
    evidência B3:
        RESOLVED_BY_B3

    nenhum ticker com evidência:
        NO_MARKET_EVIDENCE

    mais de um ticker com evidência:
        MULTIPLE_ACTIVE_CANDIDATES
    """

    records: list[
        dict[str, object]
    ] = []

    for cnpj, group in history.groupby(
        "cnpj"
    ):
        group = group.copy()

        ticker_count = group[
            "ticker"
        ].nunique()

        active = group[
            group[
                "market_evidence_days"
            ] > 0
        ].copy()

        current_ticker = None
        status = None
        evidence_days = 0
        evidence_window = int(
            group[
                "market_evidence_window"
            ].iloc[0]
        )

        if ticker_count == 1:
            row = group.iloc[0]

            current_ticker = row[
                "ticker"
            ]

            evidence_days = int(
                row[
                    "market_evidence_days"
                ]
            )

            status = "SINGLE_TICKER"

        elif len(active) == 1:
            row = active.iloc[0]

            current_ticker = row[
                "ticker"
            ]

            evidence_days = int(
                row[
                    "market_evidence_days"
                ]
            )

            status = "RESOLVED_BY_B3"

        elif len(active) == 0:
            status = (
                "NO_MARKET_EVIDENCE"
            )

        else:
            status = (
                "MULTIPLE_ACTIVE_CANDIDATES"
            )

        confidence = confidence_from_days(
            days=evidence_days,
            window_size=evidence_window,
        )

        first = group.iloc[0]

        records.append(
            {
                "cnpj": cnpj,
                "codigo_cvm": (
                    first[
                        "Codigo_CVM"
                    ]
                ),
                "denominacao_social": (
                    first[
                        "Denominacao_Social"
                    ]
                ),
                "situacao_cvm": (
                    first[
                        "Situacao"
                    ]
                ),
                "ticker_current_candidate": (
                    current_ticker
                ),
                "ticker_resolution_status": (
                    status
                ),
                "market_evidence_days": (
                    evidence_days
                ),
                "market_evidence_window": (
                    evidence_window
                ),
                "market_evidence_confidence": (
                    confidence
                ),
            }
        )

    master = pd.DataFrame(
        records
    )

    return master.sort_values(
        by="cnpj"
    ).reset_index(
        drop=True
    )


def mark_current_candidate(
    history: pd.DataFrame,
    master: pd.DataFrame,
) -> pd.DataFrame:
    """
    Marca no histórico qual ticker foi
    selecionado como candidato atual.
    """

    current_mapping = (
        master[
            [
                "cnpj",
                "ticker_current_candidate",
                "ticker_resolution_status",
            ]
        ]
        .copy()
    )

    result = history.merge(
        current_mapping,
        how="left",
        on="cnpj",
        validate="many_to_one",
    )

    result[
        "is_current_candidate"
    ] = (
        result[
            "ticker"
        ]
        == result[
            "ticker_current_candidate"
        ]
    )

    result[
        "market_evidence_confidence"
    ] = result.apply(
        lambda row: confidence_from_days(
            int(
                row[
                    "market_evidence_days"
                ]
            ),
            int(
                row[
                    "market_evidence_window"
                ]
            ),
        ),
        axis=1,
    )

    result = result.rename(
        columns={
            "Codigo_CVM": "codigo_cvm",
            "Denominacao_Social": (
                "denominacao_social"
            ),
            "Situacao": "situacao_cvm",
            "fund_name": (
                "fund_name_commercial"
            ),
            "category_status": (
                "status_fundsexplorer"
            ),
            "source": "source_ticker",
        }
    )

    return result


def add_metadata(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adiciona metadados técnicos da Silver.
    """

    dataframe = dataframe.copy()

    dataframe[
        "silver_created_at"
    ] = datetime.now(
        timezone.utc
    )

    return dataframe


def validate_silver_master(
    master: pd.DataFrame,
) -> None:
    """
    Data Quality mínima antes da persistência.
    """

    if master.empty:
        raise ValueError(
            "FII Master vazio."
        )

    if master[
        "cnpj"
    ].isna().any():
        raise ValueError(
            "FII Master contém CNPJ nulo."
        )

    if master[
        "cnpj"
    ].duplicated().any():
        raise ValueError(
            "FII Master contém CNPJ duplicado."
        )

    print(
        "\nData Quality FII Master:"
    )

    print(
        f"Linhas: "
        f"{len(master):,}"
    )

    print(
        f"CNPJs únicos: "
        f"{master['cnpj'].nunique():,}"
    )

    print(
        f"Ticker candidato definido: "
        f"{master['ticker_current_candidate'].notna().sum():,}"
    )

    print(
        f"Sem ticker candidato: "
        f"{master['ticker_current_candidate'].isna().sum():,}"
    )


def save_parquet(
    dataframe: pd.DataFrame,
    destination: Path,
) -> None:
    """
    Persiste um DataFrame em Parquet.
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
        "Construindo camada Silver "
        "do FII Master..."
    )

    # -----------------------------------------
    # CVM
    # -----------------------------------------

    cvm_zip_path = find_latest_file(
        base_directory=(
            DEFAULT_CVM_RAW_DIR
        ),
        filename=(
            "registro_fundo_classe.zip"
        ),
    )

    cvm = load_cvm_fii_classes(
        cvm_zip_path
    )

    # -----------------------------------------
    # Funds Explorer
    # -----------------------------------------

    funds_path = find_latest_file(
        base_directory=(
            DEFAULT_FUNDS_EXPLORER_BRONZE_DIR
        ),
        filename=(
            "ticker_cnpj_mapping.csv"
        ),
    )

    funds = load_funds_explorer_mapping(
        funds_path
    )

    # -----------------------------------------
    # Conflitos CVM
    # -----------------------------------------

    cvm_conflicts = get_cvm_conflicts(
        cvm
    )

    print(
        f"\nCNPJs conflitantes na CVM: "
        f"{cvm_conflicts['cnpj'].nunique():,}"
    )

    cvm_clean = remove_cvm_conflicts(
        cvm=cvm,
        conflicts=cvm_conflicts,
    )

    # -----------------------------------------
    # Evidência temporal B3
    # -----------------------------------------

    b3_files = find_latest_b3_downloads(
        base_directory=B3_RAW_DIR,
        limit=5,
    )

    print(
        "\nPregões usados:"
    )

    for path in reversed(
        b3_files
    ):
        print(
            f"  "
            f"{extract_date_from_b3_filename(path)}"
        )

    (
        ticker_days,
        ticker_dates,
    ) = build_market_evidence(
        b3_files
    )

    # -----------------------------------------
    # Histórico ticker
    # -----------------------------------------

    history = build_ticker_history(
        cvm=cvm_clean,
        funds=funds,
        ticker_days=ticker_days,
        ticker_dates=ticker_dates,
        window_size=len(
            b3_files
        ),
    )

    # -----------------------------------------
    # Master
    # -----------------------------------------

    master = resolve_current_tickers(
        history
    )

    history = mark_current_candidate(
        history=history,
        master=master,
    )

    master = add_metadata(
        master
    )

    history = add_metadata(
        history
    )

    if not cvm_conflicts.empty:
        cvm_conflicts = add_metadata(
            cvm_conflicts
        )

    # -----------------------------------------
    # Data Quality
    # -----------------------------------------

    validate_silver_master(
        master
    )

    # -----------------------------------------
    # Persistência
    # -----------------------------------------

    master_path = (
        SILVER_BASE_DIR
        / "fii_master"
        / "fii_master.parquet"
    )

    history_path = (
        SILVER_BASE_DIR
        / "fii_ticker_history"
        / "fii_ticker_history.parquet"
    )

    conflicts_path = (
        SILVER_BASE_DIR
        / "fii_master_conflicts"
        / "cvm_cnpj_conflicts.parquet"
    )

    save_parquet(
        master,
        master_path,
    )

    save_parquet(
        history,
        history_path,
    )

    if not cvm_conflicts.empty:
        save_parquet(
            cvm_conflicts,
            conflicts_path,
        )

    print(
        "\n======================================"
    )
    print(
        "Silver criada com sucesso"
    )
    print(
        "======================================"
    )

    print(
        f"FII Master: "
        f"{master_path}"
    )

    print(
        f"Ticker History: "
        f"{history_path}"
    )

    if not cvm_conflicts.empty:
        print(
            f"CVM Conflicts: "
            f"{conflicts_path}"
        )


if __name__ == "__main__":
    main()