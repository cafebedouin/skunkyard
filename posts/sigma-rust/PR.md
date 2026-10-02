Prepared with Claude Code (Anthropic, Claude Opus 5.5) for cafebedouin, using peeryard v0.1.0 (ba56b25) on 6.0.6 (21b9023933b1); executed: crate tests, and the devnet verdicts the skunkyard project recorded on that node. Branch `fix/p2sh-script-form`, from `develop` (1633e018), targets `develop`.

Fixes #<issue number>

**Observed.** `ergotree-ir/src/chain/address.rs:221-230` hashes `GetVar(1)` with no `OptionGet` before it. ergo 6.0.6 rejects every spend of that box with `ClassCastException: class scala.Some cannot be cast to class sigma.Coll`. sigma-rust also cannot parse the tree back from its bytes. In addition, `address.rs:128` recognizes only variable 1.

**Change.** `Address::script()` now writes the form of sigma-state 6.x `Pay2SHAddress.script`: `OptionGet(GetVar(126))` and `DeserializeContext(126)`, with header `0x00` and no constant segregation. The id lives in `P2SH_SCRIPT_VAR_ID` (126; it was 1 in 5.x). `recreate_from_ergo_tree` accepts 126 and the legacy id 1.

**Invariant kept and falsifier.** An address round-trips through its tree (the existing `recreate_roundtrip` proptest still passes). The change is falsified if the tree bytes differ from what sigmastate-js writes for the same hash.

**Recommended.** Merge; release-note that boxes sigma-rust ≤0.28 paid to P2SH addresses cannot be spent.

**Executed.**
- `cargo test`: ergotree-ir 272 passed; ergo-lib 121 passed.
- clippy `-D warnings` and fmt: clean.
- Eight new tests:
  - Five fail on `develop`.
  - Three fail under mutation: two when the legacy id is dropped, one when any id is accepted.
- The fixed tree is byte-equal to the sigmastate-js tree.

**Not run.** wasm-pack, the JS tests, and a node spend of a tree built by this branch.

**Evidence.** The devnet table is in the issue.

<details>
<summary>To reproduce without this tool</summary>

1. `git checkout fix/p2sh-script-form`. The `rust-toolchain` is 1.91.1.
2. `cargo test -p ergotree-ir --features arbitrary p2sh_tests` passes 8 tests. Plain `cargo test -p ergotree-ir` does not compile on `develop` either, because of an unused import in `ergo_box/register.rs` without `arbitrary`.
3. `git checkout 1633e018 -- ergotree-ir/src/chain/address.rs`, append the `p2sh_tests` module from this branch, and replace `LEGACY_P2SH_SCRIPT_VAR_ID` with `1`. Re-run: `p2sh_script_matches_reference_bytes`, `p2sh_script_matches_tree_spent_on_node`, `p2sh_script_roundtrips_through_bytes`, `p2sh_script_recreates_p2sh_address` and `recreate_p2sh_from_reference_tree_bytes` fail.
4. On this branch, change the id pattern at `address.rs:149` to `P2SH_SCRIPT_VAR_ID` only. Both `recreate_p2sh_from_legacy_*` tests fail. Change it to `_`: `recreate_p2s_for_other_deserialize_context_var` fails.
5. `cargo clippy -p ergotree-ir -p ergo-lib --all-features --all-targets -- -D warnings` and `cargo fmt --all --check` report nothing.
6. `cargo test -p ergo-lib --features arbitrary,compiler,mnemonic_gen` passes 121 tests.
7. The test vectors `00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e` come from sigmastate-js 0.6.3, `Address$.fromString(addr).toErgoTree().toHex()`.
</details>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
