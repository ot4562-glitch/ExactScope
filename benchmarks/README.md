# ExactScope benchmark harness

This directory implements the measurement contract in `docs/BENCHMARK.md`. It is developer/CI tooling, not a target runtime dependency.

## What is measured

The runner keeps these stages separate:

- tool-use recognition;
- canonical operation selection;
- exact argument extraction/order;
- tool-call validity;
- actual Tiny JSON/core status;
- final answer correctness;
- result/failure fidelity;
- incorrect numeric answer rate;
- model turns;
- provider-reported input/output token counts when available;
- model latency;
- ExactScope core latency;
- discovery latency.

The raw `results.jsonl` remains the source of truth. `summary.json` contains aggregate rates/means plus digests identifying the corpus, hot set, and exact core executable used for the run.

## Four arms

The first harness supports all benchmark arms frozen in the product contract:

| Arm | Path |
|---|---|
| `model_only` | model solves the quantitative problem itself |
| `direct` | one model turn selects/extracts and calls `xs_eval`; host returns the ExactScope result directly |
| `discovery` | `xs_find`, actual ExactScope discovery, then a second model turn for `xs_eval` |
| `constrained` | one model turn emits raw `xs_eval` arguments under the generated GBNF, then ExactScope executes |

The direct/constrained arms deliberately do not add a second model pass to paraphrase the ExactScope result. This preserves the product hypothesis that a known hot-set operation can be one inference turn plus deterministic execution.

## Core bridge

Build the host-side benchmark bridge:

```text
cargo build --package exactscope-conformance --bin exactscope-core
```

It reads one canonical Tiny JSON request from stdin and calls the real `exactscope-tinyjson` adapter. It does not contain benchmark formulas.

## Offline self-test

Windows example:

```text
python3 benchmarks/run_benchmark.py --self-test --core target/debug/exactscope-core.exe
```

Linux/macOS example:

```text
python3 benchmarks/run_benchmark.py --self-test --core target/debug/exactscope-core
```

The self-test checks corpus/core agreement for every executable case and runs actual `xs_find` discovery. It makes no model-quality claim.

## Real llama.cpp run

Start a tool-capable llama.cpp server, then run:

```text
python3 benchmarks/run_benchmark.py \
  --core target/debug/exactscope-core \
  --base-url http://127.0.0.1:8080/v1 \
  --model <server-model-name> \
  --output-dir target/benchmark/<model-id>
```

The constrained arm sends the checked-in generated GBNF in llama.cpp's request-level `grammar` field. The direct/discovery arms use OpenAI-compatible generated tool definitions.

Do not publish improvement claims from the self-test. Public accuracy/latency/token/energy claims require recorded real-model runs with immutable model/runtime/hardware metadata.
