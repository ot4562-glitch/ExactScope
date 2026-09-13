# llama.cpp reference integration

This directory maintains three deliberately narrow llama.cpp integration paths:

- `grounding_v1.py` — the maintained grounding reference/development adapter used by stable-v1 regression work and v1.1 material experiments; it is **not** the current Harness Distillation selector or the final v1.1 product boundary;
- `direct_eval_smoke.py` — the one-tool direct `xs_eval` semantic path;
- `calc_plan_smoke.py` — the one-tool bounded `xs_calc` plan path.

The grounding path is the flagship consumer path. The quantitative adapters remain separate because ordinary factual grounding should not force a weak model through a tool catalog.

These are adapters only. They do not calculate, round, invent values, convert units, choose a broader operation, or repair semantic errors.

## Grounding reference adapter and v1.1 development input

`grounding_v1.py` connects to an already-running **loopback-only** llama.cpp OpenAI-compatible endpoint. The privacy boundary accepts only literal loopback IP URLs (for example `127.0.0.1` or `[::1]`), uses a direct HTTP connection that does not consult environment proxies, does not follow redirects, and bounds one response to 1 MiB. It does not start another daemon, add a verifier model, or retry a failed model answer.

For current v1.1 work, treat this file as a **reference host/adaptation surface**, not as the product compiler. The active Harness Distillation milestone is the separate preregistered `Base B` / predeclared reference `F` / `CompiledCandidate(P)` reference-preserving cost-reduction study. `grounding_v1.py` still provides useful material behavior and runtime evidence: `GroundingSession.open()` validates profile state once, `bind_corpus()` freezes one canonical corpus snapshot, and `prepare()` compiles the stable answer contract, projection policy and prompt prefixes into `PreparedAmplifier`. Repeated `PreparedAmplifier.plan()` calls perform no profile/corpus file I/O, contract recompilation, model-prefix rebuild, or model-surface digest recomputation. Retrieval-only text stays separate from the model instruction; `precision-context-v5` keeps complete contiguous source context while collapsing exact body mirrors only when they add no query-relevant title identity, suppressing exact repeated context spans, and conservatively selecting a 512 B, 1 KiB, or 2 KiB evidence tier; model/runtime surface calibration can be persisted by identity; and model-required plans expose a stable prefix identity that the host may map to a backend-native cache only after parity is established for that model/runtime combination.

The selected route order is fixed:

```text
GroundingFrame
  -> unresolved authoritative state? host disposition, 0 model calls
  -> one compatible grounded scalar AND retrieval query == instruction? typed host value, 0 model calls
  -> no routed target / empty supplemental target? ordinary model knowledge
  -> otherwise amplified bounded evidence + typed output contract, 1 model call
```

For a previously unseen model/runtime identity, the default preflight remains the frozen full calibration: it probes `json-schema-v1` and `compact-gbnf-v1`, selects the first compatible surface, and evaluates every answer-contract candidate on that surface. Explicit surface rejection may fall through; transport/runtime failures stop immediately and a zero-score semantic calibration remains unsupported. The strict result is bound to the host-owned immutable model/runtime/surface-config key, grounding policy SHA-256, and ExactScope model-surface SHA-256. With `--capability-cache-dir`, `answer` writes that record under a content-addressed identity on the first successful use and later requests reuse it without repeating calibration. The host **MUST change `--model-key` whenever model bytes, llama.cpp runtime, chat template, reasoning mode, or other surface-affecting launch configuration changes**. Cache reuse never relaxes record validation, never triggers a retry, and never switches surfaces mid-request.

`calibrate-staged` is an unreleased additive experiment. It probes output surfaces in preference order and stops at the first supported one, then evaluates tie-preferred `answer-object-v3` first. It stops after that profile only when v3 is perfect on all frozen cases, which mathematically fixes the same winner as the full selector; otherwise it evaluates the remaining candidates. The common JSON-Schema/v3-perfect path therefore needs 5 model requests instead of 14, while ambiguous cases fall back to the full semantic comparison. Staged records carry explicit partial-evidence/accounting fields and are accepted by the same `doctor`/`--contract-record` loader, but the default capability cache continues to create full records until this experiment is qualified.

Typical setup against a running local server:

```text
python3 adapters/llama-cpp/grounding_v1.py calibrate \
  --profile <grounding-profile-dir> \
  --base-url http://127.0.0.1:8080/v1 \
  --model local-model \
  --model-key "model-sha256:<model>;runtime-sha256:<runtime>;surface-config-sha256:<config>" \
  --output grounding-contract.json
```

Before serving traffic, validate the exact profile + calibration binding without contacting llama.cpp:

```text
python3 adapters/llama-cpp/grounding_v1.py doctor \
  --profile <grounding-profile-dir> \
  --contract-record grounding-contract.json \
  --model-key "model-sha256:<model>;runtime-sha256:<runtime>;surface-config-sha256:<config>"
```

`doctor` performs **zero network/model requests**. It revalidates the profile and strict calibration record, recomputes the selected surface/contract, and prints only digests plus the selected IDs; the raw model key is not printed.

Then answer one factual question:

```text
python3 adapters/llama-cpp/grounding_v1.py answer \
  --profile <grounding-profile-dir> \
  --contract-record grounding-contract.json \
  --model-key "model-sha256:<model>;runtime-sha256:<runtime>;surface-config-sha256:<config>" \
  --base-url http://127.0.0.1:8080/v1 \
  --model local-model \
  --question "Which replacement filter does the Rover Mini use?"
```

When the model instruction contains classification/output wording that should not affect retrieval, pass a separate retrieval query:

```text
  --question "Classify the claim as SUPPORTS, REFUTES, or NOT ENOUGH INFO: The Rover Mini uses RM-F42." \
  --retrieval-query "The Rover Mini uses RM-F42."
```

An explicit retrieval query that differs from the instruction disables direct host scalar completion, so the retrieved scalar cannot accidentally answer a different operation such as a comparison or yes/no question. In that split-query case, single-target grouped evidence retains the target label because the retrieval-only wording is not otherwise visible to the model.

For an optional local corpus, v1.1 defaults to `--corpus-evidence-bytes 2048 --corpus-evidence-policy adaptive-evidence-v1 --corpus-projection precision-context-v5`. The 2048-byte value is a cap: a clear retrieval may conservatively use 512 B or 1 KiB, while ambiguous/weak retrieval keeps the full cap. The renderer can overfetch bounded lexical candidates before the final model-item cap, collapses byte-identical document bodies only when a repeated copy contributes no new query-relevant title terms, suppresses exact normalized repeated context spans, then keeps the query-best sentence with the nearest directional context: a first-sentence anchor takes its successor and later anchors take their predecessor. If the pair does not fit, the complete anchor is retained; if even that cannot fit the selected adaptive tier, the tier is promoted up to the unchanged 2 KiB cap. Sentences are never truncated. `--answer-kind` can request `text`, `choice`, `boolean`, `integer`, or `number`; repeated `--answer-choice` values are the compatibility shorthand for the generic choice contract. Numeric contracts may add `--answer-minimum` / `--answer-maximum`. Long-lived in-process hosts should create one `GroundingSession`, bind immutable corpora, then call `prepare()` once per stable contract/configuration and reuse the resulting `PreparedAmplifier`. Disk changes do not mutate a running prepared amplifier; opening a new session is the explicit operation that adopts changed artifacts.

`plan` performs the same retrieval/authority/host-routing decision but never invokes the model. By default it prints only the route/model-call decision, reply (when host-completed), selected contract and profile digest so private evidence is not sprayed into terminal logs. Use `plan --verbose` only when you explicitly need the full frame, audit and model messages for debugging; that output may contain private/device evidence.

The earlier v1.1 optimization/holdout results remain development history. The first fresh Harness Distillation transfer has since completed and **rejected** its compiled candidate: the calibration-tied cheaper policy failed the fresh reference-quality gate, so no deployable profile was emitted. A post-failure selector change cannot be validated on that same held-out. The next substantive compiler proof is the preregistered **120 fresh calibration / 600 fresh held-out** `B` / `F` / `P` study defined in `docs/V1_1_PRODUCT_DIFFERENTIATION.md`; this adapter's own surface/profile calibration machinery is separate from that compiler-selection algorithm.

## Quantitative capability requirement

The maintained path requires a capability bundle with `surface-contract.json` and `bindings.surface_contract_sha256`. Legacy generated hot-set directories and frozen pre-contract capability revisions are not accepted implicitly.

Before constructing a model request the adapter verifies:

- capability manifest digest and exact regular-file inventory;
- profile/task-map/catalog/model-asset cross-file consistency;
- exact model-surface contract ID/version/digests;
- host acceptance policy for ABI/hot-set/tool/grammar/prompt contract versions;
- a semantic-only surface: `xs_calc=false`, `xs_find=false`, one `xs_eval` tool;
- the bound `xs-eval.tool.json`, `xs-eval.gbnf`, prompt fragment, and selected catalog.

This reference is deliberately narrow. A capability that also exposes `xs_calc` needs a combined adapter rather than silently hiding one of its declared tools.

## Server

Use a model/chat template that supports tool calling. llama.cpp server flags and template behavior can change independently of ExactScope. A typical shape is:

```text
llama-server -m <model.gguf> --jinja --host 127.0.0.1 --port 8080
```

The adapter fails if the server returns ordinary text instead of the expected tool call. It never treats a silently ignored `tools` array as success.

## Offline adapter self-test

No model, network, or ExactScope runtime execution is used:

```text
python3 adapters/llama-cpp/direct_eval_smoke.py --self-test
```

The self-test uses the tracked one-operation `adapters/generated/p0-smoke` assets only as semantic fixture input, then constructs a complete canonical capability/profile/manifest/surface-contract in a temporary directory. No checked-in capability revision is modified or granted new evidence.

The self-test checks rejection of:

- a legacy capability without explicit model-surface negotiation;
- unknown operations;
- wrong scalar/vector shape or arity;
- numeric JSON values where exact decimal strings are required;
- noncanonical decimal spellings such as `01`, `+1`, or `NaN`;
- overlong decimal leaves;
- duplicate JSON object keys.

## Inspect a request without sending it

Supply a newly generated capability that already contains explicit surface negotiation:

```text
python3 adapters/llama-cpp/direct_eval_smoke.py \
  --dry-run \
  --capability <capability-bundle> \
  --model local-model
```

The system message is the compiler-generated `prompt-fragment.txt` **exactly once**. The adapter no longer rebuilds and appends the catalog signatures a second time. Model-token budget is part of the constrained-AI product boundary.

## Run against llama.cpp

```text
python3 adapters/llama-cpp/direct_eval_smoke.py \
  --capability <capability-bundle> \
  --base-url http://127.0.0.1:8080/v1 \
  --model <server-model-name> \
  --prompt <task-text>
```

For a one-operation midpoint-elasticity capability, expected model arguments are logically equivalent to:

```json
{
  "op": "econ.ped.mid",
  "a": ["10000", "12000", "100", "80"]
}
```

The response validator requires:

- exactly one response choice and one function tool call;
- function name `xs_eval`;
- exactly `op` and `a` argument fields;
- no duplicate JSON keys when arguments are returned as a JSON string;
- an operation present in the exact bound capability catalog;
- exact positional arity and scalar/vector shapes;
- decimal leaves matching ExactScope's base-10 lexical grammar, at most 96 characters each;
- at most 64 values per vector and at most 64 decimal leaves across the call.

On success it prints the validated call together with capability bundle digest, model-surface digest, hot-set digest, profile id/revision, and operation revision. **It does not execute the arithmetic.** The real product host forwards that validated call to the matching native/Wasm ExactScope runtime.

## `xs_calc` bounded-plan reference

`calc_plan_smoke.py` is the matching one-tool reference for a **calc-only** capability (`xs_calc=true`, zero semantic `xs_eval` operations, `xs_find=false`). It uses the same explicit model-surface negotiation rule and never evaluates the plan itself.

```text
python3 adapters/llama-cpp/calc_plan_smoke.py --self-test

python3 adapters/llama-cpp/calc_plan_smoke.py \
  --dry-run \
  --capability <calc-only-capability> \
  --model local-model
```

The offline self-test validates 1–8 steps, operation arity, exact decimal lexical form, duplicate/unknown fields, backward-only `#` references, literal `powi` exponent constraints, and the 512-byte canonical request ceiling. A referenced `powi` exponent is left to ExactScope because the adapter does not execute earlier steps to discover that value.

The historical `examples/llama.cpp/run_xs_calc.py` has a different purpose: it runs a model, invokes the ExactScope core, and records latency/token/result information. It is benchmark/evaluation tooling, **not** the maintained execution-free integration boundary and is not required for adapter self-tests.

## Why `tool_choice=auto` remains the default

Tool-template behavior varies by model and llama.cpp version. Both reference adapters still require an actual tool call to succeed. `--tool-choice required` is available where the server/model template reliably supports it.

## GBNF

The capability bundle also binds `xs-eval.gbnf`. The OpenAI-compatible tool path uses the generated JSON tool asset, while GBNF remains a separate exact model-surface artifact for constrained-generation integrations. The adapter validates that both are part of the same negotiated surface even though it sends only the tool schema on this API path.
