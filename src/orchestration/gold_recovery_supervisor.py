from __future__ import annotations

import os

from datetime import date
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.orchestration.gold_recovery import (
    build_recovery_plan,
)
from src.orchestration.gold_recovery_executor import (
    execute_recovery_plan,
)


PLATFORM_TIMEZONE = ZoneInfo(
    "America/Sao_Paulo"
)

DEFAULT_LOOKBACK_DAYS = 30

DEFAULT_EXPECTED_WEEKDAYS = (
    0,
    1,
    2,
    3,
    4,
)

RAW_TO_SILVER_ENVIRONMENT_VARIABLES = {
    "b3": (
        "FII_B3_RAW_TO_SILVER_FUNCTION_NAME"
    ),
    "cvm": (
        "FII_CVM_RAW_TO_SILVER_FUNCTION_NAME"
    ),
    "b3_instruments": (
        "FII_B3_INSTRUMENTS_RAW_TO_SILVER_FUNCTION_NAME"
    ),
}


def require_environment_variable(
    name: str,
) -> str:
    """
    Retorna uma variável de ambiente
    obrigatória.

    Falha explicitamente quando a
    configuração necessária não existe.
    """

    value = os.environ.get(
        name
    )

    if not value:
        raise RuntimeError(
            "Required environment variable "
            "is missing | "
            f"name={name}"
        )

    return value


def parse_positive_integer(
    *,
    value: Any,
    field_name: str,
) -> int:
    """
    Converte e valida inteiro positivo.
    """

    try:
        parsed = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Expected positive integer | "
            f"field={field_name} | "
            f"value={value}"
        ) from exc

    if parsed < 1:
        raise ValueError(
            "Expected positive integer | "
            f"field={field_name} | "
            f"value={parsed}"
        )

    return parsed


def parse_iso_date(
    *,
    value: Any,
    field_name: str,
) -> date:
    """
    Converte YYYY-MM-DD para date.
    """

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "Expected ISO date string | "
            f"field={field_name} | "
            f"value={value}"
        )

    try:
        return date.fromisoformat(
            value
        )

    except ValueError as exc:
        raise ValueError(
            "Invalid ISO date | "
            f"field={field_name} | "
            f"value={value}"
        ) from exc


def resolve_end_date(
    *,
    event: dict[str, Any],
) -> date:
    """
    Resolve a data final da janela.

    Ordem:

    1. event.end_date explícita;
    2. data atual da plataforma
       America/Sao_Paulo.
    """

    explicit_end_date = event.get(
        "end_date"
    )

    if explicit_end_date is not None:
        return parse_iso_date(
            value=explicit_end_date,
            field_name="end_date",
        )

    return (
        datetime.now(
            PLATFORM_TIMEZONE
        )
        .date()
    )


def resolve_lookback_days(
    *,
    event: dict[str, Any],
) -> int:
    """
    Resolve janela operacional de recovery.

    Ordem:

    1. event.lookback_days;
    2. FII_GOLD_RECOVERY_LOOKBACK_DAYS;
    3. DEFAULT_LOOKBACK_DAYS.
    """

    explicit_lookback = event.get(
        "lookback_days"
    )

    if explicit_lookback is not None:
        return parse_positive_integer(
            value=explicit_lookback,
            field_name="lookback_days",
        )

    environment_lookback = (
        os.environ.get(
            "FII_GOLD_RECOVERY_LOOKBACK_DAYS"
        )
    )

    if environment_lookback:
        return parse_positive_integer(
            value=environment_lookback,
            field_name=(
                "FII_GOLD_RECOVERY_LOOKBACK_DAYS"
            ),
        )

    return DEFAULT_LOOKBACK_DAYS


def parse_expected_weekdays(
    value: Any,
) -> tuple[int, ...]:
    """
    Converte dias da semana para inteiros.

    Convenção Python:

    0 = segunda-feira
    1 = terça-feira
    ...
    6 = domingo

    Formatos aceitos:

    [0, 1, 2, 3, 4]

    ou:

    "0,1,2,3,4"
    """

    if isinstance(
        value,
        str,
    ):
        raw_values = [
            item.strip()
            for item
            in value.split(",")
            if item.strip()
        ]

    elif isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        raw_values = list(
            value
        )

    else:
        raise ValueError(
            "Invalid expected weekdays | "
            f"value={value}"
        )

    weekdays = []

    for raw_value in raw_values:
        try:
            weekday = int(
                raw_value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Invalid weekday value | "
                f"value={raw_value}"
            ) from exc

        if weekday < 0 or weekday > 6:
            raise ValueError(
                "Weekday must be between "
                "0 and 6 | "
                f"value={weekday}"
            )

        weekdays.append(
            weekday
        )

    if not weekdays:
        raise ValueError(
            "Expected weekdays cannot "
            "be empty."
        )

    return tuple(
        sorted(
            set(
                weekdays
            )
        )
    )


def resolve_expected_weekdays(
    *,
    event: dict[str, Any],
) -> tuple[int, ...]:
    """
    Resolve calendário semanal esperado.

    Ordem:

    1. event.expected_weekdays;
    2. FII_GOLD_RECOVERY_EXPECTED_WEEKDAYS;
    3. segunda a sexta.
    """

    explicit_weekdays = (
        event.get(
            "expected_weekdays"
        )
    )

    if explicit_weekdays is not None:
        return parse_expected_weekdays(
            explicit_weekdays
        )

    environment_weekdays = (
        os.environ.get(
            "FII_GOLD_RECOVERY_EXPECTED_WEEKDAYS"
        )
    )

    if environment_weekdays:
        return parse_expected_weekdays(
            environment_weekdays
        )

    return DEFAULT_EXPECTED_WEEKDAYS


def parse_excluded_dates(
    value: Any,
) -> tuple[date, ...]:
    """
    Converte datas excluídas do calendário.

    Formatos aceitos:

    [
        "2026-09-07",
        "2026-10-12",
    ]

    ou:

    "2026-09-07,2026-10-12"
    """

    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        raw_values = [
            item.strip()
            for item
            in value.split(",")
            if item.strip()
        ]

    elif isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        raw_values = list(
            value
        )

    else:
        raise ValueError(
            "Invalid excluded dates | "
            f"value={value}"
        )

    excluded_dates = []

    for raw_value in raw_values:
        excluded_dates.append(
            parse_iso_date(
                value=raw_value,
                field_name=(
                    "excluded_dates"
                ),
            )
        )

    return tuple(
        sorted(
            set(
                excluded_dates
            )
        )
    )


def resolve_excluded_dates(
    *,
    event: dict[str, Any],
) -> tuple[date, ...]:
    """
    Resolve exceções explícitas do
    calendário operacional.

    Ordem:

    1. event.excluded_dates;
    2. FII_GOLD_RECOVERY_EXCLUDED_DATES;
    3. nenhuma exclusão.

    O supervisor não inventa feriados.
    """

    if "excluded_dates" in event:
        return parse_excluded_dates(
            event.get(
                "excluded_dates"
            )
        )

    environment_dates = (
        os.environ.get(
            "FII_GOLD_RECOVERY_EXCLUDED_DATES"
        )
    )

    if environment_dates:
        return parse_excluded_dates(
            environment_dates
        )

    return ()


def resolve_raw_to_silver_functions(
) -> dict[str, str]:
    """
    Resolve o mapeamento das Lambdas
    RAW->Silver já existentes.

    As chaves precisam corresponder às
    fontes usadas pelo recovery plan.
    """

    return {
        source: (
            require_environment_variable(
                environment_variable
            )
        )
        for (
            source,
            environment_variable,
        )
        in (
            RAW_TO_SILVER_ENVIRONMENT_VARIABLES
            .items()
        )
    }


def build_supervisor_configuration(
    *,
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve toda configuração necessária
    para uma rodada do supervisor.
    """

    bucket = (
        require_environment_variable(
            "FII_DATA_LAKE_BUCKET"
        )
    )

    gold_function_name = (
        require_environment_variable(
            "FII_MASTER_GOLD_FUNCTION_NAME"
        )
    )

    raw_to_silver_functions = (
        resolve_raw_to_silver_functions()
    )

    end_date = resolve_end_date(
        event=event
    )

    lookback_days = (
        resolve_lookback_days(
            event=event
        )
    )

    expected_weekdays = (
        resolve_expected_weekdays(
            event=event
        )
    )

    excluded_dates = (
        resolve_excluded_dates(
            event=event
        )
    )

    return {
        "bucket": bucket,
        "gold_function_name": (
            gold_function_name
        ),
        "raw_to_silver_functions": (
            raw_to_silver_functions
        ),
        "end_date": end_date,
        "lookback_days": (
            lookback_days
        ),
        "expected_weekdays": (
            expected_weekdays
        ),
        "excluded_dates": (
            excluded_dates
        ),
    }


def run_gold_recovery_supervisor(
    *,
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Executa uma rodada completa do
    Gold Recovery Supervisor.

    Cada invocação:

    1. redescobre o estado atual;
    2. constrói um novo recovery plan;
    3. executa exatamente uma rodada;
    4. encerra.

    Não existe polling, sleep ou espera
    ativa dentro da Lambda.

    Uma execução futura redescobre o
    estado físico atualizado e continua
    a recuperação quando necessário.
    """

    configuration = (
        build_supervisor_configuration(
            event=event
        )
    )

    bucket = configuration[
        "bucket"
    ]

    gold_function_name = (
        configuration[
            "gold_function_name"
        ]
    )

    raw_to_silver_functions = (
        configuration[
            "raw_to_silver_functions"
        ]
    )

    end_date = configuration[
        "end_date"
    ]

    lookback_days = (
        configuration[
            "lookback_days"
        ]
    )

    expected_weekdays = (
        configuration[
            "expected_weekdays"
        ]
    )

    excluded_dates = (
        configuration[
            "excluded_dates"
        ]
    )

    print(
        "Gold Recovery Supervisor START | "
        f"end_date={end_date.isoformat()} | "
        f"lookback_days={lookback_days} | "
        "expected_weekdays="
        f"{list(expected_weekdays)} | "
        "excluded_dates="
        f"{[item.isoformat() for item in excluded_dates]}"
    )

    recovery_plan = (
        build_recovery_plan(
            bucket=bucket,
            end_date=end_date,
            lookback_days=(
                lookback_days
            ),
            expected_weekdays=(
                expected_weekdays
            ),
            excluded_dates=(
                excluded_dates
            ),
        )
    )

    print(
        "Gold Recovery Supervisor PLAN | "
        f"status={recovery_plan.get('status')} | "
        "total_assessments="
        f"{recovery_plan.get('total_assessments')} | "
        "actionable_cycles="
        f"{recovery_plan.get('actionable_cycles')} | "
        "blocked_cycles="
        f"{recovery_plan.get('blocked_cycles')}"
    )

    execution_result = (
        execute_recovery_plan(
            recovery_plan=(
                recovery_plan
            ),
            gold_function_name=(
                gold_function_name
            ),
            raw_to_silver_functions=(
                raw_to_silver_functions
            ),
            bucket=bucket,
        )
    )

    result = {
        "status": (
            execution_result.get(
                "status"
            )
        ),
        "supervisor": (
            "gold-recovery"
        ),
        "window": (
            recovery_plan.get(
                "window"
            )
        ),
        "plan_status": (
            recovery_plan.get(
                "status"
            )
        ),
        "status_counts": (
            recovery_plan.get(
                "status_counts",
                {},
            )
        ),
        "action_counts": (
            recovery_plan.get(
                "action_counts",
                {},
            )
        ),
        "actionable_cycles": (
            recovery_plan.get(
                "actionable_cycles",
                0,
            )
        ),
        "blocked_cycles": (
            recovery_plan.get(
                "blocked_cycles",
                0,
            )
        ),
        "execution": (
            execution_result
        ),
    }

    print(
        "Gold Recovery Supervisor END | "
        f"status={result['status']} | "
        f"plan_status={result['plan_status']} | "
        "actionable_cycles="
        f"{result['actionable_cycles']} | "
        "blocked_cycles="
        f"{result['blocked_cycles']}"
    )

    return result


def lambda_handler(
    event,
    context,
):
    """
    AWS Lambda entrypoint.
    """

    del context

    normalized_event = (
        event
        if isinstance(
            event,
            dict,
        )
        else {}
    )

    return run_gold_recovery_supervisor(
        event=normalized_event
    )