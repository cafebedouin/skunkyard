# clockbox on mainnet, 2026-10-29: one program, three keyless legs

Wallet `9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc` (the skunkyard test wallet), both the program's
owner and the runner's payout address. The creation was built by the page's `buildCreateClock` from the skunkyard
copy of the page (`skunks/dexpage/scripts/mainnet-run.ts clock-create FAKU 10000000 3 3 1500000 50`, unsigned in
`C1-create.json`), then signed, checked on a 6.1.2 node and submitted by `skunks/oneshot/scripts/mainnet-sign.mjs`
with the contract named as `--allow-tree` and `--max-loss 1000000000` because the box carries the rent reserve
(signed form in `C1-create-signed.json`; the ledger line in `skunks/upkeep/mainnet/ledger.jsonl`). The three legs
were built and submitted by `freedex/scripts/upkeep-run.ts <wallet> --every 60`, the Node sidecar, with no
signature, through the explorer's mempool endpoint (`runner.log`). Nothing else touched the box.

Program: FAKU (`f0cac602…`), its deepest ERG pool (NFT `19ffcea5…`, 4,259 ERG, fee 3%), three legs of 0.01 ERG
every 3 blocks, tolerance 50 bps, no cap, executor fee 0.0015 ERG. Box 671 bytes; rent reserve 0.83875 ERG;
0.87325 ERG locked.

The signer printed, for C1:

```
[sign] wallet 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc; inputs 1 (1 wallet, 0 keyless)
[sign] wallet ERG in 9412308175, back 8538058175, net -874250000 nanoERG; fee 1000000; tokens leaving the wallet {}
[sign] node check http://128.253.41.100:9053: 200 "3d509bf569271685d00e97dbd89299b125cf25e45761c18869475c290c2f9ae4"
[sign] submit: 200 "3d509bf569271685d00e97dbd89299b125cf25e45761c18869475c290c2f9ae4"
SIGNED: SUBMITTED 3d509bf569271685d00e97dbd89299b125cf25e45761c18869475c290c2f9ae4 net -874250000
```

The runner printed, for the legs (`runner.log`):

```
2026-10-29T09:30:21.812Z upkeep clock-legs: program 9d54c61f on f0cac602: 10000000 nanoERG for 328 units to its owner, 400000 nanoERG to you; submitted 95082ff30496dcae33049adb889c47962c0e3efab534b2c358d1f5fdc4e3ca8b
2026-10-29T09:38:00.156Z upkeep clock-legs: program 84ad1605 on f0cac602: 10000000 nanoERG for 328 units to its owner, 400000 nanoERG to you; submitted 44c970a3b7cc7e3fec830068249f6eafdb19709303931feca3c2009842974833
2026-10-29T09:45:49.754Z upkeep clock-legs: program 2e04c968 on f0cac602: 10000000 nanoERG for 328 units to its owner, the last leg, 500000 nanoERG to you; submitted 3abd3594996ec91c0256a7187a70a7bbb3568e11f857e73fd2f66b6efcca1c15
```

| step | what | transaction | mined at | wallet net nanoERG |
|---|---|---|---|---|
| C1 | create the program (`buildCreateClock`; signed) | `3d509bf569271685d00e97dbd89299b125cf25e45761c18869475c290c2f9ae4` | 1,905,031 | -874,250,000 |
| L1 | leg 1, keyless: 0.01 ERG into the pool, 328 units to the owner (0.0001 ERG box), 0.0004 ERG to the runner, successor 0.86175 ERG | `95082ff30496dcae33049adb889c47962c0e3efab534b2c358d1f5fdc4e3ca8b` | 1,905,033 | +500,000 and 328 FAKU |
| L2 | leg 2, keyless, the same on the successor | `44c970a3b7cc7e3fec830068249f6eafdb19709303931feca3c2009842974833` | 1,905,036 | +500,000 and 328 FAKU |
| L3 | leg 3, the last, keyless: no successor; 328 units and the rest of the ERG (the 0.83875 reserve) to the owner, 0.0005 ERG to the runner | `3abd3594996ec91c0256a7187a70a7bbb3568e11f857e73fd2f66b6efcca1c15` | 1,905,039 | +839,250,000 and 328 FAKU |

Net of the four: -34,000,000 nanoERG for 984 units (9.84 FAKU): the 0.03 ERG the program bought with, the
creation's miner fee, and the three legs' miner fees, which came out of the executor fee the wallet paid itself.
The executor fees (0.0015 a leg) went to the runner's address, which here is the same wallet, so they net to zero
in the table; a stranger running the legs would have kept 0.0004, 0.0004 and 0.0005 ERG.

## What the run found

- **The clock starts at the build height, not the inclusion height.** The box's `creationHeight` is what the
  builder wrote (the explorer's height when the creation was built, 1,905,027), while the block that included it
  was 1,905,031; the first leg was therefore due at 1,905,030, before the box existed, and the runner found it due
  the moment the box was listed. Each leg's successor is created at the runner's build height, so later legs kept
  the 3-block cadence (built at 1,905,031 and 1,905,034). The tab shows the due height from the box, which is the
  truth; a creator who wants the first leg N blocks after inclusion should know the clock began a few blocks early.
- **A leg in the mempool is still an unspent box to the explorer.** The runner's second round rebuilt and
  resubmitted the same leg (same id, `565bc396…`, dropped by the node as a double spend once `95082ff3…` was mined).
  Fixed in the session: `runUpkeep` now carries a map of inputs it spent in the last ten minutes across rounds, in
  the page and the sidecar.
- Every leg was mined within a block or two of its due height at a 0.001 ERG miner fee; no leg was refused, so
  nothing was cancelled.

After the last leg the explorer's confirmed balance for the wallet read `20985535266` nanoERG and `FAKU 3861`
(`/api/v1/addresses/<wallet>/balance/confirmed`, 2026-10-29 10:05 UTC): 21,019,535,266 before C1 less 34,000,000,
and 2,877 units plus the 984 bought. The last leg waited through a 20-minute block gap (height 1,905,037 from
09:45 to 10:05 UTC); the runner resubmitted the same transaction once after its ten-minute memory lapsed, the
same id, harmless.

# Second session, 2026-10-29: one tranche sale and one buy program under the new rule, six keyless legs

Same wallet, owner and runner's payout address in one. Both creations were built by the skunkyard copy of the page
(`skunks/dexpage/scripts/mainnet-run.ts clock-create-sell FAKU 9 3 3 1500000 50`, unsigned in `S1-create.json`;
`clock-create FAKU 10000000 3 3 1500000 50`, unsigned in `C2-create.json`), signed, checked on the 6.1.2 node and
submitted by `skunks/oneshot/scripts/mainnet-sign.mjs` with each contract named as `--allow-tree` (signed forms in
`S1-create-signed.json` and `C2-create-signed.json`; ledger lines in `skunks/upkeep/mainnet/ledger.jsonl`). The six
legs were built and submitted by `freedex/scripts/upkeep-run.ts <wallet> --every 60` with no signature through the
explorer's mempool endpoint (`runner-2.log`). Nothing else touched the boxes. The two fixes were in both builders: no
rent reserve on the buy side, and every new box created at the build height plus one.

Sell program S1: 9 FAKU units in three slices of 3 every 3 blocks, tolerance 50 bps, no floor, executor fee 0.0015
ERG, on the same FAKU pool as the first session (NFT `19ffcea5…`, 4,259 ERG, fee 3%). Buy program C2: the first
session's program again, three legs of 0.01 ERG every 3 blocks, tolerance 50 bps, no cap, fee 0.0015 ERG.

The builder and the signer printed, for S1 (the check-only pass first, then the submission):

```
pool 7607751e9c77 FAKU (nft 19ffcea55491): x 4259228552403 y 144079726 fee 970; 3 legs of 3 units every 3 blocks, fee 1500000; box 714 bytes, rent reserve 892500000, minimum 257040, value 897257040
height 1905120; 7 inputs (7 wallet), 3 outputs
  out 0: 897257040 nanoERG 9×f0cac602 -> 198204150402…
[sign] wallet ERG in 9378308175, back 8480051135, net -898257040 nanoERG; fee 1000000; tokens leaving the wallet {"f0cac602":"9"}
[sign] node check http://128.253.41.100:9053: 200 "8ffed74928c91f0b41e366acb5033aac4864ca7d448cdb02504f742df173c09d"
[sign] check only; tx 8ffed74928c91f0b41e366acb5033aac4864ca7d448cdb02504f742df173c09d not submitted
[sign] submit: 200 "8ffed74928c91f0b41e366acb5033aac4864ca7d448cdb02504f742df173c09d"
SIGNED: SUBMITTED 8ffed74928c91f0b41e366acb5033aac4864ca7d448cdb02504f742df173c09d net -898257040
```

The box's `creationHeight` in `S1-create.json` is 1,905,121 at an explorer height of 1,905,120: the node's check
accepted the next block's height, and S1 was mined at 1,905,121. For C2:

```
pool 7607751e9c77 FAKU (nft 19ffcea55491): x 4259228552403 y 144079726 fee 970; 3 legs of 10000000 every 3 blocks, fee 1500000; box 666 bytes, rent reserve 0, value 34500000
  out 0: 34500000 nanoERG  -> 19f503130402…
[sign] wallet ERG in 8480051135, back 8444551135, net -35500000 nanoERG; fee 1000000; tokens leaving the wallet {}
[sign] node check http://128.253.41.100:9053: 200 "6efce60b29f36b5050bc8a590460114662c08a37ca765c3dad99ac2f8c1c8211"
SIGNED: SUBMITTED 6efce60b29f36b5050bc8a590460114662c08a37ca765c3dad99ac2f8c1c8211 net -35500000
```

The runner printed (`runner-2.log`):

```
2026-10-29T12:57:09.279Z upkeep clock-legs: sell program 600da595 on f0cac602: 3 units for 86024 nanoERG to its owner, 486024 nanoERG to you; submitted ffedaeacf9539181e60ef1d66a185935b9a07dc22139720b36389a9acf153ba9
2026-10-29T12:58:21.182Z upkeep clock-legs: program 6ead9e71 on f0cac602: 10000000 nanoERG for 328 units to its owner, 400000 nanoERG to you; submitted e57b396e2af4d7e598d82f068356d85c2e5c756d82c90c1a317ac52d793b534d
2026-10-29T13:03:55.781Z upkeep clock-legs: sell program ca40fbbc on f0cac602: 3 units for 86024 nanoERG to its owner, 486024 nanoERG to you; submitted b730af2abf35f4869389c6c3439533d99a7743d32b681a4f129efa805d24eedf
2026-10-29T13:09:25.193Z upkeep clock-legs: program eea0cd46 on f0cac602: 10000000 nanoERG for 328 units to its owner, 400000 nanoERG to you; submitted fd7782d1d5ae46bb7adb7d73e5adb85e7ed47b503e34a6f1baa8afd436f90241
2026-10-29T13:14:55.357Z upkeep clock-legs: sell program 121242b7 on f0cac602: 3 units for 86025 nanoERG to its owner, the last leg, 500000 nanoERG to you; submitted cec63af0775b67ff441691b1a3134c05480dc7004efed2b01981140c1706247b
2026-10-29T13:17:10.880Z upkeep clock-legs: program fbc69c5a on f0cac602: 10000000 nanoERG for 328 units to its owner, the last leg, 400000 nanoERG to you; submitted 1b40188cdb74c6ff984ee380c8223ebe9fbd6a55ae36edcfd517d357d7628db5
```

Inclusion heights from `/api/v1/transactions/<id>` (2026-10-29 13:24 UTC); the wallet's net per step is the sum of
the step's outputs to the wallet less its inputs from the wallet (the owner's box, the runner's payout, or the
creation's cost), as the wallet is both owner and runner:

| step | what | transaction | mined at | wallet net nanoERG |
|---|---|---|---|---|
| S1 | create the sale (`buildCreateClockSell`; signed): 9 units, 0.0045 ERG of fees, 0.8925 ERG reserve, 0.000257 ERG minimum | `8ffed74928c91f0b41e366acb5033aac4864ca7d448cdb02504f742df173c09d` | 1,905,121 | -898,257,040 and -9 FAKU |
| C2 | create the buy program (`buildCreateClock`; signed): 0.0345 ERG, no reserve | `6efce60b29f36b5050bc8a590460114662c08a37ca765c3dad99ac2f8c1c8211` | 1,905,124 | -35,500,000 |
| SL1 | sell leg 1, keyless: 3 units into the pool for 86,024 nanoERG; the owner's box topped up to 100,000 from the fee; 486,024 to the runner; successor 0.895757 ERG with 6 units, created at 1,905,125 | `ffedaeacf9539181e60ef1d66a185935b9a07dc22139720b36389a9acf153ba9` | 1,905,125 | +586,024 |
| BL1 | buy leg 1, keyless: 0.01 ERG for 328 units (0.0001 ERG box), 0.0004 ERG to the runner, successor 0.023 ERG | `e57b396e2af4d7e598d82f068356d85c2e5c756d82c90c1a317ac52d793b534d` | 1,905,126 | +500,000 and 328 FAKU |
| SL2 | sell leg 2, keyless, the same on the successor | `b730af2abf35f4869389c6c3439533d99a7743d32b681a4f129efa805d24eedf` | 1,905,129 | +586,024 |
| BL2 | buy leg 2, keyless, the same on the successor | `fd7782d1d5ae46bb7adb7d73e5adb85e7ed47b503e34a6f1baa8afd436f90241` | 1,905,131 | +500,000 and 328 FAKU |
| SL3 | sell leg 3, the last, keyless: no successor; 86,025 nanoERG of proceeds plus the reserve and the minimum (892,757,040) in one owner output of 892,843,065; 0.0005 ERG to the runner | `cec63af0775b67ff441691b1a3134c05480dc7004efed2b01981140c1706247b` | 1,905,134 | +893,343,065 |
| BL3 | buy leg 3, the last, keyless: no successor; 328 units in a 0.0001 ERG box (from the fee), 0.0004 ERG to the runner | `1b40188cdb74c6ff984ee380c8223ebe9fbd6a55ae36edcfd517d357d7628db5` | 1,905,136 | +500,000 and 328 FAKU |

Net of the eight: -37,741,927 nanoERG, +975 FAKU units: the 0.03 ERG the buy program bought with, two creation
miner fees and six leg miner fees (0.008 ERG, paid out of executor fees the wallet paid itself), less the sale's
258,073 nanoERG of proceeds; 9 units sold, 984 bought. The reserve and the minimum came back with SL3. The
explorer's confirmed balance read `20947793339` nanoERG and `FAKU 4836` at 13:24 UTC, against `20985535266` and
`3861` after the first session: -37,741,927 and +975, the same figures. A stranger running the legs would have kept
486,024, 486,024 and 500,000 nanoERG on the sale and 400,000 three times on the buy.

## What the run found

- **The sell side runs as the buy side does.** Each leg was built by the runner, accepted by the node with no
  signature, and mined within a block or two of submission; the last leg returned the reserve and the minimum with
  the proceeds in one output, as the mock-chain case predicted. The sale's owner box on a leg that is not the last
  was topped up from 86,024 to 100,000 nanoERG out of the executor's fee: 3 FAKU units sell for less than the box
  minimum the page uses, so the runner's net on those legs was 486,024 rather than 500,000.
- **The saving.** C2 locked 34,500,000 nanoERG against C1's 873,250,000 for the same program: 838,750,000 less
  held, and the box shrank from 671 to 666 bytes. The last buy leg no longer carries a reserve back; the owner's
  box on it is the 0.0001 ERG minimum, paid from the fee.
- **The creation height fix, measured.** S1 was built at explorer height 1,905,120 with its clock at 1,905,121 and
  mined at 1,905,121: the clock and the inclusion height agree, and SL1 was built once the explorer read 1,905,124,
  three blocks after the box landed. C2 was submitted at 12:52:22 UTC with the same clock, 1,905,121, but was not
  mined until 1,905,124: three blocks in the mempool, so its first leg was due the block after it landed, as in the
  first session. The fix removes the build-to-mine gap of one block; a longer wait in the mempool still starts the
  clock early by that wait, less one. The runner's log shows the pool box shared between the two programs made
  their legs alternate rounds (`found 2, submitted 1`), which is the "candidates sharing an input" rule working.
- The runner also printed one `babel-vs-pool: The operation was aborted due to timeout` line when the explorer's
  Babel listing timed out; the job skipped that round and the next round ran. No leg was refused, nothing was
  cancelled.
