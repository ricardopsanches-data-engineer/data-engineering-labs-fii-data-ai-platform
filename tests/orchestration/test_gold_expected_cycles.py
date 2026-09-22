from __future__ import annotations

from datetime import date

import pytest

from src.orchestration import (
    gold_expected_cycles,
)


def test_normalize_excluded_dates_none() -> None:
    result = (
        gold_expected_cycles
        .normalize_excluded_dates(
            None
        )
    )

    assert result == set()


def test_normalize_excluded_dates_values() -> None:
    excluded_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    ]

    result = (
        gold_expected_cycles
        .normalize_excluded_dates(
            excluded_dates
        )
    )

    assert result == {
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    }


def test_generate_expected_run_dates_weekdays_only() -> None:
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                27,
            ),
        )
    )

    assert result == [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
        date(
            2026,
            9,
            23,
        ),
        date(
            2026,
            9,
            24,
        ),
        date(
            2026,
            9,
            25,
        ),
    ]


def test_generate_expected_run_dates_excludes_dates() -> None:
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                25,
            ),
            excluded_dates={
                date(
                    2026,
                    9,
                    23,
                )
            },
        )
    )

    assert result == [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
        date(
            2026,
            9,
            24,
        ),
        date(
            2026,
            9,
            25,
        ),
    ]


def test_generate_expected_run_dates_custom_weekdays() -> None:
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                27,
            ),
            expected_weekdays={
                0,
                2,
                4,
            },
        )
    )

    assert result == [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            23,
        ),
        date(
            2026,
            9,
            25,
        ),
    ]


def test_generate_expected_run_dates_invalid_range() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "start_date must be "
            "<= end_date"
        ),
    ):
        (
            gold_expected_cycles
            .generate_expected_run_dates(
                start_date=date(
                    2026,
                    9,
                    25,
                ),
                end_date=date(
                    2026,
                    9,
                    21,
                ),
            )
        )


def test_generate_expected_run_dates_invalid_weekday() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expected_weekdays must "
            "contain values from 0 to 6"
        ),
    ):
        (
            gold_expected_cycles
            .generate_expected_run_dates(
                start_date=date(
                    2026,
                    9,
                    21,
                ),
                end_date=date(
                    2026,
                    9,
                    25,
                ),
                expected_weekdays={
                    0,
                    1,
                    7,
                },
            )
        )


def test_detect_missing_run_dates() -> None:
    expected_run_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
        date(
            2026,
            9,
            23,
        ),
    ]

    observed_run_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    ]

    result = (
        gold_expected_cycles
        .detect_missing_run_dates(
            expected_run_dates=(
                expected_run_dates
            ),
            observed_run_dates=(
                observed_run_dates
            ),
        )
    )

    assert result == [
        date(
            2026,
            9,
            23,
        )
    ]


def test_detect_missing_run_dates_complete() -> None:
    expected_run_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    ]

    observed_run_dates = [
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            9,
            22,
        ),
    ]

    result = (
        gold_expected_cycles
        .detect_missing_run_dates(
            expected_run_dates=(
                expected_run_dates
            ),
            observed_run_dates=(
                observed_run_dates
            ),
        )
    )

    assert result == []


def test_assess_expected_cycles_detects_gap() -> None:
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                23,
            ),
            observed_run_dates=[
                date(
                    2026,
                    9,
                    21,
                ),
                date(
                    2026,
                    9,
                    22,
                ),
            ],
        )
    )

    assert result[
        "status"
    ] == "GAPS_DETECTED"

    assert result[
        "expected_run_dates"
    ] == [
        "2026-09-21",
        "2026-09-22",
        "2026-09-23",
    ]

    assert result[
        "observed_run_dates"
    ] == [
        "2026-09-21",
        "2026-09-22",
    ]

    assert result[
        "missing_run_dates"
    ] == [
        "2026-09-23"
    ]

    assert result[
        "expected_cycles"
    ] == 3

    assert result[
        "observed_cycles"
    ] == 2

    assert result[
        "missing_cycles"
    ] == 1


def test_assess_expected_cycles_complete() -> None:
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                22,
            ),
            observed_run_dates=[
                date(
                    2026,
                    9,
                    21,
                ),
                date(
                    2026,
                    9,
                    22,
                ),
            ],
        )
    )

    assert result[
        "status"
    ] == "COMPLETE"

    assert result[
        "missing_run_dates"
    ] == []

    assert result[
        "expected_cycles"
    ] == 2

    assert result[
        "observed_cycles"
    ] == 2

    assert result[
        "missing_cycles"
    ] == 0


def test_assess_expected_cycles_ignores_weekend() -> None:
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                9,
                25,
            ),
            end_date=date(
                2026,
                9,
                27,
            ),
            observed_run_dates=[
                date(
                    2026,
                    9,
                    25,
                )
            ],
        )
    )

    assert result[
        "status"
    ] == "COMPLETE"

    assert result[
        "expected_run_dates"
    ] == [
        "2026-09-25"
    ]

    assert result[
        "missing_run_dates"
    ] == []


def test_assess_expected_cycles_ignores_excluded_date() -> None:
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                23,
            ),
            observed_run_dates=[
                date(
                    2026,
                    9,
                    21,
                ),
                date(
                    2026,
                    9,
                    22,
                ),
            ],
            excluded_dates={
                date(
                    2026,
                    9,
                    23,
                )
            },
        )
    )

    assert result[
        "status"
    ] == "COMPLETE"

    assert result[
        "expected_run_dates"
    ] == [
        "2026-09-21",
        "2026-09-22",
    ]

    assert result[
        "missing_run_dates"
    ] == []


def test_assess_expected_cycles_ignores_observed_date_outside_expected_calendar() -> None:
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                9,
                21,
            ),
            end_date=date(
                2026,
                9,
                27,
            ),
            observed_run_dates=[
                date(
                    2026,
                    9,
                    21,
                ),
                date(
                    2026,
                    9,
                    22,
                ),
                date(
                    2026,
                    9,
                    26,
                ),
            ],
        )
    )

    assert result[
        "expected_cycles"
    ] == 5

    assert result[
        "observed_cycles"
    ] == 2

    assert result[
        "missing_cycles"
    ] == 3

    assert result[
        "missing_run_dates"
    ] == [
        "2026-09-23",
        "2026-09-24",
        "2026-09-25",
    ]