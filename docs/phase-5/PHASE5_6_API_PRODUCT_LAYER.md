# Phase 5.6 — API / Product Layer

## 1. Objective

Phase 5.6 establishes a product-facing boundary over the governed serving layers created in previous Phase 5 increments.

The main objective is to prevent downstream consumers from depending directly on:

```text
S3 paths
local files
JSONL implementation details
RAW
SILVER
internal pipeline modules
```

The product interface must remain stable even if the underlying serving implementation changes.

---

## 2. Product Architecture

The implemented architecture is:

```text
Consumer
   |
   v
HTTP Adapter
   |
   v
Product Service
   |
   +--> Daily Consumption
   |
   +--> ML Serving
   |
   +--> AI Structured Retrieval
```

The Product Service owns the product-facing contract.

The HTTP Adapter only translates HTTP-compatible requests and responses.

---

## 3. Product Service

Implemented module:

```text
src/product/service.py
```

The service exposes two initial product operations:

```text
get_product_status()
get_fii_context(ticker)
```

---

## 4. Product Status

`get_product_status()` validates that all governed serving layers are ready and aligned.

Sources:

```text
Daily Consumption manifest
ML Serving manifest
AI Structured Retrieval manifest
```

Required state:

```text
status = READY
```

---

## 5. Temporal Alignment

The Product Layer validates:

```text
Daily trade_date
=
ML feature_date
=
AI trade_date
=
AI feature_date
```

Validated business date:

```text
2026-08-28
```

A mismatch causes the Product Layer to fail closed.

---

## 6. Population Alignment

The Product Layer also validates ticker population consistency.

Validated state:

```text
Daily tickers = 267
ML tickers    = 267
AI tickers    = 267
```

All product-facing serving layers must expose the same governed ticker population.

---

## 7. Product Version

Current product contract version:

```text
v1
```

The version is exposed to consumers independently from:

```text
feature contract version
feature version
AI context version
storage implementation
```

---

## 8. FII Context Operation

Product operation:

```text
get_fii_context(ticker)
```

Example:

```text
get_fii_context("GGRC11")
```

The consumer does not need to know:

```text
where the JSONL file exists
how structured retrieval is implemented
which local path is used
which S3 object will eventually back the service
```

---

## 9. HTTP Adapter

Implemented module:

```text
src/product/http_adapter.py
```

The adapter exposes:

```text
GET /health
GET /fii/{ticker}
```

---

## 10. Health Endpoint

Route:

```text
GET /health
```

Validated response:

```text
HTTP 200
status = READY
product_version = v1
business_date = 2026-08-28
ticker_count = 267
```

The response also exposes governed metadata for:

```text
Daily Consumption
ML Serving
AI Structured Retrieval
```

---

## 11. FII Endpoint

Route:

```text
GET /fii/GGRC11
```

Validated response:

```text
HTTP 200
```

The response contains:

```text
identity
market_state
ml_state
provenance
ticker
context_version
```

The quantitative values remain sourced from governed structured datasets.

---

## 12. HTTP Error Handling

The HTTP Adapter defines product-facing error behavior.

Current behavior:

```text
200 -> successful request
400 -> invalid request
404 -> route or ticker not found
503 -> serving layer not ready
```

This isolates downstream consumers from internal Python exceptions.

---

## 13. Lambda Compatibility

The HTTP Adapter uses a Lambda-compatible handler signature:

```text
handler(event, context)
```

It supports an API Gateway HTTP API v2-like request structure.

Therefore, future AWS deployment does not require moving product logic into a Lambda-specific implementation.

---

## 14. Separation of Responsibilities

The architecture intentionally separates:

```text
Product Service
= business/product contract

HTTP Adapter
= transport contract

Serving Layer
= governed data retrieval

Future Lambda
= runtime adapter

Future API Gateway
= external HTTP entry point
```

This avoids coupling the product contract to AWS infrastructure.

---

## 15. Validated Real Product Status

Validated state:

```text
product_version = v1
status = READY
business_date = 2026-08-28
ticker_count = 267

Daily:
dataset = fii_daily_snapshot
rows = 267

ML:
dataset = latest_inference_features
feature_contract_version = v3
feature_version = v7
features = 18

AI:
dataset = fii_structured_context
context_version = v1
ML features = 18
```

---

## 16. Validated Real FII Request

Real request tested:

```text
GET /fii/GGRC11
```

The response successfully exposed the governed GGRC11 context through the Product Layer.

The request did not require the consumer to access:

```text
JSONL directly
Parquet directly
S3 directly
Athena directly
pipeline internals
```

---

## 17. Automated Tests

Phase 5.6 validates:

```text
serving date alignment
serving date mismatch rejection
ticker-count alignment
ticker-count mismatch rejection
READY manifest enforcement
product status generation
product FII lookup
HTTP JSON response
health success
health failure
FII lookup success
FII not found
health route dispatch
FII route dispatch
unknown route handling
```

Validated result:

```text
15 tests passed
Ruff passed
git diff --check passed
```

---

## 18. AWS Deployment Decision

Current decision:

```text
Lambda
=
DEFERRED

API Gateway
=
DEFERRED
```

The HTTP product boundary is already implemented and validated locally.

There is currently no external consumer requiring a deployed public or private HTTP endpoint.

Provisioning infrastructure now would not add product capability required by the current phase.

---

## 19. Cost Decision

Phase 5.6 introduces no new AWS infrastructure.

Not provisioned:

```text
Lambda
API Gateway
ALB
ECS
EC2
EKS
persistent web server
```

Always-on compute:

```text
NONE
```

New recurring API infrastructure cost:

```text
NONE
```

---

## 20. Future Deployment Path

When an external consumer requires HTTP access, the existing adapter can become:

```text
Consumer
   |
   v
API Gateway
   |
   v
Lambda
   |
   v
HTTP Adapter
   |
   v
Product Service
   |
   v
Serving Layer
```

The product contract remains unchanged.

---

## 21. Exit Criteria

```text
[x] product boundary defined
[x] product service implemented
[x] serving readiness validation implemented
[x] business-date reconciliation implemented
[x] ticker-population reconciliation implemented
[x] exact FII product operation implemented
[x] HTTP adapter implemented
[x] health route implemented
[x] ticker route implemented
[x] error handling implemented
[x] Lambda-compatible handler implemented
[x] real health request validated
[x] real ticker request validated
[x] automated tests implemented
[x] Ruff validation passed
[x] git diff validation passed
[x] Lambda deployment evaluated
[x] API Gateway deployment evaluated
[x] unnecessary AWS infrastructure avoided
```

---

## 22. Status

```text
Phase 5.6              COMPLETE
Product Service        VALIDATED
HTTP Adapter           VALIDATED
Product Version        v1
Business Date          2026-08-28
Ticker Count           267
Automated Tests        15 PASS
Lambda                 DEFERRED
API Gateway            DEFERRED
New AWS Infrastructure NONE
Always-on Compute      NONE
```

---

## 23. Next Phase

Phase 5.7 will automate the dependency chain:

```text
D-1 trusted data
      |
      v
Daily Consumption
      |
      v
ML Serving
      |
      v
AI Structured Context
      |
      v
Product Readiness
```

The goal is to guarantee that downstream product consumers only see a coherent READY serving state.