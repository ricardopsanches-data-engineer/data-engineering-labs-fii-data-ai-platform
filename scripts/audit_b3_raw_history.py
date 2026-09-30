from __future__ import annotations

import re
import sys

from datetime import date
from datetime import timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.orchestration.b3_trading_calendar import classify_date


INVENTORY_PATH = (
    PROJECT_ROOT
    / "infrastructure"
    / "terraform"
    / "environments"
    / "dev"
    / "b3_raw_inventory.txt"
)

KEY_PATTERN = re.compile(
    r"raw/b3/"
    r"year=(\d{4})/"
    r"month=(\d{2})/"
    r"day=(\d{2})/"
    r"b3_download_(\d{8})\.zip$"
)


def read_inventory_text() -> str:
    """
    Lê o inventário gerado pelo PowerShell.

    Windows PowerShell pode gravar redirecionamento
    como UTF-16, enquanto versões mais novas podem
    usar UTF-8.
    """
    raw = INVENTORY_PATH.read_bytes()

    if raw.startswith(b"\xff\xfe") or raw.startswith(
        b"\xfe\xff"
    ):
        return raw.decode("utf-16")

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16")


def parse_inventory() -> tuple[
    dict[date, dict[str, object]],
    int,
]:
    objects: dict[
        date,
        dict[str, object],
    ] = {}

    invalid_count = 0

    for raw_line in read_inventory_text().splitlines():
        line = raw_line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 4:
            invalid_count += 1

            print(
                "INVALID_OR_EMPTY | "
                "reason=INVALID_INVENTORY_LINE | "
                f"line={line}"
            )

            continue

        try:
            size = int(parts[2])
        except ValueError:
            invalid_count += 1

            print(
                "INVALID_OR_EMPTY | "
                "reason=INVALID_SIZE | "
                f"line={line}"
            )

            continue

        key = parts[3]

        match = KEY_PATTERN.search(key)

        if match is None:
            invalid_count += 1

            print(
                "INVALID_OR_EMPTY | "
                "reason=INVALID_KEY | "
                f"key={key}"
            )

            continue

        (
            year,
            month,
            day,
            filename_date,
        ) = match.groups()

        partition_date = date(
            int(year),
            int(month),
            int(day),
        )

        expected_filename_date = (
            partition_date.strftime("%Y%m%d")
        )

        if filename_date != expected_filename_date:
            invalid_count += 1

            print(
                "INVALID_OR_EMPTY | "
                "reason=DATE_MISMATCH | "
                f"date={partition_date.isoformat()} | "
                f"key={key}"
            )

            continue

        if partition_date in objects:
            invalid_count += 1

            print(
                "INVALID_OR_EMPTY | "
                "reason=DUPLICATE_DATE | "
                f"date={partition_date.isoformat()} | "
                f"key={key}"
            )

            continue

        objects[partition_date] = {
            "size": size,
            "key": key,
        }

    return (
        objects,
        invalid_count,
    )


def main() -> None:
    (
        objects,
        parsing_invalid_count,
    ) = parse_inventory()

    if not objects:
        raise RuntimeError(
            "No valid B3 RAW objects found."
        )

    start_date = min(objects)
    end_date = max(objects)

    counts = {
        "EXPECTED_AND_PRESENT": 0,
        "EXPECTED_BUT_MISSING": 0,
        "NON_TRADING_DAY": 0,
        "UNEXPECTED_PRESENT": 0,
        "INVALID_OR_EMPTY": (
            parsing_invalid_count
        ),
    }

    missing_dates: list[str] = []
    unexpected_dates: list[str] = []
    invalid_dates: list[str] = []

    current = start_date

    while current <= end_date:
        classification = classify_date(
            current
        )

        present = current in objects

        if (
            classification["expected"]
            and present
        ):
            size = int(
                objects[current]["size"]
            )

            if size <= 0:
                status = "INVALID_OR_EMPTY"

                counts[status] += 1

                invalid_dates.append(
                    current.isoformat()
                )

            else:
                status = (
                    "EXPECTED_AND_PRESENT"
                )

                counts[status] += 1

        elif (
            classification["expected"]
            and not present
        ):
            status = (
                "EXPECTED_BUT_MISSING"
            )

            counts[status] += 1

            missing_dates.append(
                current.isoformat()
            )

        elif (
            not classification["expected"]
            and present
        ):
            status = (
                "UNEXPECTED_PRESENT"
            )

            counts[status] += 1

            unexpected_dates.append(
                current.isoformat()
            )

        else:
            status = "NON_TRADING_DAY"

            counts[status] += 1

        print(
            f"{current.isoformat()} | "
            f"{status} | "
            "calendar="
            f"{classification['status']} | "
            "reason="
            f"{classification['reason']}"
        )

        current += timedelta(
            days=1
        )

    print()
    print(
        "=== B3 RAW HISTORICAL AUDIT ==="
    )

    print(
        "window="
        f"{start_date.isoformat()}"
        ".."
        f"{end_date.isoformat()}"
    )

    print(
        f"raw_objects={len(objects)}"
    )

    for key, value in counts.items():
        print(
            f"{key}={value}"
        )

    print(
        "missing_dates="
        + (
            ",".join(missing_dates)
            if missing_dates
            else "NONE"
        )
    )

    print(
        "unexpected_dates="
        + (
            ",".join(
                unexpected_dates
            )
            if unexpected_dates
            else "NONE"
        )
    )

    print(
        "invalid_dates="
        + (
            ",".join(invalid_dates)
            if invalid_dates
            else "NONE"
        )
    )

    audit_ok = (
        counts[
            "EXPECTED_BUT_MISSING"
        ]
        == 0
        and counts[
            "INVALID_OR_EMPTY"
        ]
        == 0
    )

    print(
        "audit_status="
        + (
            "PASS"
            if audit_ok
            else "FAIL"
        )
    )

    if not audit_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()