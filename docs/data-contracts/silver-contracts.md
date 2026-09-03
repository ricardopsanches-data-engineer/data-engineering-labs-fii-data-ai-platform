# Silver Contracts — FII Data & AI Platform

## 1. Objetivo

Este documento registra os contratos da camada Silver da FII Data & AI Platform na Fase 0.

A camada Silver representa dados já parseados, tipados e normalizados, prontos para consumo por builders Gold.

Princípios:

```text
RAW preserva origem
SILVER normaliza
GOLD aplica semântica de negócio
```

---

## 2. Escopo

Na Fase 0, a Silver consolida principalmente:

- dados de pregão da B3;
- informações cadastrais e classificatórias da CVM;
- informações complementares de fontes auxiliares;
- identidade técnica necessária para os datasets Gold.

A camada Silver não contém decisões finais de corporate actions nem políticas de elegibilidade de ML.

---

## 3. B3 Silver Contract

### Finalidade

Representar dados diários de negociação de instrumentos após parsing e normalização.

### Campos principais

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

### Tipos esperados

```text
trade_date        datetime
ticker            string
instrument_id     string-like
instrument_id_type string-like
market            string-like
open_price        numeric
low_price         numeric
high_price        numeric
average_price     numeric
close_price       numeric
trades_quantity   integer-like
```

### Chave lógica

```text
trade_date + ticker
```

Quando a origem possuir granularidade adicional, identificadores técnicos podem ser usados para desambiguação durante o parsing, mas o downstream Gold de FIIs trabalha com identidade diária por ticker/data.

### Estado validado na Fase 0

```text
250 sessões
2025-08-29 -> 2026-08-28
68,747 rows
372 tickers
```

### Regras mínimas

```text
trade_date deve ser válido
ticker deve existir
prices devem ser numéricos quando presentes
trades_quantity deve ser inteiro-like
duplicidades de chave governada não devem ser introduzidas downstream
```

---

## 4. CVM Silver Contract

### Finalidade

Normalizar cadastro e classificação de fundos para suporte à identidade e enriquecimento.

### Regras

```text
encoding deve ser detectado/tratado
campos cadastrais devem permanecer rastreáveis à origem
classificação do fundo não deve ser inferida por ticker quando a fonte oficial estiver disponível
```

### Estado observado na Fase 0

Classes processadas:

```text
36,606
```

Distribuição observada:

```text
FIF          26,691
FIDC          5,299
FIP           2,461
FII           1,528
FIAGRO          356
FIIM             248
FIF (FAPI)        13
Funcine             8
FIP (FMIEE)         1
FICART              1
```

### Papel downstream

```text
CVM Silver
→ identity / classification
→ Gold datasets
```

---

## 5. Identity Contract

A identidade de um FII não deve depender apenas do ticker.

Motivo:

```text
ticker pode mudar
CNPJ tende a ser mais estável
```

Campos de identidade podem incluir:

```text
ticker
cnpj
codigo_cvm
instrument identifiers
```

Regra:

```text
ticker é identificador operacional
CNPJ/CVM fornecem identidade institucional
```

O lineage deve preservar essa distinção.

---

## 6. Temporal Contract

A Silver não deve introduzir datas futuras nem deslocar semanticamente a sessão da B3.

Para dados de pregão:

```text
trade_date = sessão real de mercado
```

As regras de horizonte futuro para ML não pertencem à Silver. Elas são aplicadas em camadas Gold/ML.

---

## 7. Mutation Policy

A Silver é derivada da RAW.

Reprocessamento deve obedecer:

```text
RAW
→ parser
→ normalized dataframe
→ Silver
```

Não é permitido:

```text
editar manualmente Silver para corrigir resultado downstream
```

Correções devem ocorrer no parser ou regra de transformação responsável.

---

## 8. Consumer Contract

Principais consumidores:

```text
Gold Daily Snapshot
Price Discontinuity detection
Corporate Action processing
Price History builders
downstream analytics
```

A Silver não deve conhecer lógica de modelo, split, Walk-Forward ou observability.

---

## 9. Quality Expectations

Antes de consumo Gold:

```text
arquivo legível
schema mínimo presente
datas parseáveis
tipos numéricos válidos
identidade coerente
sem corrupção estrutural
```

Checks específicos de qualidade de negócio são responsabilidade das camadas Gold Quality.

---

## 10. Status

```text
Silver ingestion/parsing     VALIDATED
B3 temporal coverage         VALIDATED
CVM classification parsing   VALIDATED
Identity principle           DOCUMENTED
Silver contract              DOCUMENTED
```
