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
