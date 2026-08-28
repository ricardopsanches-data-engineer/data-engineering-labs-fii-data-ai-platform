# ADR-004 — Use Apache Iceberg for Curated Analytical Tables

## Status
Accepted

## Context
The curated layers require an open table format that supports schema evolution, transactional semantics and modern analytical workloads.

## Decision
Apache Iceberg will be the preferred table format for curated analytical datasets when its benefits justify the added complexity.

## Consequences
- Better long-term table management than plain files alone.
- Integrates with AWS analytical services.
- Adds catalog and table maintenance considerations.
