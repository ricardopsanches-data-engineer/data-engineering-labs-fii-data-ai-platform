from __future__ import annotations

import re

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from typing import Any, Iterable

import boto3
from botocore.exceptions import ClientError

from src.orchestration.gold_expected_cycles import (
    generate_expected_run_dates,
)
from src.orchestration.gold_readiness import (
    PLATFORM_TIMEZONE,
)
from src.orchestration.gold_recovery_state import (
    DEFAULT_STALE_AFTER_MINUTES,
    assess_gold_recovery_state,
)


GOLD_PREFIX = "gold/fii-master"


SOURCE_CONFIG = {
    "b3": {
        "raw_prefix": "raw/b3/",
        "silver_prefix": "silver/b3/",
        "raw_pattern": re.compile(
            r"^raw/b3/"
            r"year=\d{4}/"
            r"month=\d{2}/"
            r"day=\d{2}/"
            r"b3_download_\d{8}\.zip$"
        ),
        "silver_pattern": re.compile(
            r"^silver/b3/"
            r"year=(\d{4})/"
            r"month=(\d{2})/"
            r"day=(\d{2})/"
            r"b3_trades\.parquet$"
        ),
        "gold_input_name": "b3_trades",
    },
    "cvm": {
        "raw_prefix": "raw/cvm/",
        "silver_prefix": "silver/cvm/",
        "raw_pattern": re.compile(
            r"^raw/cvm/"
            r"year=\d{4}/"
            r"month=\d{2}/"
            r"day=\d{2}/"
            r"registro_fundo_classe\.zip$"
        ),
        "silver_pattern": re.compile(
            r"^silver/cvm/"
            r"year=(\d{4})/"
            r"month=(\d{2})/"
            r"day=(\d{2})/"
            r"cvm_fund_classes\.parquet$"
        ),
        "gold_input_name": "cvm",
    },
    "b3_instruments": {
        "raw_prefix": (
            "raw/b3-instruments/"
        ),
        "silver_prefix": (
            "silver/b3-instruments/"
        ),
        "raw_pattern": re.compile(
            r"^raw/b3-instruments/"
            r"year=\d{4}/"
            r"month=\d{2}/"
            r"day=\d{2}/"
            r"pesquisa-pregao\.zip$",
            re.IGNORECASE,
        ),
        "silver_pattern": re.compile(
            r"^silver/b3-instruments/"
            r"year=(\d{4})/"
            r"month=(\d{2})/"
            r"day=(\d{2})/"
            r"b3_instruments\.parquet$",
            re.IGNORECASE,
        ),
        "gold_input_name": (
            "b3_instruments"
        ),
    },
}


ACTION_BY_STATUS = {
    "COMPLETE": "NO_ACTION",
    "IN_PROGRESS": "WAIT_FOR_COMPLETION",
    "GOLD_RETRY_REQUIRED": "RETRY_GOLD",
    "RAW_REBUILD_REQUIRED": (
        "REBUILD_SILVER_FROM_RAW"
    ),
    "RECOVERY_BLOCKED": (
        "ALERT_AND_INVESTIGATE"
    ),
    "MISSING_CYCLE": (
        "INVESTIGATE_MISSING_CYCLE"
    ),
}


def object_exists(
    *,
    bucket: str,
    key: str,
) -> bool:
    """
    Verifica se um objeto existe no S3.

    Retorna False somente quando o objeto
    realmente não existe.

    Outros erros AWS são propagados.
    """

    s3 = boto3.client("s3")

    try:
        s3.head_object(
            Bucket=bucket,
            Key=key,
        )

        return True

    except ClientError as error:
        error_code = (
            error.response
            .get("Error", {})
            .get("Code")
        )

        if error_code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            return False

        raise


def build_gold_key(
    run_date: date,
) -> str:
    """
    Constrói a chave esperada da Gold.
    """

    return (
        f"{GOLD_PREFIX}/"
        f"year={run_date.year}/"
        f"month={run_date.month:02d}/"
        f"day={run_date.day:02d}/"
        "fii_master.parquet"
    )


def object_matches_run_date(
    *,
    last_modified,
    run_date: date,
) -> bool:
    """
    Verifica se o LastModified do objeto,
    convertido para o timezone operacional,
    pertence ao run_date solicitado.
    """

    object_run_date = (
        last_modified
        .astimezone(
            PLATFORM_TIMEZONE
        )
        .date()
    )

    return (
        object_run_date
        == run_date
    )


def discover_objects_for_run_date(
    *,
    bucket: str,
    prefix: str,
    pattern: re.Pattern,
    run_date: date,
) -> list[dict[str, Any]]:
    """
    Descobre objetos físicos de uma camada
    pertencentes a determinado run_date.

    O run_date é derivado do LastModified
    convertido para America/Sao_Paulo.

    Isso evita assumir D-1, dia útil anterior,
    finais de semana ou feriados.
    """

    s3 = boto3.client("s3")

    paginator = s3.get_paginator(
        "list_objects_v2"
    )

    matches: list[
        dict[str, Any]
    ] = []

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=prefix,
    ):
        for item in page.get(
            "Contents",
            [],
        ):
            key = item["Key"]

            if not pattern.fullmatch(
                key
            ):
                continue

            last_modified = item[
                "LastModified"
            ]

            if not object_matches_run_date(
                last_modified=last_modified,
                run_date=run_date,
            ):
                continue

            matches.append(
                {
                    "key": key,
                    "last_modified": (
                        last_modified
                        .isoformat()
                    ),
                }
            )

    matches.sort(
        key=lambda item: item["key"]
    )

    return matches


def extract_reference_date_from_silver_key(
    *,
    source: str,
    key: str,
) -> date:
    """
    Extrai a reference_date da partição
    Silver correspondente.
    """

    config = SOURCE_CONFIG[
        source
    ]

    pattern = config[
        "silver_pattern"
    ]

    match = pattern.fullmatch(
        key
    )

    if match is None:
        raise ValueError(
            "Invalid Silver key for "
            f"source={source} | "
            f"key={key}"
        )

    year, month, day = (
        int(value)
        for value in match.groups()
    )

    return date(
        year,
        month,
        day,
    )


def discover_source_state(
    *,
    bucket: str,
    source: str,
    run_date: date,
) -> dict[str, Any]:
    """
    Descobre o estado físico de uma fonte
    para determinado run_date.
    """

    config = SOURCE_CONFIG[
        source
    ]

    silver_objects = (
        discover_objects_for_run_date(
            bucket=bucket,
            prefix=(
                config[
                    "silver_prefix"
                ]
            ),
            pattern=(
                config[
                    "silver_pattern"
                ]
            ),
            run_date=run_date,
        )
    )

    raw_objects = (
        discover_objects_for_run_date(
            bucket=bucket,
            prefix=(
                config[
                    "raw_prefix"
                ]
            ),
            pattern=(
                config[
                    "raw_pattern"
                ]
            ),
            run_date=run_date,
        )
    )

    return {
        "source": source,
        "silver_objects": (
            silver_objects
        ),
        "raw_objects": (
            raw_objects
        ),
    }


def build_gold_payload_from_silver(
    *,
    run_date: date,
    source_states: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, Any]:
    """
    Constrói payload explícito para a Gold
    usando as Silvers físicas encontradas.

    Cada fonte deve ter exatamente uma
    Silver válida para o run_date.
    """

    inputs: dict[
        str,
        dict[str, str],
    ] = {}

    for (
        source,
        config,
    ) in SOURCE_CONFIG.items():
        state = source_states[
            source
        ]

        silver_objects = state[
            "silver_objects"
        ]

        if len(
            silver_objects
        ) != 1:
            raise ValueError(
                "Expected exactly one "
                "Silver object | "
                f"source={source} | "
                f"count="
                f"{len(silver_objects)}"
            )

        silver_key = (
            silver_objects[0][
                "key"
            ]
        )

        reference_date = (
            extract_reference_date_from_silver_key(
                source=source,
                key=silver_key,
            )
        )

        inputs[
            config[
                "gold_input_name"
            ]
        ] = {
            "reference_date": (
                reference_date
                .isoformat()
            ),
            "key": silver_key,
        }

    return {
        "run_date": (
            run_date.isoformat()
        ),
        "inputs": inputs,
    }


def assess_run_date(
    *,
    bucket: str,
    run_date: date,
    now: datetime | None = None,
    stale_after_minutes: int = (
        DEFAULT_STALE_AFTER_MINUTES
    ),
) -> dict[str, Any]:
    """
    Diagnostica recovery operacional
    de um run_date.

    Esta função NÃO executa recuperação.

    O diagnóstico combina:

    - existência física da Gold;
    - execution state da Gold;
    - existência física das Silvers;
    - existência física das RAWs.

    COMPLETE
        Gold já existe.

    IN_PROGRESS
        Gold ainda não existe, mas existe
        execução STARTED ainda válida.

    GOLD_RETRY_REQUIRED
        Gold não existe, a execução permite
        retry e todas as Silvers existem.

    RAW_REBUILD_REQUIRED
        Uma ou mais Silvers estão ausentes,
        porém existe exatamente um RAW
        correspondente para cada fonte.

    RECOVERY_BLOCKED
        Recuperação automática não pode
        prosseguir com segurança.
    """

    effective_now = (
        now
        if now is not None
        else datetime.now(
            timezone.utc
        )
    )

    gold_key = build_gold_key(
        run_date
    )

    gold_exists = object_exists(
        bucket=bucket,
        key=gold_key,
    )

    execution_assessment = (
        assess_gold_recovery_state(
            bucket=bucket,
            run_date=(
                run_date.isoformat()
            ),
            gold_exists=gold_exists,
            now=effective_now,
            stale_after_minutes=(
                stale_after_minutes
            ),
        )
    )

    classification = (
        execution_assessment[
            "classification"
        ]
    )

    classification_status = (
        classification[
            "status"
        ]
    )

    if (
        classification_status
        == "COMPLETE"
    ):
        return {
            "status": "COMPLETE",
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
            "execution_assessment": (
                execution_assessment
            ),
        }

    if (
        classification_status
        == "IN_PROGRESS"
    ):
        return {
            "status": "IN_PROGRESS",
            "reason": (
                classification[
                    "reason"
                ]
            ),
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
            "execution_assessment": (
                execution_assessment
            ),
        }

    if classification_status in {
        "INCONSISTENT_STATE",
        "UNKNOWN_STATE",
    }:
        return {
            "status": (
                "RECOVERY_BLOCKED"
            ),
            "reason": (
                classification[
                    "reason"
                ]
            ),
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
            "execution_assessment": (
                execution_assessment
            ),
        }

    source_states = {
        source: discover_source_state(
            bucket=bucket,
            source=source,
            run_date=run_date,
        )
        for source
        in SOURCE_CONFIG
    }

    ambiguous_silver_sources = [
        source
        for source, state
        in source_states.items()
        if len(
            state[
                "silver_objects"
            ]
        ) > 1
    ]

    if ambiguous_silver_sources:
        return {
            "status": (
                "RECOVERY_BLOCKED"
            ),
            "reason": (
                "AMBIGUOUS_SILVER"
            ),
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
            "sources": (
                ambiguous_silver_sources
            ),
            "source_states": (
                source_states
            ),
            "execution_assessment": (
                execution_assessment
            ),
        }

    missing_silver_sources = [
        source
        for source, state
        in source_states.items()
        if len(
            state[
                "silver_objects"
            ]
        ) == 0
    ]

    if not missing_silver_sources:
        gold_payload = (
            build_gold_payload_from_silver(
                run_date=run_date,
                source_states=(
                    source_states
                ),
            )
        )

        return {
            "status": (
                "GOLD_RETRY_REQUIRED"
            ),
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
            "source_states": (
                source_states
            ),
            "gold_payload": (
                gold_payload
            ),
            "execution_assessment": (
                execution_assessment
            ),
        }

    blocked_sources = []
    rebuild_sources = []

    for source in (
        missing_silver_sources
    ):
        raw_objects = (
            source_states[
                source
            ][
                "raw_objects"
            ]
        )

        if len(
            raw_objects
        ) == 1:
            rebuild_sources.append(
                source
            )

        else:
            blocked_sources.append(
                {
                    "source": source,
                    "raw_count": len(
                        raw_objects
                    ),
                    "reason": (
                        "RAW_MISSING"
                        if not raw_objects
                        else "AMBIGUOUS_RAW"
                    ),
                }
            )

    if blocked_sources:
        return {
            "status": (
                "RECOVERY_BLOCKED"
            ),
            "reason": (
                "RAW_UNAVAILABLE"
            ),
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
            "missing_silver_sources": (
                missing_silver_sources
            ),
            "blocked_sources": (
                blocked_sources
            ),
            "source_states": (
                source_states
            ),
            "execution_assessment": (
                execution_assessment
            ),
        }

    return {
        "status": (
            "RAW_REBUILD_REQUIRED"
        ),
        "run_date": (
            run_date.isoformat()
        ),
        "gold_key": gold_key,
        "rebuild_sources": (
            rebuild_sources
        ),
        "source_states": (
            source_states
        ),
        "execution_assessment": (
            execution_assessment
        ),
    }


def discover_observed_run_dates(
    *,
    bucket: str,
    end_date: date,
    lookback_days: int,
) -> list[date]:
    """
    Descobre os run_dates realmente observados
    nas RAWs dentro da janela operacional.

    O run_date é derivado do LastModified
    convertido para America/Sao_Paulo.

    Não assume calendário de pregão,
    dias úteis, finais de semana ou feriados.
    """

    if lookback_days < 1:
        raise ValueError(
            "lookback_days must be >= 1."
        )

    start_date = (
        end_date
        - timedelta(
            days=lookback_days - 1
        )
    )

    s3 = boto3.client("s3")

    observed_dates: set[date] = set()

    for config in SOURCE_CONFIG.values():
        prefix = config[
            "raw_prefix"
        ]

        pattern = config[
            "raw_pattern"
        ]

        paginator = s3.get_paginator(
            "list_objects_v2"
        )

        for page in paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
        ):
            for item in page.get(
                "Contents",
                [],
            ):
                key = item[
                    "Key"
                ]

                if not pattern.fullmatch(
                    key
                ):
                    continue

                last_modified = item[
                    "LastModified"
                ]

                object_run_date = (
                    last_modified
                    .astimezone(
                        PLATFORM_TIMEZONE
                    )
                    .date()
                )

                if (
                    start_date
                    <= object_run_date
                    <= end_date
                ):
                    observed_dates.add(
                        object_run_date
                    )

    return sorted(
        observed_dates
    )


def assess_recovery_window(
    *,
    bucket: str,
    end_date: date,
    lookback_days: int,
) -> dict[str, Any]:
    """
    Diagnostica todos os ciclos observados
    dentro da janela operacional.

    Esta função NÃO executa recuperação.

    O intervalo é dinâmico e configurável.
    Dias sem qualquer evidência RAW não são
    automaticamente considerados falha.

    A detecção de ausência total de um ciclo
    pertence ao estágio seguinte do recovery.
    """

    run_dates = (
        discover_observed_run_dates(
            bucket=bucket,
            end_date=end_date,
            lookback_days=lookback_days,
        )
    )

    assessments = [
        assess_run_date(
            bucket=bucket,
            run_date=run_date,
        )
        for run_date in run_dates
    ]

    status_counts: dict[
        str,
        int,
    ] = {}

    for assessment in assessments:
        status = assessment[
            "status"
        ]

        status_counts[
            status
        ] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    return {
        "window": {
            "end_date": (
                end_date.isoformat()
            ),
            "lookback_days": (
                lookback_days
            ),
        },
        "observed_run_dates": [
            run_date.isoformat()
            for run_date
            in run_dates
        ],
        "total_cycles": len(
            assessments
        ),
        "status_counts": (
            status_counts
        ),
        "assessments": assessments,
    }


def build_window_start_date(
    *,
    end_date: date,
    lookback_days: int,
) -> date:
    """
    Calcula dinamicamente a primeira data
    da janela operacional.

    A própria end_date faz parte da janela.
    """

    if lookback_days < 1:
        raise ValueError(
            "lookback_days must be >= 1."
        )

    return (
        end_date
        - timedelta(
            days=lookback_days - 1
        )
    )


def build_missing_cycle_assessment(
    *,
    run_date: date,
) -> dict[str, Any]:
    """
    Cria diagnóstico para um ciclo que era
    esperado pelo calendário operacional,
    mas não deixou qualquer evidência RAW.

    Nenhuma recuperação é executada.
    """

    status = "MISSING_CYCLE"

    return {
        "status": status,
        "run_date": (
            run_date.isoformat()
        ),
        "action": (
            ACTION_BY_STATUS[
                status
            ]
        ),
        "reason": (
            "NO_OBSERVED_RAW_EVIDENCE"
        ),
    }


def normalize_recovery_assessment(
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """
    Acrescenta ao diagnóstico a ação
    correspondente ao seu status.

    O conteúdo original é preservado.
    """

    status = assessment[
        "status"
    ]

    if status not in (
        ACTION_BY_STATUS
    ):
        raise ValueError(
            "Unsupported recovery status: "
            f"{status}"
        )

    return {
        **assessment,
        "action": (
            ACTION_BY_STATUS[
                status
            ]
        ),
    }


def build_status_counts(
    *,
    assessments: Iterable[
        dict[str, Any]
    ],
) -> dict[str, int]:
    """
    Conta ciclos por status.
    """

    counts: dict[
        str,
        int,
    ] = {}

    for assessment in assessments:
        status = assessment[
            "status"
        ]

        counts[
            status
        ] = (
            counts.get(
                status,
                0,
            )
            + 1
        )

    return counts


def build_action_counts(
    *,
    assessments: Iterable[
        dict[str, Any]
    ],
) -> dict[str, int]:
    """
    Conta ciclos por ação recomendada.
    """

    counts: dict[
        str,
        int,
    ] = {}

    for assessment in assessments:
        action = assessment[
            "action"
        ]

        counts[
            action
        ] = (
            counts.get(
                action,
                0,
            )
            + 1
        )

    return counts


def build_recovery_plan(
    *,
    bucket: str,
    end_date: date,
    lookback_days: int,
    expected_weekdays: (
        Iterable[int]
        | None
    ) = None,
    excluded_dates: (
        Iterable[date]
        | None
    ) = None,
) -> dict[str, Any]:
    """
    Constrói o plano consolidado de
    recuperação operacional.

    Esta função NÃO executa ações AWS.

    Combina:

    1. calendário operacional esperado;
    2. ciclos observados fisicamente;
    3. diagnóstico de cada run_date;
    4. ciclos totalmente ausentes;
    5. ação recomendada por ciclo.

    Status possíveis:

    COMPLETE
        Gold já existe.

    GOLD_RETRY_REQUIRED
        As Silvers existem e a Gold precisa
        ser reconstruída.

    RAW_REBUILD_REQUIRED
        Existe RAW para reconstruir uma
        ou mais Silvers.

    RECOVERY_BLOCKED
        A recuperação automática não pode
        continuar com segurança.

    MISSING_CYCLE
        O ciclo era esperado, mas não existe
        evidência RAW daquele run_date.
    """

    start_date = (
        build_window_start_date(
            end_date=end_date,
            lookback_days=(
                lookback_days
            ),
        )
    )

    expected_run_dates = (
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

    observed_run_dates = (
        discover_observed_run_dates(
            bucket=bucket,
            end_date=end_date,
            lookback_days=(
                lookback_days
            ),
        )
    )

    expected_set = set(
        expected_run_dates
    )

    observed_set = set(
        observed_run_dates
    )

    missing_run_dates = sorted(
        expected_set
        - observed_set
    )

    unexpected_observed_run_dates = (
        sorted(
            observed_set
            - expected_set
        )
    )

    assessments: list[
        dict[str, Any]
    ] = []

    for run_date in sorted(
        observed_set
    ):
        assessment = (
            assess_run_date(
                bucket=bucket,
                run_date=run_date,
            )
        )

        normalized = (
            normalize_recovery_assessment(
                assessment
            )
        )

        normalized[
            "calendar_status"
        ] = (
            "EXPECTED"
            if run_date
            in expected_set
            else "UNEXPECTED_OBSERVED"
        )

        assessments.append(
            normalized
        )

    for run_date in (
        missing_run_dates
    ):
        missing_assessment = (
            build_missing_cycle_assessment(
                run_date=run_date
            )
        )

        missing_assessment[
            "calendar_status"
        ] = "EXPECTED"

        assessments.append(
            missing_assessment
        )

    assessments.sort(
        key=lambda item: (
            item[
                "run_date"
            ]
        )
    )

    status_counts = (
        build_status_counts(
            assessments=(
                assessments
            )
        )
    )

    action_counts = (
        build_action_counts(
            assessments=(
                assessments
            )
        )
    )

    actionable_cycles = [
        assessment
        for assessment
        in assessments
        if assessment[
            "action"
        ]
        not in {
            "NO_ACTION",
            "WAIT_FOR_COMPLETION",
        }
    ]

    blocked_cycles = [
        assessment
        for assessment
        in assessments
        if assessment[
            "status"
        ]
        in {
            "RECOVERY_BLOCKED",
            "MISSING_CYCLE",
        }
    ]

    return {
        "status": (
            "RECOVERY_REQUIRED"
            if actionable_cycles
            else "COMPLETE"
        ),
        "window": {
            "start_date": (
                start_date.isoformat()
            ),
            "end_date": (
                end_date.isoformat()
            ),
            "lookback_days": (
                lookback_days
            ),
        },
        "expected_run_dates": [
            run_date.isoformat()
            for run_date
            in expected_run_dates
        ],
        "observed_run_dates": [
            run_date.isoformat()
            for run_date
            in sorted(
                observed_set
            )
        ],
        "missing_run_dates": [
            run_date.isoformat()
            for run_date
            in missing_run_dates
        ],
        "unexpected_observed_run_dates": [
            run_date.isoformat()
            for run_date
            in (
                unexpected_observed_run_dates
            )
        ],
        "total_assessments": len(
            assessments
        ),
        "status_counts": (
            status_counts
        ),
        "action_counts": (
            action_counts
        ),
        "actionable_cycles": len(
            actionable_cycles
        ),
        "blocked_cycles": len(
            blocked_cycles
        ),
        "assessments": (
            assessments
        ),
    }