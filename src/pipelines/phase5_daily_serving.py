from __future__ import annotations

from typing import Any

from src.pipelines.ai_structured_retrieval_to_s3 import (
    run as run_ai_structured_retrieval,
)
from src.pipelines.daily_consumption_to_s3 import (
    run as run_daily_consumption,
)
from src.pipelines.ml_inference_serving_to_s3 import (
    run as run_ml_inference_serving,
)
from src.product.service import (
    get_product_status,
)


def run_phase5_daily_serving(
    force: bool = False,
) -> dict[str, Any]:
    """
    Execute the Phase 5 serving chain in
    dependency order.

    The chain stops immediately if any
    upstream step fails.
    """

    print()
    print(
        "======================================"
    )
    print(
        "PHASE 5 DAILY SERVING"
    )
    print(
        "======================================"
    )

    print()
    print(
        "[1/4] Daily Consumption"
    )

    run_daily_consumption(
        force=force,
    )

    print()
    print(
        "[2/4] ML Serving"
    )

    run_ml_inference_serving(
        force=force,
    )

    print()
    print(
        "[3/4] AI Structured Retrieval"
    )

    run_ai_structured_retrieval(
        force=force,
    )

    print()
    print(
        "[4/4] Product Readiness"
    )

    product_status = (
        get_product_status()
    )

    if (
        product_status.get(
            "status"
        )
        != "READY"
    ):
        raise RuntimeError(
            "Product layer is not READY."
        )

    print()
    print(
        "======================================"
    )
    print(
        "PHASE 5 DAILY SERVING READY"
    )
    print(
        "======================================"
    )

    print(
        "Business date: "
        f"{product_status['business_date']}"
    )

    print(
        "Tickers:       "
        f"{product_status['ticker_count']}"
    )

    return product_status


def main() -> None:
    run_phase5_daily_serving()


if __name__ == "__main__":
    main()