# ADR-001 — Use AWS as the Primary Cloud Platform

## Status
Accepted

## Context
The project is intended to simulate a modern enterprise-grade data platform while remaining suitable for a personal portfolio and controlled budget.

## Decision
AWS will be the primary cloud platform.

## Consequences
Positive:
- Broad managed data ecosystem.
- Strong alignment with data engineering and AI workloads.
- Native integration with S3, Glue, Athena, MWAA, CloudWatch and Bedrock.

Trade-offs:
- Cloud cost must be actively controlled.
- Some services may be emulated or run locally during development.
