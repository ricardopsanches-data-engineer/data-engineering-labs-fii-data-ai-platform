# Phase 5.1 — Serving Architecture

## 1. Objective

Phase 5.1 defines how downstream consumers access governed Gold data without introducing unnecessary infrastructure.

The serving foundation follows the project principles:

```text
KISS
+
serverless / on-demand
+
reuse before provisioning
+
cost awareness
+
governed Gold consumption
```

No new AWS service is introduced in Phase 5.1.

---

## 2. Phase 5 Foundation Premise

Phase 5 starts from the following architectural premise:

```text
Reliable historical data
+
updated D-1 data
+
structured serving
+
ML consumption
+
RAG / GenAI consumption
```

Serving is the boundary between governed datasets and downstream consumers.

Consumers must not depend directly on RAW or SILVER datasets.

---

## 3. Existing Serving Foundation

The current AWS platform already provides the minimum required analytical serving stack:

```text
Amazon S3
    |
    v
AWS Glue Data Catalog
    |
    v
Amazon Athena
    |
    v
Consumers
```

Existing components are reused instead of introducing additional databases, clusters, or always-on compute.

---

## 4. Physical Storage

The governed datasets remain stored in the existing Amazon S3 Data Lake.

Conceptual structure:

```text
S3 Data Lake
|
+-- raw/
|
+-- silver/
|
+-- gold/
|   |
|   +-- analytics/
|   |
|   +-- quality/
|   |
|   +-- ml/
|   |
|   +-- ai/
|
+-- athena-results/
```

Phase 5.1 does not introduce a duplicated physical `serving/` storage layer.

Serving is initially a logical consumption boundary over governed Gold datasets.

This avoids unnecessary duplication, synchronization, storage cost, and operational complexity.

---

## 5. Metadata and Logical Contract

AWS Glue Data Catalog provides the logical metadata layer.

Current development database:

```text
fii_data_ai_platform_dev
```

The Glue Catalog represents the governed interface between physical S3 datasets and query consumers.

The catalog must remain aligned with:

```text
dataset schema
partition strategy
dataset semantics
data contracts
upstream versions
```

---

## 6. Query Serving Layer

Amazon Athena is the initial analytical serving interface.

Current development workgroup:

```text
fii-data-ai-platform-dev
```

Query results are stored under:

```text
athena-results/
```

The Athena workgroup currently provides:

```text
enforced workgroup configuration
CloudWatch metrics
SSE-S3 result encryption
per-query scanned-byte cutoff
```

The configured scanned-byte cutoff is:

```text
1 GiB per query
```

This provides a cost-control guardrail for development workloads.

---

## 7. Serving Architecture

The Phase 5.1 serving architecture is:

```text
                         GOVERNED GOLD
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
             Gold Analytics            Gold ML
                  |                       |
                  +-----------+-----------+
                              |
                              v
                     Glue Data Catalog
                              |
                              v
                           Athena
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
      Analytics          ML Consumption      AI / Product
                                             Consumption
```

No new persistent compute layer is required.

---

## 8. Consumer Boundaries

Phase 5 introduces distinct consumer categories.

### 8.1 Analytics

Primary consumption:

```text
Gold Analytics
    |
    v
Glue
    |
    v
Athena
```

Examples:

```text
portfolio analysis
historical analysis
daily market analysis
quality investigation
ad-hoc SQL
```

---

### 8.2 Daily Consumption

Phase 5.2 will define a reliable D-1 consumption contract.

Expected responsibility:

```text
latest trusted market state
```

The daily serving dataset must represent a clear and deterministic business date.

---

### 8.3 ML Consumption

Phase 5.3 will define the serving boundary for inference-oriented datasets.

Existing historical ML assets such as:

```text
fii_features
fii_ml_eligibility
fii_training_dataset
fii_temporal_split
fii_walk_forward
```

are not automatically equivalent to online or latest inference serving datasets.

Training and inference contracts must remain explicitly separated.

---

### 8.4 AI / RAG Consumption

Phase 5.4 and Phase 5.5 will introduce AI retrieval boundaries only where required.

Structured quantitative data should remain queryable through governed structured datasets.

RAG and vector retrieval should be used for content that benefits from semantic retrieval.

Conceptually:

```text
Structured facts
    |
    +--> Athena / structured retrieval

Documents / semantic context
    |
    +--> RAG
          |
          +--> Embeddings
          |
          +--> Vector Store
```

Vector infrastructure must not be introduced merely to duplicate structured analytical data.

---

### 8.5 API / Product Consumption

Phase 5.6 will expose selected governed data and results through a product/API boundary.

The API must consume serving contracts instead of directly coupling to RAW or SILVER storage.

Conceptually:

```text
Product / API
      |
      v
Serving Contract
      |
      +--> Structured Data
      |
      +--> ML Results
      |
      +--> AI Retrieval / Generation
```

---

## 9. Initial Serving Contracts

### 9.1 FII Daily Snapshot

Dataset:

```text
fii_daily_snapshot
```

Purpose:

```text
daily governed analytical state
```

Grain:

```text
one row per ticker per trade date
```

Primary consumers:

```text
Analytics
Daily Consumption Layer
future API
future AI structured retrieval
```

Expected freshness:

```text
D-1
```

---

### 9.2 FII Price History

Dataset:

```text
fii_price_history
```

Purpose:

```text
governed historical price and economic-return series
```

Primary consumers:

```text
Analytics
feature engineering
ML
historical analysis
future product queries
```

This dataset is historical and must not be treated as a replacement for a dedicated latest-state serving contract.

---

### 9.3 FII Features

Dataset:

```text
fii_features
```

Purpose:

```text
governed ML feature history
```

Primary consumers:

```text
ML training
ML validation
future inference serving preparation
```

Historical feature datasets and latest inference datasets remain separate architectural concerns.

---

## 10. Serving Contract Dimensions

Every serving dataset introduced from Phase 5 onward should explicitly define:

```text
dataset name
business purpose
grain
primary key
schema
partition strategy
freshness
upstream dependencies
semantic version
quality requirements
consumer category
mutation policy
```

This prevents downstream consumers from depending on undocumented implementation details.

---

## 11. Cost and KISS Decision

Phase 5.1 deliberately does not introduce:

```text
RDS
Aurora
Redshift provisioned clusters
EC2
ECS services
OpenSearch
Vector Database
API Gateway
new Lambda serving functions
Bedrock resources
SageMaker endpoints
```

These services may only be introduced in future subphases when a concrete requirement justifies them.

The decision rule is:

```text
Can the existing architecture solve the problem?
        |
        +-- YES --> reuse
        |
        +-- NO --> evaluate new service
                      |
                      v
             prefer serverless/on-demand
                      |
                      v
               define cost impact
                      |
                      v
              define teardown path
```

---

## 12. Operational Cost Policy

All Phase 5 cloud resources must follow the project cost policy:

```text
avoid idle resources
prefer serverless
prefer on-demand
prefer scale-to-zero
destroy temporary resources after tests
review recurring cost before provisioning
```

A resource must not remain provisioned merely because it may be useful later.

---

## 13. Phase 5 Evolution

The serving architecture evolves incrementally:

```text
5.1 Serving Architecture
    Gold -> governed serving boundary

5.2 Daily Consumption Layer
    Gold -> trusted D-1 dataset

5.3 ML Serving Foundation
    Features -> latest inference dataset

5.4 AI Retrieval Foundation
    structured retrieval + RAG boundary

5.5 Embeddings / Vector DB
    semantic retrieval only where justified

5.6 API / Product Layer
    consumer-facing access

5.7 Automation
    D-1 -> serving -> ML / AI consumption
```

---

## 14. Target Daily Flow

The target Phase 5 daily flow remains:

```text
Scheduler 1x/day
      |
      v
RAW
      |
      v
Silver
      |
      v
Gold Analytics
      |
      +---------------------+
      |                     |
      v                     v
Latest ML Features      AI Serving Data
      |                     |
      v                     +--> Athena / API
Inference Dataset            |
                            +--> RAG refresh
                                  |
                                  v
                              Vector DB
```

Vector infrastructure is conditional and will only be introduced if semantic retrieval requirements justify it.

---

## 15. Architecture Decision

Phase 5.1 establishes the following decision:

```text
Physical serving storage
    = existing governed S3 Gold

Metadata contract
    = AWS Glue Data Catalog

Initial query interface
    = Amazon Athena

Always-on serving compute
    = none

New infrastructure
    = none
```

This architecture is intentionally minimal.

It provides a stable foundation for the next Phase 5 subphases without prematurely introducing infrastructure.

---

## 16. Phase 5.1 Exit Criteria

Phase 5.1 is complete when:

```text
[x] existing serving infrastructure inventoried
[x] Gold consumption boundary defined
[x] consumer categories defined
[x] Athena selected as initial structured query interface
[x] Glue retained as metadata contract
[x] S3 Gold retained as physical source
[x] no unnecessary AWS resources introduced
[x] cost policy documented
[x] future ML / AI / API boundaries documented
[x] serving architecture documented
```

---

## 17. Status

```text
Phase 5.1 Serving Architecture     DEFINED
S3 Gold serving boundary          DEFINED
Glue metadata contract            REUSED
Athena analytical serving         REUSED
ML serving boundary               PREPARED
AI retrieval boundary             PREPARED
API serving boundary              PREPARED
New AWS infrastructure            NONE
Always-on compute                 NONE
```