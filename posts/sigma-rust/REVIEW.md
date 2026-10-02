# Review record for the sigma-rust P2SH issue and pull request (2026-10-02)

Texts: `ISSUE.md`, `PR.md`, `PR-TITLE.txt`. Branch: `fix/p2sh-script-form` in the clone `~/bin/sigma-rust-pr`, three
commits on `develop` 1633e018. Captures for every executed claim: `captures/`. Not filed, not pushed.

## Reviews run, in order

| Pass | Who | On |
|---|---|---|
| Outside A | Gemini (gemini-3.8-flash via agy, sandboxed) | first texts and diff |
| Outside B | Grok (grok-4.7, web off, sandboxed) | first texts and diff |
| Fix pass | Claude (Opus 5.5) | applied the points both outside seats agreed on |
| Seat 1 derivation | Claude (Opus 5.5), fresh instance, code first | revised texts and diff |
| Seat 2 fidelity | Claude (Opus 5.5), fresh instance | revised texts against evidence and peeryard's rules |
| Seat 3 maintainer | Claude (Opus 5.5), fresh instance, as the sigma-rust maintainers | revised texts |
| Revision pass | Claude (Opus 5.5) | applied the three seats' points, produced the captures |

Raw outside-seat outputs: `seats/`. The internal seats' reports were returned to the session; their points are
itemized below.

## What the reviews changed

**From the outside seats (fix pass).** The matcher now requires `OptionGet(GetVar(id))` with the same id as
`DeserializeContext`; tests that the 0.28.0 bytes fail to parse and that sigma-rust's own interpreter evaluates the
new tree with variable 126 (and fails to reduce with variable 1 only); "ergo 6.0.6 rejects every spend" became "a
6.0.6 devnet node rejected both submitted spends"; the release note states three facts (0.28.0 wrote an unspendable
tree; new boxes need variable 126; `script()` will not rebuild a variable-1 box); the full rejected transaction is in
the issue; project names left the body; the search inventory became two sentences with its scope.

**From the three seats (revision pass).** The variable-1 interpreter test asserts the actual failure
(`ExtensionKeyNotFound(126)` at deserialize substitution) and a new test shows a hash mismatch reduces to `false`
rather than erroring; P2SH recognition requires the v0 header without constant segregation and a 24-byte hash,
returning P2S otherwise instead of an error; the legacy constant is `P2SH_SCRIPT_VAR_ID_V5`; the changelog carries
two Fixed entries (the script; the matcher that accepted any hashed input) and one Changed entry, scoped to 0.28.0 as
the only version tested; the PR states the 126-versus-1 trade-off, that sigma-state 6.x classifies the variable-1
tree as P2S while this fix keeps it P2SH, the new public API, the caller-visible changes (`Contract::pay_to_address`
and the bindings' `to_ergo_tree`), the open-PR check, a merge verdict conditional on the maintainers' choice, and an
evidence line; the issue's run card pins the base commit and the dependency, exits 1 on the defect and 0 on the fix,
and gives both outputs with measured build times; the `NonConsumedBytes` mechanism was verified against the 0.28.0
tag and commit f6048c1e and kept.

**Corrections the revision made to the reviewers' own claims.** `tx_builder.rs:868` is inside a test, so the claimed
production comparison did not exist; the real caller named is `Contract::pay_to_address`. The run-card exit condition
in the brief was inverted and was fixed. The reference's own `IsPay2SHAddress` accepts any hashed input with id 126, so
the loose matcher was not a sigma-rust-only property; the texts describe it neutrally.

## Found by the reviews, beyond the texts

- **A mainnet box in the sigma-rust form exists.** Open sigma-rust PR #860 makes the 0.28.0 bytes parse; its test
  vector is a box in exactly this form at mainnet block 1,711,120. So the defect has at least one real instance on
  mainnet, and if #860 merges, `legacy_var1_no_option_get_bytes_do_not_parse` must change. Both texts say so.
- **The classification question is a reference question too.** sigma-state 6.x's matcher requires id 126 and accepts
  any hashed input; this branch is stricter than the reference and also accepts id 1. The forum post's ask 2 ("which
  script is canonical") is where that belongs.
- **Not verified:** that the explorer files variable-126 boxes under a P2S address was observed on testnet in the
  oneshot runs but not re-checked here; the Fleet classification behavior was (`captures/fleet-p2sh.txt`).

## Before filing (the person's decisions)

1. Whether to send kushti a one-line private note about the matcher accepting any hashed input (a classification
   issue affecting anything that trusts `recreate_from_ergo_tree`; no funds at risk; the reference behaves the same).
2. File the issue, put its number into `PR.md` (`Fixes #<n>`), push the branch, open the PR with `PR-TITLE.txt`.
3. Attach or link `captures/` (they are not in the sigma-rust branch).
