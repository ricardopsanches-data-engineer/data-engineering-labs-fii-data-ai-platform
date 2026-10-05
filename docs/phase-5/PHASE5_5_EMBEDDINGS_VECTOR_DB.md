# Phase 5.5 — Embeddings / Vector DB

## 1. Objective

Phase 5.5 evaluates whether embeddings and vector retrieval are justified for the current platform state.

The objective is not to provision vector infrastructure by default.

The decision must be based on an actual semantic retrieval requirement and on the existence of a useful textual corpus.

---

## 2. Current AI Retrieval State

Phase 5.4 established a governed structured retrieval boundary.

Current AI serving artifacts:

```text
data/serving/ai/fii_structured_context.json
data/serving/ai/fii_structured_context.jsonl
```

The structured context contains:

```text
identity
market state
ML state
provenance
```

Retrieval is exact and deterministic by ticker.

---

## 3. Structured Retrieval Remains the Correct Mechanism

Current AI facts are structured quantitative data.

Examples:

```text
ticker
CNPJ
CVM code
fund name
market status
close price
intraday variation
trade quantity
ML features
serving date
```

These fields do not require semantic similarity search.

The preferred retrieval mechanisms remain:

```text
structured serving datasets
exact lookup
Athena
future API tools
```

---

## 4. Semantic Corpus Inventory

The Phase 5.5 inventory inspected the project data area for document-like content.

Formats inspected:

```text
.pdf
.txt
.md
.html
```

Current result:

```text
Gold AI document corpus       = empty
PDF files under data/         = 0
TXT files under data/         = 0
Markdown files under data/    = 0
HTML files under data/        = 0
```

Therefore, no meaningful semantic document corpus currently exists.

---

## 5. Current AI Serving Assets

The existing AI serving layer contains only:

```text
fii_structured_context.json
fii_structured_context.jsonl
```

These artifacts are structured serving contracts.

They are not a document corpus and should not be vectorized merely to introduce vector infrastructure.

---

## 6. Vector Database Decision

Current decision:

```text
Vector Database
=
NOT JUSTIFIED YET
```

The platform does not currently contain content that benefits materially from semantic similarity retrieval.

Provisioning a vector database now would add operational complexity without solving a real retrieval problem.

---

## 7. Embeddings Decision

Current decision:

```text
Embeddings
=
NOT REQUIRED YET
```

Generating embeddings for structured market facts would duplicate capabilities already provided more accurately by structured retrieval.

Exact facts should remain exact.

---

## 8. Why Structured Facts Should Not Be Embedded by Default

Example question:

```text
"What is the latest close price for GGRC11?"
```

Correct retrieval:

```text
exact structured lookup
```

Unnecessary retrieval:

```text
vector similarity search
```

A vector search introduces semantic approximation where no approximation is needed.

---

## 9. Future Semantic Retrieval Candidates

Embeddings and vector retrieval may become appropriate after the platform ingests textual content such as:

```text
FII management reports
fund reports
regulatory communications
material facts
shareholder notices
market commentary
portfolio descriptions
long-form fund documents
```

These sources contain natural language and may benefit from semantic search.

---

## 10. Future RAG Use Case

A future RAG flow may look like:

```text
User Question
      |
      v
Retrieval Router
      |
      +----------------------+
      |                      |
      v                      v
Structured Retrieval   Semantic Retrieval
      |                      |
      v                      v
Exact market facts      Document chunks
      |                      |
      +----------+-----------+
                 |
                 v
              LLM Context
                 |
                 v
                LLM
```

Structured and semantic retrieval remain separate concerns.

---

## 11. Vector Infrastructure Trigger

Vector infrastructure should only be introduced when all of the following conditions are true:

```text
a useful textual corpus exists
semantic retrieval provides clear value
chunking rules are defined
metadata strategy is defined
embedding model is selected
retrieval quality can be evaluated
cost is acceptable
operational ownership is clear
```

Until then, vector infrastructure remains deferred.

---

## 12. Candidate Future Architecture

When justified, the semantic branch may evolve to:

```text
Documents
    |
    v
Text Extraction
    |
    v
Normalization
    |
    v
Chunking
    |
    v
Embeddings
    |
    v
Vector Store
    |
    v
Semantic Retrieval
    |
    v
LLM Context
```

This architecture is intentionally not implemented in Phase 5.5.

---

## 13. Candidate AWS Services

Future evaluation may consider:

```text
Amazon Bedrock embedding models
Amazon Bedrock Knowledge Bases
Amazon OpenSearch Serverless
S3 Vector capabilities
other managed vector stores
```

No service is selected or provisioned in this phase.

Selection must be driven by:

```text
cost
scale
latency
operational complexity
AWS integration
retrieval quality
```

---

## 14. Cost Decision

Phase 5.5 creates no new AWS infrastructure.

Not provisioned:

```text
OpenSearch Serverless
Vector Database
Bedrock Knowledge Base
embedding jobs
persistent inference endpoints
EC2
ECS
EKS
RDS
SageMaker endpoint
```

Always-on compute:

```text
NONE
```

Recurring vector infrastructure cost:

```text
NONE
```

---

## 15. KISS Decision

The platform follows the principle:

```text
Do not create infrastructure before a real requirement exists.
```

The current structured retrieval implementation already satisfies the available AI data requirements.

Therefore:

```text
structured facts
→ structured retrieval

semantic documents
→ future vector retrieval
```

---

## 16. Phase 5.5 Result

Phase 5.5 does not represent a missing implementation.

It represents an explicit architectural decision.

The result is:

```text
Embeddings          DEFERRED
Vector DB           DEFERRED
Semantic Retrieval  DEFERRED
RAG Documents       WAITING FOR CORPUS
New AWS Resources   NONE
```

---

## 17. Exit Criteria

```text
[x] semantic content inventory executed
[x] Gold AI corpus inspected
[x] document-like data inspected
[x] current AI serving artifacts inspected
[x] semantic corpus confirmed absent
[x] embeddings requirement evaluated
[x] vector database requirement evaluated
[x] structured retrieval retained as preferred mechanism
[x] future vector triggers documented
[x] future semantic architecture documented
[x] no unnecessary AWS resources provisioned
[x] recurring vector infrastructure cost avoided
```

---

## 18. Status

```text
Phase 5.5                  COMPLETE
Embeddings                 DEFERRED
Vector Database            DEFERRED
Semantic Corpus            NOT AVAILABLE YET
Structured Retrieval       ACTIVE
RAG                        FUTURE
New AWS Infrastructure     NONE
Always-on Compute          NONE
```

---

## 19. Next Phase

Phase 5.6 will establish the API / Product Layer.

Its responsibility is to expose governed serving capabilities to downstream consumers without coupling them directly to RAW or SILVER storage.

Expected direction:

```text
Product / API
      |
      v
Serving Contracts
      |
      +--> Daily Consumption
      |
      +--> ML Serving
      |
      +--> AI Structured Retrieval
```