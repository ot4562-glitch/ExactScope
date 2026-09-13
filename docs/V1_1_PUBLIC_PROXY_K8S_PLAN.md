# ExactScope v1.1 — Kubernetes Operations public proxy workload

Status: **active public-development workload; not enterprise qualification**

Updated: **2026-09-13**

## 1. Purpose

This workload exists to answer a product question that the public NQ/Hotpot panel cannot answer cleanly:

> On a bounded, versioned, operational-document corpus with real host retrieval, does the frozen v1.1 semantic path add useful value over both model-only behavior and a competent ordinary RAG path?

This is a **public enterprise-like proxy**, not customer evidence. It must never be described as enterprise qualification, production readiness, customer savings, or proof of a universal control-plane category.

## 2. Frozen source

Primary source repository:

- repository: `kubernetes/website`
- authority: official Kubernetes documentation repository
- source revision: `ce98a43f24257385a9766003a6dadc95e962dc63`
- source date: 2026-09-13
- license: CC-BY-4.0
- language: English

The first bounded domain is **Pod operations and container configuration**, centered on Pod lifecycle, health probes, resource/QoS behavior, init/ephemeral containers, downward API and common Pod-configuration tasks.

The source commit is immutable for this workload. Upstream changes after the freeze do not change the workload; they create a later revision.

## 3. Workload shape

Target public proxy v0.1 contains **64 manually adjudicated questions**. Each item must bind:

- `item_id`;
- `group_id` used for leakage control;
- question;
- semantic class;
- answer contract;
- gold answer or gold disposition;
- supporting source path(s) and source-revision identity;
- answer-bearing quote/span locator for scorer-side audit only;
- unacceptable-error marker where applicable.

Target class allocation:

- 32 answerable short factual / typed-decision items;
- 12 authorized-corpus unanswerable items;
- 8 materially ambiguous / scope-insufficient items;
- 12 retrieval-stress answerable items with plausible lexical distractors.

`retrieval-stress` is a difficulty flag, not a separate truth state; those items are also answerable. The 64-item truth-state allocation remains 44 answerable / 12 unanswerable / 8 ambiguous.

Questions are grouped by factual target / source section / near-paraphrase family. A group may appear in only one split.

## 4. Splits

The initial 64 items are split before any model scoring:

- development32 — implementation debugging and one bounded policy selection pass are allowed;
- untouched-validation32 — no policy reselection, threshold changes or item replacement after serving begins.

Gold remains scorer-side. Runner-visible files contain questions and item/group identities only.

A later owner-bound qualification workload must use new data and a different qualification contract; this proxy can never be promoted into customer qualification by renaming it.

## 5. Three fixed arms

All arms use the same local model/runtime identity, generation settings and frozen question membership.

### B — model only

No retrieved document evidence is attached. This keeps continuity with the public A/G evidence and measures how much of the operational workload the base model already knows.

### R — ordinary host RAG

- host: LlamaIndex
- retriever: BM25Retriever
- retrieval top-k: 12
- raw ranked context truncated to the frozen evidence byte budget
- no ExactScope evidence shaping or semantic policy
- same answer contract and one model answer call

This is the **competent ordinary deployable alternative** for the proxy.

### G — ExactScope v1.1 integrated path

- the host still owns LlamaIndex BM25 retrieval;
- ExactScope receives only the host-ranked hits;
- initial candidate: `precision-context-v5`, 3072-byte evidence budget, cap8, top-k12;
- query/instruction separation and the frozen answer contract are retained;
- no second model, no quality retry, no reflection, no model-as-judge, no larger index, no outcome-aware routing.

The public NQ 3 KiB/cap8 result is only a prior. Development32 may reject this candidate. If a different policy is selected on development32, that policy must be frozen before untouched-validation32 and the selection history must remain public.

## 6. Metrics

Primary development metrics:

- exact task correctness / token-normalized F1 for factual text answers;
- correct unanswerable / ambiguous disposition;
- unsupported answer rate;
- unacceptable-error count;
- strict answer-contract failure rate;
- evidence-support correctness for R/G;
- input tokens;
- attached evidence bytes;
- model call count;
- sequential local model service time (descriptive only unless load order is counterbalanced).

Every item is scored under the same adjudication contract. Missing/invalid outputs remain failures unless the preregistered answer contract defines a valid abstention.

## 7. Development competence and publication gate

This is a **GitHub publication gate**, not a qualification threshold.

Before the first v1.1 public push that presents this proxy as product evidence, untouched-validation32 must satisfy all of the following:

1. B, R and G complete with zero hidden quality retries and no gold exposure to the runner.
2. G has zero strict-format failures and no more unacceptable errors than R.
3. G factual/decision utility is **not worse than R by more than 2.0 percentage points** on the frozen primary utility metric.
4. In addition, G must earn at least one material advantage over R:
   - **quality path:** G exceeds R by at least +3.0 pp on the primary utility metric; or
   - **efficiency path:** G is within the -2.0 pp quality margin and reduces mean input tokens or attached evidence bytes by at least 15%; or
   - **safety path:** G materially reduces unsupported/unacceptable errors under a predeclared count/rate rule without violating the quality margin.
5. Every regression, N/A and negative ordinary-RAG comparison is retained in the public result.

These thresholds are a project publication decision, not a statistical superiority claim. Paired uncertainty is still reported.

If G fails this gate, do **not** market the proxy as v1.1 product-value evidence. Diagnose only on development data, or narrow/pivot the product claim. Untouched-validation32 is not recycled as a new development set.

## 8. Kill / pivot criteria

Stop expanding v1.1 as a product if either condition holds after one additional fresh public proxy or the first real owner-bound workload:

- G repeatedly fails to match a competent ordinary RAG alternative on quality while offering no material safety/resource advantage; or
- any quality benefit disappears once integration, qualification, refresh and operational costs are counted.

Allowed outcomes include:

- keep stable v1.0 as the main product;
- retain the qualification/guard core as a narrower open-source library;
- recommend ordinary RAG or a stronger model instead;
- stop the v1.1 product branch.

Success criteria may not be relaxed after seeing the relevant validation outcome.

## 9. GitHub upload decision

### Public push #1 — proxy evidence checkpoint

**Push only after the proxy has completed untouched validation and the result package is reproducible.** Required payload:

- this plan;
- pinned source manifest and acquisition tool;
- 64-item question/adjudication package with scorer-side gold separated from runner input;
- B/R/G protocol and exact model/runtime identities;
- frozen development-selection record, if any;
- untouched-validation observations and score summary;
- paired uncertainty report;
- ordinary-RAG comparison;
- machine-verifiable result snapshot;
- README update that states the result whether positive or negative.

If the publication gate passes, push the current v1.1 review-surface work and proxy result together as the first credible v1.1 GitHub checkpoint. If the gate fails, do not publish a promotional v1.1 checkpoint; first narrow or pivot the claim locally and then publish the honest outcome/architecture decision.

### Public push #2 — real qualification freeze

The next major GitHub checkpoint occurs only when a **real external owner-bound workload** exists and its preregistration/Study Contract/readiness inputs have been frozen before confirmatory execution. That push may expose the protocol and non-sensitive identities, but not fabricate or leak private customer data.

### Release/tag

**Superseded release-gate note (2026-09-13):** this proxy failed its frozen development quality margin and selected no candidate. The project owner subsequently fixed the v1.1.0 scope as a **software/architecture release**: owner-bound enterprise qualification remains mandatory for enterprise/customer-value claims but is no longer a prerequisite for the software tag. The release must preserve this negative result, keep the stable support boundary limited to the Linux x86-64 native grounding C ABI/XSGI path, and label new qualification/control-plane and host-integration surfaces experimental/reference.

## 10. Immediate implementation order

1. Track the pinned Kubernetes source manifest and acquisition script.
2. Materialize the immutable source snapshot under `target/` only.
3. Build and audit the first question pool with source-span provenance.
4. Freeze group-disjoint development32 / untouched-validation32 membership.
5. Run host-owned LlamaIndex BM25 retrieval gold-blind.
6. Run B/R/G on development32 and make at most one bounded policy decision.
7. Freeze G.
8. Run untouched-validation32 once.
9. Score, report paired uncertainty and apply the publication gate.
10. Only then decide Public push #1.
