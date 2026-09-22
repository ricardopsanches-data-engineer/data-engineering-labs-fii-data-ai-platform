from __future__ import annotations

import re

from datetime import date
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.orchestration.gold_readiness import (
    PLATFORM_TIMEZONE,
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
) -> dict[str, Any]:
    """
    Diagnostica recovery operacional
    de um run_date.

    Esta função NÃO executa recuperação.

    COMPLETE
        Gold já existe.

    GOLD_RETRY_REQUIRED
        Gold não existe, mas existe
        exatamente uma Silver física
        para cada fonte.

    RAW_REBUILD_REQUIRED
        Uma ou mais Silvers estão ausentes,
        porém existe exatamente um RAW
        correspondente para cada fonte
        que precisa ser reconstruída.

    RECOVERY_BLOCKED
        Uma Silver está ausente e o RAW
        necessário também está ausente,
        ou existe ambiguidade física.
    """

    gold_key = build_gold_key(
        run_date
    )

    if object_exists(
        bucket=bucket,
        key=gold_key,
    ):
        return {
            "status": "COMPLETE",
            "run_date": (
                run_date.isoformat()
            ),
            "gold_key": gold_key,
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
    }