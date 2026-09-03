# Pipeline Lineage — FII Data & AI Platform

## 1. Objetivo

Este documento descreve a ordem lógica de execução da FII Data & AI Platform na Fase 0.

Enquanto `data-lineage.md` explica a dependência entre datasets, este documento responde:

```text
qual processo roda
→ em que ordem
→ o que ele consome
→ o que ele produz
→ onde existem gates de qualidade
→ onde existe decisão humana
```

---

## 2. Pipeline lógico completo

```text
[EXTERNAL SOURCES]
     |
     +-- B3
     +-- CVM
     +-- Funds Explorer
     |
     v
[INGESTION]
     |
     v
[RAW]
     |
     v
[PARSING / NORMALIZATION / IDENTITY]
     |
     v
[SILVER]
     |
     +---------------------------+
     |                           |
     v                           v
[DAILY SNAPSHOT]        [PRICE DISCONTINUITY DETECTOR v5]
                                     |
                                     v
                          [CORPORATE ACTION REGISTRY v2]
                                     |
                        +------------+------------+
                        |                         |
                        v                         v
                [REVIEW QUEUE]            [GOVERNED DECISION]
                        |                         |
                        +------------+------------+
                                     |
                                     v
                    [CORPORATE ACTION ADJUSTED PRICES v3]
                                     |
                      +--------------+--------------+
                      |                             |
                      v                             v
             [PRICE QUALITY v2]            [PRICE HISTORY v3]
                      |                             |
                      +--------------+--------------+
                                     |
                                     v
                              [FEATURES v7]
                                     |
                                     v
                          [ML ELIGIBILITY v3]
                                     |
                                     v
                         [TRAINING DATASET v4]
                                     |
                     +---------------+----------------+
                     |                                |
                     v                                v
             [TEMPORAL SPLIT v3]             [WALK-FORWARD v1]
                     |                                |
             +-------+-------+                        |
             |               |                        |
             v               v                        |
        [BASELINE v5]   [FINAL TEST HOLDOUT]          |
                                                     |
                                                     v
                                          [PIPELINE HEALTH v3]
                                                     |
                                                     v
                                        [CONTROLLED FAILURE v1]
```

Observability é transversal e pode inspecionar vários artefatos do pipeline independentemente da sua posição gráfica.

---

## 3. Etapa 1 — Ingestion

### Inputs

```text
B3
CVM
Funds Explorer
```

### Responsabilidade

- aquisição de dados;
- persistência RAW;
- preservação da origem;
- preparação para parsing.

### Output

```text
data/raw/...
```

### Gate

Arquivos precisam existir e ser legíveis antes do parsing.

---

## 4. Etapa 2 — Parsing / Normalization / Identity

### Inputs

```text
RAW B3
RAW CVM
RAW auxiliary sources
```

### Responsabilidade

- interpretar formatos;
- normalizar tipos;
- corrigir encoding;
- consolidar identidade;
- produzir dados tecnicamente consistentes.

### Output

```text
Silver
```

### Estado validado da base de pregão

```text
250 sessões
2025-08-29 -> 2026-08-28
68,747 rows
372 tickers
```

---

## 5. Etapa 3 — Price Discontinuity Detection

### Input

Série de preços derivada da base governada.

### Processo

```text
price series
→ statistical / rule detection
→ candidate discontinuity
```

### Output

```text
Price Discontinuities v5
```

Estado:

```text
79 candidates
38 tickers
```

### Regra de governança

O detector não é autoridade final.

```text
DETECTOR != DECISION
```

Nenhum extremo de retorno deve ser automaticamente convertido em corporate action confirmada.

---

## 6. Etapa 4 — Corporate Action Governance

### Inputs

```text
Price Discontinuities v5
external/supporting evidence
human review when required
```

### Components

```text
Corporate Action Registry v2
Corporate Action Review Queue
```

### Registry state

```text
REJECTED: 59
CONFIRMED: 16
NOT_APPLICABLE: 4
PENDING: 0
```

### Review Queue state

```text
0 pending rows
```

### Gate

Somente decisões governadas devem afetar o cálculo downstream.

---

## 7. Etapa 5 — Corporate Action Adjusted Prices

### Inputs

```text
price series
Corporate Action Registry v2
```

### Output

```text
Corporate Action Adjusted Prices v3
```

### Responsibilities

- structural price adjustment;
- economic value adjustment;
- cash + in-kind treatment;
- economic return calculation.

### Contract

```text
price semantics:
STRUCTURALLY_ADJUSTED_PRICE

return semantics:
COMPOUNDED_DAILY_RETURN_ECONOMIC

corporate action semantics:
TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

### Gate

```text
DQ issues = 0
Pending actions = 0
```

---

## 8. Etapa 6 — Quality and Price History

Adjusted Prices alimenta dois ramos irmãos.

### 8.1 Price Quality v2

Responsabilidade:

- classificar qualidade;
- registrar REVIEW;
- bloquear situações incompatíveis com ML.

Estado:

```text
PASS: 68,592
REVIEW: 155
FAIL: 0
```

### 8.2 Price History v3

Responsabilidade:

- consolidar preços governados;
- disponibilizar retornos econômicos;
- criar upstream temporal para Features.

Estado:

```text
68,747 rows
372 tickers
250 sessions
duplicates = 0
```

---

## 9. Etapa 7 — Features v7

### Input principal

```text
Price History v3
```

### Output

```text
Features v7
```

### Janelas

```text
5d
10d
20d
```

### Feature policy

```text
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

Isso significa:

- corporate actions influenciam o retorno econômico;
- payload direto do evento não é injetado como feature do modelo.

### Feature Contract v3

Somente 18 features allowlisted podem entrar nos modelos.

---

## 10. Etapa 8 — ML Eligibility v3

### Inputs

```text
Features v7
Price Quality v2
governed corporate-action status
```

### Responsibilities

- aplicar lookback mínimo;
- verificar target futuro;
- bloquear samples inadequados;
- produzir universo elegível.

### Contract

```text
lookback = 21 observations
target horizon = exact global B3 T+5
```

### State

```text
Eligible: 57,441
Ineligible: 557
```

### Gate

Somente `ml_eligible = true` pode seguir para avaliação e treinamento governado.

---

## 11. Etapa 9 — Training Dataset v4

### Input

```text
ML Eligibility v3
```

### Output

```text
Training Dataset v4
```

### Target

```text
target_return_next_5d
```

### Target semantics

```text
COMPOUNDED_DAILY_RETURN_ECONOMIC
GLOBAL_B3_TRADING_DAYS
```

### State

```text
57,998 rows
319 tickers
duplicates = 0
target nulls = 0
target nonfinite = 0
```

O Training Dataset mantém linhas elegíveis e inelegíveis com seus metadados; consumidores governados filtram conforme a política aplicável.

---

## 12. Etapa 10 — Temporal Split v3

### Input

Training Dataset v4.

### Outputs

```text
train.parquet
validation.parquet
test.parquet
```

### State

```text
TRAIN       51,207 rows
VALIDATION   1,235 rows
TEST         2,501 rows
```

### Purge contract

```text
TRAIN target max
<
VALIDATION feature min

VALIDATION target max
<
TEST feature min
```

### Holdout contract

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

### Gate

```text
overlap = 0
```

---

## 13. Etapa 11 — Baseline v5

### Inputs

```text
TRAIN
VALIDATION
Feature Contract v3
```

### TEST

Não é usado para seleção.

### Models

```text
Dummy
Linear Regression
Random Forest
```

### Purpose

- sanity check;
- baseline de performance;
- comparação simples;
- validação do pipeline ML.

Resultado observado:

```text
Linear Regression
→ melhor regressão na validation
```

A direção isoladamente não foi forte o suficiente para ser tratada como contrato de performance.

---

## 14. Etapa 12 — Walk-Forward v1

### Input

```text
Training Dataset v4
```

O TEST split é consultado apenas para a fronteira temporal.

### Policy

```text
EXPANDING_WINDOW_PURGED
```

### Structure

```text
12 folds
5 validation sessions/fold
3 models/fold
36 metric rows
```

### Purge

Para todo fold:

```text
train_target_max < validation_start
```

### TEST protection

```text
test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

### Aggregate result

Entre os três modelos avaliados, Linear Regression apresentou o melhor desempenho agregado na execução validada.

Isso é evidência experimental, não gate de saúde.

---

## 15. Etapa 13 — Pipeline Health v3

### Inputs monitorados

```text
Adjusted Prices
Price Discontinuities
Price History
Price Quality
Review Queue
Features
ML Eligibility
Training Dataset
Temporal Train
Temporal Validation
Temporal Test
Walk-Forward Metrics
Walk-Forward Summary
```

### Freshness modes

```text
DATA_DATE
TARGET_DATE
EVENT_DRIVEN
HISTORICAL_SPLIT
HISTORICAL_EXPERIMENT
```

### Execution

```powershell
python -m src.observability.pipeline_health.builder --reference-date 2026-09-01
```

### Validated result

```text
12 datasets
212 PASS
0 WARN
0 FAIL
Overall status: PASS
```

### Responsibilities

- artifact existence;
- schema;
- duplicates;
- dates;
- freshness;
- versions;
- semantics;
- cross-dataset reconciliation;
- temporal split integrity;
- purge;
- holdout protection;
- Walk-Forward reconciliation.

---

## 16. Etapa 14 — Controlled Failure v1

### Purpose

Provar que o monitor entra em FAIL quando recebe uma condição inválida conhecida.

### Scenario

```text
features_duplicate_key
```

### Process

```text
Official Features
→ temporary copy
→ duplicate one row
→ real Pipeline Health inspection
→ expected FAIL
→ delete temp artifact
→ confirm official unchanged
```

### Result

```text
Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1

Official dataset unchanged: True
Temporary artifact removed: True

Controlled Failure Test: PASS
```

---

## 17. Human governance points

A pipeline não é completamente automática por design.

O principal ponto de intervenção governada é:

```text
Price Discontinuity Detector
        |
        v
Corporate Action Registry
        |
        +--> confirmed
        +--> rejected
        +--> not applicable
        +--> pending/review
```

Essa separação é intencional.

Ela impede que uma heurística quantitativa altere silenciosamente a semântica econômica do histórico.

---

## 18. Failure boundaries

A Fase 0 possui gates explícitos.

### Data integrity failures

```text
missing artifact
unreadable parquet
duplicate governed key
missing required columns
invalid dates
```

### Freshness failures

Aplicáveis apenas quando a semântica do dataset exige freshness operacional.

### Semantic contract failures

```text
wrong dataset version
wrong price semantics
wrong return semantics
wrong target horizon
wrong target semantics
```

### Temporal failures

```text
split overlap
target crossing next split
walk-forward purge violation
validation crossing TEST
```

### Experiment integrity failures

```text
missing folds
missing models
duplicate fold/model
nonfinite metrics
summary != fold_metrics
TEST marked as used
```

---

## 19. Execution principles

A pipeline segue os seguintes princípios operacionais:

```text
1. Upstream validado é tratado como congelado.
2. Downstream não altera dados upstream.
3. Contratos são explícitos.
4. Temporalidade é parte do schema semântico.
5. Corporate actions são governadas.
6. ML só consome features allowlisted.
7. TEST final é reservado.
8. Observability não depende de performance do modelo.
9. Falhas controladas nunca corrompem o dado oficial.
10. Fase 0 prioriza confiança da base antes de sofisticação de modelo.
```

---

## 20. Ordem recomendada de reprocessamento

Quando toda a cadeia precisar ser reconstruída, a ordem lógica é:

```text
1. Ingestion
2. RAW validation
3. Parsing / normalization
4. SILVER
5. Price Discontinuities
6. Corporate Action Registry / Review
7. Adjusted Prices
8. Price Quality
9. Price History
10. Features
11. ML Eligibility
12. Training Dataset
13. Temporal Split
14. Baseline
15. Walk-Forward
16. Pipeline Health
17. Controlled Failure only when intentionally testing observability
```

O Controlled Failure não faz parte de uma execução normal de produção.

---

## 21. Fase 0 versus Fase 1

### Fase 0

```text
Local execution
Governed datasets
Gold Analytics
Gold Quality
Gold ML
Baseline
Walk-Forward
Observability
Documentation
```

### Fase 1

Planejada para evolução cloud/AWS e componentes adicionais.

Possíveis evoluções incluem:

```text
orchestration
cloud storage
distributed processing
managed observability
alerting
deployment
serving
LLM / Agents
Analytics consumption
```

Itens de Fase 1 não são apresentados como entregues na Fase 0.

---

## 22. Status

```text
Core data pipeline      VALIDATED
Corporate governance    VALIDATED
ML data pipeline        VALIDATED
Temporal validation     VALIDATED
Walk-Forward            VALIDATED
Observability           VALIDATED
Controlled failure      VALIDATED
Pipeline lineage        DOCUMENTED
```
