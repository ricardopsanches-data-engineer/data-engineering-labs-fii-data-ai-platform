from __future__ import annotations

from datetime import date
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.orchestration.gold_readiness_coordinator import (
    build_gold_payload,
    load_required_markers,
    validate_marker_fields,
    validate_marker_run_dates,
)


GOLD_PREFIX = "gold/fii-master"

SOURCE_MARKERS = {
    "b3": "b3_SUCCESS.json",
    "cvm": "cvm_SUCCESS.json",
    "b3_instruments": "b3_instruments_SUCCESS.json",
}


def object_exists(
    *,
    bucket: str,
    key: str,
) -> bool:
    """
    Verifica se um objeto existe no S3.

    Retorna:
        True  -> objeto existe
        False -> objeto não existe

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
    Constrói a chave esperada da Gold
    para um determinado ciclo.
    """

    return (
        f"{GOLD_PREFIX}/"
        f"year={run_date.year}/"
        f"month={run_date.month:02d}/"
        f"day={run_date.day:02d}/"
        "fii_master.parquet"
    )


def validate_marker_silver_objects(
    *,
    bucket: str,
    markers: dict[str, dict[str, Any]],
) -> dict[str, bool]:
    """
    Confirma se cada marker aponta para uma
    Silver que ainda existe fisicamente no S3.
    """

    result: dict[str, bool] = {}

    for source, marker in markers.items():
        silver_key = marker["silver_key"]

        result[source] = object_exists(
            bucket=bucket,
            key=silver_key,
        )

    return result


def assess_run_date(
    *,
    bucket: str,
    run_date: date,
) -> dict[str, Any]:
    """
    Diagnostica o estado de recovery de um
    run_date específico.

    Esta função NÃO executa recuperação.

    Classificações:

    COMPLETE
        Gold já existe.

    GOLD_RETRY_REQUIRED
        Gold não existe, mas os três markers
        existem e suas Silvers continuam
        disponíveis.

    SILVER_RECOVERY_REQUIRED
        Gold não existe e o conjunto de
        readiness ainda não está completo.

    SILVER_OBJECT_MISSING
        Os três markers existem, porém pelo
        menos uma Silver referenciada já não
        existe.

    O próximo estágio do Recovery Coordinator
    decidirá quais RAWs precisam ser usados.
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
            "run_date": run_date.isoformat(),
            "gold_key": gold_key,
        }

    markers = load_required_markers(
        bucket=bucket,
        run_date=run_date,
    )

    if markers is None:
        return {
            "status": (
                "SILVER_RECOVERY_REQUIRED"
            ),
            "run_date": run_date.isoformat(),
            "gold_key": gold_key,
        }

    validate_marker_run_dates(
        run_date=run_date,
        markers=markers,
    )

    validate_marker_fields(
        markers
    )

    silver_objects = (
        validate_marker_silver_objects(
            bucket=bucket,
            markers=markers,
        )
    )

    missing_silver_sources = [
        source
        for source, exists
        in silver_objects.items()
        if not exists
    ]

    if missing_silver_sources:
        return {
            "status": "SILVER_OBJECT_MISSING",
            "run_date": run_date.isoformat(),
            "gold_key": gold_key,
            "missing_sources": (
                missing_silver_sources
            ),
            "silver_objects": (
                silver_objects
            ),
        }

    gold_payload = build_gold_payload(
        run_date=run_date,
        markers=markers,
    )

    return {
        "status": "GOLD_RETRY_REQUIRED",
        "run_date": run_date.isoformat(),
        "gold_key": gold_key,
        "silver_objects": silver_objects,
        "gold_payload": gold_payload,
    }