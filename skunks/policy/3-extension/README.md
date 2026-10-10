# Experiment 3: a miner-signalled flag

## Part A: prove an existing block-extension key in script

**Off-chain control first** (`merkle.py`, plan S12). The root was rebuilt from `/blocks/{id}`'s extension fields:
- leaf `0x02 ++ key ++ value`, hashed as `blake2b256(0x00 ++ leaf)`;
- node `blake2b256(0x01 ++ left ++ right)`;
- an odd node paired with an empty one (hash = empty string);
- leaves in insertion order.

It matched the header's `extensionHash` on every block read, with **zero changes** to the reconstruction:
- 5 blocks in the final run, with 3, 4 and 16 leaves (odd and even);
- 12 more in an earlier check, with 4, 5 and 17 leaves.

Flipping one byte of one leaf gave a mismatch every time (`results.json` `control`).

**Contracts.**
- **`ExtFlag.es`** (233 B tree, 309 B box): a flag box in `QDay.es`'s layout.
  - false → true needs no key: context variable 2 holds a leaf whose key bytes are `KEY` (`0100`, the first interlink
    field, present in every non-genesis block). Variable 3 holds the path, `Coll[(Coll[Byte], Boolean)]`, which must
    fold to `CONTEXT.headers(i).extensionRoot` for the `i` in variable 4. The script has **no range check on `i`**.
  - Unchanged refresh by anyone; never back.
- **`ExtFlagAny.es`** (230 B; added, see below): the same, but the root may match *any* header in view
  (`CONTEXT.headers.exists`). It has no variable 4.
- **`Depth.es`**: `sigmaProp(CONTEXT.headers.size == N)`, compiled for N = 9 and N = 10.

### Devnet result (2026-10-10): every row as expected

`results.json`; log `run.log`. An earlier run stalled at case 6 (`run1-stalled.log`, below).

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | spend the `Depth` box with N = 9 | ACCEPT (checked) | ACCEPT | | |
| 2 | spend the `Depth` box with N = 10 | REFUSE | REFUSE (`Success((false,5))`) | node-check | 1 |
| 3 | flip with the leaf's value byte changed | REFUSE | REFUSE | node-check | 6 |
| 4 | flip with a proof for a different key present in the block (`0101`) | REFUSE | REFUSE | node-check | 6 |
| 5 | flip with a valid proof against H−9 (`i = 8`, block 174 at fullHeight 182) | ACCEPT (checked) | ACCEPT | | |
| 6 | flip with a valid proof against H−1 (`i = 0`) | ACCEPT (mined) | ACCEPT, included at 183; cost 12,647 (mempool) | | |
| 7 | case 5's proof one block later (`i = 9`), second flag box | EVAL-ERROR | EVAL-ERROR: `Failure(java.lang.ArrayIndexOutOfBoundsException: Index 9 out of bounds for length 9)` | EVAL-ERROR | 5 |
| 8 | refresh the flipped box unchanged, no key | ACCEPT | ACCEPT | | |
| 9 | true → false | REFUSE | REFUSE | node-check | 8 |
| 10 | `ExtFlagAny`: flip with a proof against block 183, submitted at fullHeight 187 | ACCEPT (mined) | ACCEPT, included at 188 (the proof 5 blocks old); cost 12,868 | | |
| 11 | `ExtFlagAny`: the same flip, leaf value byte changed | REFUSE | REFUSE | node-check | 10 |

**The two limits, as measured:**
- **9 headers.** Rows 1 and 2 show `CONTEXT.headers.size` is 9 in the mempool context of 6.0.7. Rows 5 and 7 show
  that index 8 is the deepest that works and that index 9 throws.
- **Presence only.** Row 4 proves a different key is present. It is not an absence proof, and none exists: the
  leaves are unsorted.

**Cost.** One flip costs 12,647 with 4 leaves (2 path elements) and 12,868 for `ExtFlagAny` over 9 headers. That is
the same order as any one-input transaction on this devnet (preflight's wallet payment: 17,530). The Merkle check
is negligible, as `evidence/ergo-capabilities.md` §9 estimated [it was UNVERIFIED there; now measured].

### A finding the plan did not anticipate: a fixed `i` gives a one-block window

The first run (`run1-stalled.log`) submitted case 6 and waited forever. The node's check had accepted it, but it was
never mined, and the mempool dropped it:
- `headers(i)` is the block at `HEIGHT − 1 − i`. A proof against one particular block therefore satisfies the script
  at **exactly one height**.
- If the next block does not include the transaction, it is invalid from then on.

On the rerun, case 6 resubmits with a fresh proof until mined, and every attempt is recorded. It was mined on the
first attempt.

`ExtFlagAny.es` is the remedy: match the root against any header in view, and the flip has a **9-block window**
(row 10 was mined with a proof 5 blocks old). For a mainnet flag, use the `exists` form. The fixed-`i` form is only
useful for measuring depth.

## Part B: a custom key (RULING R2 default: build within a 60-minute box)

**Read-only findings at `v6.0.7`** (tag `3a6b00d3`, fetched from upstream into `~/bin/ergo-2554`, since the local
clone lacked it, preflight S15):
- `CandidateGenerator.scala:631-669` builds the extension from parameters, interlinks and validation settings only
  (`newParams.toExtensionCandidate ++ interlinksExtension ++ newValidationSettings.toExtensionCandidate` at an epoch
  start; `interlinksExtension` otherwise).
- `application.conf` and `MiningApiRoute.scala` have no setting or route that adds a field.
- **So the stock miner cannot add a custom key.** A miner that does is a node patch, or an external miner that
  builds its own candidates.

**The box.**
- Worktree `~/scratch/ergo-6.0.7-policy` created 13:15:13Z (`partB-t0.txt`).
- Patch (`partB-patch.diff`): one field appended at the candidate's construction (`CandidateGenerator.scala:724`):
  `extensionCandidate ++ ExtensionCandidate(Seq(Array(0xF0, 0x01) -> "policy"))`.
- The first `sbt assembly` died in 4 s: the sandbox denies `/run/user/1000` for sbt's server socket. It was rerun
  with `XDG_RUNTIME_DIR` in scratch and `-Dsbt.server.autostart=false`.
- The jar was built at 13:16:58Z with JDK 8 (the tag's CI uses `adopt@1.8`): **1 min 45 s** from the first timestamp,
  57 s of sbt.

**Relay and proof**, `partB.py` → `partB.json`, on a second devnet `policy-miner`:
- A ran the patched jar and mined; B ran stock 6.0.7 and did not mine. REST on 9183 and 9184.
- **(a) A stock node accepts and relays blocks with an unknown extension key.**
  - After 40 blocks, B's block at height 20 has A's id (`1e6df5a4…`).
  - B holds the field `f001 = "policy"` in that block, and B was at height 38 with one peer.
  - This settles the [UNVERIFIED] relay question in `evidence/ergo-capabilities.md` §9.4 *for 6.0.7 peers*. Other
    implementations were not tested.
- **(b) `ExtFlag.es` with `KEY = F001` accepts a proof of the custom field.**
  - B1 was mined (leaf `02f001706f6c696379`, included at 43, cost 12,666).
  - B2 refused the same proof with the value byte flipped (node-check).

`policy-miner` is down. Peeryard's branch is untouched (`soft-partition-split`), and `~/bin/ergo-node` is untouched.

## What a custom-key miner flag would need on mainnet (from these results)

- **Miners running a patched node, or an external candidate builder, that writes the key.** Nothing else in the node
  changes: stock peers relay the blocks (B accepted them).
- **A flag box in the `exists` form, flipped by anyone within 9 blocks of a signalling block.** One block suffices,
  since presence is all that can be proven.

  A threshold ("k of the last 9 blocks carry the key") is expressible with the same fold over `headers`, one proof per
  block, but was not built. What is missing is any way to prove *absence*.
- **Key prefixes 0x00, 0x01 and 0x02 are reserved.** `0xF0` was used here. No allocation for policy keys exists.
