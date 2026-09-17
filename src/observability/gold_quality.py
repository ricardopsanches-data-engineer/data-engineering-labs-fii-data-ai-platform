from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd


OBSERVABILITY_VERSION = "v1"

DEFAULT_MIN_RESOLUTION_RATE = 0.90

RESOLVED_STATUS = "AUTO_RESOLVED"

STRUCTURAL_METHOD = (
    "B3_UNDERLYING_REFERENCE"
)

SIGNATURE_METHOD = (
    "B3_PRIMARY_SIGNATURE"
)

REQUIRED_COLUMNS = (
    "cnpj_classe",
    "resolution_status",
    "resolution_method",
    "primary_instrument_id",
    "ticker",
    "isin",
)


class GoldQualityError(
    RuntimeError
):
    """
    Raised when a Gold dataset
    violates a critical quality rule.
    """


def utc_now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


def emit_observability_event(
    event: str,
    *,
    pipeline: str,
    status: str = "INFO",
    **details: Any,
) -> None:
    """
    Emits a vendor-neutral structured
    JSON event to stdout.

    stdout can later be collected by
    CloudWatch, OpenTelemetry, Loki,
    Prometheus-related agents, etc.
    """

    payload = {
        "timestamp": utc_now_iso(),
        "observability_version": (
            OBSERVABILITY_VERSION
        ),
        "event": event,
        "pipeline": pipeline,
        "status": status,
        **details,
    }

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            separators=(
                ",",
                ":",
            ),
        )
    )


def build_check(
    name: str,
    status: str,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    """
    Keeps the same conceptual contract
    already used by pipeline_health:
    name, status, message and details.
    """

    result: dict[
        str,
        Any,
    ] = {
        "name": name,
        "status": status,
        "message": message,
    }

    if details:
        result[
            "details"
        ] = details

    return result


def resolve_status(
    checks: list[
        dict[str, Any]
    ],
) -> str:
    statuses = [
        check.get(
            "status",
            "FAIL",
        )
        for check
        in checks
    ]

    if "FAIL" in statuses:
        return "FAIL"

    if "WARN" in statuses:
        return "WARN"

    return "PASS"


def _missing_mask(
    series: pd.Series,
) -> pd.Series:
    normalized = (
        series
        .astype(
            "string"
        )
        .str.strip()
    )

    return (
        normalized.isna()
        | normalized.eq("")
    )


def _series_or_na(
    dataframe: pd.DataFrame,
    column: str,
) -> pd.Series:
    if column in dataframe.columns:
        return dataframe[
            column
        ]

    return pd.Series(
        pd.NA,
        index=dataframe.index,
        dtype="string",
    )


def calculate_fii_master_metrics(
    fii_master: pd.DataFrame,
) -> dict[str, Any]:
    rows = int(
        len(
            fii_master
        )
    )

    resolution_status = (
        _series_or_na(
            fii_master,
            "resolution_status",
        )
        .astype(
            "string"
        )
    )

    resolution_method = (
        _series_or_na(
            fii_master,
            "resolution_method",
        )
        .astype(
            "string"
        )
    )

    resolved_mask = (
        resolution_status.eq(
            RESOLVED_STATUS
        )
        .fillna(
            False
        )
    )

    unresolved_mask = (
        ~resolved_mask
    )

    resolved = int(
        resolved_mask.sum()
    )

    unresolved = int(
        unresolved_mask.sum()
    )

    resolution_rate = (
        float(
            resolved / rows
        )
        if rows
        else 0.0
    )

    structural_resolution = int(
        resolution_method.eq(
            STRUCTURAL_METHOD
        )
        .fillna(
            False
        )
        .sum()
    )

    signature_resolution = int(
        resolution_method.eq(
            SIGNATURE_METHOD
        )
        .fillna(
            False
        )
        .sum()
    )

    cnpj = _series_or_na(
        fii_master,
        "cnpj_classe",
    )

    primary_id = _series_or_na(
        fii_master,
        "primary_instrument_id",
    )

    ticker = _series_or_na(
        fii_master,
        "ticker",
    )

    isin = _series_or_na(
        fii_master,
        "isin",
    )

    missing_cnpj_mask = (
        _missing_mask(
            cnpj
        )
    )

    valid_cnpj_mask = (
        ~missing_cnpj_mask
    )

    duplicate_cnpj_rows = int(
        cnpj[
            valid_cnpj_mask
        ]
        .duplicated(
            keep=False
        )
        .sum()
    )

    resolved_primary = (
        primary_id[
            resolved_mask
        ]
    )

    resolved_primary_missing = (
        _missing_mask(
            resolved_primary
        )
    )

    valid_resolved_primary = (
        resolved_primary[
            ~resolved_primary_missing
        ]
    )

    duplicate_primary_instrument_id_rows = int(
        valid_resolved_primary
        .duplicated(
            keep=False
        )
        .sum()
    )

    resolved_without_primary_id = int(
        (
            resolved_mask
            & _missing_mask(
                primary_id
            )
        )
        .sum()
    )

    resolved_without_ticker = int(
        (
            resolved_mask
            & _missing_mask(
                ticker
            )
        )
        .sum()
    )

    resolved_without_isin = int(
        (
            resolved_mask
            & _missing_mask(
                isin
            )
        )
        .sum()
    )

    unresolved_with_primary_id = int(
        (
            unresolved_mask
            & ~_missing_mask(
                primary_id
            )
        )
        .sum()
    )

    unresolved_with_ticker = int(
        (
            unresolved_mask
            & ~_missing_mask(
                ticker
            )
        )
        .sum()
    )

    unresolved_with_isin = int(
        (
            unresolved_mask
            & ~_missing_mask(
                isin
            )
        )
        .sum()
    )

    missing_required_columns = [
        column
        for column
        in REQUIRED_COLUMNS
        if column
        not in fii_master.columns
    ]

    return {
        "gold_fii_master_rows": (
            rows
        ),
        "gold_fii_master_resolved": (
            resolved
        ),
        "gold_fii_master_unresolved": (
            unresolved
        ),
        "gold_fii_master_resolution_rate": (
            resolution_rate
        ),
        "gold_fii_master_structural_resolution": (
            structural_resolution
        ),
        "gold_fii_master_signature_resolution": (
            signature_resolution
        ),
        "gold_fii_master_missing_cnpj": int(
            missing_cnpj_mask.sum()
        ),
        "gold_fii_master_duplicate_cnpj_rows": (
            duplicate_cnpj_rows
        ),
        (
            "gold_fii_master_"
            "duplicate_primary_instrument_id_rows"
        ): (
            duplicate_primary_instrument_id_rows
        ),
        (
            "gold_fii_master_"
            "resolved_without_primary_id"
        ): (
            resolved_without_primary_id
        ),
        (
            "gold_fii_master_"
            "resolved_without_ticker"
        ): (
            resolved_without_ticker
        ),
        (
            "gold_fii_master_"
            "resolved_without_isin"
        ): (
            resolved_without_isin
        ),
        (
            "gold_fii_master_"
            "unresolved_with_primary_id"
        ): (
            unresolved_with_primary_id
        ),
        (
            "gold_fii_master_"
            "unresolved_with_ticker"
        ): (
            unresolved_with_ticker
        ),
        (
            "gold_fii_master_"
            "unresolved_with_isin"
        ): (
            unresolved_with_isin
        ),
        "missing_required_columns": (
            missing_required_columns
        ),
        "missing_required_columns_count": int(
            len(
                missing_required_columns
            )
        ),
    }


def evaluate_fii_master_quality(
    fii_master: pd.DataFrame,
    *,
    min_resolution_rate: float = (
        DEFAULT_MIN_RESOLUTION_RATE
    ),
) -> dict[str, Any]:
    metrics = (
        calculate_fii_master_metrics(
            fii_master
        )
    )

    checks: list[
        dict[str, Any]
    ] = []

    rows = metrics[
        "gold_fii_master_rows"
    ]

    checks.append(
        build_check(
            name="dataset_not_empty",
            status=(
                "PASS"
                if rows > 0
                else "FAIL"
            ),
            message=(
                "Gold FII master contains records."
                if rows > 0
                else (
                    "Gold FII master returned "
                    "zero records."
                )
            ),
            rows=rows,
        )
    )

    missing_columns = metrics[
        "missing_required_columns"
    ]

    checks.append(
        build_check(
            name="required_columns",
            status=(
                "PASS"
                if not missing_columns
                else "FAIL"
            ),
            message=(
                "All required Gold columns "
                "are present."
                if not missing_columns
                else (
                    "Required Gold columns "
                    "are missing."
                )
            ),
            missing_columns=(
                missing_columns
            ),
        )
    )

    missing_cnpj = metrics[
        "gold_fii_master_missing_cnpj"
    ]

    checks.append(
        build_check(
            name="missing_cnpj",
            status=(
                "PASS"
                if missing_cnpj == 0
                else "FAIL"
            ),
            message=(
                "All Gold rows have CNPJ."
                if missing_cnpj == 0
                else (
                    "Gold contains rows "
                    "without CNPJ."
                )
            ),
            count=missing_cnpj,
        )
    )

    duplicate_cnpj = metrics[
        "gold_fii_master_duplicate_cnpj_rows"
    ]

    checks.append(
        build_check(
            name="duplicate_cnpj",
            status=(
                "PASS"
                if duplicate_cnpj == 0
                else "FAIL"
            ),
            message=(
                "CNPJ is unique in Gold."
                if duplicate_cnpj == 0
                else (
                    "Duplicate CNPJ rows "
                    "were detected."
                )
            ),
            count=duplicate_cnpj,
        )
    )

    duplicate_primary = metrics[
        (
            "gold_fii_master_"
            "duplicate_primary_instrument_id_rows"
        )
    ]

    checks.append(
        build_check(
            name=(
                "duplicate_primary_"
                "instrument_id"
            ),
            status=(
                "PASS"
                if duplicate_primary == 0
                else "FAIL"
            ),
            message=(
                "Primary B3 instrument IDs "
                "are unique among resolved FIIs."
                if duplicate_primary == 0
                else (
                    "Duplicate primary B3 "
                    "instrument IDs detected."
                )
            ),
            count=duplicate_primary,
        )
    )

    critical_zero_metrics = {
        "resolved_without_primary_id": (
            metrics[
                (
                    "gold_fii_master_"
                    "resolved_without_primary_id"
                )
            ]
        ),
        "resolved_without_ticker": (
            metrics[
                (
                    "gold_fii_master_"
                    "resolved_without_ticker"
                )
            ]
        ),
        "resolved_without_isin": (
            metrics[
                (
                    "gold_fii_master_"
                    "resolved_without_isin"
                )
            ]
        ),
        "unresolved_with_primary_id": (
            metrics[
                (
                    "gold_fii_master_"
                    "unresolved_with_primary_id"
                )
            ]
        ),
        "unresolved_with_ticker": (
            metrics[
                (
                    "gold_fii_master_"
                    "unresolved_with_ticker"
                )
            ]
        ),
        "unresolved_with_isin": (
            metrics[
                (
                    "gold_fii_master_"
                    "unresolved_with_isin"
                )
            ]
        ),
    }

    for (
        check_name,
        value,
    ) in critical_zero_metrics.items():
        checks.append(
            build_check(
                name=check_name,
                status=(
                    "PASS"
                    if value == 0
                    else "FAIL"
                ),
                message=(
                    f"{check_name} is zero."
                    if value == 0
                    else (
                        f"{check_name} "
                        "violated Gold semantics."
                    )
                ),
                count=value,
            )
        )

    resolution_rate = metrics[
        "gold_fii_master_resolution_rate"
    ]

    checks.append(
        build_check(
            name="resolution_rate",
            status=(
                "PASS"
                if (
                    resolution_rate
                    >= min_resolution_rate
                )
                else "WARN"
            ),
            message=(
                "Resolution rate is within "
                "the expected threshold."
                if (
                    resolution_rate
                    >= min_resolution_rate
                )
                else (
                    "Resolution rate is below "
                    "the expected threshold."
                )
            ),
            resolution_rate=(
                resolution_rate
            ),
            min_resolution_rate=(
                min_resolution_rate
            ),
        )
    )

    status = resolve_status(
        checks
    )

    return {
        "status": status,
        "metrics": metrics,
        "checks": checks,
        "thresholds": {
            "min_resolution_rate": (
                min_resolution_rate
            ),
        },
    }


def assert_fii_master_quality(
    quality_result: dict[
        str,
        Any,
    ],
) -> None:
    if (
        quality_result.get(
            "status"
        )
        == "FAIL"
    ):
        failed_checks = [
            check.get(
                "name",
                "unknown",
            )
            for check
            in quality_result.get(
                "checks",
                [],
            )
            if (
                check.get(
                    "status"
                )
                == "FAIL"
            )
        ]

        raise GoldQualityError(
            "Gold FII master failed "
            "quality validation. "
            "Failed checks: "
            + ", ".join(
                failed_checks
            )
        )