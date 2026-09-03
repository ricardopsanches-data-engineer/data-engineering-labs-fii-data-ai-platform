from __future__ import annotations

import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from builder import (
    DEFAULT_CVM_RAW_DIR,
    DEFAULT_FUNDS_EXPLORER_BRONZE_DIR,
    build_fii_master,
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

B3_FILENAME_PATTERN = re.compile(
    r"b3_download_(\d{8})\.zip$"
)


def load_b3_parser():
    """
    Carrega dinamicamente o parser da B3 já existente.
    """

    spec = importlib.util.spec_from_file_location(
        "b3_parser",
        B3_PARSER_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Não foi possível carregar: "
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
    Extrai YYYYMMDD do nome:

    b3_download_20260827.zip
    """

    match = B3_FILENAME_PATTERN.search(
        path.name
    )

    if match is None:
        raise ValueError(
            f"Data não encontrada no arquivo: "
            f"{path.name}"
        )

    return match.group(1)


def find_latest_b3_downloads(
    base_directory: Path,
    limit: int = 5,
) -> list[Path]:
    """
    Localiza os N arquivos B3 mais recentes.
    """

    files = list(
        base_directory.rglob(
            "b3_download_*.zip"
        )
    )

    if not files:
        raise FileNotFoundError(
            "Nenhum arquivo "
            "b3_download_*.zip encontrado em "
            f"{base_directory}."
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
    Retorna tickers únicos encontrados em um pregão.
    """

    if "ticker" not in dataframe.columns:
        raise ValueError(
            "Coluna 'ticker' não encontrada "
            "no DataFrame da B3."
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


def build_b3_market_evidence(
    b3_files: list[Path],
) -> tuple[
    dict[str, int],
    dict[str, list[str]],
]:
    """
    Conta em quantos pregões cada ticker apareceu.

    Retorna:

    ticker_days_count:
        ticker -> quantidade de pregões

    ticker_dates:
        ticker -> datas em que apareceu
    """

    b3_parser = load_b3_parser()

    ticker_days_count: dict[
        str,
        int
    ] = defaultdict(int)

    ticker_dates: dict[
        str,
        list[str]
    ] = defaultdict(list)

    print(
        "\n======================================"
    )
    print(
        "Processando janela B3"
    )
    print(
        "======================================"
    )

    for index, b3_file in enumerate(
        b3_files,
        start=1,
    ):
        file_date = (
            extract_date_from_b3_filename(
                b3_file
            )
        )

        print(
            f"[{index}/{len(b3_files)}] "
            f"{file_date}"
        )

        (
            dataframe,
            metadata,
        ) = b3_parser.parse_b3_download(
            b3_file
        )

        tickers = normalize_b3_tickers(
            dataframe
        )

        print(
            f"  Registros: "
            f"{len(dataframe):,}"
        )

        print(
            f"  Tickers únicos: "
            f"{len(tickers):,}"
        )

        print(
            f"  XML: "
            f"{metadata['xml_file']}"
        )

        for ticker in tickers:
            ticker_days_count[
                ticker
            ] += 1

            ticker_dates[
                ticker
            ].append(
                file_date
            )

    return (
        dict(
            ticker_days_count
        ),
        dict(
            ticker_dates
        ),
    )


def build_master_market_evidence(
    master: pd.DataFrame,
    ticker_days_count: dict[str, int],
    window_size: int,
) -> pd.DataFrame:
    """
    Acrescenta evidência B3 aos tickers do Master.
    """

    evidence = (
        master[
            [
                "cnpj",
                "ticker",
                "fund_name_commercial",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    evidence[
        "market_evidence_days"
    ] = evidence[
        "ticker"
    ].map(
        ticker_days_count
    ).fillna(
        0
    ).astype(
        int
    )

    evidence[
        "market_evidence_ratio"
    ] = (
        evidence[
            "market_evidence_days"
        ]
        / window_size
    )

    return evidence.sort_values(
        by=[
            "cnpj",
            "ticker",
        ]
    ).reset_index(
        drop=True
    )


def get_ambiguous_cnpjs(
    evidence: pd.DataFrame,
) -> set[str]:
    """
    Identifica CNPJs associados a mais de um ticker.
    """

    counts = (
        evidence.groupby(
            "cnpj"
        )["ticker"]
        .nunique()
    )

    return set(
        counts[
            counts > 1
        ].index
    )


def print_general_coverage(
    evidence: pd.DataFrame,
    window_size: int,
) -> None:
    """
    Métricas gerais da presença dos tickers
    do Master na janela B3.
    """

    total = evidence[
        "ticker"
    ].nunique()

    found = evidence[
        evidence[
            "market_evidence_days"
        ] > 0
    ][
        "ticker"
    ].nunique()

    not_found = (
        total
        - found
    )

    full_window = evidence[
        evidence[
            "market_evidence_days"
        ] == window_size
    ][
        "ticker"
    ].nunique()

    coverage = (
        found
        / total
        * 100
        if total
        else 0
    )

    print(
        "\n======================================"
    )
    print(
        "Cobertura geral na janela B3"
    )
    print(
        "======================================"
    )

    print(
        f"Tickers candidatos no Master: "
        f"{total:,}"
    )

    print(
        f"Encontrados em pelo menos 1 pregão: "
        f"{found:,}"
    )

    print(
        f"Não encontrados em nenhum pregão: "
        f"{not_found:,}"
    )

    print(
        f"Presentes em todos os "
        f"{window_size} pregões: "
        f"{full_window:,}"
    )

    print(
        f"Cobertura da janela: "
        f"{coverage:.2f}%"
    )


def classify_ambiguous_cnpj(
    group: pd.DataFrame,
) -> tuple[
    str,
    str | None,
]:
    """
    Classifica um CNPJ ambíguo.

    Regras:

    RESOLVED:
        exatamente um ticker possui evidência B3.

    NO_MARKET_EVIDENCE:
        nenhum ticker apareceu na janela.

    MULTIPLE_ACTIVE_CANDIDATES:
        dois ou mais tickers possuem evidência.

    Retorna:
        status
        ticker candidato atual
    """

    active = group[
        group[
            "market_evidence_days"
        ] > 0
    ].copy()

    if len(
        active
    ) == 0:
        return (
            "NO_MARKET_EVIDENCE",
            None,
        )

    if len(
        active
    ) == 1:
        return (
            "RESOLVED",
            str(
                active.iloc[
                    0
                ][
                    "ticker"
                ]
            ),
        )

    return (
        "MULTIPLE_ACTIVE_CANDIDATES",
        None,
    )


def build_ambiguity_summary(
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cria resumo dos CNPJs com múltiplos tickers.
    """

    ambiguous_cnpjs = (
        get_ambiguous_cnpjs(
            evidence
        )
    )

    ambiguous = evidence[
        evidence[
            "cnpj"
        ].isin(
            ambiguous_cnpjs
        )
    ].copy()

    records: list[
        dict[str, object]
    ] = []

    for cnpj, group in ambiguous.groupby(
        "cnpj"
    ):
        (
            resolution_status,
            current_ticker_candidate,
        ) = classify_ambiguous_cnpj(
            group
        )

        records.append(
            {
                "cnpj": cnpj,
                "candidate_tickers": (
                    group[
                        "ticker"
                    ].nunique()
                ),
                "tickers_with_market_evidence": (
                    (
                        group[
                            "market_evidence_days"
                        ]
                        > 0
                    ).sum()
                ),
                "resolution_status": (
                    resolution_status
                ),
                "current_ticker_candidate": (
                    current_ticker_candidate
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def print_ambiguity_summary(
    summary: pd.DataFrame,
) -> None:
    """
    Exibe métricas de resolução.
    """

    if summary.empty:
        print(
            "\nNenhum CNPJ ambíguo encontrado."
        )
        return

    resolved = summary[
        summary[
            "resolution_status"
        ] == "RESOLVED"
    ]

    no_evidence = summary[
        summary[
            "resolution_status"
        ] == "NO_MARKET_EVIDENCE"
    ]

    multiple = summary[
        summary[
            "resolution_status"
        ]
        == "MULTIPLE_ACTIVE_CANDIDATES"
    ]

    print(
        "\n======================================"
    )
    print(
        "Resolução de histórico de ticker"
    )
    print(
        "======================================"
    )

    print(
        f"CNPJs ambíguos: "
        f"{len(summary):,}"
    )

    print(
        f"Resolvidos pela janela B3: "
        f"{len(resolved):,}"
    )

    print(
        f"Sem evidência de mercado: "
        f"{len(no_evidence):,}"
    )

    print(
        f"Múltiplos candidatos ativos: "
        f"{len(multiple):,}"
    )


def print_ambiguous_details(
    evidence: pd.DataFrame,
    summary: pd.DataFrame,
    window_size: int,
) -> None:
    """
    Exibe detalhes dos casos ambíguos.
    """

    ambiguous_cnpjs = set(
        summary[
            "cnpj"
        ]
    )

    ambiguous = evidence[
        evidence[
            "cnpj"
        ].isin(
            ambiguous_cnpjs
        )
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Detalhamento dos CNPJs ambíguos"
    )
    print(
        "======================================"
    )

    for cnpj, group in ambiguous.groupby(
        "cnpj"
    ):
        summary_row = summary[
            summary[
                "cnpj"
            ] == cnpj
        ].iloc[
            0
        ]

        print(
            f"\nCNPJ: {cnpj}"
        )

        for _, row in group.iterrows():
            days = row[
                "market_evidence_days"
            ]

            print(
                f"  {row['ticker']:<10} "
                f"{days}/{window_size} pregões "
                f"- "
                f"{row['fund_name_commercial']}"
            )

        print(
            f"  Status: "
            f"{summary_row['resolution_status']}"
        )

        candidate = summary_row[
            "current_ticker_candidate"
        ]

        if pd.notna(
            candidate
        ):
            print(
                f"  Candidato atual: "
                f"{candidate}"
            )


def main() -> None:
    print(
        "Diagnóstico temporal "
        "FII Master x B3..."
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

    funds_mapping_path = (
        find_latest_file(
            base_directory=(
                DEFAULT_FUNDS_EXPLORER_BRONZE_DIR
            ),
            filename=(
                "ticker_cnpj_mapping.csv"
            ),
        )
    )

    funds = load_funds_explorer_mapping(
        funds_mapping_path
    )

    # -----------------------------------------
    # Master candidato
    # -----------------------------------------

    (
        master,
        _,
        _,
    ) = build_fii_master(
        cvm_dataframe=cvm,
        funds_explorer_dataframe=funds,
    )

    # -----------------------------------------
    # Janela B3
    # -----------------------------------------

    b3_files = find_latest_b3_downloads(
        base_directory=B3_RAW_DIR,
        limit=5,
    )

    print(
        "\nArquivos B3 selecionados:"
    )

    for b3_file in reversed(
        b3_files
    ):
        print(
            f"  "
            f"{extract_date_from_b3_filename(b3_file)}"
        )

    (
        ticker_days_count,
        ticker_dates,
    ) = build_b3_market_evidence(
        b3_files
    )

    window_size = len(
        b3_files
    )

    # -----------------------------------------
    # Evidência de mercado
    # -----------------------------------------

    evidence = (
        build_master_market_evidence(
            master=master,
            ticker_days_count=(
                ticker_days_count
            ),
            window_size=window_size,
        )
    )

    print_general_coverage(
        evidence=evidence,
        window_size=window_size,
    )

    # -----------------------------------------
    # Histórico / ambiguidades
    # -----------------------------------------

    summary = (
        build_ambiguity_summary(
            evidence
        )
    )

    print_ambiguity_summary(
        summary
    )

    print_ambiguous_details(
        evidence=evidence,
        summary=summary,
        window_size=window_size,
    )

    print(
        "\nDiagnóstico temporal concluído."
    )


if __name__ == "__main__":
    main()