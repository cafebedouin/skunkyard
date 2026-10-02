Prepared with Claude Code (Anthropic, Claude Fable 5.1) for cafebedouin using peeryard v0.1.0 (ba56b25) on 6.0.6 (21b9023933b1); executed on a devnet and public testnet, recorded in the skunkyard project (link below).

## Summary

Three box scripts are in circulation for the same P2SH address; one cannot be spent on the reference node. The address pages do not say which form is canonical. Measured, one address around `proveDlog(pk)`, each form funded on a devnet and spent through `POST /transactions`:

| writer | box script reads the inner script from | spend accepted by the node |
|---|---|---|
| sigmastate-interpreter 6.0.x (`Pay2SHAddress.script`), sigmastate-js | context variable 126, through `OptionGet` | yes |
| Fleet 0.12.0 (`toP2SH` box script) | context variable 1, through `OptionGet` | yes |
| sigma-rust / ergo-lib 0.28.0 (`Address::to_ergo_tree`) | context variable 1, no `OptionGet` | no: `ClassCastException: scala.Some cannot be cast to sigma.Coll` |

Also: Fleet's `toP2SH()` hashes the ErgoTree bytes, not the serialized proposition, so it derives a different address from the reference for the same script (Fleet issue 219); and the explorer files variable-126 boxes under P2S.

## Ask

On `docs/dev/wallet/address/address_types.md`: that "serialized script bytes" means the serialized proposition without the ErgoTree header (which is the Fleet bug); the canonical sigma 6.x box script (`00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e`, variable 126) and the spender's obligation to put the serialized inner script in that variable; the 5.x form (variable 1); the table above; and that P2SH hides a key only while the box is unspent and only for one use.

## References

- sigma-rust 928 / 929; Fleet 219.
- Box bytes and node responses: https://github.com/cafebedouin/skunkyard/blob/main/skunks/oneshot/RESULT.md ("P2SH forms on a node"); forum thread 5369, section 4.
