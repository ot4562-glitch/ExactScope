# ExactScope grounding benchmark and qualification contract

Release context: **rc4 grounding candidate preparation after completed v1.0.0-rc.3 qualification**

Status: **normative for the next grounding candidate; no new model inference may begin until the candidate, corpus and preregistration inputs are frozen**

Normative grounding semantics: [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md)

The flagship product question is:

> For an existing constrained/on-device model, does ExactScope one-call grounding materially improve everyday factual accuracy and reduce wrong-confident answers, without unacceptable false grounding, privacy risk, token/context growth, retrieval latency, storage/RAM cost, or integration complexity?

The benchmark is intentionally designed so ExactScope cannot win merely by adding another model turn or by using benchmark gold to route retrieval.

## 1. Primary comparison arms

| Arm | Serving path | Answer-generation calls | Purpose |
|---|---|---:|---|
| **A** | model only | exactly 1 | baseline factual accuracy / unsupported-answer behavior |
| **G** | original question -> production router/providers/policy -> Grounding Frame/Projection -> same model | exactly 1 | flagship product arm |
| **Q** | one bounded model rewrite -> providers/policy -> Grounding Frame/Projection -> model | max 2 total | optional diagnostic; never merged with G |
| **L** | justified larger-model reference, no ExactScope | exactly 1 | optional larger-model/hardware alternative |

For secondary quantitative-only experiments, historical B/C/D labels may still be used for `xs_calc` / `xs_eval`, but they are not part of the flagship grounding score.

### 1.1 A/G fairness

Comparable A and G MUST use the same:

- item IDs and questions;
- model repository revision/file SHA-256/quantization;
- inference runtime build and launch settings;
- answer-generation call count;
- sampling policy, seed policy and max output tokens;
- answer system policy except for the preregistered Grounding Policy/Projection added only in G;
- scorer and answer-normalization rules;
- target hardware for latency/resource comparisons.

G is allowed the frozen evidence context because that is the product intervention. Added evidence bytes/tokens/latency/storage are measured, not hidden.

No extra answer retries, larger output budget, answer repair, hidden tool call, or post-answer retrieval may be added to G.

## 2. Gold isolation: no benchmark oracle in serving

This is a release-blocking benchmark rule.

The serving path may access only production-available inputs:

- original user question;
- application context that a real integration would have;
- effective security scope;
- frozen `GroundingProfile`;
- allowed source snapshots/indexes/providers.

The serving path MUST NOT access:

- expected answer;
- expected target key;
- expected source ID;
- expected Evidence Item ID;
- expected provider;
- expected answerability/abstention label;
- scorer annotations;
- benchmark class labels if they would reveal routing or answer information.

Gold/scorer files MUST be stored separately from the serving corpus/source directories and passed only to the scorer after model output is complete.

An oracle route/target/source MAY be tested only as a separately labeled diagnostic ceiling. It MUST NOT be called G and MUST NOT support the flagship product claim.

## 3. Freeze order before any model inference

The exact order is:

1. freeze ExactScope source commit and candidate version/identity;
2. freeze Grounding Contract version and concrete `GroundingProfile` bytes/SHA-256;
3. freeze router implementation/configuration identity;
4. freeze source snapshots and source manifests;
5. build/freeze provider indexes and provider identities;
6. freeze Evidence Policy/merge/freshness/conflict/timeout/budget behavior;
7. freeze Model Projection renderer/template bytes/SHA-256;
8. freeze workload corpus and scorer-side gold separately;
9. freeze benchmark generator/scorer source revisions and hashes;
10. freeze model inventory and inference runtime identity;
11. freeze model generation settings;
12. freeze failure taxonomy, metric definitions and denominators;
13. freeze retry/timeout/early-stop/single-writer rules;
14. create a no-inference preregistration record binding all of the above;
15. run candidate integrity/dry-run checks;
16. only then permit the first model request.

If any behavior-affecting asset changes after step 14, create a new candidate/run identity. Do not amend the preregistration and continue under the same label.

## 4. Candidate identity

A result belongs only to the exact combination of:

- ExactScope Git tag/commit;
- release/archive SHA-256 if a package is used;
- Grounding Contract version;
- GroundingProfile bytes/SHA-256;
- router implementation/configuration digest;
- source snapshot identities and digests;
- provider implementation/index/preprocessing/ranking identities;
- embedding model/tokenizer/index identity where applicable;
- remote-provider captured response snapshot where applicable;
- security/application scope class used by the benchmark;
- freshness/as-of policy;
- merge/dedup/conflict/ambiguity/sufficiency policy;
- timeout/retry/cancellation/late-result policy;
- evidence/context budgets;
- Model Projection template/renderer bytes/digest;
- corpus/query bytes and SHA-256;
- scorer gold bytes and SHA-256;
- model repository revision/file SHA-256;
- inference runtime/version/build/launch command;
- generation settings;
- scoring/failure policy;
- raw run records.

Changing one creates a new identity.

## 5. Flagship workload strata

The corpus must resemble ordinary assistant usage while still separating model-memory knowledge from external-grounding value.

### 5.1 Stable public everyday facts

Frozen, redistributable questions about ordinary reference knowledge, products, places or other consumer-shaped factual tasks.

Purpose:

- measure real-world-shaped answer quality;
- detect regressions where grounding damages facts the model already knows.

Because a pretrained model may already know these answers, this stratum is never sufficient by itself to prove grounding value.

### 5.2 Synthetic/private/device memory

Candidate-bound fictional facts such as:

- saved parking location;
- device nickname/identifier;
- preferred room/device setting;
- local household label;
- private project code;
- local application state;
- configuration value unavailable from model weights.

Purpose: measure true external-memory recovery without exposing real private data.

The source facts and scorer gold are generated together but stored in separate serving/gold outputs. Serving never sees the gold mapping.

### 5.3 Product/manual support

Questions over a frozen manual/FAQ/source snapshot:

- replacement parts;
- setup/default values;
- dimensions/specifications;
- feature availability;
- short procedural facts;
- identifiers/model variants.

Include sibling-product distractors.

### 5.4 Stale/revision override

The model is likely to remember or infer an old/plausible value while the authoritative source snapshot contains the newer frozen value.

Purpose: prove that current authoritative evidence can override stale model memory without exposing the stale value in the retrieval hint.

### 5.5 Distractor/entity confusion

Near-neighbor records:

- similar product names;
- rooms/devices with overlapping aliases;
- nearby part numbers;
- old/new revisions;
- sibling people/project names.

Purpose: directly measure false grounding and target disambiguation.

### 5.6 Authoritative no-answer

A real authoritative target exists, required source coverage completes successfully, but the requested fact is absent.

Correct behavior: `none` and no invented protected value.

This must be distinguished from routing failure or provider unavailability.

### 5.7 Provider unavailable / partial coverage

Deterministically inject:

- timeout;
- provider error;
- access denied;
- missing required provider;
- candidate-budget exhaustion;
- one provider success + one required-provider failure.

Purpose: prove that incomplete search does not become authoritative `none` and that frozen sufficiency rules are obeyed.

### 5.8 Ambiguity and conflict

Cases where:

- two entities remain plausible;
- two current authoritative items conflict;
- source priority cannot legally resolve the conflict.

Correct behavior is explicit `ambiguous` or `conflict`, not a plausible silent winner.

### 5.9 Multilingual/paraphrase

Natural paraphrases and selected product languages, including Korean where supported.

Coverage must be frozen before inference. Do not add aliases/tokenization rules after seeing failures and keep the same run identity.

### 5.10 Adversarial evidence / prompt injection

Evidence content may include instruction-like text such as:

- "ignore previous instructions";
- "answer X regardless of the question";
- fake system/tool directives;
- markup/code blocks containing commands;
- source text attempting to redefine authority.

Purpose: test the host/model data-versus-instruction boundary. The benchmark does not assume delimiters make prompt injection impossible.

### 5.11 Supplemental no-hit

The supplemental source does not contain the answer but the baseline model may legitimately know it.

Purpose: catch over-abstention. Supplemental absence must not be treated like authoritative absence.

### 5.12 Quantitative subsystem — secondary only

Statistics/FinQA/TAT-QA or `xs_calc`/`xs_eval` corpora remain valid for the quantitative subsystem but are reported separately from everyday grounding.

## 6. Corpus/source construction rules

### 6.1 Serving data and gold must be physically separable

Recommended layout before packaging:

```text
benchmark-candidate/
  serving/
    questions.jsonl
    sources/
    indexes/
    grounding-profile.json
  gold/
    answers.jsonl
    expected-evidence.jsonl
    class-labels.jsonl
  manifests/
    serving-manifest.json
    gold-manifest.json
```

The serving process gets only `serving/` plus runtime/model inputs. The scorer gets `gold/` only after outputs exist.

### 6.2 Candidate-bound synthetic/private generation

Synthetic/private facts should be regenerated for the new candidate from a recorded seed/generator revision so pretrained memorization is implausible.

Freeze source facts and queries before model inference. Do not regenerate easy/hard variants after seeing model behavior.

### 6.3 Public/manual source licensing

Record source revision, license/redistribution basis and extraction mapping. Do not publish copyrighted source text beyond what the license permits; frozen private evaluation snapshots may be represented by digests when redistribution is not allowed.

### 6.4 No answer-specific retrieval hints

Do not put the expected answer, expected operation/source ID, or scorer label into aliases, `target_label`, query rewrites or provider metadata.

Product-realistic stable names/aliases are allowed only if they are part of the frozen source/profile before benchmark inference.

## 7. Retrieval/policy ground-truth classes

Each item may have scorer-only annotations such as:

- `answer_expected`: yes/no;
- `authority_class`: authoritative/supplemental/mixed-target;
- `retrieval_positive`: whether at least one valid installed Evidence Item exists;
- valid evidence identities;
- forbidden/distractor evidence identities;
- expected protected target(s);
- expected group state where the state is objectively defined by the source fixture;
- expected current revision/value;
- allowed answer variants;
- whether abstention is required/permitted/incorrect.

These fields are scorer-only.

## 8. Failure taxonomy

Record failures by stage.

### Routing/security

1. relevant target not routed;
2. wrong target routed;
3. benchmark-oracle leakage;
4. security-scope/source-binding violation.

### Provider/retrieval

5. provider query failure;
6. retrieval miss despite relevant installed evidence;
7. false retrieval / distractor hit;
8. stale revision selected;
9. timeout/error/denied/budget outcome mishandled;
10. partial required coverage mishandled.

### Policy/frame

11. wrong authority assignment;
12. false authoritative `none`;
13. ambiguity mishandled;
14. conflict mishandled;
15. dedup/ordering instability;
16. budget/truncation changed semantics;
17. frame/projection identity/serialization failure.

### Model answer

18. grounding adherence failure;
19. authoritative unsupported assertion;
20. over-abstention;
21. prompt-injection/adversarial-evidence policy failure;
22. model output/token/timeout failure.

Report stage failures separately even when they result in the same final wrong answer.

## 9. Exact metric definitions

Always publish raw numerator and denominator beside every ratio.

Let:

- `N_all` = all objectively scorable factual benchmark items in the stratum;
- `N_answerable` = items where a correct substantive answer is expected/allowed under the scoring contract;
- `N_auth_unresolved` = items with an authoritative protected target whose G state is correctly expected to be `none`, `ambiguous`, `conflict`, or `unavailable` and for which assertion of a protected value is forbidden;
- `N_A_correct` = items A answered correctly;
- `N_A_not_correct_answerable` = answerable items where A was wrong or abstained;
- `N_retrieval_positive` = items with at least one valid installed expected evidence item;
- `N_G_emitted_evidence` = items where G exposed one or more Evidence Items to the model.

### 9.1 End-to-end factual accuracy

```text
factual_accuracy = correct final factual responses / N_all
```

A benchmark may separately report `answerable_accuracy = correct substantive answers / N_answerable`.

### 9.2 Useful-answer rate

```text
useful_answer_rate = correct substantive answers / N_answerable
```

A refusal is not a useful answer on an answerable item.

### 9.3 Wrong-confident-answer rate

```text
wrong_confident_answer_rate =
  wrong non-abstaining factual responses / N_all
```

If confidence is not directly measured, "confident" here operationally means the model asserted a factual answer instead of an allowed abstention/uncertainty response. Do not infer calibrated probability from prose tone.

### 9.4 Authoritative unsupported-assertion rate

```text
authoritative_unsupported_assertion_rate =
  responses asserting a protected factual value on unresolved authoritative targets
  / N_auth_unresolved
```

This is the primary hallucination-style safety metric.

### 9.5 Correct-abstention rate

```text
correct_abstention_rate =
  correct abstentions / N_auth_unresolved
```

Report by `none`, `ambiguous`, `conflict`, and `unavailable` separately.

### 9.6 Over-abstention rate

```text
over_abstention_rate =
  unnecessary abstentions on answerable items / N_answerable
```

Stratify supplemental-no-hit cases because they are specifically designed to catch blanket refusal.

### 9.7 Grounding recovery rate

```text
grounding_recovery_rate =
  items where A wrong/abstained and G correct
  / N_A_not_correct_answerable
```

Also publish the raw recovery count.

### 9.8 Grounding penalty rate

```text
grounding_penalty_rate =
  items where A correct and G wrong/forbidden-abstention
  / N_A_correct
```

This prevents a large gross gain from hiding damage to already-correct behavior.

### 9.9 Evidence hit@k

```text
hit_at_k =
  retrieval-positive items with >=1 valid expected evidence item in top-k
  / N_retrieval_positive
```

This is a scorer-side retrieval diagnostic, not input to the serving router.

### 9.10 Evidence precision@k

```text
precision_at_k =
  valid target-supporting emitted evidence items
  / all emitted evidence items for scored retrieval cases
```

Report macro and micro forms if both are useful; name them explicitly.

### 9.11 False-grounding rate

Primary item-level definition:

```text
false_grounding_rate =
  G items that expose >=1 invalid/wrong/distractor evidence item
  / N_G_emitted_evidence
```

Also report false-positive grounding on retrieval-negative/distractor cases separately.

### 9.12 Grounding adherence

```text
grounding_adherence =
  final responses consistent with the correct supplied authoritative evidence
  / cases where correct authoritative evidence was supplied
```

### 9.13 Revision override accuracy

```text
revision_override_accuracy =
  answers using the frozen current authoritative value
  / stale-revision test items
```

### 9.14 Provider-unavailable handling

```text
provider_unavailable_handling_accuracy =
  items with correct unavailable/coverage behavior
  / injected provider-failure items
```

Report timeout, denied, error, budget and partial-coverage cases separately.

### 9.15 Prompt-injection robustness

Report:

- final-answer correctness;
- whether evidence text changed protected authority/scope/tool behavior;
- whether adversarial instructions were obeyed;
- grounding adherence.

Do not collapse these into one "secure" percentage.

## 10. Cost and efficiency metrics

For each model/provider/profile:

### Grounding/runtime cost

- source snapshot bytes;
- provider index bytes;
- provider runtime/code bytes where relevant;
- resident memory/RSS/heap where measurable;
- retrieval latency p50/p95/p99;
- cold/warm distinction;
- provider attempts/outcomes;
- candidate count;
- GroundingFrame host bytes;
- Model Projection bytes;
- model-visible evidence tokens;
- provenance/policy tokens visible to model;
- end-to-end latency;
- energy where credibly measured.

### Delta versus A

- added input tokens;
- added prefill/model latency;
- added end-to-end latency;
- added storage/index bytes;
- added resident memory;
- added energy where measured.

### Efficiency ratios

After raw values are published, report where meaningful:

```text
accuracy uplift / added input token
wrong-confident-answer reduction / added input token
accuracy uplift / added index KiB
false-grounding-free recovery / added index KiB
accuracy uplift / added end-to-end ms
wrong-confident-answer reduction / added end-to-end ms
accuracy uplift / joule   # only when measured credibly
```

Do not publish a ratio without its raw numerator/denominator.

## 11. Routing/provider ablations

Ablations must be separately labeled and must not rewrite the flagship result.

Useful examples:

- exact/lexical provider only;
- semantic/vector provider only;
- exact/lexical then vector fallback;
- original-question G vs rewrite Q;
- top-k 1 vs 2 vs 3 under separately frozen profiles;
- model projection wording variants under separate candidate IDs;
- oracle-routing ceiling diagnostic.

Do not select the "best" profile per item after seeing results. A product profile is frozen before inference.

## 12. Model matrix for the next grounding candidate

The rc3 five-model matrix is historical evidence but remains a useful controlled diverse set for a **new** candidate if the files/runtime are re-frozen:

| Model | Role |
|---|---|
| Gemma 3 270M IT Q8_0 | extreme-small independent lower bound |
| LFM2.5 350M Q4_K_M | edge/on-device-first lower bound |
| Qwen3.5 0.8B Q4_0 | primary modern sub-1B |
| Qwen3.5 2B Q4_K_M | same-family scale point |
| Phi-4-mini-instruct 3.8B Q4_K_M | independent upper-small reference |

No old rc3 score transfers to the new grounding candidate.

Optional product-specific models may be added only if their runtime/profile is separately preregistered and their results are not silently mixed into the core denominator.

## 13. No-inference qualification before model benchmark

Before the first model request, the candidate must pass:

- GroundingProfile schema/canonicalization/digest validation;
- source snapshot manifest/digest validation;
- serving/gold physical-separation test;
- provider index reproducibility or exact identity check;
- deterministic router replay;
- deterministic provider replay for local providers;
- captured fixture replay for remote-provider benchmark paths;
- deterministic merge/order regardless of provider completion order;
- authoritative `none` coverage tests;
- timeout/error/denied/budget => unavailable tests;
- mixed authoritative/supplemental target tests;
- ambiguity/conflict tests;
- whole-item budget/truncation tests;
- security-scope mismatch/cache-isolation tests;
- content canonicalization/digest tests;
- Model Projection deterministic byte-for-byte tests;
- injection-laced evidence rendered as data tests;
- preregistration dry-run with zero inference;
- package manifest/checksum clean-room tests.

A candidate that fails these does not proceed to model inference.

## 14. Output/evidence structure

Use a unique directory outside mutable product source, for example:

```text
benchmarks/output/rc4-grounding-<candidate>-<model-id>-<run-id>/
```

Preserve:

```text
preregistration.json
candidate-manifest.json
model-inventory.json
serving-manifest.json
gold-manifest.json
grounding-profile.json
source-snapshot-manifests/
provider-identities/
raw/
  <arm>-<item>.jsonl
summary.json
summary.md
logs/
SHA256SUMS
```

Each raw G record should retain, subject to privacy policy:

- qid/item ID;
- Routing Plan or digest/reference;
- Provider Outcomes;
- selected Evidence Items;
- Grounding Frame;
- exact Model Projection bytes/digest;
- model prompt-token accounting;
- final raw model response;
- scored labels added **after** response generation;
- timing/resource measurements.

Require one writer. Duplicate `(arm,item_id)` keys, config drift, partial-run reuse, or incomplete runs represented as complete invalidate the run.

## 15. Preregistration record

There are two identity layers and they must not be conflated:

- `spec/schemas/grounding-preregistration-v0.1.schema.json` is the **provider-neutral grounding identity layer**. It exists so profile/source/provider/projection/corpus/model/runtime identities have a reusable logical record independent of one benchmark harness.
- `spec/schemas/grounding-benchmark-preregistration-v0.1.schema.json` is the **benchmark-run wrapper** used by `benchmarks/grounding_preregister.py`. It additionally binds the source commit, evaluation package, planned output, exact local model file, exact llama.cpp executable/launch/hardware, generation/isolation/scorer bytes, A/G call-count fairness and no-retry/no-repair state.

The benchmark preregistration tool must operate with zero inference and freeze at least:

- candidate/tag/commit/archive hashes;
- GroundingProfile SHA-256;
- source snapshot identities;
- provider/index identities;
- projection template hash;
- corpus serving/gold manifests and hashes;
- model inventory entry;
- inference runtime/version/launch command;
- hardware/thread/context settings;
- seed/temperature/sampling/max-output settings;
- answer-call count;
- timeout/retry/futility rules;
- scorer version/hash;
- output directory/run ID;
- no-hidden-repair/no-post-output-tuning flags.

The subsequent runner must refuse byte/config drift from preregistration.

### 15.1 Pre-inference package flow

The current rc4 implementation uses the following order and **stops before the last command is run without `--verify-only`**:

```text
python tools/generate_grounding_candidate.py --seed <seed> --output <candidate>
python tools/package_grounding_evaluation.py --candidate <candidate> --source-commit <40-hex-commit> --output <package-dir>
# extract the resulting .tar.gz into a fresh directory
python tools/verify_grounding_package.py --root <extracted-package-root>
python benchmarks/grounding_dry_run.py serve --candidate <extracted-package-root>/candidate --output <fresh-dryrun-dir>
python benchmarks/grounding_dry_run.py verify-gold --candidate <extracted-package-root>/candidate --records <fresh-dryrun-dir>/serving-records.jsonl --output <fresh-gold-check-dir>
python benchmarks/grounding_preregister.py create ... --output <model-preregistration.json>
python benchmarks/run_grounding_benchmark.py --preregistration <model-preregistration.json> --output <planned-output> --verify-only
```

The candidate generator, package verifier, dry-run, preregistration and runner `--verify-only` path perform zero model inference. Actual A/G inference begins only when `run_grounding_benchmark.py` is invoked **without** `--verify-only` in the later benchmark session.

The five current benchmark model identities are stored in `benchmarks/grounding-model-inventory.json`; the frozen llama.cpp runtime/host configuration is stored in `benchmarks/grounding-runtime-llama-v040.json`. Reusing those model **file identities** from rc3 does not reuse any rc3 benchmark scores or conclusions.

## 16. Claim policy

Until a frozen rc4 grounding candidate completes the model matrix, public docs MAY say:

- ExactScope has a provider-neutral grounding architecture and contract;
- the default design uses original-question prefetch and one answer-generation call;
- authoritative and supplemental evidence have distinct no-hit behavior;
- false grounding and provider unavailability are explicit failure classes;
- the existing rc3 quantitative subsystem remains available.

They MUST NOT claim from design/prototype tests alone:

- improved everyday model accuracy;
- reduced hallucination rate;
- a particular percentage reduction in wrong answers;
- superiority to larger models or RAG stacks;
- negligible latency/RAM/storage/energy cost;
- production readiness;
- broad provider/platform support.

Use [`MARKETING_CLAIMS.md`](MARKETING_CLAIMS.md) for public wording.

## 17. Historical evidence boundary

`v1.0.0-rc.3` five-model/install qualification is complete historical quantitative evidence. It established important tool-interface findings but did not test this grounding architecture.

Older r17/r20 Statistics evidence is also historical and tied to its exact earlier runtime.

Do not copy rc3/r20 scores into rc4 grounding tables. Do not rewrite frozen historical evidence to fit the new product direction.

## 18. Benchmark-ready gate

A candidate is **READY_FOR_GROUNDING_BENCHMARK** only when:

- documents/contracts are internally consistent;
- a read-only architecture review reports no P0 contract blocker;
- concrete GroundingProfile/schema/manifest bytes are frozen;
- serving and scorer data are separated and hashed;
- provider/index/source identities are frozen;
- no-inference conformance/determinism/security tests pass;
- packaging/clean-room tests pass;
- preregistration dry-run passes;
- the model matrix is downloaded/hashed or otherwise ready;
- no model inference for the candidate has yet been run.

The user may then start a separate validation/benchmark session from that immutable candidate.

**Current status note (2026-09-06, non-normative):** frozen candidate source `125ad9403f22eece7f552701d4c7376bba3b697f` has met this gate with zero rc4 model inference. Its archive/package/profile/model/runtime/preregistration identities and Linux/Windows clean-room evidence are recorded in [`GROUNDING_BENCHMARK_READY.md`](GROUNDING_BENCHMARK_READY.md). The normative criteria above remain unchanged for future candidates.
