from __future__ import annotations

import pandas as pd
import pytest

from src.observability.gold_quality import (
    GoldQualityError,
    assert_fii_master_quality,
    calculate_fii_master_metrics,
    evaluate_fii_master_quality,
)


def build_valid_gold() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cnpj_classe": [
                "11111111000111",
                "22222222000122",
                "33333333000133",
            ],
            "resolution_status": [
                "AUTO_RESOLVED",
                "AUTO_RESOLVED",
                "UNRESOLVED",
            ],
            "resolution_method": [
                "B3_UNDERLYING_REFERENCE",
                "B3_PRIMARY_SIGNATURE",
                pd.NA,
            ],
            "primary_instrument_id": [
                "1001",
                "1002",
                pd.NA,
            ],
            "ticker": [
                "AAA11",
                "BBB11",
                pd.NA,
            ],
            "isin": [
                "BRAAACTF001",
                "BRBBBCTF002",
                pd.NA,
            ],
        }
    )


def test_calculate_metrics() -> None:
    dataframe = build_valid_gold()

    metrics = calculate_fii_master_metrics(
        dataframe
    )

    assert (
        metrics["gold_fii_master_rows"]
        == 3
    )

    assert (
        metrics["gold_fii_master_resolved"]
        == 2
    )

    assert (
        metrics["gold_fii_master_unresolved"]
        == 1
    )

    assert (
        metrics[
            "gold_fii_master_structural_resolution"
        ]
        == 1
    )

    assert (
        metrics[
            "gold_fii_master_signature_resolution"
        ]
        == 1
    )

    assert (
        metrics[
            "gold_fii_master_duplicate_cnpj_rows"
        ]
        == 0
    )


def test_valid_gold_passes_quality() -> None:
    dataframe = build_valid_gold()

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.60,
    )

    assert result["status"] == "PASS"

    assert all(
        check["status"] == "PASS"
        for check in result["checks"]
    )


def test_low_resolution_rate_warns() -> None:
    dataframe = build_valid_gold()

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.90,
    )

    assert result["status"] == "WARN"

    resolution_check = next(
        check
        for check in result["checks"]
        if check["name"]
        == "resolution_rate"
    )

    assert (
        resolution_check["status"]
        == "WARN"
    )


def test_duplicate_cnpj_fails() -> None:
    dataframe = build_valid_gold()

    dataframe.loc[
        1,
        "cnpj_classe",
    ] = dataframe.loc[
        0,
        "cnpj_classe",
    ]

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.60,
    )

    assert result["status"] == "FAIL"

    duplicate_check = next(
        check
        for check in result["checks"]
        if check["name"]
        == "duplicate_cnpj"
    )

    assert (
        duplicate_check["status"]
        == "FAIL"
    )


def test_duplicate_primary_instrument_fails() -> None:
    dataframe = build_valid_gold()

    dataframe.loc[
        1,
        "primary_instrument_id",
    ] = dataframe.loc[
        0,
        "primary_instrument_id",
    ]

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.60,
    )

    assert result["status"] == "FAIL"

    duplicate_check = next(
        check
        for check in result["checks"]
        if check["name"]
        == "duplicate_primary_instrument_id"
    )

    assert (
        duplicate_check["status"]
        == "FAIL"
    )


def test_resolved_without_ticker_fails() -> None:
    dataframe = build_valid_gold()

    dataframe.loc[
        0,
        "ticker",
    ] = pd.NA

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.60,
    )

    assert result["status"] == "FAIL"

    ticker_check = next(
        check
        for check in result["checks"]
        if check["name"]
        == "resolved_without_ticker"
    )

    assert (
        ticker_check["status"]
        == "FAIL"
    )


def test_unresolved_with_primary_id_fails() -> None:
    dataframe = build_valid_gold()

    dataframe.loc[
        2,
        "primary_instrument_id",
    ] = "9999"

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.60,
    )

    assert result["status"] == "FAIL"

    primary_check = next(
        check
        for check in result["checks"]
        if check["name"]
        == "unresolved_with_primary_id"
    )

    assert (
        primary_check["status"]
        == "FAIL"
    )


def test_assert_quality_raises_on_failure() -> None:
    dataframe = build_valid_gold()

    dataframe.loc[
        0,
        "ticker",
    ] = pd.NA

    result = evaluate_fii_master_quality(
        dataframe,
        min_resolution_rate=0.60,
    )

    with pytest.raises(
        GoldQualityError
    ):
        assert_fii_master_quality(
            result
        )


def test_empty_dataset_fails() -> None:
    dataframe = build_valid_gold().iloc[
        0:0
    ]

    result = evaluate_fii_master_quality(
        dataframe
    )

    assert result["status"] == "FAIL"

    empty_check = next(
        check
        for check in result["checks"]
        if check["name"]
        == "dataset_not_empty"
    )

    assert (
        empty_check["status"]
        == "FAIL"
    )