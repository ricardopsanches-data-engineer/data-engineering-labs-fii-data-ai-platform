# Phase 5.2 — Daily Consumption Layer

## 1. Objective

Phase 5.2 introduces a governed daily consumption boundary over the existing Gold Analytics FII Daily Snapshot.

The goal is to expose the latest trusted market state without duplicating the entire Gold dataset.

The implementation follows:

```text
Gold historical snapshots
        |
        v
latest trusted partition
        |
        v
validation
        |
        v
Daily Consumption manifest
        |
        v
S3 serving pointer
```

---

## 2. Architectural Decision

The Daily Consumption Layer does not copy the full FII Daily Snapshot.

Instead, it publishes a small manifest that points to the latest validated Gold snapshot.

Canonical Gold source:

```text
gold/analytics/fii_daily_snapshot/
```

Serving pointer:

```text
serving/daily/latest_snapshot.json
```

Local development artifact:

```text
data/serving/daily/latest_snapshot.json
```

This keeps the serving layer simple and avoids:

```text
dataset duplication
additional storage copies
synchronization complexity
extra Glue tables
additional databases
always-on compute
```

---

## 3. D-1 Semantics

D-1 is not implemented as:

```text
current_date - 1 calendar day
```

The serving layer resolves the latest trusted business date available in Gold.

Selection is based on the partition date:

```text
year=YYYY/month=MM/day=DD
```

The most recent valid partition becomes the serving candidate.

Examples:

```text
Monday
-> latest market state may be Friday

Market holiday
-> previous trading session remains latest

Missing daily ingestion
-> no synthetic date is invented
```

This provides market-aware consumption semantics.

---

## 4. Canonical Source

Phase 5.2 explicitly defines the canonical Daily Snapshot path as:

```text
data/gold/analytics/fii_daily_snapshot/
```

Cloud equivalent:

```text
s3://<data-lake>/gold/analytics/fii_daily_snapshot/
```

The historical legacy path:

```text
data/gold/fii_daily_snapshot/
```

is not used for serving resolution.

---

## 5. Latest Snapshot Resolution

The serving builder searches for:

```text
fii_daily_snapshot.parquet
```

under the canonical Gold Analytics directory.

Candidates are ordered by the business partition:

```text
year
month
day
```

Filesystem modification timestamps are not used to determine business freshness.

Validated development state:

```text
2026-08-27
2026-08-28
```

Resolved latest snapshot:

```text
2026-08-28
```

---

## 6. Validation Contract

Before a snapshot can be marked `READY`, the Daily Consumption Layer validates:

```text
snapshot exists
dataset is not empty
required columns exist
required fields contain no nulls
trade_date + ticker is unique
exactly one trade_date exists
partition date equals internal trade_date
```

Required serving columns are:

```text
trade_date
ticker
cnpj
codigo_cvm
denominacao_social
close_price
```

Failure in any mandatory validation prevents generation of a `READY` serving manifest.

---

## 7. Serving Manifest

The Daily Consumption Layer materializes:

```text
latest_snapshot.json
```

Contract:

```json
{
  "dataset": "fii_daily_snapshot",
  "generated_at": "<UTC timestamp>",
  "local_path": "<canonical local Gold path>",
  "row_count": "<row count>",
  "s3_key": "<canonical Gold S3 key>",
  "status": "READY",
  "ticker_count": "<unique ticker count>",
  "trade_date": "<YYYY-MM-DD>"
}
```

Validated development result:

```text
dataset      = fii_daily_snapshot
status       = READY
trade_date   = 2026-08-28
row_count    = 267
ticker_count = 267
```

The manifest references the Gold dataset instead of duplicating it.

---

## 8. Cloud Serving Path

The manifest is published to:

```text
s3://fii-data-ai-platform-dev-datalake-625685670804/
serving/daily/latest_snapshot.json
```

No new AWS service was provisioned.

The implementation reuses the existing:

```text
Amazon S3 Data Lake
S3 versioning
S3 server-side encryption
existing Python storage abstraction
existing idempotency behavior
```

---

## 9. Logical Idempotency

The local manifest contains:

```text
generated_at
```

This timestamp changes on every execution.

Therefore, physical file SHA alone cannot represent business identity.

Phase 5.2 introduces a logical content fingerprint calculated from:

```text
dataset
status
trade_date
row_count
ticker_count
local_path
s3_key
```

The field below is excluded:

```text
generated_at
```

This produces two fingerprints with different purposes:

```text
physical sha256
-> exact uploaded bytes

content_sha256
-> logical business state
```

---

## 10. Idempotency Behavior

Expected behavior:

```text
same snapshot
+
different generated_at
        |
        v
same content_sha256
        |
        v
skip upload
```

A changed business state produces:

```text
new trade_date
or
different serving contract state
        |
        v
different content_sha256
        |
        v
new publication
```

---

## 11. AWS Validation

The first validated publication created:

```text
serving/daily/latest_snapshot.json
```

Validated logical fingerprint:

```text
400e245d2350cd73453e61618435640e8bcaf55ae89c17ca270ad71b5dc03845
```

A second consecutive execution generated a different physical artifact because `generated_at` changed.

However, the logical fingerprint remained identical.

The existing S3 publication layer correctly detected:

```text
physical artifact different
logical content identical
```

and skipped the redundant upload.

This confirms logical idempotency.

---

## 12. S3 Object Validation

Validated object properties:

```text
object exists
S3 versioning active
server-side encryption = AES256
physical sha256 metadata present
logical content_sha256 metadata present
```

The serving pointer therefore participates in the same auditability and historical protection model already used by the platform.

---

## 13. Implementation

Serving builder:

```text
src/serving/daily_consumption/builder.py
```

Package:

```text
src/serving/
src/serving/daily_consumption/
```

S3 publisher:

```text
src/pipelines/daily_consumption_to_s3.py
```

Tests:

```text
tests/serving/test_daily_consumption_builder.py
tests/serving/test_daily_consumption_to_s3.py
```

---

## 14. Automated Tests

Phase 5.2 validates:

```text
latest partition selection
valid snapshot acceptance
partition / trade_date mismatch rejection
duplicate rejection
manifest generation and persistence
generated_at exclusion from logical fingerprint
business-state changes alter logical fingerprint
correct serving S3 key publication
```

Validated result:

```text
8 tests passed
Ruff passed
git diff --check passed
```

---

## 15. Cost Decision

Phase 5.2 introduced no new AWS infrastructure.

Not introduced:

```text
Lambda
API Gateway
RDS
Aurora
Redshift
OpenSearch
ECS
EC2
SageMaker endpoint
Vector Database
Bedrock resource
```

Cloud impact is limited to a very small S3 JSON object and normal S3 request/versioning costs.

There is no always-on resource.

---

## 16. Consumer Contract

Downstream consumers should resolve the daily state through:

```text
serving/daily/latest_snapshot.json
```

The manifest identifies the trusted Gold object.

Consumers should not independently guess:

```text
today - 1
latest filesystem timestamp
latest arbitrary S3 object
```

This keeps daily-state resolution centralized and deterministic.

---

## 17. Downstream Usage

The Daily Consumption Layer becomes an upstream dependency for:

```text
Phase 5.3
ML Serving Foundation

Phase 5.4
AI Retrieval Foundation

Phase 5.6
API / Product Layer

Phase 5.7
Daily Automation
```

Conceptually:

```text
Gold Analytics
      |
      v
Daily Consumption Layer
      |
      +----------------------+
      |          |           |
      v          v           v
     ML         AI          API
```

---

## 18. Phase 5.2 Exit Criteria

```text
[x] canonical Daily Snapshot path defined
[x] latest business partition resolution implemented
[x] calendar-day subtraction avoided
[x] minimum serving contract validated
[x] partition date reconciled with trade_date
[x] duplicate protection implemented
[x] latest manifest implemented
[x] Gold dataset duplication avoided
[x] S3 serving pointer implemented
[x] logical content fingerprint implemented
[x] S3 idempotency validated
[x] automated tests implemented
[x] static quality checks passed
[x] no new AWS infrastructure introduced
```

---

## 19. Status

```text
Daily Consumption Layer        VALIDATED
Latest snapshot resolution     VALIDATED
Canonical Gold path            DEFINED
Manifest contract              VALIDATED
Logical fingerprint            VALIDATED
S3 publication                 VALIDATED
S3 idempotency                 VALIDATED
Automated tests                8 PASS
New AWS infrastructure         NONE
Always-on compute              NONE
```