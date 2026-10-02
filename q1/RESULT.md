# Q1 result: DRY RUN at height 753,934 (not the answer to Q1)

Scanned by Claude on 2026-10-01 with `bash q1/run.sh /home/scott/bin/ergo-node/.ergo/state` (two runs, identical
output, in `README.md`). **The node's UTXO state was at height 753,934 and the network tip was 1,885,567**, so these
figures describe the chain at 753,934, not today. This run checks the scanner. The answer to Q1 comes from the same
scripts re-run at the tip.

**The scanner is correct by construction at this height.** It visited 2,985,403 tree nodes with 0 label mismatches.
The traversed root `481ae8c3...86da618` equals the stored root and the stateRoot in header `f0319553...` (height
753,934) served by the node. The 1,492,701 boxes sum to 97,739,925 ERG, which equals the node's genesis boxes.

**Correction to the brief's invariant.** The total is 97,739,925 ERG, not 97,739,924. The difference is the 1-ERG
genesis no-premine-proof box, whose script is `sigmaProp(false)`. Without that box the sum is exactly 97,739,924 ERG.
Both checks are printed and enforced.

**What the dry run shows, at height 753,934:**

```
category        boxes         ERG                 pct_supply  pct_ex_protocol
p2pk            1,463,099     51,523,422.778      52.7148     95.9318
mining_reward      15,722        276,008.099       0.2824      0.5139
p2s_with_key        6,637         51,967.124       0.0532      0.0968
p2pk_other              0              0
EXPOSED         1,485,458     51,851,398.001      53.0504     96.5425
protocol                9     44,031,545.719      45.0497        -
p2s_no_key          7,233      1,856,981.279       1.8999      3.4575
p2sh                    0              0
unparseable             1              0.001
```

- Exposed value is almost all bare P2PK: 51,523,422.778 of 51,851,398.001 ERG. P2SH holds nothing at this height,
  and neither does any non-standard bare `proveDlog` tree. Exposed boxes hold 38,700 distinct token ids, in 154,360
  boxes.
- Excluding the protocol boxes, 96.5425% of ERG sits under a script that contains a key. Only 3.4575% sits under
  scripts with no group element at all.
- `p2s_with_key` is small (51,967.124 ERG). Most of it, 45,198.378 ERG in 3,927 boxes, has the key built at spend time
  (`CreateProveDlog`, for example from a register) rather than stored as a constant. One script template accounts for
  43,537.005 ERG in 1,071 boxes.
- Protocol boxes: emission 42,768,825 ERG; foundation script 1,262,719.719 ERG in 7 boxes, with R4 holding a
  serialized SigmaProp that contains a `ProveDlog` (founders' keys, reached through `DeserializeRegister`); no-premine
  proof 1 ERG. The emission tree also contains a `CreateProveDlog`. That node is the miner-output template the emission
  script checks against, not a key that spends the box (inferred from `ErgoTreePredef.expectedMinerOutScriptBytesVal`,
  not traced node by node).
- Dormancy: 0 exposed ERG is 1,051,200 or more blocks old, and 0 is 788,400 or more. That follows from the height,
  not from behavior: no box can be older than 753,934. The oldest populated exposed bucket (525,600 to 788,399
  blocks) holds 9,163,605.053 ERG in 29,795 boxes.

**Limits of the method (stated, not solved):**
- A `p2s_with_key` or `mining_reward` box may belong to a dApp, pool or contract, not to one user. The category says a
  key is in the script, not who holds it.
- Keys exposed off-chain (xpubs, signed messages, keys revealed in a spending transaction of another box on a
  hash-protected script) are not visible to a UTXO scan. P2SH counts as unexposed, but its script is revealed when it
  is spent.
- Age is `creationHeight`, the height the box creator declared. It is a last-touch proxy. It is also the field storage
  rent uses, so the ">= 1,051,200" line matches rent eligibility exactly.
- Key detection walks the parsed tree and its constants. A key held as raw bytes and decoded at run time, or kept only
  in a register, is not counted unless the tree builds a `ProveDlog` from it. Registers are inspected only for
  protocol boxes.
- Tokens are reported by id and raw amount only, with no decimals and no names.

**Cost of the final run:** at this height the scan took 55 to 57 s and copying the state took 1 to 2 s
(`out/timing.txt`). The node must be stopped for the copy.

## EIP-27 classification check (height 778,668, 2026-10-02)

Run by Claude with the same scripts on the node's state 1,451 blocks past EIP-27 activation (777,217), to confirm the
re-emission contracts classify as protocol boxes before the final run. Printed output, committed: `out/eip27-check-778668.txt`.
Roots match, 0 label mismatches, supply 97,739,925 ERG exactly. From that file:

```
protocol_box       boxes                 ERG
emission               3  41210709.200000000
foundation             7   1232719.518690072
no_premine_proof       1         1.000000000
pay_to_reemission    240      7296.000000000
reemission             1         2.590000000
EXPOSED share of non-protocol ERG: 96.0528%   (p2pk 95.3945%, p2s_no_key 3.9472%)
```

7,296 = 608 x 12. An earlier run of the same day at height 778,572 (not committed; its per-box dump was read from the
scanner's `Q1_PROTOCOL_BOXES=1` output) showed 208 pay-to-re-emission boxes holding exact multiples of 12 ERG (109 of
12, 45 of 24, 27 of 36, ...) with creation heights mostly 0, and the re-emission box at 2.59 ERG. What the numbers mean,
read from the EIP and the boxes: the 12 ERG re-emission share is taken when a miner spends a reward box, not in the
block, so a withdrawal of k reward boxes makes one 12k ERG pay-to-re-emission box, and pools stamp creation height 0 on
it. The re-emission ERG not yet in those boxes sits in unspent mining-reward boxes, which the scan counts as exposed
(they carry the miner key). Two 0.1-ERG dust boxes sent to the emission address classify as `emission`; harmless.

Reading note for the final run's storage-rent line: rent collection is done by miners and pools, and none collected at
first; the Sigmanauts pool was the first, set up with help from Cheese_Enthusiast (the developer behind Lithos and
GetBlok), as recalled by the person who runs this repository. So "exposed and rent-eligible" at the tip measures what
pools have not yet collected, not what the protocol permits.

## Third scan, height 783,047 (2026-10-02): the concentration aggregate

Same scripts after the scanner gained an aggregate line (the ranked list stays unprinted). Committed output:
`out/scan-783047.txt`; wall-clock copy 48 s, scan 103 s at 1,649,000 boxes (`out/timing.txt`). All checks pass.
Exposed 96.0967% of non-protocol ERG (p2pk 95.4235%, p2s_no_key 3.9033%); pay-to-re-emission 1,774 boxes, 57,204 ERG.
Printed: `top 20 exposed boxes together: 13997362.597567807 ERG = 26.2259% of exposed ERG, 25.2022% of non-protocol ERG`.
