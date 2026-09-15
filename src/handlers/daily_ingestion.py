from __future__ import annotations

import os
from datetime import UTC, datetime

from src.pipelines.b3_raw_to_s3 import ingest_daily as ingest_b3_daily
from src.pipelines.cvm_raw_to_s3 import ingest_daily as ingest_cvm_daily


def configure_runtime_environment() -> None:
    """
    Configura o filesystem de execução.

    Local:
        mantém o diretório atual do projeto.

    AWS Lambda:
        utiliza /tmp, que é a área gravável
        disponível durante a execução.
    """

    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        os.chdir("/tmp")

        print(
            "Runtime AWS Lambda detectado | "
            "working_directory=/tmp"
        )


def run_daily_ingestion() -> dict:
    """
    Executa a ingestão diária das fontes B3 e CVM.

    As fontes são independentes:
    falha em uma não impede a tentativa da outra.

    Ao final, se qualquer fonte falhar,
    a execução é marcada como erro para que
    a AWS possa identificar e tratar a falha.
    """

    started_at = datetime.now(UTC)

    results = {
        "b3": {
            "status": "pending",
            "error": None,
        },
        "cvm": {
            "status": "pending",
            "error": None,
        },
    }

    print("======================================")
    print("DAILY INGESTION")
    print("======================================")
    print(f"Início UTC: {started_at.isoformat()}")
    print()

    try:
        ingest_b3_daily()

        results["b3"]["status"] = "success"

    except Exception as error:
        results["b3"]["status"] = "error"
        results["b3"]["error"] = str(error)

        print(
            "B3 | ERROR | "
            f"{error}"
        )

    print()

    try:
        ingest_cvm_daily()

        results["cvm"]["status"] = "success"

    except Exception as error:
        results["cvm"]["status"] = "error"
        results["cvm"]["error"] = str(error)

        print(
            "CVM | ERROR | "
            f"{error}"
        )

    finished_at = datetime.now(UTC)

    results["started_at"] = started_at.isoformat()
    results["finished_at"] = finished_at.isoformat()

    print()
    print("======================================")
    print("Resumo final")
    print("======================================")
    print(f"B3:  {results['b3']['status']}")
    print(f"CVM: {results['cvm']['status']}")
    print(f"Fim UTC: {finished_at.isoformat()}")

    failed_sources = [
        source
        for source in ("b3", "cvm")
        if results[source]["status"] == "error"
    ]

    if failed_sources:
        raise RuntimeError(
            "Falha na ingestão diária das fontes: "
            + ", ".join(failed_sources)
        )

    return results


def lambda_handler(
    event: dict,
    context: object,
) -> dict:
    """
    Entry point da AWS Lambda.
    """

    del event
    del context

    configure_runtime_environment()

    return run_daily_ingestion()


if __name__ == "__main__":
    run_daily_ingestion()