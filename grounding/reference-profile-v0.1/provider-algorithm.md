# exact-lexical-v1 (declarative implementation identity)

P1 freezes this algorithm; the provider runtime is P2 work. No model, embedding,
network, prototype fact-pack authority, or performance claim is involved.

1. Verify profile, scope, provider, bound source snapshot and index digests before
   accessing records. Invoke once per TargetPlan binding; only its source_ids and
   target_key may supply evidence. Revision strings are opaque equality tokens.
2. Normalize queries and aliases by replacing ASCII A-Z with a-z, extracting
   maximal [a-z0-9]+ runs, and joining runs with one ASCII space. No Unicode
   normalization, transliteration, stemming, locale folding or stop words.
3. The index contains one row per source record, sorted by UTF-8 bytes of
   (source_id, source_revision, item_id, target_key). Each row contains the sorted
   unique normalized aliases, including empty aliases (which never match).
4. Exact score is 1 if a nonempty normalized query equals any alias, else 0.
   Lexical score is the maximum cardinality of the intersection of distinct
   query tokens and alias tokens; empty intersections do not match. Match when
   exact score=1 or lexical score>=2. Sort descending exact score then lexical
   score, then ascending UTF-8 (source_id, source_revision, item_id, target_key).
   Keep all matches: rank never establishes authority or resolves disagreement.
5. Deduplicate identical (source_id, source_revision, item_id, target_key) only
   when canonical content bytes agree; differing bytes are an integrity error.
   Emit content_sha256 over canonical content, without aliases or ranking scores.
6. A complete scan with matches yields ok/complete=true; an empty complete scan
   yields none/complete=true/reason=null. Never truncate: more than 16 matches
   yields budget_exceeded/complete=false with no candidates. No access => denied;
   bad identity/index/content => error; deadline/cancellation => timeout. These
   failures have complete=false, empty candidates and a stable nonempty reason.
   Invocation identity echoes qid/profile digest/security scope/target/provider,
   attempt=1 and the exact sorted bound source snapshot digests.
