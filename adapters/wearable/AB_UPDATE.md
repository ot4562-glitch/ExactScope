# Wearable A/B activation reference v0.1

This document specifies the crash-consistent activation journal implemented by `exactscope_wearable_ab.[ch]`.

It solves one narrow product problem: after a complete candidate runtime/pack set has already been downloaded, authenticated, hashed, mounted, smoke-tested, and frozen, make the switch from slot A to slot B durable without ever requiring a partially written candidate to become active.

It does not download files, verify signatures, write pack contents, or own flash/filesystem APIs. Those remain product responsibilities.

## 1. Persistent objects

The product owns:

```text
slot A: complete runtime/pack-set image
slot B: complete runtime/pack-set image
journal copy 0: 96 bytes
journal copy 1: 96 bytes
```

The two journal copies MUST reside in storage such that writing one does not overwrite or erase the other. A platform using erase-block flash must place/abstract them accordingly.

## 2. Canonical 96-byte journal record

All multibyte integers are little-endian. The implementation serializes fields byte-by-byte and never persists a native C struct.

| Offset | Size | Field |
|---:|---:|---|
| 0 | 8 | magic `XSWAB01\0` |
| 8 | 2 | format version = 1 |
| 10 | 2 | record size = 96 |
| 12 | 8 | monotonically increasing generation |
| 20 | 1 | active slot, 0=A or 1=B |
| 21 | 1 | previous slot, opposite of active |
| 22 | 2 | flags; bit 0 = rollback available |
| 24 | 32 | SHA-256 digest supplied for active complete image/pack set |
| 56 | 32 | retained previous-slot digest; required when rollback flag is set |
| 88 | 4 | reserved zero |
| 92 | 4 | CRC-32/ISO-HDLC over bytes 0..91 |

CRC parameters are the standard reflected ISO-HDLC profile used by the implementation:

```text
polynomial (reflected): 0xEDB88320
initial value:          0xFFFFFFFF
reflect input/output:   yes
final xor:              0xFFFFFFFF
```

CRC detects torn/corrupted journal records. It is not an authenticity mechanism. Product signature/authentication MUST occur before activation.

## 3. Storage callback contract

`xsw_ab_storage_v1` exposes exactly three product callbacks:

```text
read_record(copy, out[96])
write_record(copy, bytes[96])
flush()
```

Required semantics:

- copy index is only 0 or 1;
- `write_record` may stage/cache the new bytes;
- `flush` is the durability barrier;
- after successful `flush`, a following `read_record` must observe the durable bytes;
- after power loss before a successful flush, staged data may disappear;
- reads return durable data only;
- callbacks must not make an incomplete write to one copy destroy the other copy.

After any storage callback error, the caller MUST discard its RAM decision state and invoke `xsw_ab_recover` before making another update decision.

## 4. Recovery rule

At boot/restart:

1. read both 96-byte copies;
2. independently verify magic/version/size/reserved fields/CRC/slot invariants/digest invariants;
3. if exactly one is valid, use it;
4. if both are valid with different generations, use the higher generation;
5. if both are valid with the same generation and identical content, either copy is equivalent;
6. if both are valid with the same generation but different content, fail `INTEGRITY_ERROR`;
7. if neither is valid, fail rather than guessing an active slot.

A newer torn record is therefore ignored when an older complete copy remains valid.

Generation wrap is not allowed. An attempted commit at `UINT64_MAX` returns `OVERFLOW`.

## 5. Factory bootstrap

`xsw_ab_bootstrap` is only for provisioning an uninitialized product.

Both journal copies must be blank, defined as entirely `0x00` or entirely `0xFF`.

Bootstrap refuses:

- an existing valid journal;
- nonblank invalid/corrupt metadata;
- zero active digest;
- invalid slot.

It writes generation 1 to copy 0, flushes, rereads, verifies CRC/content, and only then returns a usable RAM state.

A field-return/repair flow must not use bootstrap to hide corrupted production metadata without an explicit product recovery policy.

## 6. Candidate staging rule

`xsw_ab_candidate_slot` returns the inactive slot only when the current generation has no retained rollback obligation.

If `rollback_available=1`, candidate staging is blocked. The product must first either:

- `xsw_ab_accept_active`, ending the rollback-retention window; or
- `xsw_ab_rollback`, switching back to the previous known-good slot.

This prevents an updater from overwriting the only retained rollback image while the new release is still provisional.

## 7. Required preconditions before activation

The function name is intentionally `xsw_ab_commit_validated_candidate`.

Before calling it, the product MUST have completed all of:

1. write complete candidate bytes into the inactive slot;
2. force candidate content itself durable according to product storage semantics;
3. verify publisher authenticity/signature using the product trust root;
4. compute and verify the complete candidate digest;
5. create a fresh ExactScope host/context;
6. mount the complete dynamic pack set or load the fused candidate runtime;
7. allow ExactScope to validate CRC/format/limits/programs/collisions;
8. run the fixed candidate smoke corpus;
9. freeze the candidate registry;
10. obtain the digest passed to the A/B activation layer.

The A/B journal layer treats `candidate_digest` as a host-authenticated identity. It does not implement cryptography beyond journal CRC.

## 8. Atomic activation algorithm

Starting from durable generation `g` in selected metadata copy `r`:

```text
candidate slot = 1 - active slot
new generation = g + 1
new active = candidate
new previous = old active
rollback_available = 1
new active digest = validated candidate digest
new previous digest = old active digest
metadata target copy = 1 - r
```

Commit ordering is exactly:

```text
encode canonical 96-byte record
    -> write_record(non-current copy)
    -> flush()
    -> read_record(same copy)
    -> verify format + CRC + exact semantic equality
    -> update in-RAM state
```

The current durable metadata copy is never overwritten during that transaction.

If write, flush, reread, CRC, or semantic verification fails, the function does not update the caller's RAM state.

## 9. Stale decision prevention

Before every activation/accept/rollback commit, the implementation rereads durable metadata with `xsw_ab_recover` and compares it with the caller's RAM state.

If another actor or a prior uncertain commit advanced generation/state, the operation fails `INVALID_REQUEST`.

The caller must recover and decide again from the newest durable state.

This prevents an old in-memory updater decision from overwriting a newer durable activation.

## 10. Rollback

A successful candidate activation preserves:

```text
active = new candidate
previous = old known-good
rollback_available = 1
```

`xsw_ab_rollback` creates another generation:

```text
active = previous
previous = failed/newer active
rollback_available = 0
```

The rollback is itself written to the non-current journal copy, flushed, reread, and verified.

No compilation or pack rewriting is required.

## 11. Accepting a release

After the product-defined soak/health window succeeds, call `xsw_ab_accept_active`.

This creates another durable generation with the same active slot but clears `rollback_available`.

Only after this commit may the updater reuse/overwrite the inactive old slot for a future candidate.

The old digest may remain in the journal record for audit/diagnostic continuity, but the flag is authoritative for overwrite permission.

## 12. Power-loss expectations

The CI memory-backed test exercises at least these cases:

1. before candidate write;
2. during candidate content write;
3. after candidate write, before authentication;
4. after authentication, before ExactScope validation;
5. after validation, before activation metadata write;
6. journal `write_record` failure;
7. durability `flush` failure;
8. torn new journal record that reaches durable storage;
9. successful activation followed by immediate crash/recovery.

It additionally verifies rollback, release acceptance, stale RAM-state rejection, and recovery when an older metadata copy is corrupt.

CI demonstrates the reference algorithm. Product qualification still requires the same failure injection on the real storage/filesystem/flash implementation because actual durability semantics are device-specific.

## 13. Product storage mapping examples

### POSIX-like filesystem

A product adaptation might map each 96-byte copy to a separate preallocated metadata object and implement `flush` with the platform's durable-write primitive. The product must also ensure directory/rename semantics for any surrounding A/B slot pointer are not weaker than this journal contract.

### Raw flash

Use independent erase/program locations for copies 0 and 1. Do not place both copies in one erase unit if updating one requires erasing the other. Respect device program granularity and bad-block/ECC policy below the callback boundary.

### Key-value/NVRAM service

Use two distinct keys/records and a synchronous durability barrier if the service exposes one. If the service cannot guarantee the callback semantics above, it is not a conforming backend for this reference.

## 14. Security boundary

The A/B journal protects **crash consistency and accidental corruption**, not malicious replacement.

The product must separately enforce:

- authenticated update channel;
- publisher signature/trust policy;
- anti-rollback policy if required by the product;
- protected storage permissions;
- digest binding between candidate bytes and journal identity.

ExactScope deliberately does not embed vendor keys or a network updater.

## 15. Integration with `exactscope_wearable_ref`

For `native-dynamic-exact`, the expected sequence is:

```text
recover A/B journal
select active complete pack set
initialize xsw_ref_host
mount active packs
finish_install / freeze
serve

update arrives
candidate_slot()
product writes + authenticates inactive complete set
initialize separate candidate xsw_ref_host
mount candidate complete set
run smoke corpus
finish_install / freeze
commit_validated_candidate()
recreate/switch serving context according to product process model
retain previous slot until accept_active() or rollback()
```

Do not mutate the serving frozen context in place as the product's atomic update mechanism. Build/validate a complete candidate context and switch product ownership only after activation metadata is durable.

## 16. Release evidence

The physical qualification report should record:

- journal backend/storage technology;
- exact callback implementation version;
- durability primitive used by `flush`;
- number and locations of injected crashes;
- recovered generation/active slot for every case;
- candidate and active digests;
- any filesystem/flash-specific deviations.

A successful host-memory CI test is necessary but not sufficient for a `qualified` real-device claim.
