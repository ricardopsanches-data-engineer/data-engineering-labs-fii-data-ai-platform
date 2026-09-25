from datetime import date

import pytest

from src.orchestration.b3_trading_calendar import (
    B3_HOLIDAY,
    TRADING_DAY,
    WEEKEND,
    classify_date,
    generate_trading_days,
    is_trading_day,
    load_b3_calendar,
    previous_trading_day,
)


def test_load_b3_calendar_2026():
    calendar = load_b3_calendar(
        year=2026
    )

    assert calendar["year"] == 2026
    assert calendar["market"] == "B3"


def test_classify_regular_trading_day():
    result = classify_date(
        date(2026, 9, 25)
    )

    assert result == {
        "date": "2026-09-25",
        "expected": True,
        "status": TRADING_DAY,
        "reason": (
            "Regular B3 trading day"
        ),
        "special": False,
    }


def test_classify_weekend():
    result = classify_date(
        date(2026, 9, 26)
    )

    assert result["expected"] is False
    assert result["status"] == WEEKEND
    assert result["reason"] == "Weekend"


def test_classify_b3_holiday():
    result = classify_date(
        date(2026, 10, 12)
    )

    assert result["expected"] is False
    assert (
        result["status"]
        == B3_HOLIDAY
    )

    assert (
        result["reason"]
        == "Nossa Senhora Aparecida"
    )


def test_classify_special_trading_day():
    result = classify_date(
        date(2026, 2, 18)
    )

    assert result["expected"] is True
    assert (
        result["status"]
        == TRADING_DAY
    )

    assert result["special"] is True


def test_july_9_is_trading_day():
    result = classify_date(
        date(2026, 7, 9)
    )

    assert result["expected"] is True
    assert (
        result["status"]
        == TRADING_DAY
    )

    assert result["special"] is True


def test_is_trading_day():
    assert (
        is_trading_day(
            date(2026, 9, 25)
        )
        is True
    )

    assert (
        is_trading_day(
            date(2026, 9, 26)
        )
        is False
    )

    assert (
        is_trading_day(
            date(2026, 10, 12)
        )
        is False
    )


def test_previous_trading_day_after_weekend():
    result = previous_trading_day(
        date(2026, 9, 28)
    )

    assert result == date(
        2026,
        9,
        25,
    )


def test_previous_trading_day_after_holiday_and_weekend():
    result = previous_trading_day(
        date(2026, 10, 13)
    )

    assert result == date(
        2026,
        10,
        9,
    )


def test_generate_trading_days():
    result = generate_trading_days(
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


def test_generate_trading_days_rejects_invalid_range():
    with pytest.raises(
        ValueError,
        match="end_date",
    ):
        generate_trading_days(
            start_date=date(
                2026,
                10,
                13,
            ),
            end_date=date(
                2026,
                10,
                9,
            ),
        )


def test_missing_calendar_year_fails_explicitly():
    with pytest.raises(
        FileNotFoundError,
        match="year=2027",
    ):
        classify_date(
            date(
                2027,
                1,
                4,
            )
        )