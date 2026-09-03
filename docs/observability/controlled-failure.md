# Controlled Failure — FII Data & AI Platform

## 1. Objetivo

O Controlled Failure foi criado para provar que a observabilidade da plataforma não apenas apresenta resultados verdes em condições normais, mas também detecta uma falha conhecida quando ela é introduzida de forma controlada.

Implementação:

```text
src/observability/controlled_failure/runner.py
```

Versão validada:

```text
Controlled Failure version: v1
```

## 2. Princípio de segurança

O teste nunca altera o dataset oficial.

Dataset oficial utilizado:

```text
data/gold/ml/fii_features/fii_features.parquet
```

Fluxo:

```text
Features oficial
      |
      | leitura
      v
cópia temporária
      |
      | injeta exatamente uma linha duplicada
      v
dataset temporário corrompido
      |
      | Pipeline Health inspect_dataset()
      v
FAIL esperado
      |
      v
arquivo temporário removido
```

O arquivo oficial permanece somente leitura durante todo o teste.

## 3. Falha injetada

O cenário controlado é:

```text
features_duplicate_key
```

A cópia temporária recebe exatamente uma duplicidade da chave governada do dataset de Features.

Execução validada:

```text
Original rows: 68,747
Corrupted rows: 68,748
Injected rows: 1
Expected duplicate count: 1
```

## 4. Mecanismo testado

O runner usa o mecanismo real de inspeção do Pipeline Health.

Ele não simula manualmente um resultado de falha.

O comportamento esperado é:

```text
dataset status = FAIL
duplicates check = FAIL
duplicate_count = 1
```

Resultado observado:

```text
Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1
```

Portanto, a detecção funcionou como projetado.

## 5. Verificações de segurança

Após o teste, o runner confirma:

```text
Official dataset unchanged: True
Temporary artifact removed: True
```

A integridade do arquivo oficial é verificada por assinatura operacional baseada em:

- path;
- file size;
- modification time.

O teste só é considerado bem-sucedido quando:

1. a falha temporária é detectada;
2. a contagem de duplicidades é exatamente a esperada;
3. o dataset oficial permanece inalterado;
4. o artefato temporário é removido.

## 6. Resultado validado

Execução:

```powershell
python -m src.observability.controlled_failure.runner
```

Resultado:

```text
Controlled Failure Test
Controlled failure version: v1
Test: features_duplicate_key
Safety: official parquet READ ONLY, corruption only temp copy

Original rows: 68,747
Corrupted rows: 68,748
Injected rows: 1
Expected duplicate count: 1

Observed dataset status: FAIL
Observed duplicates check: FAIL
Observed duplicate count: 1

Official dataset unchanged: True
Temporary artifact removed: True

Test status: PASS
```

## 7. Interpretação

Há dois status diferentes e ambos são corretos:

```text
Dataset temporário corrompido -> FAIL
Controlled Failure Test       -> PASS
```

O primeiro demonstra que o monitor detectou o problema.

O segundo demonstra que o cenário de teste produziu exatamente o comportamento esperado sem danificar o dado oficial.

## 8. Evidência

Outputs operacionais:

```text
data/observability/controlled_failure/latest.json
data/observability/controlled_failure/history/<timestamp>.json
```

A evidência curada da execução validada da Fase 0 está documentada em:

```text
docs/observability/evidence/phase-0-observability-evidence.md
```

## 9. O que esse teste prova

O Controlled Failure v1 fornece evidência de que:

- o detector de duplicidades está ativo;
- uma quebra real de chave produz FAIL;
- a lógica testada é a mesma usada pelo Pipeline Health;
- o teste é isolado;
- o dado oficial não é corrompido;
- o artefato temporário é descartado.

## 10. O que esse teste não pretende provar

O teste não tenta cobrir todas as possíveis falhas da plataforma.

Ele não substitui:

- checks de schema;
- freshness;
- contracts;
- temporal leakage;
- holdout protection;
- reconciliação de ML;
- validações dos demais datasets.

Esses controles são cobertos pelo Pipeline Health v3.

O Controlled Failure é uma prova operacional complementar de que o framework consegue efetivamente entrar em estado de falha quando uma condição inválida é introduzida.
