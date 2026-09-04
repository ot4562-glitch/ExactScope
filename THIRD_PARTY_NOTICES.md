# Third-party notices

ExactScope itself remains licensed under `MIT OR Apache-2.0` as described in `LICENSE-MIT` and `LICENSE-APACHE`.

## Rust development/build dependencies

The locked workspace uses the following crates from crates.io. The exact versions and checksums in `Cargo.lock` are authoritative.

- `itoa` — MIT OR Apache-2.0
- `memchr` — Unlicense OR MIT
- `proc-macro2` — MIT OR Apache-2.0
- `quote` — MIT OR Apache-2.0
- `serde`, `serde_core`, and `serde_derive` — MIT OR Apache-2.0
- `serde_json` — MIT OR Apache-2.0
- `syn` — MIT OR Apache-2.0
- `unicode-ident` — Unicode-3.0
- `zmij` — MIT

These crates are used by host-side pack compilation/tooling. The minimum deterministic kernel and no-import Wasm path do not gain a network or service dependency from them.

## Evaluation datasets

Public oracle/structural result summaries were derived locally from:

- FinQA, copyright 2021 Zhiyu Chen, MIT License.
- TAT-QA, copyright 2021 Fengbin Zhu, MIT License.

The datasets are not redistributed in ExactScope release archives. Their names, row identifiers, arithmetic derivations, and aggregate results are used only to make the validation method reproducible and auditable.

## Model/runtime evaluation

The checked-in llama.cpp result summary identifies the locally evaluated runtime build and GGUF filenames. ExactScope does not redistribute llama.cpp or model weights. Users must obtain them under their respective upstream terms. Qwen and Llama names are used only to identify benchmark inputs; no compatibility, endorsement, or certification is implied.
