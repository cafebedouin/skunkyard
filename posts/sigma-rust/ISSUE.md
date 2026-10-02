# P2SH box script from `Address::script()` is rejected by an ergo 6.0.6 devnet node, and does not parse back in sigma-rust

Prepared with Claude Code (Anthropic, Claude Opus 5.5) for cafebedouin, using peeryard v0.1.0 (ba56b25) on 6.0.6 (21b9023933b1); the devnet runs are the skunkyard project's.

## Summary

The P2SH box script that `Address::script()` writes was rejected by an ergo 6.0.6 devnet node (`ergo-6.0.6.jar`, sha256 `21b9023933b1...`, block version 4): two spends were submitted and both were rejected. The script (`ergotree-ir/src/chain/address.rs:221-230` on `develop` at 1633e018) hashes the `Option` returned by `GetVar(1)` instead of the `Coll[Byte]` inside it. sigma-rust's own parser also rejects the tree bytes. The reference (sigma-state 6.x) and Fleet SDK both wrap `GetVar` in `OptionGet` inside `CalcBlake2b256`, and their trees spend. Versions: 0.28.0 (the only version tested; the code is unchanged since #407).

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

A one-node devnet of ergo 6.0.6 (block version 4). The box carried these bytes unchanged, and each spend had `08cd ++ pk` in variable 1 plus a valid `proveDlog(pk)` proof over the bytes to sign (one proof made by ergo-lib-wasm, one by sigmastate-js). `POST /transactions` answered the first:

```
HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" }
```

The second (tx `b7a5410e...7284`) got the same `ClassCastException`. The node accepted the box when it was created, so a box funded with the tree sigma-rust writes could not be spent on a 6.0.6 node even with a valid proof: the script itself fails.

<details>
<summary>The first rejected transaction, as submitted</summary>

Address `rNoPVtL9L9cuzgqQqkPsqo9VginDU6dBAtBamSU` (testnet), pk `0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4`, hash `c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9`. Box script written by ergo-lib-wasm 0.28.0 `Address.from_base58(addr).to_ergo_tree()`: `00ea02d193b4cbe3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801`. Box `ff5dec6a...` of funding tx `b3a15c7173e2666113e6a1deb213cddee9c13128c7db6344387b1d11d4a1d023`; extension variable 1 is `0e23 ++ 08cd ++ pk`; proof by ergo-lib-wasm `sign_message_using_p2pk` over the bytes to sign.

```json
{"inputs":[{"boxId":"ff5dec6a1d1817562dcfa67e9657d8655832fae4fae09ec43cc64e01b8433a0f","spendingProof":{"proofBytes":"c095798b35617b031ca2dd720dea095407d8cef2198bcdcad8ff3a61ab7c0a32ac2d433f8df8ba8ea05697edac5f282884a1735b904598ab","extension":{"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":24},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":24}],"id":"69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b"}
```

The box id, the funding transaction and the proof are specific to that devnet. To re-run on another node, fund a box with the tree above, build the same one-input spend, and sign its bytes to sign with the secret of pk. The reproduction without a node is the run card below.
</details>

## What the reference and Fleet write

- sigmastate-interpreter 6.x, `Pay2SHAddress.script` (`data/shared/src/main/scala/org/ergoplatform/ErgoAddress.scala`; `val scriptId = 126: Byte`, line 186 in 6.0.6 and 6.0.7, `1` in 5.0.2 at line 183): `SigmaAnd(EQ(Slice(CalcBlake2b256(GetVarByteArray(126).get), 0, 24), hash).toSigmaProp, DeserializeContext(126, SSigmaProp))`, header `0x00`, constants not segregated. Bytes as written by sigmastate-js 0.6.3: `00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e`.
- Fleet SDK 0.12.0 writes the 5.x form, variable 1 with `OptionGet`: `00ea02d193b4cbe4e3010e040004300e18 ++ hash ++ d40801`.

Both forms were spent and confirmed on the same 6.0.6 devnet node (table below).

## Second defect: the tree does not parse back

`ErgoTree::sigma_parse_bytes` on the bytes above fails, because `CalcBlake2b256`'s input type check sees `SOption(SColl(SByte))`. In ergo-lib-wasm 0.28.0 this showed up as `ErgoTree root expr parsing (deserialization) error: NonConsumedBytes`: in 0.28.0, `sigma_parse_bytes` returned `NonConsumedBytes` in place of the parse result whenever bytes were left over (removed in f6048c1e, after 0.28.0). In 0.28.0, `constants_len()`, `template_bytes()` and `Wallet.sign_transaction` fail on such a box, and `recreate_from_ergo_tree` returns a P2S address on the parsed tree (on the in-memory tree it returns P2SH).

Separately, `recreate_from_ergo_tree` (`address.rs:108-181`) matches only `DeserializeContext` id `1`, so the reference 6.x (id 126) tree is reported as P2S; with id 1 it accepts any hashed expression, without checking that it reads the same variable.

## Reproduction (run card)

**Needs:**
- Rust 1.91.1, which is the `rust-toolchain` of the repository.
- A checkout of `develop` at `1633e01835d48e4d4b127f7478e602e129e80110`.
- crates.io access for `base16`.

**Takes:** 1m38s for the cold build measured on `develop` (1m14s on the fix branch), with the crates.io index already cached.

**Touches:** a scratch cargo project only. No node and no network calls at run time.

**How to stop:** it exits by itself: status 1 when the bytes do not parse back or the 6.x tree is not P2SH, 0 otherwise.

`Cargo.toml`: `ergotree-ir = { path = "<sigma-rust>/ergotree-ir" }`, `base16 = "0.2.1"`. `src/main.rs`:

```rust
use ergotree_ir::chain::address::{Address, AddressEncoder};
use ergotree_ir::ergo_tree::ErgoTree;
use ergotree_ir::serialization::SigmaSerializable;

fn main() {
    let addr = AddressEncoder::unchecked_parse_address_from_str("qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i").unwrap();
    let tree = addr.script().unwrap();
    let bytes = tree.sigma_serialize_bytes().unwrap();
    println!("script() bytes: {}", base16::encode_lower(&bytes));
    let parsed = ErgoTree::sigma_parse_bytes(&bytes);
    println!("parse back:     {:?}", parsed.as_ref().map(|_| "ok"));
    let reference = base16::decode("00ea02d193b4cbe4e37e0e040004300e1862d1e48400494bfedf9bf70d4af152428fb46f32bf05d199d4087e").unwrap();
    let ref_tree = ErgoTree::sigma_parse_bytes(&reference).unwrap();
    let is_p2sh = Address::recreate_from_ergo_tree(&ref_tree).map(|a| matches!(a, Address::P2SH(_)));
    println!("recreate(6.x reference tree) is P2SH: {:?}", is_p2sh);
    if parsed.is_err() || is_p2sh != Ok(true) {
        std::process::exit(1);
    }
}
```

Output on `develop` 1633e018 (`time cargo run -q`), exit status 1. The stable parts are `InvalidArgument`, expected `SColl(SByte)`, got `SOption(SColl(SByte))`, and `Ok(false)`; the error wrapping may differ between builds:

```
script() bytes: 00ea02d193b4cbe3010e040004300e1862d1e48400494bfedf9bf70d4af152428fb46f32bf05d199d40801
parse back:     Err(InvalidArgument(InvalidArgumentError("InvalidExprEvalTypeError: InvalidExprEvalTypeError: expected: SColl(SByte), got: SOption(SColl(SByte))\nBacktrace:\ndisabled backtrace")))
recreate(6.x reference tree) is P2SH: Ok(false)
```

Output with the proposed fix, exit status 0:

```
script() bytes: 00ea02d193b4cbe4e37e0e040004300e1862d1e48400494bfedf9bf70d4af152428fb46f32bf05d199d4087e
parse back:     Ok("ok")
recreate(6.x reference tree) is P2SH: Ok(true)
```

## Evidence: P2SH forms on a node

A one-node devnet of ergo 6.0.6 (2026-10-02; block version 4; three runs with the same verdicts; run 3 shown). It used one P2SH address of `proveDlog(pk)`, pk `0254e96d...7d06b4`, hash `c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9`. The node wallet paid 1 ERG to each tree. Two control rows (each working form signed by the other library) also confirmed; all six rows and the run log are in the captures (`devnet-p2sh-forms.txt`).

| form | writer | var | signed by | node response | confirmed |
|---|---|---|---|---|---|
| sigma-state 6.x | sigmastate-js | 126 | sigmastate-js | HTTP 200 `0d280c1c...f026` | height 21 |
| 5.x / Fleet | Fleet | 1 | sigmastate-js | HTTP 200 `dce6f6b6...5dc4` | height 24 |
| sigma-rust | ergo-lib-wasm | 1, no OptionGet | ergo-lib-wasm (message signature over the bytes to sign; transaction signing failed locally) | HTTP 400 `ClassCastException` (above) | no |
| sigma-rust | ergo-lib-wasm | 1, no OptionGet | sigmastate-js (message signature) | HTTP 400 `ClassCastException` | no |

## Prior reports searched

Issues and pull requests of ergoplatform/sigma-rust in all states were searched on 2026-10-02 for `P2SH`, `Pay2SH`, `DeserializeContext` and `OptionGet`, and the 65 open pull requests for the files they touch (`gh-search.txt`, `open-prs-address-rs.txt`). The hits are #337 and #407 (the request for `Address::Pay2Sh` and its implementation, which wrote `var_id: 1` without `OptionGet`), open #860 (makes sigma-rust parse this tree form, met on mainnet at block 1,711,120, without changing `Address::script()`), and #240, #365, #776, #777, #846, #879 on `DeserializeContext` evaluation; none reports that `Address::script()` writes an unspendable tree.

## Proposed fix

Build the sigma-state 6.x form in `Address::script()`:
- `GetVar(126, Coll[Byte])` wrapped in `OptionGet`, then `CalcBlake2b256`, `Slice(0, 24)`, `==` hash, and `BoolToSigmaProp`.
- `SigmaAnd` with `DeserializeContext(126, SigmaProp)`.
- Header `0x00`, no constant segregation.

The variable id should be a named constant that cites `Pay2SHAddress.scriptId` and the 5.x to 6.x change. The minimal alternative is to keep variable 1 and add `OptionGet`: that matches Fleet and the explorer today, which file variable-126 boxes under a P2S address; the maintainers choose between the two.

`recreate_from_ergo_tree` should recognize P2SH when the hashed input is `OptionGet(GetVar(id))`, `DeserializeContext` reads the same id (126 or 1), the hash is 24 bytes and the header is `0x00`, and return P2S otherwise. sigma-state 6.x classifies the variable-1 tree as P2S (its `IsPay2SHAddress` matches id 126 only, `reference-matcher.txt`), while this fix keeps classifying it as P2SH, so that Fleet and 5.x boxes keep their address; reviewers can decide. `script()` cannot know which form guards an existing box, so a spender of a variable-1 box reads the box script and populates variable 1.

Not covered by this fix: the bytes sigma-rust wrote through 0.28.0 stay unparseable by sigma-rust's stricter `CalcBlake2b256` type check. The reference parser accepts them and fails only at evaluation; #860 takes up that question.
