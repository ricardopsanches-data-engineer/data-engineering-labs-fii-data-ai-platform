# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Product definition, repository, local ingestion, data contracts and initial architecture | COMPLETE |
| 1 | AWS Foundation, Terraform, IAM, cost governance and auditability | COMPLETE |
| 2 | AWS Data Lake Foundation, RAW/Silver ingestion, serverless automation and observability | COMPLETE |
| 3 | AWS Analytics Foundation: Glue Data Catalog, schemas, Athena and analytical discovery | NEXT |
| 4 | Pipeline orchestration and workflow management | PLANNED |
| 5 | Advanced transformations, Parquet optimization and Apache Iceberg | PLANNED |
| 6 | Data Quality and advanced observability | PLANNED |
| 7 | Gold analytical layer and business datasets | PLANNED |
| 8 | Portfolio and quantitative engine | PLANNED |
| 9 | Generative AI, RAG and agents | PLANNED |
| 10 | Product hardening, CI/CD and final documentation | PLANNED |

## Current Status

Phase 2 completed.

Current platform capabilities include:

- AWS infrastructure managed with Terraform.
- Remote Terraform state with locking and versioning.
- IAM least-privilege operational model.
- AWS Budget and CloudTrail audit foundation.
- Versioned and encrypted Amazon S3 Data Lake.
- B3 and CVM RAW ingestion.
- Scheduled daily ingestion using EventBridge Scheduler and AWS Lambda.
- B3 RAW to Silver transformation.
- Parquet Silver datasets.
- Containerized B3 Silver processing using Amazon ECR and AWS Lambda.
- Event-driven RAW to Silver processing using Amazon S3 notifications.
- SHA-256 based idempotency and overwrite protection.
- CloudWatch logging, metrics and operational dashboard.
- Dedicated ingestion and B3 Silver observability scripts.

## Next Phase

Phase 3 — AWS Analytics Foundation

Planned initial scope:

```text
S3 SILVER
    |
    v
AWS Glue Data Catalog
    |
    v
Schema / Metadata Discovery
    |
    v
Amazon Athena
    |
    v
Analytical Queries