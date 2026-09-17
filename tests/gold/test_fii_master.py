from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.gold.fii_master import (
    build_fii_master,
)


CVM_PATH = Path(
    "data/silver/cvm/"
    "year=2026/month=09/day=14/"
    "cvm_fund_classes.parquet"
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


def load_gold() -> pd.DataFrame:
    cvm = pd.read_parquet(
        CVM_PATH
    )

    instruments = pd.read_parquet(
        INSTRUMENTS_PATH
    )

    trades = pd.read_parquet(
        TRADES_PATH
    )

    return build_fii_master(
        cvm=cvm,
        instruments=instruments,
        trades=trades,
    )


def test_fii_master_expected_row_count() -> None:
    gold = load_gold()

    assert len(gold) == 389


def test_cnpj_is_unique() -> None:
    gold = load_gold()

    assert (
        gold["cnpj_classe"]
        .duplicated()
        .sum()
        == 0
    )


def test_resolution_counts() -> None:
    gold = load_gold()

    counts = (
        gold[
            "resolution_status"
        ]
        .value_counts()
        .to_dict()
    )

    assert (
        counts[
            "AUTO_RESOLVED"
        ]
        == 363
    )

    assert (
        counts[
            "UNRESOLVED"
        ]
        == 26
    )


def test_resolved_rows_have_identity() -> None:
    gold = load_gold()

    resolved = gold[
        gold[
            "resolution_status"
        ].eq(
            "AUTO_RESOLVED"
        )
    ]

    assert (
        resolved[
            "primary_instrument_id"
        ]
        .isna()
        .sum()
        == 0
    )

    assert (
        resolved[
            "ticker"
        ]
        .isna()
        .sum()
        == 0
    )

    assert (
        resolved[
            "isin"
        ]
        .isna()
        .sum()
        == 0
    )


def test_primary_instrument_is_unique() -> None:
    gold = load_gold()

    resolved = gold[
        gold[
            "resolution_status"
        ].eq(
            "AUTO_RESOLVED"
        )
    ]

    assert (
        resolved[
            "primary_instrument_id"
        ]
        .duplicated()
        .sum()
        == 0
    )


def test_unresolved_rows_do_not_have_primary_identity() -> None:
    gold = load_gold()

    unresolved = gold[
        gold[
            "resolution_status"
        ].eq(
            "UNRESOLVED"
        )
    ]

    assert (
        unresolved[
            "primary_instrument_id"
        ]
        .notna()
        .sum()
        == 0
    )

    assert (
        unresolved[
            "ticker"
        ]
        .notna()
        .sum()
        == 0
    )

    assert (
        unresolved[
            "isin"
        ]
        .notna()
        .sum()
        == 0
    )


def assert_known_fii(
    gold: pd.DataFrame,
    cnpj: str,
    ticker: str,
    instrument_id: str,
) -> None:
    row = gold[
        gold[
            "cnpj_classe"
        ].eq(
            cnpj
        )
    ]

    assert len(row) == 1

    record = row.iloc[0]

    assert (
        record["ticker"]
        == ticker
    )

    assert (
        record[
            "primary_instrument_id"
        ]
        == instrument_id
    )

    assert (
        record[
            "resolution_method"
        ]
        == "B3_UNDERLYING_REFERENCE"
    )

    assert (
        record[
            "resolution_status"
        ]
        == "AUTO_RESOLVED"
    )

    assert (
        record[
            "resolution_evidence"
        ]
        == "STRUCTURAL_AND_TRADED"
    )


def test_known_fii_resolutions() -> None:
    gold = load_gold()

    assert_known_fii(
        gold=gold,
        cnpj="36771692000119",
        ticker="VGHF11",
        instrument_id="200003070794",
    )

    assert_known_fii(
        gold=gold,
        cnpj="28737771000185",
        ticker="ALZR11",
        instrument_id="200003037047",
    )

    assert_known_fii(
        gold=gold,
        cnpj="42754362000118",
        ticker="KNUQ11",
        instrument_id="200003077484",
    )


def test_resolution_method_counts() -> None:
    gold = load_gold()

    counts = (
        gold[
            "resolution_method"
        ]
        .value_counts(
            dropna=False
        )
    )

    assert (
        counts[
            "B3_UNDERLYING_REFERENCE"
        ]
        == 201
    )

    assert (
        counts[
            "B3_PRIMARY_SIGNATURE"
        ]
        == 162
    )


def test_resolution_evidence_counts() -> None:
    gold = load_gold()

    counts = (
        gold[
            "resolution_evidence"
        ]
        .value_counts(
            dropna=False
        )
    )

    assert (
        counts[
            "STRUCTURAL_AND_TRADED"
        ]
        == 180
    )

    assert (
        counts[
            "STRUCTURAL_ONLY"
        ]
        == 21
    )

    assert (
        counts[
            "SIGNATURE_AND_TRADED"
        ]
        == 15
    )

    assert (
        counts[
            "SIGNATURE_ONLY"
        ]
        == 147
    )