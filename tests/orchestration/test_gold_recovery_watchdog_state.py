from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from src.orchestration import (
    gold_recovery_watchdog_state,
)


BUCKET = "fii-data-ai-platform-dev-datalake-test"

WATCHDOG_DATE = date(
    2026,
    9,
    25,
)

EXPECTED_STATE_KEY = (
    "control/gold-recovery-watchdog/"
    "watchdog_date=2026-09-25/"
    "state.json"
)

FIXED_TIMESTAMP = (
    "2026-09-25T13:00:00+00:00"
)


class FakeS3Client:
    """
    Implementação mínima de S3 em memória
    necessária para os testes do watchdog.
    """

    def __init__(self) -> None:
        self.objects: dict[
            tuple[str, str],
            bytes,
        ] = {}

        self.put_calls: list[
            dict
        ] = []

        self.get_calls: list[
            dict
        ] = []

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
    ) -> dict:
        self.put_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "Body": Body,
                "ContentType": ContentType,
            }
        )

        self.objects[
            (
                Bucket,
                Key,
            )
        ] = Body

        return {
            "ETag": '"fake-etag"',
        }

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> dict:
        self.get_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
            }
        )

        object_key = (
            Bucket,
            Key,
        )

        if (
            object_key
            not in self.objects
        ):
            raise ClientError(
                {
                    "Error": {
                        "Code": "NoSuchKey",
                        "Message": (
                            "The specified key "
                            "does not exist."
                        ),
                    }
                },
                "GetObject",
            )

        return {
            "Body": BytesIO(
                self.objects[
                    object_key
                ]
            )
        }


def install_fake_s3(
    monkeypatch: pytest.MonkeyPatch,
) -> FakeS3Client:
    """
    Instala um cliente S3 fake no módulo
    sendo testado.
    """

    fake_s3 = FakeS3Client()

    monkeypatch.setattr(
        gold_recovery_watchdog_state.boto3,
        "client",
        lambda service_name: fake_s3,
    )

    return fake_s3


def test_normalize_watchdog_date_from_date(
) -> None:
    result = (
        gold_recovery_watchdog_state
        .normalize_watchdog_date(
            WATCHDOG_DATE
        )
    )

    assert result == "2026-09-25"


def test_normalize_watchdog_date_from_iso_string(
) -> None:
    result = (
        gold_recovery_watchdog_state
        .normalize_watchdog_date(
            "2026-09-25"
        )
    )

    assert result == "2026-09-25"


def test_normalize_watchdog_date_rejects_invalid_string(
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid watchdog date",
    ):
        (
            gold_recovery_watchdog_state
            .normalize_watchdog_date(
                "25-09-2026"
            )
        )


def test_normalize_watchdog_date_rejects_invalid_type(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "watchdog_date must be "
            "date or ISO string"
        ),
    ):
        (
            gold_recovery_watchdog_state
            .normalize_watchdog_date(
                20260925
            )
        )


def test_build_watchdog_state_key(
) -> None:
    result = (
        gold_recovery_watchdog_state
        .build_watchdog_state_key(
            watchdog_date=(
                WATCHDOG_DATE
            )
        )
    )

    assert result == EXPECTED_STATE_KEY


@pytest.mark.parametrize(
    "status",
    [
        "OPEN",
        "CLOSED_SUCCESS",
        "FINAL_RECOVERY_DISPATCHED",
        "CLOSED_FAILED",
        "open",
        "closed_success",
    ],
)
def test_validate_status_accepts_supported_values(
    status: str,
) -> None:
    result = (
        gold_recovery_watchdog_state
        .validate_status(
            status
        )
    )

    assert (
        result
        == status.strip().upper()
    )


def test_validate_status_rejects_unknown_value(
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid watchdog status",
    ):
        (
            gold_recovery_watchdog_state
            .validate_status(
                "SOMETHING_ELSE"
            )
        )


def test_read_watchdog_state_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_s3 = install_fake_s3(
        monkeypatch
    )

    result = (
        gold_recovery_watchdog_state
        .read_watchdog_state(
            bucket=BUCKET,
            watchdog_date=(
                WATCHDOG_DATE
            ),
        )
    )

    assert result is None

    assert fake_s3.get_calls == [
        {
            "Bucket": BUCKET,
            "Key": EXPECTED_STATE_KEY,
        }
    ]


def test_write_watchdog_state_persists_open_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_s3 = install_fake_s3(
        monkeypatch
    )

    monkeypatch.setattr(
        gold_recovery_watchdog_state,
        "utc_now_iso",
        lambda: FIXED_TIMESTAMP,
    )

    result = (
        gold_recovery_watchdog_state
        .write_watchdog_state(
            bucket=BUCKET,
            watchdog_date=(
                WATCHDOG_DATE
            ),
            status="OPEN",
            attempt=1,
            max_attempts=3,
            final_attempt=False,
            check_hour=10,
            outcome=(
                "RECOVERY_DISPATCHED"
            ),
            details={
                "action": (
                    "REBUILD_SILVER_FROM_RAW"
                ),
                "source": "b3",
            },
        )
    )

    assert (
        result["state_key"]
        == EXPECTED_STATE_KEY
    )

    assert (
        result["state_uri"]
        == (
            f"s3://{BUCKET}/"
            f"{EXPECTED_STATE_KEY}"
        )
    )

    payload = result[
        "payload"
    ]

    assert payload == {
        "watchdog_date": (
            "2026-09-25"
        ),
        "status": "OPEN",
        "attempt": 1,
        "max_attempts": 3,
        "final_attempt": False,
        "check_hour": 10,
        "outcome": (
            "RECOVERY_DISPATCHED"
        ),
        "updated_at": (
            FIXED_TIMESTAMP
        ),
        "details": {
            "action": (
                "REBUILD_SILVER_FROM_RAW"
            ),
            "source": "b3",
        },
    }

    assert len(
        fake_s3.put_calls
    ) == 1

    put_call = fake_s3.put_calls[
        0
    ]

    assert (
        put_call["Bucket"]
        == BUCKET
    )

    assert (
        put_call["Key"]
        == EXPECTED_STATE_KEY
    )

    assert (
        put_call["ContentType"]
        == "application/json"
    )

    assert (
        (
            BUCKET,
            EXPECTED_STATE_KEY,
        )
        in fake_s3.objects
    )


def test_write_then_read_watchdog_state_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_s3(
        monkeypatch
    )

    monkeypatch.setattr(
        gold_recovery_watchdog_state,
        "utc_now_iso",
        lambda: FIXED_TIMESTAMP,
    )

    (
        gold_recovery_watchdog_state
        .write_watchdog_state(
            bucket=BUCKET,
            watchdog_date=(
                "2026-09-25"
            ),
            status=(
                "CLOSED_SUCCESS"
            ),
            attempt=2,
            max_attempts=3,
            final_attempt=False,
            check_hour=14,
            outcome=(
                "PIPELINE_COMPLETE"
            ),
            details={
                "plan_status": (
                    "COMPLETE"
                )
            },
        )
    )

    state = (
        gold_recovery_watchdog_state
        .read_watchdog_state(
            bucket=BUCKET,
            watchdog_date=(
                "2026-09-25"
            ),
        )
    )

    assert state is not None

    assert (
        state["status"]
        == "CLOSED_SUCCESS"
    )

    assert state[
        "attempt"
    ] == 2

    assert state[
        "check_hour"
    ] == 14

    assert (
        state["outcome"]
        == "PIPELINE_COMPLETE"
    )

    assert (
        state["updated_at"]
        == FIXED_TIMESTAMP
    )


def test_read_watchdog_state_rejects_empty_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_s3 = install_fake_s3(
        monkeypatch
    )

    fake_s3.objects[
        (
            BUCKET,
            EXPECTED_STATE_KEY,
        )
    ] = b""

    with pytest.raises(
        RuntimeError,
        match=(
            "Watchdog state object "
            "is empty"
        ),
    ):
        (
            gold_recovery_watchdog_state
            .read_watchdog_state(
                bucket=BUCKET,
                watchdog_date=(
                    WATCHDOG_DATE
                ),
            )
        )


def test_read_watchdog_state_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_s3 = install_fake_s3(
        monkeypatch
    )

    fake_s3.objects[
        (
            BUCKET,
            EXPECTED_STATE_KEY,
        )
    ] = b"{invalid-json"

    with pytest.raises(
        RuntimeError,
        match=(
            "Invalid watchdog state JSON"
        ),
    ):
        (
            gold_recovery_watchdog_state
            .read_watchdog_state(
                bucket=BUCKET,
                watchdog_date=(
                    WATCHDOG_DATE
                ),
            )
        )


def test_read_watchdog_state_rejects_missing_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_s3 = install_fake_s3(
        monkeypatch
    )

    fake_s3.objects[
        (
            BUCKET,
            EXPECTED_STATE_KEY,
        )
    ] = b'{"watchdog_date":"2026-09-25"}'

    with pytest.raises(
        RuntimeError,
        match=(
            "Watchdog state "
            "missing status"
        ),
    ):
        (
            gold_recovery_watchdog_state
            .read_watchdog_state(
                bucket=BUCKET,
                watchdog_date=(
                    WATCHDOG_DATE
                ),
            )
        )


@pytest.mark.parametrize(
    (
        "attempt",
        "max_attempts",
        "check_hour",
        "expected_message",
    ),
    [
        (
            0,
            3,
            10,
            (
                "attempt must be "
                "greater than zero"
            ),
        ),
        (
            1,
            0,
            10,
            (
                "max_attempts must be "
                "greater than zero"
            ),
        ),
        (
            4,
            3,
            10,
            (
                "attempt cannot be "
                "greater than max_attempts"
            ),
        ),
        (
            1,
            3,
            -1,
            (
                "check_hour must be "
                "between 0 and 23"
            ),
        ),
        (
            1,
            3,
            24,
            (
                "check_hour must be "
                "between 0 and 23"
            ),
        ),
    ],
)
def test_write_watchdog_state_rejects_invalid_execution_metadata(
    monkeypatch: pytest.MonkeyPatch,
    attempt: int,
    max_attempts: int,
    check_hour: int,
    expected_message: str,
) -> None:
    install_fake_s3(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        (
            gold_recovery_watchdog_state
            .write_watchdog_state(
                bucket=BUCKET,
                watchdog_date=(
                    WATCHDOG_DATE
                ),
                status="OPEN",
                attempt=attempt,
                max_attempts=(
                    max_attempts
                ),
                final_attempt=False,
                check_hour=(
                    check_hour
                ),
                outcome="TEST",
            )
        )


def test_write_watchdog_state_rejects_empty_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_s3(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="outcome is required",
    ):
        (
            gold_recovery_watchdog_state
            .write_watchdog_state(
                bucket=BUCKET,
                watchdog_date=(
                    WATCHDOG_DATE
                ),
                status="OPEN",
                attempt=1,
                max_attempts=3,
                final_attempt=False,
                check_hour=10,
                outcome="   ",
            )
        )


def test_watchdog_day_is_closed_for_success(
) -> None:
    state = {
        "status": "CLOSED_SUCCESS",
    }

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_is_closed(
            state
        )
        is True
    )

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_succeeded(
            state
        )
        is True
    )

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_failed(
            state
        )
        is False
    )


def test_watchdog_day_is_closed_for_failure(
) -> None:
    state = {
        "status": "CLOSED_FAILED",
    }

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_is_closed(
            state
        )
        is True
    )

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_succeeded(
            state
        )
        is False
    )

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_failed(
            state
        )
        is True
    )


@pytest.mark.parametrize(
    "state",
    [
        None,
        {
            "status": "OPEN",
        },
        {
            "status": (
                "FINAL_RECOVERY_DISPATCHED"
            ),
        },
    ],
)
def test_watchdog_day_is_not_closed_while_recovery_can_continue(
    state,
) -> None:
    assert (
        gold_recovery_watchdog_state
        .watchdog_day_is_closed(
            state
        )
        is False
    )

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_succeeded(
            state
        )
        is False
    )

    assert (
        gold_recovery_watchdog_state
        .watchdog_day_failed(
            state
        )
        is False
    )