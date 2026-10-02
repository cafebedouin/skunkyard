# P2SH box script from `Address::script()` cannot be spent on the reference node, and does not parse back in sigma-rust

## Summary

For a P2SH address, `Address::script()` (`ergotree-ir/src/chain/address.rs`, the `Address::P2SH` arm, lines 220-263 on `develop` at 1633e018) writes a box script that hashes the `Option` returned by `GetVar(1)` instead of the `Coll[Byte]` inside it. ergo 6.0.6 rejects every spend of such a box. sigma-rust's own parser also rejects the tree bytes. The reference (sigma-state 6.x) and Fleet SDK both write `OptionGet` before `CalcBlake2b256`, and their trees spend.

## What sigma-rust writes

```
SigmaAnd(
  BoolToSigmaProp(EQ(Slice(CalcBlake2b256(GetVar(1, Coll[Byte])), 0, 24), hash)),
  DeserializeContext(1, SigmaProp))
```

ErgoTree header `0x00`. For testnet address `qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i` (hash `62d1e48400494bfedf9bf70d4af152428fb46f32bf05d199`):

```
00ea02d193b4cbe3010e040004300e1862d1e48400494bfedf9bf70d4af152428fb46f32bf05d199d40801
```

`cb` (CalcBlake2b256) is followed directly by `e3 01 0e` (GetVar, id 1, `Coll[Byte]`). No `e4` (OptionGet).

## What the node does with it

ergo 6.0.6 devnet, block version 4. The box carried these bytes unchanged, and the spend had `08cd ++ pk` in variable 1 plus a valid `proveDlog(pk)` proof. `POST /transactions` answered:

```
HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" }
```

The node accepted the box when it was created, so a payer using sigma-rust can lock funds in a box that no prover can spend.

## What the reference and Fleet write

- sigmastate-interpreter 6.x, `Pay2SHAddress.script` (`data/shared/src/main/scala/org/ergoplatform/ErgoAddress.scala`; `val scriptId = 126: Byte`, line 186 in 6.0.6 and 6.0.7, `1` in 5.0.2 at line 183): `SigmaAnd(EQ(Slice(CalcBlake2b256(GetVarByteArray(126).get), 0, 24), hash).toSigmaProp, DeserializeContext(126, SSigmaProp))`, header `0x00`, constants not segregated. Bytes as written by sigmastate-js 0.6.3: `00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e`.
- Fleet SDK 0.12.0 writes the 5.x form, variable 1 with `OptionGet`: `00ea02d193b4cbe4e3010e040004300e18 ++ hash ++ d40801`.

Both forms were spent and confirmed on the same 6.0.6 devnet node (table below).

## Second defect: the tree does not parse back

`ErgoTree::sigma_parse_bytes` on the bytes above fails, because `CalcBlake2b256`'s input type check sees `SOption(SColl(SByte))`. In ergo-lib-wasm 0.28.0 this showed up as `ErgoTree root expr parsing (deserialization) error: NonConsumedBytes`. In 0.28.0, `sigma_parse_bytes` replaced the real error with `NonConsumedBytes` when bytes were left over (removed in f6048c1e). Effects in 0.28.0:
- `constants_len()` and `template_bytes()` throw on the parsed tree.
- `Address.recreate_from_ergo_tree` returns a P2S address (`hS3Egony3bqLSmg5Dsw...`) instead of the P2SH address.
- `Wallet.sign_transaction` fails on its own form.

Separately, `recreate_from_ergo_tree` matches only `DeserializeContext` id `1`, so the reference 6.x (id 126) tree is reported as P2S.

## Reproduction (run card)

**Needs:**
- Rust 1.91.1, which is the `rust-toolchain` of the repository.
- A checkout of `develop`.
- crates.io access for `base16`.

**Takes:** about 1 minute for a cold build.

**Touches:** a scratch cargo project only. No node and no network calls at run time.

`Cargo.toml`: `ergotree-ir = { path = "<sigma-rust>/ergotree-ir" }`, `base16 = "0.2"`. `src/main.rs`:

```rust
use ergotree_ir::chain::address::{Address, AddressEncoder};
use ergotree_ir::ergo_tree::ErgoTree;
use ergotree_ir::serialization::SigmaSerializable;

fn main() {
    let addr = AddressEncoder::unchecked_parse_address_from_str("qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i").unwrap();
    let tree = addr.script().unwrap();
    let bytes = tree.sigma_serialize_bytes().unwrap();
    println!("script() bytes: {}", base16::encode_lower(&bytes));
    println!("parse back:     {:?}", ErgoTree::sigma_parse_bytes(&bytes).map(|_| "ok"));
    let reference = base16::decode("00ea02d193b4cbe4e37e0e040004300e1862d1e48400494bfedf9bf70d4af152428fb46f32bf05d199d4087e").unwrap();
    let ref_tree = ErgoTree::sigma_parse_bytes(&reference).unwrap();
    println!("recreate(6.x reference tree) is P2SH: {:?}", Address::recreate_from_ergo_tree(&ref_tree).map(|a| matches!(a, Address::P2SH(_))));
}
```

Expected output on `develop` 1633e018 (verbatim, `cargo run -q`):

```
script() bytes: 00ea02d193b4cbe3010e040004300e1862d1e48400494bfedf9bf70d4af152428fb46f32bf05d199d40801
parse back:     Err(InvalidArgument(InvalidArgumentError("InvalidExprEvalTypeError: InvalidExprEvalTypeError: expected: SColl(SByte), got: SOption(SColl(SByte))\nBacktrace:\ndisabled backtrace")))
recreate(6.x reference tree) is P2SH: Ok(false)
```

There is also a JavaScript reproduction against ergo-lib-wasm-nodejs 0.28.0: `skunks/oneshot/scripts/sigma-rust-p2sh-repro.cjs` in the skunkyard project. It was not re-run for this report.

## Evidence: P2SH forms on a node

The skunkyard project ran this test (2026-10-02; one ergo 6.0.6 node, block version 4; three runs with the same verdicts; run 3 shown). It used one P2SH address of `proveDlog(pk)`, pk `0254e96d...7d06b4`, hash `c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9`. The node wallet paid 1 ERG to each tree.

| form | writer | var | signed by | node response | confirmed |
|---|---|---|---|---|---|
| sigma-state 6.x | sigmastate-js | 126 | sigmastate-js | HTTP 200 `0d280c1c...f026` | height 21 |
| 5.x / Fleet | Fleet | 1 | sigmastate-js | HTTP 200 `dce6f6b6...5dc4` | height 24 |
| sigma-rust | ergo-lib-wasm | 1, no OptionGet | ergo-lib-wasm (message signature over the bytes to sign; transaction signing failed locally) | HTTP 400 `ClassCastException` (above) | no |
| sigma-rust | ergo-lib-wasm | 1, no OptionGet | sigmastate-js (message signature) | HTTP 400 `ClassCastException` | no |
| sigma-state 6.x | sigmastate-js | 126 | ergo-lib-wasm (message signature, control) | HTTP 200 `6a57db0f...eaa7` | height 27 |
| 5.x / Fleet | Fleet | 1 | ergo-lib-wasm `Wallet.sign_transaction` | HTTP 200 `2d1a2de7...9caa` | height 29 |

## Prior reports searched

All searches were run on 2026-10-02 against ergoplatform/sigma-rust:
- `gh issue list` and `gh pr list` with `--state all --search` for `P2SH`, `Pay2SH`, `DeserializeContext`, `GetVar 126`, `OptionGet`, and `scriptId`.
- `gh api search/issues` for `P2SH`, `Pay2SH`, `pay to script hash`, `p2sh script`, `ClassCastException`, `NonConsumedBytes`, and `scala.Some`.
- `git log` of `address.rs` on `develop`, including `-L` over the P2SH arm.

Hits:
- #337 (closed): the issue that asked for `Address::Pay2Sh`.
- #407 (merged 2021-09-23): the implementation. Commits c80c5a6c and 52b7a1f5 wrote `var_id: 1` without `OptionGet`, and the form has not changed since.
- #879 (open): `DeserializeContext` substitution when a variable is absent. It is related to `DeserializeContext` but not to this defect.

No hit reports the missing `OptionGet` or the variable-126 change.

## Proposed fix

Build the sigma-state 6.x form in `Address::script()`:
- `GetVar(126, Coll[Byte])` wrapped in `OptionGet`, then `CalcBlake2b256`, `Slice(0, 24)`, `==` hash, and `BoolToSigmaProp`.
- `SigmaAnd` with `DeserializeContext(126, SigmaProp)`.
- Header `0x00`, no constant segregation.

The variable id should be a named constant that cites `Pay2SHAddress.scriptId` and the 5.x to 6.x change. `recreate_from_ergo_tree` should accept variable 126 and the legacy variable 1, so that addresses are still recognized for boxes already on chain.

Not covered by this fix: the old sigma-rust bytes stay unparseable by sigma-rust's stricter `CalcBlake2b256` type check. The reference parser accepts them and fails only at evaluation, so whether sigma-rust should parse such trees is a separate question.
