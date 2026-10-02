Prepared with Claude Code (Anthropic, Claude Opus 5.5) for cafebedouin, using peeryard v0.1.0 (ba56b25) on 6.0.6 (21b9023933b1). Branch `fix/p2sh-script-form` from `develop` (1633e018).

**Wrap `GetVar` in `OptionGet` in the P2SH box script**

Fixes #<issue number>

**Observed.** `develop`'s `ergotree-ir/src/chain/address.rs:221-230` hashes `GetVar(1)` without `OptionGet`. A 6.0.6 devnet node rejected both submitted spends of boxes with that tree (`ClassCastException`); sigma-rust cannot parse it. Tested on 0.28.0 only, unchanged since #407.

**Change.**
- `script()` writes the sigma-state 6.x form (variable 126). Keeping variable 1 and adding `OptionGet` would match Fleet and the explorer, which file variable-126 boxes under a P2S address; the maintainers choose.
- `recreate_from_ergo_tree` returns P2SH only for hashed `OptionGet(GetVar(id))` with `DeserializeContext(id)` (id 126 or 1), a 24-byte hash and header `0x00`; otherwise P2S, not an error. sigma-state 6.x classifies variable 1 as P2S.
- New public API: `P2SH_SCRIPT_VAR_ID`, `P2SH_SCRIPT_VAR_ID_V5`.

**Invariant kept.** P2PK, P2S and all address strings are unchanged. Callers see new P2SH `script()` bytes (also via `Contract::pay_to_address`) and `recreate` results.

**Open PRs.** None touches `address.rs`; #860 and #879 each affect one new test (details).

**Recommended:** merge after the maintainers choose 126 or 1; review commit by commit.

**Executed.** `tests-after.txt`, `clippy.txt`, `fmt.txt`, `tests-on-develop.txt`, `mutations.txt`, `runcard-develop.txt`, `runcard-fixed.txt`. Logs: no node run of this branch; the node evidence is the issue's.

Evidence: `p2sh_script_matches_tree_spent_on_node` pins the node-spent bytes.

**Not run.** wasm-pack; JS, Python, iOS binding tests (none covers a P2SH tree); a node spend of this tree.

<details>
<summary>Tests, mutations, open PRs and how to re-run</summary>

`rust-toolchain` is 1.91.1. Plain `cargo test -p ergotree-ir` does not compile on `develop` either (unused import in `ergo_box/register.rs` without `arbitrary`).

- `cargo test -p ergotree-ir --features arbitrary`: 278 passed (+2 doc).
- `cargo test -p ergotree-interpreter --features arbitrary`: 342 passed (+8 integration).
- `cargo test -p ergo-lib --features arbitrary,compiler,mnemonic_gen`: 121 passed (+1 doc).
- `cargo clippy -p <crate> --all-features --all-targets -- -D warnings` for ergotree-ir, ergo-lib, ergotree-interpreter, and `cargo fmt --all --check`: clean.

New tests, `ergotree-ir/src/chain/address.rs` (`p2sh_tests`):
- `p2sh_script_matches_reference_bytes`: `script()` equals sigmastate-js 0.6.3 `toErgoTree()`, `00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e`.
- `p2sh_script_matches_tree_spent_on_node`: `script()` equals `00ea02d193b4cbe4e37e0e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d4087e`, spent with variable 126 on the 6.0.6 devnet node.
- `p2sh_script_roundtrips_through_bytes`, `p2sh_script_recreates_p2sh_address`: serialize, parse, recreate.
- `recreate_p2sh_from_reference_tree_bytes`, `recreate_p2sh_from_legacy_var1_option_get_tree`: the 6.x and 5.x/Fleet trees are P2SH.
- `recreate_p2s_from_legacy_var1_no_option_get_tree`, `legacy_var1_no_option_get_bytes_do_not_parse`: the 0.28.0 form is P2S; its bytes fail with expected `SColl(SByte)`, got `SOption(SColl(SByte))`.
- `recreate_p2s_for_other_deserialize_context_var`, `recreate_p2s_for_mismatched_get_var_and_deserialize_context_ids`, `recreate_p2s_for_hash_input_other_than_option_get_get_var`: variable 2, mismatched ids, a constant or `OptionGet(SELF.R4)` hashed are P2S.
- `recreate_p2s_for_segregated_constants_header`, `recreate_p2s_for_v1_header`: the 6.x expression under header `0x10`, `0x09` or `0x19` is P2S.
- `recreate_p2s_for_hash_constant_not_24_bytes`: a 23-, 25- or 32-byte hash gives P2S, not an error.

New tests, `ergotree-interpreter/src/sigma_protocol/verifier.rs` (`p2sh_tests`):
- `p2sh_script_with_var_126_reduces_to_proposition_and_verifies`: `08cd ++ pk` in variable 126 reduces to `proveDlog(pk)`; a proof verifies.
- `p2sh_script_with_var_126_of_other_proposition_reduces_to_false`: another key's proposition in variable 126 reduces to `TrivialProp(false)` (the hash check rejects, not an error).
- `p2sh_script_with_only_var_1_fails_to_reduce`: fails with `SubstDeserializeError(ExtensionKeyNotFound(126))`, before `OptionGet`/`GetVar` run.

On `develop` (`tests-on-develop.txt`; module appended, the two constants defined locally, `OptionGet` and `OneArgOpTryBuild` imported): 7 of 14 ir tests and all 3 interpreter tests fail. The header, hash-length, other-variable and other-input tests pass there, since `develop` never classifies a variable-126 tree as P2SH; the mutations below show they can fail.

Mutations (`mutations.txt`, each reverted; `git diff --stat` empty at the end):
- `CalcBlake2b256` input type check removed: `legacy_var1_no_option_get_bytes_do_not_parse`.
- Id equality dropped: `recreate_p2s_for_mismatched_get_var_and_deserialize_context_ids`.
- Any hash input accepted: that test, `recreate_p2s_for_hash_input_other_than_option_get_get_var`, `recreate_p2s_from_legacy_var1_no_option_get_tree`.
- `P2SH_SCRIPT_VAR_ID = 1`: both byte tests, `recreate_p2sh_from_reference_tree_bytes`, the mismatched-ids test, all three interpreter tests.
- `OptionGet` dropped from `script()`: the four `p2sh_script_*` ir tests, all three interpreter tests.
- Header check dropped: `recreate_p2s_for_segregated_constants_header`, `recreate_p2s_for_v1_header`.
- 24-byte check dropped (back to `Err`): `recreate_p2s_for_hash_constant_not_24_bytes`.

Open PRs (`open-prs-address-rs.txt`, 65 open): none touches `address.rs`. #860 widens `check_post_eval_tpe` to accept `SOption(T)` for `T`; its test parses the 0.28.0 form from mainnet block 1,711,120. If it merges, `legacy_var1_no_option_get_bytes_do_not_parse` must change, and those bytes parse and are classified P2S. #879 leaves an absent-variable `DeserializeContext` unsubstituted; if it merges, the variable-1 test fails at evaluation instead of substitution.

Matching rule against the reference (`reference-matcher.txt`): sigma-state 6.0.6 `IsPay2SHAddress` requires id 126 and accepts any `CalcHash` input, any header and any hash length. This branch also accepts id 1 and is stricter on the input, the header and the length.
</details>
