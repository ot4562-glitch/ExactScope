# Five-arm Statistics runner

Build `exactscope-core`, install `requirements-dev.txt`, then run:

```sh
python benchmarks/test_capability_benchmark.py
python benchmarks/capability_benchmark.py --config local-model-config.json --output benchmarks/output/my-run
```

The configuration contains `small` and optionally `larger` objects, each declaring
`base_url` (llama.cpp `/v1` endpoint), `model`, `model_sha256`, `tokenizer_id`,
`quantization`, `runtime_revision`, `hardware`, `context_size` and `threads`.
Record additional launch settings such as GPU layers and reasoning mode too.
Token counts use that server's `/tokenize` endpoint with special tokens disabled;
full chat prompt/completion usage comes from its actual response. The exact model
and launch configuration must be verified by the operator, not inferred by the runner.

The runner validates all gold calls before querying models, then evaluates the
same items in A (small only), B (calc), C (eval), D (combined), E (larger only).
Tool arms require a permitted request or explicit failure. No-call arms return
a decimal or failure. All paths are one model turn; a host renderer preserves
the runtime response. Result/failure fidelity therefore measures host forwarding,
not a second model's ability to copy a result. Plan selection/extraction have no
unique gold decomposition and remain explicitly unmeasured; semantic operation
selection and ordered argument extraction are measured separately.

Scoring compares numbers at the predeclared six-place half-even Statistics
precision. This is evaluation equivalence only: the host never changes the actual
18-place `xs_calc` response. Error names must match exactly. Missing/ambiguous
methods remain no-call cases, and mismatched/zero-denominator vectors remain typed
runtime failure cases. Syntax failures never trigger retries or repair.

Output includes raw per-item replies, core responses, tokens, model turns, plan
length, model and bridge latency, each arm's actual prompt/grammar, and digest-bound
metadata/summary. Bridge latency includes process startup and JSON transport; it is
not a standalone kernel latency measurement. Partial raw results survive a failed
run, but no complete paired summary is produced for missing items or duplicate IDs.

Optional `incremental_costs` supplies measured D-minus-A `artifact_bytes`,
`resident_bytes`, `prompt_tokens`, `added_ms`, and `joules`. Every density retains
the raw numerator/denominator and scale; missing or non-positive denominators
produce null with a reason. No budget ceiling is treated as measured RAM or energy.
CRR uses `(D-A)/(E-A)` only when E exceeds A. The larger model's costs remain in
its own configuration. These are controlled synthetic corpus results, not public
dataset scores, general model equivalence, target qualification or energy evidence.

## Initial interface experiment

The first complete run used Qwen3 0.6B Q8_0 and a Qwen3 1.7B Q8_0 reference on
the local desktop: 240 cases per arm, 1,200 raw records. It exposed a serious
interface failure: tool arms emitted error objects on every case and never called
the core. Correct outcomes were A 0/240, B 8/240, C 10/240, D 10/240, E 6/240.
The few correct tool-arm outcomes are preserved errors, not recovered numeric
capability. A positive arithmetic CRR from these tiny error-only counts must not
be promoted as a useful capability upgrade. This is a prompt/surface failure to
fix, with the complete original run retained for comparison.

The second development run uses shorter request-translation prompts and shorter
GBNF rule namespaces (actual combined grammar 3,444 bytes, within the 4,096-byte
profile ceiling). Results: A 2/240, B 10/240, C 177/240, D 175/240, E 17/240.
C made 231 calls and D 229, versus zero in the first experiment. C matched 215
argument vectors but only 180 operation selections; sample/population method
selection is a remaining weakness. B still made no calls and the answer-only
A/E prompts are poor baselines. This is development-interface evidence with
those limitations, not a credible larger-model substitution claim. The raw CRR
11.5333 is retained mathematically, with its small 15/240 reference gap visible.
No held-out accuracy claim is made after tuning on this corpus.
