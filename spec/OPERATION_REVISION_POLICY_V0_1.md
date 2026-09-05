# ExactScope operation revision policy v0.1

Status: active prerelease compatibility policy. This policy defines identity and change control; it does not by itself create a Tier 1/Tier 2 support promise.

## 1. Identity

The semantic public identity of an operation is:

```text
canonical operation key + operation revision
```

Pack-local numeric operation IDs and internal kernel IDs are separate namespaces. Neither may be inferred from the operation revision. Existing stable internal kernel IDs are never renumbered merely because an operation revision changes.

An existing `(canonical key, revision)` is immutable. A frozen capability or release artifact keeps its original bytes and identity even after newer revisions exist.

## 2. What is part of an operation revision

Changing any of the following requires a new operation revision unless the policy below requires a new key instead:

- argument count, names, order, scalar/vector shape, or numeric semantic kind;
- input constraints or cross-input relations;
- unit compatibility or output unit rules;
- deterministic mathematical definition;
- method semantics such as sample vs population or midpoint vs endpoint;
- output count, output names, semantic kinds, scale, rounding, classification, or error/status behavior;
- classification-before-rounding rules or other ordering that can change an observable result.

A same-revision implementation may change internal code, generated plumbing, optimization, layout, or build strategy only when the externally defined exact result/status semantics remain unchanged. Such a change still produces a new core/artifact/source identity.

## 3. When to create a new key

A materially different method SHOULD use a new canonical key rather than overloading a revision. Examples include sample versus population variance, Pearson versus rank correlation, or midpoint versus endpoint elasticity.

A revision is appropriate for an incompatible correction or contract evolution of the same intended method. A new key is preferred when both methods may remain useful side by side.

Canonical keys are never recycled for unrelated semantics.

## 4. Adapter and transport changes are separate

Operation revision and model-surface contract revision are independent compatibility dimensions.

- A tool-schema, grammar, or prompt change that does not change operation semantics may require a new model-surface contract version/digest without changing the operation revision.
- An ABI/wire encoding change may require an ABI/protocol revision without changing the operation revision.
- A semantic operation change requires an operation revision even if the JSON shape or ABI bytes happen to remain parseable.

Hosts must negotiate all relevant dimensions; one matching version does not override a mismatch in another.

## 5. Supported release-line rule

Before ExactScope promotes any artifact to Tier 1 or Tier 2, that release line MUST publish the exact operation revisions it contains.

Once `(key, revision)` appears in a supported release line:

1. its semantics remain immutable permanently;
2. maintenance releases in that supported line MUST NOT silently replace it with another revision;
3. removing it from a successor supported line is an explicit breaking/EOL decision, not an optimization side effect;
4. a replacement revision or key must be named explicitly in compatibility/release records;
5. historical artifacts/evidence remain attached to their original operation revision and are never transferred to the replacement.

ExactScope currently has no stable supported release artifact, so this policy creates no retroactive LTS claim for experimental capability bundles.

## 6. Specialized capability rule

A specialized capability may intentionally expose only a subset of reviewed operations. Omission is part of that capability identity and is not evidence that the omitted operation was deleted globally.

For an **upgrade of the same declared capability surface**, however, removing an existing operation is breaking. Upgrade compatibility therefore defaults to requiring every baseline operation to remain present at the same revision.

A different intentionally narrower capability must use its own profile identity/revision and is compared as a different product slice rather than a transparent upgrade.

## 7. Static upgrade check

`tools/check_operation_revision_compat.py` compares two immutable capability bundles without executing ExactScope.

Default upgrade compatibility requires:

- every baseline operation key remains present;
- no operation revision decreases;
- no existing operation silently changes revision;
- if the same `(key, revision)` remains, the model-visible method/signature/argument metadata remains identical;
- new operation keys are allowed.

A deliberate revision upgrade may be inspected with `--allow-revision-upgrade`; the checker still reports the changed revision and never treats old evidence as applicable to the new revision. Operation removal has no transparent-upgrade override: use a different capability identity when narrowing the surface.

This checker is a compatibility guard, not a proof that the underlying mathematical implementation is correct. Numeric/conformance evidence remains separate.

## 8. Change procedure

For a semantic change:

1. decide whether the change is a new method/key or a revision of the same method;
2. preserve the old key/revision semantics and stable IDs;
3. add the new reviewed semantic definition and implementation binding;
4. regenerate deterministic metadata without rewriting frozen capability revisions;
5. create a new capability/profile revision;
6. run ordinary component/conformance checks appropriate to the change;
7. attach new model/target evidence only to the new exact artifact if such evidence is later collected;
8. update compatibility and migration records before any support promotion.

No benchmark result, model result, or qualification record may be inherited solely because the canonical key stayed the same.
