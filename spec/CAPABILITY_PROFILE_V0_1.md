# ExactScope capability profile v0.1

Status: **design draft**. This document defines the proposed machine-readable identity for a deployed ExactScope capability slice. It is not yet a stable runtime ABI or release-format promise.

See [`../docs/CAPABILITY_PRODUCT_ARCHITECTURE.md`](../docs/CAPABILITY_PRODUCT_ARCHITECTURE.md) for the product rationale and [`schemas/capability-profile.schema.json`](schemas/capability-profile.schema.json) for the matching design-draft machine-readable shape.

## 1. Purpose

A hot set answers "which operations are selected?" A capability profile must answer a larger product question:

> **What narrow AI capability is this artifact intended to add, what model-facing surface does it expose, what device/model budgets does it obey, and what evidence identifies the claim?**

The profile is build-time/deployment metadata. The AI model does not need to read this full document or JSON object at runtime.

## 2. Profile identity

Canonical conceptual fields:

| Field | Meaning |
|---|---|
| `format` | fixed profile format identifier |
| `format_version` | profile-format revision |
| `profile_id` | immutable product/profile identifier |
| `profile_revision` | revision of this profile definition |
| `domain` | primary reviewed domain source |
| `task_families` | outcome-oriented capability families this slice is designed to cover |

A profile ID identifies the selected capability product, not merely an operation-count label.

## 3. Runtime surface

`runtime_surface` records what the AI/host can actually invoke.

Proposed fields:

- `xs_calc.enabled` — whether the generic bounded arithmetic lane is present;
- `xs_calc.plan_revision` — plan contract identity when enabled;
- `xs_eval.operations` — canonical semantic operation keys selected for the profile;
- `xs_find.enabled` — normally `false` for a weak-model serving profile;
- `normal_model_turns_max` — intended hot-path model-turn budget, normally `1`;
- `model_visible_tools_max` — maximum number of top-level tools exposed to the model.

The broad domain source catalog must not be implied by `xs_eval.operations`; only the selected slice is model-visible.

## 4. Model difficulty budget

`model_budget` records constraints that affect weak-model usability.

Proposed fields:

- `semantic_operation_count`;
- `prompt_fragment_bytes_max`;
- `schema_bytes_max`;
- `grammar_bytes_max`;
- `generated_request_tokens_max` where a tokenizer-specific record is available;
- `request_bytes_max`;
- `plan_steps_max`;
- `normal_model_turns_max`;
- optional tokenizer-specific prompt token measurements.

Measured benchmark results such as valid-call rate do not belong in the immutable budget itself; they belong in evidence records linked from the profile.

## 5. Device footprint budget

`device_budget` records the intended deployment envelope.

Proposed fields:

- `artifact_bytes_max`;
- `resident_bytes_max` when known/frozen;
- `scratch_bytes_max` when known/frozen;
- `imports_max` for Wasm profiles;
- `target_profile` such as native-static or no-import-wasm;
- optional architecture/toolchain constraints.

A released artifact may use less than the budget. Exceeding the budget requires a new profile revision or explicit qualification rule.

## 6. Bindings and artifact identity

`bindings` should make generated model assets and runtime semantics immutable together.

Proposed digests/identities:

- core/ABI revision;
- scope-pack/fused-registry digest;
- hot-set/source selection digest;
- tool-schema digest;
- grammar digest;
- prompt-fragment digest;
- final runtime artifact digest;
- compiler/profile-generator version.

A mismatch invalidates the profile binding. The host must not silently combine a model surface from one registry with an artifact from another.

## 7. Evidence identity

`evidence` links the profile to reproducible validation without embedding benchmark results into the runtime contract.

Proposed fields:

- golden/conformance suite ID and digest;
- benchmark mapping ID and digest;
- supported task-family corpus identity;
- optional qualification-record IDs;
- optional model-evaluation result bundle IDs.

The profile may exist before all evidence is complete, but support/marketing labels must identify which evidence gates have actually passed.

## 8. Support label

A small explicit support label prevents "it compiled" from becoming a support claim.

Initial conceptual values:

- `experimental` — design/integration evaluation only;
- `benchmarked` — reproducible model-level evidence exists for the profile;
- `target-qualified` — a named constrained target has passed the required integration/resource checks;
- `lts` — a maintained compatibility/change-control promise exists.

The exact stable registry of support labels should be frozen later if the profile format is adopted.

## 9. Statistics example

A first Statistics profile can select the existing `statistics-core-8` operations:

```text
stats.sum
stats.mean
stats.mean.weighted
stats.var.pop
stats.var.sample
stats.sd.pop
stats.sd.sample
stats.corr.pearson
```

The capability claim is not "contains 8 operations." The intended task-family claim is closer to:

- common descriptive aggregation;
- weighted mean;
- explicit sample/population variance and standard deviation;
- Pearson correlation;
- fail-closed method distinction where semantic identity matters.

That distinction is why `task_families` exists separately from `xs_eval.operations`.

## 10. Example shape

See [`examples/statistics-capability-profile.json`](examples/statistics-capability-profile.json).

Conceptually:

```json
{
  "format": "exactscope.capability.profile",
  "format_version": "0.1-draft",
  "profile_id": "statistics-core-8-ai",
  "profile_revision": 1,
  "domain": "statistics",
  "task_families": [
    "descriptive-aggregation",
    "variance-standard-deviation-method-selection",
    "pearson-correlation"
  ],
  "runtime_surface": {
    "xs_calc": {"enabled": true, "plan_revision": "plan-v0.1"},
    "xs_eval": {"operations": ["stats.sum", "stats.mean"]},
    "xs_find": {"enabled": false},
    "model_visible_tools_max": 2,
    "normal_model_turns_max": 1
  }
}
```

The full example intentionally uses placeholder/null evidence digests where release data does not yet exist. A draft profile must not invent proof.

## 11. Compiler relationship

The future capability compiler should consume:

- domain source metadata;
- required task families;
- target model/runtime constraints;
- device footprint budget;
- optional benchmark-derived selection guidance.

It should emit:

- a capability profile;
- selected/fused runtime data;
- model-facing tool/schema/grammar/prompt assets;
- manifests/digests;
- conformance inputs;
- benchmark/evidence linkage metadata.

The first compiler should be deterministic and configuration-driven. Model-based automatic selection is not required.

## 12. Validation rules for a future schema

If this design is promoted to a machine-validated schema, at minimum enforce:

1. non-empty `profile_id`, `domain`, and `task_families`;
2. unique canonical `xs_eval.operations`;
3. `xs_find.enabled=false` by default for serving profiles;
4. fixed positive upper bounds for artifact/request/tool/turn budgets;
5. `xs_calc.plan_revision` required when `xs_calc.enabled=true`;
6. digest fields either valid SHA-256 strings or explicitly absent while experimental;
7. support labels cannot exceed the available evidence gate;
8. model-visible operation count must agree with the selected semantic operation list;
9. profile revisions are immutable once attached to a published release artifact.

## 13. Product rule

A capability profile is successful only when its linked benchmark shows that the target weak model gains a useful task-family capability at an acceptable tool penalty and at a sufficiently small device/model cost.

A larger profile is not automatically better. The default optimization target is the **smallest profile that closes the required capability gap**.
