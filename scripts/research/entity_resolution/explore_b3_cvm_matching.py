from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


B3_PATH = Path(
    "data/silver/b3-instruments/"
    "year=2026/month=09/day=11/"
    "b3_instruments.parquet"
)

CVM_PATH = Path(
    "data/silver/cvm/"
    "year=2026/month=09/day=14/"
    "cvm_fund_classes.parquet"
)

OUTPUT_ROOT = Path(
    "data/analysis/b3-cvm-matching"
)


GENERIC_TOKENS = {
    "FII",
    "FUNDO",
    "FDO",
    "INVESTIMENTO",
    "INV",
    "IMOBILIARIO",
    "IMOB",
    "DE",
    "DA",
    "DO",
    "DAS",
    "DOS",
    "RESPONSABILIDADE",
    "RESP",
    "LIMITADA",
    "LIM",
    "RESPLIM",
}


def normalize_text(
    value: object,
) -> str:
    if pd.isna(value):
        return ""

    text = str(value)

    text = (
        unicodedata
        .normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .upper()
    )

    text = re.sub(
        r"[^A-Z0-9]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def build_core_name(
    value: object,
) -> str:
    text = normalize_text(
        value
    )

    tokens = [
        token
        for token in text.split()
        if token not in GENERIC_TOKENS
    ]

    return " ".join(
        tokens
    )


def build_b3_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    summary = (
        dataframe
        .groupby(
            "core_name",
            as_index=False,
        )
        .agg(
            b3_rows=(
                "instrument_id",
                "size",
            ),
            b3_instrument_ids=(
                "instrument_id",
                "nunique",
            ),
            b3_tickers=(
                "ticker",
                "nunique",
            ),
            b3_isins=(
                "isin",
                "nunique",
            ),
            b3_assets=(
                "asset",
                "nunique",
            ),
            b3_corporate_names=(
                "corporate_name",
                "nunique",
            ),
        )
    )

    return summary


def build_cvm_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    summary = (
        dataframe
        .groupby(
            "core_name",
            as_index=False,
        )
        .agg(
            cvm_rows=(
                "CNPJ_Classe",
                "size",
            ),
            cvm_cnpjs=(
                "CNPJ_Classe",
                "nunique",
            ),
            cvm_codes=(
                "Codigo_CVM",
                "nunique",
            ),
        )
    )

    return summary


def classify_matches(
    cvm_summary: pd.DataFrame,
    b3_summary: pd.DataFrame,
) -> pd.DataFrame:
    result = cvm_summary.merge(
        b3_summary,
        on="core_name",
        how="left",
    )

    result["match_status"] = (
        "NO_B3_MATCH"
    )

    has_b3_match = (
        result["b3_rows"]
        .notna()
    )

    unique_cvm = (
        result["cvm_cnpjs"]
        .eq(1)
    )

    result.loc[
        has_b3_match
        & unique_cvm,
        "match_status",
    ] = "UNIQUE_MATCH"

    result.loc[
        has_b3_match
        & ~unique_cvm,
        "match_status",
    ] = "AMBIGUOUS_MATCH"

    return result


def build_unique_bridge_candidates(
    b3: pd.DataFrame,
    cvm_fii: pd.DataFrame,
    classification: pd.DataFrame,
) -> pd.DataFrame:
    unique_core_names = set(
        classification.loc[
            classification[
                "match_status"
            ].eq(
                "UNIQUE_MATCH"
            ),
            "core_name",
        ]
    )

    cvm_unique = (
        cvm_fii[
            cvm_fii[
                "core_name"
            ].isin(
                unique_core_names
            )
        ][
            [
                "core_name",
                "CNPJ_Classe",
                "Codigo_CVM",
                "Denominacao_Social",
                "Situacao",
            ]
        ]
        .drop_duplicates(
            subset=[
                "core_name",
                "CNPJ_Classe",
            ]
        )
    )

    bridge_candidates = (
        b3[
            b3[
                "core_name"
            ].isin(
                unique_core_names
            )
        ]
        .merge(
            cvm_unique,
            on="core_name",
            how="inner",
        )
    )

    bridge_candidates = (
        bridge_candidates[
            [
                "instrument_id",
                "instrument_id_type",
                "listing_market",
                "asset",
                "ticker",
                "isin",
                "corporate_name",
                "CNPJ_Classe",
                "Codigo_CVM",
                "Denominacao_Social",
                "Situacao",
                "core_name",
            ]
        ]
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    bridge_candidates[
        "match_method"
    ] = "CORE_NAME_EXACT"

    bridge_candidates[
        "match_status"
    ] = "CANDIDATE"

    return bridge_candidates


def main() -> None:
    print(
        "======================================"
    )
    print(
        "B3 INSTRUMENTS x CVM FII"
    )
    print(
        "MATCH CLASSIFICATION"
    )
    print(
        "======================================"
    )
    print()

    b3 = pd.read_parquet(
        B3_PATH
    )

    cvm = pd.read_parquet(
        CVM_PATH
    )

    cvm_fii = cvm[
        cvm["Tipo_Classe"].eq(
            "Classes de Cotas de Fundos FII"
        )
    ].copy()

    b3 = b3[
        b3[
            "corporate_name"
        ].notna()
    ].copy()

    b3["core_name"] = (
        b3[
            "corporate_name"
        ]
        .map(
            build_core_name
        )
    )

    cvm_fii["core_name"] = (
        cvm_fii[
            "Denominacao_Social"
        ]
        .map(
            build_core_name
        )
    )

    b3 = b3[
        b3[
            "core_name"
        ].ne("")
    ].copy()

    cvm_fii = cvm_fii[
        cvm_fii[
            "core_name"
        ].ne("")
    ].copy()

    b3_summary = (
        build_b3_summary(
            b3
        )
    )

    cvm_summary = (
        build_cvm_summary(
            cvm_fii
        )
    )

    classification = (
        classify_matches(
            cvm_summary=cvm_summary,
            b3_summary=b3_summary,
        )
    )

    unique_matches = (
        classification[
            classification[
                "match_status"
            ].eq(
                "UNIQUE_MATCH"
            )
        ]
        .copy()
    )

    ambiguous_matches = (
        classification[
            classification[
                "match_status"
            ].eq(
                "AMBIGUOUS_MATCH"
            )
        ]
        .copy()
    )

    no_b3_matches = (
        classification[
            classification[
                "match_status"
            ].eq(
                "NO_B3_MATCH"
            )
        ]
        .copy()
    )

    bridge_candidates = (
        build_unique_bridge_candidates(
            b3=b3,
            cvm_fii=cvm_fii,
            classification=classification,
        )
    )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    unique_matches.to_csv(
        OUTPUT_ROOT
        / "unique_matches.csv",
        index=False,
    )

    ambiguous_matches.to_csv(
        OUTPUT_ROOT
        / "ambiguous_matches.csv",
        index=False,
    )

    no_b3_matches.to_csv(
        OUTPUT_ROOT
        / "no_b3_matches.csv",
        index=False,
    )

    bridge_candidates.to_csv(
        OUTPUT_ROOT
        / "bridge_candidates.csv",
        index=False,
    )

    print(
        "FIIs CVM: "
        f"{len(cvm_fii):,}"
    )

    print(
        "Core names CVM: "
        f"{len(cvm_summary):,}"
    )

    print()

    print(
        "UNIQUE_MATCH: "
        f"{len(unique_matches):,}"
    )

    print(
        "AMBIGUOUS_MATCH: "
        f"{len(ambiguous_matches):,}"
    )

    print(
        "NO_B3_MATCH: "
        f"{len(no_b3_matches):,}"
    )

    print()

    total_core_names = len(
        cvm_summary
    )

    unique_rate = (
        len(unique_matches)
        / total_core_names
        * 100
    )

    print(
        "Taxa de core_names com "
        "match único: "
        f"{unique_rate:.2f}%"
    )

    print()

    print(
        "Bridge candidates gerados: "
        f"{len(bridge_candidates):,}"
    )

    print()

    print(
        "=== AMBIGUIDADES CVM ==="
    )

    if ambiguous_matches.empty:
        print(
            "Nenhuma ambiguidade encontrada."
        )
    else:
        ambiguous_core_names = (
            ambiguous_matches[
                "core_name"
            ]
            .tolist()
        )

        ambiguous_details = (
            cvm_fii[
                cvm_fii[
                    "core_name"
                ].isin(
                    ambiguous_core_names
                )
            ][
                [
                    "core_name",
                    "CNPJ_Classe",
                    "Codigo_CVM",
                    "Denominacao_Social",
                    "Situacao",
                ]
            ]
            .sort_values(
                [
                    "core_name",
                    "CNPJ_Classe",
                ]
            )
        )

        print(
            ambiguous_details
            .to_string(
                index=False
            )
        )

    print()
    print(
        "=== AMOSTRA BRIDGE ==="
    )

    print(
        bridge_candidates[
            [
                "instrument_id",
                "ticker",
                "isin",
                "CNPJ_Classe",
                "Codigo_CVM",
                "core_name",
            ]
        ]
        .head(30)
        .to_string(
            index=False
        )
    )

    print()
    print(
        "Arquivos gerados em:"
    )

    print(
        f"  {OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()