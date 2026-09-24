from __future__ import annotations

from typing import Any

import pytest

from src.orchestration import (
    gold_recovery_executor,
)


BUCKET = (
    "fii-data-ai-platform-dev-"
    "datalake-625685670804"
)

GOLD_FUNCTION_NAME = (
    "fii-data-ai-platform-dev-"
    "fii-master-gold"
)

RAW_TO_SILVER_FUNCTIONS = {
    "b3": (
        "fii-data-ai-platform-dev-"
        "b3-raw-to-silver"
    ),
    "cvm": (
        "fii-data-ai-platform-dev-"
        "cvm-raw-to-silver"
    ),
    "b3_instruments": (
        "fii-data-ai-platform-dev-"
        "b3-instruments-raw-to-silver"
    ),
}


def build_gold_retry_assessment() -> dict[str, Any]:
    return {
        "status": (
            "GOLD_RETRY_REQUIRED"
        ),
        "action": "RETRY_GOLD",
        "run_date": "2026-09-22",
        "gold_payload": {
            "run_date": "2026-09-22",
            "inputs": {
                "b3_trades": {
                    "reference_date": (
                        "2026-09-21"
                    ),
                    "key": (
                        "silver/b3/"
                        "year=2026/"
                        "month=09/"
                        "day=21/"
                        "b3_trades.parquet"
                    ),
                },
                "cvm": {
                    "reference_date": (
                        "2026-09-22"
                    ),
                    "key": (
                        "silver/cvm/"
                        "year=2026/"
                        "month=09/"
                        "day=22/"
                        "cvm_fund_classes.parquet"
                    ),
                },
                "b3_instruments": {
                    "reference_date": (
                        "2026-09-22"
                    ),
                    "key": (
                        "silver/"
                        "b3-instruments/"
                        "year=2026/"
                        "month=09/"
                        "day=22/"
                        "b3_instruments.parquet"
                    ),
                },
            },
        },
    }


def build_raw_rebuild_assessment() -> dict[str, Any]:
    return {
        "status": (
            "RAW_REBUILD_REQUIRED"
        ),
        "action": (
            "REBUILD_SILVER_FROM_RAW"
        ),
        "run_date": "2026-09-22",
        "rebuild_sources": [
            "cvm",
        ],
        "source_states": {
            "b3": {
                "source": "b3",
                "raw_objects": [
                    {
                        "key": (
                            "raw/b3/"
                            "year=2026/"
                            "month=09/"
                            "day=21/"
                            "b3_download_"
                            "20260921.zip"
                        )
                    }
                ],
                "silver_objects": [],
            },
            "cvm": {
                "source": "cvm",
                "raw_objects": [
                    {
                        "key": (
                            "raw/cvm/"
                            "year=2026/"
                            "month=09/"
                            "day=22/"
                            "registro_"
                            "fundo_classe.zip"
                        )
                    }
                ],
                "silver_objects": [],
            },
            "b3_instruments": {
                "source": (
                    "b3_instruments"
                ),
                "raw_objects": [
                    {
                        "key": (
                            "raw/"
                            "b3-instruments/"
                            "year=2026/"
                            "month=09/"
                            "day=22/"
                            "pesquisa-pregao.zip"
                        )
                    }
                ],
                "silver_objects": [],
            },
        },
    }


def test_invoke_lambda_async(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    class FakeLambdaClient:
        def invoke(
            self,
            **kwargs,
        ):
            calls.append(
                kwargs
            )

            return {
                "StatusCode": 202,
            }

    monkeypatch.setattr(
        gold_recovery_executor.boto3,
        "client",
        lambda service: (
            FakeLambdaClient()
        ),
    )

    payload = {
        "run_date": "2026-09-22",
    }

    result = (
        gold_recovery_executor
        .invoke_lambda_async(
            function_name=(
                GOLD_FUNCTION_NAME
            ),
            payload=payload,
        )
    )

    assert result == {
        "function_name": (
            GOLD_FUNCTION_NAME
        ),
        "invoke_status_code": 202,
        "payload": payload,
    }

    assert len(
        calls
    ) == 1

    assert calls[0][
        "FunctionName"
    ] == GOLD_FUNCTION_NAME

    assert calls[0][
        "InvocationType"
    ] == "Event"


def test_invoke_lambda_async_rejects_non_202(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLambdaClient:
        def invoke(
            self,
            **kwargs,
        ):
            return {
                "StatusCode": 200,
            }

    monkeypatch.setattr(
        gold_recovery_executor.boto3,
        "client",
        lambda service: (
            FakeLambdaClient()
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Unexpected Lambda "
            "async invoke response"
        ),
    ):
        (
            gold_recovery_executor
            .invoke_lambda_async(
                function_name=(
                    GOLD_FUNCTION_NAME
                ),
                payload={
                    "run_date": (
                        "2026-09-22"
                    )
                },
            )
        )


def test_execute_gold_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = (
        build_gold_retry_assessment()
    )

    monkeypatch.setattr(
        gold_recovery_executor,
        "invoke_lambda_async",
        lambda **kwargs: {
            "function_name": (
                kwargs[
                    "function_name"
                ]
            ),
            "invoke_status_code": 202,
            "payload": (
                kwargs[
                    "payload"
                ]
            ),
        },
    )

    result = (
        gold_recovery_executor
        .execute_gold_retry(
            assessment=assessment,
            gold_function_name=(
                GOLD_FUNCTION_NAME
            ),
        )
    )

    assert result[
        "status"
    ] == "DISPATCHED"

    assert result[
        "action"
    ] == "RETRY_GOLD"

    assert result[
        "run_date"
    ] == "2026-09-22"

    assert result[
        "invoke_status_code"
    ] == 202

    assert result[
        "payload"
    ] == {
        **assessment[
            "gold_payload"
        ],
        "trigger": "RECOVERY",
    }


def test_execute_gold_retry_requires_correct_status() -> None:
    assessment = (
        build_gold_retry_assessment()
    )

    assessment[
        "status"
    ] = "COMPLETE"

    with pytest.raises(
        ValueError,
        match=(
            "Gold retry requires "
            "status="
        ),
    ):
        (
            gold_recovery_executor
            .execute_gold_retry(
                assessment=assessment,
                gold_function_name=(
                    GOLD_FUNCTION_NAME
                ),
            )
        )


def test_build_gold_recovery_payload_adds_recovery_trigger() -> None:
    assessment = (
        build_gold_retry_assessment()
    )

    result = (
        gold_recovery_executor
        .build_gold_recovery_payload(
            assessment=assessment
        )
    )

    assert result == {
        **assessment[
            "gold_payload"
        ],
        "trigger": "RECOVERY",
    }



def test_execute_gold_retry_requires_correct_action() -> None:
    assessment = (
        build_gold_retry_assessment()
    )

    assessment[
        "action"
    ] = "NO_ACTION"

    with pytest.raises(
        ValueError,
        match=(
            "Gold retry requires "
            "action=RETRY_GOLD"
        ),
    ):
        (
            gold_recovery_executor
            .execute_gold_retry(
                assessment=assessment,
                gold_function_name=(
                    GOLD_FUNCTION_NAME
                ),
            )
        )


def test_execute_gold_retry_requires_payload() -> None:
    assessment = (
        build_gold_retry_assessment()
    )

    assessment.pop(
        "gold_payload"
    )

    with pytest.raises(
        ValueError,
        match=(
            "must contain gold_payload"
        ),
    ):
        (
            gold_recovery_executor
            .execute_gold_retry(
                assessment=assessment,
                gold_function_name=(
                    GOLD_FUNCTION_NAME
                ),
            )
        )


def test_execute_gold_retry_validates_run_date() -> None:
    assessment = (
        build_gold_retry_assessment()
    )

    assessment[
        "gold_payload"
    ][
        "run_date"
    ] = "2026-09-21"

    with pytest.raises(
        ValueError,
        match=(
            "Gold retry run_date "
            "mismatch"
        ),
    ):
        (
            gold_recovery_executor
            .execute_gold_retry(
                assessment=assessment,
                gold_function_name=(
                    GOLD_FUNCTION_NAME
                ),
            )
        )


def test_build_raw_to_silver_payload() -> None:
    assessment = (
        build_raw_rebuild_assessment()
    )

    assessment[
        "bucket"
    ] = BUCKET

    result = (
        gold_recovery_executor
        .build_raw_to_silver_payload(
            assessment=assessment,
            source="cvm",
        )
    )

    assert result == {
        "bucket": BUCKET,
        "key": (
            "raw/cvm/"
            "year=2026/"
            "month=09/"
            "day=22/"
            "registro_fundo_classe.zip"
        ),
    }


def test_build_raw_to_silver_payload_requires_exactly_one_raw() -> None:
    assessment = (
        build_raw_rebuild_assessment()
    )

    assessment[
        "bucket"
    ] = BUCKET

    assessment[
        "source_states"
    ][
        "cvm"
    ][
        "raw_objects"
    ] = []

    with pytest.raises(
        ValueError,
        match=(
            "requires exactly "
            "one RAW object"
        ),
    ):
        (
            gold_recovery_executor
            .build_raw_to_silver_payload(
                assessment=assessment,
                source="cvm",
            )
        )


def test_build_raw_to_silver_payload_requires_bucket() -> None:
    assessment = (
        build_raw_rebuild_assessment()
    )

    with pytest.raises(
        ValueError,
        match=(
            "must contain bucket"
        ),
    ):
        (
            gold_recovery_executor
            .build_raw_to_silver_payload(
                assessment=assessment,
                source="cvm",
            )
        )


def test_execute_raw_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = (
        build_raw_rebuild_assessment()
    )

    assessment[
        "bucket"
    ] = BUCKET

    calls = []

    def fake_invoke_lambda_async(
        *,
        function_name: str,
        payload: dict,
    ) -> dict:
        calls.append(
            {
                "function_name": (
                    function_name
                ),
                "payload": payload,
            }
        )

        return {
            "function_name": (
                function_name
            ),
            "invoke_status_code": 202,
            "payload": payload,
        }

    monkeypatch.setattr(
        gold_recovery_executor,
        "invoke_lambda_async",
        fake_invoke_lambda_async,
    )

    result = (
        gold_recovery_executor
        .execute_raw_rebuild(
            assessment=assessment,
            raw_to_silver_functions=(
                RAW_TO_SILVER_FUNCTIONS
            ),
        )
    )

    assert result[
        "status"
    ] == "DISPATCHED"

    assert result[
        "action"
    ] == (
        "REBUILD_SILVER_FROM_RAW"
    )

    assert result[
        "run_date"
    ] == "2026-09-22"

    assert len(
        result[
            "dispatches"
        ]
    ) == 1

    assert len(
        calls
    ) == 1

    assert calls[0][
        "function_name"
    ] == (
        RAW_TO_SILVER_FUNCTIONS[
            "cvm"
        ]
    )


def test_execute_raw_rebuild_requires_function_mapping() -> None:
    assessment = (
        build_raw_rebuild_assessment()
    )

    assessment[
        "bucket"
    ] = BUCKET

    with pytest.raises(
        ValueError,
        match=(
            "Missing RAW->Silver "
            "function mapping"
        ),
    ):
        (
            gold_recovery_executor
            .execute_raw_rebuild(
                assessment=assessment,
                raw_to_silver_functions={
                    "b3": (
                        RAW_TO_SILVER_FUNCTIONS[
                            "b3"
                        ]
                    )
                },
            )
        )


def test_execute_assessment_skips_no_action() -> None:
    result = (
        gold_recovery_executor
        .execute_assessment(
            assessment={
                "status": "COMPLETE",
                "action": "NO_ACTION",
                "run_date": (
                    "2026-09-22"
                ),
            },
            gold_function_name=(
                GOLD_FUNCTION_NAME
            ),
            raw_to_silver_functions=(
                RAW_TO_SILVER_FUNCTIONS
            ),
            bucket=BUCKET,
        )
    )

    assert result == {
        "status": "SKIPPED",
        "action": "NO_ACTION",
        "run_date": "2026-09-22",
        "reason": (
            "NO_ACTION_REQUIRED"
        ),
    }


def test_execute_assessment_waits_for_completion() -> None:
    result = (
        gold_recovery_executor
        .execute_assessment(
            assessment={
                "status": "IN_PROGRESS",
                "action": (
                    "WAIT_FOR_COMPLETION"
                ),
                "run_date": (
                    "2026-09-22"
                ),
                "reason": (
                    "STARTED_EXECUTION_ACTIVE"
                ),
            },
            gold_function_name=(
                GOLD_FUNCTION_NAME
            ),
            raw_to_silver_functions=(
                RAW_TO_SILVER_FUNCTIONS
            ),
            bucket=BUCKET,
        )
    )

    assert result == {
        "status": "WAITING",
        "action": (
            "WAIT_FOR_COMPLETION"
        ),
        "run_date": "2026-09-22",
        "reason": (
            "STARTED_EXECUTION_ACTIVE"
        ),
    }



def test_execute_assessment_blocks_manual_investigation() -> None:
    result = (
        gold_recovery_executor
        .execute_assessment(
            assessment={
                "status": (
                    "RECOVERY_BLOCKED"
                ),
                "action": (
                    "ALERT_AND_INVESTIGATE"
                ),
                "run_date": (
                    "2026-09-22"
                ),
                "reason": (
                    "RAW_UNAVAILABLE"
                ),
            },
            gold_function_name=(
                GOLD_FUNCTION_NAME
            ),
            raw_to_silver_functions=(
                RAW_TO_SILVER_FUNCTIONS
            ),
            bucket=BUCKET,
        )
    )

    assert result == {
        "status": "BLOCKED",
        "action": (
            "ALERT_AND_INVESTIGATE"
        ),
        "run_date": "2026-09-22",
        "reason": "RAW_UNAVAILABLE",
    }


def test_execute_assessment_rejects_unknown_action() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Unsupported "
            "recovery action"
        ),
    ):
        (
            gold_recovery_executor
            .execute_assessment(
                assessment={
                    "status": "WHATEVER",
                    "action": "DELETE_WORLD",
                    "run_date": (
                        "2026-09-22"
                    ),
                },
                gold_function_name=(
                    GOLD_FUNCTION_NAME
                ),
                raw_to_silver_functions=(
                    RAW_TO_SILVER_FUNCTIONS
                ),
                bucket=BUCKET,
            )
        )


def test_execute_recovery_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery_plan = {
        "status": (
            "RECOVERY_REQUIRED"
        ),
        "assessments": [
            {
                "status": "COMPLETE",
                "action": "NO_ACTION",
                "run_date": (
                    "2026-09-21"
                ),
            },
            {
                "status": (
                    "GOLD_RETRY_REQUIRED"
                ),
                "action": "RETRY_GOLD",
                "run_date": (
                    "2026-09-22"
                ),
            },
            {
                "status": (
                    "RECOVERY_BLOCKED"
                ),
                "action": (
                    "ALERT_AND_INVESTIGATE"
                ),
                "run_date": (
                    "2026-09-23"
                ),
            },
        ],
    }

    fake_results = {
        "2026-09-21": {
            "status": "SKIPPED",
            "action": "NO_ACTION",
            "run_date": (
                "2026-09-21"
            ),
        },
        "2026-09-22": {
            "status": "DISPATCHED",
            "action": "RETRY_GOLD",
            "run_date": (
                "2026-09-22"
            ),
        },
        "2026-09-23": {
            "status": "BLOCKED",
            "action": (
                "ALERT_AND_INVESTIGATE"
            ),
            "run_date": (
                "2026-09-23"
            ),
        },
    }

    monkeypatch.setattr(
        gold_recovery_executor,
        "execute_assessment",
        (
            lambda *,
            assessment,
            gold_function_name,
            raw_to_silver_functions,
            bucket: (
                fake_results[
                    assessment[
                        "run_date"
                    ]
                ]
            )
        ),
    )

    result = (
        gold_recovery_executor
        .execute_recovery_plan(
            recovery_plan=(
                recovery_plan
            ),
            gold_function_name=(
                GOLD_FUNCTION_NAME
            ),
            raw_to_silver_functions=(
                RAW_TO_SILVER_FUNCTIONS
            ),
            bucket=BUCKET,
        )
    )

    assert result[
        "status"
    ] == "EXECUTED_WITH_BLOCKS"

    assert result[
        "total_results"
    ] == 3

    assert result[
        "dispatched"
    ] == 1

    assert result[
        "blocked"
    ] == 1

    assert result[
        "skipped"
    ] == 1


def test_execute_recovery_plan_without_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery_plan = {
        "assessments": [
            {
                "status": "COMPLETE",
                "action": "NO_ACTION",
                "run_date": (
                    "2026-09-21"
                ),
            },
            {
                "status": (
                    "GOLD_RETRY_REQUIRED"
                ),
                "action": "RETRY_GOLD",
                "run_date": (
                    "2026-09-22"
                ),
            },
        ]
    }

    fake_results = {
        "2026-09-21": {
            "status": "SKIPPED",
            "action": "NO_ACTION",
            "run_date": (
                "2026-09-21"
            ),
        },
        "2026-09-22": {
            "status": "DISPATCHED",
            "action": "RETRY_GOLD",
            "run_date": (
                "2026-09-22"
            ),
        },
    }

    monkeypatch.setattr(
        gold_recovery_executor,
        "execute_assessment",
        (
            lambda *,
            assessment,
            gold_function_name,
            raw_to_silver_functions,
            bucket: (
                fake_results[
                    assessment[
                        "run_date"
                    ]
                ]
            )
        ),
    )


def test_execute_recovery_plan_with_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery_plan = {
        "assessments": [
            {
                "status": (
                    "IN_PROGRESS"
                ),
                "action": (
                    "WAIT_FOR_COMPLETION"
                ),
                "run_date": (
                    "2026-09-22"
                ),
            }
        ]
    }

    monkeypatch.setattr(
        gold_recovery_executor,
        "execute_assessment",
        lambda **kwargs: {
            "status": "WAITING",
            "action": (
                "WAIT_FOR_COMPLETION"
            ),
            "run_date": (
                "2026-09-22"
            ),
        },
    )

    result = (
        gold_recovery_executor
        .execute_recovery_plan(
            recovery_plan=(
                recovery_plan
            ),
            gold_function_name=(
                GOLD_FUNCTION_NAME
            ),
            raw_to_silver_functions=(
                RAW_TO_SILVER_FUNCTIONS
            ),
            bucket=BUCKET,
        )
    )

    assert result[
        "status"
    ] == (
        "EXECUTED_WITH_WAITING"
    )

    assert result[
        "total_results"
    ] == 1

    assert result[
        "dispatched"
    ] == 0

    assert result[
        "waiting"
    ] == 1

    assert result[
        "blocked"
    ] == 0

    assert result[
        "skipped"
    ] == 0

    assert result[
        "results"
    ] == [
        {
            "status": "WAITING",
            "action": (
                "WAIT_FOR_COMPLETION"
            ),
            "run_date": (
                "2026-09-22"
            ),
        }
    ]


def test_execute_recovery_plan_requires_assessments() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Recovery plan must contain "
            "an assessments list"
        ),
    ):
        (
            gold_recovery_executor
            .execute_recovery_plan(
                recovery_plan={},
                gold_function_name=(
                    GOLD_FUNCTION_NAME
                ),
                raw_to_silver_functions=(
                    RAW_TO_SILVER_FUNCTIONS
                ),
                bucket=BUCKET,
            )
        )