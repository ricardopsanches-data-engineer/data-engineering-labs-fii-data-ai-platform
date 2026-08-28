# ADR-002 — Use Amazon S3 as the Data Lake Storage Layer

## Status
Accepted

## Context
The platform requires durable, scalable and cost-efficient object storage for raw and curated datasets.

## Decision
Amazon S3 will be the primary Data Lake storage layer.

## Consequences
- Enables separation of storage and compute.
- Integrates with Glue, Athena and Iceberg.
- Requires clear naming, partitioning, lifecycle and access policies.
