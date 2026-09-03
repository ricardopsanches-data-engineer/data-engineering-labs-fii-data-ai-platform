# Observability Overview — FII Data & AI Platform

## 1. Objetivo

A camada de observabilidade da FII Data & AI Platform foi criada para verificar, de forma automatizada e reproduzível, a saúde dos principais artefatos de dados e ML da Fase 0.

O objetivo não é medir se um modelo é “bom” ou “ruim”. A observabilidade valida se a plataforma está íntegra, consistente com seus contratos, temporalmente correta e livre de falhas estruturais detectáveis.

Na Fase 0, a observabilidade é executada localmente e cobre:

- existência e leitura de artefatos;
- row count;
- duplicidades;
- schema mínimo;
- validade de datas;
- freshness com semântica específica por dataset;
- versões e contratos semânticos;
- reconciliação entre datasets;
- integridade dos splits temporais;
- prevenção de leakage;
- preservação do TEST final;
- integridade do Walk-Forward;
- reconciliação entre métricas detalhadas e resumo agregado;
- teste controlado de falha.

## 2. Componentes

### 2.1 Pipeline Health

Implementação:

```text
src/observability/pipeline_health/builder.py
```

Versão validada na Fase 0:

```text
Observability version: v3
```

Execução validada:

```powershell
python -m src.observability.pipeline_health.builder --reference-date 2026-09-01
```

Resultado validado:

```text
Overall status: PASS
Datasets monitored: 12
Checks PASS: 212
Checks WARN: 0
Checks FAIL: 0
```

### 2.2 Controlled Failure

Implementação:

```text
src/observability/controlled_failure/runner.py
```

Versão validada:

```text
Controlled Failure version: v1
```

O teste injeta uma duplicidade apenas em uma cópia temporária do dataset de Features e executa o mecanismo real de inspeção do Pipeline Health.

O dataset oficial permanece somente leitura.

Resultado validado:

```text
Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1
Official dataset unchanged: True
Temporary artifact removed: True
Test status: PASS
```

A interpretação correta é:

```text
Dataset temporário corrompido: FAIL esperado
Controlled Failure Test: PASS
```

Ou seja, a observabilidade detectou corretamente a falha que deveria detectar.

## 3. Datasets monitorados

O Pipeline Health v3 monitora 12 artefatos Parquet:

| # | Dataset | Camada | Freshness |
|---|---|---|---|
| 1 | corporate_action_adjusted_prices | Gold Analytics | DATA_DATE |
| 2 | price_discontinuities | Gold Analytics | EVENT_DRIVEN |
| 3 | price_history | Gold Analytics | DATA_DATE |
| 4 | price_quality | Gold Quality | DATA_DATE |
| 5 | corporate_action_review_queue | Gold Quality | EVENT_DRIVEN |
| 6 | features | Gold ML | DATA_DATE |
| 7 | ml_eligibility | Gold ML | TARGET_DATE |
| 8 | training_dataset | Gold ML | TARGET_DATE |
| 9 | temporal_split_train | Gold ML | HISTORICAL_SPLIT |
| 10 | temporal_split_validation | Gold ML | HISTORICAL_SPLIT |
| 11 | temporal_split_test | Gold ML | HISTORICAL_SPLIT |
| 12 | walk_forward_fold_metrics | Gold ML | HISTORICAL_EXPERIMENT |

O Walk-Forward também utiliza um artefato JSON:

```text
data/gold/ml/fii_walk_forward/summary.json
```

Esse JSON é validado e reconciliado contra o `fold_metrics.parquet`.

## 4. Semânticas de freshness

A plataforma não aplica uma regra genérica de “última data” a todos os datasets.

### DATA_DATE

Utilizada para datasets operacionais cuja atualização é representada por uma data de dado, como `trade_date` ou `feature_date`.

Exemplos:

- Price History;
- Price Quality;
- Features;
- Corporate Action Adjusted Prices.

### TARGET_DATE

Utilizada em datasets supervisionados em que a cobertura temporal correta depende da última `target_date`.

Exemplos:

- ML Eligibility;
- Training Dataset.

### EVENT_DRIVEN

Utilizada em datasets baseados em eventos.

A idade do último evento não é interpretada como staleness.

Exemplos:

- Price Discontinuities;
- Corporate Action Review Queue.

### HISTORICAL_SPLIT

Utilizada em artefatos deliberadamente históricos.

Sua saúde é determinada por:

- fronteiras temporais;
- purge;
- eligibility;
- ausência de overlap;
- política de holdout.

Exemplos:

- Train;
- Validation;
- Test.

### HISTORICAL_EXPERIMENT

Utilizada para o Walk-Forward.

Sua saúde é determinada por:

- contrato;
- estrutura dos folds;
- integridade temporal;
- purge;
- preservação do TEST;
- validade das métricas;
- reconciliação entre artefatos.

A idade da última janela de validação não é usada como critério de staleness.

## 5. Contratos semânticos monitorados

Na execução validada da Fase 0, o Pipeline Health v3 verifica os principais contratos da plataforma, incluindo:

```text
Price History: v3
Price Quality: v2
Features: v7
ML Eligibility: v3
Training Dataset: v4
Temporal Split: v3
Walk-Forward: v1
```

Semânticas críticas:

```text
price_semantics
= STRUCTURALLY_ADJUSTED_PRICE

return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

target_return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

target_horizon
= 5

target_horizon_semantics
= GLOBAL_B3_TRADING_DAYS

corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

## 6. Reconciliação entre datasets

A observabilidade verifica relações entre artefatos, incluindo:

- Price History e Features com row count reconciliado;
- ML Eligibility e Training Dataset com row count reconciliado;
- ML Eligibility e Training Dataset com o mesmo universo de samples;
- splits temporais como subconjunto do universo elegível;
- ausência de overlap entre Train, Validation e Test.

## 7. Integridade temporal

Os splits possuem validações explícitas de purge.

Contrato:

```text
train.target_date < validation.feature_date
validation.target_date < test.feature_date
```

A execução validada confirmou:

```text
train_validation_purge: PASS
validation_test_purge: PASS
temporal_split_overlap: PASS
```

## 8. Walk-Forward observável

O Walk-Forward v1 utiliza:

```text
Policy: EXPANDING_WINDOW_PURGED
Folds: 12
Validation sessions per fold: 5
Models: 3
Fold metric rows: 36
Target: target_return_next_5d
```

O Pipeline Health v3 verifica:

- versão;
- policy;
- fold count;
- IDs sequenciais;
- modelos esperados;
- uma linha por combinação fold/model;
- quantidade de datas de validation;
- datas válidas;
- purge em todos os folds;
- ausência de overlap entre janelas de validation;
- TEST boundary;
- validation antes do TEST;
- validation target antes do TEST;
- métricas finitas;
- ranges válidos;
- reconciliação do `summary.json`.

## 9. Preservação do TEST

O TEST final permanece reservado para avaliação final.

O Walk-Forward declara e a observabilidade valida:

```text
test_policy
= RESERVED_FINAL_HOLDOUT_NO_MODEL_EVALUATION

test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

Performance de modelo não é utilizada como condição de saúde.

Por exemplo, a observabilidade não exige que:

- Linear Regression seja o melhor modelo;
- R² seja positivo;
- directional accuracy supere um threshold arbitrário.

Esses valores são resultados experimentais, não contratos operacionais.

## 10. Artefatos operacionais

Pipeline Health:

```text
data/observability/pipeline_health/latest.json
data/observability/pipeline_health/history/<timestamp>.json
```

Controlled Failure:

```text
data/observability/controlled_failure/latest.json
data/observability/controlled_failure/history/<timestamp>.json
```

Esses arquivos são outputs de execução e não devem ser confundidos com documentação estável.

A evidência curada da Fase 0 é mantida em:

```text
docs/observability/evidence/
```

## 11. Limites da Fase 0

A Fase 0 implementa observabilidade local e executável.

Não fazem parte deste escopo:

- Prometheus;
- Grafana;
- alerting distribuído;
- métricas de infraestrutura cloud;
- orchestration observability;
- tracing distribuído;
- observabilidade AWS.

Essas capacidades podem ser avaliadas na Fase 1, quando a plataforma for migrada/evoluída para AWS.

## 12. Status

```text
Pipeline Health v3       VALIDATED
Controlled Failure v1    VALIDATED
Healthy execution        PASS
Controlled failure       PASS
Phase 0 observability    IMPLEMENTED AND EVIDENCED
```
