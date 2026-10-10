# The mainnet signers

Two scripts sign with the skunkyard mainnet test wallet (`~/.config/skunkyard/mainnet-wallet.txt`, 24 words, mode
600; made by `scripts/mainnet-wallet.mjs`). Nothing else in this repository signs mainnet transactions.

Both:
- read the mnemonic and never print it;
- require a node's `/transactions/check` before anything is submitted;
- require `--purpose` with `--submit`, and append each submission to `skunks/upkeep/mainnet/ledger.jsonl`;
- keep the day's loss in `~/.config/skunkyard/mainnet-spend.json` (mode 600) under one shared daily cap.

## `scripts/mainnet-sign.mjs`: the wallet key

- **Secret:** the wallet key, `m/44'/429'/0'/0/0`. It derives the recovery key's *public* key only, to recognise the
  recovery address and the two-step trees, and never signs with it.
- **Signs:**
  - inputs at the wallet's P2PK tree;
  - inputs at the wallet's two-step vault (once its announce conditions hold, that vault reduces to `proveDlog`
    of the wallet key).

  Every other input is left keyless, with its context extension kept.
- **Outputs it allows:**
  - the wallet;
  - the wallet's KeepAlive vault (`skunks/keepalive/kaa-mainnet-G.tree` with the wallet key, placeholder found
    once);
  - the wallet's two-step vault (`scripts/twostep-trees.mjs`);
  - the recovery address;
  - the miner-fee contract;
  - a successor at any input's own script;
  - a two-step **pending** box, only when its R4 destination is the wallet's own tree and its R6 is the wallet's
    vault.
- **Refuses:**
  - any other destination;
  - a pending box to any other destination (checked 2026-10-10 with a pending box addressed to the recovery
    address);
  - a non-positive value or token amount;
  - a fee above `--max-fee` (0.005 ERG);
  - a wallet loss above `--max-loss` (0.5 ERG) in one transaction, or above `--day-cap` (5 ERG) in a day;
  - any input already spent.
- **Used for:** the Babel takes, the swaps, the U1c takes, the KeepAlive demo, and the two-step deposit, announces
  and sponsored completion.

## `scripts/mainnet-sign-cancel.mts`: the recovery key, for one shape only

- **Secret:** the recovery key only, `m/44'/429'/0'/0/1` (the wallet's second derivation path). The main signer
  never uses it.
- **The one shape it accepts:**
  - exactly two inputs: a box at the wallet's two-step pending tree, then a box at the recovery address (which pays
    the fee);
  - no data inputs;
  - output 0 at the wallet's two-step vault with exactly the pending box's value and tokens;
  - every other output to the wallet, the recovery address or the fee contract, with no tokens;
  - fee at most `--max-fee`; loss under `--max-loss` and the shared day cap.
- **Signing:** with sigmastate-js against the node's last 10 headers. The pending box's guard is a sigma OR (owner
  or recovery), which Fleet's single-key proof can't make. Its prover holds only the recovery secret, so the OR is
  proved through the recovery branch.
- **Refuses:** any other shape. Checked 2026-10-10: a cancel whose output 0 was the wallet instead of the vault was
  refused.
- **Used for:** the two-step mainnet demo's recovery cancel (`skunks/policy/2-twostep/mainnet/README.md`).
