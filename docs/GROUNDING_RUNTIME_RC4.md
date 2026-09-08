# Grounding runtime — rc4 reference implementation

Status: **v1 implementation record; selected r25 host policy is shipped alongside the stable Linux x86-64 native grounding software path. Physical ARM64 qualification remains unclaimed.**

This document records the concrete implementation choice made after the frozen
Grounding Contract v0.1 and reference GroundingProfile were completed.

## Runtime boundary

The rc4 reference grounding path is host-side. `tools/grounding_runtime.py`
implements the frozen provider-neutral serving boundary and the local
`local-exact-lexical` reference provider. It does not invoke a language model.

The path is:

```text
QueryEnvelope
 -> deterministic reference router
 -> RetrievalProvider interface
 -> local exact/lexical provider
 -> typed ProviderOutcome records
 -> deterministic Evidence Policy
 -> grouped GroundingFrame + audit sidecar
 -> frozen Model Projection renderer/policy/template
```

The runtime verifies the reference profile manifest, canonical JSON bytes,
SHA-256 references, provider identity, source snapshots, adapter configuration,
index/source consistency, target/provider/source bindings, and the profile
identity before serving a request.

## Selected r25 completion order

The selected r25 v1 host policy adds no second retrieval system. It uses the same validated `GroundingFrame` and resolves it in this order:

1. one unresolved authoritative target in `none`, `unavailable`, `ambiguous`, or `conflict` -> deterministic host disposition;
2. exactly one `grounded` item with contract-native `content.kind = scalar` -> deterministic canonical scalar value from the host;
3. no routed target or an empty supplemental target -> ordinary model knowledge with no grounding context;
4. remaining grounded text -> compact model projection + frozen grounding policy + one model answer call.

The scalar lane is not text post-processing. The source adapter must already have supplied a valid canonical scalar under Grounding Contract v0.1. The host never derives a scalar by regexing a text evidence sentence, consulting benchmark gold, or guessing a value. Text evidence therefore remains a real model-interpretation problem.

In the frozen 30-item matched screen this order produced 10 unresolved host completions, 13 scalar host completions and 7 model calls. All 23 host completions were correct in all seven measured models. The same semantic scores were reproduced after native C-ABI/release integration; the measurements remain bound to that exact provider/corpus/policy screen rather than becoming a universal accuracy claim.

`adapters/llama-cpp/grounding_v1.py` is the first selected consumer adapter. It talks only to a loopback llama.cpp endpoint, performs no retry, and uses a one-time model-identity-bound answer-contract calibration for model-required questions. The reusable selected model-facing bytes live in `tools/grounding_v1_surface.py`.

## Transport decision

v1 exposes the deterministic `.xsgi` search/projection core through the native C ABI. The native boundary binds and validates immutable provider bytes, performs bounded search with caller-owned scratch, and emits deterministic compact evidence. It does not absorb host responsibilities such as application security scope, routing, authority, provider access, or model execution.

Grounding Wasm remains deferred. The existing no-import Wasm path continues to belong to the separate quantitative subsystem until a grounding Wasm transport has its own parity and qualification evidence.

## Provider behavior

The local provider is intentionally small and replaceable. The provider-neutral
`RetrievalProvider` interface prevents the exact/lexical implementation from
becoming the universal grounding contract.

For the reference profile:

- only digest-bound local sources are read;
- network access is denied;
- only ASCII `A-Z` is folded to lowercase;
- tokens are maximal ASCII `[a-z0-9]+` runs;
- exact alias match wins, otherwise at least two distinct overlapping tokens are
  required;
- ranking and tie-break order are frozen by the reference profile assets;
- rank never establishes authority;
- authority comes only from TargetPlan/source bindings;
- no result is silently truncated;
- a complete empty required search is `none`;
- timeout/error/denied/budget/incomplete required coverage is `unavailable`;
- conflicting canonical content for one target is `conflict`;
- the reference router rejects ambiguous alias configuration at profile load;
- the static reference profile rejects `as_of` and timestamp-bearing evidence.

## Model Projection

The renderer is separately digest-bound by the profile. It emits deterministic
compact JSON data and a fixed higher-priority grounding policy. Model-visible
data preserves target label, authority, state and approved content while
omitting security scope, profile digest, provider scores and content digests.
Evidence is escaped as untrusted data; no claim is made that delimiters alone
eliminate prompt injection.

## Benchmark isolation

The serving runtime has no scorer-gold input, expected-answer field, expected
source/evidence ID, or expected target mapping. The future benchmark generator
must physically separate serving and gold trees, and the scorer must remain the
only component that opens gold data.

## Verification

`tools/test_grounding_profile.py` verifies the frozen P1 identities and schemas.
`tools/test_grounding_runtime.py` verifies the host/provider/policy/frame/
projection behavior without inference, including complete no-hit versus
unavailability, provider completion-order invariance, conflict handling,
security scope, projection budgets, adversarial evidence escaping, and absence
of benchmark-gold dependencies.

No model accuracy, latency, RAM, energy, or physical-target claim is established
by these implementation tests.
