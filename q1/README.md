# Q1: UTXO-set scan for quantum-exposed ERG and tokens (DRY RUN at height 753934)

**This is a dry run, not the Q1 result.** The local node's UTXO state was at height 753,934 while the network tip
(`maxPeerHeight` in `out/node-info.json`) was 1,885,567. The scan validates the scanner end to end against a real
state; it does not describe today's chain. Age buckets are relative to the scanned height, so every bucket at or
above 788,400 blocks is empty by construction. The final run repeats this procedure when the node reaches the tip.

## What it does

`Scan.scala` opens a copy of the node's state database with the node's own classes (`scorex.db.LDBVersionedStore`,
`VersionedLDBAVLStorage.fetch`) and walks the authenticated AVL+ tree from the stored root. It recomputes every node
label (leaf: `blake2b256(0 ++ key ++ value ++ nextLeafKey)`; internal: `blake2b256(1 ++ balance ++ left ++ right)`),
so the set of boxes is the one the root digest commits to. Each leaf is parsed with
`org.ergoplatform.wallet.boxes.ErgoBoxSerializer`. The tree's sentinel leaf is skipped and counted.

Classification of each box's ErgoTree, first match wins:

| category | rule |
|---|---|
| `protocol` | box id is a genesis box (`ErgoState.genesisBoxes`), or tree bytes equal `ErgoTreePredef.emissionBoxProp` / `foundationScript`, or `ReemissionRules.reemissionBoxProp` / `payToReemission` (mainnet settings from the jar) |
| `unparseable` | sigma could not parse the tree |
| `p2pk` | 36 bytes, `00 08 cd` + 33-byte point |
| `mining_reward` | bytes equal `ErgoTreePredef.rewardOutputScript(720, pk)` with the 33-byte key slot wildcarded |
| `p2sh` | bytes equal `Pay2SHAddress(script).script` with the 24-byte hash slot wildcarded |
| `p2pk_other` | proposition is `SigmaPropConstant(ProveDlog)` or `CreateProveDlog(GroupElementConstant)` |
| `p2s_with_key` | proposition or constants contain a `ProveDlog`, `ProveDHTuple`, `CreateProveDlog`, `CreateProveDHTuple` node or a GroupElement value |
| `p2s_no_key` | everything else |

"Exposed" = `p2pk + p2pk_other + mining_reward + p2s_with_key`. Age = scanned height minus the box's
`creationHeight`. The scan exits non-zero if any label mismatches, if the traversed root differs from the stored
root, or if either supply check fails.

**Supply check, contradiction with the brief.** The brief said the box values must sum to exactly 97,739,924 ERG. They
sum to 97,739,925 ERG, which equals the sum of the node's own genesis boxes and `emissionRules.coinsTotal`. The
extra 1 ERG is the genesis no-premine-proof box (`b8ce8cfe...`, tree `10010100d17300` = `sigmaProp(false)`, so it
cannot be spent). Excluding that box, the sum is exactly 97,739,924 ERG. The scan prints and enforces both checks.

## Run

Stop the node first. `run.sh` refuses to run while `java ... ergo-6.0.6.jar` is running. It copies the state
directory to `q1/work/`, scans the copy, and deletes the copy, so the node's own database is never opened.

```bash
bash q1/run.sh /home/scott/bin/ergo-node/.ergo/state      # tables to stdout, CSVs to q1/out/
bash q1/check-header.sh                                     # with the node running again: header stateRoot vs traversed root
```

Pinned: `ergo-6.0.6.jar` (sha256 `21b9023933b19b98b7eb4d50cb78bcb6c827a0fe65711a00ceaf1b83f8f3a323`, checked by
`run.sh`) is the only classpath entry. Compiled with `scalac 2.12.20` via coursier (the scala-library version the jar
bundles). OpenJDK 21.0.12.1. `scan.conf` is an empty settings file. With it, `ErgoSettingsReader` loads the jar's
mainnet defaults.

## Dry-run record

- `/info` just before stopping the node (`out/node-info.json`): fullHeight 753922, bestFullHeaderId
  `83440115f4d163039f4d89498713872006b54defe351d1fe9b6f48cdb086935a`, stateRoot
  `4bf585fcaf5390abc15218bee3d8d07579fe54e8ebb234c6af60c60f572e3b3318`. The node applied 12 more blocks before it
  exited, so the scanned state is at 753934, header `f0319553c8b03489131ed2bef97c4b1e83d804bb4e893c0799d574249e3abcf3`.
  `check-header.sh` compares the traversed root with that header's stateRoot as served by the restarted node:

```
scanned state header id:            f0319553c8b03489131ed2bef97c4b1e83d804bb4e893c0799d574249e3abcf3
header height / stateRoot (node):   753934 481ae8c3b84f6e44983523eb4524e3bf0e2d818e76ca2a6338d40544caf86da618
traversed root digest (scan):       481ae8c3b84f6e44983523eb4524e3bf0e2d818e76ca2a6338d40544caf86da618
header stateRoot == traversed root: True
/info before stop: fullHeight=753922 bestFullHeaderId=83440115f4d163039f4d89498713872006b54defe351d1fe9b6f48cdb086935a stateRoot=4bf585fcaf5390abc15218bee3d8d07579fe54e8ebb234c6af60c60f572e3b3318
/info stateRoot == traversed root:  False  (blocks applied between /info and stop: 12)
```

- Two runs, stdout identical. Wall-clock times from `run.sh` (seconds):

```
run1:
wall-clock seconds: copy 2, scan 57
run2:
wall-clock seconds: copy 1, scan 55
diff run1 run2 stdout: identical
```

## Output (second run, verbatim; also `out/scan-output.txt`)

```
# Q1 UTXO scan (ergo-6.0.6.jar classes; traversal of the authenticated AVL+ tree)
# mining_reward template: rewardOutputScript(minerRewardDelay=720, pk), 54 bytes, key slot at offset 7
# p2sh template: Pay2SHAddress script, 44 bytes, hash slot at offset 17
# genesis boxes (ErgoState.genesisBoxes): emission b69575e11c5c43400bfead5976ee0d6245a1168396b2e2a4f384691f275d501c value=93409132500000000 tree=101004020e361002...; no_premine_proof b8ce8cfe331e5eadfb0783bdc375c94413433f65e1e45857d71550d42e4d83bd value=1000000000 tree=10010100d17300...; foundation 5527430474b673e4aafb08e0079c639de23e6a17e87edd00f78662b43c88aeda value=4330791500000000 tree=100e040004c09440...
# genesis sum = 97739925000000000 nanoERG; emissionRules.coinsTotal = 97739925000000000
# state context height (tip used for ages): 753934
# state context last header id: f0319553c8b03489131ed2bef97c4b1e83d804bb4e893c0799d574249e3abcf3
# state store version: 481ae8c3b84f6e44983523eb4524e3bf0e2d818e76ca2a6338d40544caf86da618
# age bucket thresholds (blocks): 131400, 262800, 525600, 788400, 1051200  buckets: <131400 | 131400-262799 | 262800-525599 | 525600-788399 | 788400-1051199 | >=1051200
# nodes visited: 2985403, label mismatches: 0, sentinel leaves: 1, box id != leaf key: 0
# boxes with creationHeight > tip: 0, max creationHeight: 753934

stored root digest:    481ae8c3b84f6e44983523eb4524e3bf0e2d818e76ca2a6338d40544caf86da618
traversed root digest: 481ae8c3b84f6e44983523eb4524e3bf0e2d818e76ca2a6338d40544caf86da618  match=true
total boxes: 1492701  total box bytes: 134651028
supply check: sum of all box values = 97739925000000000 nanoERG = 97739925.000000000 ERG; genesis sum = 97739925000000000; equal=true
supply check: sum excluding the no-premine-proof box (b8ce8cfe331e5ead..., 1000000000 nanoERG, present=true) = 97739924000000000 nanoERG = 97739924.000000000 ERG; brief figure 97739924000000000; equal=true

== By category ==
category                                               boxes                 ERG  pct_supply  pct_supply_ex_protocol  boxes_with_tokens  distinct_token_ids
p2pk                                                 1463099  51523422.778083379     52.7148                 95.9318             148946               36353
p2pk_other                                                 0         0.000000000      0.0000                  0.0000                  0                   0
mining_reward                                          15722    276008.099284001      0.2824                  0.5139                 16                  17
p2sh                                                       0         0.000000000      0.0000                  0.0000                  0                   0
protocol                                                   9  44031545.718690072     45.0497                       -                  6                  16
p2s_with_key                                            6637     51967.123901479      0.0532                  0.0968               5398                2451
p2s_no_key                                              7233   1856981.279041069      1.8999                  3.4575               5935                 910
unparseable                                                1         0.001000000      0.0000                  0.0000                  0                   0
EXPOSED(p2pk+p2pk_other+mining_reward+p2s_with_key)  1485458  51851398.001268859     53.0504                 96.5425             154360               38700
TOTAL                                                1492701  97739925.000000000    100.0000                100.0000             160301               39363

== Protocol boxes ==
protocol_box      boxes                 ERG  tree_key_indicator    register_key_indicator
emission              1  42768825.000000000   create_prove_dlog                         -
foundation            7   1262719.718690072                   -  R4:serialized_prove_dlog
no_premine_proof      1         1.000000000                   -                         -

== p2s_with_key by first key indicator found ==
indicator              boxes              ERG
create_prove_dh_tuple     58     17.146500000
create_prove_dlog       3927  45198.378460000
group_element_value        5      0.050000000
prove_dlog              2647   6751.548941479

== p2s_with_key: top 10 script templates by ERG (of 234 distinct; template = blake2b256(ErgoTree.template), first 8 bytes) ==
template          boxes              ERG  first_key_indicator
441438d8b1a847e8   1071  43537.005000000    create_prove_dlog
842e6165a18b3a28     12   4058.272900000           prove_dlog
7d507235e5dd3e05     66   1164.000000000    create_prove_dlog
c439d478a39c8457     17    718.947230970           prove_dlog
ea5f97f7597b325f      3    580.230000000           prove_dlog
5153fa5abfba5094     20    507.117127060           prove_dlog
d36ad138f86dd4a7      8    287.882250000    create_prove_dlog
61c7b9a8765bcfb4      4    203.704000819           prove_dlog
75833402a4b7d760     20    197.204000000           prove_dlog
bd35823b2ded0f9b     92     84.307500000    create_prove_dlog

== p2s_no_key: top 10 script templates by ERG (of 342 distinct; template = blake2b256(ErgoTree.template), first 8 bytes) ==
template          boxes                ERG  first_key_indicator
c7709a676c759d63      2  1323098.913505748                    -
850f2d5b02b3e666     62   520876.606849715                    -
bff7d38d6ae0f207      2    10250.093406380                    -
91a2f80777b42d1d    240     1494.996000000                    -
84e5e6c0db984157    659      668.798000000                    -
c5b42041b47633fa     18      231.054000000                    -
77dd972f4b409269      1       79.893910269                    -
a8c36eea8a185e24      1       66.000000000                    -
d14aba1223ecfdb4      4       49.995050000                    -
ac953af5d3571744      5       29.200000000                    -

== By category x age bucket (age = tip - creationHeight, blocks) ==
category           age_bucket   boxes                 ERG
p2pk                  <131400  962897  18591768.286484727
p2pk            131400-262799  437768   8494027.557659882
p2pk            262800-525599   32938  15284159.286965012
p2pk            525600-788399   29496   9153467.646973758
p2pk           788400-1051199       0         0.000000000
p2pk                >=1051200       0         0.000000000
p2pk_other            <131400       0         0.000000000
p2pk_other      131400-262799       0         0.000000000
p2pk_other      262800-525599       0         0.000000000
p2pk_other      525600-788399       0         0.000000000
p2pk_other     788400-1051199       0         0.000000000
p2pk_other          >=1051200       0         0.000000000
mining_reward         <131400   10005    158695.166884487
mining_reward   131400-262799    4715     99858.610900054
mining_reward   262800-525599     864      8476.759599460
mining_reward   525600-788399     138      8977.561900000
mining_reward  788400-1051199       0         0.000000000
mining_reward       >=1051200       0         0.000000000
p2sh                  <131400       0         0.000000000
p2sh            131400-262799       0         0.000000000
p2sh            262800-525599       0         0.000000000
p2sh            525600-788399       0         0.000000000
p2sh           788400-1051199       0         0.000000000
p2sh                >=1051200       0         0.000000000
protocol              <131400       4  44031544.678690072
protocol        131400-262799       3         0.030000000
protocol        262800-525599       1         0.010000000
protocol        525600-788399       1         1.000000000
protocol       788400-1051199       0         0.000000000
protocol            >=1051200       0         0.000000000
p2s_with_key          <131400    3932      3651.242538141
p2s_with_key    131400-262799    1356     14088.791713802
p2s_with_key    262800-525599    1188     33067.245249536
p2s_with_key    525600-788399     161      1159.844400000
p2s_with_key   788400-1051199       0         0.000000000
p2s_with_key        >=1051200       0         0.000000000
p2s_no_key            <131400    6664   1584067.404986803
p2s_no_key      131400-262799     382        72.781390000
p2s_no_key      262800-525599     134       176.528617045
p2s_no_key      525600-788399      53    272664.564047221
p2s_no_key     788400-1051199       0         0.000000000
p2s_no_key          >=1051200       0         0.000000000
unparseable           <131400       0         0.000000000
unparseable     131400-262799       1         0.001000000
unparseable     262800-525599       0         0.000000000
unparseable     525600-788399       0         0.000000000
unparseable    788400-1051199       0         0.000000000
unparseable         >=1051200       0         0.000000000
EXPOSED               <131400  976834  18754114.695907355
EXPOSED         131400-262799  443839   8607974.960273738
EXPOSED         262800-525599   34990  15325703.291814008
EXPOSED         525600-788399   29795   9163605.053273758
EXPOSED        788400-1051199       0         0.000000000
EXPOSED             >=1051200       0         0.000000000

exposed and storage-rent eligible (age >= 1051200 blocks): boxes=0 ERG=0.000000000 (0.0000% of supply, 0.0000% ex protocol)

== Top 20 token ids in exposed categories, by number of holding boxes ==
token_id                                                          boxes          raw_amount
0779ec04f2fae64e87418a1ad917639d4668f78484f45df962b0dec14a2591d2  75362          4989345031
ef802b475c06189fdbf844153cdc1d449a5ba87cce13d11bb47b5a539f27f12b  20817   95590324206308898
30974274078845f263b4f21787e33cc99e9ec19a17ad85a5bc6da2cca91c5a2e  20521   42391890740106929
fbbaac7337d051c10fc3da0ccb864f4d32d40027551e1c3ea3ce361f39b91e40  13345           957006095
472c3d4ecaa08fb7392ff041ee2e6af75f4a558810a74b28600549d5392810e8  12965     984889311310188
e91cbc48016eb390f8f872aa2962772863e2e840708517d1ab85e57451f91bed  12359            52939702
0cd8c9f416e5b1ca9f986a7f10a84191dfb85941619e49e53c0dc30ebf83324b  11894         20550517332
36aba4b4a97b65be491cf9f5ca57b5408b0da8d0194f30ec8330d1e8946161c1   4183              408583
4f5c05967a2a68d5fe0cdd7a688289f5b1a8aef7d24cab71c20ab8896068e0a8   2984     449947967046007
003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0   2419          1362803669
fa6326a26334f5e933b96470b53b45083374f71912b0d7597f00c2c7ebeb5da6   1761         21703473120
5a34d53ca483924b9a6aa0c771f11888881b516a8d1a9cdc535d063fe26d065e   1605    1861161074507085
1c51c3a53abfe87e6db9a03c649e8360f255ffc4bd34303d30fc7db23ae551db   1425       1170482404943
03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04   1423            51750881
1a6a8c16e4b1cc9d73d03183565cfb8e79dd84198cb66beeed7d3463e0da2b98   1347        199999379391
303f39026572bcb4060b51fafc93787a236bb243744babaa99fceb833d61e198   1268         78237684765
e249780a22e14279357103749102d0a7033e0459d10b7f277356522ae9df779c    820      39303960160215
d71693c49a84fbbecd4908c94813b46514b18b67a99952dc1e6e4791556de413    730           569199581
00b1e236b60b95c2c6f8007a9d89bc460fc9e78f98b09faec9449007b40bccf3    727       2090825934351
699a7fcc9978340acf5f8d4b7a43b1d21c0e82182792fe10ec43c032cfcd1d62    593  100000000000000000

== Top 20 token ids in exposed categories, by raw amount ==
token_id                                                                   raw_amount  boxes
17c21d0dcde99d552a6430c9d96fae3247d88bc484306333060b46e2af7e953f  9223372036854774807      1
19e5b066e46094f99c39564208995fc0544f7a452082e2aaa1b5b090a7f104b9  9223372036854774807      1
4aa1e892c8b6d8ff5acd0f3c8a77975b3851f32aa9298c2acc9daafa8fbd7624  9223372036854774807      1
a0fddcb960e2a4b82b7c7647058485338e38d8f4c6d4f07a568e0765784c98b8  9223372036854774807      1
dca5ced7c814761c9d0a75509d884e46e971ffaaa5497f4bf9476f4f35cfeb56  9223372036854774807      1
eabfa0c3ee84692c1f37dcb4b36d182e2cb971dffa6792cae18cf54c9f7f4693  9223372036854774807      1
29c231e5ed1174223a15575104b954524eb2c91baabb65732144a92b222033e4  4500000000000000000      2
aa9011d6e69b96b9bd734cebe8a64a776bd49f2db98a4acb1c8d3108cd23b662  2000000000000000000      1
20b22d9b4ea1b4ee0c46f16fafa8a6eea20812e566f2291efbc29d1836884e55  1234567890123456800      1
a07f38e5b37d67bb18f68a79a615567b3627055f48f3fcbc26f147a98cac70ba  1234567890123456800      1
b21f9d034e0296fa54f85fede94c1c3323b1d52a77ba1eba9fb8ecb0ec810a3d  1234567890123456800      1
eb41912d6e04773acdf12e669d21a7c5925ee8e09fd1e2f56c7cd6dc529a3ee6  1234567890123456800      1
0c1ae0ed8307abf191719dbb5fe16f54342dee973e56635a0d8d4c83f4dd43c4  1234567890123456789      1
131d726c5e190ef1d4a47a8fd581ac916105ebcc8169f8461835aff200108421  1234567890123456789      1
2170179acb579cddf144bfc44cfbdb967cb26255c761b7cd46564f03110db8cc  1234567890123456789      1
24a370194722bf9a16c9ba0f28cd4fe7325a1aeb289f35aebedd562ed6ab7866  1234567890123456789      1
36af2332458f4758891aef53edf9dce0915ba8f8b97db6a005004b6b0af793e4  1234567890123456789      1
3b03cf193ca58f65374fc9d55a2a542224758580889eb0cdb8f351974d064118  1234567890123456789      1
4b83a45f55691a976ceb0fdadbe05e891c317849d7ae2207918e1a46298e3e0d  1234567890123456789      1
4c93c2304a66e64fce0f71e8b21227aa1400b71fd82e8759c193e2a4bb4eafa5  1234567890123456789      1

== Top 20 boxes by value in exposed categories ==
[20 rows redacted from this file on 2026-10-01: box ids with the largest exposed balances are a target list.
 The scan now prints this table only with Q1_TOP_BOXES=1. The run that produced this file printed it.]
```

CSV files in `out/`: `by_category.csv`, `by_category_age.csv`, `protocol.csv`, `p2s_with_key_indicators.csv`,
`p2s_with_key_top_templates.csv`, `p2s_no_key_top_templates.csv`, `top_tokens_by_boxes.csv`,
`top_tokens_by_amount.csv`, `totals.csv` (`top_boxes.csv` only with `Q1_TOP_BOXES=1`).
