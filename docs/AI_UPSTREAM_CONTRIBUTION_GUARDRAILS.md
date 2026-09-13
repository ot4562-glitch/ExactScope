# AI-assisted upstream contribution guardrails

Status: **binding development and publication guardrail for ExactScope v1.1 integration/upstream work**

Purpose: ExactScope is developed with substantial AI assistance. The product direction, acceptance criteria, and final go/no-go decisions may be human-owned while implementation is largely AI-produced. That is acceptable only if correctness is established by reproducible evidence rather than by confidence in the coding agent.

This document applies to the current bridge/interop work around:

- `microsoft/onnxruntime-genai` — issue `#2549`
- `pytorch/executorch` — issue `#22761`
- `google-ai-edge/litert-samples` / LiteRT-LM — issue `#308`

It supplements, rather than replaces:

- `docs/UPSTREAM_VALIDATION_PLAN.md`
- `docs/AI_INTEGRATION.md`
- `docs/V1_1_INTEGRATION_FEEDBACK.md`
- the ExactScope grounding/runtime specifications

The upstream objective is **not** to push ExactScope into big-tech repositories as a dependency. ExactScope should first behave like a serious external consumer of those runtimes, discover real integration problems, produce minimal reproductions, and contribute fixes/examples only when they are useful to the upstream project on their own merits. Promotion is a possible consequence of good contribution quality, never the justification for a change.

---

## 1. Core rule: AI output is not evidence

A statement from an implementation agent such as:

- "this should work";
- "the API is compatible";
- "the test coverage is sufficient";
- "the runtime behavior is equivalent";
- "this is safe";
- "the upstream project supports this";

is **not evidence**.

A claim becomes admissible only when it is backed by one or more of the following:

1. a passing executable test whose purpose is independent of the implementation;
2. an observed run against the exact upstream release/commit being claimed;
3. a direct comparison with an official upstream example/reference behavior;
4. a clean-room build/run from declared inputs;
5. static/sanitizer/fuzz/property evidence where applicable;
6. an upstream source/document citation to the exact public interface used;
7. maintainer feedback in the public upstream issue/PR.

If evidence is missing, write **`NOT VERIFIED`**. Do not convert uncertainty into likely-sounding prose.

---

## 2. Non-negotiable architecture invariants

All bridge, interop, example, and upstream contribution code must preserve these invariants.

1. **The upstream runtime owns model execution.**
   - ORT GenAI owns tokenizer/generation/search/KV/execution-provider behavior.
   - ExecuTorch owns runner/model execution.
   - LiteRT-LM owns Engine/Conversation/model execution.

2. **ExactScope owns grounding qualification and its semantic policy.**
   - Do not copy retrieval, authority, coverage, freshness, ambiguity/conflict resolution, ranking, evidence projection, or host-completion logic into upstream adapters.

3. **Adapters normalize transport, not meaning.**
   - No semantic repair, guessed conversions, inferred missing operands, hidden re-ranking, or model-specific reasoning in an adapter.

4. **No hidden second inference.**
   - A path documented as one model call must make one model call.
   - A deterministic completion path must make zero model calls.

5. **No retry/repair agent loop.**
   - Failure is not silently converted into a second attempt with a different prompt/model/path.

6. **No fail-open grounding fallback.**
   - Never implement behavior equivalent to:
     `grounding failed -> ask the model from memory anyway`
     when the target is authoritative/protected.

7. **Typed failures remain typed failures.**
   - Examples include `Reject`, `Unavailable`, contract violation, upstream runtime error, malformed output, identity mismatch, or context-budget failure.
   - Do not collapse these into a plausible natural-language answer.

8. **The integration must remain removable.**
   - Removing a runtime adapter must not require changing ExactScope core semantics.
   - Runtime-specific requirements stay adapter-owned unless at least two independent runtimes demonstrate the same missing public seam and a core change is separately justified.

9. **No upstream dependency request by default.**
   - Do not ask Microsoft, PyTorch/Meta, or Google to add ExactScope as a required dependency unless maintainers explicitly request that direction.

10. **No claim inflation.**
    - Runtime attachment success is not evidence of answer-quality transfer.
    - A smoke test is not a benchmark.
    - A benchmark on one runtime/model is not cross-runtime qualification.
    - Design targets such as ARM64/mobile/wearable are not stable support claims until physically qualified.

Any implementation violating an invariant above is rejected regardless of how many tests pass.

---

## 3. Development roles: Builder, Breaker, Upstream Auditor, Release Judge

For meaningful integration/upstream work, separate the following roles conceptually and, when practical, use separate agents/contexts.

### A. Builder

Responsibilities:

- implement the smallest adapter/example/fix;
- use public upstream APIs only unless the task explicitly investigates an internal API;
- write basic positive and negative tests;
- keep upstream-owned behavior upstream-owned;
- record exact upstream version/commit used;
- avoid broad refactors unrelated to the integration question.

The Builder must not be the sole authority that its own work is correct.

### B. Breaker

The Breaker assumes the Builder is wrong until proven otherwise.

It should create **new tests and counterexamples**, not merely re-run the Builder's suite.

At minimum attack:

- empty/missing evidence;
- ambiguous/conflicting evidence;
- unavailable/timeout/error states;
- malformed model output;
- unexpected role/message combinations;
- boundary-size inputs;
- context/token-budget overflow;
- Unicode/escaping/delimiter cases;
- upstream API errors/exceptions;
- stale or mismatched runtime/profile identity;
- duplicate or reordered fields/messages where order matters;
- cancellation/partial execution where applicable;
- accidental extra model calls;
- accidental fallback to ungrounded model memory.

The Breaker should report counterexamples even if they are inconvenient for the current design.

### C. Upstream Auditor

The Auditor verifies the integration against the upstream project itself.

Required checks:

- inspect current upstream source for every API relied upon;
- determine whether each API is public, stable, experimental, deprecated, internal, or test-only;
- compare our usage with official upstream examples/tests;
- verify the exact stable release targeted;
- when practical, verify current upstream `main` separately;
- identify licensing, CLA, file-header, formatting, build, test, and contribution requirements;
- ensure the proposed contribution solves an upstream-relevant problem without requiring ExactScope.

Do not infer API stability from a header name or package import alone.

### D. Release Judge

The Judge does not repair the implementation while judging it.

The Judge reads the evidence from Builder, Breaker, and Auditor and returns one of:

- `PASS`
- `FAIL`
- `NOT VERIFIED`

If the Judge starts editing code, the judgment is invalidated and must be repeated after changes.

If only one AI agent is available, execute these phases sequentially with explicit context separation and do **not** call the result "independent review". Record that independence was limited.

---

## 4. Tests must not merely encode the implementation's mistake

The highest-risk AI failure mode is a shared misconception appearing in both code and tests.

Therefore, integration validation must use multiple test origins.

### 4.1 Specification tests

Derived from ExactScope contracts/specifications and architecture invariants, not from implementation details.

Examples:

- authoritative unresolved states never become model-memory answers;
- `complete` produces zero model calls;
- `generate` performs only the documented number of model calls;
- malformed generation fails closed;
- adapters do not mutate evidence semantics.

### 4.2 Upstream-conformance tests

Derived from actual upstream interfaces/examples.

Examples:

- official ORT GenAI generation path vs ExactScope-attached generation path;
- real ExecuTorch `IRunner` declaration and, before compatibility claims, a real `.pte` + tokenizer runner;
- real LiteRT-LM `Engine` / `Conversation` behavior and declared model/context limits.

### 4.3 Adversarial tests

Created after implementation by the Breaker from likely failure modes and deliberately chosen counterexamples.

They should include cases the Builder did not anticipate.

### 4.4 Differential tests

Where ExactScope should be transparent to upstream behavior, compare:

```text
same runtime + same model + same model-visible input
    -> official/reference path output/behavior A

same runtime + same model + same model-visible input
    -> ExactScope adapter path output/behavior B
```

Differences must be explained. Unexplained differences are a failure, not an opportunity to update expected outputs.

### 4.5 Property/invariant tests

When feasible, encode structural properties such as:

- model call count is exactly 0 or 1 according to disposition;
- adapter never emits an answer when finalization rejects;
- message/evidence budgets are bounded;
- failures are monotonic (adding an upstream error cannot improve disposition to a success);
- runtime-specific adapter code cannot change authority state;
- serialization/deserialization preserves declared semantics.

---

## 5. Minimum evidence packet for any compatibility claim

Before writing `supports`, `compatible`, `works with`, or equivalent wording, produce a compact evidence packet containing at least:

```text
ExactScope commit:              <sha>
ExactScope branch:              <name>
Upstream repository:            <owner/repo>
Upstream release/version:       <version, if applicable>
Upstream commit:                <sha>
OS / architecture:              <exact environment>
Compiler/interpreter:           <version>
Adapter/public API used:        <exact interface>

Build/compile:                  PASS | FAIL
Official/reference smoke:       PASS | FAIL | N/A
ExactScope attached smoke:      PASS | FAIL
Negative/fail-closed cases:     PASS | FAIL
Model-call-count assertion:     PASS | FAIL
Identity/config mismatch test:  PASS | FAIL
Context/budget boundary test:   PASS | FAIL | N/A
Clean-room reproduction:        PASS | FAIL | NOT RUN

Upstream source modified:       yes/no + files
ExactScope core logic copied:   yes/no
New dependency added:           yes/no + reason
Known limitations:              <explicit list>
Unverified claims:              <explicit list>
```

Store evidence under `target/` or another non-authoritative generated-results location unless an artifact is intentionally part of the public repository.

Do not publish machine-specific build artifacts or secrets.

---

## 6. Clean-room gate

A local developer environment can hide missing dependencies, stale generated files, environment variables, cached models, or accidental source-tree coupling.

Before a strong compatibility claim or upstream PR:

1. start from a clean checkout/worktree or equivalent isolated build directory;
2. use only documented inputs/dependencies;
3. record exact dependency/runtime versions;
4. rebuild the integration from scratch;
5. run the declared smoke and negative tests;
6. verify no untracked local file is required;
7. verify no developer-specific absolute path is embedded;
8. verify source modifications match the intended diff only;
9. record the result.

If clean-room reproduction is impractical (for example proprietary hardware/model access), say so explicitly and narrow the claim.

---

## 7. Upstream contribution gate

Do **not** open a PR merely because code exists.

An upstream PR is allowed only when all applicable conditions are satisfied:

- the proposed change is useful to the upstream project even if the reviewer ignores ExactScope;
- the issue/discussion has supplied placement guidance, **or** the repository's contribution conventions clearly make the placement unambiguous;
- the change uses the smallest appropriate public seam;
- there is a minimal reproduction or a self-contained example;
- tests demonstrate the behavior independently of prose claims;
- Builder/Breaker/Auditor evidence has been reviewed;
- the diff contains no copied ExactScope core policy;
- the diff contains no marketing copy disguised as documentation;
- license/CLA/header/style requirements are satisfied;
- no benchmark or compatibility claim exceeds the collected evidence.

Preferred PR structure:

```text
Problem
Minimal reproduction / motivation
Why the proposed boundary belongs here
Smallest change
Tests
Exact upstream version/commit tested
Known limitations
```

Avoid unsupported language such as:

- "should work";
- "probably compatible";
- "AI analysis suggests";
- "universal";
- "production-ready" when only smoke-tested.

Use `NOT VERIFIED` where appropriate.

---

## 8. Contribution must not become disguised marketing

The current strategy is to make ExactScope a useful external consumer of upstream runtimes.

Good behavior:

- report a real bug encountered while integrating;
- provide a minimal reproduction independent of ExactScope where possible;
- fix a real documentation/API/test gap;
- add an example only if it teaches an upstream-relevant integration pattern;
- answer maintainer questions with measured evidence;
- disclose ExactScope affiliation when relevant.

Bad behavior:

- unrelated typo PRs for visibility;
- opening issues whose only purpose is to link ExactScope;
- mass-posting the same proposal to many repositories;
- asking for stars, promotion, mentions, or endorsement;
- adding ExactScope branding where generic wording is more appropriate;
- pushing a dependency before maintainers ask for one.

A merge is valuable precisely because the contribution stands on its own.

---

## 9. Upstream compatibility lab policy

ExactScope may maintain an interoperability/compatibility lab against stable releases and selected upstream `main` commits.

The lab is a **consumer test surface**, not a certification authority.

Recommended outputs:

```text
upstream runtime
  stable: PASS / FAIL / NOT TESTED
  main:   PASS / FAIL / NOT TESTED
  public surface tested: <API>
  exact commit/version: <identity>
  last verified: <date>
  limitations: <text>
```

Rules:

- never auto-open upstream issues from CI;
- first reproduce a failure and determine whether it is ours, environmental, or upstream;
- minimize the reproduction so it does not require ExactScope if possible;
- report regressions only after comparison to a known-good upstream commit/release;
- do not label `main` failures as regressions without bisect/comparison evidence;
- keep compatibility results distinct from answer-quality benchmark results.

This lab can indirectly create visibility because maintainers may encounter ExactScope through useful bug reports and reproducible external-consumer feedback. Visibility is not the test oracle.

---

## 10. v1.1 development priority and change control

Upstream work must not derail the v1.1 amplification/qualification program.

Priority order:

1. preserve the active v1.1 experimental program and frozen evaluation rules;
2. use bridge/interop work as a pressure test of the public seam;
3. record integration friction in `docs/V1_1_INTEGRATION_FEEDBACK.md`;
4. do not change ExactScope core merely to make one runtime adapter prettier;
5. only promote a repeated integration problem into a core/API proposal after independent evidence;
6. freeze the final adapter contract only after the relevant v1.1 public semantic boundary is stable.

If an integration suggests a core change, the report must include:

```text
integration friction
current workaround
proposed core/public-interface change
which runtimes exhibit the problem
performance impact
ABI/API impact
security/fail-closed impact
whether required or ergonomic only
evidence supporting the change
```

High-risk changes require explicit architecture review before implementation:

- public contract changes;
- fail-open/fail-closed semantics;
- authority/coverage logic;
- security boundary changes;
- new inference/retry path;
- benchmark methodology changes;
- upstream-facing performance/quality claims.

---

## 11. AI-specific review checklist

Before declaring work complete, explicitly answer each item.

### Source/API truth

- [ ] Did we read the current upstream source rather than rely on model memory?
- [ ] Is every relied-upon API classified as public/stable/experimental/internal?
- [ ] Are exact versions/commits recorded?
- [ ] Did we compare with an official upstream example or test?

### Semantics

- [ ] Can any failure silently become an ungrounded answer?
- [ ] Can the adapter change authority, evidence meaning, or qualification state?
- [ ] Can the adapter accidentally make a second model call?
- [ ] Are unknown/ambiguous/conflict/unavailable states preserved?
- [ ] Are context/budget failures explicit rather than hidden by dropping evidence?

### Testing

- [ ] Are there tests not authored from the same assumptions as the implementation?
- [ ] Did a Breaker create new counterexamples?
- [ ] Are negative cases at least as important as the happy path?
- [ ] Is model-call count directly asserted?
- [ ] Is a clean-room reproduction available or its absence disclosed?

### Upstream contribution quality

- [ ] Would the proposed PR still be useful if ExactScope did not exist?
- [ ] Is the diff minimal?
- [ ] Does it avoid product marketing?
- [ ] Are CLA/license/header/style requirements understood?
- [ ] Are all claims limited to measured evidence?

### Reporting

- [ ] Are known limitations written down?
- [ ] Are unverified claims labeled `NOT VERIFIED`?
- [ ] Are generated artifacts separated from authoritative source/spec files?
- [ ] Did we avoid changing expected outputs merely to make a failing test pass?

Any unchecked item blocks a strong compatibility claim or upstream PR unless the Judge documents why it is genuinely non-applicable.

---

## 12. Required final report for the current working agent

For each meaningful upstream/interop implementation slice, report:

```text
A. Goal and upstream target
B. Exact upstream public seam used
C. Exact versions/commits
D. Files changed
E. Dependencies added/removed
F. Positive test evidence
G. Negative/adversarial test evidence
H. Differential/upstream-conformance evidence
I. Clean-room evidence
J. Known limitations
K. Unverified claims
L. Integration friction that may affect v1.1
M. Recommended next action: continue locally / request maintainer guidance / PR-ready / stop
N. Judge result: PASS / FAIL / NOT VERIFIED
```

The report must distinguish:

- **observed fact**;
- **inference**;
- **proposal**;
- **unverified assumption**.

Do not compress those categories into one confident narrative.

---

## 13. Human decision boundary

The human project owner does not need to manually author or line-review every generated line in order to use AI-assisted development responsibly.

The human-owned responsibilities are instead:

- choose the problem and product direction;
- define non-negotiable semantic/safety boundaries;
- decide what evidence is sufficient for a public claim;
- approve public contract changes;
- approve benchmark methodology changes;
- approve upstream PR submission when evidence gates pass;
- reject changes whose maintenance burden or product direction is wrong even if technically valid.

AI agents may implement, test, attack, audit, and summarize. They may not replace the evidence gate.

The governing principle is the same one ExactScope applies to model output:

> **Do not trust a plausible answer when a verifiable contract and evidence can decide the question.**
