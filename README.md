# FII Data & AI Platform

A production-inspired **Data Engineering, Data Architecture, Machine Learning and Cloud Data Platform for Brazilian Real Estate Investment Funds (FIIs)**.

The project is being developed incrementally, starting with a trustworthy local data foundation and evolving toward an independent AWS-based production-oriented platform.

The engineering strategy prioritizes:

```text
trustworthy data
        >
complex models
        >
unnecessary infrastructure
```

The platform emphasizes explicit contracts, corporate-action governance, temporal correctness, observability, reproducibility, infrastructure as code, cloud cost control, security and auditability.

---

## Current Status

```text
Phase 0 — Local Data Foundation        ✅ COMPLETE
Release: v0.1.0-phase0

Phase 1 — AWS Foundation               ✅ COMPLETE
Release: v0.2.0-phase1

Phase 2 — Data Lake Foundation         🚧 NEXT
```

Current platform evolution:

```text
Local governed data platform
        |
        v
AWS secure foundation
        |
        v
Cloud Data Lake
        |
        v
Managed processing / orchestration
        |
        v
Analytics / ML / AI
```

---

# Project Goals

The long-term objective is to build an independent cloud-native data and AI platform for Brazilian Real Estate Investment Funds.

Core goals:

- Ingest and preserve FII market and fund data from approved sources.
- Build reproducible RAW, Silver and Gold data layers.
- Govern corporate actions instead of treating price discontinuities as automatic truth.
- Produce economically meaningful price and return histories.
- Enforce explicit data contracts across analytical and ML datasets.
- Build leakage-aware training datasets and temporal splits.
- Evaluate models through both holdout validation and purged walk-forward experiments.
- Add executable observability and controlled-failure evidence.
- Document architecture, lineage, contracts and closure criteria.
- Run the platform on a secure, reproducible and cost-controlled AWS foundation.
- Build a cloud Data Lake using managed AWS services.
- Support future Analytics, portfolio workflows, DARF automation and Generative AI / Agents.

---

# Engineering Philosophy

The central engineering principle is:

```text
trustworthy data
        >
complex models
```

The project does not start with AI.

It starts with:

```text
source reliability
      |
      v
data contracts
      |
      v
governance
      |
      v
temporal correctness
      |
      v
observability
      |
      v
reproducibility
      |
      v
cloud foundation
      |
      v
analytics / ML / AI
```

The goal is not to maximize model metrics before the underlying data platform is trustworthy.

The platform must produce data that is:

```text
traceable
governed
semantically consistent
temporally correct
observable
reproducible
auditable
cost-aware
```

---

# Platform Roadmap

```text
Phase 0
LOCAL DATA FOUNDATION
        |
        v
Phase 1
AWS FOUNDATION
        |
        v
Phase 2
DATA LAKE FOUNDATION
        |
        v
Phase 3
PIPELINES / ORCHESTRATION
        |
        v
Phase 4
ANALYTICS / ML PLATFORM
        |
        v
Phase 5
AI / PRODUCT CAPABILITIES
```

The exact boundaries may evolve as architectural decisions are validated.

---

# Releases

## Phase 0

```text
v0.1.0-phase0
```

Scope:

```text
Local Data Engineering
Data Governance
Corporate Actions
Gold Analytics
Data Quality
ML Dataset Engineering
Temporal Validation
Local Observability
Controlled Failure
Documentation
```

---

## Phase 1

```text
v0.2.0-phase1
```

Scope:

```text
AWS Foundation
Terraform
Remote State
State Locking
IAM
Least Privilege
Cost Guardrails
CloudTrail
Audit Logging
Cloud Security Controls
Infrastructure Documentation
```

---

# Architecture Overview

The platform currently has two validated architectural foundations.

```text
                        EXTERNAL SOURCES
                   B3 / CVM / Funds Explorer
                              |
                              v
                             RAW
                              |
                              v
                           SILVER
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
      Gold Analytics                     Gold Quality
             |                                 |
             +----------------+----------------+
                              |
                              v
                           Gold ML
                              |
                       +------+------+
                       |             |
                       v             v
                   Baseline     Walk-Forward
                              |
                              v
                    Local Observability
                              |
                              v
                     AWS Foundation
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
        Terraform          Budgets         CloudTrail
             |                                  |
             v                                  v
       Remote State                       Audit S3 Bucket
             |
             v
        Phase 2 Data Lake
```

The complete architecture documentation is available under:

```text
docs/architecture/
```

AWS infrastructure documentation:

```text
infrastructure/terraform/README.md
```

---

# Phase 0 — Local Data Foundation

Phase 0 proved that the platform can produce trustworthy local analytical and ML-ready data before cloud migration.

It evolved beyond a simple repository bootstrap and became a complete local proof of the core platform architecture.

---

# Data Sources

## B3

Primary source for market trading data.

Validated example:

```text
Trading date: 2026-08-27
Automated download: OK
Source package: SPRE260827.zip
Internal format: XML
Parsed records: 50,390
```

Core fields include:

```text
trade_date
ticker
instrument_id
instrument_id_type
market
open_price
low_price
high_price
average_price
close_price
trades_quantity
```

---

## CVM

Official source for fund registration and classification.

Validated parser result:

```text
Total classes: 36,606
FII classes: 1,528
```

---

## Funds Explorer

Complementary source used for enrichment of the FII universe.

It is treated as auxiliary and does not replace official B3/CVM identity or governance.

---

# Data Layers

## RAW

Purpose:

```text
preserve source data
support replay
maintain traceability
```

Example:

```text
data/raw/b3/year=2026/month=08/day=27/
```

---

## Silver

Purpose:

```text
parse
type
normalize
standardize
```

Validated market base:

```text
Sessions: 250
Period: 2025-08-29 -> 2026-08-28
Rows: 68,747
Tickers: 372
```

---

## Gold

The Gold layer is divided into:

```text
analytics/
quality/
ml/
ai/
```

---

# Corporate Action Governance

Corporate actions are treated as governed economic events.

The platform explicitly separates detection from decision:

```text
Price Discontinuity Detector
            |
            v
         Candidate
            |
            v
Corporate Action Registry
            |
        +---+---+
        |       |
        v       v
      Review  Decision
        |       |
        +---+---+
            |
            v
     Adjusted Prices
```

Core rule:

```text
DETECTOR != DECISION
```

A large price move is not automatically converted into a confirmed corporate action.

---

## Price Discontinuities v5

Validated state:

```text
Candidates: 79
Tickers: 38

REJECTED:       59
CONFIRMED:      16
NOT_APPLICABLE: 4
PENDING:         0
```

---

## Corporate Action Registry v2

Validated state:

```text
Rows: 79
Fields: 20
Confirmed actions: 16
Pending: 0
```

---

## Corporate Action Adjusted Prices v3

Validated state:

```text
Rows: 68,747
Tickers: 372
Sessions: 250
DQ issues: 0

Confirmed actions: 16
Structural actions: 5
Economic actions: 11
In-kind actions: 1
Pending actions: 0
```

Semantic contract:

```text
price_semantics
= STRUCTURALLY_ADJUSTED_PRICE

return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

Economic return:

```text
daily_return_economic =

(close_adjusted + total_economic_value_adjusted)
/
previous_close_adjusted
- 1
```

---

# Gold Analytics

## Price History v3

Validated state:

```text
Rows: 68,747
Tickers: 372
Sessions: 250
Duplicates: 0
```

This is the governed time-series upstream for feature engineering.

---

## Daily Snapshot

The project currently contains two historical physical paths:

```text
data/gold/analytics/fii_daily_snapshot/...
data/gold/fii_daily_snapshot/...
```

Phase 0 deliberately does not silently declare one canonical.

Canonicalization remains an explicit architectural decision for future cleanup.

---

# Gold Quality

## Price Quality v2

Validated state:

```text
Rows: 68,747
Tickers: 372

PASS:   68,592
REVIEW:    155
FAIL:        0
```

Confirmed corporate actions are not automatically treated as data-quality failures.

---

## Corporate Action Review Queue

Validated state:

```text
Rows: 0
Pending cases: 0
```

An empty queue is valid by contract.

---

# Gold ML

## Features v7

Validated state:

```text
Rows: 68,747
Tickers: 372
Feature-ready rows: 61,913
```

Feature windows:

```text
5
10
20
```

Corporate-action feature policy:

```text
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

The economic effect is embedded in returns rather than injected as direct event payload.

---

# Feature Contract v3

Only 18 governed features are allowed into models:

```text
daily_return
return_5d
volatility_5d
price_to_ma5

return_10d
volatility_10d
price_to_ma10

return_20d
volatility_20d
price_to_ma20

return_spread_5d_10d
ma_ratio_5_10
volatility_ratio_5d_10d
trades_ratio_5d_10d

return_spread_10d_20d
ma_ratio_10_20
volatility_ratio_10d_20d
trades_ratio_10d_20d
```

This prevents accidental model consumption of non-governed columns.

---

# ML Eligibility v3

Validated state:

```text
Rows: 57,998
Tickers: 319
Eligible: 57,441
Ineligible: 557
DQ issues: 0
```

Contract:

```text
lookback = 21 observations
target = exact global B3 T+5
```

---

# Training Dataset v4

Validated state:

```text
Rows: 57,998
Tickers: 319
Duplicates: 0
Target nulls: 0
Target nonfinite: 0
Invalid target chronology: 0
```

Target:

```text
target_return_next_5d
```

Target semantics:

```text
target_horizon = 5
target_horizon_semantics = GLOBAL_B3_TRADING_DAYS
target_return_semantics = COMPOUNDED_DAILY_RETURN_ECONOMIC
```

The target uses the economic return curve, not a price-only shortcut.

---

# Temporal Split v3

Validated split:

```text
TRAIN
51,207 rows

VALIDATION
1,235 rows

TEST
2,501 rows
```

Temporal rules:

```text
train.target_date < validation.feature_date
validation.target_date < test.feature_date
overlap = 0
```

Final holdout policy:

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

---

# Baseline v5

Models:

```text
DummyRegressor
LinearRegression
RandomForestRegressor
```

Policy:

```text
TRAIN -> VALIDATION
TEST untouched
```

Linear Regression produced the best regression result in the validated validation window.

This is an experimental result, not an operational health contract.

---

# Walk-Forward v1

Policy:

```text
EXPANDING_WINDOW_PURGED
```

Validated structure:

```text
12 folds
5 validation sessions per fold
3 models
36 metric rows
18 governed features
```

Final TEST boundary:

```text
2026-08-10
```

TEST protection:

```text
test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

Aggregate results:

| Model | Mean MAE | Mean RMSE | Mean R² | Directional Accuracy | Directional Lift |
|---|---:|---:|---:|---:|---:|
| Dummy Mean | 1.9131% | 3.2459% | -0.035719 | 57.46% | 0.00 pp |
| Linear Regression | 1.8752% | 3.1594% | 0.017932 | 58.23% | +0.78 pp |
| Random Forest | 1.9476% | 3.2958% | -0.071450 | 55.32% | -2.14 pp |

Linear Regression was the best aggregate candidate among the three evaluated models.

The signal is modest and is not presented as a production trading model.

---

# Local Observability

Phase 0 implements executable local observability.

Components:

```text
Pipeline Health v3
Controlled Failure v1
```

---

## Pipeline Health v3

Validated command:

```powershell
python -m src.observability.pipeline_health.builder --reference-date 2026-09-01
```

Validated result:

```text
Overall status: PASS
Datasets monitored: 12
Checks PASS: 212
Checks WARN: 0
Checks FAIL: 0
```

Freshness semantics:

```text
DATA_DATE
TARGET_DATE
EVENT_DRIVEN
HISTORICAL_SPLIT
HISTORICAL_EXPERIMENT
```

The health layer checks:

- artifact existence;
- readability;
- schema;
- duplicates;
- dates;
- freshness;
- versions;
- economic semantics;
- cross-dataset reconciliation;
- split integrity;
- purge;
- holdout protection;
- Walk-Forward integrity;
- metric reconciliation.

It does **not** require any model to achieve an arbitrary performance threshold.

---

# Controlled Failure v1

The project also proves that the monitor can fail correctly.

Command:

```powershell
python -m src.observability.controlled_failure.runner
```

Controlled scenario:

```text
features_duplicate_key
```

Validated result:

```text
Original rows: 68,747
Corrupted rows: 68,748
Injected rows: 1

Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1

Official dataset unchanged: True
Temporary artifact removed: True

Test status: PASS
```

Interpretation:

```text
temporary corrupted dataset -> FAIL
controlled failure test      -> PASS
```

The real detection logic catches the defect without modifying the official Gold dataset.

---

# Phase 0 Closure

Phase 0 is officially complete.

Release:

```text
v0.1.0-phase0
```

Technical implementation:

```text
[x] B3 ingestion
[x] CVM parsing
[x] RAW layer
[x] Silver layer
[x] Gold Analytics
[x] Corporate Action Governance
[x] Price Quality
[x] Economic Price History
[x] Feature Engineering
[x] ML Eligibility
[x] Economic T+5 Training Target
[x] Purged Temporal Split
[x] Governed Feature Contract
[x] Baseline Models
[x] Purged Walk-Forward
[x] Pipeline Health
[x] Controlled Failure
[x] Data Lineage
[x] Data Contracts
[x] Architecture Documentation
[x] Observability Evidence
[x] Phase 0 Closure Documentation
[x] Final README
[x] Final repository review
[x] Push final branch
[x] Pull Request
[x] Merge into main
[x] Release tag
```

Closure documentation:

```text
docs/phase-0/phase-0-closure.md
```

---

# Phase 1 — AWS Foundation

Phase 1 moved the project from a local-only platform toward an independently operated AWS cloud foundation.

The objective was **not** to build the Data Lake yet.

The objective was to establish the AWS environment required to safely support future data-platform workloads.

Release:

```text
v0.2.0-phase1
```

---

# Phase 1 Architecture

```text
Developer Workstation
        |
        | AWS CLI browser login + MFA
        v
fii-platform-admin
        |
        v
fii-platform-admins
        |
        v
fii-platform-phase1-admin
        |
        +------------------------------+
        |              |               |
        v              v               v
    Terraform      AWS Budgets     CloudTrail
        |                              |
        v                              v
Remote State S3                  Audit S3 Bucket
        |
        +-- Encryption
        +-- Versioning
        +-- Public access blocked
        +-- State locking
```

CloudTrail:

```text
Multi-region
Global service events
Management Events
Read + Write
Log-file validation
```

Audit bucket:

```text
AES256 encryption
Versioning enabled
Public access blocked
365-day lifecycle
force_destroy = false
```

---

# Phase 1 Terraform Structure

```text
infrastructure/
└── terraform/
    ├── README.md
    │
    ├── bootstrap/
    │   ├── main.tf
    │   ├── outputs.tf
    │   ├── providers.tf
    │   ├── variables.tf
    │   └── versions.tf
    │
    ├── environments/
    │   └── dev/
    │       ├── backend.tf
    │       ├── main.tf
    │       ├── outputs.tf
    │       ├── providers.tf
    │       ├── terraform.tfvars.example
    │       ├── variables.tf
    │       ├── versions.tf
    │       └── .terraform.lock.hcl
    │
    └── modules/
        ├── budget/
        ├── iam/
        └── observability/
```

Detailed Terraform documentation:

```text
infrastructure/terraform/README.md
```

---

# Terraform Backend

Terraform remote state is stored in:

```text
fii-data-ai-platform-tfstate-625685670804
```

Environment state:

```text
environments/dev/terraform.tfstate
```

Backend protections:

```text
Versioning                  Enabled
Encryption                  AES256
Public access               Blocked
State locking               Enabled
force_destroy               false
```

The bootstrap Terraform state remains local intentionally because the backend infrastructure must exist before Terraform can migrate its own state.

---

# AWS Region

Primary operating region:

```text
sa-east-1
```

São Paulo is the platform's primary region.

CloudTrail is configured as multi-region so that AWS management events outside the primary region are also audited.

---

# Cost Governance

AWS Budget:

```text
fii-data-ai-platform-dev-monthly
```

Monthly threshold:

```text
USD 10
```

Notifications:

```text
Forecasted spend > 80%
Actual spend > 100%
```

The budget provides visibility and alerts.

It does not automatically stop AWS resources.

---

# IAM Foundation

Operational IAM user:

```text
fii-platform-admin
```

Operational IAM group:

```text
fii-platform-admins
```

Terraform-managed customer policy:

```text
fii-platform-phase1-admin
```

Authentication model:

```text
AWS CLI browser login
MFA
temporary credentials
no permanent CLI access keys
```

The AWS-managed:

```text
AdministratorAccess
```

was used only during controlled bootstrap/recovery and was removed from normal operation after the custom policy was validated.

The normal operational path uses scoped permissions.

---

# Least Privilege

The Phase 1 IAM policy currently covers only the foundation services required by the platform:

```text
Terraform backend S3
Audit bucket S3
AWS CloudTrail
AWS Budgets
IAM foundation lifecycle
STS caller identity
```

The policy will evolve as later phases introduce new services.

Broad permanent administrative permissions are intentionally avoided.

---

# Cloud Audit Foundation

CloudTrail trail:

```text
fii-data-ai-platform-dev
```

Validated configuration:

```text
Logging                       Enabled
Multi-region                  Enabled
Global service events         Enabled
Management Events             Enabled
Read / Write                  All
Data Events                   Disabled
Log-file validation           Enabled
Organization trail            Disabled
```

Data Events were intentionally deferred because they are not required by the AWS Foundation and can introduce additional CloudTrail cost.

---

# CloudTrail Audit Bucket

Bucket:

```text
fii-data-ai-platform-audit-625685670804
```

Validated controls:

```text
Versioning                  Enabled
Encryption                  AES256
Public access               Blocked
Lifecycle                   365 days
Noncurrent retention        365 days
force_destroy               false
```

The bucket policy restricts CloudTrail delivery to the configured trail.

---

# Phase 1 Terraform Outputs

The development environment exposes:

```text
audit_bucket_arn
audit_bucket_name
budget_name
cloudtrail_arn
cloudtrail_name
iam_admin_group_name
```

Validated values:

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

---

# Phase 1 Validation Evidence

Final Terraform validation:

```text
terraform fmt -check -recursive
PASS

terraform validate
PASS

terraform plan
No changes. Your infrastructure matches the configuration.
```

Validated AWS controls:

```text
IAM scoped operational access       PASS
AdministratorAccess removed         PASS

AWS Budget                          HEALTHY

Terraform remote backend            PASS
Terraform state locking             PASS
Terraform state encryption          PASS
Terraform state versioning          PASS

CloudTrail logging                  Enabled
CloudTrail multi-region             Enabled
Global service events               Enabled
Management Events                   Enabled
Read + Write Events                 All
Log-file validation                 Enabled

Audit bucket encryption             AES256
Audit bucket versioning             Enabled
Audit bucket public access          Blocked
Audit lifecycle                     365 days

Terraform drift                     None
```

---

# Phase 1 Closure

Phase 1 is officially complete.

```text
[x] Terraform AWS foundation
[x] Environment-based Terraform structure
[x] AWS provider configuration
[x] AWS Budget guardrails
[x] IAM operational identity
[x] MFA
[x] Temporary AWS CLI authentication
[x] Custom least-privilege IAM policy
[x] AdministratorAccess removed from normal operation
[x] Terraform S3 backend
[x] State migration
[x] State encryption
[x] State versioning
[x] State locking
[x] S3 public-access protection
[x] Multi-region CloudTrail
[x] Management Events
[x] Log-file validation
[x] Protected audit bucket
[x] Audit retention lifecycle
[x] Terraform outputs
[x] Terraform documentation
[x] Final fmt validation
[x] Final Terraform validation
[x] Drift-free plan
[x] Pull Request
[x] Merge into main
[x] Release tag
```

Release:

```text
v0.2.0-phase1
```

---

# Phase 1 Success Case

Phase 1 demonstrates the creation of a small but production-oriented AWS platform foundation using Terraform.

The foundation provides:

- reproducible infrastructure;
- remote Terraform state;
- state locking;
- versioned infrastructure state;
- cloud cost governance;
- least-privilege operational access;
- MFA-protected authentication;
- controlled administrative bootstrap;
- centralized multi-region auditing;
- protected audit-log storage;
- explicit retention;
- infrastructure drift detection.

The architectural goal is not to reproduce a large enterprise landing zone.

The goal is to implement the controls relevant to an independent production-oriented data platform while keeping operational complexity and cloud cost proportional to the project.

---

# Repository Structure

```text
fii-data-ai-platform/
│
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── Makefile
├── pyproject.toml
├── requirements-dev.txt
│
├── config/
│   └── corporate_actions/
│
├── data/
│   ├── raw/
│   ├── silver/
│   ├── gold/
│   │   ├── analytics/
│   │   ├── quality/
│   │   ├── ml/
│   │   └── ai/
│   └── observability/
│
├── docs/
│   ├── architecture/
│   ├── data-contracts/
│   ├── lineage/
│   ├── observability/
│   │   └── evidence/
│   └── phase-0/
│
├── src/
│   ├── ingestion/
│   ├── transformation/
│   ├── analytics/
│   ├── quality/
│   ├── ml/
│   └── observability/
│
├── tests/
├── sql/
├── docker/
│
├── infrastructure/
│   └── terraform/
│       ├── bootstrap/
│       ├── environments/
│       │   └── dev/
│       └── modules/
│           ├── budget/
│           ├── iam/
│           └── observability/
│
└── .github/
```

Some scaffold directories are intentionally retained for later phases.

---

# Technical Documentation

## Architecture

```text
docs/architecture/

├── architecture-overview.md
└── data-platform-architecture.md
```

---

## Lineage

```text
docs/lineage/

├── data-lineage.md
└── pipeline-lineage.md
```

---

## Data Contracts

```text
docs/data-contracts/

├── silver-contracts.md
├── gold-analytics-contracts.md
└── gold-ml-contracts.md
```

---

## Observability

```text
docs/observability/

├── observability-overview.md
├── controlled-failure.md
└── evidence/
    └── phase-0-observability-evidence.md
```

---

## Phase 0 Closure

```text
docs/phase-0/

└── phase-0-closure.md
```

---

## AWS Infrastructure

```text
infrastructure/terraform/

└── README.md
```

The Terraform README contains the detailed AWS Foundation documentation, including authentication, backend bootstrap, IAM, cost governance, audit architecture, credential recovery and Terraform operational workflow.

---

# Versioned Contracts

Validated versions at the end of Phase 0:

```text
Price Discontinuities             v5
Corporate Action Registry         v2
Corporate Action Adjusted Prices  v3
Price Quality                     v2
Price History                     v3
Features                          v7
ML Eligibility                    v3
Training Dataset                  v4
Temporal Split                    v3
Feature Contract                  v3
Baseline                          v5
Walk-Forward                      v1
Pipeline Health                   v3
Controlled Failure               v1
```

Validated upstream components are treated as frozen unless a real bug, contract inconsistency or semantic error is discovered.

---

# Local Development

Environment used during the local platform phase:

```text
Windows
PowerShell
VS Code
Python 3.13
Git
Parquet
```

Create an environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Run available tests:

```powershell
pytest -q
```

Run observability:

```powershell
python -m src.observability.pipeline_health.builder --reference-date 2026-09-01
```

Run controlled failure:

```powershell
python -m src.observability.controlled_failure.runner
```

---

# AWS Development

Primary region:

```text
sa-east-1
```

Authenticate:

```powershell
aws login
```

Verify identity:

```powershell
aws sts get-caller-identity
```

Expected operational identity:

```text
arn:aws:iam::625685670804:user/fii-platform-admin
```

Terraform may require the temporary AWS CLI session credentials to be exported:

```powershell
(aws configure export-credentials --format powershell) -join "`n" | Invoke-Expression
```

Do not print, share or commit the exported credentials.

---

# Terraform Workflow

Initialize:

```powershell
terraform -chdir=infrastructure/terraform/environments/dev init
```

Format:

```powershell
terraform -chdir=infrastructure/terraform fmt -recursive
```

Validate formatting:

```powershell
terraform -chdir=infrastructure/terraform fmt -check -recursive
```

Validate configuration:

```powershell
terraform -chdir=infrastructure/terraform/environments/dev validate
```

Plan:

```powershell
terraform -chdir=infrastructure/terraform/environments/dev plan
```

Expected stable state:

```text
No changes. Your infrastructure matches the configuration.
```

Apply:

```powershell
terraform -chdir=infrastructure/terraform/environments/dev apply
```

Every apply must be reviewed before confirmation.

---

# Expired AWS Credentials

Temporary AWS credentials expire.

Typical error:

```text
ExpiredToken
The security token included in the request is expired
```

Clear stale PowerShell credentials:

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

Validate the AWS CLI session:

```powershell
aws sts get-caller-identity
```

If required:

```powershell
aws login
```

Export fresh credentials:

```powershell
(aws configure export-credentials --format powershell) -join "`n" | Invoke-Expression
```

---

# Cost Strategy

The platform follows a cost-aware cloud engineering strategy.

AWS resources are introduced only when justified by the current platform phase.

Every new AWS service is evaluated for:

```text
idle cost
request cost
execution cost
storage cost
free-tier implications
cleanup behavior
resource lifecycle
forgotten-resource risk
business / architectural necessity
```

Current AWS Foundation cost profile:

| Component | Cost behavior |
|---|---|
| IAM | No direct charge |
| Terraform | No AWS runtime charge |
| AWS Budget | Cost governance only |
| Terraform state S3 | Small storage/request cost |
| CloudTrail Management Events | First management-event trail copy |
| Audit S3 | Small storage/request cost |
| CloudWatch Logs | Not enabled |
| CloudTrail Data Events | Not enabled |
| CloudTrail Lake | Not enabled |

The project intentionally avoids provisioning infrastructure only for architectural appearance.

---

# Security Principles

The AWS foundation follows these principles:

```text
least privilege
MFA
temporary credentials
no permanent AWS CLI access keys
remote Terraform state
state locking
encryption by default
versioning
public-access blocking
auditability
controlled bootstrap
break-glass root access
no unnecessary administrator permissions
```

Root access is not part of the normal operational path.

It is retained only as an MFA-protected recovery mechanism.

---

# Architecture Freeze Rule

Validated upstream components are treated as frozen.

They should only be reopened for:

```text
real bug
contract inconsistency
proven semantic error
```

Optional improvements or experiments should move to backlog, downstream layers or new versions.

This principle applies to both data-platform components and infrastructure components.

---

# Phase 2 — Data Lake Foundation

Phase 2 is the next active platform phase.

Primary scope:

```text
Amazon S3 Data Lake

RAW
SILVER
GOLD

AWS Glue Data Catalog
Amazon Athena
```

Phase 2 will migrate the logical local data architecture toward cloud-native storage and metadata management.

The objective is to preserve the semantic and governance guarantees already validated during Phase 0.

Planned architecture:

```text
Sources
   |
   v
S3 RAW
   |
   v
S3 SILVER
   |
   v
S3 GOLD
   |
   +-------------------+
   |                   |
   v                   v
Glue Data Catalog    Athena
```

The exact physical architecture will be validated incrementally.

---

# Future Platform Evolution

Potential later phases may introduce:

```text
automated ingestion
orchestration
managed processing
data quality automation
CloudWatch operational monitoring
CI/CD
analytics consumption
ML workflow automation
model registry
API / serving layer
portfolio analytics
portfolio rebalancing support
DARF calculation workflows
Generative AI
RAG
Agents
natural-language data access
```

These are roadmap capabilities and are not presented as currently implemented functionality.

---

# Product Direction

The platform may eventually support:

```text
FII analytics
portfolio analysis
risk analysis
fund comparison
portfolio rebalancing assistance
capital-gain calculation
DARF workflow support
AI-assisted investment research
natural-language data exploration
```

Any financial or tax-related functionality must be independently validated before real-world use.

---

# Success Case Narrative

The project demonstrates the progressive construction of a data and AI platform from first principles.

## Phase 0

Proved:

```text
data ingestion
data governance
semantic contracts
economic return correctness
data quality
ML dataset engineering
temporal validation
local observability
controlled failure
```

## Phase 1

Proved:

```text
Infrastructure as Code
AWS foundation
least privilege
cost governance
remote Terraform state
state locking
cloud auditability
secure S3 configuration
multi-region CloudTrail
drift-free infrastructure
```

The project deliberately evolves from trustworthy data toward cloud infrastructure, analytics, ML and AI rather than starting with AI before the underlying platform is reliable.

---

# Project Milestones

```text
v0.1.0-phase0
Local Data Foundation
COMPLETE
        |
        v
v0.2.0-phase1
AWS Foundation
COMPLETE
        |
        v
Phase 2
Data Lake Foundation
NEXT
```

---

# Disclaimer

This project is educational, technical and experimental.

It does not provide investment advice, tax advice or personalized financial recommendations.

Any future portfolio, recommendation or DARF-related functionality must be independently validated before real-world use.