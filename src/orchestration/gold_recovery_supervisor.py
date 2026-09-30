from __future__ import annotations



import os



from datetime import date

from datetime import datetime

from typing import Any

from zoneinfo import ZoneInfo



from src.observability.gold_recovery_watchdog_notifications import (

    publish_watchdog_notification,

)

from src.orchestration.b3_trading_calendar import (

    classify_date,

)

from src.orchestration.gold_recovery import (

    build_recovery_plan,

)

from src.orchestration.gold_recovery_executor import (

    execute_recovery_plan,

)

from src.orchestration.gold_recovery_watchdog_state import (

    read_watchdog_state,

    watchdog_day_is_closed,

    write_watchdog_state,

)





PLATFORM_TIMEZONE = ZoneInfo(

    "America/Sao_Paulo"

)



DEFAULT_LOOKBACK_DAYS = 30



WATCHDOG_TRIGGER = "watchdog"



WATCHDOG_NOTIFICATION_TOPIC_ENV = (

    "FII_GOLD_RECOVERY_WATCHDOG_SNS_TOPIC_ARN"

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





def parse_hour(

    *,

    value: Any,

    field_name: str,

) -> int:

    """

    Converte e valida hora entre 0 e 23.

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

            "Expected hour integer | "

            f"field={field_name} | "

            f"value={value}"

        ) from exc



    if parsed < 0 or parsed > 23:

        raise ValueError(

            "Expected hour between 0 and 23 | "

            f"field={field_name} | "

            f"value={parsed}"

        )



    return parsed





def parse_boolean(

    *,

    value: Any,

    field_name: str,

) -> bool:

    """

    Converte valores booleanos explícitos.

    """



    if isinstance(

        value,

        bool,

    ):

        return value



    if isinstance(

        value,

        str,

    ):

        normalized = (

            value

            .strip()

            .lower()

        )



        if normalized == "true":

            return True



        if normalized == "false":

            return False



    raise ValueError(

        "Expected boolean | "

        f"field={field_name} | "

        f"value={value}"

    )





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



    O calendário operacional não é mais

    configurado pelo supervisor.



    A fonte de verdade passa a ser o

    calendário oficial B3 consumido pelo

    recovery plan.

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

    }





def is_watchdog_event(

    *,

    event: dict[str, Any],

) -> bool:

    """

    Identifica invocação do watchdog.

    """



    trigger = str(

        event.get(

            "trigger",

            "",

        )

    ).strip().lower()



    return (

        trigger

        == WATCHDOG_TRIGGER

    )





def resolve_watchdog_configuration(

    *,

    event: dict[str, Any],

) -> dict[str, Any]:

    """

    Resolve metadados enviados pelo

    EventBridge Scheduler.

    """



    attempt = (

        parse_positive_integer(

            value=event.get(

                "attempt"

            ),

            field_name="attempt",

        )

    )



    max_attempts = (

        parse_positive_integer(

            value=event.get(

                "max_attempts"

            ),

            field_name="max_attempts",

        )

    )



    if attempt > max_attempts:

        raise ValueError(

            "attempt cannot be greater "

            "than max_attempts."

        )



    final_attempt = (

        parse_boolean(

            value=event.get(

                "final_attempt"

            ),

            field_name="final_attempt",

        )

    )



    check_hour = (

        parse_hour(

            value=event.get(

                "check_hour"

            ),

            field_name="check_hour",

        )

    )



    verification_only = (

        parse_boolean(

            value=event.get(

                "verification_only",

                False,

            ),

            field_name="verification_only",

        )

    )



    return {

        "attempt": attempt,

        "max_attempts": max_attempts,

        "final_attempt": final_attempt,

        "check_hour": check_hour,

        "verification_only": (

            verification_only

        ),

    }





def resolve_next_check_hour(

    *,

    check_hour: int,

) -> int | None:

    """

    Próximo horário operacional conhecido

    do watchdog.



    10 -> 14

    14 -> 18

    18 -> 20

    """



    mapping = {

        10: 14,

        14: 18,

        18: 20,

    }



    return mapping.get(

        check_hour

    )





def summarize_recovery_action(

    *,

    execution_result: dict[str, Any],

) -> str:

    """

    Resume ações executadas na rodada.

    """



    actions = []



    for result in (

        execution_result.get(

            "results",

            [],

        )

    ):

        if not isinstance(

            result,

            dict,

        ):

            continue



        action = result.get(

            "action"

        )



        if (

            action

            and action not in actions

        ):

            actions.append(

                str(action)

            )



    if not actions:

        return "NO_ACTION"



    return ", ".join(

        actions

    )





def summarize_pipeline_stage(

    *,

    recovery_plan: dict[str, Any],

) -> str:

    """

    Identifica de forma resumida o ponto

    operacional do pipeline.

    """



    assessments = (

        recovery_plan.get(

            "assessments",

            [],

        )

    )



    statuses = []



    for assessment in assessments:

        if not isinstance(

            assessment,

            dict,

        ):

            continue



        status = assessment.get(

            "status"

        )



        if (

            status

            and status not in statuses

        ):

            statuses.append(

                str(status)

            )



    if not statuses:

        return "PIPELINE"



    return ", ".join(

        statuses

    )





def build_watchdog_details(

    *,

    recovery_plan: dict[str, Any],

    execution_result: dict[str, Any],

) -> dict[str, Any]:

    """

    Monta detalhes compactos para S3

    e notificação operacional.

    """



    return {

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

        "dispatched": (

            execution_result.get(

                "dispatched",

                0,

            )

        ),

        "waiting": (

            execution_result.get(

                "waiting",

                0,

            )

        ),

        "blocked": (

            execution_result.get(

                "blocked",

                0,

            )

        ),

        "skipped": (

            execution_result.get(

                "skipped",

                0,

            )

        ),

    }





def run_standard_supervisor(

    *,

    configuration: dict[str, Any],

) -> dict[str, Any]:

    """

    Mantém o comportamento tradicional

    do supervisor.

    """



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



    print(

        "Gold Recovery Supervisor START | "

        f"end_date={end_date.isoformat()} | "

        f"lookback_days={lookback_days} | "

        "calendar=B3"

    )



    recovery_plan = (

        build_recovery_plan(

            bucket=bucket,

            end_date=end_date,

            lookback_days=(

                lookback_days

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

        "recovery_plan": recovery_plan,

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



def run_watchdog_final_verification(

    *,

    configuration: dict[str, Any],

    watchdog_configuration: dict[str, Any],

) -> dict[str, Any]:

    """

    Executa somente a verificação final.



    Nenhuma ação de recovery é disparada.



    O estado físico atual é redescoberto e

    o dia é encerrado definitivamente como

    sucesso ou falha.

    """



    bucket = configuration[

        "bucket"

    ]



    end_date = configuration[

        "end_date"

    ]



    lookback_days = (

        configuration[

            "lookback_days"

        ]

    )



    watchdog_date = (

        end_date.isoformat()

    )



    attempt = watchdog_configuration[

        "attempt"

    ]



    max_attempts = (

        watchdog_configuration[

            "max_attempts"

        ]

    )



    final_attempt = (

        watchdog_configuration[

            "final_attempt"

        ]

    )



    check_hour = (

        watchdog_configuration[

            "check_hour"

        ]

    )



    recovery_plan = (

        build_recovery_plan(

            bucket=bucket,

            end_date=end_date,

            lookback_days=(

                lookback_days

            ),

        )

    )



    plan_status = str(

        recovery_plan.get(

            "status"

        )

        or "UNKNOWN"

    )



    pipeline_complete = (

        plan_status == "COMPLETE"

    )



    pipeline_stage = (

        summarize_pipeline_stage(

            recovery_plan=(

                recovery_plan

            )

        )

    )



    details = {

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

        "verification_only": True,

        "recovery_dispatched": False,

    }



    if pipeline_complete:

        outcome = "FINAL_SUCCESS"

        state_status = (

            "CLOSED_SUCCESS"

        )

        result_status = "SUCCESS"



    else:

        outcome = "FINAL_FAILED"

        state_status = (

            "CLOSED_FAILED"

        )

        result_status = "FAILED"



    state_result = (

        write_watchdog_state(

            bucket=bucket,

            watchdog_date=(

                watchdog_date

            ),

            status=state_status,

            attempt=attempt,

            max_attempts=max_attempts,

            final_attempt=final_attempt,

            check_hour=check_hour,

            outcome=outcome,

            details=details,

        )

    )



    topic_arn = (

        require_environment_variable(

            WATCHDOG_NOTIFICATION_TOPIC_ENV

        )

    )



    notification = (

        publish_watchdog_notification(

            topic_arn=topic_arn,

            watchdog_date=(

                watchdog_date

            ),

            attempt=attempt,

            max_attempts=max_attempts,

            check_hour=check_hour,

            outcome=outcome,

            plan_status=plan_status,

            recovery_action="NO_ACTION",

            pipeline_stage=(

                pipeline_stage

            ),

            result_status=(

                result_status

            ),

            final_attempt=True,

            next_check_hour=None,

            details=details,

        )

    )



    print(

        "Gold Recovery Watchdog FINAL | "

        f"watchdog_date={watchdog_date} | "

        f"outcome={outcome} | "

        f"plan_status={plan_status}"

    )



    return {

        "status": result_status,

        "supervisor": (

            "gold-recovery-watchdog"

        ),

        "watchdog": {

            "date": watchdog_date,

            "attempt": attempt,

            "max_attempts": (

                max_attempts

            ),

            "final_attempt": True,

            "check_hour": check_hour,

            "verification_only": True,

            "outcome": outcome,

            "state": state_result,

            "notification": (

                notification

            ),

        },

        "plan_status": plan_status,

        "recovery_plan": (

            recovery_plan

        ),

    }





def watchdog_check_already_processed(

    *,

    existing_state: dict[str, Any] | None,

    attempt: int,

    check_hour: int,

) -> bool:

    """

    Evita repetir exatamente o mesmo check

    do watchdog quando o Scheduler entregar

    o mesmo evento mais de uma vez.

    """



    if not isinstance(

        existing_state,

        dict,

    ):

        return False



    try:

        existing_attempt = int(

            existing_state.get(

                "attempt"

            )

        )



        existing_check_hour = int(

            existing_state.get(

                "check_hour"

            )

        )



    except (

        TypeError,

        ValueError,

    ):

        return False



    return (

        existing_attempt == attempt

        and existing_check_hour == check_hour

    )




def run_watchdog_supervisor(

    *,

    configuration: dict[str, Any],

    event: dict[str, Any],

) -> dict[str, Any]:

    """

    Executa uma rodada controlada pelo

    watchdog diário.

    """



    watchdog_configuration = (

        resolve_watchdog_configuration(

            event=event

        )

    )



    bucket = configuration[

        "bucket"

    ]



    end_date = configuration[

        "end_date"

    ]



    watchdog_date = (

        end_date.isoformat()

    )



    calendar_classification = (

        classify_date(

            end_date

        )

    )



    if not bool(

        calendar_classification.get(

            "expected",

            False,

        )

    ):

        print(

            "Gold Recovery Watchdog NO_ACTION | "

            f"watchdog_date={watchdog_date} | "

            "reason=NON_TRADING_DAY | "

            "calendar_status="

            f"{calendar_classification.get('status')}"

        )



        return {

            "status": "NO_ACTION",

            "supervisor": (

                "gold-recovery-watchdog"

            ),

            "watchdog_date": (

                watchdog_date

            ),

            "reason": (

                "NON_TRADING_DAY"

            ),

            "calendar": (

                calendar_classification

            ),

        }



    existing_state = (

        read_watchdog_state(

            bucket=bucket,

            watchdog_date=(

                watchdog_date

            ),

        )

    )



    if watchdog_day_is_closed(

        existing_state

    ):

        print(

            "Gold Recovery Watchdog NO_ACTION | "

            f"watchdog_date={watchdog_date} | "

            "reason=DAY_ALREADY_CLOSED"

        )



        return {

            "status": "NO_ACTION",

            "supervisor": (

                "gold-recovery-watchdog"

            ),

            "watchdog_date": (

                watchdog_date

            ),

            "reason": (

                "DAY_ALREADY_CLOSED"

            ),

            "state": existing_state,

        }



    if watchdog_check_already_processed(

        existing_state=existing_state,

        attempt=(

            watchdog_configuration[

                "attempt"

            ]

        ),

        check_hour=(

            watchdog_configuration[

                "check_hour"

            ]

        ),

    ):

        print(

            "Gold Recovery Watchdog NO_ACTION | "

            f"watchdog_date={watchdog_date} | "

            "reason=CHECK_ALREADY_PROCESSED | "

            "attempt="

            f"{watchdog_configuration['attempt']} | "

            "check_hour="

            f"{watchdog_configuration['check_hour']}"

        )



        return {

            "status": "NO_ACTION",

            "supervisor": (

                "gold-recovery-watchdog"

            ),

            "watchdog_date": (

                watchdog_date

            ),

            "reason": (

                "CHECK_ALREADY_PROCESSED"

            ),

            "state": existing_state,

        }



    if (

        watchdog_configuration[

            "verification_only"

        ]

    ):

        return (

            run_watchdog_final_verification(

                configuration=(

                    configuration

                ),

                watchdog_configuration=(

                    watchdog_configuration

                ),

            )

        )



    standard_result = (

        run_standard_supervisor(

            configuration=configuration

        )

    )



    recovery_plan = (

        standard_result.get(

            "recovery_plan",

            {},

        )

    )



    execution_result = (

        standard_result.get(

            "execution",

            {}

        )

    )



    plan_status = str(

        standard_result.get(

            "plan_status"

        )

        or "UNKNOWN"

    )



    attempt = watchdog_configuration[

        "attempt"

    ]



    max_attempts = (

        watchdog_configuration[

            "max_attempts"

        ]

    )



    final_attempt = (

        watchdog_configuration[

            "final_attempt"

        ]

    )



    check_hour = (

        watchdog_configuration[

            "check_hour"

        ]

    )



    dispatched = int(

        execution_result.get(

            "dispatched",

            0,

        )

        or 0

    )



    waiting = int(

        execution_result.get(

            "waiting",

            0,

        )

        or 0

    )



    blocked = int(

        execution_result.get(

            "blocked",

            0,

        )

        or 0

    )



    pipeline_complete = (

        plan_status == "COMPLETE"

        and dispatched == 0

        and waiting == 0

        and blocked == 0

    )



    recovery_action = (

        summarize_recovery_action(

            execution_result=(

                execution_result

            )

        )

    )



    pipeline_stage = (

        summarize_pipeline_stage(

            recovery_plan=(

                recovery_plan

            )

        )

    )



    details = (

        build_watchdog_details(

            recovery_plan=(

                recovery_plan

            ),

            execution_result=(

                execution_result

            ),

        )

    )



    if pipeline_complete:

        outcome = (

            "PIPELINE_COMPLETE"

        )



        state_status = (

            "CLOSED_SUCCESS"

        )



        result_status = (

            "SUCCESS"

        )



        next_check_hour = None



    elif final_attempt:

        if dispatched > 0:

            outcome = (

                "FINAL_RECOVERY_DISPATCHED"

            )



            result_status = (

                "DISPATCHED"

            )



        else:

            outcome = (

                "FINAL_ATTEMPT_PENDING"

            )



            result_status = (

                "PENDING"

            )



        state_status = (

            "FINAL_RECOVERY_DISPATCHED"

        )



        next_check_hour = (

            resolve_next_check_hour(

                check_hour=check_hour

            )

        )



    else:

        if dispatched > 0:

            outcome = (

                "RECOVERY_DISPATCHED"

            )



            result_status = (

                "DISPATCHED"

            )



        else:

            outcome = (

                "RECOVERY_PENDING"

            )



            result_status = (

                "PENDING"

            )



        state_status = "OPEN"



        next_check_hour = (

            resolve_next_check_hour(

                check_hour=check_hour

            )

        )



    state_result = (

        write_watchdog_state(

            bucket=bucket,

            watchdog_date=(

                watchdog_date

            ),

            status=state_status,

            attempt=attempt,

            max_attempts=max_attempts,

            final_attempt=final_attempt,

            check_hour=check_hour,

            outcome=outcome,

            details=details,

        )

    )



    topic_arn = (

        require_environment_variable(

            WATCHDOG_NOTIFICATION_TOPIC_ENV

        )

    )



    notification = (

        publish_watchdog_notification(

            topic_arn=topic_arn,

            watchdog_date=(

                watchdog_date

            ),

            attempt=attempt,

            max_attempts=max_attempts,

            check_hour=check_hour,

            outcome=outcome,

            plan_status=plan_status,

            recovery_action=(

                recovery_action

            ),

            pipeline_stage=(

                pipeline_stage

            ),

            result_status=(

                result_status

            ),

            final_attempt=(

                final_attempt

            ),

            next_check_hour=(

                next_check_hour

            ),

            details=details,

        )

    )



    return {

        **standard_result,

        "supervisor": (

            "gold-recovery-watchdog"

        ),

        "watchdog": {

            "date": (

                watchdog_date

            ),

            "attempt": attempt,

            "max_attempts": (

                max_attempts

            ),

            "final_attempt": (

                final_attempt

            ),

            "check_hour": (

                check_hour

            ),

            "outcome": outcome,

            "state": (

                state_result

            ),

            "notification": (

                notification

            ),

        },

    }





def run_gold_recovery_supervisor(

    *,

    event: dict[str, Any],

) -> dict[str, Any]:

    """

    Executa o Gold Recovery Supervisor.



    Modo padrão:

        comportamento tradicional.



    Modo watchdog:

        adiciona estado diário,

        controle de tentativas e

        notificação SNS.

    """



    configuration = (

        build_supervisor_configuration(

            event=event

        )

    )



    if is_watchdog_event(

        event=event

    ):

        return (

            run_watchdog_supervisor(

                configuration=(

                    configuration

                ),

                event=event,

            )

        )



    return (

        run_standard_supervisor(

            configuration=(

                configuration

            )

        )

    )





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