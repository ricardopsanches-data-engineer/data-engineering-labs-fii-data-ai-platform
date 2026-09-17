from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.gold.fii_master import (
    build_fii_master,
)


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

    print(
        "Registros: "
        f"{len(fii_master):,}"
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

    resolved = (
        fii_master[
            "resolution_status"
        ]
        .eq(
            "AUTO_RESOLVED"
        )
        .sum()
    )

    total = len(
        fii_master
    )

    resolution_rate = (
        resolved
        / total
        * 100
    )

    print()
    print(
        "Taxa de resolução: "
        f"{resolution_rate:.2f}%"
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


def main() -> None:
    args = parse_args()

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

    if fii_master.empty:
        raise RuntimeError(
            "fii_master generation "
            "returned zero records."
        )

    reference_date = (
        fii_master[
            "reference_date"
        ]
        .dropna()
        .iloc[0]
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

    print_summary(
        fii_master
    )

    print()
    print(
        "Gold parquet written to:"
    )
    print(
        f"  {output_path}"
    )


if __name__ == "__main__":
    main()