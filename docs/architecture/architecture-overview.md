# Architecture Overview — FII Data & AI Platform

## 1. Objetivo

Este documento apresenta a visão arquitetural da FII Data & AI Platform na Fase 0.

A plataforma foi construída localmente com foco em:

- ingestão e padronização de dados;
- governança de corporate actions;
- datasets analíticos confiáveis;
- qualidade de dados;
- preparação de dados para ML;
- validação temporal;
- observabilidade;
- documentação e rastreabilidade.

A Fase 0 prioriza confiança dos dados e contratos explícitos antes de expansão para cloud.

---

## 2. Princípios arquiteturais

A arquitetura segue os princípios:

```text
1. RAW preserva origem
2. SILVER normaliza
3. GOLD aplica semântica de negócio
4. Detector != decisão
5. Corporate actions são governadas
6. Retorno econômico é tratado explicitamente
7. ML consome apenas features allowlisted
8. Temporalidade é parte do contrato
9. TEST final é preservado
10. Observability valida sem alterar datasets
11. Camadas validadas ficam congeladas
12. Fase 0 local, Fase 1 cloud/AWS
```

---

## 3. Visão macro

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

---

## 4. Camada de fontes

### B3

Fonte principal de dados de pregão.

Responsabilidades:

- preços;
- negociações;
- datas de sessão;
- identificadores de instrumentos.

### CVM

Fonte oficial cadastral e classificatória.

Responsabilidades:

- identificação institucional;
- classe de fundo;
- suporte à governança de identidade.

### Funds Explorer

Fonte complementar usada para enriquecimento de informações do universo de FIIs.

---

## 5. RAW

Objetivo:

```text
preservar exatamente a origem
```

Responsabilidades:

- armazenar arquivos recebidos;
- permitir reprocessamento;
- manter rastreabilidade da fonte.

A RAW não deve conter lógica de negócio.

Exemplo:

```text
data/raw/b3/year=2026/month=08/day=27/
```

---

## 6. SILVER

Objetivo:

```text
transformar dados brutos em dados tecnicamente consistentes
```

Responsabilidades:

- parsing;
- encoding;
- tipagem;
- normalização;
- identidade;
- consolidação de campos técnicos.

Estado validado da base B3 utilizada:

```text
250 sessões
2025-08-29 -> 2026-08-28
68,747 rows
372 tickers
```

A Silver não decide corporate actions e não aplica política de ML.

---

## 7. Gold Analytics

A Gold Analytics adiciona semântica de negócio e séries governadas.

Principais componentes:

```text
FII Daily Snapshot
Price Discontinuities
Corporate Action Adjusted Prices
Price History
```

### Price Discontinuities v5

Detecta candidatos a descontinuidade.

```text
79 candidates
38 tickers
```

Regra:

```text
DETECTOR != DECISION
```

### Corporate Action Adjusted Prices v3

Aplica decisões governadas de corporate actions.

Semânticas:

```text
price_semantics
= STRUCTURALLY_ADJUSTED_PRICE

return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

### Price History v3

Entrega a série temporal governada usada por Features.

```text
68,747 rows
372 tickers
250 sessions
```

---

## 8. Gold Quality

Responsável por qualidade e governança operacional.

Principais componentes:

```text
Price Quality v2
Corporate Action Review Queue
```

### Price Quality v2

Estado:

```text
PASS:   68,592
REVIEW:    155
FAIL:        0
```

A qualidade não trata corporate action confirmada como erro automaticamente.

### Review Queue

Representa casos pendentes de análise.

Estado validado:

```text
0 pending rows
```

Fila vazia é válida.

---

## 9. Corporate Action Governance

A governança de corporate actions é um ponto central da arquitetura.

Fluxo:

```text
Price Discontinuity Detector
          |
          v
candidate
          |
          v
Corporate Action Registry v2
          |
     +----+----+
     |         |
     v         v
 review     decision
     |         |
     +----+----+
          |
          v
Adjusted Prices
```

Estados observados:

```text
REJECTED: 59
CONFIRMED: 16
NOT_APPLICABLE: 4
PENDING: 0
```

Princípio:

```text
heurística quantitativa
!=
decisão econômica final
```

---

## 10. Gold ML

A Gold ML prepara datasets governados para modelagem.

Componentes:

```text
Features v7
ML Eligibility v3
Training Dataset v4
Temporal Split v3
Feature Contract v3
Baseline v5
Walk-Forward v1
```

---

## 11. Features v7

Estado:

```text
68,747 rows
372 tickers
61,913 feature-ready rows
```

Janelas:

```text
5
10
20
```

Corporate-action policy:

```text
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

O modelo não recebe payload direto de corporate action.

---

## 12. ML Eligibility v3

Responsável por decidir quais samples podem entrar em ML.

Estado:

```text
57,998 rows
57,441 eligible
557 ineligible
```

Contrato:

```text
lookback = 21 observations
target = exact global B3 T+5
```

---

## 13. Training Dataset v4

Estado:

```text
57,998 rows
319 tickers
duplicates = 0
target nulls = 0
target nonfinite = 0
```

Target:

```text
target_return_next_5d
```

Semântica:

```text
COMPOUNDED_DAILY_RETURN_ECONOMIC
GLOBAL_B3_TRADING_DAYS
```

---

## 14. Temporal Split v3

Estrutura:

```text
TRAIN       51,207 rows
VALIDATION   1,235 rows
TEST         2,501 rows
```

Regras:

```text
train.target_date < validation.feature_date
validation.target_date < test.feature_date
overlap = 0
```

Política:

```text
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

---

## 15. Feature Contract v3

Allowlist de 18 features.

Objetivo:

- impedir consumo acidental de colunas indevidas;
- estabilizar contrato de entrada;
- separar engenharia de feature de modelagem.

---

## 16. Baseline v5

Modelos:

```text
DummyRegressor
LinearRegression
RandomForestRegressor
```

Política:

```text
TRAIN -> VALIDATION
TEST reservado
```

Resultado observado:

```text
Linear Regression
→ melhor desempenho de regressão na validation
```

Resultado experimental não é contrato de saúde.

---

## 17. Walk-Forward v1

Política:

```text
EXPANDING_WINDOW_PURGED
```

Estrutura:

```text
12 folds
5 validation sessions/fold
3 models
36 metric rows
```

Contrato principal:

```text
train_target_max < validation_start
```

TEST:

```text
test_features_used = false
test_targets_used = false
test_predictions_generated = false
```

Resultado agregado observado:

```text
Linear Regression
→ melhor modelo no agregado
```

---

## 18. Observability

A observabilidade é transversal.

Componentes:

```text
Pipeline Health v3
Controlled Failure v1
```

Pipeline Health validado:

```text
12 datasets monitored
212 PASS
0 WARN
0 FAIL
Overall status: PASS
```

Freshness modes:

```text
DATA_DATE
TARGET_DATE
EVENT_DRIVEN
HISTORICAL_SPLIT
HISTORICAL_EXPERIMENT
```

---

## 19. Controlled Failure

Cenário:

```text
features_duplicate_key
```

Fluxo:

```text
official Features
→ temporary copy
→ inject one duplicate
→ Pipeline Health inspection
→ expected FAIL
→ remove temp
→ confirm official unchanged
```

Resultado:

```text
Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1
Official dataset unchanged: True
Temporary artifact removed: True
Test status: PASS
```

---

## 20. Fronteira da Fase 0

A Fase 0 cobre:

```text
local ingestion
local storage
local transformation
Gold datasets
data quality
corporate-action governance
ML preparation
baseline
walk-forward
observability
documentation
```

Não faz parte da Fase 0:

```text
AWS deployment
cloud orchestration
managed storage
managed observability
serving API
production model deployment
LLM/Agents production layer
distributed processing
```

---

## 21. Fase 1 — Direção arquitetural

A Fase 1 deverá evoluir a plataforma para cloud/AWS.

Possíveis componentes:

```text
S3
Glue / Catalog
Athena
Step Functions / MWAA
Lambda
ECS / Batch
CloudWatch
SageMaker
API layer
LLM / Agents
Analytics consumption
```

Esses componentes representam roadmap e não são apresentados como já implementados.

---

## 22. Decisões arquiteturais importantes

### Decisão 1 — confiar na base antes de sofisticar ML

A plataforma prioriza:

```text
data correctness
semantic correctness
temporal correctness
```

antes de otimização de modelo.

### Decisão 2 — corporate actions governadas

Eventos extremos não alteram automaticamente a série econômica.

### Decisão 3 — target econômico

O target incorpora retorno econômico e não somente variação de preço.

### Decisão 4 — TEST reservado

O holdout final não é usado para escolha de modelo.

### Decisão 5 — observability sem performance gate

Pipeline Health valida integridade, não exige performance mínima arbitrária.

### Decisão 6 — freeze rule

Camadas validadas só são reabertas por:

```text
real bug
contract inconsistency
proven semantic error
```

---

## 23. Status

```text
Data architecture        VALIDATED
Corporate governance     VALIDATED
ML architecture          VALIDATED
Temporal architecture    VALIDATED
Observability            VALIDATED
Architecture overview    DOCUMENTED
```
