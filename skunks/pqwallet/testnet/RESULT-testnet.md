# pqwallet step 4: the quantum-day vault end to end on Ergo public testnet (2026-10-24)

**PASS.** Pass condition (`../CHARTER.md`, step 4): the transaction ids printed, a forged migration refused by the
node. Every transaction below was built, signed and submitted by TypeScript in this directory's parent
(`scripts/testnet-flow.ts`, `src/*.ts`); every hash-key signature came from `src/wotsplus.ts` under the on-disk
`UsedStore` (`used.json`), every secp signature from the testnet wallet's seed (Fleet's `Prover` for plain P2PK
inputs, sigmastate-js for the P2S flag box). The vault is `skunks/qvault/QVault2.es` (SK-055 variant 2, step 3's
shape) and the flag `skunks/qvault/QDay.es`, both unchanged; their trees were compiled once and pinned, and every
address below is a constant substitution into the pinned bytes (`src/vault-tree.ts`), never a per-key compile.

## Environment

- Node: `http://213.239.193.208:9052`, `/info`: `appVersion 6.0.8`, `network testnet`, `name ergo-testnet-6.0.8`,
  extra index on (`/blockchain/indexedHeight` = `fullHeight`), `/script/p2sAddress` and `/script/addressToTree`
  open without an API key (used once, to pin). Heights 605,262 (`keys`) to 605,271 (the last confirmation); testnet
  blocks about two minutes apart (confirmations 82 to 124 s after submission).
- Explorer: `https://api-testnet.ergoplatform.com/api/v1`, consulted only to check the lag: at the end of the run its
  `networkState.height` was 604,047 against the node's 605,271, and it did not yet know the first transaction. Every
  verdict and height here is the node's.
- Libraries: `@fleet-sdk/core` 0.12.0, `@fleet-sdk/wallet` 0.12.0, `@fleet-sdk/serializer` 0.11.0, `sigmastate-js`
  0.6.3 (the versions `skunks/oneshot` pins), `@noble/hashes` 2.4.0, `@scure/bip39` 2.4.0, Node v25.1.0, `tsx`.
- Wallet: the skunkyard testnet wallet `3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU` (`m/44'/429'/0'/0/0`),
  1.073 ERG before, 1.054 ERG after: 0.019 ERG used (0.01 ERG stays in the flag box; 0.004 ERG in wallet fees;
  0.005 ERG in vault-side fees and bounties). Budget was 0.3 ERG.
- Fees: 0.001 ERG on every wallet transaction and hash-key spend; the keyless transactions pay only their bounty to the
  fee contract (Fleet's `FEE_CONTRACT`, delay 720): 0.001 ERG (merge) and 0.002 ERG (lone forward).

## Trees: compiled once, pinned, substituted

`scripts/pin-trees.ts` compiled `QVault2.es` and `QDay.es` at the node (`/script/p2sAddress`, `treeVersion 1`: the
compiler the step-3 devnet run used; header `0x19`) with the mainnet schedule constants (PERIOD 1,051,200, WINDOW
21,600, PER_INPUT 500000L, REFRESH 2000000L, SLACK 10) and distinctive placeholder bytes for every per-owner constant
(`src/vault-tree.ts` `PLACEHOLDER`: blake2b256 of a label for the four 32-byte constants, the canonical test
mnemonic's EIP-3 keys 0 and 1 for OWNER and ORACLE, 777,777 for BACKSTOP). The tree decoded from the address was
checked against `/script/addressToTree`, each placeholder located, and the files written (`pin-trees.log`):

```
pin node=http://213.239.193.208:9052 appVersion=6.0.8 network=testnet height=605259
pin QVault2 tree_bytes=1351 header=0x19 address=3CBLnV6NzUMveeA2zKSTFVjr… (1852 chars)
pin QVault2 OWNER len=33 offsets=[89]
pin QVault2 QDAY_NFT len=32 offsets=[11]
pin QVault2 PKSEED len=32 offsets=[45]
pin QVault2 PKCOMMIT len=32 offsets=[345]
pin QVault2 SUCCESSOR len=32 offsets=[391]
pin QVault2 BACKSTOP len=3 offsets=[80,382]
pin QDay tree_bytes=153 header=0x19 address=2jFvbQvkJhoATbM4MJQkENqU… (216 chars)
pin QDay ORACLE len=33 offsets=[19]
pin QVault2 round_trip=true zeroed_blake2b256=000d534203e197ae5767520fdc588bc60e5360b3fa5ce40dad4b4195263fbe64
pin QDay round_trip=true zeroed_blake2b256=d4a783e7a105a61c3f0497e49089749edf06e9fbac041a484beb95cf2bc5fdd2
```

Files: `../trees/QVault2.tree` (1,351 bytes), `../trees/QDay.tree` (153 bytes), `../trees/pins.json` (offsets,
placeholders, hashes, compiler). `src/vault-tree.ts` asserts on every load that (a) each placeholder occurs exactly at
the pinned offsets and nowhere else, (b) every substituted value has the placeholder's length (BACKSTOP as a zigzag
VLQ: 900,000 and 777,777 are both three bytes, as is every height in 8,192 .. 1,048,575), and (c) substituting the
placeholder values reproduces the pinned file byte for byte (`round_trip=true` above). The pinned hashes are the
trees with every per-owner constant zeroed (BACKSTOP's three bytes too): **QVault2
`000d534203e197ae5767520fdc588bc60e5360b3fa5ce40dad4b4195263fbe64`, QDay
`d4a783e7a105a61c3f0497e49089749edf06e9fbac041a484beb95cf2bc5fdd2`**.

What the pin found that the source does not say: `$BACKSTOP` is written twice in `QVault2.es` (`beforeQday`,
`afterQday`) and the compiler emits two Int constants for it (offsets 80 and 382), so the builder writes both; the
other constants occur once. The Scala harness's `tree-constants` (sigma-state 6.0.7) reads the pinned QVault2 tree as
134 constants with `SInt 777777` at indices 5 and 118 and the five `Coll[Byte]` key constants at 2, 3, 8, 115, 121
(`tree-constants.log`). The mainnet-constant tree is 1,351 bytes against the devnet run's 1,346 (PERIOD and WINDOW
take three bytes each instead of one).

As a one-time witness that substitution gives what a compile would (not how addresses are built), each of the three
real trees was also compiled at the node from the substituted source and the addresses compared:

```
a: cross-check: QDay substituted tree == node compile for the demo oracle: true
b: cross-check: vault k+1 substituted tree == node compile for its constants: true
b: cross-check: vault k substituted tree == node compile for its constants: true
```

## Keys

One seed, both key families (the point of step 1): the testnet wallet's 24-word mnemonic gives the owner key
(`m/44'/429'/0'/0/0`), the **demo oracle** (`m/44'/429'/0'/0/1`, the same seed's next EIP-3 key: a stand-in, not an
oracle; the mainnet flag's governance is out of scope) and, through option B (`vaultKey('B', seed, 0, k)`), the WOTS+
hash keys of vault k (k = 0) and vault k+1 (k = 1):

```
keys: wallet 3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU (m/44'/429'/0'/0/0, pk 032d0c040f8ef24535cab2ee8529631bc60111095b3770dddc27f314aaca841a29)
keys: demo oracle pk 03b2ac547ab2a6645e7e365330a255fb9830f1251fef9a5e2ffa852feade984db9 (m/44'/429'/0'/0/1, the same seed: a demo, not an oracle)
keys: vault 0 hash key (option B, vaultKey('B', seed, 0, 0)): PKSEED 55215f53c4e2e74aa16aa7c86953f1f10ee163112127a47238857dfdb8ac4ed0 PKCOMMIT 522c3209d376e1b707821754995ae35f8d4dfd5471b4c84c167db53e283bceb1
keys: vault 1 hash key (option B, vaultKey('B', seed, 0, 1)): PKSEED 64793ea6f47eb5864b7130f2110da5c049ed8a16c1a9a2ecfdf3551612bb9c20 PKCOMMIT d409055e888d1de11c1846a3c9d93d4ffa447479b782ba4217efe881fc823f2b
```

BACKSTOP 900,000 for both vaults (about 295,000 blocks ahead, roughly 410 days at two-minute blocks).

## The flow, as printed (`lines.txt`; full log `run.log`; each transaction as submitted with the node's answer in `txs/`)

**a. The flag.** The NFT (supply 1, id = the first input's box id) minted straight into the QDay box with `R4 = 0100`
(Boolean false), ORACLE = the demo oracle:

```
a: QDay tree 153 bytes, address 2jFvbQvkJhoATbM4MJQkENqUmMvtpLT6dgk9z6VGN29CN1qsxKnymLhBB18QeZHfeJmNjtGeyA5gXCmhXFRtjAmMUkqG57n7vY7nWFrewSNoUzoq7sG3bb2gkEwjxdDeKkrWwb9Hn4CkCvGqKS1tK4pq57WPX9nLz7VtDBhERLL5wCb26NnWUY5LNsGoHDM5waJV4bg4JXSYPizbxsmCZUvn
a: flag NFT id 72b950c686741516c9b83ac6684e26cc1c7b95c8e9e773c830f867ebb8210675 (supply 1, minted straight into the QDay box, R4 = 0100)
a: mint the flag into the QDay box: tx 0897bdf7f8443bbc33b41f333b66b03c07fce54b4498c7b47bd96c44618ff648 confirmed at height 605264
a: flag box 803f5c51ede97b1fef359fb652e0f322e3d6c64128f49bc2871206a4c7f55240
```

**b. The vaults.** Vault k+1 first (SUCCESSOR = 32 zero bytes, its own PKSEED/PKCOMMIT), then vault k with
SUCCESSOR = blake2b256(tree of k+1); OWNER = the wallet key, QDAY_NFT = the id above:

```
b: vault k+1 (key 1): tree 1351 bytes, SUCCESSOR 00..00, BACKSTOP 900000, address 3CBLnV6NzUMveeA2xTBtJpPTzGX67nW45gnjmxEc8eg1P4eAh9enfDizpJLW81msYhSPafBnvA9oSn6jAz1zJzBaDPSs1mv2Zke43WutCekie5SnNtYvEWniFr3dFR2BaawLjhU1JwgV3PYGfUpgPUUJAbBXBf8nWEkvEzm6hRwoNewcMyDg5cxrJKHYFtyUhPp5P1S6sFuCSt8VMTSoNK8yi5iL1ACTPtjFeyN8iYFGihcfkFDEWRuZcyXD7ASuLr9zC79zmpyBXvfm5ujKDugNwSQE5XhD7nZJodeTDaRFR7UKX8PmRNhxqUVVka
b: vault k (key 0): tree 1351 bytes, SUCCESSOR = blake2b256(tree of k+1) = 2bd0823546f7f33395bfa34325f9aff7d7b03a32671a11d3d9538dee76d34a32, BACKSTOP 900000, address 3CBLnV6NzUMveeA2xTBtJpPTzGX67nW45gnjmxEc8eg1P4eAh9enfDizpJLW81motm59Xuv9tPGV91WeoB6k73CGwUdriZSCx3g3ge1dX5PTYtkRACGPND9uNtKnrTNDX223sppuwFf4uexX7TCJ3JyiBLmkigvN9bmoKtwn82KVdkQYVGnUiZ3f8JG3Yc7oCrZnEXvHsHzEA82HnxbySs4V9Qz8wVC62fzvyjDjNz
```

**c. Two payments to vault k** (0.03 and 0.02 ERG, one transaction, two outputs):

```
c: two payments to vault k (30000000 + 20000000 nanoERG): tx fc9630cedb4adb363f0c38857fb17eb8825606a26f52369aaf1331d3740bdf9e confirmed at height 605265
c: vault k boxes a6b915844bfb8d50f82550c65fd7e8e493d3e8177c17a1faf859e9be0135b325 (30000000) and f67d8094b19f963611c122209f1361d984911537607b26eb8be58d353a48c322 (20000000)
```

**d. Keyless merge.** Both inputs at vault k with context variable 0 = `0400` (Int 0), proofs empty, one output at
vault k with total − bounty, bounty = min(2 × 500,000, total − largest) = 1,000,000 to the fee contract, creation
height = the current height, no other input:

```
d: keyless merge of a6b915844bfb… and f67d8094b19f…: var 0 = 0400, output 49000000 at vault k, bounty 1000000 to the fee contract, creation height 605265, proofs empty (built id 0c84238326ceb2b08b61dadf3ce34f5e4d48f0c886837f21c1b2c0af7df64421)
d: keyless merge at vault k: tx 0c84238326ceb2b08b61dadf3ce34f5e4d48f0c886837f21c1b2c0af7df64421 confirmed at height 605266
d: merged box 1ba529d1e832e3fe6f034dcb827650500a5c785e655dde5c69d29384754821e7
```

**e. The demo oracle flips the flag.** Input 0 the flag box (its script reduces to `proveDlog(ORACLE)` on this
shape), input 1 a wallet box paying the fee (QDay requires `OUTPUTS(0)` at its own script with the same tokens and at
least the same value, so the fee cannot come from the flag box); OUTPUTS(0) the flag with `R4 = 0101`; reduced and
signed by sigmastate-js with the oracle and wallet secrets against the node's last ten headers:

```
e: oracle flip: input 0 the flag box (P2S, reduces to proveDlog(oracle)), input 1 a wallet box for the fee; OUTPUTS(0) same value 10000000, same token, R4 = 0101; signed with sigmastate-js at tip 605266 (id 26d1f3bc945bf446388bb47bbb61da5fce664cdb4645dcfae989ec46c68a16b4)
e: the demo oracle sets the flag true: tx 26d1f3bc945bf446388bb47bbb61da5fce664cdb4645dcfae989ec46c68a16b4 confirmed at height 605267
e: flag box now ecb6947c3c570d5b28f12fccee0927ebfd01c77a83a6998ca76f425290778365 (R4 = true)
```

**f. Migration: the forgery first, then the honest spend, one digest.** One input (the merged box), outputs
value − fee to the wallet and the fee; the digest blake2b256(boxId ++ outputs' bytesWithoutRef) signed once by
vault k's WOTS+ key (the UsedStore recorded the digest before the signature was computed); the forged copy is the
same transaction with signature byte 0's low bit flipped, carried as context variable 1 (`0e e010` ++ 2,144 bytes).
No data input: the hash path needs only variable 1 and `mine.size == 1`.

```
f: hash-key spend of the merged box 1ba529d1e832e3fe6f034dcb827650500a5c785e655dde5c69d29384754821e7 (49000000) to the wallet, creation height 605267: digest 267ccb6077dc04a7d57c3fe1be61561f41822d58f6749af8c34fa32c83346b3f, WOTS+ signature 2144 bytes under PKCOMMIT 522c3209d376e1b707821754995ae35f8d4dfd5471b4c84c167db53e283bceb1 (recorded in testnet/used.json before signing)
f: FORGED migration (signature byte 0, low bit flipped), same digest: REFUSED HTTP 400: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 569ec291860bcb035020423de67fadf88c86ce7d5beea1212f194bc542fe8403: #0 => Success((false,38779))"
}
f: honest migration (vault k hash key): tx 5603ee16b79734c244974f47e9fadbd3e1a747295a621eff1b77d2f6a4a88998 confirmed at height 605268
f: wallet received box 987fc3f2d8e5e43cef69e63e232af661d7bd23634740ea762fc6d4ee08ed574c
```

The node's text says what happened: the forged input's script was evaluated to the end (`Success((false, 38779))`:
every WOTS+ chain finished, the commitment compared, false at cost 38,779) and the transaction refused. The honest
one, different only in that bit, was mined two heights later.

**g. A late payment, then the forward: the wrong destination first.** 0.02 ERG paid to vault k after the migration
confirmed; then one input at vault k, context variable 0 = `0400`, the true flag box as a data input (`afterQday`),
bounty = min(value / 2, 2,000,000) = 2,000,000, proofs empty. Submitted first with the output at the wallet's P2PK
tree (must be refused: the forward reaches only the committed successor, the merge path needs two inputs, the lone
refresh window is more than a million blocks away), then with the output at vault k+1's tree:

```
g: a late payment of 20000000 to vault k after the migration: tx 81f9ee74d002f4f2688c08f342c2b6f00d6adb128c8659e5ad4144680c0db3e6 confirmed at height 605269
g: late box bf6bbf672ecc77463a6bc2fc7883462057695e3fb620c14386fd6ad1e96d58e0
g: forward to the wallet P2PK instead of the successor: REFUSED HTTP 400: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 70cfeadf5faaf8229eb188112538bea6493eef8fe1b82bb541bb2abde457971b: #0 => Success((false,226))"
}
g: keyless forward to vault k+1 (18000000 kept, bounty 2000000): tx e4c6a2186e6b20ed707d9825e2527108ca96928a0456e0fe4b5a820b1193e8f5 confirmed at height 605270
g: forwarded box at vault k+1: 4e0bac8e336b0f1a874d61184d54d71b526b382c3c0c3d80f18d2a35db60c078
```

**h. The successor spends.** Vault k+1's hash key, its first and only signature, moves the forwarded box to the wallet:

```
h: vault k+1 hash-key spend of the forwarded box 4e0bac8e336b0f1a874d61184d54d71b526b382c3c0c3d80f18d2a35db60c078 (18000000) to the wallet, creation height 605270: digest b994b1c8c6afbdd4cbf51394275e30e55204f32c415028d8f599e2a823815136, PKCOMMIT d409055e888d1de11c1846a3c9d93d4ffa447479b782ba4217efe881fc823f2b (its first and only signature)
h: vault k+1 hash key spends the forwarded box: tx 67a96659a30918e71fdcee6ea2bd9b19b191d773dc8bf74d0fe12835941c9edc confirmed at height 605271
h: wallet received box 2a8633a7b0bb4db8a62e533ccd931a38657c16a6d5acb5f94e6782d77ac94689
```

## Verification

Every accepted transaction re-queried from the node after the run (`node-confirmations.txt`,
`GET /blockchain/transaction/byId/{id}`):

```
0897bdf7f8443bbc33b41f333b66b03c07fce54b4498c7b47bd96c44618ff648 inclusionHeight 605264 confirmations 7 inputs 1 outputs 3
fc9630cedb4adb363f0c38857fb17eb8825606a26f52369aaf1331d3740bdf9e inclusionHeight 605265 confirmations 6 inputs 1 outputs 4
0c84238326ceb2b08b61dadf3ce34f5e4d48f0c886837f21c1b2c0af7df64421 inclusionHeight 605266 confirmations 5 inputs 2 outputs 2
26d1f3bc945bf446388bb47bbb61da5fce664cdb4645dcfae989ec46c68a16b4 inclusionHeight 605267 confirmations 4 inputs 2 outputs 3
5603ee16b79734c244974f47e9fadbd3e1a747295a621eff1b77d2f6a4a88998 inclusionHeight 605268 confirmations 3 inputs 1 outputs 2
81f9ee74d002f4f2688c08f342c2b6f00d6adb128c8659e5ad4144680c0db3e6 inclusionHeight 605269 confirmations 2 inputs 1 outputs 3
e4c6a2186e6b20ed707d9825e2527108ca96928a0456e0fe4b5a820b1193e8f5 inclusionHeight 605270 confirmations 1 inputs 1 outputs 2
67a96659a30918e71fdcee6ea2bd9b19b191d773dc8bf74d0fe12835941c9edc inclusionHeight 605271 confirmations 0 inputs 1 outputs 2
```

Eight accepted, one per block from 605,264 to 605,271; two refused, both with the node's script verdict
(`Success((false, cost))`), quoted above verbatim and kept with the submitted bytes in `txs/f-migrate-forged.json`
and `txs/g-forward-to-key.json`.

The UsedStore after the run (`used.json`): exactly one digest per hash key, the digests of f and h:

```
{
 "522c3209d376e1b707821754995ae35f8d4dfd5471b4c84c167db53e283bceb1": "267ccb6077dc04a7d57c3fe1be61561f41822d58f6749af8c34fa32c83346b3f",
 "d409055e888d1de11c1846a3c9d93d4ffa447479b782ba4217efe881fc823f2b": "b994b1c8c6afbdd4cbf51394275e30e55204f32c415028d8f599e2a823815136"
}
```

`npm test` after the run: `ALL PASS (32 checks)`; `npm run typecheck` clean (the flow scripts type-check with the
project's flags as well).

## What this shows, and its limits

- The step-3 shape runs on the public network with the real schedule constants: the 6.0.8 testnet node accepted the
  keyless merge, the oracle flip, the hash-key migration, the keyless forward to the committed successor and the
  successor's hash-key spend, and refused the forged migration and the forward to a key address, with no change to
  `QVault2.es` or `QDay.es`.
- Addresses by substitution into a pinned tree hold up against the compiler on real constants (three of three), and
  the builder's checks are the ones a wallet would ship.
- One seed, both key families: the owner key, the demo oracle and both WOTS+ keys are functions of the same 24 words.
- **Demo oracle.** The flag was flipped by a key of the same seed. Nothing here says who holds the mainnet oracle key
  or whether a miner signal replaces it (charter: out of scope).
- **Mainnet constants mean the lone refresh was not shown.** With PERIOD 1,051,200 and WINDOW 21,600 the KeepAlive
  refresh window opens about 1,029,600 blocks after a box's creation; the devnet run (step 3, 40 / 20) covers that
  row. Likewise the backstop path (row 10's shape) was not reached: both backstops are at 900,000.
- **Not run here:** the forged flag (a second NFT unit, rows 8c/8d/f8), the foreign-input and short-value forwards
  (f5, f6), a merge-and-forward in one transaction (f7), the owner-key spend before quantum day (row 1); all judged on
  the devnet in step 3 and not repeated on testnet. No SLH-DSA signature went to the node (the vault's key is
  WOTS+); a node verdict on a noble SLH-DSA signature is still owed.
- The second payment to vault k after the migration was deliberate; the flow does not show a race (a third party's
  dust merged with a pending spend); that is the seat-round reasoning in `../RESULT.md`, not a measurement.
- Costs: the node's rejection texts carry the script cost of the refused evaluations (38,779 for the full WOTS+
  verification that failed; 226 for the forward that failed at the destination check); the accepted transactions'
  costs were not read back (not in `/blockchain/transaction/byId`).
