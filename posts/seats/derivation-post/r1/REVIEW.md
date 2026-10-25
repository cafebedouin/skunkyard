# Derivation post, seat round r1 (2026-10-25): what the seats found and what v2 changed

Draft v1 of `posts/2026-10-derivation-reply-draft.md` went to three seats on a public-only slice outside the repo
(`build-slice.sh`: the draft, thread 5371's opening post from the forum's raw endpoint, and `skunks/pqwallet`'s
sources, tests, vectors and results): a Claude Opus Fidelity seat (`prompt-fidelity.md`, `out/fidelity.md`), Grok
(`prompt-outside.md`, `out/grok.md`, raw and meta beside it) and Gemini via agy (`prompt-outside.md`). Gemini's first
run produced no text: it requested a shell command, which headless mode auto-denies, and ended with an empty response
(`out/agy-20261025T172812Z.raw.txt`). It was rerun with `prompt-outside-agy.md`, which opens with a read-only
instruction; that run's output is recorded below when it arrived.

Every fact a seat introduced was re-derived against the sources before it changed the draft; the "witness" column
says where.

## Verdicts

- Fidelity: post with the listed fixes; all six printed vector values, the heights, the versions and the testnet
  claims match their sources.
- Grok: do not post as is; rule B as coded is a sound hardened HMAC tree and the vectors match, but the draft
  overclaims the xpub test, misstates B's HMAC count, treats C as implemented, and is a new topic on a KeepAlive
  thread.
- Gemini: see the section at the end.

## Disposition

| Finding | Seat | Witness | v2 |
|---|---|---|---|
| "two HMAC-SHA512 calls per level" is wrong: one per level plus one at the root | Grok 1, Fidelity | `src/derive.ts` `rootB`, `childB` | **Fixed**: "one call per level" |
| "Three rules were implemented": C is described only | Grok 2 | `derive.ts` header, "Nothing to implement"; `leaf()` takes `'A' \| 'B'` | **Fixed**: "written up, not coded" |
| "This settles how a wallet would derive … restore works from the phrase alone" overclaims; the vault address needs values the seed lacks | Grok 3 | `DERIVATION.md` "a proposal, not a standard"; section 4 of the draft | **Fixed**: "proposes"; restore limits in section 4 |
| "the test prints child 7's key": it compares two arrays and prints a PASS line | Grok 4, Fidelity | `test/derive.test.ts` check 7 | **Fixed** in the draft and in `DERIVATION.md` line 20 |
| Discrete log, unused addresses and hardened descendants are reading, not the test | Grok 5, Grok 29 | check 7 takes a child private key as input | **Fixed**: "The test shows one sibling; the rest is BIP32 arithmetic", labelled (read, BIP32) |
| Check 11 ("neither rule's leaf") is a byte inequality, not a reachability proof | Grok 6 | `test` check 11 | **Fixed**: stated as "equals neither rule's leaf at index 7", no security weight |
| "its 64-byte seed is checked against the published value": the test checks the `TREZOR`-passphrase vector; the PQ vectors use the empty passphrase | Grok 7, Fidelity | `test` lines 17–19; `vectors/*.json` `passphrase: ""` | **Fixed**: both stated; the empty-passphrase seed given |
| "flag box id" should be the flag NFT id; the box id changes on every spend | Grok 8, Fidelity | `testnet/RESULT-testnet.md` pin `QDAY_NFT`; `DERIVATION.md` "flag NFT" | **Fixed** |
| SUCCESSOR dropped: vault k's address commits to vault k+1's tree; restore follows the chain; one spare generation | Fidelity | `RESULT.md` "The successor is fixed at creation"; pin `SUCCESSOR` | **Added** to section 4 |
| "any BIP32 library or hardware wallet derives the leaf today": device path allowlists are not in the slice | Grok 9 | none in slice | **Fixed**: "whether a hardware device allows the path is device-specific" |
| A's hardware benefit offered without `DERIVATION.md`'s condition (device-internal, never serializes a key on the branch) | Fidelity | `DERIVATION.md` "kept only as a device-internal path" | **Added** after the table |
| Master-xpub row drops that any node's extended key on the branch has the same reach and that nothing in the code enforces non-serialization | Fidelity | `DERIVATION.md` option-A paragraph | **Fixed**: row retitled "leaked extended key on the branch", both points in |
| WOTS+ keygen under-specified: chain start, the tweakable hash, the commitment includes `pkseed` | Fidelity | `src/wotsplus.ts` lines 15–18, 47, 49 | **Fixed**: the three formulas written out |
| Schedule under-specified: eight leaves, leaf-index prefix, Merkle rule | Fidelity | `derive.ts` `scheduleKeys`; `merkle.ts` | **Fixed** |
| "Full leaves … in the vectors" overclaims: no SLH-DSA leaf, no schedule leaf secrets, no B root | Fidelity, Grok (missing list) | `vectors/derive-B.json` before this round | **Fixed by adding them**: `scripts/vectors.ts` now writes the SLH-DSA leaf, eight schedule leaf secrets and B's root split; regenerated, the six headline values unchanged, the diff additive (A +11 lines, B +16 and one line re-terminated); `npm test` ALL PASS 32 |
| `expand` capped at 64 bytes | Fidelity | `derive.ts` `expand` | **Added** |
| "two libraries agree on what a seed means" is one key pair and one signature | Fidelity, Grok 25 | `RESULT.md` limits | **Fixed** |
| Python cross-check is a copy of the harness functions, not the harness file | Fidelity, Grok 10 | `RESULT.md` limits | **Stated** |
| SLH-DSA sign-and-verify is a noble self-check | Fidelity, Grok 11 | `test` lines 70–73 | **Stated**: "the same library verifies" |
| Credit line named only Grok and Gemini as review seats while a correction credited "in review" came from the Claude seat | Fidelity | `DERIVATION.md` correction note; `RESULT.md` seat round | **Fixed**: "three review seats, one a Claude instance and two outside models"; no model is tied to a finding |
| BIP32's `"Bitcoin seed"` string should be cited for B's independence; SLIP-0010 cited beside the child step; FIPS 205 does not specify `expand` | Grok (standards) | `derive.ts` comments; FIPS 205 keygen input | **Added**, each labelled (read) |
| Why not BIP85; why B has no purpose level | Grok (missing) | BIP85 derives entropy from a hardened BIP32 child key | **Added** one sentence each, (read, BIP85) |
| State that KeepAlive and the two-step vault are unchanged | Grok (missing) | thread 5371 | **Added** to the first paragraph |
| One leaf hex to debug against, and the B root split | Grok (missing) | `vectors/derive-B.json` after regeneration | **Added**: vault-0 secret and root key half quoted |
| Cut the 32-check list, the named-model process, testnet heights | Grok (cut) | | **Partly**: the check list compressed to one paragraph; heights cut; the credit line kept, shortened, because the house rule is to credit AI tools up front |
| Vehicle: a reply forks the KeepAlive thread; the charter calls this its own post | Grok (fit) | `CHARTER.md` step 5; thread 5371's open item | **Operator's call**: the draft works as either; the header says so |
| Thread 5372's sentence not in the slice | Grok 12, Fidelity | | **Accepted**: the quote is from the thread (fetched 2026-10-25) and stays, paraphrased to one line |
| EIP-3 depth-4 export, Ledger secp-only: reading, unlabelled | Fidelity, Grok 13 | | **Labelled** (read) |
| `derive.ts` header still said "no public key of this branch is ever computed" | Grok (crypto reading) | `derive.ts` lines 6–9 | **Fixed** in the code comment |

Kept against advice: the length. v1 was 1,439 words; v2 is 1,785, because the seats asked for the keygen formulas,
the schedule rule and the vector inventory, which make the post reproducible without the repository. The lint's
80-word budget for a reply fails on this file by design; the operator decides.

## Gemini (agy), rerun

The rerun (`out/agy-20261025T173755Z.raw.txt`, meta beside it; no denied actions) read v1 and verdicted "reject in
current form". It repeated the HMAC count, the `TREZOR` vector, the flag NFT id, rule C and the thread-fit findings
above, and added these:

| Finding | Witness | v2 |
|---|---|---|
| The BIP32 formula omits `be32(i)` and the 32-byte truncation of the HMAC output | `derive.ts` `siblingFromXpub` | **Fixed** |
| "five hardened levels" is wrong for A, which has six from the master (the purpose) | `derive.ts` `pathA` | **Fixed**: "below the root (B) or the purpose (A)" |
| `leaf` is defined with four arguments and called with three | `derive.ts` `leaf()` | **Fixed**: the three-argument form declared as shorthand for one account |
| B's path string `pq/429'/account'/scheme'/use'/index'` never written out | `derive.ts` `pathB` | **Added** |
| Address length: wallets will ask whether UIs and QR codes take a 986-character address | `RESULT.md` vectors line (986 chars); `RESULT-testnet.md` pin (vault address 1,852 chars) | **Added** to section 4 |
| Cut the AI attribution line | | **Kept**: the house rule credits AI tools up front |
| Vehicle: thread 5372 or a new topic, not 5371 | thread 5371's two asks | **To the operator**: header rewritten; the two outside seats agree |
| Provide a copy-paste TypeScript snippet | | **Not added**: the four-line rule is exact and the file is linked; length |
| Name an EIP number or PR for the domain string | | **Not added**: the post asks whether one should exist; none does |
