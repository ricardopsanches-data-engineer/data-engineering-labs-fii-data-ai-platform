# Gold ML Contracts — FII Data & AI Platform

## 1. Objetivo

Este documento registra os contratos dos artefatos Gold ML da Fase 0.

Escopo:

```text
Features v7
ML Eligibility v3
Training Dataset v4
Temporal Split v3
Feature Contract v3
Baseline v5
Walk-Forward v1
```

O objetivo central é garantir que temporalidade, elegibilidade, semântica econômica e holdout sejam tratados como contratos, não como convenções implícitas.

---

## 2. Features v7

### Path

```text
data/gold/ml/fii_features/fii_features.parquet
```

### Version

```text
feature_version = v7
```

### Grain

```text
1 row por feature_date + ticker
```

### Key

```text
feature_date + ticker
```

### Estado validado

```text
Rows: 68,747
Tickers: 372
Feature-ready rows: 61,913
Duplicates: 0
```

### Windows

```text
5
10
20
```

### Semantics

```text
price_semantics
= STRUCTURALLY_ADJUSTED_PRICE

return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

### Corporate-action feature policy

```text
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

Corporate action impact is embedded in the economic return curve; direct event payload is not used as an ML feature.

### Freshness

```text
DATA_DATE
```

via:

```text
feature_date
```

---

## 3. Feature Contract v3

### Purpose

Define explicit allowlist for model inputs.

### Feature count

```text
18
```

### Allowlist

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

### Rule

No model may silently consume columns outside this allowlist.

### Missing values

Structural NaNs may exist in specific engineered ratios.

Imputation is fit only on TRAIN data.

---

## 4. ML Eligibility v3

### Path

```text
data/gold/ml/fii_ml_eligibility/
```

### Version

```text
ml_eligibility_version = v3
```

### Grain

```text
feature_date + ticker
```

### Estado validado

```text
Rows: 57,998
Tickers: 319
Eligible: 57,441
Ineligible: 557
DQ issues: 0
```

### Eligibility contract

```text
feature lookback = 21 observations
target horizon = exact global B3 T+5
```

### Blocking conditions

Examples:

```text
Price Quality REVIEW
Registry REJECTED
```

Confirmed corporate actions and isolated extreme returns are not automatically blocking.

### Freshness

```text
TARGET_DATE
```

via:

```text
target_date
```

### Consumer

```text
Training Dataset v4
```

---

## 5. Training Dataset v4

### Path

```text
data/gold/ml/fii_training_dataset/fii_training_dataset.parquet
```

### Version

```text
training_dataset_version = v4
```

### Grain

```text
feature_date + ticker
```

### Estado validado

```text
Rows: 57,998
Tickers: 319
Duplicates: 0
Target nulls: 0
Target nonfinite: 0
Invalid target chronology: 0
```

### Target

```text
target_return_next_5d
```

### Horizon

```text
target_horizon = 5
target_horizon_semantics = GLOBAL_B3_TRADING_DAYS
```

### Return semantics

```text
target_return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC
```

### Corporate action semantics

```text
corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

### Chronology

Required:

```text
target_date > feature_date
```

### Freshness

```text
TARGET_DATE
```

### Consumers

```text
Temporal Split v3
Walk-Forward v1
```

---

## 6. Temporal Split v3

### Paths

```text
data/gold/ml/fii_temporal_split/train.parquet
data/gold/ml/fii_temporal_split/validation.parquet
data/gold/ml/fii_temporal_split/test.parquet
```

### Version

```text
split_version = v3
```

### State

```text
TRAIN
51,207 rows
2025-09-26 -> 2026-07-17

VALIDATION
1,235 rows
2026-07-27 -> 2026-07-31

TEST
2,501 rows
2026-08-10 -> 2026-08-21
```

### Split names

Each file must contain the matching split name:

```text
train
validation
test
```

### Eligibility

Every row assigned to a split must satisfy:

```text
ml_eligible = true
```

### Purge semantics

```text
TARGET_DATE_BEFORE_NEXT_SPLIT
```

Required:

```text
max(train.target_date)
<
min(validation.feature_date)
```

and:

```text
max(validation.target_date)
<
min(test.feature_date)
```

### Overlap

Required:

```text
train ∩ validation = 0
train ∩ test = 0
validation ∩ test = 0
```

### Holdout policy

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

---

## 7. Baseline v5

### Purpose

Reference experiment using governed train/validation data.

### Models

```text
DummyRegressor
LinearRegression
RandomForestRegressor
```

### Random Forest configuration

```text
n_estimators = 200
random_state = 42
n_jobs = -1
```

### Policy

```text
TRAIN -> VALIDATION
TEST untouched
```

### Observed result

Linear Regression produced the best regression result in the validated validation window.

Performance is not part of the data-health contract.

---

## 8. Walk-Forward v1

### Paths

```text
data/gold/ml/fii_walk_forward/fold_metrics.parquet
data/gold/ml/fii_walk_forward/summary.json
```

### Version

```text
walk_forward_version = v1
```

### Policy

```text
EXPANDING_WINDOW_PURGED
```

### Structure

```text
fold_count = 12
validation_feature_sessions = 5
models = 3
metric rows = 36
feature_count = 18
```

### Model set

```text
dummy_mean
linear_regression
random_forest
```

### Purge contract

For every fold:

```text
train_target_max < validation_start
```

### Validation overlap contract

Validation windows must not overlap.

### Final TEST boundary

```text
test_start = 2026-08-10
```

Required:

```text
max(validation_end) < test_start
max(validation_target_max) < test_start
```

### TEST policy

```text
RESERVED_FINAL_HOLDOUT_NO_MODEL_EVALUATION
```

Required flags:

```text
test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

### Metric integrity

Required:

```text
MAE finite and >= 0
RMSE finite and >= 0
R² finite
directional_accuracy between 0 and 1
majority_directional_accuracy between 0 and 1
directional_lift finite
```

### Reconciliation

`summary.json` must reconcile with `fold_metrics.parquet`.

This includes aggregate metrics per model.

---

## 9. Walk-Forward Observed Result

Validated aggregate result:

| Model | Mean MAE | Mean RMSE | Mean R² | Directional Accuracy | Directional Lift |
|---|---:|---:|---:|---:|---:|
| Dummy Mean | 1.9131% | 3.2459% | -0.035719 | 57.46% | 0.00 pp |
| Linear Regression | 1.8752% | 3.1594% | 0.017932 | 58.23% | +0.78 pp |
| Random Forest | 1.9476% | 3.2958% | -0.071450 | 55.32% | -2.14 pp |

Linear Regression was the best model in the aggregate execution across the five summarized criteria.

This result is experimental, not contractual.

---

## 10. Cross-Dataset Contracts

### Features vs Price History

```text
row_count(Features)
=
row_count(Price History)
```

Validated:

```text
68,747 = 68,747
```

### Eligibility vs Training

```text
row_count(Eligibility)
=
row_count(Training Dataset)
```

Validated:

```text
57,998 = 57,998
```

Their governed sample keys also reconcile.

### Split vs Eligibility

Final split rows must be a subset of eligible rows.

Validated.

---

## 11. Leakage Prevention Contract

The platform treats leakage as a contract failure.

Forbidden:

```text
future target information in features
target crossing next split
overlapping temporal splits
validation reaching final TEST
using TEST for model selection
fitting imputers/scalers on validation/test
```

Required:

```text
fit transformations on TRAIN only
respect target_date boundaries
reserve TEST
```

---

## 12. Performance vs Health

Observability must not fail because:

```text
Linear Regression stopped being best
R² became negative
Directional Accuracy dropped
Random Forest improved
```

Those are experiment outcomes.

Health checks must focus on:

```text
contract integrity
temporal integrity
artifact integrity
metric computability
holdout protection
reconciliation
```

---

## 13. Observability Contract

Pipeline Health v3 monitors the ML chain and Walk-Forward.

Validated result:

```text
12 datasets monitored
212 checks PASS
0 WARN
0 FAIL
```

Walk-Forward contract checks include:

```text
version
policy
folds
models
row count
fold/model uniqueness
validation sessions
temporal dates
purge
non-overlap
TEST boundary
metric ranges
summary reconciliation
```

---

## 14. Mutation Policy

Frozen upstream artifacts must not be changed merely to improve model metrics.

Reopen only for:

```text
real bug
contract inconsistency
proven semantic error
```

Optional improvements belong to backlog or downstream evolution.

---

## 15. Status

```text
Features v7            VALIDATED
Feature Contract v3    VALIDATED
ML Eligibility v3      VALIDATED
Training Dataset v4    VALIDATED
Temporal Split v3      VALIDATED
Baseline v5            VALIDATED
Walk-Forward v1        VALIDATED
Gold ML contracts      DOCUMENTED
```
