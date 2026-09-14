# Terraform — AWS Foundation

This directory contains the Infrastructure as Code (IaC) used to provision and manage the AWS foundation for the **FII Data & AI Platform**.

The infrastructure is managed with Terraform and follows a phased architecture so that each stage of the platform can evolve independently while preserving security, cost control, reproducibility, and operational maturity.

---

## Current Status

### Phase 1 — AWS Foundation

Status:

```text
COMPLETE
Release: v0.2.0-phase1
```

Implemented:

- AWS provider configuration
- Environment-based Terraform structure
- AWS Budget and cost guardrails
- IAM operational access
- Least-privilege Phase 1 IAM policy
- Remote Terraform state in Amazon S3
- Terraform state locking
- S3 state encryption
- S3 state versioning
- Public-access protection for Terraform state
- Multi-region AWS CloudTrail
- Management Events auditing
- CloudTrail log-file validation
- Dedicated S3 audit bucket
- S3 audit-log encryption
- S3 audit-log versioning
- S3 public-access protection
- Audit-log retention lifecycle
- Terraform environment outputs
- Infrastructure documentation
- Final drift-free validation
- Pull Request / merge / release tag

The AWS Foundation is designed to remain intentionally small while providing enough governance, auditability, security, and reproducibility to support the next platform phases.

---

## Architecture

```text
Developer Workstation
        |
        | AWS CLI login + MFA
        v
fii-platform-admin
        |
        v
fii-platform-admins
        |
        v
fii-platform-phase1-admin
        |
        +----------------------------+
        |                            |
        v                            v
Terraform                       AWS Budgets
        |
        +----------------------------+
        |
        v
Amazon S3 — Terraform State
        |
        +-- Encryption
        +-- Versioning
        +-- Public access blocked
        +-- State locking

AWS CloudTrail
        |
        +-- Multi-region trail
        +-- Global service events
        +-- Management Events
        +-- Read + Write events
        +-- Log-file validation
        |
        v
Amazon S3 — Audit Logs
        |
        +-- AES256 encryption
        +-- Versioning
        +-- Public access blocked
        +-- 365-day retention
```

---

## Directory Structure

```text
infrastructure/
└── terraform/
    ├── README.md
    │
    ├── bootstrap/
    │   ├── .terraform.lock.hcl
    │   ├── main.tf
    │   ├── outputs.tf
    │   ├── providers.tf
    │   ├── variables.tf
    │   └── versions.tf
    │
    ├── environments/
    │   └── dev/
    │       ├── .terraform.lock.hcl
    │       ├── backend.tf
    │       ├── main.tf
    │       ├── outputs.tf
    │       ├── providers.tf
    │       ├── terraform.tfvars.example
    │       ├── variables.tf
    │       └── versions.tf
    │
    └── modules/
        ├── budget/
        │   ├── main.tf
        │   ├── outputs.tf
        │   └── variables.tf
        │
        ├── iam/
        │   ├── main.tf
        │   ├── outputs.tf
        │   └── variables.tf
        │
        └── observability/
            ├── main.tf
            ├── outputs.tf
            └── variables.tf
```

---

## Terraform Roots

There are two Terraform root modules with different responsibilities.

### `bootstrap/`

Responsible only for provisioning the infrastructure required by the Terraform backend.

Current resource:

- S3 bucket for remote Terraform state

The bootstrap state is intentionally local because the remote backend cannot exist before the backend infrastructure itself is created.

Backend bucket:

```text
fii-data-ai-platform-tfstate-625685670804
```

The bucket is configured with:

- versioning
- AES256 server-side encryption
- public-access blocking
- `force_destroy = false`

The bootstrap state remains local by design.

This avoids the circular dependency of requiring the remote backend before the backend itself exists.

---

### `environments/dev/`

Primary Terraform root for the development environment.

It uses the S3 remote backend:

```text
bucket = fii-data-ai-platform-tfstate-625685670804
key    = environments/dev/terraform.tfstate
region = sa-east-1
```

State locking uses Terraform's native S3 lockfile support.

No DynamoDB locking table is required.

---

## AWS Region

Primary AWS region:

```text
sa-east-1
```

São Paulo is currently the platform's primary operating region.

CloudTrail is configured as a multi-region trail so that management activity performed outside the primary region is also audited.

---

## Modules

### Budget

Path:

```text
modules/budget
```

Provides the initial cost-governance controls for the platform.

Current development budget:

```text
fii-data-ai-platform-dev-monthly
```

Monthly threshold:

```text
USD 10
```

Notifications:

- Forecasted spend above 80%
- Actual spend above 100%

The budget is a financial guardrail and notification mechanism.

It does **not** automatically stop AWS resources when the threshold is exceeded.

---

## IAM

Path:

```text
modules/iam
```

Operational IAM user:

```text
fii-platform-admin
```

IAM group:

```text
fii-platform-admins
```

Terraform-managed customer policy:

```text
fii-platform-phase1-admin
```

The environment was initially bootstrapped using broader administrative access.

After the required Terraform resources and permissions were validated, the AWS-managed `AdministratorAccess` policy was removed from the normal operational path.

The current model follows a scoped Phase 1 permission strategy.

Permissions currently cover:

- Terraform remote-state access
- Audit S3 bucket administration
- AWS CloudTrail administration
- AWS Budget management
- Required IAM foundation operations
- STS caller identity validation

The policy will evolve incrementally as new platform phases introduce new AWS services.

Broad permanent administrator permissions are intentionally avoided.

---

## Least-Privilege Strategy

The IAM approach follows an incremental least-privilege model.

Bootstrap sequence:

```text
Temporary broader administrative capability
        |
        v
Terraform-managed IAM foundation
        |
        v
Custom Phase 1 policy
        |
        v
Validation
        |
        v
AdministratorAccess removed
```

The normal operational identity now relies on:

```text
fii-platform-phase1-admin
```

The AWS-managed `AdministratorAccess` policy is not part of the normal operational path.

Root access is retained only as an MFA-protected break-glass recovery mechanism.

---

## Observability and Audit

Path:

```text
modules/observability
```

CloudTrail trail:

```text
fii-data-ai-platform-dev
```

Audit bucket:

```text
fii-data-ai-platform-audit-625685670804
```

Current CloudTrail configuration:

- Multi-region trail
- Global service events enabled
- Management Events enabled
- Read and Write management events
- Data Events disabled
- Log-file validation enabled
- Logging enabled

Data Events are intentionally deferred because they are unnecessary for the current foundation and can introduce additional CloudTrail costs.

CloudWatch Logs integration is also deferred until application and data-processing workloads exist that require operational log aggregation and monitoring.

---

## Audit Bucket Security

The CloudTrail audit bucket is configured with:

```text
Versioning                Enabled
Encryption                AES256
Public access             Blocked
force_destroy             false
Current log retention     365 days
Noncurrent retention      365 days
```

The CloudTrail bucket policy restricts log delivery to the configured trail and uses `aws:SourceArn` to reduce confused-deputy risk.

Audit logs cannot be silently removed by a normal Terraform destroy while objects remain because `force_destroy` is disabled.

---

## Authentication

Local development uses modern AWS CLI browser authentication rather than permanent IAM access keys.

Typical authentication:

```powershell
aws login
```

Verify the active identity:

```powershell
aws sts get-caller-identity
```

Expected operational identity:

```text
arn:aws:iam::625685670804:user/fii-platform-admin
```

The root account is not used for normal Terraform operations.

Root access is protected with MFA and retained only as a break-glass recovery mechanism.

---

## Terraform Backend Authentication

The AWS CLI login session and the Terraform S3 backend may require temporary credentials to be exported into the current PowerShell environment.

Export the current AWS CLI session credentials:

```powershell
(aws configure export-credentials --format powershell) -join "`n" | Invoke-Expression
```

Do not commit, print, or share the resulting credential values.

Validate only that the environment variables exist:

```powershell
Test-Path Env:AWS_ACCESS_KEY_ID
Test-Path Env:AWS_SECRET_ACCESS_KEY
Test-Path Env:AWS_SESSION_TOKEN
```

Expected:

```text
True
True
True
```

---

## Expired Credential Recovery

Temporary AWS credentials eventually expire.

Typical symptom:

```text
ExpiredToken: The security token included in the request is expired
```

Clear stale environment credentials:

```powershell
Remove-Item Env:AWS_ACCESS_KEY_ID -ErrorAction SilentlyContinue
Remove-Item Env:AWS_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue
Remove-Item Env:AWS_SESSION_TOKEN -ErrorAction SilentlyContinue
```

Verify:

```powershell
Test-Path Env:AWS_ACCESS_KEY_ID
Test-Path Env:AWS_SECRET_ACCESS_KEY
Test-Path Env:AWS_SESSION_TOKEN
```

Expected:

```text
False
False
False
```

Then validate the AWS CLI session:

```powershell
aws sts get-caller-identity
```

If required:

```powershell
aws login
```

Finally export fresh temporary credentials again:

```powershell
(aws configure export-credentials --format powershell) -join "`n" | Invoke-Expression
```

---

## Terraform Workflow

Run Terraform from the environment root.

### Initialize

```powershell
terraform -chdir=infrastructure/terraform/environments/dev init
```

Run `init` again whenever modules or backend configuration change.

---

### Format

```powershell
terraform -chdir=infrastructure/terraform fmt -recursive
```

For CI-style validation:

```powershell
terraform -chdir=infrastructure/terraform fmt -check -recursive
```

---

### Validate

```powershell
terraform -chdir=infrastructure/terraform/environments/dev validate
```

Expected:

```text
Success! The configuration is valid.
```

---

### Plan

```powershell
terraform -chdir=infrastructure/terraform/environments/dev plan
```

Infrastructure should converge to:

```text
No changes. Your infrastructure matches the configuration.
```

Any unexpected destroy operation must be reviewed before applying.

---

### Apply

```powershell
terraform -chdir=infrastructure/terraform/environments/dev apply
```

Always review the execution plan before confirming an apply.

---

## Terraform Targeting

`-target` is not part of the normal deployment workflow.

It may be used only for exceptional bootstrap or recovery situations where one infrastructure dependency must exist before another resource can be safely managed.

Example encountered during Phase 1:

```text
IAM permissions
        |
        v
S3 audit bucket + CloudTrail
```

The IAM policy was updated first so that the operational Terraform identity could safely provision the observability resources.

After targeted operations, a complete Terraform plan must always be executed to verify that no changes were skipped.

---

## State Protection

Terraform state files must never be committed to Git.

The repository ignores:

```text
.terraform/
*.tfstate
*.tfstate.*
*.tfvars
```

The provider dependency lock file is committed:

```text
.terraform.lock.hcl
```

Environment examples may also be committed:

```text
terraform.tfvars.example
```

Real `terraform.tfvars` files remain local because they may contain environment-specific or sensitive values.

---

## Terraform Outputs

The `dev` environment exposes the main Phase 1 infrastructure identifiers:

```text
audit_bucket_arn
audit_bucket_name
budget_name
cloudtrail_arn
cloudtrail_name
iam_admin_group_name
```

Validated outputs:

```text
audit_bucket_name
= fii-data-ai-platform-audit-625685670804

budget_name
= fii-data-ai-platform-dev-monthly

cloudtrail_name
= fii-data-ai-platform-dev

iam_admin_group_name
= fii-platform-admins
```

Outputs can be inspected with:

```powershell
terraform -chdir=infrastructure/terraform/environments/dev output
```

---

## Cost Strategy

The AWS Foundation is intentionally designed to have very low idle cost.

Current cost profile:

| Component | Cost behavior |
|---|---|
| IAM | No direct charge |
| AWS Budget | No compute workload |
| Terraform | No AWS runtime cost |
| Terraform state S3 | Small storage/request cost |
| CloudTrail Management Events | First trail management-event copy |
| CloudTrail audit S3 | Small storage/request cost |
| CloudWatch Logs | Not enabled |
| CloudTrail Data Events | Not enabled |
| CloudTrail Lake | Not enabled |

Before adding any new AWS service, the project evaluates:

1. Cost while idle
2. Cost per request or execution
3. Free-tier implications
4. Cleanup behavior
5. Risk of forgotten resources
6. Whether the service is required in the current phase

The project intentionally avoids provisioning services only for architectural appearance.

---

## Phase Boundaries

### Phase 1 — AWS Foundation

Completed scope:

```text
Cost governance
IAM
Least privilege
Terraform backend
Remote state
State locking
Security foundation
Audit / CloudTrail
Protected audit storage
Terraform outputs
Infrastructure conventions
Documentation
```

Phase 1 is complete and released as:

```text
v0.2.0-phase1
```

---

### Phase 2 — Data Lake Foundation

Planned:

```text
Amazon S3 Data Lake

RAW
SILVER
GOLD

AWS Glue Data Catalog
Amazon Athena
```

The Data Lake is intentionally **not** part of Phase 1.

---

### Future Phases

Future phases may introduce:

- orchestration
- automated ingestion
- serverless processing
- data quality
- operational monitoring
- CI/CD
- analytics
- ML workflow automation
- generative AI
- recommendation workflows

Services will be introduced only when required by the platform architecture.

---

## Engineering Principles

The infrastructure follows these principles:

- Infrastructure as Code
- Least privilege
- MFA-protected operational access
- No permanent AWS CLI access keys
- Remote and versioned Terraform state
- State locking
- Encryption by default
- Public-access protection
- Explicit cost guardrails
- Centralized auditability
- Incremental architecture
- Small blast radius
- Reproducibility
- Controlled bootstrap and recovery
- Separation between platform phases
- No unnecessary always-on infrastructure

---

## Phase 1 Validation Evidence

The Phase 1 infrastructure has been validated through AWS CLI and Terraform.

Validated controls include:

```text
AWS Budget                         HEALTHY

IAM scoped operational access     OK
AdministratorAccess removed       OK

Terraform remote backend          OK
Terraform state locking           OK
S3 state versioning               Enabled
S3 state encryption               Enabled

CloudTrail logging                Enabled
CloudTrail multi-region           Enabled
Global service events             Enabled
Management Events                 Enabled
Read / Write Events               All
CloudTrail log validation         Enabled

Audit bucket versioning           Enabled
Audit bucket encryption           AES256
Audit bucket public access        Blocked
Audit log retention               365 days

Terraform drift                   None
```

Final formatting validation:

```text
terraform fmt -check -recursive
PASS
```

Final Terraform configuration validation:

```text
terraform validate
PASS
```

Final Terraform convergence:

```text
No changes. Your infrastructure matches the configuration.
```

---

## Phase 1 Closure

Phase 1 is officially closed.

Release:

```text
v0.2.0-phase1
```

Git / GitHub closure:

```text
Pull Request: #2

Merge commit:
fc97909753e85ced485c2119a35a793370e4dc71

Release tag:
v0.2.0-phase1

Terraform drift:
None

Working tree at closure:
Clean
```

Closure criteria:

```text
[x] AWS Foundation provisioned
[x] AWS provider configured
[x] Environment-based Terraform structure created
[x] Cost guardrails validated
[x] IAM operational identity validated
[x] MFA configured
[x] Temporary AWS CLI authentication validated
[x] Least-privilege IAM validated
[x] AdministratorAccess removed from normal operation
[x] Terraform remote state validated
[x] State migration completed
[x] State locking validated
[x] State encryption validated
[x] State versioning validated
[x] Public-access protection validated
[x] CloudTrail logging validated
[x] CloudTrail multi-region validated
[x] Management Events validated
[x] Log-file validation enabled
[x] Audit bucket encryption validated
[x] Audit bucket versioning validated
[x] Audit bucket public-access controls validated
[x] Audit retention validated
[x] Terraform outputs validated
[x] Infrastructure documentation completed
[x] terraform fmt -check passed
[x] terraform validate passed
[x] terraform plan converged with no changes
[x] Pull Request merged into main
[x] Release tag published
```

Phase 1 establishes the minimum production-oriented AWS foundation required to safely begin building the cloud Data Lake in Phase 2.

---

## Success Case

Phase 1 demonstrates the creation of a small but production-oriented AWS platform foundation using Terraform.

The implementation includes:

- reproducible infrastructure provisioning
- remote and protected Terraform state
- state locking
- versioned infrastructure state
- cost governance
- least-privilege operational access
- MFA-protected authentication
- temporary credentials instead of permanent CLI keys
- controlled administrative bootstrap
- centralized multi-region AWS audit logging
- protected audit-log storage
- explicit retention
- drift validation
- documented recovery procedures

The objective is not to reproduce a large enterprise landing zone.

The objective is to implement the engineering controls that are relevant to an independent data platform while keeping operational complexity and cloud cost proportional to the project.

---

## Next Phase

The next infrastructure milestone is:

```text
Phase 2 — Data Lake Foundation
```

Initial planned services:

```text
Amazon S3
AWS Glue Data Catalog
Amazon Athena
```

Logical layers:

```text
RAW
SILVER
GOLD
```

The Phase 2 architecture will preserve the governance, semantic and reproducibility guarantees already validated during the local platform phase.