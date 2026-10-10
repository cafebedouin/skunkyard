I couldn't save this to a file because the Write tool is disabled in this session, so the full document is below.

# Derivation seat: "template hash" on the node vs the explorer

**Verdict: file with fixes.** The core claim holds in the code. The node hashes `tree.template` with Blake2b256, the explorer hashes it with SHA-256, and each side's docs name its own function. The repro output agrees: each hash finds 22 boxes on its own service and none on the other. But the draft has these problems:
- It calls the explorer's fallback a defect when the node has the same fallback.
- It misstates when the explorer's fallback runs.
- The explorer "API docs" it quotes describe request-body fields, not the route it names.
- The repro ran against a different node version than the source the draft cites, and its output includes a line the script cannot print.
- It leaves out the strongest evidence of intent: #2218 itself asks for blake2b256.

Excerpt files are cited by their own line numbers, with the real line in parentheses where it helps.

---

## Part A (from the evidence only, written before opening the draft)

### A1. What each side hashes

**Node:** the function is `IndexedContractTemplateSerializer.hashTreeTemplate` (`node/IndexedContractTemplate.scala:55-65`).
- **Normal case:** `VersionContext.withVersions(3, 3) { bytesToId(Algos.hash(tree.template)) }` (`:57-58`).
- **Fallback:** if anything goes wrong (`Throwable`), it uses `bytesToId(Algos.hash(tree.bytes))`. The code comment calls this a "fake template hash" (`:60-63`).
- **What `Algos.hash` is:**
  - `object Algos extends ErgoAlgos` (`node/Algos-ergo-core.scala:11`) and does not override `hash`.
  - `ErgoAlgos` sets `val hash: HF = Blake2b256` (`node/ErgoAlgos.scala:11-13`).
  - So the node uses **Blake2b-256**: 32 bytes, turned into hex by `bytesToId`.
- **Docs:** OpenAPI says "blake2b256 hash of an ErgoTree template encoded in base 16" (`openapi.yaml…:19, :71`, i.e. lines 6838 and 6890).
- The address index uses the same function: `hashErgoTree = Algos.hash(tree.bytes)` (`IndexedErgoAddress…:10`, i.e. line 114).

**Explorer:** the function is `sigmaWrappers.deriveErgoTreeTemplateHash` (`explorer/sigma.scala:48-55`).
- **Step 1:** it deserializes the tree with `deserializeErgoTree`, under `withVersions(V6SoftForkVersion, V6SoftForkVersion)` (`:24, :28-31`).
- **Step 2:** `Try(Sha256.hash(tree.template)).getOrElse(Sha256.hash(rawBytes))` (`:52`). Here `rawBytes` is the decoded hex input (`:51`) and `Sha256` is `scorex.crypto.hash.Sha256` (`:9`). So the explorer uses **SHA-256**.
- **The fallback is narrower than "tree does not parse":**
  - It only runs if deserializing worked and `.template` then threw.
  - If deserializing fails, the call raises an error (`:30`) and no hash is produced at all.
  - The backfill migration calls `.get` on the result (`RegistersAndConstantsMigration…:11`, i.e. line 85), so the migration would throw on such a tree.
  - A minor difference: `Try` only catches non-fatal errors, while the node catches every `Throwable`.
- **Docs:**
  - The text "SHA-256 hash of ErgoTree template this box script should have" sits on the `BoxQuery` and `BoxAssetsQuery` request-body fields (`BoxQuery.scala:37`, `BoxAssetsQuery.scala:19`).
  - The `byErgoTreeTemplateHash` route definitions name no hash function. They say only "a hash of the given ErgoTreeTemplate" (`BoxesEndpointDefs…:21`) or nothing (`:61-71`).

### A2. Are the bytes the same? Other possible differences

- **Both call `tree.template`** (node `:58`, explorer `:52`). How sigma defines `ErgoTree.template` is **not in the evidence** [UNVERIFIED]. So we can't check here that "template" means the expression bytes without the header, size field and constants.
- **VersionContext:** the node passes a literal `(3, 3)`. The explorer passes `V6SoftForkVersion`, and whether that equals 3 is [UNVERIFIED].
- **Sigma library versions:** the node (6.0.7) uses sigmastate v6.0.6. The explorer's sigma version isn't in the evidence [UNVERIFIED], so a version difference in how `template` behaves can't be ruled out.
- **How the tree is read:**
  - The node hashes the tree already attached to the box. The explorer deserializes it again from hex.
  - Some trees deserialize as "unparsed" (soft-fork). For those, both sides fall back.
  - The node then hashes `tree.bytes` and the explorer hashes the raw input. These match only if `tree.bytes` keeps the original bytes [UNVERIFIED].
- **Header:** if `template` leaves out the header (unverified), then trees that differ only in header version or size flag get the same template hash. That is true on both sides, so it doesn't cause a mismatch between them.
- **Trees without segregated constants:**
  - #2218 proposed skipping them (`ergo-2218.md:14`), and a later comment says the skip was implemented (`:29`).
  - But `hashTreeTemplate` has no skip, and the code that calls it isn't in the excerpt. The `ExtraIndexer` excerpt shows only `findAndUpdateTemplate` (`:18-39`). So whether the node skips them is **CANNOT CHECK**.
  - The explorer doesn't skip them. If the node does, the two services would also disagree on these trees, whatever the hash function.
- **Fallbacks differ:** when the template can't be computed, both sides hash the whole tree, with different functions. A tree that fails deserialization gets a hash on the node but none on the explorer.
- **Possible key collision on the node (an extension, unverified):**
  - The node's fallback key `Blake2b(tree.bytes)` is the same value as the address index's `hashErgoTree(tree)`.
  - Templates are looked up by the raw `id` (`ExtraIndexer…:26`), while tokens go through `uniqueId` (`:7`).
  - If addresses are also stored under that raw hash (not shown in the excerpt), the template entry and address entry for an unparseable tree would share a key.

### A3. Is the repro sound?

**How it extracts the template** (`repro.py:25-38`): it is parsed by hand and written for this one tree.
- The header byte `0x10` means constants are segregated and there's no size field. The constant count is a VLQ.
- Constants `0x04`/`0x05` (Int/Long) are followed by a zigzag VLQ value. `0x0e` (Coll[Byte]) is a VLQ length followed by the bytes.
- The EIP-31 tree is `10 06 | 04 00 | 0e 20 <32 bytes> | 04 00 | 04 00 | 05 00 | 05 00 | d803…`.
- The parser reads exactly those six constants and returns `d803…`, which is correct for this tree.
- It matches sigma's `template` only if the unverified definition in A2 holds. The results back it up: each service found boxes under the hash computed for it. A wrong extraction would have found zero on both.

**Hash functions:** Python's `sha256` and `blake2b(digest_size=32)` match the services' `Sha256` and `Blake2b256`.

**What the output shows** (`output.txt:1-4`):

| Hash | Explorer | Node |
|---|---|---|
| SHA-256 | 22 | 0 |
| Blake2b | 0 | 22 |

- The node's 22 is a full count, because it is below `limit=100`.
- The node returns an empty list for unknown hashes rather than a 404 (`BlockchainApiRoute…:44-46`). So 0 means "no such hash", not an error.

**What it doesn't show:**
1. That the two sets of 22 are the same boxes. Only counts are compared, not box ids.
2. That these are SigUSD boxes. The template doesn't depend on the token, so they are Babel boxes for every token.
3. How fallback, non-segregated, or v1+ trees behave.
4. That the cited source matches what was tested. The node queried was 6.1.2, but the source in the evidence is 6.0.7, and the deployed explorer build is unknown.

**Integrity problem:** `output.txt:5` ("node 6.1.2 mainnet 1891228") **cannot come from `repro.py`**. The script only prints at lines 43, 44 and 50. Either the line was added by hand or a different script was run.

### A4. Standards and intent

- **EIP-5** defines how a template is serialized (`eip-0005.md:46-67, 187-197`). It expects the template bytes to be "obtained for hashing" (`:88-90`) but **names no hash function**.
- **EIP-31** gives the Babel template with a `{tokenId}` gap and no hash.
- **ergo-scala-compiler#11** says "Hash of: serialized contract template" with no function named (`:9-10`). greenhat replies that it belongs in sigma as `ErgoTree.templateId` (`:14`). Whether that was ever added is CANNOT CHECK.
- **The node's intent is explicit.** #2218 says "`templateHash` is a `blake2b256` hash of the box's `ergoTree.template` encoded as a `base16` string" (`ergo-2218.md:11`), with Babel fees as the example (`:6`). #2219 closes it (`ergo-2219.md:3`).
- Nothing in the threads mentions the explorer's existing SHA-256 field.

### A5. Which is correct, and what changing either side costs

- **By standard:** neither is correct, because no standard exists. Each side matches its own docs.
- **By consistency:** Blake2b matches the node's general hash function and its other index keys. The evidence supports only that much, not the draft's wider claim about "all Ergo ids".
- **By who came first:** the explorer field probably predates June 2025, since it needed a backfill migration. But no date is in the evidence, so this is CANNOT CHECK.
- **Switching the node to SHA-256:**
  - Templates are stored by their hash (`IndexedContractTemplate.scala:21-22, 73`), so the whole extra index would need rebuilding.
  - Clients using the documented blake2b values since 2025-06 would break.
  - It would reverse the choice #2218 made on purpose.
- **Switching the explorer to Blake2b:**
  - Every stored output would need its hash recomputed, like the existing migration did.
  - Clients that store or hard-code hashes would break silently: same route, but old hashes would return 0.
- **Cheapest fix:** document the difference on both sides, and optionally add a separate Blake2b field or route to the explorer. A canonical hash in sigma would settle it for new code without breaking anyone.

---

## Part B: the draft's claims

| # | Claim (draft line) | Status | Evidence / note |
|---|---|---|---|
| 1 | Both hash "the ErgoTree with its segregated constants removed" (3-4) | **Partly confirmed** | Both call `tree.template` (`IndexedContractTemplate.scala:58`, `sigma.scala:52`). What `template` means isn't in the evidence [UNVERIFIED], and the description doesn't mention that the header is also left out. |
| 2 | Node: `bytesToId(Algos.hash(tree.template))` is BLAKE2b-256, at `:58` (6) | **CONFIRMED** | `:58`, `Algos-ergo-core.scala:11`, `ErgoAlgos.scala:13`. The draft misses `withVersions(3,3)` (`:57`) and the node's own fallback (`:60-63`). |
| 3 | OpenAPI says "blake2b256 hash of an ErgoTree template"; route `/blockchain/box/byTemplateHash/{hash}` (6-7) | **CONFIRMED** | `openapi…:9, :19`. The unspent route is at `:61, :71`. |
| 4 | Added in #2219 for #2218 (7) | **CONFIRMED** | `ergo-2219.md:1-3` |
| 5 | Explorer uses `Sha256.hash(tree.template)`, at `sigma.scala:52` (8-9) | **CONFIRMED** | `sigma.scala:9, :52`. The repo path `modules/explorer-core/…` is CANNOT CHECK. |
| 6 | Explorer falls back "when the tree does not parse" (8) | **WRONG** | The fallback only runs when `.template` fails after a successful deserialize. A failed deserialize raises an error (`sigma.scala:30`), and the migration's `.get` throws (`Migration…:11`). |
| 7 | Explorer API docs say "SHA-256 hash of ErgoTree template" (9-10) | **CONFIRMED, wrong source** | The text is on the request-body fields `BoxQuery.scala:37` and `BoxAssetsQuery.scala:19`. The `byErgoTreeTemplateHash` routes name no function (`BoxesEndpointDefs…:21, :61-71`). |
| 8 | Explorer route `/api/v1/boxes/byErgoTreeTemplateHash/{hash}` (10) | **CANNOT CHECK (prefix)** | The suffix is confirmed at `BoxesEndpointDefs…:63`. `PathPrefix` isn't in the excerpt; `repro.py:45` uses `/api/v1/boxes/`. |
| 9 | Neither API mentions the other (12) | **CANNOT CHECK fully** | True of every excerpt provided, but these are excerpts, not the full specs. |
| 10 | Repro table: 22/0 and 0/22 (17-20) | **CONFIRMED** | `output.txt:1-4`. Not disclosed: only counts compared; node 6.1.2 vs cited 6.0.7 source; line 5 not printed by the script; template parsed by hand. |
| 11 | Babel fees are "the example #2218 was written for" (14) | **CONFIRMED** | `ergo-2218.md:6` |
| 12 | Repro is "for SigUSD" (14-15) | **Misleading** | The template doesn't depend on the token, so the 22 are Babel boxes for all tokens. Saying so shows the feature working as designed. |
| 13 | Lithos client, and "we found it when a job…" (22-24) | **CANNOT CHECK** | Not in the evidence. |
| 14 | "The explorer's fallback also puts two kinds of value in one field" (24-25) | **One-sided** | The node does the same thing: it stores a "fake template hash" of the whole tree (`IndexedContractTemplate.scala:63`). |
| 15 | EIP-5 defines serialization but no hash (27) | **CONFIRMED** | `eip-0005.md:46-67`. It does expect the template to be hashed (`:88-90`), which is worth citing. |
| 16 | The #11 reply put it in sigma as `ErgoTree.templateId` (27-28) | **CONFIRMED** | `ergo-scala-compiler-11.md:14` |
| 17 | "That was never added" (28) | **CANNOT CHECK** | No sigma source in the evidence. |
| 18 | Every other Ergo id (box, tx, token, P2SH) is BLAKE2b-256 (31-32) | **CANNOT CHECK** | The evidence only shows `Algos.hash` and the address-index hash. From memory, P2SH uses a shortened Blake2b-256 digest, so "is BLAKE2b-256" is loose there. |
| 19 | The node already uses Blake2b (32) | **CONFIRMED** | Same evidence as #2. |
| 20 | SHA-256 has been used "for years" (34) | **CANNOT CHECK** | No dates for the explorer field in the evidence. |

### What the draft misses
1. **#2218 explicitly specifies blake2b256** (`ergo-2218.md:11`). This is the best evidence of the node's intent, and the draft doesn't cite it.
2. **The node has the same kind of fallback** (`:60-63`, catching every `Throwable`). Claim 14 should either treat both sides the same or be dropped.
3. **The open question about skipping trees without segregated constants.** It was proposed and said to be done, but the skip isn't in `hashTreeTemplate`. If the node skips them and the explorer doesn't, the services disagree on those trees whatever the hash function.
4. **Version and context caveats:** `withVersions(3,3)` vs `V6SoftForkVersion`; the explorer's sigma version is unknown; the repro node is 6.1.2 but the cited source is 6.0.7.
5. **Repro fixes:**
   - Compare box ids, not just counts.
   - Either make the script print the node version line, or remove that line from `output.txt`.
   - Say that the template is parsed by hand for this one tree.
6. **The cost of the node-side change:** switching the node to SHA-256 would mean rebuilding its whole index, because templates are stored by their hash (`IndexedContractTemplate.scala:21-22`). That is a stronger reason for proposal 1 than "every other id is Blake2b".
7. **Optional, unverified:** the node's fallback key may be the same as the address index's key for the same tree. Mention it only if checking the full `IndexedErgoAddress`/`ExtraIndexer` source confirms it.
