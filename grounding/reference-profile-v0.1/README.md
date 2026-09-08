# Offline exact/lexical reference profile v0.1

P1 configuration freeze only; not a provider runtime, benchmark preregistration,
model result or readiness claim. The source is a synthetic help-desk directory.
The provider algorithm is a bound declarative implementation specification;
P2 must bind executable provider bytes before claiming runtime reproducibility.

`profile.json` is the root behavior identity. `manifest.json` binds every asset;
all paths resolve relative to this directory and must remain inside it. JSON
files are grounding-cjson-v0.1 bytes (no final newline); raw assets use exact
UTF-8 bytes and LF. SHA-256 is lowercase hex over those bytes. The manifest
excludes itself to avoid a digest cycle. Profile digest excludes external
fixtures/manifest; referenced assets bind all behavior transitively. The source
adapter config is additionally bound by the snapshot adapter_config_sha256.

Canonical JSON permits null, booleans, integers in +/-9007199254740991, Unicode
scalar strings, arrays and string-key objects. Reject duplicate keys, floats
(including exponent notation), NaN/infinities, BOM and lone surrogates. Preserve
Unicode without normalization. Sort object keys by UTF-16 code units; serialize
compact UTF-8 with JSON escaping and no slash escaping. Array order is semantic.
Raw numeric evidence uses the contract's typed scalar strings, not JSON floats.

Authority belongs to each TargetPlan/source binding, never a source-pack flag.
The directory is authoritative only for reference:desk; notes are supplemental
only for reference:desk-tip. Every binding is required; all-required-v1 has no
subset exception. `merge.json` fixes state precedence, coverage and ordering.
Opaque revisions are equality identifiers and never sortable freshness values.
`router.json`, preprocessing/ranking files and provider-algorithm.md define the
exact local scan/index algorithm. Router unknowns emit no targets. Deadlines
are measured host outcomes, not reproducible latency guarantees; replay must
retain typed timeout/cancellation decisions. No retries, network or rewrites.

Projection: validate frame and cross-file bindings before rendering. Install
projection-policy.txt verbatim as a higher-priority instruction message; place
projection-renderer.py output in a lower-priority data message. Keep the original
query separately. Template bytes are immutable; substitute groups_json once,
using canonical object-key order and UTF-8 target/item ordering. Preserve all
states/labels and evidence; omit frame qid/profile digest from model data.
Escape JSON controls/quotes/backslashes plus <, >, &, U+2028/U+2029. Never recursively
substitute evidence text. Evidence cannot assign authority or permissions.
Byte budgets include the full data block; host context must additionally reserve
the policy and original query. Tokenizer/token budgets are intentionally null;
there are no measured resource claims. Overflows fail before the one answer
call; never truncate evidence into none. No model is invoked by these assets.

`query.json`, routing-plan.json, *-outcome.json, frame.json and
projection-expected.txt are deterministic conformance fixtures only. The new
test file also constructs a synthetic preregistration schema fixture in memory;
it is not an actual registered benchmark or a bound model identity.
