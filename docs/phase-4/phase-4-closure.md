# Phase 4 - AWS Analytics & AI Foundation Closure

## 1. Objective

Phase 4 extends the FII Data & AI Platform from an operational AWS Data Lake into a governed analytics and machine-learning foundation.

The phase focuses on:

- analytical Gold datasets;
- ML-ready Gold datasets;
- AWS Glue Data Catalog integration;
- Amazon Athena consumption;
- temporal correctness;
- leakage prevention;
- walk-forward model evaluation;
- observability;
- security;
- cost governance;
- reproducibility.

The implementation preserves the platform engineering principles established in previous phases:

```text
trustworthy data
>
complex models
>
unnecessary infrastructure
```

---

## 2. Phase Status

```text
Phase 4 - AWS Analytics & AI Foundation

Analytics Foundation          COMPLETE
ML Data Foundation            COMPLETE
Glue Catalog                  COMPLETE
Athena Consumption            COMPLETE
Temporal Validation           COMPLETE
Walk-Forward Evaluation       COMPLETE
Observability Validation      COMPLETE
Security Validation           COMPLETE
Cost Validation               COMPLETE
End-to-End Validation         COMPLETE
Documentation                 IN PROGRESS
GitHub Closure                PENDING
```

Phase 4 must only be considered officially closed after:

```text
feature branch push
-> Pull Request
-> review/checks
-> merge into main
-> release tag
-> local/remote branch cleanup
```

---

## 3. AWS Environment

Primary region:

```text
sa-east-1
```

Data Lake bucket:

```text
fii-data-ai-platform-dev-datalake-625685670804
```

Glue database:

```text
fii_data_ai_platform_dev
```

Athena workgroup:

```text
fii-data-ai-platform-dev
```

The analytical architecture intentionally favors AWS serverless and on-demand services to minimize idle infrastructure cost.

---

## 4. Gold Analytics Foundation

Phase 4 publishes the following analytical datasets to Amazon S3.

### 4.1 FII Daily Snapshot

Dataset:

```text
fii_daily_snapshot
```

Purpose:

- point-in-time daily analytical snapshot;
- one row per FII for the reference trading date;
- direct analytical consumption.

Validated state:

```text
267 rows
20 columns
reference date: 2026-08-28
```

S3 layout:

```text
gold/analytics/fii_daily_snapshot/
year=YYYY/
month=MM/
day=DD/
fii_daily_snapshot.parquet
```

Catalog:

```text
Glue table: fii_daily_snapshot
Athena: validated
```

---

### 4.2 FII Price History

Dataset version:

```text
Price History v3
```

Purpose:

- governed historical prices;
- economic returns;
- upstream source for ML feature engineering.

Validated state:

```text
68,747 rows
90 columns
period: 2025-08-29 -> 2026-08-28
```

S3 partition strategy:

```text
year/month
```

Layout:

```text
gold/analytics/fii_price_history/
year=YYYY/
month=MM/
fii_price_history.parquet
```

Catalog:

```text
Glue table: fii_price_history
Athena: validated
```

---

### 4.3 Corporate Action Adjusted Prices

Dataset version:

```text
Corporate Action Adjusted Prices v3
```

Purpose:

- preserve raw market prices;
- apply governed structural price adjustments;
- keep cash and in-kind economic effects explicit;
- prevent silent corporate-action transformations.

Validated state:

```text
68,747 rows
57 columns
period: 2025-08-29 -> 2026-08-28
```

Price semantics:

```text
STRUCTURALLY_ADJUSTED_PRICE
```

S3 layout:

```text
gold/analytics/fii_corporate_action_adjusted_prices/
year=YYYY/
fii_corporate_action_adjusted_prices.parquet
```

Catalog:

```text
Glue table: fii_corporate_action_adjusted_prices
Athena: validated
```

---

### 4.4 Price Discontinuities

Dataset version:

```text
Price Discontinuities v5
```

Purpose:

- quantitative detection of suspicious price discontinuities;
- candidate generation for corporate-action governance;
- explicit review status instead of automatic economic reinterpretation.

Validated state:

```text
79 rows
44 columns
```

S3 layout:

```text
gold/analytics/fii_price_discontinuities/
fii_price_discontinuities.parquet
```

Catalog:

```text
Glue table: fii_price_discontinuities
Athena: validated
```

---

## 5. Gold ML Foundation

Phase 4 publishes a complete ML-ready governed chain.

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

## 6. FII Features

Dataset version:

```text
Features v7
```

Validated state:

```text
68,747 rows
54 columns

feature_ready:
61,913 ready
6,834 not ready
```

Feature windows:

```text
5d
10d
20d
```

Feature policy:

```text
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

This policy means corporate-action economic effects may influence governed returns, but direct corporate-action payload fields are not injected into the model feature set.

S3 partition strategy:

```text
year/month
```

Catalog:

```text
Glue table: fii_features
Athena: validated
```

---

## 7. ML Eligibility

Dataset version:

```text
ML Eligibility v3
```

Responsibilities:

- enforce feature readiness;
- enforce future-target availability;
- block governed quality issues;
- protect the training population from contaminated observations.

Target horizon:

```text
exact global B3 T+5 trading days
```

Validated state:

```text
57,998 rows
37 columns

eligible:   57,441
ineligible:    557
```

Eligibility contract:

```text
ml_eligible =
feature_window_clean
AND
target_horizon_clean
```

Catalog:

```text
Glue table: fii_ml_eligibility
Athena: validated
```

---

## 8. Training Dataset

Dataset version:

```text
Training Dataset v4
```

Target:

```text
target_return_next_5d
```

Target semantics:

```text
COMPOUNDED_DAILY_RETURN_ECONOMIC
GLOBAL_B3_TRADING_DAYS
```

Validated state:

```text
57,998 rows
88 columns

eligible:   57,441
ineligible:    557
```

The dataset deliberately preserves both eligible and ineligible observations with governance metadata.

Governed consumers must explicitly filter according to the intended policy.

S3 partition strategy:

```text
feature_date year/month
```

Catalog:

```text
Glue table: fii_training_dataset
Athena: validated
```

---

## 9. Temporal Split

Dataset version:

```text
Temporal Split v3
```

Outputs:

```text
train.parquet
validation.parquet
test.parquet
```

Validated state:

```text
TRAIN       51,207 rows
VALIDATION   1,235 rows
TEST         2,501 rows
```

Split layout:

```text
gold/ml/fii_temporal_split/
split=train/train.parquet

gold/ml/fii_temporal_split/
split=validation/validation.parquet

gold/ml/fii_temporal_split/
split=test/test.parquet
```

The split uses global feature dates and target dates rather than arbitrary row counts.

Leakage protection:

```text
TRAIN:
feature_date < validation_start
AND
target_date < validation_start

VALIDATION:
feature_date >= validation_start
AND
feature_date < test_start
AND
target_date < test_start

TEST:
feature_date >= test_start
```

Purge semantics:

```text
TARGET_DATE_BEFORE_NEXT_SPLIT
```

Final holdout policy:

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

Catalog:

```text
Glue table: fii_temporal_split
Athena: validated
```

---

## 10. Walk-Forward Evaluation

Version:

```text
Walk-Forward v1
```

Policy:

```text
EXPANDING_WINDOW_PURGED
```

Configuration:

```text
12 folds
5 validation sessions per fold
3 models per fold
36 metric rows
minimum 80 training feature sessions
```

Models:

```text
dummy_mean
linear_regression
random_forest
```

Governed feature count:

```text
18
```

Metrics include:

```text
MAE
RMSE
R2
Directional Accuracy
Directional Lift
Prediction Distribution
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

Physical layout:

```text
gold/ml/fii_walk_forward/
|-- fold_metrics/
|   `-- fold_metrics.parquet
|
`-- summary/
    `-- summary.json
```

The Parquet and JSON artifacts intentionally use separate prefixes.

This prevents Athena from interpreting the governance JSON artifact as Parquet.

Catalog:

```text
Glue table: fii_walk_forward

Glue location:
gold/ml/fii_walk_forward/fold_metrics/

Athena: validated
```

---

## 11. Athena Validation

All Phase 4 analytical and ML tables were validated through Amazon Athena.

Named queries include:

```text
fii_daily_snapshot_sample
fii_price_history_sample
fii_corporate_action_adjusted_prices_sample
fii_price_discontinuities_sample
fii_features_sample
fii_ml_eligibility_sample
fii_training_dataset_sample
fii_temporal_split_sample
fii_walk_forward_sample
```

Athena workgroup controls:

```text
EnforceWorkGroupConfiguration = true

BytesScannedCutoffPerQuery =
1,073,741,824 bytes
1 GiB

PublishCloudWatchMetricsEnabled = true

Result encryption =
SSE_S3
```

This prevents uncontrolled analytical scans and supports cost-aware query execution.

---

## 12. Glue Data Catalog

The AWS Glue Data Catalog provides managed metadata for Silver, Gold Analytics and Gold ML datasets.

Validated catalog includes:

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

Partition projection is used where appropriate to avoid manual partition maintenance.

---

## 13. Storage and Idempotency

Phase 4 reuses the platform S3 storage abstraction.

Publishing behavior:

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

This separates physical file identity from logical dataset identity and prevents silent overwrites.

---

## 14. Security Validation

The Data Lake bucket was validated with:

```text
S3 Versioning = Enabled
Default encryption = AES256

BlockPublicAcls        = true
IgnorePublicAcls       = true
BlockPublicPolicy      = true
RestrictPublicBuckets  = true
```

The platform continues to follow least-privilege IAM principles.

Additional permissions are not introduced merely to simplify diagnostics.

---

## 15. Lifecycle and Cost Governance

RAW lifecycle rules are enabled for:

```text
raw/b3/
raw/cvm/
raw/b3-instruments/
```

Current policy:

```text
current objects:
expire after 30 days

noncurrent versions:
expire after 7 days

incomplete multipart uploads:
abort after 7 days
```

AWS Budget:

```text
fii-data-ai-platform-dev-monthly
monthly limit: USD 10
```

Phase 4 intentionally avoids persistent ML infrastructure.

The Terraform state contains no:

```text
aws_instance
SageMaker endpoint
SageMaker model endpoint infrastructure
```

The ML experiments execute locally while governed artifacts are persisted to the serverless AWS analytical foundation.

---

## 16. Cloud Audit

CloudTrail:

```text
trail:
fii-data-ai-platform-dev

home region:
sa-east-1

multi-region:
true

log file validation:
enabled

logging:
enabled
```

Audit bucket:

```text
fii-data-ai-platform-audit-625685670804
```

This provides management-event auditability independently from the Data Lake bucket.

---

## 17. End-to-End Validation

Final Phase 4 validation confirmed:

```text
git working tree:
clean

terraform fmt:
PASS

terraform validate:
PASS

terraform plan:
No changes

Glue Catalog:
validated

Athena named queries:
validated

Gold Analytics S3:
validated

Gold ML S3:
validated

security controls:
validated

cost controls:
validated

CloudTrail:
validated
```

Final Terraform evidence:

```text
No changes.
Your infrastructure matches the configuration.
```

This confirms that the declared infrastructure and deployed AWS environment are synchronized at the end of Phase 4 implementation.

---

## 18. Gold Analytics Storage Footprint

Validated inventory:

```text
17 objects
24,891,903 bytes
```

Datasets:

```text
fii_daily_snapshot
fii_price_history
fii_corporate_action_adjusted_prices
fii_price_discontinuities
```

---

## 19. Gold ML Storage Footprint

Validated inventory:

```text
31 objects
62,182,565 bytes
```

Datasets:

```text
fii_features
fii_ml_eligibility
fii_training_dataset
fii_temporal_split
fii_walk_forward
```

The footprint demonstrates that the current ML analytical foundation remains small and suitable for serverless/on-demand consumption.

---

## 20. Architecture Delivered by Phase 4

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
AWS Serverless Processing
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

Supporting controls:

```text
Terraform
IAM
S3 Versioning
S3 Encryption
Public Access Block
Lifecycle Policies
AWS Budget
CloudTrail
CloudWatch
Athena Scan Limits
Logical Content Hashing
```

---

## 21. Engineering Decisions Reinforced

Phase 4 reinforces the following platform principles:

```text
1. Data contracts are explicit.

2. Corporate-action semantics are governed.

3. Logical data identity is distinct from physical file identity.

4. Temporal correctness is part of the ML contract.

5. Target leakage is actively prevented.

6. Final TEST data is reserved.

7. Model performance does not define platform health.

8. Analytics infrastructure is serverless whenever practical.

9. Expensive idle ML infrastructure is avoided.

10. Infrastructure must converge to Terraform state with no drift.

11. Every analytical artifact must have a clear physical storage contract.

12. Different file formats must not share the same Athena table prefix.

13. Phase closure requires technical validation plus Git governance.
```

---

## 22. Phase 4 Closure Criteria

Technical implementation:

```text
[x] Gold Analytics datasets published to S3
[x] Gold Analytics datasets cataloged in Glue
[x] Gold Analytics validated in Athena

[x] Features published
[x] ML Eligibility published
[x] Training Dataset published
[x] Temporal Split published
[x] Walk-Forward metrics published

[x] Gold ML datasets cataloged in Glue
[x] Gold ML datasets validated in Athena

[x] Temporal leakage protections validated
[x] Final TEST holdout protected

[x] S3 security validated
[x] Athena cost controls validated
[x] AWS Budget validated
[x] CloudTrail validated
[x] Terraform compute footprint reviewed

[x] Terraform fmt validated
[x] Terraform validate passed
[x] Terraform plan returned no changes

[x] Phase 4 closure documentation created
```

Git governance:

```text
[ ] Push feature branch
[ ] Open Pull Request
[ ] Review/checks
[ ] Merge through Pull Request
[ ] Create Phase 4 release tag
[ ] Delete remote feature branch
[ ] Delete local feature branch
[ ] Confirm clean main
```

---

## 23. Closure State

At this point:

```text
Phase 4 technical implementation:
COMPLETE

Phase 4 AWS validation:
COMPLETE

Phase 4 documentation:
COMPLETE

Phase 4 GitHub release process:
PENDING
```

Phase 4 is therefore technically complete but must not yet be declared officially closed.

Official closure occurs only after the Pull Request, merge, release tag and branch cleanup are completed.