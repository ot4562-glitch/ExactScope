# Grounding runtime — rc4 reference implementation

Status: **IMPLEMENTED / NO-INFERENCE REFERENCE**

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

## Transport decision

No new native C ABI or Wasm grounding transport is introduced for the rc4
reference candidate. The frozen reference provider performs host filesystem
asset loading, profile validation, routing and local retrieval, so forcing this
behavior into the no-import quantitative core would add an unnecessary ABI and
platform dependency without improving the benchmark question.

The existing Rust/C/Wasm quantitative subsystem remains unchanged and is still
available as the separate deterministic calculation subsystem. A future product
profile may define a stable native or Wasm grounding transport only when a real
integration requires it; that would receive its own contract/profile identity.

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
