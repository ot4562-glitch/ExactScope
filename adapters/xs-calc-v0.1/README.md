# `xs_calc` plan-v0.1 model assets

This directory contains the first checked-in model-facing assets for ExactScope bounded arithmetic plans.

Files:

- `xs-calc.tool.json` — OpenAI-compatible function definition;
- `xs-calc.gbnf` — llama.cpp-style bounded grammar, including an explicit 1-8 step limit and bounded whitespace;
- `prompt-fragment.txt` — compact host/system guidance.

The runtime contract is defined by [`../../spec/PLAN_V0_1.md`](../../spec/PLAN_V0_1.md) and the reusable JSON Schema is [`../../spec/schemas/xs-calc-tool.schema.json`](../../spec/schemas/xs-calc-tool.schema.json).

These files contain no calculation logic. Runtime validation and calculation remain authoritative in `exactscope-kernel` / `exactscope-tinyjson`.

Important: grammar-level result references permit `#0` through `#7`; the runtime additionally enforces that a reference points only to an earlier step. This avoids exploding the grammar while preserving fail-closed semantics.
