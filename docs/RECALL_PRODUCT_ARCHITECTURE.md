# ExactScope recall product architecture — prototype history

Status: **NON-NORMATIVE early rc4 prototype design retained for implementation history**

> Do not implement or benchmark directly from this document. It predates the provider-neutral target-group contract and hard-codes assumptions such as `xs_recall`, one fact-pack shape, lexical ranking, global hit/miss behavior, and an older R arm. The current normative grounding design is [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md), [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md), and [`BENCHMARK.md`](BENCHMARK.md). Where this file conflicts, the newer contract wins.

Release context recorded here: **early rc4 recall prototype before target-group/provider-neutral redesign**

## 1. Historical prototype objective

ExactScope recall is a tiny deterministic grounding layer for constrained local models.

The target failure is not limited to arithmetic. Small models often fail because they:

- do not contain a fact;
- contain a stale version of a fact;
- retrieve the wrong nearby fact;
- confidently fill a missing value;
- confuse similarly named entities;
- spend many reasoning tokens reconstructing information that should have been fetched directly.

The product objective is therefore:

> **Let a small model ask for a fact cheaply, return only installed evidence deterministically, and make unsupported answers measurably harder to produce.**

This is an external-memory / grounding product, not a claim that the model's internal weights become more knowledgeable.

## 2. Primary serving path

The normal consumer path should avoid an extra model/tool turn entirely:

```text
user question
    |
    v
ExactScope prefetch(question)
    |
    +--> exact key / alias / bounded token match
    +--> deterministic ranking
    +--> immutable fact/revision/source identity
    |
    +--> hit: compact evidence records
    |
    `--> no hit: typed MISSING_INFORMATION
             |
             v
small model receives question + compact grounding once
             |
             v
        one answer generation
```

Only when direct question prefetch is insufficient may the model emit one short constrained reformulation such as `{"q":"aster orbital period","k":2}`. That fallback must be benchmarked separately because it adds output tokens and potentially another inference turn.

The model is not asked to reconstruct factual memory from weights when an authoritative fact pack already contains the relevant evidence.

## 3. `xs_recall` contract

The first request shape should remain tiny:

```json
{"q":"red glass author","k":2}
```

A compact successful response conceptually contains:

```json
{
  "s": 0,
  "h": [
    {
      "id": "demo.author",
      "e": "The fictional handbook Red Glass was written by Mira Venn.",
      "src": "demo-pack@1",
      "rev": 1,
      "rank": 5
    }
  ]
}
```

A no-hit response is not an empty excuse to guess. It is a typed miss:

```json
{"s":8,"e":"MISSING_INFORMATION"}
```

The host/model policy for an authoritative pack is: **no evidence -> no factual assertion from that pack**.

## 4. Determinism and ranking

The first recall profile intentionally avoids embedding inference and remote vector databases inside the ExactScope runtime.

Ranking is bounded and deterministic:

1. exact fact ID;
2. exact normalized alias;
3. alias prefix at a token boundary;
4. all query tokens present in an alias;
5. all alias tokens present in a longer query;
6. stable source-pack order as a tie breaker.

This is deliberately conservative. False positive retrieval can create a stronger hallucination than a no-hit, so precision is preferred over broad fuzzy matching in the first profile.

Semantic query rewriting may be performed by the small model, but the rewrite itself is constrained to a short retrieval query and is scored separately in qualification.

## 5. Fact pack

A fact pack is data, not executable code. Each record carries at minimum:

- stable fact ID;
- compact evidence text;
- source/provenance identity;
- revision;
- normalized aliases / keyword phrases.

A production pack should also bind:

- pack ID and version;
- creation/source timestamp where meaningful;
- source document/content digest;
- record-set digest;
- locale/language metadata;
- update/rollback identity;
- optional validity interval where the fact is time-sensitive.

The same fact ID may advance to a later revision. Qualification must verify that the selected pack revision overrides stale model memory when the pack is declared authoritative.

## 6. What ExactScope recall does not do

The deterministic core does not:

- invent aliases at runtime;
- browse the network;
- synthesize a missing fact;
- merge contradictory facts silently;
- claim semantic equivalence from an embedding distance;
- repair the model's final prose;
- treat model confidence as evidence.

Future optional semantic indexes may be added only if their model/index identity and failure behavior are independently frozen and measurable. They are not required for the first recall product.

## 7. Memory versus information retrieval

The product should distinguish three use cases.

### 7.1 Device/private memory

Examples:

- product configuration;
- user-approved local notes;
- device/service identifiers;
- organization-specific facts;
- offline manuals.

These are ideal because the base model cannot be expected to know them.

### 7.2 Long-tail factual retrieval

Curated local packs can hold facts that are too rare or expensive to keep reliable in a small model's weights.

### 7.3 Fresh/stale-knowledge override

A newer immutable fact revision may intentionally conflict with the model's pretrained memory. The returned pack evidence is authoritative only within the declared product policy/scope.

## 8. Hallucination benchmark

A recall benchmark must not be only a trivia accuracy test. It needs at least five case classes:

1. **closed-book long-tail** — real factual questions likely to expose weak recall;
2. **synthetic/private facts** — fictional or generated facts unavailable during model training;
3. **stale-memory override** — pack revision intentionally differs from plausible pretrained knowledge;
4. **no-answer** — relevant-looking question with no supporting fact in the pack;
5. **distractor/confusable** — several similar records where only one is supported.

Optional sixth class:

6. **multilingual/paraphrase** — same fact addressed through alternate language or wording.

The corpus must be frozen before inference and may not be used to add benchmark-answer-specific aliases after results are seen.

## 9. Benchmark arms

Minimum comparison:

- **A — model only**: answer from weights;
- **R — model + ExactScope recall**: one constrained retrieval query, deterministic fact hit/miss, then evidence-grounded answer;
- **L — larger-model reference**: optional but strongly preferred when the product claim is hardware/model replacement avoidance.

Useful ablations:

- R0: exact/alias only;
- R1: bounded token retrieval;
- native-tool versus constrained envelope only when preregistered.

Do not add retries or hidden query repair after seeing an incorrect result.

## 10. Required metrics

Primary metrics:

- exact factual answer accuracy;
- supported-answer accuracy;
- unsupported factual assertion rate (**hallucination rate**);
- no-answer abstention accuracy;
- retrieval hit@1 / hit@k;
- evidence/fact-ID precision;
- stale-memory override accuracy;
- distractor selection accuracy.

Efficiency metrics:

- added input tokens;
- retrieval query output tokens;
- evidence tokens returned;
- total model latency delta;
- ExactScope retrieval latency;
- fact-pack bytes;
- runtime bytes / mutable memory;
- accuracy uplift per added token;
- hallucination reduction per added token;
- accuracy uplift per fact-pack KiB;
- hallucination reduction per millisecond.

Raw counts must always accompany ratios.

## 11. Scoring rule

The scorer must separate four failures:

1. **query-generation failure** — model did not request the relevant fact;
2. **retrieval failure** — deterministic index did not return the expected installed fact;
3. **grounding failure** — correct evidence was returned but final answer contradicted/ignored it;
4. **unsupported-answer failure** — no supporting evidence existed but the model asserted a factual answer anyway.

This separation is central to product development. It tells us whether to improve the small-model request surface, the fact index, or the answer policy.

## 12. Promotion criterion

The recall feature should become the flagship ExactScope claim only after the same frozen candidate demonstrates, across several small models:

- material factual-accuracy uplift;
- material unsupported-answer/hallucination reduction;
- high retrieval precision on distractor cases;
- correct abstention on no-answer cases;
- stable behavior on synthetic/private facts;
- bounded token/latency/storage cost;
- no hidden retry or benchmark-specific alias repair.

Academic-domain expansion is secondary until this product thesis is established.
