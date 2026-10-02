Prepared with Claude Code (Anthropic, Claude Opus 5.5) for cafebedouin, using peeryard v0.1.0 (ba56b25) on 6.0.6 (21b9023933b1); executed: crate tests; the skunkyard project's devnet verdicts on that node. Branch `fix/p2sh-script-form`, from `develop` (1633e018), targets `develop`.

Fixes #<issue number>

**Observed.** On `develop`, `ergotree-ir/src/chain/address.rs:221-230` hashes `GetVar(1)` without `OptionGet`. A 6.0.6 devnet node (block version 4) rejected both submitted spends of that box: `ClassCastException: class scala.Some cannot be cast to class sigma.Coll`. sigma-rust cannot parse the tree; `address.rs:128` recognizes only variable 1.

**Change.**
- `Address::script()` writes the sigma-state 6.x `Pay2SHAddress.script` form: `OptionGet(GetVar(126))` hashed, `DeserializeContext(126)`, header `0x00`, no constant segregation.
- `recreate_from_ergo_tree` returns P2SH only for a hashed `OptionGet(GetVar(id, Coll[Byte]))` with `DeserializeContext` of the same id, 126 or 1: the 6.x and 5.x/Fleet forms. The 0.28.0 form still does not parse from bytes, and is P2S when built in memory.

**Invariant.** A P2SH address survives `script()`, serialization, parsing and recreation. The existing `recreate_roundtrip` proptest never serialized or parsed; `p2sh_script_recreates_p2sh_address` does. Falsifier: bytes differing from sigmastate-js's for the same hash.

**Release note.** Published sigma-rust through 0.28.0 wrote unspendable P2SH box scripts. New boxes need context variable 126 holding the serialized proposition as `Coll[Byte]`. `script()` will not rebuild a variable-1 box (Fleet, sigma-state 5.x); spenders read the box script.

**Recommended:** review commit by commit.

**Executed.** Tests, clippy, fmt pass; each new test fails when its rule breaks (details).

**Not run.** wasm-pack, JS tests, a node spend of this branch's tree. The `ClassCastException` reproduction needs a node; the issue carries the transaction.

<details>
<summary>Tests and how to re-run them</summary>

`rust-toolchain` is 1.91.1. Plain `cargo test -p ergotree-ir` does not compile on `develop` either (unused import in `ergo_box/register.rs` without `arbitrary`).

- `cargo test -p ergotree-ir --features arbitrary`: 275 passed.
- `cargo test -p ergotree-interpreter --features arbitrary`: 341 passed.
- `cargo test -p ergo-lib --features arbitrary,compiler,mnemonic_gen`: 121 passed.
- `cargo clippy -p ergotree-ir -p ergo-lib --all-features --all-targets -- -D warnings` and `cargo fmt --all --check`: clean.

New tests in `ergotree-ir/src/chain/address.rs` (`p2sh_tests`):
- `p2sh_script_matches_reference_bytes`: `script()` equals sigmastate-js 0.6.3 `Address$.fromString(addr).toErgoTree()`, `00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e`.
- `p2sh_script_matches_tree_spent_on_node`: `script()` equals the tree spent on the devnet node.
- `p2sh_script_roundtrips_through_bytes`: the tree serializes, parses back equal, and re-serializes to the same bytes.
- `p2sh_script_recreates_p2sh_address`: address to tree to bytes to tree to the same address.
- `recreate_p2sh_from_reference_tree_bytes`: the 6.x tree read from bytes is P2SH.
- `recreate_p2sh_from_legacy_var1_option_get_tree`: the 5.x/Fleet tree is P2SH.
- `recreate_p2s_from_legacy_var1_no_option_get_tree`: the 0.28.0 form is P2S.
- `legacy_var1_no_option_get_bytes_do_not_parse`: its bytes fail to parse with expected `SColl(SByte)`, got `SOption(SColl(SByte))`.
- `recreate_p2s_for_other_deserialize_context_var`: variable 2 is P2S.
- `recreate_p2s_for_mismatched_get_var_and_deserialize_context_ids`: `GetVar(1)` with `DeserializeContext(126)`, and the reverse, are P2S.
- `recreate_p2s_for_hash_input_other_than_option_get_get_var`: a constant or `OptionGet(SELF.R4)` hashed is P2S.

New tests in `ergotree-interpreter/src/sigma_protocol/verifier.rs` (`p2sh_tests`):
- `p2sh_script_with_var_126_reduces_to_proposition_and_verifies`: the `script()` tree, read from bytes, with `08cd ++ pk` in variable 126, reduces to `proveDlog(pk)`, and a proof by the secret verifies.
- `p2sh_script_with_only_var_1_fails_to_reduce`: the same with variable 1 instead does not reduce.

Each fails when its rule is broken:
- On `develop` 1633e018 (the tests added to its `address.rs`): the first five above, `recreate_p2s_from_legacy_var1_no_option_get_tree`, `recreate_p2s_for_mismatched_get_var_and_deserialize_context_ids`, and both interpreter tests (the tree does not parse) fail.
- `CalcBlake2b256` input type check removed: `legacy_var1_no_option_get_bytes_do_not_parse` fails.
- Id equality dropped from the matcher: `recreate_p2s_for_mismatched_get_var_and_deserialize_context_ids` fails.
- Any hash input accepted: that test, `recreate_p2s_for_hash_input_other_than_option_get_get_var` and `recreate_p2s_from_legacy_var1_no_option_get_tree` fail.
- `P2SH_SCRIPT_VAR_ID` set to 1, or `OptionGet` dropped from `script()`: both interpreter tests fail.
</details>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
