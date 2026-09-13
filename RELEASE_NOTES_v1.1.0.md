# ExactScope v1.1.0 — release notes

**Release scope.** ExactScope v1.1.0 is a **direction-setting software/architecture release**, not a blanket performance-upgrade, enterprise-qualification, or customer-economics claim. Its main purpose is to make the product boundary explicit: retain the proven Linux x86-64 native grounding C ABI/XSGI path as the stable core, and establish the qualification/policy/admission/finalization/drift architecture that future customer evidence can bind to. New v1.1 qualification, enterprise DocQA, Bridge, host-integration and conformance-demo surfaces are **experimental/reference** unless a narrower document explicitly states otherwise.

That distinction is deliberate. NQ/Hotpot development evidence remains positive on average, while the Kubernetes long-document proxy is negative and closes without a selected candidate. v1.1.0 therefore records a clearer technical direction and evidence discipline rather than claiming that every workload became faster or more accurate.

A normal `v1.1.0` tag was consequence-reviewed by GPT-6 Astra and judged defensible with this stability boundary. Enterprise/customer qualification is not required for the software tag, but remains unclaimed and is still required before customer-value, production-readiness, or economic-superiority statements.

## What v1.1 adds

v1.1 implements a reference semantic/qualification layer around a host-owned AI stack:

```text
Workload Contract + Host Capability Manifest + Semantic Policy
  -> Candidate Execution Policy
  -> separate Qualification Attestation
  -> Qualified Execution Profile
  -> admit -> host execution -> finalize
  -> Execution Receipt
  -> drift / requalification planning
```

The host still owns retrieval execution and authorization, model weights, tokenizer/chat template, inference, scheduling/batching, cache, constrained/speculative decoding, tools, fallback, deployment and rollback.

Implemented reference surfaces include:

- restricted workload and host-capability schemas;
- deterministic source-to-artifact policy lowering;
- immutable Candidate Execution Policy identity;
- separate Qualification Attestation bound to exact candidate/workload/host/evaluation identities;
- Qualified Execution Profile construction only from a validated candidate/attestation pair;
- request-bound admission receipts and mandatory finalization semantics;
- explicit stale/mismatch rejection and requalification planning;
- a fail-closed enterprise DocQA reference chain from preregistration through attestation/profile construction;
- a `CONFORMANCE_DEMO_ONLY` executable lifecycle/drift demonstration;
- machine-verifiable frozen public-development evidence;
- experimental runtime-bridge evidence across ORT GenAI, ExecuTorch and LiteRT-LM at individually documented evidence levels.

**Fail-closed scope:** admission/finalization assumes a trusted enforcing host boundary that reports the current behavior-affecting identities and does not bypass the guard. Digest binding establishes consistency with supplied identities; a valid profile/attestation does not independently prove host truthfulness, enterprise suitability, workload quality, production readiness, or economic advantage.

## Stability boundary

### Stable in v1.1.0

- Linux x86-64 native grounding static library;
- C ABI declared by the shipped public headers;
- deterministic XSGI bind/search/projection behavior within the declared native support scope;
- deterministic package verification/clean-room C11 integration required by the release gate.

### Experimental/reference in v1.1.0

- qualification/control-plane schemas and Python reference tooling;
- Candidate / Attestation / Qualified Profile workflow APIs outside the stable native C ABI;
- enterprise DocQA preregistration/readiness/scoring/analysis/decision/attestation workflow;
- `CONFORMANCE_DEMO_ONLY` examples;
- llama.cpp host-attached amplifier/reference integration beyond the stable C ABI guarantee;
- ExactScope Bridge and runtime-specific ORT/ExecuTorch/LiteRT adapters;
- public-development evidence-shaping configurations and research policies.

Package manifests label the host integration `experimental-reference` and the qualification architecture `source-reference-only`.

## Frozen public-development evidence

The final post-freeze 20-model A/G panel scheduled 20 model identities on NQ64 and Hotpot64. All 40 serving cells were attempted before scoring, with no quality retry, hidden repair, or post-panel policy reselection. The panel produced **32 scored cells / 8 protocol N/A**.

Here **A is the same model without attached evidence and G is that same model under the frozen ExactScope evidence/answer-contract path**.

- NQ64: mean F1 **12.44% -> 21.68% (+9.24 pp)** across 16/20 valid model pairs; improved/tied/regressed = **14 / 0 / 2**.
- Hotpot64 with host-owned LlamaIndex BM25 + frozen H1: mean F1 **11.63% -> 31.42% (+19.79 pp)** across 16/20 valid pairs; improved/tied/regressed = **15 / 0 / 1**.
- Equal-weight descriptive mean over 32 valid model-task pairs: **+14.52 pp**.

The Hotpot result is **model-only -> H1**, not ordinary-RAG -> H1. It does not establish H1's incremental superiority over ordinary RAG across models. Regressions and protocol-incompatible N/A identities remain visible in the tracked evidence snapshot.

Machine-verifiable evidence: `benchmarks/v1.1-final-public-evidence.json` with `python3 tools/verify_v11_public_evidence.py`.

## Direct stable-v1 -> v1.1 development checks

On separate same-Qwen untouched development cohorts:

- NQ: frozen v1.1 improved F1 by **+1.63 pp** versus stable v1 while reducing measured input/evidence bytes; local model service time was approximately **19% higher**.
- Hotpot: frozen v1.1 improved F1 by **+6.22 pp** versus stable v1; local model service time was approximately **21% higher**.

These are workload/model-specific development comparisons, not proof that v1.1 is universally superior to v1.0.

## Kubernetes Operations public proxy — negative result

To test transfer beyond the public NQ/Hotpot development regime, v1.1 froze a public enterprise-like long-document proxy using the official `kubernetes/website` repository at commit `ce98a43f24257385a9766003a6dadc95e962dc63`, host-owned LlamaIndex BM25 retrieval, and Qwen3.5 0.8B.

The only evidence-eligible initial development32 run (`three-arm-r4`) measured:

| Arm | Primary utility | Answerable F1 |
|---|---:|---:|
| B — model only | 11.36% | 16.53% |
| R — ordinary LlamaIndex RAG | **28.51%** | **41.46%** |
| G — `precision-context-v5` | 17.51% | 25.47% |

- **G − R = −10.99 pp** primary utility.
- paired bootstrap 95% interval: **−22.76 pp to −0.48 pp**.
- the prospectively declared quality margin was **−2 pp**, so G failed.
- G used 48.3% fewer evidence bytes and 37.3% fewer input tokens than R; those resource reductions are **not** an economic-advantage claim.

Exactly one bounded development diagnosis was prospectively allowed. Every candidate failed the frozen quality margin:

- C1 contiguous rank-1 window: **−4.42 pp vs R**;
- C2 contiguous rank-1/2 windows: **−7.06 pp**;
- RAW2560: **−4.80 pp**.

The frozen decision is **`selected_arm = null`**. Untouched validation32 was deliberately **not served**, and no second proxy-tuning round is allowed.

Invalidated preliminary run identities are retained rather than hidden: r1 source drift before scoring; r2 host startup failure before a model call; r3 score-serialization failure before score publication. Full account: `docs/V1_1_PUBLIC_PROXY_K8S_RESULT.md`.

This result means v1.1 **must not** be marketed as a qualified replacement for ordinary RAG on long operational documents.

## Runtime integration evidence

The Bridge evidence level differs by backend and is not a blanket compatibility promise:

- **ONNX Runtime GenAI 0.15.2:** real local generation smoke, grounded ExactScope delivery reaching ORT, strict post-validation, current C++ header compile.
- **ExecuTorch `IRunner`:** current upstream header compile + executable fake-runner contract smoke; **no real `.pte` + tokenizer compatibility claim yet**.
- **LiteRT-LM 0.17.0:** real Engine/Conversation execution with the official fixture, ExactScope ordinary-knowledge delivery, and a documented grounded-context capacity limitation of that fixture.

## Enterprise qualification status

The enterprise DocQA qualification infrastructure is implemented, but **no real owner-bound enterprise workload has been qualified**. No claim is made for:

- enterprise/customer qualification;
- production-ready customer behavior;
- demonstrated total-economic advantage;
- successful automatic cost optimization;
- universal v1.1 superiority over v1.0;
- general superiority over competent ordinary RAG;
- a proven new market category or moat.

Those are post-release evidence questions, not fabricated prerequisites for this software tag.

## Release gates

The `v1.1.0` tag is allowed only after the exact release commit satisfies all of the following:

- stable-v1 grounding regression and native C ABI compatibility checks pass against the release artifact;
- benchmark discovery and qualification/reference tests pass;
- public-evidence verifier and tamper/overclaim tests pass;
- design validator, security/publication audit and license checks pass;
- release-facing docs preserve the Kubernetes negative result and the stability/claim boundaries above;
- the selected Linux x86-64 native distributable builds and passes clean-room extraction/C11 verification;
- deterministic release manifest, SHA256 checksums, and applicable SBOM/license/NOTICE are complete;
- public package contains no secrets, private paths, or unsupported customer claims;
- GitHub CI/release checks pass on the exact commit to be tagged.

If a packaging/CI defect appears, only release mechanics may be fixed without reopening frozen benchmark policies or success criteria; all applicable gates are rerun and final artifacts/checksums regenerated.

## After v1.1.0

ExactScope research is no longer allowed to delay this release with another public tuning cycle. The next empirical value milestone is a real owner-bound workload or another independently justified deployment study. Until such evidence exists, the release remains an honest software/architecture milestone with a stable native grounding core and experimental/reference v1.1 control-plane surfaces.
