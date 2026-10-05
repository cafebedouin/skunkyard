# C1 validation run at height 836,808 (stale state; not the C1 answer)

Run by Claude on 2026-10-05 with the C1 mode of the q1 scanner (skunkyard `bc92d1e`, `Q1_C1=1`, `ergo-6.0.6.jar`
at the pinned hash) on a copy of the local mainnet node's state, which stopped syncing at **height 836,808**. The
network tip is about 1,887,800. These tables check the C1 code end to end on a real UTXO set. They do not describe
today's chain: the templates that dominate the tip (below, and `../c1-replication-odiseus-1886343/README.md`) were
mostly created after this height.

Scan checks (`scan-checks.txt`): traversed root equals stored root `b9f8a3f8…ab2e19`; 1,888,905 boxes; box sum
equals the genesis sum, 97,739,925 ERG. The default-mode output of the same scanner on the same state was
byte-identical to the pre-C1 scanner (`f905f9e`): stdout and all nine q1 CSVs.

Files: the seven `c1_*.csv` files as written by the scan, and `c1-section-stdout.txt` (the C1 part of stdout).
Aggregates only. In `c1_top_templates.csv` the explorer hash is withheld for templates with fewer than 10 boxes;
`c1_template_bytes.csv` holds template bytes (no constants, so no keys) for the 36 constant-segregated top templates
with at least 10 boxes. Reporting rule (SK-036): quote classes and totals, not single low-count templates.

## What it shows at 836,808

```
class                      boxes           ERG
single_dlog              1851095  94298549.447   (P2PK 56.3M; emission box 37.7M; mining reward 0.27M)
sigmaprop_from_data          250    967720.116   (foundation boxes, R4 SigmaProp)
dh_tuple                    1371     45850.059
threshold                     80      4126.138
and_or                       415       414.643
multi_key_no_connective      309       208.267
no_key                     35384   2423056.329
unparseable                    1         0.001
```

**At height 836,808, the DH undercount is real and large.** `c1_dh_check.csv`: of the p2s_with_key boxes at that height, q1 filed 58 boxes and
17.147 ERG under `create_prove_dh_tuple`, but 1,371 boxes and 45,850.059 ERG carry a `proveDHTuple` leaf. The other
1,313 boxes (45,832.913 ERG) were filed under `create_prove_dlog`, because the full-mix script puts
`proveDlog(c2)` before `proveDHTuple(g, c1, gX, c2)`. By value q1's DH row was about 2,700 times too small at 836,808. These are stale-state figures; they are
not tip numbers and are not to be quoted as such.
At 836,808, 96.6% of the DH value is one template, `441438d8b1a847e8`, the ErgoMixer full-mix box (identification in the
replication README).

The run does not answer C1 at the tip. That needs a C1 run on a synced state (instructions in `q1/README.md`,
section "C1 mode"); until then the tip picture rests on the external q1 run plus template identification.
