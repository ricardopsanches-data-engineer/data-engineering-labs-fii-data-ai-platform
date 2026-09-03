from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.observability.pipeline_health.builder import (
    DEFAULT_MAX_FRESHNESS_DAYS,
    FEATURES_PATH,
    PROJECT_ROOT,
    DatasetSpec,
    inspect_dataset,
)


# ============================================================
# Controlled failure contract
# ============================================================

CONTROLLED_FAILURE_VERSION = "v1"

TEST_NAME = "features_duplicate_key"

REFERENCE_DATE = pd.Timestamp(
    "2026-09-01"
)


# ============================================================
# Evidence outputs
# ============================================================

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "observability"
    / "controlled_failure"
)

LATEST_PATH = (
    OUTPUT_DIR
    / "latest.json"
)

HISTORY_DIR = (
    OUTPUT_DIR
    / "history"
)


# ============================================================
# Helpers
# ============================================================

def json_default(
    value: Any,
) -> Any:
    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    raise TypeError(
        "Objeto não serializável: "
        f"{type(value).__name__}"
    )


def get_check(
    result: dict[str, Any],
    check_name: str,
) -> dict[str, Any] | None:
    """
    Localiza um check produzido pelo
    Pipeline Health.
    """

    for check in result.get(
        "checks",
        [],
    ):
        if (
            check.get("name")
            == check_name
        ):
            return check

    return None


def save_evidence(
    evidence: dict[str, Any],
) -> Path:
    """
    Persiste latest.json e uma cópia
    histórica da evidência.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated_at = (
        datetime.fromisoformat(
            evidence[
                "generated_at"
            ]
        )
    )

    history_filename = (
        generated_at.strftime(
            "%Y%m%dT%H%M%SZ"
        )
        + ".json"
    )

    history_path = (
        HISTORY_DIR
        / history_filename
    )

    payload = json.dumps(
        evidence,
        indent=2,
        ensure_ascii=False,
        default=json_default,
    )

    LATEST_PATH.write_text(
        payload,
        encoding="utf-8",
    )

    history_path.write_text(
        payload,
        encoding="utf-8",
    )

    return history_path


# ============================================================
# Original dataset protection
# ============================================================

def capture_original_signature() -> dict[str, Any]:
    """
    Captura informações do parquet oficial
    antes do teste.

    O teste nunca escreve nesse arquivo.
    """

    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            "Dataset oficial de Features "
            "não encontrado: "
            f"{FEATURES_PATH}"
        )

    stat = FEATURES_PATH.stat()

    return {
        "path": str(
            FEATURES_PATH
        ),
        "size_bytes": int(
            stat.st_size
        ),
        "modified_ns": int(
            stat.st_mtime_ns
        ),
    }


def validate_original_unchanged(
    before: dict[str, Any],
) -> tuple[
    bool,
    dict[str, Any],
]:
    """
    Confirma que o parquet oficial não foi
    alterado durante o teste.
    """

    if not FEATURES_PATH.exists():
        return (
            False,
            {
                "reason": (
                    "Arquivo original deixou "
                    "de existir."
                ),
            },
        )

    stat = FEATURES_PATH.stat()

    after = {
        "path": str(
            FEATURES_PATH
        ),
        "size_bytes": int(
            stat.st_size
        ),
        "modified_ns": int(
            stat.st_mtime_ns
        ),
    }

    unchanged = (
        before[
            "size_bytes"
        ]
        == after[
            "size_bytes"
        ]
        and before[
            "modified_ns"
        ]
        == after[
            "modified_ns"
        ]
    )

    return (
        unchanged,
        after,
    )


# ============================================================
# Failure injection
# ============================================================

def create_corrupted_features_copy(
    destination: Path,
) -> dict[str, Any]:
    """
    Cria uma cópia temporária de Features
    contendo exatamente uma linha adicional
    duplicada.

    O dataset oficial é somente leitura.
    """

    source = pd.read_parquet(
        FEATURES_PATH
    )

    if source.empty:
        raise RuntimeError(
            "Não é possível executar o teste: "
            "Features está vazio."
        )

    required_columns = {
        "feature_date",
        "ticker",
    }

    missing_columns = (
        required_columns
        - set(
            source.columns
        )
    )

    if missing_columns:
        raise RuntimeError(
            "Features não possui as colunas "
            "necessárias para o teste: "
            f"{sorted(missing_columns)}"
        )

    original_duplicate_count = int(
        source.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    if original_duplicate_count != 0:
        raise RuntimeError(
            "O dataset oficial já possui "
            "duplicidades. O controlled "
            "failure exige baseline saudável."
        )

    duplicated_row = (
        source.iloc[
            [
                0
            ]
        ]
        .copy()
    )

    corrupted = pd.concat(
        [
            source,
            duplicated_row,
        ],
        ignore_index=True,
    )

    corrupted.to_parquet(
        destination,
        index=False,
    )

    injected_duplicate_count = int(
        corrupted.duplicated(
            subset=[
                "feature_date",
                "ticker",
            ]
        ).sum()
    )

    return {
        "original_rows": int(
            len(
                source
            )
        ),
        "corrupted_rows": int(
            len(
                corrupted
            )
        ),
        "rows_injected": 1,
        "original_duplicate_count": (
            original_duplicate_count
        ),
        "expected_duplicate_count": (
            injected_duplicate_count
        ),
    }


# ============================================================
# Controlled DatasetSpec
# ============================================================

def build_controlled_spec(
    corrupted_path: Path,
) -> DatasetSpec:
    """
    Replica o contrato observado de Features,
    trocando somente o path pelo parquet
    temporariamente corrompido.
    """

    return DatasetSpec(
        name=(
            "features_controlled_failure"
        ),
        path=corrupted_path,
        date_candidates=(
            "feature_date",
            "trade_date",
            "date",
        ),
        key_candidates=(
            (
                "feature_date",
                "ticker",
            ),
            (
                "trade_date",
                "ticker",
            ),
        ),
        required_columns=(
            "ticker",
            "feature_version",
            "feature_ready",
            "price_semantics",
            "return_semantics",
            "corporate_action_value_semantics",
        ),
        freshness_mode="DATA_DATE",
        freshness_date_candidates=(
            "feature_date",
            "trade_date",
            "date",
        ),
    )


# ============================================================
# Controlled failure execution
# ============================================================

def run_controlled_failure() -> dict[str, Any]:
    generated_at = datetime.now(
        timezone.utc
    )

    original_before = (
        capture_original_signature()
    )

    print(
        "======================================"
    )
    print(
        "Controlled Failure Test"
    )
    print(
        "======================================"
    )

    print(
        "Controlled failure version: "
        f"{CONTROLLED_FAILURE_VERSION}"
    )

    print(
        "Test: "
        f"{TEST_NAME}"
    )

    print(
        "Official dataset:"
    )

    print(
        f"  {FEATURES_PATH}"
    )

    print(
        "\nSafety policy:"
    )

    print(
        "  Official parquet is READ ONLY."
    )

    print(
        "  Corruption is injected only "
        "into a temporary copy."
    )

    with tempfile.TemporaryDirectory(
        prefix=(
            "fii_observability_"
            "controlled_failure_"
        )
    ) as temporary_directory:

        temporary_path = Path(
            temporary_directory
        )

        corrupted_path = (
            temporary_path
            / "fii_features_corrupted.parquet"
        )

        print(
            "\nCreating temporary "
            "corrupted dataset..."
        )

        injection = (
            create_corrupted_features_copy(
                destination=(
                    corrupted_path
                )
            )
        )

        print(
            "Original rows: "
            f"{injection['original_rows']:,}"
        )

        print(
            "Corrupted rows: "
            f"{injection['corrupted_rows']:,}"
        )

        print(
            "Injected rows: "
            f"{injection['rows_injected']}"
        )

        print(
            "Expected duplicate count: "
            f"{injection['expected_duplicate_count']}"
        )

        spec = build_controlled_spec(
            corrupted_path=(
                corrupted_path
            )
        )

        print(
            "\nRunning Pipeline Health "
            "against temporary copy..."
        )

        (
            observed_result,
            _,
        ) = inspect_dataset(
            spec=spec,
            reference_date=(
                REFERENCE_DATE
            ),
            max_freshness_days=(
                DEFAULT_MAX_FRESHNESS_DAYS
            ),
        )

        duplicates_check = get_check(
            result=(
                observed_result
            ),
            check_name="duplicates",
        )

        if duplicates_check is None:
            duplicate_detected = False
            observed_duplicate_status = None
            observed_duplicate_count = None

        else:
            observed_duplicate_status = (
                duplicates_check.get(
                    "status"
                )
            )

            details = (
                duplicates_check.get(
                    "details",
                    {},
                )
            )

            observed_duplicate_count = (
                details.get(
                    "duplicate_count"
                )
            )

            duplicate_detected = (
                observed_duplicate_status
                == "FAIL"
                and observed_duplicate_count
                == injection[
                    "expected_duplicate_count"
                ]
            )

        dataset_failed = (
            observed_result.get(
                "status"
            )
            == "FAIL"
        )

    (
        original_unchanged,
        original_after,
    ) = validate_original_unchanged(
        original_before
    )

    temporary_removed = (
        not corrupted_path.exists()
    )

    test_passed = all(
        [
            duplicate_detected,
            dataset_failed,
            original_unchanged,
            temporary_removed,
        ]
    )

    evidence = {
        "controlled_failure_version": (
            CONTROLLED_FAILURE_VERSION
        ),
        "test_name": (
            TEST_NAME
        ),
        "generated_at": (
            generated_at.isoformat()
        ),
        "reference_date": (
            REFERENCE_DATE
            .date()
            .isoformat()
        ),
        "test_status": (
            "PASS"
            if test_passed
            else "FAIL"
        ),
        "expected_behavior": {
            "dataset_status": (
                "FAIL"
            ),
            "duplicates_check_status": (
                "FAIL"
            ),
            "duplicate_count": (
                injection[
                    "expected_duplicate_count"
                ]
            ),
        },
        "observed_behavior": {
            "dataset_status": (
                observed_result.get(
                    "status"
                )
            ),
            "duplicates_check_status": (
                observed_duplicate_status
            ),
            "duplicate_count": (
                observed_duplicate_count
            ),
        },
        "failure_injection": (
            injection
        ),
        "safety": {
            "official_dataset_modified": (
                not original_unchanged
            ),
            "official_dataset_unchanged": (
                original_unchanged
            ),
            "temporary_artifact_removed": (
                temporary_removed
            ),
            "original_before": (
                original_before
            ),
            "original_after": (
                original_after
            ),
        },
        "assertions": {
            "duplicate_detected": (
                duplicate_detected
            ),
            "dataset_failed_as_expected": (
                dataset_failed
            ),
            "official_dataset_unchanged": (
                original_unchanged
            ),
            "temporary_artifact_removed": (
                temporary_removed
            ),
        },
    }

    history_path = save_evidence(
        evidence
    )

    print(
        "\n======================================"
    )
    print(
        "Controlled Failure Result"
    )
    print(
        "======================================"
    )

    print(
        "Observed dataset status: "
        f"{observed_result.get('status')}"
    )

    print(
        "Observed duplicates check: "
        f"{observed_duplicate_status}"
    )

    print(
        "Observed duplicate count: "
        f"{observed_duplicate_count}"
    )

    print(
        "Official dataset unchanged: "
        f"{original_unchanged}"
    )

    print(
        "Temporary artifact removed: "
        f"{temporary_removed}"
    )

    print(
        "\nTest status: "
        f"{evidence['test_status']}"
    )

    print(
        "\nEvidence:"
    )

    print(
        f"Latest: "
        f"{LATEST_PATH}"
    )

    print(
        f"History: "
        f"{history_path}"
    )

    return evidence


# ============================================================
# Main
# ============================================================

def main() -> None:
    evidence = (
        run_controlled_failure()
    )

    if (
        evidence[
            "test_status"
        ]
        != "PASS"
    ):
        raise RuntimeError(
            "Controlled failure não "
            "comprovou o comportamento "
            "esperado."
        )

    print(
        "\nControlled failure concluído "
        "com sucesso."
    )

    print(
        "O monitor detectou a quebra "
        "e o dataset oficial permaneceu "
        "intacto."
    )


if __name__ == "__main__":
    main()