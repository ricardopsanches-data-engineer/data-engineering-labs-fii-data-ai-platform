from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable


DEFAULT_EXPECTED_WEEKDAYS = frozenset(
    {
        0,  # Monday
        1,  # Tuesday
        2,  # Wednesday
        3,  # Thursday
        4,  # Friday
    }
)


def normalize_excluded_dates(
    excluded_dates: (
        Iterable[date] | None
    ),
) -> set[date]:
    """
    Normaliza datas explicitamente excluídas
    do calendário operacional.

    Exemplos:
    - feriados;
    - paralisações planejadas;
    - datas em que a plataforma não deveria
      executar por decisão operacional.
    """

    if excluded_dates is None:
        return set()

    return set(
        excluded_dates
    )


def generate_expected_run_dates(
    *,
    start_date: date,
    end_date: date,
    expected_weekdays: (
        Iterable[int]
        | None
    ) = None,
    excluded_dates: (
        Iterable[date]
        | None
    ) = None,
) -> list[date]:
    """
    Gera as datas em que a plataforma
    deveria ter executado.

    Não consulta AWS e não infere existência
    de dados.

    O calendário é determinado por:
    - intervalo solicitado;
    - weekdays esperados;
    - exclusões explícitas.
    """

    if start_date > end_date:
        raise ValueError(
            "start_date must be "
            "<= end_date."
        )

    weekdays = (
        set(
            DEFAULT_EXPECTED_WEEKDAYS
        )
        if expected_weekdays is None
        else set(
            expected_weekdays
        )
    )

    invalid_weekdays = {
        weekday
        for weekday in weekdays
        if weekday < 0
        or weekday > 6
    }

    if invalid_weekdays:
        raise ValueError(
            "expected_weekdays must "
            "contain values from 0 to 6."
        )

    exclusions = (
        normalize_excluded_dates(
            excluded_dates
        )
    )

    expected_dates: list[
        date
    ] = []

    current_date = (
        start_date
    )

    while (
        current_date
        <= end_date
    ):
        if (
            current_date.weekday()
            in weekdays
            and current_date
            not in exclusions
        ):
            expected_dates.append(
                current_date
            )

        current_date += (
            timedelta(
                days=1
            )
        )

    return expected_dates


def detect_missing_run_dates(
    *,
    expected_run_dates: (
        Iterable[date]
    ),
    observed_run_dates: (
        Iterable[date]
    ),
) -> list[date]:
    """
    Detecta ciclos esperados que não possuem
    nenhuma evidência observada.

    O detector não tenta recuperar nada.
    Apenas identifica ausência total.
    """

    expected = set(
        expected_run_dates
    )

    observed = set(
        observed_run_dates
    )

    return sorted(
        expected
        - observed
    )


def assess_expected_cycles(
    *,
    start_date: date,
    end_date: date,
    observed_run_dates: (
        Iterable[date]
    ),
    expected_weekdays: (
        Iterable[int]
        | None
    ) = None,
    excluded_dates: (
        Iterable[date]
        | None
    ) = None,
) -> dict:
    """
    Compara calendário operacional esperado
    contra os ciclos realmente observados.

    Retorna somente diagnóstico.
    Nenhuma ação AWS é executada.
    """

    expected_dates = (
        generate_expected_run_dates(
            start_date=start_date,
            end_date=end_date,
            expected_weekdays=(
                expected_weekdays
            ),
            excluded_dates=(
                excluded_dates
            ),
        )
    )

    observed_dates = sorted(
        set(
            observed_run_dates
        )
    )

    missing_dates = (
        detect_missing_run_dates(
            expected_run_dates=(
                expected_dates
            ),
            observed_run_dates=(
                observed_dates
            ),
        )
    )

    return {
        "start_date": (
            start_date.isoformat()
        ),
        "end_date": (
            end_date.isoformat()
        ),
        "expected_run_dates": [
            value.isoformat()
            for value
            in expected_dates
        ],
        "observed_run_dates": [
            value.isoformat()
            for value
            in observed_dates
        ],
        "missing_run_dates": [
            value.isoformat()
            for value
            in missing_dates
        ],
        "expected_cycles": len(
            expected_dates
        ),
        "observed_cycles": len(
            set(
                expected_dates
            )
            & set(
                observed_dates
            )
        ),
        "missing_cycles": len(
            missing_dates
        ),
        "status": (
            "GAPS_DETECTED"
            if missing_dates
            else "COMPLETE"
        ),
    }