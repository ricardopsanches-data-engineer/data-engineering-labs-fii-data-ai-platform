from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import pandas as pd

from src.gold.fii_master import (
    build_fii_master,
)
from src.observability.gold_quality import (
    DEFAULT_MIN_RESOLUTION_RATE,
    assert_fii_master_quality,
    emit_observability_event,
    evaluate_fii_master_quality,
)


PIPELINE_NAME = "fii_master_gold"

DEFAULT_OUTPUT_ROOT = Path(
    "data/gold/fii-master"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build Gold FII master "
            "from CVM, B3 Instruments "
            "and B3 Trades Silver data."
        )
    )

    parser.add_argument(
        "--cvm",
        required=True,
        type=Path,
        help=(
            "Path to CVM Silver parquet."
        ),
    )

    parser.add_argument(
        "--instruments",
        required=True,
        type=Path,
        help=(
            "Path to B3 Instruments "
            "Silver parquet."
        ),
    )

    parser.add_argument(
        "--trades",
        required=False,
        type=Path,
        help=(
            "Optional path to B3 Trades "
            "Silver parquet."
        ),
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=(
            "Gold output root directory."
        ),
    )

    parser.add_argument(
        "--min-resolution-rate",
        type=float,
        default=(
            DEFAULT_MIN_RESOLUTION_RATE
        ),
        help=(
            "Minimum expected entity "
            "resolution rate. "
            "Below this value the pipeline "
            "emits WARN instead of FAIL."
        ),
    )

    return parser.parse_args()


def validate_input_file(
    path: Path,
    label: str,
) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} file not found: "
            f"{path}"
        )


def validate_resolution_threshold(
    value: float,
) -> None:
    if not 0 <= value <= 1:
        raise ValueError(
            "--min-resolution-rate "
            "must be between 0 and 1."
        )


def build_output_path(
    output_root: Path,
    reference_date: object,
) -> Path:
    date = pd.Timestamp(
        reference_date
    )

    return (
        output_root
        / f"year={date.year:04d}"
        / f"month={date.month:02d}"
        / f"day={date.day:02d}"
        / "fii_master.parquet"
    )


def print_summary(
    fii_master: pd.DataFrame,
    quality_result: dict,
) -> None:
    print()
    print(
        "======================================"
    )
    print(
        "GOLD FII MASTER"
    )
    print(
        "======================================"
    )
    print()

    metrics = quality_result[
        "metrics"
    ]

    print(
        "Registros: "
        f"{metrics['gold_fii_master_rows']:,}"
    )

    print(
        "Resolvidos: "
        f"{metrics['gold_fii_master_resolved']:,}"
    )

    print(
        "Não resolvidos: "
        f"{metrics['gold_fii_master_unresolved']:,}"
    )

    print(
        "Taxa de resolução: "
        f"{metrics['gold_fii_master_resolution_rate'] * 100:.2f}%"
    )

    print(
        "Status de qualidade: "
        f"{quality_result['status']}"
    )

    if fii_master.empty:
        return

    print()
    print(
        "=== RESOLUTION STATUS ==="
    )

    print(
        fii_master[
            "resolution_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "=== RESOLUTION METHOD ==="
    )

    print(
        fii_master[
            "resolution_method"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "=== RESOLUTION EVIDENCE ==="
    )

    print(
        fii_master[
            "resolution_evidence"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "=== QUALITY CHECKS ==="
    )

    for check in quality_result[
        "checks"
    ]:
        print(
            f"{check['status']:4} "
            f"{check['name']}: "
            f"{check['message']}"
        )

    print()
    print(
        "=== SAMPLE ==="
    )

    sample_columns = [
        "cnpj_classe",
        "codigo_cvm",
        "ticker",
        "isin",
        "primary_instrument_id",
        "resolution_method",
        "resolution_evidence",
    ]

    print(
        fii_master[
            sample_columns
        ]
        .head(20)
        .to_string(
            index=False
        )
    )


def run_pipeline(
    args: argparse.Namespace,
) -> Path:
    started_at = perf_counter()

    emit_observability_event(
        "pipeline_started",
        pipeline=PIPELINE_NAME,
        cvm_path=str(
            args.cvm
        ),
        instruments_path=str(
            args.instruments
        ),
        trades_path=(
            str(
                args.trades
            )
            if args.trades
            is not None
            else None
        ),
        output_root=str(
            args.output_root
        ),
        min_resolution_rate=(
            args.min_resolution_rate
        ),
    )

    validate_resolution_threshold(
        args.min_resolution_rate
    )

    validate_input_file(
        args.cvm,
        "CVM Silver",
    )

    validate_input_file(
        args.instruments,
        "B3 Instruments Silver",
    )

    if args.trades is not None:
        validate_input_file(
            args.trades,
            "B3 Trades Silver",
        )

    print(
        "Reading CVM Silver..."
    )

    cvm = pd.read_parquet(
        args.cvm
    )

    print(
        "Reading B3 Instruments Silver..."
    )

    instruments = pd.read_parquet(
        args.instruments
    )

    trades = None

    if args.trades is not None:
        print(
            "Reading B3 Trades Silver..."
        )

        trades = pd.read_parquet(
            args.trades
        )

    print(
        "Building Gold fii_master..."
    )

    fii_master = build_fii_master(
        cvm=cvm,
        instruments=instruments,
        trades=trades,
    )

    quality_result = (
        evaluate_fii_master_quality(
            fii_master,
            min_resolution_rate=(
                args.min_resolution_rate
            ),
        )
    )

    emit_observability_event(
        "gold_fii_master_quality",
        pipeline=PIPELINE_NAME,
        status=quality_result[
            "status"
        ],
        metrics=quality_result[
            "metrics"
        ],
        checks=quality_result[
            "checks"
        ],
        thresholds=quality_result[
            "thresholds"
        ],
    )

    print_summary(
        fii_master,
        quality_result,
    )

    assert_fii_master_quality(
        quality_result
    )

    reference_dates = (
        fii_master[
            "reference_date"
        ]
        .dropna()
    )

    if reference_dates.empty:
        raise RuntimeError(
            "Gold FII master has no "
            "reference_date."
        )

    reference_date = (
        reference_dates.iloc[0]
    )

    output_path = (
        build_output_path(
            output_root=args.output_root,
            reference_date=reference_date,
        )
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fii_master.to_parquet(
        output_path,
        index=False,
    )

    elapsed_seconds = (
        perf_counter()
        - started_at
    )

    emit_observability_event(
        "pipeline_completed",
        pipeline=PIPELINE_NAME,
        status=quality_result[
            "status"
        ],
        output_path=str(
            output_path
        ),
        reference_date=str(
            pd.Timestamp(
                reference_date
            ).date()
        ),
        rows=int(
            len(
                fii_master
            )
        ),
        elapsed_seconds=round(
            elapsed_seconds,
            4,
        ),
    )

    print()
    print(
        "Gold parquet written to:"
    )
    print(
        f"  {output_path}"
    )

    return output_path


def main() -> None:
    args = parse_args()

    started_at = perf_counter()

    try:
        run_pipeline(
            args
        )

    except Exception as exc:
        elapsed_seconds = (
            perf_counter()
            - started_at
        )

        emit_observability_event(
            "pipeline_failed",
            pipeline=PIPELINE_NAME,
            status="FAIL",
            error_type=(
                type(
                    exc
                ).__name__
            ),
            error_message=str(
                exc
            ),
            elapsed_seconds=round(
                elapsed_seconds,
                4,
            ),
        )

        raise


if __name__ == "__main__":
    main()