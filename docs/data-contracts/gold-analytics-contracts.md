# Gold Analytics Contracts — FII Data & AI Platform

## 1. Objetivo

Este documento descreve os contratos dos principais datasets Gold Analytics e Gold Quality da Fase 0.

Esses contratos tornam explícitos:

- chave;
- versão;
- semântica;
- dependências;
- regras de integridade;
- política de freshness;
- consumers.

---

## 2. Corporate Action Adjusted Prices v3

### Path

```text
data/gold/analytics/fii_corporate_action_adjusted_prices/
```

### Version

```text
v3
```

### Grain

```text
1 row por trade_date + ticker
```

### Key

```text
trade_date + ticker
```

### Estado validado

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

### Semântica

```text
price_semantics
= STRUCTURALLY_ADJUSTED_PRICE

return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

### Economic return

```text
daily_return_economic =
(close_price_adjusted + total_economic_value_adjusted)
/
previous_close_price_adjusted
- 1
```

### Freshness

```text
DATA_DATE
```

Data usada:

```text
trade_date
```

### Consumers

```text
Price Quality v2
Price History v3
```

---

## 3. Price Discontinuities v5

### Path

```text
data/gold/analytics/fii_price_discontinuities/
```

### Version

```text
v5
```

### Grain

Evento/candidato de descontinuidade por ticker e data.

### Estado validado

```text
Candidates: 79
Tickers: 38
```

### Governed statuses observados

```text
REJECTED: 59
CONFIRMED: 16
NOT_APPLICABLE: 4
PENDING: 0
```

### Contract principle

```text
DETECTOR != DECISION
```

O dataset detecta candidatos. Ele não confirma automaticamente corporate actions.

### Freshness

```text
EVENT_DRIVEN
```

A idade do último evento não é staleness.

### Consumers

```text
Corporate Action Registry v2
Corporate Action Review Queue
```

---

## 4. Corporate Action Registry v2

### Version

```text
v2
```

### Estado validado

```text
Rows: 79
Fields: 20
Confirmed actions: 16
Pending: 0
```

### Papel

Armazenar decisão governada sobre corporate actions.

### Econômica

O registro suporta componentes:

```text
cash
in-kind
total economic value
```

### Contract rule

Somente eventos governados podem modificar a curva de preços/retornos downstream.

---

## 5. Corporate Action Review Queue

### Path

```text
data/gold/quality/fii_corporate_action_review_queue/
```

### Grain

Caso pendente de revisão por evento/ticker.

### Empty policy

```text
allow_empty = true
```

### Estado validado

```text
Rows: 0
Pending: 0
```

### Freshness

```text
EVENT_DRIVEN
```

### Contract principle

Fila vazia significa ausência de casos pendentes, não falha do pipeline.

---

## 6. Price History v3

### Path

```text
data/gold/analytics/fii_price_history/
```

### Version

```text
price_history_version = v3
```

### Grain

```text
1 row por trade_date + ticker
```

### Key

```text
trade_date + ticker
```

### Estado validado

```text
Rows: 68,747
Tickers: 372
Sessions: 250
Duplicates: 0
```

### Required semantics

```text
price_semantics
= STRUCTURALLY_ADJUSTED_PRICE

return_semantics
= COMPOUNDED_DAILY_RETURN_ECONOMIC

corporate_action_value_semantics
= TOTAL_ECONOMIC_VALUE_CASH_PLUS_IN_KIND
```

### Freshness

```text
DATA_DATE
```

### Consumer

```text
Features v7
```

---

## 7. Price Quality v2

### Path

```text
data/gold/quality/fii_price_quality/
```

### Version

```text
v2
```

### Grain

```text
1 row por trade_date + ticker
```

### Key

```text
trade_date + ticker
```

### Estado validado

```text
Rows: 68,747
Tickers: 372

PASS:   68,592
REVIEW:    155
FAIL:        0
```

### Policy

Corporate action confirmada não implica REVIEW automaticamente.

Possíveis causas de REVIEW incluem:

```text
pending corporate action
long gap
micro-price condition
```

### Freshness

```text
DATA_DATE
```

### Consumer

```text
ML Eligibility v3
```

---

## 8. Daily Snapshot

### Paths observados

```text
data/gold/analytics/fii_daily_snapshot/...
data/gold/fii_daily_snapshot/...
```

### Contract note

A Fase 0 identificou dois caminhos físicos históricos.

A observabilidade não escolheu um deles silenciosamente como canônico.

Qualquer consolidação futura deve ser uma decisão explícita de arquitetura.

---

## 9. Cross-Dataset Contracts

### Price History vs Features

Contrato validado:

```text
row_count(Price History)
=
row_count(Features)
```

Estado:

```text
68,747 = 68,747
```

### Adjusted Prices downstream

```text
Adjusted Prices
→ Price History
→ Features
```

e

```text
Adjusted Prices
→ Price Quality
→ ML Eligibility
```

Semântica econômica deve permanecer consistente entre essas cadeias.

---

## 10. Freshness Modes

### DATA_DATE

Aplicável a:

```text
Adjusted Prices
Price History
Price Quality
```

Critério:

```text
latest operational data date
```

### EVENT_DRIVEN

Aplicável a:

```text
Price Discontinuities
Review Queue
```

Critério:

```text
último evento não define staleness
```

---

## 11. Governance Contract

Corporate action segue:

```text
detect
→ review/governance
→ decision
→ economic adjustment
```

É proibido por contrato semântico:

```text
extreme return
→ automatic confirmed corporate action
```

---

## 12. Data Mutation Policy

Datasets Gold são derivados dos upstreams governados.

Correções devem ocorrer no builder/regra responsável.

Não usar:

```text
edição manual de Parquet
```

como mecanismo normal de correção.

---

## 13. Observability Contract

Na execução validada do Pipeline Health v3:

```text
Adjusted Prices      PASS
Price Discontinuities PASS
Price History         PASS
Price Quality         PASS
Review Queue          PASS
```

Esses checks cobrem existência, schema mínimo, duplicidades, datas, freshness aplicável e semânticas principais.

---

## 14. Status

```text
Adjusted Prices v3        VALIDATED
Price Discontinuities v5  VALIDATED
Registry v2               VALIDATED
Review Queue              VALIDATED
Price History v3          VALIDATED
Price Quality v2          VALIDATED
Gold Analytics contracts  DOCUMENTED
```
