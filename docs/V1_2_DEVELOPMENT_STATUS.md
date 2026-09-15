# ExactScope v1.2 development status

Status: **ACTIVE DEVELOPMENT / RESEARCH**

Updated: **2026-09-15**

Latest stable release: **v1.1.0**

## Current product direction

ExactScope v1.2 is being narrowed into a cold-path configuration selector/exporter for AI products that already work.

> **Keep the existing AI stack. Use its existing measurements and capabilities. Select only a non-overlapping minimum-sufficient configuration, export it in the host's native form, and leave the production path.**

The intended production result has no ExactScope daemon, inference server, retrieval/index, evaluation engine, model call, or hot-path dependency when the host can consume the exported configuration directly.

## What v1.2 is not trying to become

ExactScope is not trying to replace or compete head-on with:

- RAG frameworks or vector databases;
- prompt/program optimizers;
- benchmark/evaluation harnesses;
- agent frameworks or routers;
- inference runtimes;
- tokenizer/chat-template stacks;
- structured-generation engines;
- cache/scheduler/telemetry systems.

Those systems are hosts or suppliers. If a host already implements a capability well, ExactScope should reuse it or delete its own copy.

## Current leading product hypothesis

The current leading hypothesis is a **minimum-sufficient configuration selector**:

1. consume externally produced candidate measurements;
2. require an explicit quality floor and cost definition;
3. select a cheaper configuration only when comparative evidence supports it;
4. emit host-native configuration/IDs/settings;
5. disappear from production.

A small external-result importer is supporting plumbing only. Semantic lowering is a cross-cutting `SUPPORTED | LOSSY | UNSUPPORTED` verification property, not a compatibility runtime.

## Current evidence

### Zero-runtime deletion chain

On one frozen MMLU-Pro development profile, the counted ExactScope semantic delta was reduced from:

- **18,114 B** -> **1,389 B** -> **708 B**

while preserving **96/96 deterministic request parity** and keeping ExactScope hot-path imports, model calls, and extra network round trips at **0**.

This is an architecture/deletion result, not a product-value claim.

### Promptfoo native falsification

Promptfoo `0.123.0` represented the remaining tested chat-message and per-test structured-output semantics natively with:

- message semantic parity: **96/96**;
- response-format semantic parity: **96/96**;
- external model calls: **0**;
- custom execution files: **0**;
- ExactScope runtime dependency: **0**.

Result: ExactScope will **not** build a Promptfoo-specific executor for that job.

### First external-result import

A strict data-only Promptfoo result importer consumed **96** externally produced rows without starting Promptfoo or a model again and normalized only the candidate observations needed for selection.

The artifact contained only one candidate, so ExactScope returned:

`selected_candidate = null`

`NO_SELECTION_EVIDENCE`

This is deliberate. v1.2 must not manufacture an optimization decision when comparative evidence is missing.

## Current research order

1. Try to delete output-surface selection as ordinary host configuration.
2. Obtain a real externally measured artifact with at least two comparable candidates plus the unchanged host baseline.
3. Predeclare a quality floor and cost definition, then test the minimum-sufficient selector.
4. Compare that workflow against host-native tooling or a small script; kill the product wedge if it is equally easy.
5. Test a second materially different host using `SUPPORTED | LOSSY | UNSUPPORTED`, not a compatibility runtime.
6. Resume context-budget/runtime-cost selection only when a concrete host selection gap appears.
7. Run customer-like and broad release evidence only after the surviving product boundary is frozen.

## Upstream integration status

ExecuTorch issue `pytorch/executorch#22761` is open, labeled `rfc`, and currently assigned to `mergennachin`. The assignment is a useful maintainer/placement signal, but it is **not acceptance and not a dependency of ExactScope v1.2**.

Current ExecuTorch `GenerationConfig` already exposes host-native settings including grammar, maximum new tokens, sequence length, and temperature. The current v1.2 direction may therefore require **no ExecuTorch runtime change at all**. The issue is being treated as a coordination/feedback channel while that is clarified.

ONNX Runtime GenAI `#2549` and LiteRT samples `#308` remain open without an assignee at the time of this update.

See `V1_2_UPSTREAM_INTEGRATION_STATUS.md` for the detailed boundary.

## Release boundary

`v1.2` is **not released**. `v1.2.0-alpha.1` remains a frozen research/engineering checkpoint rather than a stable release. The latest stable release is still `v1.1.0`.

A future v1.2 release must show that the surviving selector/exporter creates measurable value over both the unchanged host and a simple native/manual alternative without rebuilding the host's AI stack.
