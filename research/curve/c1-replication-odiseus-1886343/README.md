# C1 first cut: external replication at height 1,886,343 (odiseus, GitHub: odiseusme)

Four aggregate tables from an independent run of `q1/run.sh` at skunkyard 28331fe on a synced mainnet node
(ergo-6.0.6.jar matching the pin; state copied from a stopped node, scanned on a separate machine), received
2026-10-05 in the developer chat. Same run as the Q1 census re-run (tip 1,886,343, header c331d6a6…cbba; traversed root
= stored root 870e5a8d…b419; 0 label mismatches; box sum = genesis sum). Credit: "odiseus (GitHub: odiseusme)", as the
contributor asked.

Files as written by the run: `p2s_with_key_indicators.csv`, `p2s_with_key_top_templates.csv`,
`p2s_no_key_top_templates.csv`, `by_category_age.csv`. `top_boxes.csv` was deliberately not shared.

Checks done here (2026-10-05): the indicator rows sum to the published p2s_with_key line (37,027 boxes,
2,907,737.890 ERG); age buckets sum per category (printed by the check above; see commit message).

Reporting rule (SK-036): template level only. Some templates have very few boxes (e.g. a no-key template with 2 boxes);
quote classes and totals, not single low-count templates.

## Template identification (2026-10-05, Claude)

How the template id is computed (`q1/Scan.scala`): `hex(blake2b256(tree.template)).take(16)`, i.e. the first 8
bytes of blake2b256 over `ErgoTree.template`, which is the serialized root expression without the header and the
constants segment. The public explorer indexes `sha256` of the same bytes as `ergoTreeTemplateHash`
(explorer-backend `modules/explorer-core/.../protocol/sigma.scala`, `deriveErgoTreeTemplateHash`), so the two ids
differ but name the same template. Both are printed by `q1.TemplateId` (skunkyard `bc92d1e`).

Method: candidate ErgoTrees from public sources (P2S addresses decode to the full tree: base58, strip the prefix
byte and the 4-byte checksum) and from the outputs of 240 randomly sampled blocks between heights 1,360,744 and
1,623,543, run through `q1.TemplateId`, compared with the ids in the two top-template tables. Template level only:
contract classes are named, no box ids or addresses.

Box and ERG figures in this table are at height 1,886,343 (odiseus's run).

| template | at 1,886,343 | template structure | identified as | evidence |
|---|---|---|---|---|
| `4d0028d7861677d9` | 11,342 boxes, 2,669,998.071 ERG | `atLeast(c0, Coll(c1..c10))`, all constants: one `AtLeast` over 10 constant `ProveDlog` keys; `c0 = 6` in the trees examined | **a bridge custody 6-of-10 multisig** | template bytes `987300830a08730173027303730473057306730773087309730a`; the id is reproduced from a compiled 6-of-10 tree with synthetic keys (`q1/test-c1.sh`); the q1 id was recomputed from trees in the bridge's own published configuration and matched. Which project: held back until the project has been told |
| `59eeee379e227e99` | 1,126 boxes, 94,798.372 ERG | `atLeast(n, R4.map(row => proveDlog(decodePoint(row))))` over a data input, plus a token check | **a bridge lock wallet** (same bridge as above) | structure matches the bridge's published lock contract; project held back as above |
| `441438d8b1a847e8` | 941 boxes, 46,996.792 ERG | `(proveDlog(R5) \|\| proveDHTuple(g, R4, R6, R5)) && sigmaProp(nextAlice \|\| nextBob \|\| destroyToken)` | **ErgoMixer full-mix box** (ring member; DH) | AST matches `TokenErgoMix.fullMixScript` in `ergoMixer/ergoMixBack` (`mixer/app/mixinterface/TokenErgoMix.scala`) node for node; the address appears in that repository's test dataset. Recompiling the source with the 6.0.6 compiler gives a different id (`a85a4f3f232cecc7`), so the match is structural, not byte-identical (likely compiler version) |
| `9662579c80ed3102` | 714 boxes, 6,010.035 ERG | `pk && sigmaProp(HEIGHT > c)` | **generic timelocked key** (no project) | template bytes `ea027300d191a37301` |
| `c7709a676c759d63` (no key) | 2 boxes, 1,627,357.900 ERG | no sigma leaf | **SigmaUSD bank** | the sampled tree's address is `bankAddress` in `anon-real/sigma-usd` `src/utils/consts.js` |
| `850f2d5b02b3e666` (no key) | 285 boxes, 626,030.811 ERG | no sigma leaf | **ErgoDEX (Spectrum) AMM pool** | the sampled tree's address is the ErgoDEX TVL address in DefiLlama's `projects/ergodex.js` and `DEX_ADDRESS` in `duckpools/off-chain-bot` `consts.py` |

Not identified (not met in the block sample, not tried further): with key `cab8078155d95283` (seen in the sample: a
66-constant contract with a single `proveDlog` built from a register; no public source found for its address),
`c4ab8f4e8cfab60b`, `842e6165a18b3a28` (at height 836,808: a threshold over 5 constant keys), `063c6980d20d9956`,
`05b263637b4c055b`, `b4a78b84c0581ff6` (at 836,808: a threshold over 3 constant keys); without key
`c00078acded11dc0`, `c6fb63b67b49057c`, `bacea7c6d7afcf90`, `5cf7ae4d451a8dbe`, `0459b0766ff5504e`,
`cd850616f538f665`, `f75f464df95f7d8b`, `bff7d38d6ae0f207`. Lookups by explorer template hash time out on the
public explorer instances for large templates, so the forward method (candidate tree to id) was the one that worked.

### What it means for C1 (inferred at height 1,886,343 from odiseus's tables and the identification; not a C1 run)

- **At 1,886,343, the p2s_with_key line is mostly bridge custody.** 2,669,998 of 2,907,738 ERG (91.82%) sits
  under the 6-of-10 template, and the bridge lock wallet adds 94,798 ERG (3.26%). Both are `threshold` in C1's
  terms (the `AtLeast` node is in the template, so every box of these templates has it). Inferred lower bound for
  the threshold class at 1,886,343: 2,764,796 ERG, 95.08% of p2s_with_key. q1 filed the first under `prove_dlog`
  and the second under `create_prove_dlog`: its indicator rows say nothing about multisig.
- **At 1,886,343, the DH row undercounts.** q1's `create_prove_dh_tuple` row there is 47 boxes and 17.663 ERG.
  The mixer's full-mix template alone, filed by q1 under `create_prove_dlog`, has a `proveDHTuple` node in its
  template and holds 46,996.792 ERG in 941 boxes at that height. Inferred lower bound for DH-bearing value at
  1,886,343: 47,014.456 ERG (the two sets are disjoint). The separate, measured figure from the stale state at
  836,808 is in `../c1-validation-836808/`; it is not a tip number.
- For C2/C3: the quantum-relevant value outside P2PK at 1,886,343 is chiefly one custody multisig with constant
  keys (keys visible from the moment the box exists, C5's second class), which is the case C3's hash-based
  threshold lock would have to replace.
