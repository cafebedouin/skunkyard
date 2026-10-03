# SK-029 result: many-time hash-based keys on a devnet and on public testnet

Runs 2026-10-02 on the peeryard rig (one mining node, `ergo-6.0.6.jar`, `--devnet`, block version 4, 2-second
blocks), hook `manytime.sh`, driver `ManyTime.scala` on sigma-state 6.0.7; WOTS n = 32, w = 16 (67 chains, 2,144-byte
signature), h = 4 (16 leaves); funding 1 ERG with R4 = 0, each spend pays 0.1 ERG out and recreates the box.
Devnet fixed charge for 1 input and 3 outputs: 10,000 + 2,000 + 300 = 12,300 (mainnet: 13,003 + 298 = 13,301).

## Runs 5 and 6: the v2 rules on the devnet, plain and hybrid, 2026-10-03, both PASS with printed verdicts

After the five seats on the first reply draft (`posts/REVIEW-manytime-reply.md`), the script's rules changed
(`manytime.es`, commit 2f88c9f): a box with no R4 reads as index 0, so a plain payment to the address funds a
usable box; the spend names its leaf (context var 2) and may use any leaf at or above the box's index; the
continuing box must carry an index above the leaf used (unless the leaf was the last). The hook funds box 0 with a
plain payment in the testnet run (run 7); on the devnet the hook still funds box 0 with R4 = 0, and after the first spend funds a second plain box at the same address, which is the devnet's plain-payment witness. The driver sets the
recreated box's creation height to the current height. Logs: `runs/manytime-v2rules-20261003.log`,
`runs/manytime-v2rules-hybrid-20261003.log`. Tree 934 bytes (973 hybrid); box 975 to 977 (1,014 to 1,016); spend
3,477 (3,572) bytes.

| spend | box R4 before | what it does | plain: node verdict, cost | hybrid: node verdict, cost |
|---|---|---|---|---|
| nodlog | absent (0) | valid hash signature, no curve proof | n/a | rejected, `Success((false,38282))` |
| forged | absent (0) | one signature bit flipped | rejected, 37,916 | rejected, 37,749 |
| wrongindex | absent (0) | recreated box keeps index 0 | rejected, 52 | rejected, 54 |
| valid, leaf 0 | absent (0) | recreates with R4 = 1 | confirmed, 37,644 (mempool 49,944) | confirmed, 38,159 (mempool 50,459) |
| staleleaf | 1 | leaf 0 signed again against R4 = 1 (leaf below the index) | rejected, `Success((false,28))`, no exception now: `leaf >= i` fails before the lookup | rejected, 30 |
| below | 1 | leaf 0 named explicitly against R4 = 1 | rejected (script check) | rejected (script check) |
| skip, leaf 3 | 1 | leaf 3 ≥ 1, recreates with R4 = 4 | confirmed, 37,876 (mempool 50,176); R4 read `0408` | confirmed, 38,072 |
| second plain box, leaf 4 | absent (0) | a new plain payment to the address, spent with the wallet's next leaf 4, R4 = 5 | confirmed, 37,779 (mempool 50,079) | confirmed, 38,209 |

Verdict lines as printed: `MANYTIME: PASS (mode=manytime ... below_rejected=yes spend0_confirmed=yes
skip_spend_confirmed=yes second_plain_box_confirmed=yes)` and the same for `mode=hybrid` with
`nodlog_rejected=yes`. The costs of the valid spends vary with the message (37,644 to 37,876 plain); the many-time
machinery is not separable from that variation; the wrong-index and stale-leaf rejections cost 28 to 54 units.

What the v2 rules change, in one line each: a plain payment is spendable (run 5, box 0 and the second box); a box
at index i refuses any leaf below i (stale and below) and accepts any leaf at or above it (skip), so a stuck spend
is replaced with the next leaf and several boxes of one key set are driven by one wallet counter; the chain
enforces the index per box, the wallet keeps the counter per key set.

## Run 7: the v2 rules on public testnet, `testnet/v2-artifacts/run-v2.log`, PASS

2026-10-03 01:25 to 01:30 UTC, the same public testnet node (ergo 6.0.1, block version 4), a fresh 16-leaf key
set, box 0 funded by a plain payment with no register (transaction
`c4b2d677a82f5e3fd647c27067635aaf6d24e413c8968f84a2fcfa534413caaa`, box
`c5bff21b6020af06277b3298e7e95ab60aaafb5d700340322c544e3d33321ce1`), 1 ERG. Every round's node response and the
driver's figures are in `testnet/v2-artifacts/` (`tx_*.json`, `*.body`, `spend_*.err`, `box-*.json`). Box 977 to 979
bytes; every spend 3,484 bytes.

| spend | box R4 before | node verdict | script cost | artifact |
|---|---|---|---|---|
| forged | absent (0) | rejected, `Success((false,37854))` | 37,854 | |
| wrongindex | absent (0) | rejected, `Success((false,52))` | 52 | |
| valid, leaf 0 | absent (0) | confirmed, R4 → 1, creation height 577,730 | 37,854 | tx `e9d0108c08259bb4cbf09275bffeb75618b9e51c46180d0a1a674698d6328359`, box `53c93614cf2ae16ef71e1e3f2287da10ee4507c511d5d6e652547b457820dc3f` |
| staleleaf (leaf 0 signed again) | 1 | rejected, `Success((false,28))` | 28 | |
| below (leaf 0 named) | 1 | rejected, `Success((false,28))` | 28 | |
| skip, leaf 3 | 1 | confirmed, R4 → 4 (`0408`), creation height 577,733 | 37,781 | tx `118c911e57a9bace5efd30ffda96c481e6fa0d8467dd0711fb91c28f84530251`, box `9c80ebb0934fff52ffaccd8d4f14b6c1753fe138117cb03ddb843f2b6c2ee533` |

Verdict line as printed: `TESTNET-MANYTIME: forged_rejected=yes wrongindex_rejected=yes valid0_confirmed=yes
staleleaf_rejected=yes below_rejected=yes skip_leaf3_confirmed=yes`. The box carrying index 4 is left unspent on
testnet. Devnet and testnet agree on every verdict and on the rejection costs; the valid spends differ by the
message-dependent hash count.

## Run 8: v3, the singleton design, on the devnet, `runs/singleton-20261003.log`, PASS

After the second seat round on the reply draft (`posts/REVIEW-manytime-reply.md`, round 2): under the v2 rules the
index was enforced per box, so a fresh box at the same address (any plain payment) started at 0 and accepted a leaf
another box had used; the one-time property across a key set rested on the wallet's counter. v3 moves the index
into one box per key set. `state.es`: the singleton, marked by a token of supply 1 minted once per key set (its id
is a constant of both scripts); SELF and OUTPUTS(0) must carry the token; the v2 rules otherwise (missing R4 reads
0, the spend names a leaf at or above the index, the continuing box carries an index above it; on the last leaf
OUTPUTS(0) may be any script, so the token can move to a new key set's singleton); the message covers every input
id and every output. `deposit.es` (61 bytes): a box here is spendable only in a transaction that also spends a box
carrying the token. Deposits are plain payments to the deposit address; the state address is never published.
Driver `Singleton.scala`, hook `singleton.sh`. One mining node, ergo 6.0.6, block version 4; n = 32, w = 16,
h = 4; the wallet issued the token (`1c41655b…`, height 19) and funded, in one transaction at height 21, the
singleton S0 (token, R4 = 0), two plain deposits D1 and D2 and a plain box P0 at the state address without the
token. State tree 1,026 bytes; singleton box 1,102 bytes; deposit box 102 bytes.

| round | inputs | what | node verdict | script cost |
|---|---|---|---|---|
| forged | S0 | one signature bit flipped | rejected, `Success((false,37904))` | 37,904 |
| wrongindex | S0 | continuing box keeps index 0 | rejected, `Success((false,73))` | 73 |
| nostate | D1 | a deposit spent alone, no singleton in the transaction | rejected, `Success((false,7))` | 7 |
| addinput | S0 + D1 | signed over S0 alone, posted with D1 added | rejected, `Success((false,37602))` | 37,602 |
| notoken | P0 | a box at the state address without the token, valid signature | rejected, `Success((false,23))` | 23 |
| valid, leaf 0 | S0 + D1 | sweep D1, pay 0.1 ERG, recreate S1 with R4 = 1 | confirmed at height 32, D1 gone from the UTXO set | 38,007 (state 37,996 + deposit 11); mempool 52,707 |
| staleleaf | S1 | leaf 0 again against index 1 | rejected, `Success((false,46))` | 46 |
| skip, leaf 3 | S1 + D2 | sweep D2, recreate S2 with R4 = 4 | confirmed, S2 R4 `0408` with the token, D2 gone | 38,204 (state 38,193 + deposit 11); mempool 52,904 |

Every spend with one deposit is 3,637 bytes (the 1,102-byte singleton rides along; the deposit input adds its 32-byte
id and an empty proof). Verdict line: `SINGLETON: PASS (forged_rejected=yes wrongindex_rejected=yes
nostate_rejected=yes addinput_rejected=yes notoken_rejected=yes spend0_confirmed=yes staleleaf_rejected=yes
skip_spend_confirmed=yes deposit1_spent=yes deposit2_spent=yes)`. What run 8 adds to runs 5 to 7: the counter is
one per key set and the chain enforces it for every box the key set owns, because nothing at the deposit address
moves without the singleton; a used leaf cannot be replayed on a fresh deposit (nostate: 7 units); a signed
transaction cannot be padded with a deposit (addinput); a plain payment to the state address is inert (notoken).
Not run: the last-leaf branch (the token moving to a new key set), heights above 4, several deposits in one spend,
a bad lookup proof at a legal index (still the exception path, by reading), hybrid mode under v3.

## Run 9: v3 on public testnet, `testnet/v3-artifacts-run9/run-v3.log`, PASS

2026-10-03 01:58 to 02:03 UTC, the same public testnet node (ergo 6.0.1, block version 4), a fresh 16-leaf key set.
The project's testnet wallet minted the token (`f60cfae9…`, box `79946aa7…`, through Fleet's `mintToken`), the
scripts were compiled with it, and one Fleet transaction (`5147e6a0…`) funded S0 (1 ERG, token, R4 = 0), D1 and D2
(0.3 ERG each, plain payments to the deposit address) and P0 (0.3 ERG, plain, at the state address). Every node
response and driver line is in `testnet/v3-artifacts-run9/`. Singleton box 1,104 bytes, deposit box 104; every spend
with one deposit 3,644 bytes.

| round | inputs | node verdict | script cost | artifact |
|---|---|---|---|---|
| forged | S0 | rejected, `Success((false,37915))` | 37,915 | |
| wrongindex | S0 | rejected, `Success((false,73))` | 73 | |
| nostate | D1 | rejected, `Success((false,7))` | 7 | |
| addinput | S0 + D1 | rejected, `Success((false,37997))` | 37,997 | |
| notoken | P0 | rejected, `Success((false,23))` | 23 | |
| valid, leaf 0 | S0 + D1 | confirmed; S1 R4 `0402` with the token, creation height 577,790; D1 gone | 37,786 | tx `1ccc214bdb96d64e6f56cc51c40c90fc4c30cb84dd7e00b15f4f349a592bd40f`, box `a7b813ac67ff9473d7f58e51be2f49fa472dc99f33bad8d4fdaad7796b1dff47` |
| staleleaf | S1 | rejected, `Success((false,46))` | 46 | |
| skip, leaf 3 | S1 + D2 | confirmed; S2 R4 `0408` with the token, creation height 577,793; D2 gone | 37,762 | tx `f08692435c16f283bee3ac8e15f83370da14c63bba96c9965cd1d47730c4844d`, box `f87401e1b6254964a090e05bd5583f5f65c6e8ab2cd61164a6a7f4630525c79e` |

Verdict line: `TESTNET-SINGLETON: forged_rejected=yes wrongindex_rejected=yes nostate_rejected=yes
addinput_rejected=yes notoken_rejected=yes valid0_confirmed=yes deposit1_spent=yes staleleaf_rejected=yes
skip_leaf3_confirmed=yes deposit2_spent=yes`. S2 (index 4, with the token) and P0 are left on testnet. Devnet and
testnet agree on every verdict and on every rejection cost but the forged and addinput ones, which carry the
message-dependent hash count.

## Run 10: v3.1 on the devnet, with rotation, `runs/singleton-v31-20261003.log`, PASS

After the third seat round (`posts/REVIEW-manytime-reply.md`, round 3). `state.es` v3.1: before the last leaf the
continuing index must also stay below the leaf count; on the last leaf OUTPUTS(0) must be neither this script nor the
deposit script (the deposit script's bytes are a constant of the state script); the message covers every data-input
id. The hook now generates a second key set B, compiled with the same token, whose deposit address is the same as
A's (printed: "key set B shares the deposit address"), and funds three deposits. Same rig, ergo 6.0.6, block version 4,
n = 32, w = 16, h = 4. State tree 1,131 bytes; singleton box 1,207; deposit box 102; every spend 3,742 bytes.

| round | inputs | what | node verdict | script cost |
|---|---|---|---|---|
| forged | S0 | one signature bit flipped | rejected, `Success((false,37913))` | 37,913 |
| wrongindex | S0 | continuing index stays 0 | rejected, `Success((false,75))` | 75 |
| nostate | D1 | a deposit alone | rejected, `Success((false,7))` | 7 |
| addinput | S0 + D1 | signed over S0 alone, posted with D1 | rejected, `Success((false,37737))` | 37,737 |
| notoken | P0 | the state address without the token | rejected, `Success((false,23))` | 23 |
| valid, leaf 0 | S0 + D1 | sweep D1, S1 at index 1 | confirmed, D1 gone | 38,141 (mempool 52,841) |
| staleleaf | S1 | leaf 0 against index 1 | rejected, `Success((false,46))` | 46 |
| skip, leaf 3 | S1 + D2 | sweep D2, S2 at index 4 | confirmed, S2 R4 `0408`, D2 gone | 38,179 (mempool 52,879) |
| overindex | S2 | leaf 4, continuing index written as 16 | rejected, `Success((false,84))` | 84 |
| lastsame | S2 | leaf 15, token kept under this script | rejected, `Success((false,65))` | 65 |
| lastdeposit | S2 | leaf 15, token sent to the deposit script | rejected, `Success((false,64))` | 64 |
| rotate | S2 | leaf 15, token to key set B's singleton at index 0 | confirmed, S3 under B's tree (`tree_is_B=yes`), R4 `0400` | 38,046 (mempool 50,746) |
| after rotation | S3 + D3 | key set B's leaf 0 sweeps D3 | confirmed, S4 R4 `0402`, D3 gone | 37,994 (mempool 52,694) |

Verdict line: `SINGLETON: PASS (… overindex_rejected=yes lastleaf_same_script_rejected=yes
lastleaf_to_deposit_rejected=yes rotate_confirmed=yes sweep_after_rotation_confirmed=yes deposit3_spent=yes)`.
What run 10 adds: the last-leaf branch ran (rotation to a second key set, SK-032), and a deposit made before the
rotation was swept by the second key set, so the deposit address survives a key-set change; the two ways a wallet
could have misused the last leaf, and the one way it could have stranded the token early, are refused at 64 to 84
units. The node's charge above script cost is 14,700 for two inputs and three outputs and 12,700 for one input and
three outputs, 400 above the input/output formula in both shapes (devnet inputCost 2,000, outputCost 100), which
by inference is token access (`tokenAccessCost` 100); the mainnet derivation adds the same 400.

## Run 11: v3.1 on public testnet, with rotation, `testnet/v3-artifacts/run-v31.log`, PASS

2026-10-03 02:16 to 02:27 UTC, the same public testnet node (ergo 6.0.1, block version 4), fresh key sets A and B
compiled with one token (`b9463e54…`, minted in its own transaction, box `5155b410…`); one funding transaction
(`1f86e5ef…`) for S0 (1 ERG, token, R4 = 0), D1, D2, D3 (0.3 ERG each, plain) and P0 (0.3 ERG, plain, at A's state
address). Artifacts in `testnet/v3-artifacts/`. Singleton box 1209 bytes, deposit box 104; every spend 3,749 bytes.

| round | inputs | node verdict | script cost | artifact |
|---|---|---|---|---|
| forged | S0 | rejected, `Success((false,37918))` | 37,918 | |
| wrongindex | S0 | rejected, `Success((false,75))` | 75 | |
| nostate | D1 | rejected, `Success((false,7))` | 7 | |
| addinput | S0 + D1 | rejected, `Success((false,37948))` | 37,948 | |
| notoken | P0 | rejected, `Success((false,23))` | 23 | |
| valid, leaf 0 | S0 + D1 | confirmed; S1 R4 `0402`, token, creation height 577,813; D1 gone | 37,959 | tx `908e055e53d85c65f662358d884b65968fcdcf0596d0241e87873c03a7a1f984` |
| staleleaf | S1 | rejected, `Success((false,46))` | 46 | |
| skip, leaf 3 | S1 + D2 | confirmed; S2 R4 `0408`, token, height 577,816; D2 gone | 37,896 | tx `2c3675deb6602644e7b25d2229b1116fce7a5b06079c97af81e311d560d56390` |
| overindex | S2 | rejected, `Success((false,84))` | 84 | |
| lastsame | S2 | rejected, `Success((false,65))` | 65 | |
| lastdeposit | S2 | rejected, `Success((false,64))` | 64 | |
| rotate, leaf 15 | S2 | confirmed; S3 under key set B's tree (`tree_is_B True`), R4 `0400`, token, height 577,818 | 37,910 | tx `b88aa7569982de804fff39362b5386fc69de1d99bc0a70e8eba96f7e6d545874`, box `5e6b5bc2a78394e3bc5c5ab713bc062f2cf15eba4ae24ed57aed86f8f470c291` |
| after rotation, B's leaf 0 | S3 + D3 | confirmed; S4 R4 `0402`, token, height 577,822; D3 gone | 37,773 | tx `da38a18b7b33ee888f2cbf9455022aa963a736f98e7dfcbe62bba3a4fba3c316`, box `cb1b87b903a4da219a3229ef3f150338a645872acde82642b82046194d9cda6b` |

Verdict line: all sixteen flags `yes` (`TESTNET-SINGLETON: … rotate_confirmed=yes sweep_after_rotation_confirmed=yes
deposit3_spent=yes`). Devnet and testnet agree on every verdict and on every rejection cost except forged and
addinput (message-dependent). Left on testnet: S4 (key set B's singleton at index 1, holding the token), P0, and a
0.5 ERG deposit funded afterwards at the deposit address (`testnet/v3-artifacts/breakit-fund.log`, box
`6a09d6453c4ac2a0df692404426e922bd95647ab3082b089ecd9a0a5cef62168`) as the "break it" box: spending it without key
set B's next leaf is the challenge. Note on procedure: as in run 9, several transactions carrying a valid leaf-0
signature over distinct messages (wrongindex, addinput, notoken) were handed to the public node before the leaf-0
spend confirmed; harmless because nothing spent in that interval and the index then passed 0, which is the window
the design closes at confirmation.

## Earlier runs under the v1 rules (R4 required, leaf = index, index + 1)

## Run 1: the script as first written (`&&` with the verification first), `runs/manytime-v1-eager-20261002.log`, PASS

Tree 908 bytes; box 951 bytes; every spend 3,448 bytes (signature 2,144 and proof 187 in the extension, the recreated 951-byte box, the two other outputs and the transaction framing).

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| forged | 0 | one signature bit flipped | rejected, `Success((false,37777))` | 37,777 |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,37736))` | 37,736 |
| valid, leaf 0 | 0 | recreates with R4 = 1 | confirmed (mempool cost 50,097) | 37,797 |
| valid, leaf 1 | 1 | recreates with R4 = 2 | confirmed (mempool cost 50,062) | 37,762 |

The index advanced 0, 1, 2 on chain (R4 read `0400`, `0402`, `0404`). Both rejections paid the full WOTS cost: the
final `&&` had the chain computation on its left, and ErgoTree evaluates a `val` where it is used, so the state
check came second.

## Run 2: cheap checks first, and the stale-leaf case, `runs/manytime-v2-ordered-20261002.log`, PASS

The state check and the AVL lookup moved to the left of the `&&` with the WOTS block on its right, so the block
runs only when they pass. Tree 910 bytes; box 953 bytes; every spend 3,450 bytes (the same composition, two bytes more of script).

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| forged | 0 | one signature bit flipped | rejected, `Success((false,37860))` | 37,860 (the signature check is last, so a forged signature always pays the full chain computation) |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,38))` | **38** |
| valid, leaf 0 | 0 | recreates with R4 = 1 | confirmed (mempool cost 50,160) | 37,860 |
| staleleaf | 1 | leaf 0's signature and proof against R4 = 1 | rejected, `Failure(InvocationTargetException)` from `root.get(key 2, proof for key 1).get` | not reported (an exception, not `false`) |
| valid, leaf 1 | 1 | recreates with R4 = 2 | confirmed (mempool cost 50,049) | 37,749 |

Index on chain: 0, 1, 2 again. A spend that fails to advance the index is now turned away at a thousandth of the
cost of verifying it; a forged signature cannot be, since the verification is the check. The stale-leaf rejection
is by exception: the lookup key the script computes from `SELF.R4` is not the key the proof was built for, and
the expression `root.get(...).get` fails, whether inside the proof verification or as `None.get` the node's
message does not say. ErgoScript has no catch, so the rejection stays an exception; the node rejects it either way.

## Run 3: the hybrid, `proveDlog(ownerPk) && (many-time lock)`, `runs/manytime-hybrid-20261003.log`, every case as expected, no verdict line (the hook had a syntax error at its verdict, found by the seats and fixed; rerun as run 6)

`hybrid.es` is `manytime.es` with `proveDlog(ownerPk) &&` in front; the driver signs the sigma leaf with the
interpreter's own prover (`ProverInterpreter`, the owner's secret) and the hash side as before. Tree 949 bytes
(the 33-byte key plus the AND node); box 992 bytes; spend 3,545 bytes (the 56-byte Schnorr proof added).

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| nodlog | 0 | valid WOTS signature and proof, empty sigma proof | rejected, `Success((false,38351))`: the hash side passes in full, then the curve leaf has no proof | 38,351 |
| forged | 0 | one WOTS bit flipped, no sigma proof | rejected, `Success((false,37953))` | 37,953 |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,39))` | 39 |
| valid, leaf 0 | 0 | both proofs | confirmed (mempool cost 50,651), R4 → 1 | 38,351 |
| staleleaf | 1 | leaf 0 against R4 = 1 | rejected by exception, as in run 2 | not reported |
| valid, leaf 1 | 1 | both proofs | confirmed (mempool cost 50,563), R4 → 2 | 38,263 |

The AND costs about 500 units over the pure hash lock (the `proveDlog` leaf's 341 plus the conjunction) and 95
bytes. What the hybrid buys: a holder loses nothing today's key gives, since the curve key must still sign; what
it does not buy: protection of that curve key, which is as exposed as any P2PK key and whose compromise is
harmless only because the hash side is also required. The migration reading is the post's: hybrid now, hash-only
when the holder chooses.

## Run 4: public testnet under the v1 rules, `testnet/v1-artifacts/run.log`, PASS (the runner's round logs went to its own output capture, so costs and ids below are from `testnet/v1-artifacts/*.body` and `spend_*.err`, published with this result)

2026-10-03 00:56 to 01:01 UTC, through the Cornell testnet node (`http://128.253.41.110:9052`, ergo 6.0.1 testnet,
block version 4, API open), funded from the project's testnet wallet with `fund-any.mjs` (R4 = 0), the same 16-leaf
key set shape, `minerRewardDelay` 720. Box 955 bytes, tree 910 (the testnet prefix changes nothing but the address);
every spend 3,457 bytes. The recreated boxes carried the funding box's creation height (a driver choice, since fixed).

| spend | node verdict | script cost | artifact |
|---|---|---|---|
| forged | rejected, `Success((false,37997))` | 37,997 | |
| wrongindex | rejected, `Success((false,38))` | 38 | |
| valid, leaf 0 | confirmed, R4 → 1 | 37,997 | tx `8185de6dc06b28eecf8b1f6393e337ef1aa93c3b672579e823e86f552c49e6eb`, box `eb8987a55198cd1d402ce128e8c640a3654d21780c797ea233f85566232bf3f6` |
| staleleaf (against the new box) | rejected, `Failure(InvocationTargetException)` | not reported | |
| valid, leaf 1 | confirmed, R4 → 2 | 37,550 | tx `1634f45e8e96f52fa529e7df6a342f5034bcae7b7d774985093b6be849c8063e`, box `1b7823189bd260605a163e1d5c4593cec106b14ff7e1f951d15b1f4009df0fc0` |

Funding transaction `dc2cba875cc7486cb4293f0540fc23f9441acc18bfe9f1cf409f7ca304d9a042`, box
`bd12f74eb91f6daa98dc3cc53f34388d55c3ca39c8fe7531159951f490d1d35b`. The box carrying index 2 is left unspent on
testnet. Verdicts and costs match the devnet run to within the message-dependent WOTS variation.

## What it settles, in one table against the one-time pilot

| | one-time WOTS box (`q2`, the post) | many-time, v2 (runs 5 to 7) | many-time, v3.1 singleton (runs 10 and 11) |
|---|---|---|---|
| keys per box | 1 | 2^h (16 here; the digest is 33 bytes at any h) | 2^h per key set, one singleton plus any number of deposits; the deposit address survives rotation |
| proposition bytes | 840 (constant form) | 934 | 1,131 state, 61 deposit |
| box bytes | 866 (constant form, the post) | 975 to 979 | 1,207 to 1209 singleton, 102 to 104 deposit |
| spend bytes | 2,345 (testnet) / 2,340 (devnet) | 3,477 to 3,484 | 3,742 (devnet) to 3,749 (testnet) with one deposit |
| script cost, valid spend | 37,592 | 37,644 to 37,876 | devnet 37,994 to 38,179, testnet 37,773 to 37,959 (the deposit's script 11) |
| mainnet cost per spend (derived; 10,000 + 2,407 per input + 298 per output + 400 token access as the devnet charged) | 50,595 (37,592 + 13,003, 1 in / 2 out) | 51,177 (37,876 + 13,301, 1 in / 3 out) | 54,287 (38,179 + 15,708 + 400, 2 in / 3 out) |
| per block, by cost (8,001,091) / by size (1,271,009 bytes), derived, floors | 158 / 542 | 156 / 365 | 147 / 339 |
| index enforced by | n/a | the chain, per box; across boxes the wallet | the chain, per key set, while the token stays in a singleton (every spend passes through it); at the last leaf the token must leave to another script |

Cost-bound, like the pilot: the interpreter's WOTS cost dominates and the many-time machinery adds under two percent
(v3's second input adds 2,407 of fixed charge). The rent of the box that persists, derived at mainnet's factor of
1,250,000 nanoERG per byte per four years: 1.22 ERG for the v2 box (977 bytes), 1.38 ERG for the v3 singleton
(1,102 to 1,104 bytes); a v3 deposit box is 102 bytes and persists only until swept.

## Not shown, stated once

The index is public (R4 names the next leaf, the proof names the one used) and the unused commitments stay inside the digest: a used leaf's proof carries its own commitment and sibling hashes, nothing about unused leaves. This is not a hidden signer. The chain's index moves only when a spend
confirms; the wallet's counter must move when it signs, because a signature that never confirms (a replacement that
lost the race) is still public to whoever saw it, so the wallet keeps one counter per key set, never decremented, and
a wallet rebuilt from the chain skips ahead past the index by a margin (`LITERATURE.md`, refinements). Under v1 and
v2 the message bound `SELF.id` and the outputs; under v3 it binds every input id and every output, and under v3.1
every data-input id as well. The tree is built off chain and read-only; adding leaves is a different script.
