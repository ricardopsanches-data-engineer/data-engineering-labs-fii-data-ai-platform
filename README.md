# FII Data & AI Platform

A production-inspired Data Engineering, Data Architecture, Machine Learning and Cloud Data Platform for Brazilian Real Estate Investment Funds (FIIs).

The project evolves incrementally from a trustworthy local data foundation toward a secure, governed and cost-aware AWS platform for analytics, machine learning and future AI capabilities.

The engineering strategy prioritizes:

```text
trustworthy data
>
complex models
>
unnecessary infrastructure
```

The platform emphasizes:

- explicit data contracts;
- corporate-action governance;
- temporal correctness;
- reproducibility;
- idempotency;
- observability;
- infrastructure as code;
- cloud security;
- cost control;
- auditability.

---

# Current Status

```text
Phase 0 - Local Data Foundation              COMPLETE
Release: v0.1.0-phase0

Phase 1 - AWS Foundation                     COMPLETE
Release: v0.2.0-phase1

Phase 2 - AWS Data Lake Foundation           COMPLETE

Phase 3 - AWS Gold Automation                COMPLETE
Release: v0.4.0-phase3

Phase 4 - AWS Analytics & AI Foundation      IN CLOSURE
```

Phase 4 technical implementation and AWS validation are complete.

The remaining closure workflow is:

```text
documentation
-> feature branch push
-> Pull Request
-> review/checks
-> merge into main
-> release tag
-> branch cleanup
```

Phase 4 must not be considered officially closed until this GitHub release workflow is complete.

---

# Platform Evolution

```text
Local Governed Data Platform
        |
        v
AWS Secure Foundation
        |
        v
AWS Data Lake
        |
        v
Automated Serverless Pipelines
        |
        v
Gold Analytics
        |
        v
Gold ML Foundation
        |
        v
Analytics / ML / AI
```

---

# Project Goals

The long-term objective is to build an independent cloud-native data and AI platform for Brazilian Real Estate Investment Funds.

Core goals:

- ingest and preserve market and fund data from governed sources;
- build reproducible RAW, Silver and Gold layers;
- govern corporate actions instead of treating price discontinuities as automatic truth;
- produce economically meaningful price and return histories;
- enforce explicit data contracts;
- build leakage-aware ML datasets;
- protect final temporal holdouts;
- evaluate models through purged temporal validation;
- provide executable observability;
- maintain reproducible infrastructure through Terraform;
- operate under explicit AWS cost controls;
- support future analytics, portfolio workflows, DARF automation and AI capabilities.

---

# Engineering Philosophy

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

Validated upstream components are treated as frozen unless a real bug, contract inconsistency or proven semantic error is discovered.

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
AWS DATA LAKE FOUNDATION
        |
        v
Phase 3
AWS GOLD AUTOMATION
        |
        v
Phase 4
AWS ANALYTICS & AI FOUNDATION
        |
        v
Future Phases
AI / PRODUCT CAPABILITIES
```

---

# Architecture Overview

The current platform combines a governed local data and ML foundation with a serverless AWS analytical architecture.

```text
External Sources
      |
      v
B3 / CVM
      |
      v
AWS Ingestion
      |
      v
S3 RAW
      |
      v
Serverless Processing
      |
      v
S3 SILVER
      |
      v
Governed GOLD
      |
      +------------------------------+
      |                              |
      v                              v
Gold Analytics                   Gold ML
      |                              |
      v                              v
Glue Catalog                    Features
      |                              |
      v                              v
Athena                       ML Eligibility
                                     |
                                     v
                              Training Dataset
                                     |
                                     v
                               Temporal Split
                                     |
                                     v
                                Walk-Forward
```

Infrastructure and operational controls:

```text
Terraform
IAM
S3 Versioning
S3 Encryption
Public Access Block
Lifecycle Policies
AWS Budgets
CloudTrail
CloudWatch
Athena Scan Limits
Logical Content Hashing
```

---

# Data Sources

## B3

Primary source for market trading data.

Validated ingestion includes B3 daily market packages and instrument information.

Core market fields include:

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

## CVM

Official source for Brazilian fund registration and classification.

Validated local reference:

```text
Total fund classes: 36,606
FII classes:         1,528
```

Complementary sources may be used for enrichment but do not replace official B3/CVM identity or governance.

---

# Data Lake

Primary AWS region:

```text
sa-east-1
```

Development Data Lake:

```text
fii-data-ai-platform-dev-datalake-625685670804
```

Logical layers:

```text
RAW
SILVER
GOLD
```

Gold is organized into analytical and ML domains:

```text
gold/
|-- analytics/
|-- fii-master/
`-- ml/
```

---

# RAW Layer

RAW preserves source artifacts for replay, traceability and controlled reprocessing.

Examples:

```text
raw/b3/
raw/cvm/
raw/b3-instruments/
```

Operational controls include:

```text
SHA-256 fingerprinting
S3 Versioning
idempotent upload
silent overwrite protection
```

Current lifecycle policy:

```text
current RAW objects:
expire after 30 days

noncurrent versions:
expire after 7 days

incomplete multipart uploads:
abort after 7 days
```

---

# Silver Layer

Silver transforms source-specific RAW data into typed, normalized and reusable datasets.

Current catalog includes:

```text
b3_trades
b3_instruments
cvm_fund_classes
```

Silver datasets are stored in S3 and registered in the AWS Glue Data Catalog.

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
            v
          Review
            |
            v
         Decision
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

# Gold Analytics

Phase 4 publishes the following analytical datasets to AWS:

```text
fii_daily_snapshot
fii_price_history
fii_corporate_action_adjusted_prices
fii_price_discontinuities
```

## FII Daily Snapshot

Validated state:

```text
267 rows
20 columns
reference date: 2026-08-28
```

S3 strategy:

```text
year/month/day
```

## Price History v3

Validated state:

```text
68,747 rows
90 columns
period: 2025-08-29 -> 2026-08-28
```

This is the governed time-series upstream for ML feature engineering.

## Corporate Action Adjusted Prices v3

Validated state:

```text
68,747 rows
57 columns
```

Price semantics:

```text
STRUCTURALLY_ADJUSTED_PRICE
```

Return semantics:

```text
COMPOUNDED_DAILY_RETURN_ECONOMIC
```

Corporate-action value semantics:

```text
TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

## Price Discontinuities v5

Validated state:

```text
79 rows
44 columns
```

The detector generates candidates while the governed registry determines their interpretation.

---

# Gold ML

The governed ML chain is:

```text
Price History
    |
    v
Features
    |
    v
ML Eligibility
    |
    v
Training Dataset
    |
    v
Temporal Split
    |
    v
Walk-Forward Evaluation
```

---

# Features v7

Validated state:

```text
68,747 rows
54 columns

feature-ready:     61,913
not feature-ready:  6,834
```

Feature windows:

```text
5d
10d
20d
```

Corporate-action feature policy:

```text
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

Only governed features are permitted for model consumption.

---

# ML Eligibility v3

Validated state:

```text
57,998 rows
37 columns

eligible:   57,441
ineligible:    557
```

Target horizon:

```text
exact global B3 T+5 trading days
```

Eligibility requires clean feature windows and a valid target horizon.

---

# Training Dataset v4

Validated state:

```text
57,998 rows
88 columns
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

The dataset preserves eligible and ineligible observations with their governance metadata.

---

# Temporal Split v3

Validated split:

```text
TRAIN       51,207 rows
VALIDATION   1,235 rows
TEST         2,501 rows
```

The split uses feature dates and future target dates instead of arbitrary row positions.

Purging rules prevent training targets from crossing into later validation periods.

Final TEST policy:

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

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
3 models per fold
36 metric rows
18 governed features
```

Models:

```text
dummy_mean
linear_regression
random_forest
```

Every fold enforces:

```text
train_target_max < validation_start
```

The final TEST holdout is protected:

```text
test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

Walk-forward artifacts:

```text
gold/ml/fii_walk_forward/
|-- fold_metrics/
|   `-- fold_metrics.parquet
|
`-- summary/
    `-- summary.json
```

Parquet and JSON artifacts intentionally use separate S3 prefixes so Athena only reads compatible file formats.

---

# AWS Glue Data Catalog

Development database:

```text
fii_data_ai_platform_dev
```

Current catalog includes:

```text
b3_instruments
b3_trades
cvm_fund_classes

fii_master

fii_daily_snapshot
fii_price_history
fii_corporate_action_adjusted_prices
fii_price_discontinuities

fii_features
fii_ml_eligibility
fii_training_dataset
fii_temporal_split
fii_walk_forward
```

Partition projection is used where appropriate to avoid manual partition registration.

---

# Amazon Athena

Athena workgroup:

```text
fii-data-ai-platform-dev
```

Validated controls:

```text
EnforceWorkGroupConfiguration = true
BytesScannedCutoffPerQuery    = 1 GiB
CloudWatch Metrics            = enabled
Result encryption             = SSE_S3
```

Phase 4 provides named queries for the major Gold Analytics and Gold ML datasets.

The workgroup limits uncontrolled scans and keeps analytical consumption serverless and cost-aware.

---

# Storage Idempotency

The S3 publishing abstraction separates physical file identity from logical data identity.

Behavior:

```text
object missing
-> upload

same physical SHA-256
-> skip

different physical SHA-256
but same logical content SHA-256
-> skip as equivalent repackaging

different logical content
-> block

explicit force
-> allow new version
```

This prevents silent replacement of governed datasets.

---

# Observability

The platform contains both local data-health validation and AWS operational observability.

Local validation includes:

```text
Pipeline Health
Controlled Failure
schema checks
duplicate checks
date checks
freshness checks
semantic checks
cross-dataset reconciliation
temporal split integrity
holdout protection
walk-forward reconciliation
```

Operational AWS components include:

```text
CloudWatch
CloudTrail
AWS Budgets
Athena query metrics
Lambda logs
operational alerting
```

Model performance is not used as an infrastructure-health gate.

---

# Security

Core security principles:

```text
least privilege
MFA
temporary AWS CLI credentials
no permanent CLI access keys
remote Terraform state
state locking
encryption by default
S3 Versioning
public-access blocking
auditability
controlled administrative access
```

Data Lake controls validated in Phase 4:

```text
Versioning = Enabled
Encryption = AES256

BlockPublicAcls        = true
IgnorePublicAcls       = true
BlockPublicPolicy      = true
RestrictPublicBuckets  = true
```

---

# Cloud Audit

CloudTrail:

```text
fii-data-ai-platform-dev
```

Configuration:

```text
home region:         sa-east-1
multi-region:        enabled
global events:       enabled
log-file validation: enabled
logging:             enabled
```

Audit bucket:

```text
fii-data-ai-platform-audit-625685670804
```

---

# Cost Governance

Monthly AWS Budget:

```text
fii-data-ai-platform-dev-monthly
```

Budget limit:

```text
USD 10
```

The architecture prefers:

```text
serverless
on-demand
small storage footprint
no idle compute
no permanent ML endpoints
```

Phase 4 does not introduce EC2 instances or persistent SageMaker endpoint infrastructure through Terraform.

---

# Infrastructure as Code

AWS infrastructure is managed through Terraform.

Structure:

```text
infrastructure/
`-- terraform/
    |-- bootstrap/
    |-- environments/
    |   `-- dev/
    `-- modules/
```

Current modules cover platform capabilities including:

```text
IAM
Budget
Observability
S3 Data Lake
Glue Catalog
Athena
Lambda
EventBridge Scheduler
ECR
CloudWatch
Gold operational controls
```

Stable infrastructure state is validated using:

```text
terraform fmt
terraform validate
terraform plan
```

Expected final state:

```text
No changes.
Your infrastructure matches the configuration.
```

---

# Git Workflow

Each new project phase follows:

```text
update main
-> create feature branch
-> develop
-> test
-> terraform plan when applicable
-> push
-> open Pull Request
-> review/checks
-> merge through Pull Request
-> create release tag
-> delete local and remote feature branch
```

Direct final integration into `main` is intentionally avoided.

---

# Releases

## Phase 0

```text
v0.1.0-phase0
```

Delivered:

```text
Local Data Foundation
Data Governance
Corporate Actions
Gold Analytics
Gold Quality
ML Dataset Engineering
Temporal Validation
Local Observability
Controlled Failure
Documentation
```

## Phase 1

```text
v0.2.0-phase1
```

Delivered:

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
```

## Phase 2

Status:

```text
COMPLETE
```

Delivered the AWS Data Lake foundation and cloud-native movement from RAW toward Silver and governed analytical consumption.

Detailed closure documentation:

```text
docs/phase-2/phase-2-closure.md
```

## Phase 3

```text
v0.4.0-phase3
```

Delivered automated AWS Gold processing, operational readiness and recovery controls.

Detailed closure documentation:

```text
docs/phase3/PHASE3_CLOSURE.md
```

## Phase 4

Status:

```text
TECHNICALLY COMPLETE
GITHUB CLOSURE PENDING
```

Delivered:

```text
Gold Analytics AWS publication
Gold ML AWS publication
Glue Catalog integration
Athena analytical consumption
ML feature foundation
ML eligibility governance
Training dataset
Purged temporal split
Walk-forward evaluation
Security validation
Cost validation
Cloud audit validation
End-to-end Terraform validation
```

Closure documentation:

```text
docs/phase-4/phase-4-closure.md
```

---

# Technical Documentation

Architecture:

```text
docs/architecture/
```

Data contracts:

```text
docs/data-contracts/
```

Lineage:

```text
docs/lineage/
```

Observability:

```text
docs/observability/
```

Phase closures:

```text
docs/phase-0/
docs/phase-1/
docs/phase-2/
docs/phase3/
docs/phase-4/
```

AWS infrastructure:

```text
infrastructure/terraform/README.md
```

---

# Local Development

Primary development environment:

```text
Windows
PowerShell
VS Code
Python 3.13
Git
Parquet
```

Create the Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Run tests:

```powershell
pytest -q
```

---

# AWS Development

Authenticate:

```powershell
aws login
```

Validate identity:

```powershell
aws sts get-caller-identity
```

Primary AWS region:

```text
sa-east-1
```

Terraform workflow:

```powershell
cd infrastructure\terraform\environments\dev

terraform init
terraform fmt -recursive ..\..
terraform validate
terraform plan
```

Review every Terraform plan before applying infrastructure changes.

---

# Architecture Freeze Rule

Validated upstream components are treated as frozen.

They should only be reopened for:

```text
real bug
contract inconsistency
proven semantic error
```

Optional enhancements belong in the backlog, downstream components or explicit new versions.

---

# Future Platform Evolution

Potential future capabilities include:

```text
analytics consumption
dashboarding
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

# Current Milestone

```text
Phase 0
Local Data Foundation
COMPLETE
        |
        v
Phase 1
AWS Foundation
COMPLETE
        |
        v
Phase 2
AWS Data Lake Foundation
COMPLETE
        |
        v
Phase 3
AWS Gold Automation
COMPLETE
        |
        v
Phase 4
AWS Analytics & AI Foundation
TECHNICALLY COMPLETE
GITHUB CLOSURE PENDING
```

---

# Disclaimer

This project is educational, technical and experimental.

It does not provide investment advice, tax advice or personalized financial recommendations.

Any future portfolio, recommendation or DARF-related functionality must be independently validated before real-world use.