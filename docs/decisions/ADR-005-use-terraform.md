# ADR-005 — Use Terraform for Infrastructure as Code

## Status
Accepted

## Context
The project should be reproducible, auditable and easy to destroy/recreate to control costs.

## Decision
Terraform will provision AWS infrastructure.

## Consequences
- Infrastructure changes are versioned in Git.
- Environments can be recreated consistently.
- State management and secrets require careful handling.
