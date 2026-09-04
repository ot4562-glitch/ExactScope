# Public `xs_calc` evidence

These JSON files are checked-in evidence, not general model-accuracy claims:

- `finqa-xs-calc-oracle.json`: FinQA test gold programs lowered to bounded plans, executed by ExactScope, and compared with explicit `qa.answer` values.
- `tatqa-xs-calc-oracle.json`: TAT-QA dev arithmetic derivations lowered to bounded plans, executed by ExactScope, and compared exactly with explicit answers.
- `xs-calc-llama-b10797.json`: five-case constrained-generation integration smoke for the three RC reference GGUF files.

The public dataset inputs are pinned as follows:

- FinQA test: upstream `main.zip`, archive SHA-256 `b6e8aadb9cdebe9be6574dfbdcba835a90f0a71664a417118d1d4a2671339a6f`; `dataset/test.json` SHA-256 `831dbfb2e785dbc227f895ce3f24046433467aec67b09db2bd6ac7692a8a30dc`.
- TAT-QA dev: upstream commit `870accc41953dcde885aabeb963d94aabdc0fbc3`; `dataset_raw/tatqa_dataset_dev.json` SHA-256 `6c3660345bf155b44bb3b55e63a4355716521028f291263d47c66667335f0144`.

Only rows whose runtime result exactly matches the explicit dataset answer form the oracle/structural validation subset. Dataset-specific implicit percentage scaling and rounding are not guessed. MathQA `annotated_formula` is not used.

To reproduce an oracle report after obtaining the upstream dataset under its own license and building `exactscope-core`:

```text
cargo build --release -p exactscope-conformance --bin exactscope-core
python benchmarks/public_xs_calc_oracle.py finqa --source <FinQA-test.json> --core target/release/exactscope-core --output finqa.json
python benchmarks/public_xs_calc_oracle.py tatqa --source <tatqa-dev.json> --core target/release/exactscope-core --output tatqa.json
```

The FinQA parser uses a parenthesis-depth-aware top-level splitter. It does not use `program.split(", ")`, which corrupts function arguments.
