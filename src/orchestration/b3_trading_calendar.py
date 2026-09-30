from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any


TRADING_DAY = "TRADING_DAY"
WEEKEND = "WEEKEND"
B3_HOLIDAY = "B3_HOLIDAY"


def get_default_calendar_root() -> Path:
    """
    Retorna o diretório padrão dos
    calendários oficiais B3.

    Estrutura esperada:

        config/
        └── calendars/
            └── b3/
                └── YYYY.json

    Funciona tanto no repositório local
    quanto no pacote da Lambda, desde que
    o diretório config seja empacotado
    na raiz do deployment.
    """

    repository_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    return (
        repository_root
        / "config"
        / "calendars"
        / "b3"
    )


def get_calendar_path(
    *,
    year: int,
    calendar_root: Path | None = None,
) -> Path:
    """
    Resolve o arquivo de calendário
    correspondente ao ano solicitado.
    """

    if calendar_root is None:
        calendar_root = (
            get_default_calendar_root()
        )

    return (
        calendar_root
        / f"{year}.json"
    )


def load_b3_calendar(
    *,
    year: int,
    calendar_root: Path | None = None,
) -> dict[str, Any]:
    """
    Carrega o calendário oficial B3
    versionado no projeto.

    O sistema falha explicitamente quando
    não existe calendário para o ano.

    Isso evita assumir incorretamente que
    qualquer segunda a sexta possui pregão.
    """

    calendar_path = get_calendar_path(
        year=year,
        calendar_root=calendar_root,
    )

    if not calendar_path.exists():
        raise FileNotFoundError(
            "B3 trading calendar not found "
            f"for year={year}: "
            f"{calendar_path}"
        )

    try:
        content = calendar_path.read_text(
            encoding="utf-8"
        )

        calendar = json.loads(
            content
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Invalid B3 trading calendar JSON: "
            f"{calendar_path}"
        ) from error

    configured_year = calendar.get(
        "year"
    )

    if configured_year != year:
        raise ValueError(
            "B3 trading calendar year mismatch | "
            f"requested={year} | "
            f"configured={configured_year}"
        )

    if (
        "non_trading_dates"
        not in calendar
    ):
        raise ValueError(
            "B3 trading calendar is missing "
            "'non_trading_dates'."
        )

    if (
        "special_trading_dates"
        not in calendar
    ):
        raise ValueError(
            "B3 trading calendar is missing "
            "'special_trading_dates'."
        )

    return calendar


def build_date_index(
    entries: list[dict[str, Any]],
) -> dict[date, dict[str, Any]]:
    """
    Converte entradas JSON indexadas por
    string ISO em um mapa indexado por date.
    """

    result: dict[
        date,
        dict[str, Any],
    ] = {}

    for entry in entries:
        raw_date = entry.get(
            "date"
        )

        if not raw_date:
            raise ValueError(
                "Calendar entry is missing "
                "'date'."
            )

        try:
            parsed_date = (
                date.fromisoformat(
                    raw_date
                )
            )

        except ValueError as error:
            raise ValueError(
                "Invalid calendar date: "
                f"{raw_date}"
            ) from error

        result[
            parsed_date
        ] = entry

    return result


def classify_date(
    value: date,
    *,
    calendar_root: Path | None = None,
) -> dict[str, Any]:
    """
    Classifica uma data segundo o
    calendário operacional da B3.

    Status possíveis:

        TRADING_DAY
            Pregão esperado.

        WEEKEND
            Sábado ou domingo.

        B3_HOLIDAY
            Data oficialmente sem pregão
            segundo calendário B3.

    A resposta mantém também o motivo,
    permitindo observabilidade e auditoria.
    """

    calendar = load_b3_calendar(
        year=value.year,
        calendar_root=calendar_root,
    )

    if value.weekday() >= 5:
        return {
            "date": value.isoformat(),
            "expected": False,
            "status": WEEKEND,
            "reason": "Weekend",
            "special": False,
        }

    non_trading_dates = (
        build_date_index(
            calendar[
                "non_trading_dates"
            ]
        )
    )

    if value in non_trading_dates:
        entry = (
            non_trading_dates[
                value
            ]
        )

        return {
            "date": value.isoformat(),
            "expected": False,
            "status": B3_HOLIDAY,
            "reason": entry.get(
                "reason",
                "B3 non-trading date",
            ),
            "special": False,
        }

    special_trading_dates = (
        build_date_index(
            calendar[
                "special_trading_dates"
            ]
        )
    )

    if value in special_trading_dates:
        entry = (
            special_trading_dates[
                value
            ]
        )

        return {
            "date": value.isoformat(),
            "expected": True,
            "status": TRADING_DAY,
            "reason": entry.get(
                "reason",
                "Special B3 trading date",
            ),
            "special": True,
        }

    return {
        "date": value.isoformat(),
        "expected": True,
        "status": TRADING_DAY,
        "reason": "Regular B3 trading day",
        "special": False,
    }


def is_trading_day(
    value: date,
    *,
    calendar_root: Path | None = None,
) -> bool:
    """
    Retorna True somente quando existe
    pregão esperado para a data.
    """

    classification = classify_date(
        value,
        calendar_root=calendar_root,
    )

    return bool(
        classification[
            "expected"
        ]
    )


def previous_trading_day(
    reference_date: date,
    *,
    calendar_root: Path | None = None,
) -> date:
    """
    Retorna o último dia de pregão
    anterior à data de referência.

    Exemplo:

        segunda-feira 28/09/2026
        ->
        sexta-feira 25/09/2026
    """

    candidate = (
        reference_date
        - timedelta(days=1)
    )

    max_days_to_check = 370
    checked_days = 0

    while checked_days < max_days_to_check:
        if is_trading_day(
            candidate,
            calendar_root=calendar_root,
        ):
            return candidate

        candidate -= timedelta(
            days=1
        )

        checked_days += 1

    raise RuntimeError(
        "Unable to find previous B3 "
        "trading day within safety window | "
        f"reference_date={reference_date}"
    )


def generate_trading_days(
    *,
    start_date: date,
    end_date: date,
    calendar_root: Path | None = None,
) -> list[date]:
    """
    Retorna todos os pregões esperados
    dentro do intervalo inclusivo.
    """

    if end_date < start_date:
        raise ValueError(
            "end_date must be greater than "
            "or equal to start_date."
        )

    trading_days: list[
        date
    ] = []

    candidate = start_date

    while candidate <= end_date:
        if is_trading_day(
            candidate,
            calendar_root=calendar_root,
        ):
            trading_days.append(
                candidate
            )

        candidate += timedelta(
            days=1
        )

    return trading_days