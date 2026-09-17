from __future__ import annotations

from pathlib import Path

import pandas as pd


BRIDGE_PATH = Path(
    "data/analysis/b3-cvm-matching/"
    "bridge_candidates.csv"
)

INSTRUMENTS_PATH = Path(
    "data/silver/b3-instruments/"
    "year=2026/month=09/day=11/"
    "b3_instruments.parquet"
)

TRADES_PATH = Path(
    "data/silver/b3/"
    "year=2026/month=09/day=11/"
    "b3_trades.parquet"
)


def main() -> None:
    bridge = pd.read_csv(
        BRIDGE_PATH,
        dtype=str,
    )

    instruments = pd.read_parquet(
        INSTRUMENTS_PATH
    )

    trades = pd.read_parquet(
        TRADES_PATH
    )

    global_underlying_ids = set(
        instruments[
            "underlying_instrument_id"
        ]
        .dropna()
        .astype(str)
    )

    traded_ids = set(
        trades[
            "instrument_id"
        ]
        .dropna()
        .astype(str)
    )

    columns = [
        "instrument_id",
        "underlying_instrument_id",
        "ticker",
        "isin",
        "security_category",
        "b3_market",
        "b3_segment",
        "instrument_type",
        "asset",
        "corporate_name",
        "trading_start_date",
        "trading_end_date",
    ]

    analysis = (
        bridge[
            [
                "instrument_id",
                "CNPJ_Classe",
                "Codigo_CVM",
                "core_name",
            ]
        ]
        .merge(
            instruments[columns],
            on="instrument_id",
            how="left",
        )
    )

    analysis["is_underlying_target"] = (
        analysis[
            "instrument_id"
        ]
        .astype(str)
        .isin(
            global_underlying_ids
        )
    )

    analysis["is_traded"] = (
        analysis[
            "instrument_id"
        ]
        .astype(str)
        .isin(
            traded_ids
        )
    )

    counts = (
        analysis
        .groupby(
            "CNPJ_Classe"
        )
        .agg(
            underlying_targets=(
                "is_underlying_target",
                "sum",
            ),
            traded_candidates=(
                "is_traded",
                "sum",
            ),
        )
    )

    structurally_resolved_cnpjs = set(
        counts[
            counts[
                "underlying_targets"
            ].eq(1)
        ]
        .index
    )

    unresolved_cnpjs = set(
        counts[
            counts[
                "underlying_targets"
            ].eq(0)
        ]
        .index
    )

    analysis["resolution_group"] = (
        "UNRESOLVED"
    )

    analysis.loc[
        analysis[
            "CNPJ_Classe"
        ].isin(
            structurally_resolved_cnpjs
        ),
        "resolution_group",
    ] = "STRUCTURAL_RESOLVED"

    primary = analysis[
        analysis[
            "is_underlying_target"
        ]
    ].copy()

    unresolved = analysis[
        analysis[
            "CNPJ_Classe"
        ].isin(
            unresolved_cnpjs
        )
    ].copy()

    print(
        "======================================"
    )
    print(
        "PRIMARY INSTRUMENT PATTERN ANALYSIS"
    )
    print(
        "======================================"
    )
    print()

    print(
        "CNPJs estruturalmente resolvidos: "
        f"{len(structurally_resolved_cnpjs):,}"
    )

    print(
        "CNPJs sem underlying target: "
        f"{len(unresolved_cnpjs):,}"
    )

    print()

    print(
        "=== PRIMARY: SECURITY CATEGORY ==="
    )

    print(
        primary[
            "security_category"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()

    print(
        "=== PRIMARY: B3 MARKET ==="
    )

    print(
        primary[
            "b3_market"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()

    print(
        "=== PRIMARY: B3 SEGMENT ==="
    )

    print(
        primary[
            "b3_segment"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()

    print(
        "=== PRIMARY: INSTRUMENT TYPE ==="
    )

    print(
        primary[
            "instrument_type"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()

    print(
        "=== PRIMARY: TICKER SUFFIX ==="
    )

    ticker_suffix = (
        primary[
            "ticker"
        ]
        .fillna("")
        .str.extract(
            r"(\d+)$"
        )[0]
    )

    print(
        ticker_suffix
        .value_counts(
            dropna=False
        )
        .head(30)
        .to_string()
    )

    print()

    print(
        "=== UNRESOLVED: SECURITY CATEGORY ==="
    )

    print(
        unresolved[
            "security_category"
        ]
        .value_counts(
            dropna=False
        )
        .head(30)
        .to_string()
    )

    print()

    print(
        "=== UNRESOLVED: B3 MARKET ==="
    )

    print(
        unresolved[
            "b3_market"
        ]
        .value_counts(
            dropna=False
        )
        .head(30)
        .to_string()
    )

    print()

    print(
        "=== UNRESOLVED: INSTRUMENT TYPE ==="
    )

    print(
        unresolved[
            "instrument_type"
        ]
        .value_counts(
            dropna=False
        )
        .head(30)
        .to_string()
    )

    print()

    print(
        "=== UNRESOLVED COM TRADE ÚNICO ==="
    )

    trade_only_cnpjs = set(
        counts[
            counts[
                "underlying_targets"
            ].eq(0)
            & counts[
                "traded_candidates"
            ].eq(1)
        ]
        .index
    )

    trade_only = analysis[
        analysis[
            "CNPJ_Classe"
        ].isin(
            trade_only_cnpjs
        )
        & analysis[
            "is_traded"
        ]
    ]

    print(
        trade_only[
            [
                "CNPJ_Classe",
                "Codigo_CVM",
                "instrument_id",
                "ticker",
                "isin",
                "security_category",
                "b3_market",
                "b3_segment",
                "instrument_type",
                "core_name",
            ]
        ]
        .sort_values(
            [
                "security_category",
                "ticker",
            ]
        )
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()