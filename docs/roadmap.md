# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Local Data Foundation: ingestion, contracts, governance, Gold Analytics, Gold ML, temporal validation and local observability | COMPLETE |
| 1 | AWS Foundation: Terraform, IAM, remote state, cost governance, CloudTrail and secure cloud baseline | COMPLETE |
| 2 | AWS Data Lake Foundation: S3 RAW/Silver, Lambda-based transformations, EventBridge scheduling, Glue/Athena foundation and operational observability | COMPLETE |
| 3 | AWS Gold Automation: automated Gold processing, readiness checks, recovery supervision and operational controls | COMPLETE |
| 4 | AWS Analytics & AI Foundation: Gold Analytics, Gold ML, Glue Catalog, Athena, temporal split, walk-forward evaluation, security and cost validation | IN CLOSURE |
| 5 | AI / Product Capabilities: analytical consumption, model lifecycle, API/serving, Generative AI, RAG, agents and product workflows | PLANNED |

---

## Current Status

Phase 4 is technically complete and currently in the final closure workflow.

Current platform capabilities include:

- AWS infrastructure managed with Terraform.
- Remote Terraform state with locking and versioning.
- IAM least-privilege operational model.
- AWS Budget and CloudTrail audit foundation.
- Versioned and encrypted Amazon S3 Data Lake.
- B3 and CVM RAW ingestion.
- Scheduled daily ingestion using EventBridge Scheduler and AWS Lambda.
- Event-driven RAW to Silver processing using Amazon S3 notifications.
- Parquet Silver datasets.
- Amazon ECR-backed Lambda processing.
- SHA-256 physical fingerprinting.
- Logical content hashing.
- Idempotent S3 publication.
- Silent overwrite protection.
- CloudWatch logging, metrics, dashboards and operational alerts.
- Automated Gold readiness checks.
- Gold recovery supervision.
- AWS Glue Data Catalog.
- Amazon Athena analytical consumption.
- Gold Analytics publication to S3.
- Gold ML publication to S3.
- Governed feature engineering.
- ML eligibility governance.
- Training dataset generation.
- Purged temporal train/validation/test split.
- Final TEST holdout protection.
- Purged expanding-window walk-forward evaluation.
- Cost-aware serverless analytical architecture.
- Terraform drift validation.
- Phase-based Git and Pull Request release workflow.

---

## Phase 0 - Local Data Foundation

Status:

```text
COMPLETE
```

Release:

```text
v0.1.0-phase0
```

Primary scope:

```text
Local ingestion
Data contracts
Corporate-action governance
Gold Analytics
Gold Quality
Gold ML
ML Eligibility
Training Dataset
Temporal Split
Baseline Models
Walk-Forward Evaluation
Pipeline Health
Controlled Failure
Architecture Documentation
```

Phase 0 established the governed local data and ML foundation before cloud migration.

---

## Phase 1 - AWS Foundation

Status:

```text
COMPLETE
```

Release:

```text
v0.2.0-phase1
```

Primary scope:

```text
Terraform
AWS Provider
IAM
MFA
Temporary AWS CLI authentication
Remote Terraform state
State locking
S3 security
AWS Budgets
CloudTrail
Audit bucket
Cost governance
```

Phase 1 created the secure and reproducible AWS foundation required by later platform phases.

---

## Phase 2 - AWS Data Lake Foundation

Status:

```text
COMPLETE
```

Primary scope:

```text
Amazon S3 Data Lake
RAW
Silver
AWS Lambda
Amazon ECR
EventBridge Scheduler
S3 event notifications
B3 ingestion
CVM ingestion
RAW to Silver
Parquet
Glue Data Catalog foundation
Athena foundation
CloudWatch observability
```

Phase 2 moved the platform from a local-only data architecture toward an operational AWS Data Lake.

Core flow:

```text
External Sources
      |
      v
AWS Ingestion
      |
      v
S3 RAW
      |
      v
Lambda Processing
      |
      v
S3 SILVER
```

Operational guarantees include:

```text
S3 Versioning
Encryption
Public Access Block
SHA-256 fingerprinting
idempotency
overwrite protection
serverless execution
```

---

## Phase 3 - AWS Gold Automation

Status:

```text
COMPLETE
```

Release:

```text
v0.4.0-phase3
```

Primary scope:

```text
Gold automation
Gold readiness checks
Gold recovery supervision
Watchdog scheduling
Operational observability
Failure recovery controls
CloudWatch metrics
CloudWatch alarms
SNS operational alerts
```

Phase 3 operationalized the governed Gold layer and introduced readiness and recovery controls around daily processing.

Conceptual flow:

```text
S3 SILVER
    |
    v
Gold Readiness
    |
    v
Gold Processing
    |
    v
Validation
    |
    +--> SUCCESS
    |
    +--> Recovery Supervisor
             |
             v
          Watchdog
```

---

## Phase 4 - AWS Analytics & AI Foundation

Status:

```text
IN CLOSURE
```

Technical implementation:

```text
COMPLETE
```

AWS validation:

```text
COMPLETE
```

Remaining work:

```text
documentation
feature branch push
Pull Request
review/checks
merge into main
release tag
branch cleanup
```

Phase 4 must only be considered officially complete after the GitHub closure workflow is finished.

Primary scope:

```text
Gold Analytics
Gold ML
Glue Catalog
Athena
Feature Engineering
ML Eligibility
Training Dataset
Temporal Split
Walk-Forward Evaluation
Security Validation
Cost Validation
Cloud Audit Validation
End-to-End Terraform Validation
```

---

## Phase 4 - Gold Analytics

Current analytical datasets:

```text
fii_daily_snapshot
fii_price_history
fii_corporate_action_adjusted_prices
fii_price_discontinuities
```

Architecture:

```text
S3 GOLD ANALYTICS
        |
        v
Glue Data Catalog
        |
        v
Amazon Athena
```

Current storage footprint:

```text
17 objects
24,891,903 bytes
```

---

## Phase 4 - Gold ML

Current ML datasets:

```text
fii_features
fii_ml_eligibility
fii_training_dataset
fii_temporal_split
fii_walk_forward
```

Governed ML flow:

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

Current storage footprint:

```text
31 objects
62,182,565 bytes
```

---

## Phase 4 - Temporal Governance

The ML foundation explicitly prevents leakage.

Temporal split contract:

```text
TRAIN
feature_date < validation_start
target_date < validation_start

VALIDATION
feature_date >= validation_start
feature_date < test_start
target_date < test_start

TEST
feature_date >= test_start
```

Final TEST policy:

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

Walk-forward policy:

```text
EXPANDING_WINDOW_PURGED
```

Each fold enforces:

```text
train_target_max < validation_start
```

Final TEST protection:

```text
test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

---

## Phase 4 - Analytics Consumption

AWS Glue Data Catalog database:

```text
fii_data_ai_platform_dev
```

Athena workgroup:

```text
fii-data-ai-platform-dev
```

Athena controls:

```text
EnforceWorkGroupConfiguration = true
BytesScannedCutoffPerQuery    = 1 GiB
CloudWatch Metrics            = enabled
Result Encryption             = SSE_S3
```

Phase 4 named queries cover the major Gold Analytics and Gold ML datasets.

---

## Phase 4 - Cost and Security

Current architectural strategy:

```text
serverless
on-demand
small storage footprint
no idle EC2
no permanent SageMaker endpoints
cost-aware query execution
```

AWS Budget:

```text
fii-data-ai-platform-dev-monthly
USD 10 monthly limit
```

Data Lake controls:

```text
S3 Versioning = Enabled
Encryption    = AES256
Public Access = Blocked
```

RAW lifecycle:

```text
current objects:
expire after 30 days

noncurrent versions:
expire after 7 days

incomplete multipart uploads:
abort after 7 days
```

CloudTrail:

```text
fii-data-ai-platform-dev
multi-region
logging enabled
log-file validation enabled
```

---

## Phase 4 - Final Validation

Validated final state:

```text
git working tree:
clean before documentation changes

terraform fmt:
PASS

terraform validate:
PASS

terraform plan:
No changes

Glue Catalog:
validated

Athena:
validated

Gold Analytics:
validated

Gold ML:
validated

Security:
validated

Cost controls:
validated

CloudTrail:
validated
```

Final Terraform result:

```text
No changes.
Your infrastructure matches the configuration.
```

---

## Phase 5 - AI / Product Capabilities

Status:

```text
PLANNED
```

Phase 5 represents the next logical evolution after the Analytics & AI Foundation is formally closed.

Potential scope includes:

```text
analytical consumption
dashboards
advanced portfolio analytics
ML workflow automation
model lifecycle
model registry
API / serving
portfolio workflows
portfolio rebalancing support
capital-gain workflows
DARF automation
Generative AI
RAG
Agents
natural-language data access
```

Exact Phase 5 scope must be defined before implementation.

As with previous phases, architecture should evolve incrementally and only introduce AWS services that provide clear technical or product value.

---

## Platform Evolution

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
Phase 5
AI / PRODUCT CAPABILITIES
```

---

## Engineering Principles

The roadmap follows these rules:

```text
1. Trustworthy data before complex models.

2. Governance before automation.

3. Explicit contracts before implicit assumptions.

4. Temporal correctness before model performance.

5. Serverless before permanently running infrastructure.

6. Cost control is part of architecture.

7. Security is part of architecture.

8. Observability is part of delivery.

9. Terraform is the source of truth for AWS infrastructure.

10. Every phase must pass technical validation before closure.

11. Every phase must close through Pull Request.

12. Release tags represent completed platform milestones.
```

---

## Release Workflow

Every phase follows:

```text
update main
-> create feature branch
-> develop
-> validate
-> terraform plan when applicable
-> push
-> Pull Request
-> review/checks
-> merge into main
-> create release tag
-> delete remote feature branch
-> delete local feature branch
```

A phase is not officially complete until this workflow is finished.