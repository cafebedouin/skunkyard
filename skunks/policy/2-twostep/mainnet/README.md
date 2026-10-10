# The two-step withdrawal vault on mainnet (2026-10-10)

The skunkyard test wallet's two-step vault ran on mainnet: an announce, a completion with no vault signature, and a
cancel by a recovery key.

**Trees** (`skunks/oneshot/scripts/twostep-trees.mjs`): the devnet-tested `Vault.tree` and `Pending.tree`
(`skunks/policy/2-twostep/`, 23 + 5 rows) with only the owner and recovery key constants substituted, each placeholder
found exactly once. No hand-edited tree.
- Vault 332 B, pending 187 B.
- **Owner:** the wallet's key, `m/44'/429'/0'/0/0`.
- **Recovery:** a different key, the wallet's second derivation path `m/44'/429'/0'/0/1`.
- **DELAY is 15 blocks,** the tested value, so the tree is the tested tree with only keys changed. A real vault would
  use hundreds: the logic is byte-identical and only the constant differs.

**Signers.**
- `mainnet-sign.mjs` signs the deposit, the announces and the completion with the wallet key.
  - It recognises the vault and pending trees, built as above.
  - A pending box is an allowed destination only when its R4 destination is the wallet's own tree and its R6 is this
    vault. Checked: a pending box to another destination is refused.
- `mainnet-sign-cancel.mts` signs the cancel and nothing else.
  - It holds only the recovery secret and signs with sigmastate-js. The pending box's "owner or recovery" is a sigma
    OR, which a single-key proof can't make.
  - It accepts only one shape: the pending box plus a box at the recovery address in; the vault (exactly the pending
    value) out first. Checked: a cancel whose first output isn't the vault is refused.

**Heights.** Every time-locked transaction was built for the next block and judged by the node's
`/transactions/check` (the wallet-versus-check height offset).

| step | transaction | height | signed by | what happened |
|---|---|---|---|---|
| 1 deposit | `029fc1e8f901cd98a88f27c629d3bf0f6e8e1581ae94a3a29a7fbaeece11acd8` | 1,891,686 | wallet | vault boxes V1 `94b28fca…` and V2 `d5e41585…` (0.005 ERG each); a 0.003 ERG fee box at the recovery address |
| 2 announce V1 | `7e20f56920cd0e5b5880438c892964b42a5ccc15c5be0ec600ac4a82f1c187e0` | 1,891,688 | owner key (vault), wallet (fee box) | pending P1 `80ac3857…`, destination the wallet, deadline 1,891,705 |
| 4 announce V2 | `5f4c29d28a752f7d5ec73c722878c5eba3bdd767909600eb99ddd840cfaefa5f` | 1,891,690 | owner key, wallet | pending P2 `45423e6b…`, deadline 1,891,707 |
| 5 recovery cancel P2 | `1304806181bb3c6d0bf389bc5a2536ec07f321b32a2fb7a8c04add7c7b5a8875` | 1,891,692 | **recovery key only** | P2 back into the vault (`f22a0443…`, 0.005 ERG), 15 blocks before its deadline; the recovery box paid the fee, its change went to the wallet |
| 3 complete P1 | `b25c7550a6a36f7ee887c03089ff825769afe7b3c39872eb3f39a94eca3e6be1` | 1,891,706 | **no vault or pending signature**; a wallet box paid the fee | P1's 0.005 ERG to the wallet at its deadline (next block 1,891,705 ≥ R5) |

**Order.** The steps are numbered in the requested order (announce, complete, announce, cancel), but ran on chain as
1, 2, 4, 5, 3. V2 was announced while P1's deadline ran down, and the cancel had to fall well inside V2's window
(about 15 blocks before its deadline), so it landed before P1's completion. Both paths are on chain; the cancel
happened first.

**Cost and balance.**
- 0.01 ERG went into the vault: 0.005 came back by completion, and 0.005 remains in the vault (`f22a0443…`, the
  cancelled V2, still the owner's to announce).
- Fees: 5 × 0.0011 ERG.
- Wallet 21.213324102 ERG, reconciling to the nanoERG: 21.223824102 − 0.0141 − 0.0011 − 0.0011 + 0.005 − 0.0011 +
  0.0019.
- Ledger lines in `skunks/upkeep/mainnet/ledger.jsonl`.

Both mainnet signers (what each holds, accepts and refuses): `skunks/oneshot/SIGNERS.md`.
