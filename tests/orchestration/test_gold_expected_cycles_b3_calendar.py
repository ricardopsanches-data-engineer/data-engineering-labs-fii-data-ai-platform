from datetime import date

from src.orchestration import (
    gold_expected_cycles,
)


def test_expected_cycles_uses_b3_calendar_by_default():
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                10,
                9,
            ),
            end_date=date(
                2026,
                10,
                13,
            ),
        )
    )

    assert result == [
        date(
            2026,
            10,
            9,
        ),
        date(
            2026,
            10,
            13,
        ),
    ]


def test_expected_cycles_does_not_expect_b3_holiday():
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                10,
                12,
            ),
            end_date=date(
                2026,
                10,
                12,
            ),
        )
    )

    assert result == []


def test_expected_cycles_does_not_expect_weekend():
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                9,
                26,
            ),
            end_date=date(
                2026,
                9,
                27,
            ),
        )
    )

    assert result == []


def test_expected_cycles_accepts_special_trading_day():
    result = (
        gold_expected_cycles
        .generate_expected_run_dates(
            start_date=date(
                2026,
                7,
                9,
            ),
            end_date=date(
                2026,
                7,
                9,
            ),
        )
    )

    assert result == [
        date(
            2026,
            7,
            9,
        )
    ]


def test_assessment_does_not_report_holiday_as_gap():
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                10,
                9,
            ),
            end_date=date(
                2026,
                10,
                13,
            ),
            observed_run_dates=[
                date(
                    2026,
                    10,
                    9,
                ),
                date(
                    2026,
                    10,
                    13,
                ),
            ],
        )
    )

    assert (
        result[
            "expected_run_dates"
        ]
        == [
            "2026-10-09",
            "2026-10-13",
        ]
    )

    assert (
        result[
            "missing_run_dates"
        ]
        == []
    )

    assert (
        result[
            "missing_cycles"
        ]
        == 0
    )

    assert (
        result[
            "status"
        ]
        == "COMPLETE"
    )


def test_assessment_reports_missing_trading_day_as_gap():
    result = (
        gold_expected_cycles
        .assess_expected_cycles(
            start_date=date(
                2026,
                10,
                9,
            ),
            end_date=date(
                2026,
                10,
                13,
            ),
            observed_run_dates=[
                date(
                    2026,
                    10,
                    9,
                ),
            ],
        )
    )

    assert (
        result[
            "missing_run_dates"
        ]
        == [
            "2026-10-13",
        ]
    )

    assert (
        result[
            "missing_cycles"
        ]
        == 1
    )

    assert (
        result[
            "status"
        ]
        == "GAPS_DETECTED"
    )