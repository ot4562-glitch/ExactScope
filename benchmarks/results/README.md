# Public `xs_calc` evidence

These JSON files are checked-in evidence, not general model-accuracy claims:

- `finqa-xs-calc-oracle.json`: FinQA test gold programs lowered to bounded plans, executed by ExactScope, and compared with explicit `qa.answer` values.
- `tatqa-xs-calc-oracle.json`: TAT-QA dev arithmetic derivations lowered to bounded plans, executed by ExactScope, and compared exactly with explicit answers.
- `xs-calc-llama-b10797.json`: five-case constrained-generation integration smoke for the three RC reference GGUF files.

Only rows whose runtime result exactly matches the explicit dataset answer form the oracle/structural validation subset. Dataset-specific implicit percentage scaling and rounding are not guessed. MathQA `annotated_formula` is not used.

To reproduce an oracle report after obtaining the upstream dataset under its own license and building `exactscope-core`:

```text
cargo build --release -p exactscope-conformance --bin exactscope-core
python benchmarks/public_xs_calc_oracle.py finqa --source <FinQA-test.json> --core target/release/exactscope-core --output finqa.json
python benchmarks/public_xs_calc_oracle.py tatqa --source <tatqa-dev.json> --core target/release/exactscope-core --output tatqa.json
```

The FinQA parser uses a parenthesis-depth-aware top-level splitter. It does not use `program.split(", ")`, which corrupts function arguments.
