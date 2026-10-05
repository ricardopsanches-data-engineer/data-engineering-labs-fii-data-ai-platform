# Phase 5.3 — ML Serving Foundation

## 1. Objective

Phase 5.3 introduces a governed ML serving boundary for inference workloads.

The objective is to expose only the latest trusted, inference-ready feature state, without mixing:

- historical training data;
- future targets;
- training eligibility;
- split metadata;
- experiment metadata.

The resulting artifact is the operational input boundary for future model inference.

---

## 2. Architectural Principle

Training and inference have different temporal requirements.

Training uses historical rows with known future targets.

Inference uses the latest known feature state and must not depend on future target availability.

Therefore:

```text
Training readiness
!=
Inference readiness
```

The platform explicitly separates these concerns.

---

## 3. Training Eligibility vs Inference Readiness

The existing ML Eligibility v3 contract was designed for supervised training.

Its semantics include:

```text
feature lookback = 21 observations
target horizon = exact global B3 T+5
```

As a consequence, the latest eligible training row cannot necessarily be the latest feature row.

Validated state:

```text
Latest Features date:
2026-08-28

Latest ML Eligibility date:
2026-08-21
```

This difference is expected because training eligibility requires future target availability.

Therefore, ML Eligibility is not used as the direct serving filter for live inference.

---

## 4. Serving Temporal Authority

ML Serving does not independently infer its serving date.

The authoritative date is provided by Phase 5.2:

```text
Daily Consumption Layer
trade_date = latest trusted market state
```

The ML feature layer must reconcile against this date.

Required invariant:

```text
Daily Consumption trade_date
=
Latest Feature feature_date
```

Validated:

```text
2026-08-28
=
2026-08-28
```

If this invariant fails, ML Serving fails closed instead of exposing stale feature state.

---

## 5. Source Dataset

Canonical feature source:

```text
data/gold/ml/fii_features/fii_features.parquet
```

Validated state:

```text
Rows: 68,747
Columns: 54
Latest feature_date: 2026-08-28
Latest rows: 267
```

The serving process selects only the latest trusted feature date.

---

## 6. Inference Readiness

Inference readiness is based on current feature availability.

Validated latest state:

```text
feature_date = 2026-08-28
rows = 267
feature_ready = true for all 267 rows
feature_version = v7
source_price_history_version = v3
```

The serving layer therefore uses:

```text
feature_date = Daily Consumption trade_date
AND
feature_ready = true
```

Training-specific `ml_eligible` is intentionally not used.

---

## 7. Feature Contract

The serving dataset reuses the governed Feature Contract v3.

Validated contract:

```text
Feature Contract version: v3
Source Features version: v7
Feature windows: [5, 10, 20]
Feature count: 18
```

The contract validates:

```text
approved allowlist
feature existence
numeric types
finite values
semantic versions
price semantics
return semantics
corporate-action policy
leakage protection
```

---

## 8. Official Feature Allowlist

The serving dataset exposes only the approved ML features:

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

---

## 9. Serving Dataset Contract

Local artifact:

```text
data/serving/ml/latest_inference_features.parquet
```

Cloud artifact:

```text
serving/ml/latest_inference_features.parquet
```

The dataset contains:

```text
feature_date
ticker
feature_version
source_price_history_version
+
18 governed ML features
```

Total validated columns:

```text
22
```

---

## 10. Leakage Prevention

The ML Serving dataset must not expose:

```text
future targets
target dates
training eligibility
temporal split metadata
predictions from previous experiments
training-only governance metadata
```

Validated output:

```text
target columns      = []
eligibility columns = []
```

This maintains a strict inference boundary.

---

## 11. Latest Inference Dataset

Validated production-like local output:

```text
feature_date = 2026-08-28
rows = 267
tickers = 267
features = 18
feature_version = v7
source_price_history_version = v3
```

The output contains one row per:

```text
feature_date + ticker
```

and duplicate keys are rejected.

---

## 12. ML Serving Manifest

Local manifest:

```text
data/serving/ml/latest_inference_features.json
```

Cloud manifest:

```text
serving/ml/latest_inference_features.json
```

Validated structure:

```json
{
  "dataset": "latest_inference_features",
  "dataset_path": "data/serving/ml/latest_inference_features.parquet",
  "feature_contract_version": "v3",
  "feature_count": 18,
  "feature_date": "2026-08-28",
  "feature_version": "v7",
  "generated_at": "<UTC timestamp>",
  "row_count": 267,
  "source_price_history_version": "v3",
  "status": "READY",
  "ticker_count": 267
}
```

---

## 13. Logical Dataset Fingerprint

The physical Parquet representation is not treated as the sole business identity.

The publisher computes a deterministic logical fingerprint from:

```text
column names
column types
row values
deterministic feature_date/ticker ordering
```

Validated logical fingerprint:

```text
d9b2e422865a5e82e39a70f48cb95a36abd522ea63fb15601995413bfce582c5
```

The fingerprint is independent from Parquet serialization details.

---

## 14. Logical Manifest Fingerprint

The manifest contains operational metadata:

```text
generated_at
```

This changes on every execution.

Therefore, logical manifest identity intentionally ignores `generated_at`.

Validated logical fingerprint:

```text
e37c83115e08b60292eafdae06ce6fb0c1d7a7bc8f19c9d2bb32173ffe146fec
```

---

## 15. S3 Idempotency

The first validated execution created:

```text
serving/ml/latest_inference_features.parquet
serving/ml/latest_inference_features.json
```

The second consecutive execution demonstrated idempotency.

Dataset:

```text
same physical SHA
same logical fingerprint
-> upload skipped
```

Manifest:

```text
different physical SHA
same logical fingerprint
-> repackaging detected
-> upload skipped
```

This avoids unnecessary S3 object versions when the business state has not changed.

---

## 16. S3 Validation

Dataset object:

```text
server-side encryption = AES256
versioning = active
physical sha256 metadata = present
content_sha256 metadata = present
```

Manifest object:

```text
server-side encryption = AES256
versioning = active
physical sha256 metadata = present
content_sha256 metadata = present
```

No always-on compute resource was introduced.

---

## 17. Implementation

ML Serving builder:

```text
src/serving/ml_inference/builder.py
```

Package:

```text
src/serving/ml_inference/
```

S3 publisher:

```text
src/pipelines/ml_inference_serving_to_s3.py
```

Tests:

```text
tests/serving/test_ml_inference_builder.py
tests/serving/test_ml_inference_serving_to_s3.py
```

---

## 18. Automated Tests

Phase 5.3 validates:

```text
serving date resolution
Daily Consumption reconciliation
feature freshness mismatch rejection
latest feature selection
inference readiness independence from training eligibility
Feature Contract allowlist projection
target exclusion
eligibility exclusion
duplicate-key rejection
manifest generation
end-to-end local build
logical dataset fingerprint stability
logical fingerprint mutation detection
manifest generated_at exclusion
manifest business-state mutation detection
correct S3 keys
```

Validated result:

```text
15 tests passed
Ruff passed
git diff --check passed
```

---

## 19. Cost Decision

Phase 5.3 introduced no new AWS infrastructure.

Not introduced:

```text
SageMaker Endpoint
EC2
ECS
EKS
RDS
Aurora
Redshift
OpenSearch
Lambda
API Gateway
Bedrock
Vector Database
```

Cloud impact is limited to two small S3 serving artifacts and normal request/versioning costs.

There is no always-on compute.

---

## 20. ML Serving Architecture

The final Phase 5.3 flow is:

```text
Daily Consumption Layer
        |
        | trusted market date
        v
Gold ML Features
        |
        | freshness reconciliation
        v
Inference Readiness
        |
        | feature_ready = true
        v
Feature Contract v3
        |
        | 18 approved features
        v
Latest Inference Dataset
        |
        +----------------------+
        |                      |
        v                      v
Parquet Serving           Serving Manifest
        |                      |
        +-----------+----------+
                    |
                    v
                  S3
```

---

## 21. Downstream Role

The ML Serving Foundation becomes the controlled source for future:

```text
batch inference
online inference preparation
model scoring
recommendation generation
API exposure
AI-assisted explanation
automation
```

No consumer should directly read the full historical feature dataset when it only needs current inference state.

---

## 22. Phase 5.3 Exit Criteria

```text
[x] latest trusted feature date reconciled with Daily Consumption
[x] training eligibility separated from inference readiness
[x] feature_ready serving rule defined
[x] Feature Contract v3 reused
[x] exactly 18 governed ML features exposed
[x] targets excluded
[x] training eligibility excluded
[x] duplicate-key protection implemented
[x] latest inference dataset created
[x] ML serving manifest created
[x] dataset logical fingerprint implemented
[x] manifest logical fingerprint implemented
[x] S3 publisher implemented
[x] S3 idempotency validated
[x] automated tests implemented
[x] AWS object metadata validated
[x] no new infrastructure introduced
[x] no always-on compute introduced
```

---

## 23. Status

```text
Daily reconciliation       VALIDATED
Inference readiness        VALIDATED
Feature Contract           v3
Feature source             v7
Feature count              18
Serving feature_date       2026-08-28
Serving rows               267
Serving tickers            267
Target leakage             NONE
Training eligibility leak  NONE
Dataset S3 publication     VALIDATED
Manifest S3 publication    VALIDATED
Dataset idempotency        VALIDATED
Manifest idempotency       VALIDATED
Automated tests            15 PASS
New AWS infrastructure     NONE
Always-on compute          NONE
```