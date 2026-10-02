Prepared with Claude Code (Anthropic, Claude Fable 5.1) for cafebedouin; executed: sigmastate-js 0.6.3 reduction of the resulting box script (recorded in the skunkyard project, link below).

## Summary

`ErgoAddress.toP2SH()` (`packages/core/src/models/ergoAddress.ts`, lines 186-190 at 0.12.0) hashes the full ErgoTree bytes:

```ts
const hash = blake2b256(this.#ergoTree).subarray(0, P2SH_HASH_LENGTH);
```

The reference (`Pay2SHAddress.apply(prop)` in sigmastate-interpreter, `data/shared/src/main/scala/org/ergoplatform/ErgoAddress.scala`) hashes the serialized proposition, which is the tree bytes without the ErgoTree header: for a P2PK address that is `08cd ++ pk` (35 bytes), not `0008cd ++ pk` (36 bytes). The two hashes differ, so `toP2SH()` returns a different address from the reference for the same script.

## Consequence

A P2SH box is spent by putting the proposition bytes into the context variable the box script reads; the script hashes that value and compares it with the 24-byte hash in the address. For an address made by `toP2SH()`, the hash in the box is of `0008cd ++ pk`, while the spender supplies `08cd ++ pk` (the only form `DeserializeContext` accepts). Reduction yields `false`: funds sent to a `toP2SH()` address cannot be spent.

Executed (sigmastate-js 0.6.3, reduce of the box script with variable 126 = `08cd ++ pk`): for pk `03f2dab4…`, the reference P2SH address is `qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i` and `ErgoAddress.fromErgoTree(<P2PK tree>).toP2SH()` gives `qGTwZAJmGFgsocxdWta7RdQbP9zoGADfhyD4EvK`; the box script for the latter reduces with `Script reduced to false`. Record: https://github.com/cafebedouin/skunkyard/blob/main/skunks/oneshot/recon/README.md (section "Address cross-check"; raw run in `recon/runs/node-run.txt`, lines 5-7 and 35).

## Related, for a decision rather than a fix

`fromHash` and `decode` write the P2SH box script that reads context variable 1 (`00ea02d193b4cbe4e3010e040004300e18 ++ hash ++ d40801`, lines 26-28), which is the sigma-state 5.x form. sigma-state 6.x reads variable 126 (`Pay2SHAddress.scriptId = 126`), and its address recreation classifies the variable-1 tree as P2S. Both forms spend on an ergo 6.0.6 node (one-node devnet, recorded in the same repository, `skunks/oneshot/RESULT.md`, "P2SH forms on a node"); which one SDKs should write is a question for the sigma-state maintainers, raised alongside ergoplatform/sigma-rust#928, where the Rust side wrote a third, unspendable form.

## Proposed fix

In `toP2SH()`, hash the proposition bytes (the ErgoTree body after the header, as `Pay2SHAddress.apply` does), not `this.#ergoTree`. A test: `ErgoAddress.fromErgoTree("0008cd" + pk).toP2SH()` must equal the reference address for the same key (`qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i` for the key above, testnet).

Not covered here: trees with constant segregation, where "the proposition bytes" are what `ErgoTree.toProposition(replaceConstants = true)` serializes; the reference substitutes constants first.
