# Data Platform Architecture — FII Data & AI Platform

## 1. Objetivo

Este documento detalha a arquitetura técnica da plataforma de dados da FII Data & AI Platform na Fase 0.

A visão é organizada por:

```text
sources
storage layers
processing
governance
quality
ML
observability
consumption boundaries
```

---

## 2. Arquitetura em camadas

```text
+-------------------------------------------------------------+
|                     EXTERNAL SOURCES                        |
|                  B3 | CVM | Funds Explorer                  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                            RAW                              |
|        source-preserving / replayable / traceable           |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                           SILVER                            |
| parsing | typing | normalization | identity | standardization|
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                         GOLD LAYER                          |
|                                                             |
|   +------------------+  +----------------+  +--------------+ |
|   |    Analytics     |  |    Quality     |  |      ML      | |
|   +------------------+  +----------------+  +--------------+ |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                      OBSERVABILITY                          |
| Pipeline Health | Controlled Failure | Evidence             |
+-------------------------------------------------------------+
```

---

## 3. Storage model

A Fase 0 usa persistência local em diretórios versionados logicamente.

Estrutura principal:

```text
data/
├── raw/
├── silver/
├── gold/
│   ├── analytics/
│   ├── quality/
│   ├── ml/
│   └── ai/
└── observability/
```

---

## 4. RAW architecture

A RAW mantém a granularidade e formato original quando possível.

Exemplo B3:

```text
data/raw/b3/
└── year=YYYY/
    └── month=MM/
        └── day=DD/
```

Princípios:

```text
immutable source intent
partition by acquisition/business date
replayable ingestion
no business decisions
```

---

## 5. SILVER architecture

A Silver converte fonte em estrutura analítica consistente.

Responsabilidades:

```text
parse
type
normalize
standardize identity
remove source-format complexity
```

A Silver serve como camada de desacoplamento entre origem e Gold.

---

## 6. Gold Analytics architecture

Estrutura:

```text
data/gold/analytics/
├── fii_daily_snapshot/
├── fii_price_discontinuities/
├── fii_corporate_action_adjusted_prices/
└── fii_price_history/
```

### fii_price_discontinuities

Responsabilidade:

```text
candidate detection
```

Não decide corporate action.

### fii_corporate_action_adjusted_prices

Responsabilidade:

```text
structural adjustment
economic adjustment
economic return generation
```

### fii_price_history

Responsabilidade:

```text
governed time series
economic returns
feature upstream
```

---

## 7. Gold Quality architecture

Estrutura:

```text
data/gold/quality/
├── fii_price_quality/
└── fii_corporate_action_review_queue/
```

### Price Quality

Classifica qualidade por observação.

### Review Queue

Materializa exceções pendentes de governança.

---

## 8. Gold ML architecture

Estrutura:

```text
data/gold/ml/
├── fii_features/
├── fii_ml_eligibility/
├── fii_training_dataset/
├── fii_temporal_split/
└── fii_walk_forward/
```

Fluxo:

```text
Price History
     |
     v
Features
     |
     v
Eligibility
     |
     v
Training Dataset
     |
  +--+----------------+
  |                   |
  v                   v
Temporal Split     Walk-Forward
  |
  v
Baseline
```

---

## 9. AI boundary

Estrutura prevista/observada:

```text
data/gold/ai/
├── fii_context/
└── documents/
```

Na Fase 0, essa área representa fronteira arquitetural e espaço de evolução.

Componentes LLM/Agents completos ficam fora do escopo de fechamento da Fase 0.

---

## 10. Corporate Action architecture

A arquitetura separa três responsabilidades:

```text
Detection
Governance
Application
```

### Detection

```text
Price Discontinuities v5
```

### Governance

```text
Corporate Action Registry v2
Review Queue
human decision
```

### Application

```text
Corporate Action Adjusted Prices v3
```

Esse desenho reduz risco de propagação automática de falso positivo.

---

## 11. Economic semantics architecture

A plataforma usa duas curvas conceituais:

```text
price-only
economic
```

A econômica incorpora:

```text
structural adjustments
cash distributions
in-kind value
```

O retorno econômico downstream é propagado até:

```text
Price History
Features
Training Dataset
Walk-Forward
```

---

## 12. ML feature architecture

Feature engineering usa janelas:

```text
5d
10d
20d
```

A entrada do modelo é controlada por Feature Contract v3.

Categorias de features:

```text
returns
volatility
moving-average relations
cross-window spreads
volume/trades ratios
```

Não são incluídos diretamente:

```text
corporate-action event payloads
future information
non-governed columns
```

---

## 13. Temporal architecture

A temporalidade é tratada como dimensão de arquitetura.

### Training target

```text
T+5 exact global B3 trading sessions
```

### Split purge

```text
target_date before next split feature_date
```

### Walk-Forward

```text
expanding window
purged folds
non-overlapping validation windows
```

### Final TEST

```text
reserved
untouched
no model selection
```

---

## 14. Observability architecture

Estrutura:

```text
src/observability/
├── pipeline_health/
└── controlled_failure/
```

Outputs:

```text
data/observability/
├── pipeline_health/
└── controlled_failure/
```

Documentation:

```text
docs/observability/
```

---

## 15. Pipeline Health architecture

Pipeline Health v3 executa checks em duas categorias.

### Dataset checks

```text
file existence
parquet readability
row count
required columns
duplicates
date parsing
freshness
```

### Platform contract checks

```text
semantic versions
economic semantics
cross-dataset reconciliation
split integrity
purge
holdout
walk-forward contract
metric reconciliation
```

Resultado validado:

```text
212 PASS
0 WARN
0 FAIL
```

---

## 16. Freshness architecture

Freshness é semântica, não genérica.

### DATA_DATE

Usado em:

```text
Adjusted Prices
Price History
Price Quality
Features
```

### TARGET_DATE

Usado em:

```text
ML Eligibility
Training Dataset
```

### EVENT_DRIVEN

Usado em:

```text
Price Discontinuities
Review Queue
```

### HISTORICAL_SPLIT

Usado em:

```text
Train
Validation
Test
```

### HISTORICAL_EXPERIMENT

Usado em:

```text
Walk-Forward
```

---

## 17. Failure architecture

A plataforma distingue:

```text
data failure
semantic failure
temporal failure
experiment integrity failure
```

Exemplos:

### Data failure

```text
missing file
unreadable parquet
duplicate key
```

### Semantic failure

```text
wrong version
wrong return semantics
wrong target horizon
```

### Temporal failure

```text
split overlap
purge violation
validation crossing test
```

### Experiment failure

```text
missing folds
nonfinite metrics
summary mismatch
TEST used
```

---

## 18. Controlled Failure architecture

Controlled Failure v1 prova o caminho de falha sem tocar no dado oficial.

```text
official dataset
      |
      | read
      v
temporary copy
      |
      | inject fault
      v
Pipeline Health inspection
      |
      v
expected FAIL
      |
      v
cleanup
```

Essa estratégia permite teste real do detector com baixo risco.

---

## 19. Data contracts and lineage

Documentação arquitetural complementar:

```text
docs/lineage/
docs/data-contracts/
docs/observability/
```

Esses documentos servem como contrato humano e referência técnica.

---

## 20. Local execution model

A Fase 0 roda localmente em:

```text
Windows
PowerShell
Python
VS Code
Git
Parquet
```

O objetivo é validar lógica, contratos e arquitetura antes da migração para infraestrutura cloud.

---

## 21. Versioning model

Componentes principais possuem versões semânticas internas:

```text
Price Discontinuities v5
Corporate Action Registry v2
Adjusted Prices v3
Price Quality v2
Price History v3
Features v7
ML Eligibility v3
Training Dataset v4
Temporal Split v3
Feature Contract v3
Baseline v5
Walk-Forward v1
Pipeline Health v3
Controlled Failure v1
```

Essas versões ajudam a detectar incompatibilidades downstream.

---

## 22. Freeze model

Um artefato validado é tratado como upstream congelado.

Reabertura somente por:

```text
real bug
contract inconsistency
proven semantic error
```

Não é justificativa suficiente:

```text
querer melhorar métrica
nova ideia opcional
refatoração estética
```

Esses itens entram em backlog ou nova versão.

---

## 23. Security and safety posture

Na Fase 0:

- fontes são lidas e transformadas localmente;
- Controlled Failure não altera fonte oficial;
- TEST final é protegido por contrato;
- histórico operacional de observability é separado de documentação estável;
- mutações de dados devem ocorrer por builders, não edição manual ad hoc.

---

## 24. Scalability boundary

A arquitetura local foi desenhada para permitir evolução.

Limites naturais da Fase 0:

```text
single-machine execution
local filesystem
manual execution sequencing
local observability
```

Esses limites motivam a Fase 1.

---

## 25. Target architecture — Fase 1

Possível mapeamento AWS:

```text
RAW/SILVER/GOLD
→ Amazon S3

Metadata / Catalog
→ AWS Glue Data Catalog

SQL analytics
→ Athena

Orchestration
→ Step Functions / MWAA

Batch processing
→ Glue / ECS / Batch

Monitoring
→ CloudWatch

ML
→ SageMaker

API / serving
→ API Gateway + Lambda / ECS

Secrets
→ Secrets Manager

Infrastructure
→ Terraform / CloudFormation
```

A escolha final deve ser feita na Fase 1 conforme custo, simplicidade e necessidade real.

---

## 26. Non-goals da Fase 0

Não são objetivos concluídos:

```text
production cloud deployment
high availability
real-time streaming
distributed compute
managed alerting
public API
model serving
LLM/Agents production
automated CI/CD production
```

Esses pontos não devem ser apresentados como entregues.

---

## 27. Arquitetura de consumo futura

Consumidores futuros podem incluir:

```text
Analytics dashboards
ML scoring
portfolio analysis
DARF support
LLM context
Agents
API
```

Esses consumidores devem usar Gold governada, nunca RAW diretamente.

---

## 28. Architecture decision summary

```text
Source preservation       -> RAW
Technical normalization   -> SILVER
Business semantics        -> GOLD
Quality gates             -> Gold Quality
ML readiness              -> Gold ML
Temporal correctness      -> Split + Walk-Forward
Operational trust         -> Observability
Human governance          -> Corporate Action Registry
Cloud scale               -> Phase 1
```

---

## 29. Status

```text
Layered architecture          VALIDATED
Gold semantic architecture    VALIDATED
ML architecture               VALIDATED
Temporal architecture         VALIDATED
Observability architecture    VALIDATED
Phase 0/Phase 1 boundary      DOCUMENTED
Data platform architecture    DOCUMENTED
```
