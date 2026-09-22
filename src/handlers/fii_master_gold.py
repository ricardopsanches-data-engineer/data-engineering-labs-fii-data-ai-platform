from __future__ import annotations

import os
import re

from argparse import Namespace
from datetime import date, datetime
from pathlib import Path

import boto3
import pandas as pd

from src.orchestration.gold_execution_state import (
    mark_execution_failed,
    mark_execution_started,
    mark_execution_succeeded,
)
from src.orchestration.gold_readiness import (
    PLATFORM_TIMEZONE,
)
from src.pipelines.fii_master_gold import (
    DEFAULT_MIN_RESOLUTION_RATE,
    run_pipeline,
)
from src.storage.s3 import upload_file


TMP_ROOT = Path(
    "/tmp/fii-master-gold"
)

TMP_CVM = (
    TMP_ROOT
    / "silver"
    / "cvm"
    / "cvm_fund_classes.parquet"
)

TMP_INSTRUMENTS = (
    TMP_ROOT
    / "silver"
    / "b3-instruments"
    / "b3_instruments.parquet"
)

TMP_TRADES = (
    TMP_ROOT
    / "silver"
    / "b3"
    / "b3_trades.parquet"
)

TMP_GOLD_ROOT = (
    TMP_ROOT
    / "gold"
    / "fii-master"
)


SILVER_PATTERNS = {
    "b3": re.compile(
        r"^silver/b3/"
        r"year=(\d{4})/"
        r"month=(\d{2})/"
        r"day=(\d{2})/"
        r"b3_trades\.parquet$"
    ),
    "cvm": re.compile(
        r"^silver/cvm/"
        r"year=(\d{4})/"
        r"month=(\d{2})/"
        r"day=(\d{2})/"
        r"cvm_fund_classes\.parquet$"
    ),
    "b3-instruments": re.compile(
        r"^silver/b3-instruments/"
        r"year=(\d{4})/"
        r"month=(\d{2})/"
        r"day=(\d{2})/"
        r"b3_instruments\.parquet$"
    ),
}


SILVER_PREFIXES = {
    "b3": "silver/b3/",
    "cvm": "silver/cvm/",
    "b3-instruments": (
        "silver/b3-instruments/"
    ),
}


REQUIRED_EVENT_INPUTS = {
    "b3_trades": "b3",
    "cvm": "cvm",
    "b3_instruments": (
        "b3-instruments"
    ),
}


def parse_partition_date(
    key: str,
    source: str,
) -> date | None:
    pattern = SILVER_PATTERNS[
        source
    ]

    match = pattern.fullmatch(
        key
    )

    if match is None:
        return None

    year, month, day = (
        int(
            value
        )
        for value
        in match.groups()
    )

    return date(
        year,
        month,
        day,
    )


def list_partitioned_objects(
    bucket: str,
    source: str,
) -> list[
    tuple[
        date,
        str,
    ]
]:
    s3 = boto3.client(
        "s3"
    )

    paginator = (
        s3.get_paginator(
            "list_objects_v2"
        )
    )

    objects: list[
        tuple[
            date,
            str,
        ]
    ] = []

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=(
            SILVER_PREFIXES[
                source
            ]
        ),
    ):
        for item in page.get(
            "Contents",
            [],
        ):
            key = item[
                "Key"
            ]

            partition_date = (
                parse_partition_date(
                    key=key,
                    source=source,
                )
            )

            if (
                partition_date
                is None
            ):
                continue

            objects.append(
                (
                    partition_date,
                    key,
                )
            )

    return sorted(
        objects,
        key=lambda item: (
            item[0]
        ),
    )


def find_latest_object(
    bucket: str,
    source: str,
    max_date: (
        date
        | None
    ) = None,
) -> tuple[
    date,
    str,
]:
    objects = (
        list_partitioned_objects(
            bucket=bucket,
            source=source,
        )
    )

    if max_date is not None:
        objects = [
            item
            for item
            in objects
            if item[0]
            <= max_date
        ]

    if not objects:
        constraint = (
            f" <= "
            f"{max_date.isoformat()}"
            if max_date
            is not None
            else ""
        )

        raise FileNotFoundError(
            "No valid Silver object "
            f"found for {source}"
            f"{constraint}."
        )

    return objects[
        -1
    ]


def validate_object_exists(
    bucket: str,
    key: str,
) -> None:
    boto3.client(
        "s3"
    ).head_object(
        Bucket=bucket,
        Key=key,
    )


def parse_event_reference_date(
    value: str,
    input_name: str,
) -> date:
    try:
        return date.fromisoformat(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Invalid reference_date for "
            f"{input_name}: {value}. "
            "Expected YYYY-MM-DD."
        ) from exc


def resolve_explicit_inputs(
    bucket: str,
    event: dict,
) -> dict | None:
    inputs = event.get(
        "inputs"
    )

    if inputs is None:
        return None

    if not isinstance(
        inputs,
        dict,
    ):
        raise ValueError(
            "Event field 'inputs' "
            "must be an object."
        )

    resolved: dict[
        str,
        dict,
    ] = {}

    for (
        input_name,
        source,
    ) in (
        REQUIRED_EVENT_INPUTS.items()
    ):
        input_data = inputs.get(
            input_name
        )

        if not isinstance(
            input_data,
            dict,
        ):
            raise ValueError(
                "Missing or invalid Gold "
                f"input: {input_name}."
            )

        key = input_data.get(
            "key"
        )

        reference_date_value = (
            input_data.get(
                "reference_date"
            )
        )

        if not key:
            raise ValueError(
                "Missing key for Gold "
                f"input: {input_name}."
            )

        if not reference_date_value:
            raise ValueError(
                "Missing reference_date "
                "for Gold input: "
                f"{input_name}."
            )

        partition_date = (
            parse_partition_date(
                key=key,
                source=source,
            )
        )

        if partition_date is None:
            raise ValueError(
                "Invalid Silver key for "
                f"{input_name}: {key}"
            )

        reference_date = (
            parse_event_reference_date(
                value=(
                    reference_date_value
                ),
                input_name=(
                    input_name
                ),
            )
        )

        if (
            partition_date
            != reference_date
        ):
            raise ValueError(
                "Gold input reference_date "
                "does not match its Silver "
                "partition. "
                f"input={input_name} | "
                "reference_date="
                f"{reference_date} | "
                "partition_date="
                f"{partition_date}"
            )

        validate_object_exists(
            bucket=bucket,
            key=key,
        )

        resolved[
            input_name
        ] = {
            "source": (
                source
            ),
            "reference_date": (
                reference_date
            ),
            "key": key,
        }

    instruments_date = (
        resolved[
            "b3_instruments"
        ][
            "reference_date"
        ]
    )

    cvm_date = (
        resolved[
            "cvm"
        ][
            "reference_date"
        ]
    )

    trades_date = (
        resolved[
            "b3_trades"
        ][
            "reference_date"
        ]
    )

    if (
        cvm_date
        > instruments_date
    ):
        raise ValueError(
            "CVM Silver reference_date "
            "cannot be newer than "
            "B3 Instruments. "
            f"cvm={cvm_date} | "
            "instruments="
            f"{instruments_date}"
        )

    if (
        trades_date
        > instruments_date
    ):
        raise ValueError(
            "B3 Trades reference_date "
            "cannot be newer than "
            "B3 Instruments. "
            f"trades={trades_date} | "
            "instruments="
            f"{instruments_date}"
        )

    return resolved


def download_object(
    bucket: str,
    key: str,
    local_path: Path,
) -> None:
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    boto3.client(
        "s3"
    ).download_file(
        bucket,
        key,
        str(
            local_path
        ),
    )


def build_gold_s3_key(
    reference_date: date,
) -> str:
    return (
        "gold/fii-master/"
        f"year="
        f"{reference_date.year:04d}/"
        f"month="
        f"{reference_date.month:02d}/"
        f"day="
        f"{reference_date.day:02d}/"
        "fii_master.parquet"
    )


def resolve_execution_run_date(
    event: dict,
) -> str:
    """
    Resolve o run_date operacional usado
    pelo execution state.

    Quando o evento contém run_date, ele
    precisa estar no formato YYYY-MM-DD.

    Para compatibilidade com invocações
    manuais antigas sem run_date, usa a
    data atual em America/Sao_Paulo.
    """

    run_date_value = event.get(
        "run_date"
    )

    if run_date_value is None:
        return (
            datetime.now(
                PLATFORM_TIMEZONE
            )
            .date()
            .isoformat()
        )

    normalized = str(
        run_date_value
    ).strip()

    try:
        parsed = (
            date.fromisoformat(
                normalized
            )
        )

    except ValueError as exc:
        raise ValueError(
            "Invalid Gold run_date: "
            f"{run_date_value}. "
            "Expected YYYY-MM-DD."
        ) from exc

    return (
        parsed.isoformat()
    )


def resolve_execution_trigger(
    event: dict,
) -> str:
    """
    Resolve a origem lógica da execução.

    Exemplos esperados:

    NORMAL
    RECOVERY
    MANUAL

    O valor é aberto para permitir novas
    origens sem alterar o handler.
    """

    trigger = event.get(
        "trigger",
        "NORMAL",
    )

    normalized = str(
        trigger
    ).strip().upper()

    if not normalized:
        return "NORMAL"

    return normalized


def get_request_id(
    context,
) -> str | None:
    """
    Obtém aws_request_id quando disponível.

    Mantém compatibilidade com testes e
    execuções locais sem Lambda context.
    """

    if context is None:
        return None

    return getattr(
        context,
        "aws_request_id",
        None,
    )


def run_fii_master_gold(
    bucket: str,
    explicit_inputs: (
        dict
        | None
    ) = None,
    run_date: (
        str
        | None
    ) = None,
) -> dict:
    print(
        "======================================"
    )

    print(
        "FII MASTER GOLD | AWS"
    )

    print(
        "======================================"
    )

    if explicit_inputs is None:
        print(
            "Modo de seleção: latest "
            "compatible Silvers"
        )

        (
            instruments_date,
            instruments_key,
        ) = find_latest_object(
            bucket=bucket,
            source=(
                "b3-instruments"
            ),
        )

        (
            cvm_date,
            cvm_key,
        ) = find_latest_object(
            bucket=bucket,
            source="cvm",
            max_date=(
                instruments_date
            ),
        )

        (
            trades_date,
            trades_key,
        ) = find_latest_object(
            bucket=bucket,
            source="b3",
            max_date=(
                instruments_date
            ),
        )

    else:
        print(
            "Modo de seleção: explicit "
            "Silver inputs"
        )

        instruments_date = (
            explicit_inputs[
                "b3_instruments"
            ][
                "reference_date"
            ]
        )

        instruments_key = (
            explicit_inputs[
                "b3_instruments"
            ][
                "key"
            ]
        )

        cvm_date = (
            explicit_inputs[
                "cvm"
            ][
                "reference_date"
            ]
        )

        cvm_key = (
            explicit_inputs[
                "cvm"
            ][
                "key"
            ]
        )

        trades_date = (
            explicit_inputs[
                "b3_trades"
            ][
                "reference_date"
            ]
        )

        trades_key = (
            explicit_inputs[
                "b3_trades"
            ][
                "key"
            ]
        )

    print(
        "B3 Instruments Silver selecionado | "
        "reference_date="
        f"{instruments_date.isoformat()} | "
        f"key={instruments_key}"
    )

    print(
        "CVM Silver selecionado | "
        "reference_date="
        f"{cvm_date.isoformat()} | "
        f"key={cvm_key}"
    )

    print(
        "B3 Trades Silver selecionado | "
        "reference_date="
        f"{trades_date.isoformat()} | "
        f"key={trades_key}"
    )

    download_object(
        bucket=bucket,
        key=cvm_key,
        local_path=TMP_CVM,
    )

    download_object(
        bucket=bucket,
        key=instruments_key,
        local_path=TMP_INSTRUMENTS,
    )

    download_object(
        bucket=bucket,
        key=trades_key,
        local_path=TMP_TRADES,
    )

    args = Namespace(
        cvm=TMP_CVM,
        instruments=(
            TMP_INSTRUMENTS
        ),
        trades=TMP_TRADES,
        output_root=(
            TMP_GOLD_ROOT
        ),
        min_resolution_rate=(
            DEFAULT_MIN_RESOLUTION_RATE
        ),
    )

    output_path = run_pipeline(
        args
    )

    gold_dataframe = (
        pd.read_parquet(
            output_path
        )
    )

    gold_reference_values = (
        gold_dataframe[
            "reference_date"
        ]
        .dropna()
    )

    if (
        gold_reference_values.empty
    ):
        raise RuntimeError(
            "Gold output has no "
            "reference_date."
        )

    gold_reference_date = (
        pd.Timestamp(
            gold_reference_values.iloc[
                0
            ]
        )
        .date()
    )

    if (
        gold_reference_date
        != instruments_date
    ):
        raise RuntimeError(
            "Gold reference_date does not "
            "match the selected "
            "B3 Instruments partition. "
            "gold="
            f"{gold_reference_date} | "
            "instruments="
            f"{instruments_date}"
        )

    gold_key = (
        build_gold_s3_key(
            gold_reference_date
        )
    )

    upload_file(
        local_path=output_path,
        bucket_name=bucket,
        s3_key=gold_key,
        force=False,
    )

    print()

    print(
        "Gold FII Master publicado | "
        f"s3://{bucket}/{gold_key}"
    )

    return {
        "status": "success",
        "run_date": run_date,
        "reference_date": (
            gold_reference_date
            .isoformat()
        ),
        "records": int(
            len(
                gold_dataframe
            )
        ),
        "inputs": {
            "cvm": {
                "reference_date": (
                    cvm_date
                    .isoformat()
                ),
                "key": cvm_key,
            },
            "b3_instruments": {
                "reference_date": (
                    instruments_date
                    .isoformat()
                ),
                "key": (
                    instruments_key
                ),
            },
            "b3_trades": {
                "reference_date": (
                    trades_date
                    .isoformat()
                ),
                "key": trades_key,
            },
        },
        "gold_key": gold_key,
        "gold_uri": (
            f"s3://{bucket}/"
            f"{gold_key}"
        ),
    }


def lambda_handler(
    event,
    context,
):
    bucket = os.environ.get(
        "FII_DATA_LAKE_BUCKET"
    )

    if not bucket:
        raise RuntimeError(
            "Environment variable "
            "FII_DATA_LAKE_BUCKET "
            "is required."
        )

    event = event or {}

    run_date = (
        resolve_execution_run_date(
            event
        )
    )

    trigger = (
        resolve_execution_trigger(
            event
        )
    )

    request_id = (
        get_request_id(
            context
        )
    )

    started_details = {
        "request_id": request_id,
        "has_explicit_inputs": (
            event.get(
                "inputs"
            )
            is not None
        ),
    }

    print(
        "Gold execution state | "
        f"run_date={run_date} | "
        f"trigger={trigger} | "
        "status=STARTED"
    )

    mark_execution_started(
        bucket=bucket,
        run_date=run_date,
        trigger=trigger,
        details=(
            started_details
        ),
    )

    try:
        explicit_inputs = (
            resolve_explicit_inputs(
                bucket=bucket,
                event=event,
            )
        )

        result = (
            run_fii_master_gold(
                bucket=bucket,
                explicit_inputs=(
                    explicit_inputs
                ),
                run_date=run_date,
            )
        )

        success_details = {
            "request_id": (
                request_id
            ),
            "reference_date": (
                result[
                    "reference_date"
                ]
            ),
            "records": (
                result[
                    "records"
                ]
            ),
        }

        mark_execution_succeeded(
            bucket=bucket,
            run_date=run_date,
            trigger=trigger,
            gold_key=(
                result[
                    "gold_key"
                ]
            ),
            details=(
                success_details
            ),
        )

        print(
            "Gold execution state | "
            f"run_date={run_date} | "
            f"trigger={trigger} | "
            "status=SUCCEEDED"
        )

        return result

    except Exception as exc:
        print(
            "Gold execution state | "
            f"run_date={run_date} | "
            f"trigger={trigger} | "
            "status=FAILED | "
            f"error_type="
            f"{type(exc).__name__} | "
            f"error={exc}"
        )

        failure_details = {
            "request_id": (
                request_id
            ),
        }

        try:
            mark_execution_failed(
                bucket=bucket,
                run_date=run_date,
                trigger=trigger,
                error_type=(
                    type(exc).__name__
                ),
                error_message=(
                    str(exc)
                ),
                details=(
                    failure_details
                ),
            )

        except Exception as state_exc:
            print(
                "WARNING | Failed to persist "
                "Gold FAILED state | "
                f"run_date={run_date} | "
                f"error_type="
                f"{type(state_exc).__name__} | "
                f"error={state_exc}"
            )

        raise