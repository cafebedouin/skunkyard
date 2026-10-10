# Fidelity review: ISSUE-DRAFT.md

**Verdict: file it after fixes; it does not need a rewrite.** The main claim holds up. The node hashes `tree.template` with BLAKE2b-256 and the explorer hashes it with SHA-256. The reproduction shows the same 22 boxes under each service's own hash and none under the other's. There are four faults to fix before filing:
1. **The fallback criticism is one-sided.** The draft blames only the explorer for its whole-tree fallback, but the node does the same thing (`IndexedContractTemplate.scala:61-63`).
2. **The explorer quote is pinned to the wrong place.** The "SHA-256" text comes from the POST search-body schemas, not from the GET route the draft names.
3. **The reproduction table misleads.** Its explorer column names the wrong route, and it implies the 22 boxes are SigUSD boxes, when the template is the same for every token.
4. **The draft is missing what a maintainer needs to act:** the node version and height, and a copy-paste reproduction.

Several phrases are also stronger than the evidence supports (see B).

## Task A: statement-by-statement check

Excerpt line numbers are converted to source lines (an excerpt file's line 1 is its first source line).

| # | Statement in draft | Verdict | Evidence |
|---|---|---|---|
| 1 | Title: node uses BLAKE2b-256, explorer uses SHA-256 | CONFIRMED | `node/IndexedContractTemplate.scala:58`; `Algos-ergo-core.scala:11` (`Algos extends ErgoAlgos`); `ErgoAlgos.scala:13` (`hash = Blake2b256`); `explorer/sigma.scala:52` |
| 2 | Both offer "boxes by ErgoTree template hash" | CONFIRMED | `BlockchainApiRoute.scala:311,329`; `BoxesEndpointDefs.scala:122,129` |
| 3 | Both hash the same thing (`tree.template`) | CONFIRMED | `IndexedContractTemplate.scala:58`, `sigma.scala:52`; the matching 22/22 counts back it up (`repro/output.txt:3-4`) |
| 4 | "the ErgoTree with its segregated constants removed" | CONFIRMED (header and size field are also removed) | `ergo-2218.md:9`; `repro.py:4` |
| 5 | `bytesToId(Algos.hash(tree.template))` at `IndexedContractTemplate.scala:58` | CONFIRMED | `IndexedContractTemplate.scala:58` |
| 6 | OpenAPI says "blake2b256 hash of an ErgoTree template" | CONFIRMED (truncated: the full text continues "…encoded in base 16") | `openapi.yaml:6838`, `:6890` |
| 7 | Node route `/blockchain/box/byTemplateHash/{hash}` | CONFIRMED | `openapi.yaml:6828`; `BlockchainApiRoute.scala:311` |
| 8 | Added in #2219 for #2218 | CONFIRMED | `ergo-2219.md:1-3` ("Closes #2218"). Note #2218 is still OPEN (`ergo-2218.md:1,36`) |
| 9 | Explorer `Sha256.hash(tree.template)` at `sigma.scala:52` | CONFIRMED | `sigma.scala:52` |
| 10 | Explorer falls back "when the tree does not parse" | WRONG (imprecise) | The fallback runs only when `tree.template` throws *after* `deserializeErgoTree` has succeeded (`sigma.scala:49-52`). If deserialization itself fails, the error is raised and there is no fallback (`sigma.scala:30`) |
| 11 | Path `explorer-backend/modules/explorer-core/.../protocol/sigma.scala` | CANNOT CHECK | The package `org.ergoplatform.explorer.protocol` (`sigma.scala:1`) is consistent with it, but the module directory is not in the evidence |
| 12 | Explorer API docs say "SHA-256 hash of ErgoTree template" for `/api/v1/boxes/byErgoTreeTemplateHash/{hash}` | WRONG (misattributed) | The quote is the `ergoTreeTemplateHash` field description in the POST search bodies (`BoxQuery.scala:37`, `BoxAssetsQuery.scala:19`). The GET route (`BoxesEndpointDefs.scala:122`) has no description. The stream route (`:80`) says only "a hash of the given ErgoTreeTemplate" |
| 13 | `/api/v1/boxes/` prefix | CONFIRMED (by the live call, not by source) | `PathPrefix` is not in the excerpt; `repro.py:45` plus `output.txt:3` show the path answered |
| 14 | "nothing in either API says the other exists" | CANNOT CHECK | Only excerpts are present, so a statement about the whole API can't be proven by reading. See B1 |
| 15 | Reproduction on mainnet, 2026-10-09 | CONFIRMED | `README-SLICE.md:20`; `output.txt:5` |
| 16 | The tree is the EIP-31 Babel fee contract | CONFIRMED | `repro.py:10-13` matches `eip-0031-contract-template.md:5` |
| 17 | "the example #2218 was written for" | WRONG (overstated) | #2218 uses it "as an example" (`ergo-2218.md:6`) |
| 18 | "for SigUSD (`03faf2cb…bf04`)" | ID matches `repro.py:14`. That it is SigUSD: CANNOT CHECK (only a variable name says so) | The framing misleads: the template is the same for every token (`repro.py:5-6`), so the 22 boxes are all Babel boxes, not SigUSD ones |
| 19 | SHA-256 `4e83fa68…c465` | CONFIRMED | `output.txt:1` |
| 20 | BLAKE2b-256 `ad6fbaa2…5574` | CONFIRMED | `output.txt:2` |
| 21 | 22 / 0 and 0 / 22 boxes | CONFIRMED | `output.txt:3-4`. The explorer figure is the `total` field; the node figure is the list length with `limit=100` (`repro.py:48-50`), so it is complete |
| 22 | Table column header: explorer `byErgoTreeTemplateHash` | WRONG | The script queried `unspent/byErgoTreeTemplateHash` (`repro.py:45`). The node header `unspent/byTemplateHash` is correct (`repro.py:46`) |
| 23 | Tools: Babel fees, DEX orders, Lithos keyless jobs | Babel fees CONFIRMED (`eip-0031…:9`, `ergo-2218.md:6`). DEX orders and Lithos: CANNOT CHECK | — |
| 24 | "We found it when a job that worked against the explorer found nothing on a node" | CANNOT CHECK | There is no trace of it in the evidence. The reproduction is a demonstration built afterwards |
| 25 | The explorer's fallback puts two kinds of value in one field | CONFIRMED, but misleading because it leaves something out | `sigma.scala:52`. The node does the same with BLAKE2b-256 of `tree.bytes` (`IndexedContractTemplate.scala:61-63`) |
| 26 | EIP-5 defines the template serialization but no hash | CONFIRMED | `eip-0005.md:46-67`. It does foresee hashing the template bytes (`:88-90`), which supports the draft's case |
| 27 | ergo-scala-compiler#11 proposed a global template id | CONFIRMED | `ergo-scala-compiler-11.md:1-10` |
| 28 | The reply: it belongs in sigma as `ErgoTree.templateId` | CONFIRMED | `ergo-scala-compiler-11.md:14` (greenhat, the only comment) |
| 29 | "that was never added" | CANNOT CHECK | No sigmastate `ErgoTree` source is in the evidence |
| 30 | "every other Ergo identifier (box, transaction and token ids, P2SH) is BLAKE2b-256" | CANNOT CHECK | The evidence shows only the node's own ErgoTree hash (`IndexedErgoAddress.scala:114`). Outside the evidence: P2SH uses a 192-bit truncation of BLAKE2b-256, so "is BLAKE2b-256" is loose |
| 31 | "the node already uses it" | CONFIRMED | `IndexedContractTemplate.scala:58` |
| 32 | Explorer clients "have used it for years" | CANNOT CHECK | A backfill migration exists (`RegistersAndConstantsMigration.scala:84-87`), but nothing gives dates |
| — | Missing: node version and height | — | `output.txt:5` (node 6.1.2, height 1891228). The source was read at 6.0.7 (`README-SLICE.md:10`) |

## Task B: overclaim and framing

1. **"nothing in either API says the other exists"** (#14). Replace with: *"Neither service's documentation for these routes mentions the other definition, and a hash from one returns an empty result (not an error) on the other."* The "not an error" part is supported: the node's unspent route returns an empty result for an unknown template (`BlockchainApiRoute.scala:323-325`, `getOrElse(IndexedContractTemplate(templateHash))`), and the explorer returned `total: 0`.
2. **The fallback is blamed on the explorer only** (#25). This is the most serious framing problem: a node maintainer will spot it straight away. Replace the last sentence of "Why it matters" with: *"Both services also fall back to hashing the whole tree when `tree.template` throws (node: BLAKE2b-256 of `tree.bytes`, `IndexedContractTemplate.scala:61-63`; explorer: SHA-256 of the raw bytes, `sigma.scala:52`). So each index holds template hashes for most trees and whole-tree hashes for the rest, and neither API documents this."* In proposal item 2, change "and states the fallback" to *"and both services document the fallback"*.
3. **"every other Ergo identifier … is BLAKE2b-256"** (#30). Replace with: *"BLAKE2b-256, because the node already uses it for this and its other indexes (`Algos.hash`; e.g. `IndexedErgoAddress.scala:114`), and changing the node would invalidate its stored index keys (`IndexedContractTemplate.scala:22,73`) and force a reindex."* That reindex cost is the real argument, and it is checkable.
4. **"breaking it would break tools that have used it for years"** (#32). Replace with: *"keeping SHA-256 for existing clients"*.
5. **"the example #2218 was written for"** (#17). Replace with: *"the example #2218 uses"*.
6. **SigUSD framing** (#18). Replace the lead-in to the reproduction with: *"The EIP-31 Babel fee contract, instantiated with the SigUSD token id. Its constants are segregated, so the template, and both hashes, are the same for every token: the 22 are all unspent Babel fee boxes."*
7. **Is the proposal a foregone conclusion?** Mostly not: it is labelled "for maintainers to decide", and the offer to help is made conditional on agreement. Two problems remain:
   - It names only one option.
   - It asks for changes in two other repositories (sigmastate and explorer-backend) from the ergo tracker.

   Fixes:
   - Change the heading to *"**Possible direction (maintainers' call):**"*.
   - Add as a final item: *"4. The alternative, the node switching to SHA-256, avoids touching the explorer but requires a reindex; listed for completeness."*
   - Rename `ErgoTree.templateHash` to `ErgoTree.templateId`, so it matches the earlier reply it cites.
   - Add: *"Item 1 would need a sigmastate-interpreter issue and item 2 an explorer-backend issue; I'll open those if this direction is agreed."*
8. **Is "Why it matters" honest about how we found it?** It can't be confirmed from the evidence (#24). The only artefact is a reproduction built on 2026-10-09, and the Lithos mention reads like promotion. Keep the discovery sentence only if it is literally true, phrased as: *"We hit this moving a template query from the explorer to a node; the reproduction below was written afterwards to isolate it."* Replace the tools sentence with: *"Clients that find contracts by template (e.g. EIP-31 wallets looking for Babel fee boxes, the case in #2218) must know which service they are querying and hash accordingly."*

## Task C: register

1. **Length, tone and structure.** About right for an ergo issue: short, neutral, with code references. Cut the Lithos/DEX mentions, "years", and the list of identifiers in parentheses. Fix the title to: *"Template hash: node uses BLAKE2b-256, explorer uses SHA-256 (incompatible values, same name)"*.
2. **Missing: environment.** Add after the title: *"Node 6.1.2, mainnet, height 1,891,228 (source read at 6.0.7); explorer api.ergoplatform.com, explorer-backend master as of 2026-10-09."*
3. **Missing: a minimal reproduction that needs no Python.** Replace the table's lead-in with the block below. Fix the table's explorer header to `unspent/byErgoTreeTemplateHash`.
   ````
   Template bytes (EIP-31 Babel tree with header and constants removed):
   T=d803d601e30004d602e4c6a70408d603e4c6a7050595e67201d804d604b2a5e4720100d605b2db63087204730000d606db6308a7d60799c1a7c17204d1968302019683050193c27204c2a7938c720501730193e4c672040408720293e4c672040505720393e4c67204060ec5a796830201929c998c7205029591b1720673028cb272067303000273047203720792720773057202
   echo -n $T | xxd -r -p | b2sum -l 256   # ad6fbaa2fa57169ae9ccf7f548a8abce983e4124ed30d0b73eed5d75225f5574
   echo -n $T | xxd -r -p | sha256sum      # 4e83fa68ef3ed9794bbab5d8799998a9e09fb10a0afe8d1bf928936dfd11c465
   curl -s "$NODE/blockchain/box/unspent/byTemplateHash/ad6fbaa2…5574?limit=100" | jq length   # 22
   curl -s "$NODE/blockchain/box/unspent/byTemplateHash/4e83fa68…c465?limit=100" | jq length   # 0
   curl -s "https://api.ergoplatform.com/api/v1/boxes/unspent/byErgoTreeTemplateHash/4e83fa68…c465?limit=1" | jq .total  # 22
   curl -s "https://api.ergoplatform.com/api/v1/boxes/unspent/byErgoTreeTemplateHash/ad6fbaa2…5574?limit=1" | jq .total  # 0
   ````
   - **Check before filing:** I worked out `T` by hand from the tree in `repro.py:10-13`, following its parser at `repro.py:25-38`: six constants end at `…0500`, and the template starts at `d803`. Run the two hash commands once to confirm the digests.
   - **Hashes:** put the full hashes in the curl lines; I've shortened them here only for width.
   - **Node IP:** don't publish the third-party node's address from `repro.py:46`; keep `$NODE` as a placeholder.
4. **Missing: expected vs actual.** Add one line: *"Expected: one definition of 'template hash', or each API naming its own. Actual: the same name, two functions, and a silent empty result across services."*
5. **Links.** Replace the `.../` explorer path with a commit permalink to `sigma.scala#L52`, and link the explorer's route definitions (`BoxesEndpointDefs.scala` L122/L129) instead of quoting the search-body schema as if it were the route's documentation.
6. **Leave out:** the fact that #2218 is still open even though #2219 merged (`ergo-2218.md:36`). It's true, but it's off-topic and has already been raised in that thread.
