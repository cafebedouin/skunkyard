# What is here

`POST-DRAFT.md` is a draft forum post for the Ergo forum (ergoforum.org), not yet posted. Its audience is wallet
developers. It says that opt-in "policy" contracts on Ergo boxes work without a fork. Two run on mainnet: KeepAlive,
and a two-step withdrawal vault. Five more were tested on a devnet. It lists what a wallet would need to add.

`evidence/` holds the public material the draft relies on, copied from the repository
https://github.com/cafebedouin/skunkyard on 2026-10-10:

- `keepalive/`: KeepAlive contracts, README (including its mainnet demo table) and devnet results.
- `qvault/`: the quantum-day vault contracts, README and devnet results.
- `policy/`:
  - the seven devnet experiments (contracts `*.es`, `README.md`, `results*.json`);
  - `2-twostep/mainnet/README.md` (the two-step mainnet table);
  - `EXPERIMENTS.md` (the write-up, including the wallet-support list and the rulings);
  - `ergo-capabilities.md` (what an Ergo script can see).
- `oneshot/`: the two mainnet signers (`mainnet-sign.mjs`, `mainnet-sign-cancel.mts`), their description
  (`SIGNERS.md`), and the tree builder (`twostep-trees.mjs`).
- `mainnet-tx/`: the eight mainnet transactions the draft cites, as the public explorer
  (api.ergoplatform.com) returned them on 2026-10-10, one JSON file per transaction id.

A devnet "case" or "row" was judged by an Ergo node 6.0.7. ACCEPT is the node's check returning 200; REFUSE is the
node's "should pass verification", or its wallet's "Script reduced to false". The `results*.json` files record each
verdict and its source.

Nothing here needs to be run. Judge from the files.
