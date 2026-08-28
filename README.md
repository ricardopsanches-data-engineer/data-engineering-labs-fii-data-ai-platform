# FII Data & AI Platform

Modern **Data Engineering, Data Architecture and Generative AI** platform for Brazilian Real Estate Investment Funds (FIIs), built with a production-inspired AWS architecture.

> Current status: **Phase 0 — Product definition and project foundation**

## Goals

- Ingest FII data from approved sources.
- Preserve raw and historical datasets.
- Build curated analytical layers.
- Orchestrate pipelines with Apache Airflow.
- Provision AWS infrastructure with Terraform.
- Apply automated tests, data quality and observability.
- Enable SQL analytics and quantitative portfolio analysis.
- Evolve later to Generative AI, RAG and agentic capabilities.

## Planned Stack

| Area | Technology |
|---|---|
| Cloud | AWS |
| IaC | Terraform |
| Data Lake | Amazon S3 |
| Catalog | AWS Glue Data Catalog |
| Orchestration | Apache Airflow / Amazon MWAA |
| Processing | Python / PySpark / AWS Glue |
| Formats | JSON / Parquet / Apache Iceberg |
| Query | Amazon Athena |
| Quality | AWS Glue Data Quality + automated tests |
| Observability | Amazon CloudWatch |
| CI/CD | GitHub Actions |
| Local development | Docker |
| Tests | Pytest |
| Code quality | Ruff / pre-commit |
| Future AI | Amazon Bedrock / RAG / Agentic AI |

## Repository Structure

```text
fii-data-ai-platform/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── Makefile
├── pyproject.toml
├── requirements-dev.txt
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── diagrams/
│   └── data-model/
├── infrastructure/
│   └── terraform/
├── airflow/
│   ├── dags/
│   └── plugins/
├── src/
│   ├── ingestion/
│   ├── transformation/
│   ├── quality/
│   ├── analytics/
│   └── ai/
├── tests/
├── sql/
├── docker/
├── data/
│   └── samples/
└── .github/
    └── workflows/
```

## Roadmap

| Phase | Scope |
|---|---|
| 0 | Product definition, repository and initial architecture |
| 1 | AWS foundation + Terraform |
| 2 | S3 Data Lake |
| 3 | FII data ingestion |
| 4 | Airflow / Amazon MWAA |
| 5 | Transformations + Iceberg |
| 6 | Data Quality + Observability |
| 7 | Analytical layer |
| 8 | Portfolio and quantitative engine |
| 9 | Generative AI / RAG / Agents |
| 10 | Product hardening and final documentation |

## Phase 0 Checklist

- [x] Define product vision
- [x] Define business problem
- [x] Define MVP direction
- [x] Choose initial stack
- [x] Define roadmap
- [x] Create repository structure
- [x] Create initial project documentation
- [x] Create initial ADRs
- [ ] Select and validate the first FII data source
- [ ] Initialize remote GitHub repository
- [ ] Begin Phase 1 — AWS foundation + Terraform

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell

python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Architecture Decisions

Initial ADRs are stored under `docs/decisions/`:

- ADR-001 — Use AWS
- ADR-002 — Use Amazon S3 as Data Lake
- ADR-003 — Use Apache Airflow
- ADR-004 — Use Apache Iceberg
- ADR-005 — Use Terraform

## Cost Strategy

Development will run locally whenever possible. AWS resources will be created only when needed and provisioned through Terraform, with budgets, tagging and teardown strategies included from the beginning.

## Disclaimer

This project is educational, technical and experimental. It does not provide investment advice or personalized financial recommendations.
