# ADR-003 — Use Apache Airflow for Workflow Orchestration

## Status
Accepted

## Context
The project requires explicit, observable and schedulable orchestration of ingestion and transformation workflows.

## Decision
Apache Airflow will be used for orchestration. Local development will use Docker; production validation will target Amazon MWAA when appropriate.

## Consequences
- DAG-based orchestration becomes a core project pattern.
- Local development avoids keeping managed environments active unnecessarily.
- DAG design and dependency management must remain simple and testable.
