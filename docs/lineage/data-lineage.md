# Data Lineage — FII Data & AI Platform

## 1. Objetivo

Este documento descreve a linhagem de dados da FII Data & AI Platform na Fase 0, cobrindo as principais fontes externas, camadas de persistência, datasets Gold, artefatos de ML e observabilidade.

A finalidade é responder, para cada artefato relevante:

```text
de onde vem
→ como é transformado
→ qual dataset produz
→ qual contrato carrega
→ quem consome
```

A Fase 0 é local. A evolução para AWS pertence à Fase 1.

---

## 2. Visão macro

```text
B3 / CVM / Funds Explorer
          |
          v
        RAW
          |
          v
       SILVER
          |
          +------------------------------+
          |                              |
          v                              v
  Gold Daily Snapshot          Price Discontinuities v5
                                         |
                                         v
                             Corporate Action Registry v2
                                         |
                                         +----------------------+
                                         |                      |
                                         v                      v
                              Review Queue                governed decisions
                                         |                      |
                                         +----------+-----------+
                                                    |
                                                    v
                              Corporate Action Adjusted Prices v3
                                                    |
                               +--------------------+--------------------+
                               |                                         |
                               v                                         v
                     Price Quality v2                          Price History v3
                               |                                         |
                               +--------------------+--------------------+
                                                    |
                                                    v
                                              Features v7
                                                    |
                                                    v
                                         ML Eligibility v3
                                                    |
                                                    v
                                         Training Dataset v4
                                                    |
                                                    v
                                          Temporal Split v3
                                                    |
                                  +-----------------+-----------------+
                                  |                                   |
                                  v                                   v
                            Baseline v5                       Walk-Forward v1
                                                                      |
                                                                      v
                                                              Observability v3
```

Observability é uma camada transversal. Ela monitora artefatos e contratos, mas não produz dados de negócio.

---

## 3. Fontes externas

### 3.1 B3

Papel:

- fonte primária de dados de pregão;
- fornece preços, volume operacional e identificadores de instrumentos;
- serve de base para a série histórica de FIIs.

Exemplo de ingestão validada na Fase 0:

```text
Pregão: 2026-08-27
Download automatizado: SPRE260827.zip
Formato interno: XML
Registros parseados: 50,390
```

Principais campos ingeridos:

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

Consumidores:

```text
RAW B3
→ SILVER
→ Gold Analytics / ML
```

---

### 3.2 CVM

Papel:

- cadastro e classificação oficial de fundos;
- identificação de classes de fundos;
- enriquecimento de identidade e governança cadastral.

Na Fase 0, o parser de classes foi validado com detecção automática de encoding.

Exemplo de distribuição observada:

```text
FII: 1,528 classes
```

Consumidores:

```text
RAW CVM
→ SILVER / identity layer
→ Gold
```

---

### 3.3 Funds Explorer

Papel:

- fonte complementar usada no projeto para informações do universo de FIIs;
- participa do enriquecimento e identificação de entidades.

A fonte é complementar e não substitui contratos oficiais da B3/CVM.

---

## 4. RAW

A camada RAW preserva os dados de origem com mínima transformação.

Objetivos:

- reprodutibilidade;
- rastreabilidade;
- possibilidade de reprocessamento;
- preservação do conteúdo recebido da fonte.

Exemplo de particionamento B3:

```text
data/raw/b3/
└── year=2026/
    └── month=08/
        └── day=27/
            └── b3_download_20260827.zip
```

A camada RAW não é consumida diretamente por ML.

---

## 5. SILVER

A camada SILVER normaliza e consolida dados técnicos usados pelos builders downstream.

Estado validado da série B3 utilizada na Fase 0:

```text
Sessões: 250
Período: 2025-08-29 -> 2026-08-28
Rows: 68,747
Tickers: 372
```

Papel principal:

```text
RAW
→ parsing
→ tipagem
→ normalização
→ identidade
→ SILVER
```

A SILVER é o principal upstream para os datasets analíticos Gold.

---

## 6. Gold Analytics

### 6.1 FII Daily Snapshot

Papel:

- visão diária consolidada;
- consumo analítico;
- base para aplicações downstream de apresentação e análise.

Há dois caminhos físicos históricos observados no projeto:

```text
data/gold/analytics/fii_daily_snapshot/...
data/gold/fii_daily_snapshot/...
```

A Fase 0 não escolheu silenciosamente um caminho canônico durante a implementação da observabilidade.

Essa decisão deve permanecer explícita caso a estrutura seja consolidada posteriormente.

---

### 6.2 Price Discontinuities v5

Dataset:

```text
data/gold/analytics/fii_price_discontinuities/
```

Papel:

- detectar movimentos extremos ou descontinuidades de preço;
- produzir candidatos para análise de corporate actions;
- separar detecção quantitativa de decisão de governança.

Estado validado:

```text
Candidates: 79
Tickers: 38

Registry statuses:
REJECTED: 59
CONFIRMED: 16
NOT_APPLICABLE: 4
PENDING: 0
```

Regra arquitetural:

```text
DETECTOR != DECISION
```

O detector identifica candidatos. Ele não confirma corporate actions.

Consumidor principal:

```text
Corporate Action Registry v2
```

---

### 6.3 Corporate Action Adjusted Prices v3

Dataset:

```text
data/gold/analytics/fii_corporate_action_adjusted_prices/
```

Papel:

- ajustar estruturalmente a curva de preço;
- incorporar efeitos econômicos de corporate actions;
- produzir uma série consistente para cálculo de retorno.

Estado validado:

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

Semântica econômica:

```text
daily_return_economic =
(close_adjusted + total_economic_value_adjusted)
/
previous_close_adjusted
- 1
```

Semântica de corporate action:

```text
TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

Consumidores:

```text
Price Quality v2
Price History v3
```

---

### 6.4 Price History v3

Dataset:

```text
data/gold/analytics/fii_price_history/
```

Estado validado:

```text
Rows: 68,747
Tickers: 372
Sessions: 250
Duplicates: 0
```

Contrato:

```text
price_history_version = v3
price_semantics = STRUCTURALLY_ADJUSTED_PRICE
return_semantics = COMPOUNDED_DAILY_RETURN_ECONOMIC
corporate_action_value_semantics =
TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

Papel:

- consolidar a série temporal governada;
- fornecer retornos econômicos;
- servir como upstream principal de Features v7.

Consumidor:

```text
Features v7
```

---

## 7. Gold Quality

### 7.1 Price Quality v2

Dataset:

```text
data/gold/quality/fii_price_quality/
```

Estado validado:

```text
Rows: 68,747
Tickers: 372

PASS:   68,592
REVIEW:    155
FAIL:        0
```

Papel:

- marcar qualidade do histórico de preços;
- distinguir eventos confirmados de casos realmente problemáticos;
- fornecer sinal governado para elegibilidade de ML.

Casos REVIEW podem incluir:

- pending corporate action;
- long gap;
- micro-price situations.

Corporate actions confirmadas não são automaticamente consideradas falha de qualidade.

Consumidor:

```text
ML Eligibility v3
```

---

### 7.2 Corporate Action Review Queue

Dataset:

```text
data/gold/quality/fii_corporate_action_review_queue/
```

Papel:

- expor casos pendentes de decisão;
- preservar governança humana;
- separar processamento automático de confirmação manual.

Estado validado no fechamento:

```text
Rows: 0
Pending cases: 0
```

O dataset vazio é permitido por contrato.

---

## 8. Corporate Action Registry v2

Papel:

- registro governado das decisões sobre corporate actions;
- armazenamento da classificação final;
- suporte aos ajustes de preço e retorno econômico.

Estado validado:

```text
Rows: 79
Fields: 20
Confirmed actions: 16
Pending: 0
```

Ações governadas incluem componentes:

```text
cash
in-kind
total economic value
```

A linhagem correta é:

```text
Price Discontinuities
        |
        v
candidate detection
        |
        v
Corporate Action Registry
        |
        v
human/governed decision
        |
        v
Adjusted Prices
```

Nunca:

```text
extreme return
= automatically confirmed corporate action
```

---

## 9. Gold ML

### 9.1 Features v7

Dataset:

```text
data/gold/ml/fii_features/fii_features.parquet
```

Estado validado:

```text
Rows: 68,747
Tickers: 372
Feature-ready rows: 61,913
```

Janelas:

```text
5
10
20
```

Contrato semântico:

```text
feature_version = v7

feature_corporate_action_policy =
ECONOMIC_EFFECT_EMBEDDED_IN_RETURNS_NO_DIRECT_CA_PAYLOAD_FEATURES
```

A feature layer não carrega payload direto de corporate action como feature.

O efeito econômico já está incorporado na série de retornos.

Principais consumers:

```text
ML Eligibility v3
Baseline v5
Walk-Forward v1
```

---

### 9.2 ML Eligibility v3

Dataset:

```text
data/gold/ml/fii_ml_eligibility/
```

Estado validado:

```text
Rows: 57,998
Eligible: 57,441
Ineligible: 557
DQ issues: 0
```

Papel:

- decidir quais samples podem entrar em treinamento;
- aplicar qualidade, lookback e horizonte futuro;
- bloquear condições incompatíveis com ML.

Políticas relevantes:

```text
lookback = 21 observations
target = exact global B3 T+5
```

Bloqueadores incluem:

```text
Price Quality REVIEW
Registry REJECTED
```

Eventos confirmados de corporate action e extremos isolados podem ser informativos sem automaticamente invalidar uma amostra.

Consumidor:

```text
Training Dataset v4
```

---

### 9.3 Training Dataset v4

Dataset:

```text
data/gold/ml/fii_training_dataset/
```

Estado validado:

```text
Rows: 57,998
Tickers: 319
Duplicates: 0
Target nulls: 0
Target nonfinite: 0
```

Target:

```text
target_return_next_5d
```

Contrato:

```text
training_dataset_version = v4
target_horizon = 5
target_horizon_semantics = GLOBAL_B3_TRADING_DAYS
target_return_semantics = COMPOUNDED_DAILY_RETURN_ECONOMIC
```

O target econômico usa crescimento cumulativo de `daily_return_economic` em `(T, U]`.

Foram observados casos em que o target econômico diverge do retorno puramente baseado em preço, evidenciando a necessidade de incorporar corporate actions.

Consumidor:

```text
Temporal Split v3
Walk-Forward v1
```

---

### 9.4 Temporal Split v3

Datasets:

```text
data/gold/ml/fii_temporal_split/train.parquet
data/gold/ml/fii_temporal_split/validation.parquet
data/gold/ml/fii_temporal_split/test.parquet
```

Estado validado:

```text
TRAIN
Rows: 51,207
Feature max: 2026-07-17
Target max: 2026-07-24

VALIDATION
Rows: 1,235
Feature range: 2026-07-27 -> 2026-07-31
Target max: 2026-08-07

TEST
Rows: 2,501
Feature range: 2026-08-10 -> 2026-08-21
```

Contratos:

```text
split_version = v3

split_purge_semantics =
TARGET_DATE_BEFORE_NEXT_SPLIT

test_holdout_policy =
RESERVED_UNTOUCHED_FOR_MODEL_SELECTION
```

Regras:

```text
train.target_date < validation.feature_date
validation.target_date < test.feature_date
```

Overlap validado:

```text
0
```

Consumidores:

```text
Baseline v5
final holdout evaluation
```

---

### 9.5 Feature Contract v3

Papel:

- restringir explicitamente as features permitidas para ML;
- prevenir uso acidental de payloads não governados;
- padronizar a matriz de entrada.

Features permitidas:

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

Total:

```text
18 features
```

---

### 9.6 Baseline v5

Papel:

- criar referência inicial de performance;
- comparar modelos simples e interpretáveis;
- validar pipeline de treinamento sem consumir o TEST final.

Modelos:

```text
DummyRegressor
LinearRegression
RandomForestRegressor
```

Política:

```text
TRAIN -> VALIDATION
TEST reserved
```

O Baseline v5 não é produtor de datasets de negócio.

Ele produz evidência experimental.

---

### 9.7 Walk-Forward v1

Artefatos:

```text
data/gold/ml/fii_walk_forward/fold_metrics.parquet
data/gold/ml/fii_walk_forward/summary.json
```

Contrato:

```text
walk_forward_version = v1
policy = EXPANDING_WINDOW_PURGED
fold_count = 12
validation sessions/fold = 5
models = 3
metric rows = 36
```

Papel:

- medir estabilidade temporal;
- reduzir dependência de uma única janela de validation;
- preservar o TEST final;
- provar purge em múltiplos regimes.

O TEST permanece:

```text
RESERVED_FINAL_HOLDOUT_NO_MODEL_EVALUATION
```

Resultado observado na Fase 0:

```text
Linear Regression
→ melhor resultado agregado entre os 3 modelos avaliados
```

Isso é resultado experimental, não contrato operacional.

---

## 10. Observability

### 10.1 Pipeline Health v3

Implementação:

```text
src/observability/pipeline_health/builder.py
```

Resultado validado:

```text
Datasets monitored: 12
Checks PASS: 212
Checks WARN: 0
Checks FAIL: 0
Overall status: PASS
```

Papel:

- monitorar contratos;
- freshness;
- schema;
- duplicidades;
- reconciliações;
- splits;
- leakage;
- Walk-Forward;
- preservação do TEST.

Observability lê os artefatos downstream, mas não altera seus conteúdos.

---

### 10.2 Controlled Failure v1

Implementação:

```text
src/observability/controlled_failure/runner.py
```

Papel:

- provar que o framework detecta uma quebra conhecida;
- injetar duplicidade apenas em cópia temporária;
- preservar o dataset oficial.

Resultado validado:

```text
Temporary corrupted dataset: FAIL
Duplicate detection: FAIL
Official dataset unchanged: True
Temporary artifact removed: True
Controlled Failure Test: PASS
```

---

## 11. Matriz resumida de lineage

| Artefato | Upstream principal | Consumer principal | Chave / identidade | Versão |
|---|---|---|---|---|
| Silver B3 | RAW B3 | Gold Analytics | trade_date + ticker | — |
| Price Discontinuities | Silver / price series | Registry | event_date + ticker | v5 |
| Corporate Action Registry | Discontinuities + governance | Adjusted Prices | governed event identity | v2 |
| Review Queue | Registry / detected cases | governance | event/ticker | governed queue |
| Adjusted Prices | Price series + Registry | PQ / PH | trade_date + ticker | v3 |
| Price Quality | Adjusted/price series | Eligibility | trade_date + ticker | v2 |
| Price History | Adjusted Prices | Features | trade_date + ticker | v3 |
| Features | Price History | Eligibility / ML | feature_date + ticker | v7 |
| ML Eligibility | Features + PQ | Training | feature_date + ticker | v3 |
| Training Dataset | Eligibility + economic target | Split / Walk-Forward | feature_date + ticker | v4 |
| Temporal Split | Training | Baseline | feature_date + ticker | v3 |
| Walk-Forward Metrics | Training + TEST boundary | Observability | fold_id + model | v1 |
| Pipeline Health | Gold + ML artifacts | operators / evidence | artifact contracts | v3 |

---

## 12. Princípios de lineage

A Fase 0 segue estes princípios:

```text
1. Detector != decisão
2. Dados oficiais upstream são preservados
3. Semântica econômica é propagada downstream
4. ML usa apenas features allowlisted
5. Eligibility antecede treinamento
6. Tempo é tratado como parte do contrato
7. TEST final permanece isolado
8. Observability valida, mas não modifica datasets
9. Artefatos congelados não são reabertos sem bug ou erro semântico comprovado
```

---

## 13. Status da linhagem

```text
External Sources -> RAW -> SILVER          DOCUMENTED
Gold Analytics / Quality                  DOCUMENTED
Corporate Action Governance               DOCUMENTED
Gold ML                                    DOCUMENTED
Temporal Validation                        DOCUMENTED
Observability                              DOCUMENTED
```

A linhagem descrita neste documento representa o estado validado da Fase 0.
