# option on mainnet, 2026-10-29: two calls and two puts from the test wallet

Wallet `9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc` (the skunkyard test wallet), writer and buyer in one.
Every step was built by the page's own builders from the skunkyard copy of the page
(`skunks/dexpage/scripts/mainnet-run.ts option-write | option-buy | option-exercise | option-reclaim`, unsigned
JSON in `skunks/dexpage/mainnet/option-*.json`), then signed, checked on a 6.1.2 node and submitted by
`skunks/oneshot/scripts/mainnet-sign.mjs` (signed forms in `skunks/dexpage/mainnet/option-<step>-signed.json`;
ledger lines in `skunks/upkeep/mainnet/ledger.jsonl`). The writes name the new tree as `--allow-tree`; a call
write needs `--max-loss 1000000000` because the box holds a rent reserve the cap counts as loss; the exercise and
the reclaim name the tree as `--sign-tree`, since those paths reduce to the wallet's own key. Nothing else touched
the boxes. (The two put writes were built in the same minute, so the second's unsigned file overwrote the first's;
both signed forms are kept.)

Terms: FAKU (`f0cac602…`, 2 decimals; the pool's price was about 30,500 nanoERG per unit from the clocked box's
legs). Calls on 9 units at a strike of 30,000 nanoERG per unit (270,000 in all), puts on 320 units at 31,250
(10,000,000 in all, the 0.01 ERG collateral); every option expiring at 1,905,177, 30 blocks from the build height
1,905,147, premium 0.001 ERG.

The builder and the signer printed, for the four writes (C1's builder line is from the box as the buy step read
it back, since the signed build's own line was not kept; the explorer read height 1,905,147 while the four were
built and they were mined at 1,905,148):

```
call 6408a2ffd043: 9 units of f0cac602d618, strike 30000 (270000 in all), expiry 1905177 (height 1905147), premium 1000000, unsold, value 711250000
[sign] wallet ERG in 893843065, back 181593065, net -712250000 nanoERG; fee 1000000; tokens leaving the wallet {"f0cac602":"9"}
[sign] node check http://128.253.41.100:9053: 200 "88390a99f8cbad33760b6be3b399455bcf52bd0fb3d93b174e8f330e1a415e5f"
SIGNED: SUBMITTED 88390a99f8cbad33760b6be3b399455bcf52bd0fb3d93b174e8f330e1a415e5f net -712250000
call on 9 units of f0cac602d618: strike 30000 nanoERG/unit (270000 in all), expiry 1905177 (height 1905147 + 30), premium 1000000; box 569 bytes, rent reserve 711250000, value 711250000
[sign] wallet ERG in 8446723183, back 7734473183, net -712250000 nanoERG; fee 1000000; tokens leaving the wallet {"f0cac602":"9"}
SIGNED: SUBMITTED 5cece0d9c340ec4f38e68fb44da9e9c4275a9fa587c637cc799c15f78aeb5460 net -712250000
put on 320 units of f0cac602d618: strike 31250 nanoERG/unit (10000000 in all), expiry 1905177 (height 1905147 + 30), premium 1000000; box 520 bytes, rent reserve 0, value 10000000
[sign] wallet ERG in 20000000, back 9000000, net -11000000 nanoERG; fee 1000000; tokens leaving the wallet {}
SIGNED: SUBMITTED cf844235178402b610bf6e7c85df615c5ebd1742ecd3c43cc0ccf280484c9c08 net -11000000
put on 320 units of f0cac602d618: strike 31250 nanoERG/unit (10000000 in all), expiry 1905177 (height 1905147 + 30), premium 1000000; box 520 bytes, rent reserve 0, value 10000000
[sign] wallet ERG in 11100000, back 100000, net -11000000 nanoERG; fee 1000000; tokens leaving the wallet {}
SIGNED: SUBMITTED 23512ea58c092ba6a4ba9197df95cfb31dc6f201b7000f2658c71e336f505a8f net -11000000
```

The four writes were mined at 1,905,148 (`/api/v1/transactions/<id>`): the first call as box `6408a2ff…`, the
second call `5a1e895e…`, the first put `d4c8b7d3…`, the second put `6a47c930…`.

The builder and the signer printed, for the two buys (keyless path: the option box carries no proof; the wallet
signs only its own input for the premium and the fee):

```
call 6408a2ffd043: 9 units of f0cac602d618, strike 30000 (270000 in all), expiry 1905177 (height 1905147), premium 1000000, unsold, value 711250000
  out 0: 1000000 nanoERG  -> wallet
  out 1: 711250000 nanoERG 9×f0cac602 -> 19f202080404…
[sign] wallet 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc; inputs 2 (1 wallet, 1 keyless)
[sign] wallet ERG in 7734473183, back 7733473183, net -1000000 nanoERG; fee 1000000; tokens leaving the wallet {}
[sign] node check http://128.253.41.100:9053: 200 "00b09b3d9c705b99a48dc332d4eb9ecebbc55fb2d46919f396080de296be2d41"
SIGNED: SUBMITTED 00b09b3d9c705b99a48dc332d4eb9ecebbc55fb2d46919f396080de296be2d41 net -1000000
put d4c8b7d36bbf: 320 units of f0cac602d618, strike 31250 (10000000 in all), expiry 1905177 (height 1905147), premium 1000000, unsold, value 10000000
  out 0: 1000000 nanoERG  -> wallet
  out 1: 10000000 nanoERG  -> 19e202070404…
[sign] wallet 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc; inputs 2 (1 wallet, 1 keyless)
[sign] wallet ERG in 181593065, back 180593065, net -1000000 nanoERG; fee 1000000; tokens leaving the wallet {}
SIGNED: SUBMITTED ce01d9bf4e211f8e483eab1c3a2ec91b8a5ed2da3f63f5afa049058be5910ebe net -1000000
```

Both buys were mined at 1,905,149; the sold call is box `7c4f691c…`, the sold put `2273d3da…`. For the two
exercises (the buyer's key path: the signer signs the option box too, named as `--sign-tree`, and the node's check
accepted the proof, so the reduced proposition is the buyer's plain key as the contract intends):

```
call 7c4f691c15c3: 9 units of f0cac602d618, strike 30000 (270000 in all), expiry 1905177 (height 1905148), premium 1000000, sold to 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc, value 711250000
  out 0: 711520000 nanoERG  -> wallet
  out 1: 100000 nanoERG 9×f0cac602 -> wallet
[sign] inputs under these scripts are signed with the wallet key: 19f2020804040402…
[sign] wallet 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc; inputs 2 (2 wallet, 0 keyless)
[sign] wallet ERG in 8443723183, back 8442723183, net -1000000 nanoERG; fee 1000000; tokens leaving the wallet {}
[sign] node check http://128.253.41.100:9053: 200 "9e39054580f1a66a819c4283c1f6575c785638b151fc62810285a4de9e5da64b"
SIGNED: SUBMITTED 9e39054580f1a66a819c4283c1f6575c785638b151fc62810285a4de9e5da64b net -1000000
put 2273d3dae390: 320 units of f0cac602d618, strike 31250 (10000000 in all), expiry 1905177 (height 1905148), premium 1000000, sold to 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc, value 10000000
  out 0: 100000 nanoERG 320×f0cac602 -> wallet
  out 1: 10000000 nanoERG  -> wallet
[sign] inputs under these scripts are signed with the wallet key: 19e2020704040402…
[sign] wallet 9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc; inputs 3 (3 wallet, 0 keyless)
[sign] wallet ERG in 190593065, back 189593065, net -1000000 nanoERG; fee 1000000; tokens leaving the wallet {}
SIGNED: SUBMITTED fadce9ab848c87e5d4b2af5e0773b22047d04e544415312231337cc65ef4513f net -1000000
```

Both exercises were mined at 1,905,151. The second call and the second put were left unsold; once the explorer
read 1,905,177, the expiry, the writer's reclaims were built (the builder requires the wallet's height to have
reached the expiry; the node evaluates the next block, where `HEIGHT > expiry` holds) and signed under the
writer's key:

```
call 5a1e895eeee1: 9 units of f0cac602d618, strike 30000 (270000 in all), expiry 1905177 (height 1905177), premium 1000000, unsold, value 711250000
  out 0: 711250000 nanoERG 9×f0cac602 -> wallet
[sign] inputs under these scripts are signed with the wallet key: 19f2020804040402…
[sign] wallet ERG in 890743065, back 889743065, net -1000000 nanoERG; fee 1000000; tokens leaving the wallet {}
[sign] node check http://128.253.41.100:9053: 200 "1d642d7058ce7bcfb2841569d699fd502e76537796d82e14112fba29f4ad1586"
SIGNED: SUBMITTED 1d642d7058ce7bcfb2841569d699fd502e76537796d82e14112fba29f4ad1586 net -1000000
put 6a47c9302c1e: 320 units of f0cac602d618, strike 31250 (10000000 in all), expiry 1905177 (height 1905177), premium 1000000, unsold, value 10000000
  out 0: 10000000 nanoERG  -> wallet
[sign] inputs under these scripts are signed with the wallet key: 19e2020704040402…
[sign] wallet ERG in 20000000, back 19000000, net -1000000 nanoERG; fee 1000000; tokens leaving the wallet {}
SIGNED: SUBMITTED 11881457098d42e609b96b66d862b18dcfe9f925cef51bbad02cdb77bbda6299 net -1000000
```

Inclusion heights from `/api/v1/transactions/<id>`; the wallet's net per step is the signer's printed `net` (the
wallet is writer and buyer, so a premium, a strike or a collateral moving between the two nets to the miner fee):

| step | what | transaction | mined at | wallet net nanoERG |
|---|---|---|---|---|
| C1 | write a call on 9 FAKU units, strike 30,000/unit, expiry 1,905,177, premium 0.001 ERG; 0.71125 ERG reserve held (`buildWrite`, `--allow-tree`) | `88390a99f8cbad33760b6be3b399455bcf52bd0fb3d93b174e8f330e1a415e5f` | 1,905,148 | -712,250,000 and -9 FAKU |
| C2 | write a second call, the same terms | `5cece0d9c340ec4f38e68fb44da9e9c4275a9fa587c637cc799c15f78aeb5460` | 1,905,148 | -712,250,000 and -9 FAKU |
| P1 | write a put on 320 units, strike 31,250/unit, 0.01 ERG collateral, expiry 1,905,177, premium 0.001 ERG | `cf844235178402b610bf6e7c85df615c5ebd1742ecd3c43cc0ccf280484c9c08` | 1,905,148 | -11,000,000 |
| P2 | write a second put, the same terms | `23512ea58c092ba6a4ba9197df95cfb31dc6f201b7000f2658c71e336f505a8f` | 1,905,148 | -11,000,000 |
| B1 | buy C1 (`buildBuy`, keyless path): 0.001 ERG premium to the writer, box `7c4f691c…` with the buyer in R7 | `00b09b3d9c705b99a48dc332d4eb9ecebbc55fb2d46919f396080de296be2d41` | 1,905,149 | -1,000,000 |
| BP1 | buy P1, the same: box `2273d3da…` | `ce01d9bf4e211f8e483eab1c3a2ec91b8a5ed2da3f63f5afa049058be5910ebe` | 1,905,149 | -1,000,000 |
| E1 | exercise the call (`buildExercise`, `--sign-tree`): 711,520,000 nanoERG (reserve plus strike) to the writer, 9 units in a 0.0001 ERG box to the buyer | `9e39054580f1a66a819c4283c1f6575c785638b151fc62810285a4de9e5da64b` | 1,905,151 | -1,000,000 |
| EP1 | exercise the put: 320 units in a 0.0001 ERG box to the writer, 10,000,000 nanoERG to the buyer | `fadce9ab848c87e5d4b2af5e0773b22047d04e544415312231337cc65ef4513f` | 1,905,151 | -1,000,000 |
| R2 | reclaim C2 after its expiry (`buildReclaim`, `--sign-tree`): 9 units and the reserve back | `1d642d7058ce7bcfb2841569d699fd502e76537796d82e14112fba29f4ad1586` | 1,905,178 | -1,000,000 |
| RP2 | reclaim P2 after its expiry: the collateral back | `11881457098d42e609b96b66d862b18dcfe9f925cef51bbad02cdb77bbda6299` | 1,905,178 | -1,000,000 |

Net of the ten: -10,000,000 nanoERG and 0 FAKU, the ten miner fees. The explorer's confirmed balance read
`20218543339` nanoERG and `FAKU 4827` after the first eight (14:06 UTC: the second call's reserve, the second put's
collateral and 9 units still in their boxes) and `20937793339` and `FAKU 4836` after the reclaims (15:15 UTC),
against `20947793339` and `4836` before the round.

## What the run found

- **Both key paths reduce to the one key.** The exercises and the reclaims were signed with the wallet's plain
  Schnorr proof on the option input (`--sign-tree`), and the node's check accepted all four: the contract's
  three-way disjunction folds to `buyer` on an exercise and to `writer` on a reclaim, with the other branches
  trivially false. Nobody without the register's key can produce that proof, which is what "non-transferable" means
  here.
- **The reclaims landed the block after the expiry.** Built when the explorer read 1,905,177 (the expiry), mined
  at 1,905,178, the first block in which `HEIGHT > expiry`; the builder's rule (the wallet's height has reached the
  expiry) is exactly one block conservative, as the charter preregistered.
- **The explorer's height lagged by a block** while the four writes were built (it read 1,905,147; they were mined
  at 1,905,148). Nothing in a write depends on the height but the expiry, so the options expired a block earlier
  than "30 blocks after inclusion"; a page that wants an exact term should add one.
- **Two steps built in the same minute overwrite each other's unsigned file** (`option-write-…T1355.json`,
  `option-buy-…T1400.json`, `option-exercise-…T1403.json`, `option-reclaim-…T1513.json`); the signed forms,
  one per step, are the record (`option-<step>-<kind>-signed.json`), and the exercise and reclaim unsigned forms
  were copied to `option-<step>-<kind>.json` before signing.
- No step was refused by the node; nothing was cancelled. The budget: 0.01 ERG net, under the 0.05 ERG the
  brief allowed.
