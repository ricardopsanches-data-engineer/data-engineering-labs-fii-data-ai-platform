# Phase 0 Observability Evidence

## 1. Escopo

Este documento registra a evidência curada das execuções de observabilidade validadas durante o fechamento da Fase 0 da FII Data & AI Platform.

A evidência possui dois cenários:

1. execução saudável da plataforma;
2. falha controlada em cópia temporária.

---

## 2. Healthy Run — Pipeline Health v3

Comando executado:

```powershell
python -m src.observability.pipeline_health.builder --reference-date 2026-09-01
```

Identificação:

```text
Observability version: v3
Reference date: 2026-09-01
Max freshness: 7 days
```

Freshness semantics:

```text
DATA_DATE
TARGET_DATE
EVENT_DRIVEN
HISTORICAL_SPLIT
HISTORICAL_EXPERIMENT
```

### Resultado global

```text
Overall status: PASS
Datasets monitored: 12
Checks PASS: 212
Checks WARN: 0
Checks FAIL: 0
```

### Datasets

```text
corporate_action_adjusted_prices   PASS
price_discontinuities              PASS
price_history                      PASS
price_quality                      PASS
corporate_action_review_queue      PASS
features                           PASS
ml_eligibility                     PASS
training_dataset                   PASS
temporal_split_train               PASS
temporal_split_validation          PASS
temporal_split_test                PASS
walk_forward_fold_metrics          PASS
```

### Volumes observados

```text
Corporate Action Adjusted Prices  68,747 rows / 372 tickers
Price Discontinuities                  79 rows /  38 tickers
Price History                      68,747 rows / 372 tickers
Price Quality                      68,747 rows / 372 tickers
Corporate Action Review Queue           0 rows /   0 tickers
Features                           68,747 rows / 372 tickers
ML Eligibility                     57,998 rows / 319 tickers
Training Dataset                   57,998 rows / 319 tickers
Temporal Split Train               51,207 rows / 311 tickers
Temporal Split Validation           1,235 rows / 265 tickers
Temporal Split Test                 2,501 rows / 274 tickers
Walk-Forward Fold Metrics              36 rows
```

### Freshness operacional

Para a referência `2026-09-01`:

```text
Adjusted Prices latest trade_date: 2026-08-28 -> 4 days -> PASS
Price History latest trade_date:   2026-08-28 -> 4 days -> PASS
Price Quality latest trade_date:   2026-08-28 -> 4 days -> PASS
Features latest feature_date:      2026-08-28 -> 4 days -> PASS
ML Eligibility latest target_date: 2026-08-28 -> 4 days -> PASS
Training latest target_date:       2026-08-28 -> 4 days -> PASS
```

Event-driven datasets não usam idade do último evento como staleness.

Historical splits e historical experiments não usam freshness contra a data atual.

---

## 3. Contratos validados

A execução confirmou:

```text
Price History version       v3
Price Quality version       v2
Features version            v7
ML Eligibility version      v3
Training Dataset version    v4
Temporal Split version      v3
Walk-Forward version        v1
```

Semânticas:

```text
price_semantics
STRUCTURALLY_ADJUSTED_PRICE

return_semantics
COMPOUNDED_DAILY_RETURN_ECONOMIC

target_return_semantics
COMPOUNDED_DAILY_RETURN_ECONOMIC

target_horizon
5

target_horizon_semantics
GLOBAL_B3_TRADING_DAYS

corporate_action_value_semantics
TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

---

## 4. Integridade temporal

Checks validados:

```text
temporal_split_overlap            PASS
train_validation_purge            PASS
validation_test_purge             PASS
split_vs_eligible_reconciliation  PASS
```

Contrato de purge:

```text
Train target max < Validation feature min
Validation target max < Test feature min
```

---

## 5. Walk-Forward Evidence

Artefatos:

```text
data/gold/ml/fii_walk_forward/fold_metrics.parquet
data/gold/ml/fii_walk_forward/summary.json
```

Contrato:

```text
Policy: EXPANDING_WINDOW_PURGED
Folds: 12
Validation feature sessions/fold: 5
Models: 3
Rows: 36
Features: 18
Target: target_return_next_5d
```

Modelos:

```text
dummy_mean
linear_regression
random_forest
```

O Pipeline Health v3 confirmou:

```text
walk_forward.summary_exists                  PASS
walk_forward.summary_read                    PASS
walk_forward.metrics_available               PASS
walk_forward.version                         PASS
walk_forward.policy                          PASS
walk_forward.fold_count                      PASS
walk_forward.fold_ids                        PASS
walk_forward.models                          PASS
walk_forward.metrics_row_count               PASS
walk_forward.fold_model_uniqueness           PASS
walk_forward.validation_sessions_contract    PASS
walk_forward.validation_feature_dates        PASS
walk_forward.temporal_dates                  PASS
walk_forward.purge                           PASS
walk_forward.validation_non_overlap          PASS
walk_forward.test_start                      PASS
walk_forward.validation_before_test          PASS
walk_forward.validation_target_before_test   PASS
walk_forward.metrics_finite                  PASS
walk_forward.regression_metric_ranges        PASS
walk_forward.directional_metric_ranges       PASS
walk_forward.summary_models_reconciliation   PASS
```

Além disso, as métricas agregadas de cada modelo foram reconciliadas entre o Parquet detalhado e o JSON de resumo.

### Preservação do TEST

```text
test_policy
RESERVED_FINAL_HOLDOUT_NO_MODEL_EVALUATION

test_features_used
false

test_targets_used
false

test_predictions_generated
false
```

Todos os checks correspondentes ficaram em `PASS`.

---

## 6. Resultado experimental observado

O Walk-Forward não usa performance como contrato de saúde, mas a execução produziu o seguinte resultado agregado:

| Modelo | Mean MAE | Mean RMSE | Mean R² | Mean Directional Accuracy | Mean Directional Lift |
|---|---:|---:|---:|---:|---:|
| Dummy Mean | 1.9131% | 3.2459% | -0.035719 | 57.46% | 0.00 pp |
| Linear Regression | 1.8752% | 3.1594% | 0.017932 | 58.23% | +0.78 pp |
| Random Forest | 1.9476% | 3.2958% | -0.071450 | 55.32% | -2.14 pp |

Na execução observada, Linear Regression apresentou o melhor resultado agregado nos cinco critérios resumidos pelo experimento.

Essa observação é um resultado experimental e não uma condição para o Pipeline Health ficar saudável.

---

## 7. Controlled Failure Evidence

Comando executado:

```powershell
python -m src.observability.controlled_failure.runner
```

Cenário:

```text
Test: features_duplicate_key
Controlled Failure version: v1
```

A falha foi introduzida apenas em uma cópia temporária.

```text
Original rows: 68,747
Corrupted rows: 68,748
Injected rows: 1
Expected duplicate count: 1
```

Resultado do detector:

```text
Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1
```

Verificações de segurança:

```text
Official dataset unchanged: True
Temporary artifact removed: True
```

Resultado do teste:

```text
Test status: PASS
```

Interpretação:

```text
O artefato temporário inválido falhou como esperado.
O framework de observabilidade detectou a quebra.
O dataset oficial permaneceu intacto.
```

---

## 8. Evidência operacional gerada

Healthy run:

```text
data/observability/pipeline_health/latest.json
data/observability/pipeline_health/history/20260903T110340Z.json
```

Controlled failure validado:

```text
data/observability/controlled_failure/latest.json
data/observability/controlled_failure/history/20260903T102611Z.json
```

Esses arquivos são outputs operacionais.

Este documento é a evidência estável e versionável da execução validada da Fase 0.

---

## 9. Conclusão

A observabilidade da Fase 0 foi validada em dois estados complementares.

### Estado saudável

```text
12 datasets monitored
212 PASS
0 WARN
0 FAIL
Overall status: PASS
```

### Estado de falha controlada

```text
1 duplicate injected in temporary Features copy
Dataset health: FAIL
Duplicate detector: FAIL
Official dataset unchanged: True
Temporary artifact removed: True
Controlled Failure Test: PASS
```

Conclusão:

```text
Pipeline Health v3       VALIDATED
Controlled Failure v1    VALIDATED
Healthy path             PROVEN
Failure detection path   PROVEN
Official data safety     PROVEN
```
