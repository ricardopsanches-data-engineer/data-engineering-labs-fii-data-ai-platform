# FII Data & AI Platform

A production-inspired **Data Engineering, Data Architecture and Machine Learning platform for Brazilian Real Estate Investment Funds (FIIs)**.

The project focuses on building a trustworthy local data platform first, with explicit contracts, corporate-action governance, temporal correctness and observability before moving to AWS and more advanced AI capabilities.

> Current status: **Phase 0 — Final closure in progress**

---

## Project Goals

- Ingest and preserve FII market and fund data from approved sources.
- Build reproducible RAW, Silver and Gold data layers.
- Govern corporate actions instead of treating price discontinuities as automatic truth.
- Produce economically meaningful price and return histories.
- Enforce explicit data contracts across analytical and ML datasets.
- Build leakage-aware training datasets and temporal splits.
- Evaluate models through both holdout validation and purged walk-forward experiments.
- Add executable observability and controlled-failure evidence.
- Document architecture, lineage, contracts and closure criteria.
- Evolve the validated local platform to AWS in the next phase.
- Support future Analytics, portfolio workflows, DARF automation and Generative AI / Agents.

---

## Phase 0 Philosophy

The central engineering principle is:

```text
trustworthy data
>
complex models
```

The goal of Phase 0 was not to maximize ML metrics.

It was to prove that the platform can produce data that is:

```text
traceable
governed
semantically consistent
temporally correct
observable
reproducible
```

---

## Architecture Overview

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
          +-------------------+-------------------+
          |                                       |
          v                                       v
   Gold Analytics                           Gold Quality
          |                                       |
          +-------------------+-------------------+
                              |
                              v
                           Gold ML
                              |
                     +--------+--------+
                     |                 |
                     v                 v
                 Baseline        Walk-Forward
                     |                 |
                     +--------+--------+
                              |
                              v
                       Observability
```

The complete architecture is documented under:

```text
docs/architecture/
```

---

## Data Sources

### B3

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

### CVM

Official source for fund registration and classification.

Validated parser result:

```text
Total classes: 36,606
FII classes: 1,528
```

### Funds Explorer

Complementary source used for enrichment of the FII universe.

It is treated as auxiliary and does not replace official B3/CVM identity or governance.

---

## Data Layers

### RAW

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

### Silver

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

### Gold

The Gold layer is divided into:

```text
analytics/
quality/
ml/
ai/
```

---

## Corporate Action Governance

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
     +----+----+
     |         |
     v         v
   Review    Decision
     |         |
     +----+----+
          |
          v
Adjusted Prices
```

Core rule:

```text
DETECTOR != DECISION
```

A large price move is not automatically converted into a confirmed corporate action.

### Price Discontinuities v5

Validated state:

```text
Candidates: 79
Tickers: 38

REJECTED: 59
CONFIRMED: 16
NOT_APPLICABLE: 4
PENDING: 0
```

### Corporate Action Registry v2

Validated state:

```text
Rows: 79
Fields: 20
Confirmed actions: 16
Pending: 0
```

### Corporate Action Adjusted Prices v3

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

## Gold Analytics

### Price History v3

Validated state:

```text
Rows: 68,747
Tickers: 372
Sessions: 250
Duplicates: 0
```

This is the governed time-series upstream for feature engineering.

### Daily Snapshot

The project currently contains two historical physical paths:

```text
data/gold/analytics/fii_daily_snapshot/...
data/gold/fii_daily_snapshot/...
```

Phase 0 deliberately does not silently declare one canonical.

Canonicalization remains an explicit architectural decision for future cleanup.

---

## Gold Quality

### Price Quality v2

Validated state:

```text
Rows: 68,747
Tickers: 372

PASS:   68,592
REVIEW:    155
FAIL:        0
```

Confirmed corporate actions are not automatically treated as data-quality failures.

### Corporate Action Review Queue

Validated state:

```text
Rows: 0
Pending cases: 0
```

An empty queue is valid by contract.

---

## Gold ML

### Features v7

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

## Feature Contract v3

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

## ML Eligibility v3

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

## Training Dataset v4

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

## Temporal Split v3

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

## Baseline v5

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

## Walk-Forward v1

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

## Observability

Phase 0 implements executable local observability.

Components:

```text
Pipeline Health v3
Controlled Failure v1
```

### Pipeline Health v3

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

## Controlled Failure v1

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

## Repository Structure

```text
fii-data-ai-platform/
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
├── infrastructure/
└── .github/
```

Some scaffold directories are intentionally retained for later phases.

---

## Technical Documentation

### Architecture

```text
docs/architecture/
├── architecture-overview.md
└── data-platform-architecture.md
```

### Lineage

```text
docs/lineage/
├── data-lineage.md
└── pipeline-lineage.md
```

### Data Contracts

```text
docs/data-contracts/
├── silver-contracts.md
├── gold-analytics-contracts.md
└── gold-ml-contracts.md
```

### Observability

```text
docs/observability/
├── observability-overview.md
├── controlled-failure.md
└── evidence/
    └── phase-0-observability-evidence.md
```

### Phase 0 Closure

```text
docs/phase-0/
└── phase-0-closure.md
```

---

## Versioned Contracts

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

---

## Local Development

Environment used during Phase 0:

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

Run available tests according to the current project modules:

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

## Phase 0 Status

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
[ ] Final repository review
[ ] Push latest branch state
[ ] Open Pull Request
[ ] Merge into main
```

Phase 0 is considered fully closed after the final repository review and merge into `main`.

---

## Roadmap

The original roadmap evolved during implementation.

Phase 0 ultimately became a complete local proof of the core platform rather than only a repository scaffold.

### Phase 1 — AWS Evolution

Possible next steps:

```text
AWS landing zone
Amazon S3 RAW/SILVER/GOLD
AWS Glue Data Catalog
Amazon Athena
Orchestration
CloudWatch
Managed processing
SageMaker / ML workflow
API / serving layer
Analytics consumption
```

### Future Product Capabilities

Potential later capabilities:

```text
portfolio analytics
FII comparison
portfolio rebalancing support
DARF calculation workflows
Generative AI
RAG
Agents
natural-language data access
```

These items are roadmap, not completed Phase 0 capabilities.

---

## Architecture Freeze Rule

Validated upstream components are treated as frozen.

They should only be reopened for:

```text
real bug
contract inconsistency
proven semantic error
```

Optional improvements or experiments should move to backlog, downstream layers or new versions.

---

## Cost Strategy

Development runs locally whenever possible.

AWS resources will be introduced only when the cloud phase requires them, with explicit attention to:

```text
budgets
tagging
resource teardown
cost visibility
minimal always-on infrastructure
```

---

## Disclaimer

This project is educational, technical and experimental.

It does not provide investment advice, tax advice or personalized financial recommendations.

Any future portfolio, recommendation or DARF-related functionality must be independently validated before real-world use.
