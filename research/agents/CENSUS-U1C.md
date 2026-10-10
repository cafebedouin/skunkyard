# Census U1c: every keyless spending path on mainnet, read from the scripts

Task: `prompts/census-u1c.md`. Scan: `census-u1c.py` (subcommands `walk`, `l`, `m`, `n`, `o`) with helpers in
`census/`: `utxo.py` (the unspent-set walk and box size), `paths.py` (the decompiled-script parser, path split and
classifier), `traced_u1c.py` (the hand traces), `candidates_u1c.py` (the unsigned candidate transactions),
`summarize_u1c.py` (every table below). Reuses U1b's `census/explorer.py`, `trees.py`, `names.py`. Output:
`census/u1c/` (`l.json`, `m.json`, `m-scripts.json`, `n.json`, `n-offers.json`, `o.json`, `traced.json`,
`height.json`, `summary.md`, and `candidates/`); the 1,232 raw stream responses and the compacted UTXO are
git-ignored under `census/raw/u1c/` and `census/out/`.

## Height, endpoint, method

- **Height 1,891,260**, the chain tip when the walk began (`/info`). **Endpoint:**
  `https://api.ergo.aap.cornell.edu/api/v1` (the Cornell mirror). The backup `api.ergobackup.aap.cornell.edu` still
  failed TLS (certificate expired, as in U1b) and was not used. Candidate transactions (line p) and line n's live
  takes were rebuilt at tip **1,891,297** (the boxes as they stood when built), stated with each.
- **Chain parameters, read from the chain** (`/info`, block 978,944): `storageFeeFactor` **1,250,000** nanoERG per
  byte, `minValuePerByte` 360. Rent period 1,051,200 blocks. One rent claim on a box of *n* bytes takes
  `n × 1,250,000` nanoERG.
- **The whole unspent set, walked by inclusion height.** `/boxes/unspent/stream?minHeight=a&maxHeight=b` returns
  every still-unspent box included in blocks a..b. The mirror caps a request at 1,536 blocks, so **1,232 requests**
  cover heights 0..1,891,260 — well within the prompt's ~2,000-request budget, so the whole set was walked rather
  than sampled. **3,176,571 unspent boxes, 2,118 templates** (2,117 contract templates + P2PK pooled as one). Dense
  ranges that returned 503 were split in half and retried (`census/utxo.py`); every range is present with no gap
  (checked). The walk took about an hour over three passes; each range records when it was read
  (`height.json`: first 1791600622, last ~1791603000), so a box spent between the first and last read can be
  missing — the set moves while it is walked. Box size is `len(ErgoBox.bytes)` computed from the explorer's fields
  (`utxo.box_size`; checked against live rent claims: a 79-byte P2PK box = 98,750,000 nanoERG, matching U1b).
- **Template hash** is the explorer's (SHA-256 of the constant-free tree), as U1b; a node's index uses BLAKE2b-256
  (ergoplatform/explorer-backend#289). All hashes here are the explorer's.
- **Paths** come from the explorer's decompiled script (`ergoTreeScript`) with a live box's constants
  (`ergoTreeConstants`) substituted, parsed into an AST, `HEIGHT`-against-constant comparisons folded at the fixed
  height, and the top proposition split into one conjunction of leaves per way it can be true (`||`, `anyOf`, both
  arms of an `if` whose branches hold a signature or `false`). This is a **reading of the decompiled text, not an
  evaluation**: every classification the parser makes is **SUSPECTED**; the ones in `traced.json` were traced by
  hand and are **CONFIRMED**. No key and no node were used; **nothing was built or submitted** beyond the unsigned
  candidate files.

**Build and submit nothing.** The candidates in `census/u1c/candidates/` are unsigned node-JSON transactions with
empty proofs and the context extension each input needs, against the boxes at height 1,891,297. They were **not**
checked by a node, signed, or broadcast. Each is [UNVERIFIED by a node].

## What "keyless" means here, and why the classifier's "keyless now" is not free money

The classifier marks a leaf **key** when it is SigmaProp-typed (`proveDlog`, `proveDHTuple`, `atLeast`, a SigmaProp
constant, or a SigmaProp read from a register or context variable); a path with no such leaf is **keyless**. But a
keyless path is not a free take:

- **keyless now** means no signature is needed, *not* that an outsider profits. Most of line m's "keyless now" ERG is
  a pool or bank swap (`2dcc7830` ErgoDEX pool, `c9162bd0` USE bank, `8b5dac35` hodlERG) or protocol plumbing
  (`ae9ac8d9` EIP-27 re-emission, 12.99M ERG, swept by the emission transaction). These need the taker's **own
  capital** or a **counterparty**, and pay whoever builds the transaction **nothing** beyond the protocol's own
  rules. The parser cannot tell "anyone profits" from "anyone may submit"; it reports the latter.
- The takes that actually pay an executor are the ones traced by hand (below) and shipped as candidates.
- **keyless with input** is the honest residual for most of the set: a path that reads another input's tokens/id,
  a data input, or a context variable. Whether that input is obtainable is a per-protocol question; the parser only
  flags that one is read.

So the headline number — 487 templates "keyless now", 13.75M ERG — is **traffic and plumbing, not takeable value**,
exactly the trap U1b's "rent only" label fell into, now in the other direction. The takeable keyless value standing
now is small (line n), as U1b found: storage rent remains the one large keyless take, and it is own-block only.

## l. The template set (full tables in `census/u1c/summary.md`)

- **P2PK: 3,075,918 boxes, 77,573,298 ERG.** At rent age now **90**; reaching it within 30 d **91,278**, 90 d
  **237,978**, 365 d **812,606**. This is the unspent-set-by-age U1b could not list from this mirror (U1b "Not
  measured"); the walk supplies it. At U1b's ~0.082 ERG taken per claimed P2PK box (6,282.4 ERG over 76,926 boxes
  in its 30-day window), 812,606 boxes maturing within a year is the rough scale of P2PK rent flow, most of it on
  tiny boxes consumed whole. Only **90** P2PK boxes sit past rent age unclaimed now — claims are taken within 0–36
  blocks of maturity (U1b), so the stock is the flow reaching age, roughly 2,200–2,600 boxes a day.
- **Contract boxes: 100,653 boxes, 19,033,970 ERG, 2,117 templates.** The ERG is concentrated: EIP-27 re-emission
  (`ae9ac8d9`, 12.99M), an unknown multisig/escrow family (`44f78dee`, 2.67M, 11,386 boxes), the SigmaUSD bank
  (`246e1405`, 1.63M), ErgoDEX N2T pools (`2dcc7830`, 632k over 285 pools), the USE bank (`c9162bd0`, 297k), a
  time-locked-key template (`961e872f`, 217k over 29,098 boxes — a vesting/lock family, keyless only as rent), and
  Rosen Bridge collateral (`0c7face7`/`1151628a`, 182k).
- **By box count:** the time-locked key `961e872f` (29,098), the `44f78dee` family (11,386), an unknown token-gated
  template `83359e0b` (9,400, all below one rent claim, all reaching rent age within a year — 10.3 ERG at risk),
  the FlowLens immutable-records template `75bee19d` (8,306, unspendable by design — see line m), `e116065b`
  (5,566), SkyHarbor sales (`f9f76671`, 2,765). Value, creation-height and size distributions per template are in
  `l.json` and the summary's two tables.

## m. Every path, classified (full data in `m.json`; scripts in `m-scripts.json`)

Classifier over the 2,117 contract templates, by each template's most open path:

| most open path | templates | boxes | ERG | note |
|---|---|---|---|---|
| keyless now | 487 | 5,058 | 13,753,819 | mostly pools, banks, plumbing (needs capital/counterparty; pays the executor nothing) |
| keyless later | 291 | 1,149 | 12,688 | a height, age or timestamp gate |
| keyless with input | 1,128 | 29,561 | 2,190,356 | reads another input, a data input, or a context variable |
| key only | 183 | 56,425 | 3,077,015 | every path needs a signature |
| unreachable only | 3 | 8,310 | 3 | no input can satisfy any path |
| no path | 2 | 3 | 1 | the proposition is `false` after folding |
| not decompiled / not split | 23 | 147 | 87 | see below |

- **Could not decompile or classify (23 templates, 147 boxes, 87 ERG).** The explorer returns no decompilation for
  the LithosDex orders and fee vault (`b4fd5d9b`, `7122d569`, `29956fe5` — they use `DeserializeContext`, which the
  explorer prints as "not implemented"; the spender supplies a script in a context variable, checked against a hash
  constant — classified **keyless with input** where the hash appears, else left here) and for several unknown
  templates (`1c6a6202`, `d51d6c6c`, `47b6c65a`, three boxes whose tree this parser cannot hash — shown as
  `unparsed:191`). Nine templates have **more than 256 split paths** (deeply nested `if`s, e.g. `b4cf99e5` 320,
  `fd14cf52` 512): the split is capped and they are left unclassified rather than guessed. Two have a genuine
  parser gap (`1acd93e6`, `a510cbf2`). These are the templates the census explicitly could not read; all are small.
- **Unreachable by design.** `75bee19d` (8,306 boxes, "flowlens:forensic:immutable:v2" in R4): the only path is
  `HEIGHT < 0 && R4 == tag`, which no block can satisfy — immutable records, unspendable even by their author,
  recovered only by storage rent four years on (CONFIRMED). This is the stranded-value shape U1b found in six
  Machina boxes, here at scale.
- **Unreachable per box** (a path reads `SELF.Rn.get` and the box lacks `Rn`): 14 of 285 ErgoDEX pools, 11 of 293
  T2T pools, 6 of 7 `a16dfa91` (Machina — the no-R6 strand U1b flagged, confirmed here on live boxes), and a long
  tail (summary). SUSPECTED (register presence read from the box, path-death inferred from the parser's leaves).

### Keyless paths traced by hand (CONFIRMED) — do any pay an executor?

33 templates were read line by line (`traced.json`). The finding mirrors U1b: **almost no keyless path pays whoever
builds the transaction.**

- **Staking incentive** (`278ccff2`, `b924a4f7`): the consolidation bounty (0.0005 ERG per merged box) is real and
  CONFIRMED, but every box ≤ 0.1 ERG was merged on 2026-10-09 (U1b round two); the 14 surviving boxes each hold more
  than 0.1 ERG, so the bounty path is closed until new small boxes are created. **0 takeable now.**
- **Paideia DAO treasury** (`37142e74`, `5b41af39`): a keyless merge of ≥ 5 boxes of one DAO's tree pays at most
  **0.002 ERG per transaction** (not per box), and a keyless **refresh** at 504,000 blocks of box age — rent
  protection built into the contract (CONFIRMED). No DAO tree has ≥ 5 boxes now, so no merge is due; a few refreshes
  are due but pay 0.002 ERG. This is the clearest new keyless-upkeep shape the census found, and it is tiny.
- **Free boxes** (`e9d13195`, `OUTPUTS.size == 1`): 30 boxes, **0.70 ERG**, a miner's own block only (no fee box
  fits a one-output transaction) [inferred] — candidate `e9d13195d73d-1`.
- **Everything else pays the protocol, not the executor:** the Phoenix hodl banks (`8b5dac35`, `5811576e` —
  user-paid mint/burn), SigmaFi bonds (`edacb0e6`, `44830db1` — matured value to the lender, no reward), fee/tip
  splitters and payout boxes (`0df8312f`, `9a54eb24`, `2b0bcc21`, `c7c5a98a` — fixed recipients), the AVL payout
  ledgers (`ab9e9b2a`, `a88b7bcf`), the GORT/DORT buybacks (`f2aa6b79`, `8b1e2b81`), EIP-27 (`ae9ac8d9`,
  `707c363f`), and the two AgeUSD banks and the USE bank (`246e1405`, `9259d83f`, `c9162bd0` — mint/redeem needs the
  oracle as a data input, and the arbitrage leg needs a second transaction and capital, U1b j). All CONFIRMED to pay
  the executor nothing beyond the protocol's own fee outputs.

## n. What each keyless path pays and costs (live at tip 1,891,297, `n.json`)

| take | standing now | what the executor gets | transactions | capital | repeating? |
|---|---|---|---|---|---|
| **Babel + grid/limit offers vs N2T pools** (U1b g, rerun) | 22 Babel, 14 OtG, 5 kushti, 7 Machina-limit, 6 Machina-grid unspent | **0.0291 ERG** taken in turn (4 Machina-grid bids) | 1 each | none | one-time (stale bids) |
| **Free boxes** `e9d13195` | 30 boxes | **0.7016 ERG** (own block only) | 1 | none | one-time |
| ErgoDEX N2T SwapSell v1 executor fee | 36 orders, 2 executable | **0.0009 ERG** | 1 | none | per order (recurs as orders arrive) |
| Consolidation bounty (staking) | 0 boxes ≤ 0.1 ERG | 0 (all merged 2026-10-09) | — | none | repeating once small boxes exist |
| Paideia treasury merge | no tree with ≥ 5 boxes | 0 now; ≤ 0.002 ERG/tx when due | 1 | none | repeating |
| Paideia refresh (later) | a few boxes due; first at height 1,842,321 | ≤ 0.002 ERG/box | 1 | none | repeating (per 504,000 blocks) |

The Babel/offer and SwapSell figures are U1b's line g and SwapSell-v1 code rerun on live boxes (`n-offers.json`);
the standing keyless take is **under 0.8 ERG**, almost all of it the free boxes, and that is own-block only. **This
confirms U1b and contradicts nothing in it:** reading every script rather than sampling did not uncover a large
keyless take hiding behind a "rent only" label. The one genuinely new keyless-upkeep mechanism (Paideia's built-in
merge/refresh) pays 0.002 ERG and nothing is due.

## o. Protocol funds at risk from storage rent (`o.json`)

645 contract templates hold boxes worth less than one rent claim. Boxes reaching rent age: **176 now (2.9 ERG),
1,321 within 30 d (13.7 ERG), 2,434 within 90 d (52.7 ERG), 25,249 within 365 d (200.0 ERG)**. The largest at-risk
templates within a year: an unknown family `b10e22f0` (57 boxes, 42.8 ERG), a Rosen-Bridge-adjacent `7df7d49c`
(845 boxes, 39.1 ERG, holds rsDIS/USE/ErgOne), `ab4d7134` (55, 15.2), `e116065b` (4,428, 13.3), the token-gated
`83359e0b` (9,400, 10.3 — an Ergo-RWT-beta box), SkyHarbor sales (`f9f76671`, 2,320 boxes, 7.0), the time-locked
key `961e872f` (583, 5.8).

**Can a third party preserve them?** For almost all, **no keyless path lets an outsider do it**: the preserve paths
the classifier finds are "keyless with input" — they need the protocol's own state box (a bridge repo box, a DAO
config, a staking state NFT) that only the protocol holds. The template-level `preserve` verdicts in `o.json` are
SUSPECTED except the staking and Paideia rows (CONFIRMED from the hand traces). So these are **KeepAlive targets**
(a holder-opted vault, `skunks/keepalive/`) or protocol-level fixes (EIP-53/51), **not** jobs a Lithos miner can do
for a fee today — the opposite of the staking consolidation bounty, which was keyless precisely because its path
read no external box. The 200 ERG/year is also small against P2PK rent (812,606 boxes maturing within a year).

## p. Candidates (unsigned, `census/u1c/candidates/`, height 1,891,297)

| file | kind | inputs | payout ERG | Lithos upkeep job? |
|---|---|---|---|---|
| `e9d13195d73d-1.json` | free box (`OUTPUTS.size == 1`) | 30 | **0.7016** | one-time; own block only (no fee box) [inferred] |
| `a68900b67ff5-1.json` | Machina grid bids vs N2T pool (f0cac602) | 4 | **0.0206** | one-time (stale bids) |
| `a68900b67ff5-2.json` | Machina grid bid vs N2T pool (d4f01926) | 2 | **0.0063** | one-time |
| `36d1944fe6d7-1.json` | ErgoDEX N2T SwapSell v1 executor fee | 2 | **0.0010** | repeating (executor fee per order) |

Each has a `.meta.json` sidecar with the amounts and the exact contract rule each output satisfies. The free-box
and SwapSell candidates follow U1b/U1's shapes; the Machina-grid candidate is the one shape U1b described but did
not build — pool at input 0, each grid bid box after it with context var 0 = false (bid side) and var 1 = its
successor's output index, R6 = its id, one pool swap for all the units. All are **[UNVERIFIED by a node]**; to be
checked and taken, if at all, outside this session.

**Checked on chain (2026-10-10, outside the census session).** We checked all four against a 6.1.2 node
(`/transactions/check`, tip 1,891,302) and took three; all three were mined at 1,891,305
(`skunks/upkeep/mainnet/README.md`, round four):
- both Machina-grid candidates passed as built: +0.0206353 and +0.0062539 ERG;
- the SwapSell candidate was **malformed**: the owner's box held 0 ERG, below the minimum box value. Its fee rule
  allows any split of the 2,000,000 nanoERG left over, so we rebuilt it to give the owner 1,000,000 and take
  nothing, and submitted it;
- the node checks the one-output candidate as valid but its mempool refuses it ("Min fee not met"), which confirms
  the [inferred] "own block only".

## What this extends or contradicts in U1b and UPKEEP.md

- **Extends U1b's "Not measured".** The unspent set by age is now listed: 812,606 P2PK boxes and ~25,000 contract
  boxes reach rent age within a year. U1b could not get this from the mirror; the by-inclusion-height walk does.
- **Confirms "rent only was a sampling label."** Reading every script (not 12 samples) finds the same thing U1b's
  spot-reads did: the staking templates have a keyless consolidation path; almost everything else labelled by
  spender behaviour needs either a key or the protocol's own state box. No large keyless take was hiding.
- **Confirms the scorecard.** The standing keyless take is under 0.8 ERG (mostly free boxes, own-block only); every
  arbitrage/offer take is small now, as U1b and U1 measured. Storage rent remains the one large keyless take and is
  own-block only since node 6.0.7.
- **Adds a second built-in rent defence.** Paideia's treasury contract carries a keyless merge *and* a keyless
  refresh at 504,000 blocks of box age (half the rent period) — the due-job shape (UPKEEP.md U3) with a deadline set
  by box age, deployed and live, independent of the staking bounty. It pays 0.002 ERG, confirming UPKEEP.md's "small
  money": these are upkeep bonuses, not a security budget.
- **Sharpens the KeepAlive case.** Line o shows most at-risk protocol boxes have *no* keyless third-party preserve
  path (they need the protocol's state box), so they cannot be defended by a generic executor the way the staking
  boxes were; they need an opt-in vault (`skunks/keepalive/`) or a protocol change. The staking bounty worked
  because its path read no external box — a design property, not a given.

## Not measured / limits

- **Classifier is a text reading, every un-traced classification is SUSPECTED.** It does not evaluate arithmetic
  (whether a successor can actually hold the value a path demands), cannot judge whether a "keyless with input" box
  is obtainable, caps the path split at 256 (9 templates left unclassified), and cannot read `DeserializeContext`
  scripts the explorer does not decompile (the LithosDex orders among them).
- **"keyless now" over-counts takeable value** by design: it means no signature, not that an outsider profits; the
  real takes are the hand-traced ones and the candidates.
- **The set moves while walked** (~an hour of reads); a box spent mid-walk can be missing, and counts are as-of the
  read times in `height.json`, not a single instant.
- **No node verification.** No candidate was checked, signed or submitted; node acceptance of any of them is
  [UNVERIFIED].
- Duckpools/SigmaFi liquidation health, and the exact per-box rent timing beyond the age buckets, are not computed.
