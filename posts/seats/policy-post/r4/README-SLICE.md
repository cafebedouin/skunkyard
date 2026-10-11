# What is here

`POST-DRAFT-PROTOCOL.md` is the protocol post, the fourth round of review of a draft for the Ergo forum
(ergoforum.org), split in two after the second round, not yet posted; the wallet post is reviewed separately and
is not in this slice. `POST-LESSONS.md`
is a short companion document on the defects the reviews found. The wallet post's audience is wallet developers;
the protocol post's is the node and protocol side. It says that opt-in "policy" contracts on Ergo boxes
work without a fork: two run on mainnet (KeepAlive, a two-step withdrawal vault), the rest were tested on a devnet.
It lists what a wallet would need to add per policy, describes a three-member family of rotating-key receive
addresses, and reports that a FIPS 205 SLH-DSA-SHA2-128s verifier fits in an ErgoScript proposition.

`evidence/` holds the public material the draft relies on, copied from the repository
https://github.com/cafebedouin/skunkyard on 2026-10-10:

- `keepalive/`: KeepAlive contracts, README (with its mainnet demo table), devnet results, the mainnet tree and
  address, and the demo's transactions as built (`tx/`).
- `qvault/`: the quantum-day vault contracts (hash key now WOTS+), README, devnet results and harness.
- `policy/`:
  - the seven devnet experiments (contracts `*.es`, `README.md`, `results*.json`); `2-twostep/` includes
    `Pending2.es` (the cross-vault fix) and `mainnet/` (the mainnet table and transactions as built);
  - `6-rekey/` whole: `CHARTER.md`, `SCHEME-SIZING.md`, `README.md`, every contract (`FixedKey.es`,
    `RekeyAccount*.es`, `RekeySchedule.es`, `WotsPlus.es`), results, harnesses, and `slhdsa/` (the SLH-DSA verifier
    `SlhDsa.es`, its stages, the Python reference `slhdsa_ref.py`, the Scala harness, `results.json`,
    `results-devnet.json`, `vectors*.json`, `spends.json`, `run.log`). `vectors.json` holds a throwaway test
    private key, labelled as such in `slhdsa/README.md`;
  - `probe-sign-height.json` (the wallet-versus-check height probe);
  - `EXPERIMENTS.md` (the write-up, including the wallet-support list and the rulings);
  - `ergo-capabilities.md` (what an Ergo script can see).
- `oneshot/`: the two mainnet signers (`mainnet-sign.mjs`, `mainnet-sign-cancel.mts`), their description
  (`SIGNERS.md`), and the tree builder (`twostep-trees.mjs`).
- `mainnet-tx/`: the eight mainnet transactions the draft cites, as the public explorer (api.ergoplatform.com)
  returned them on 2026-10-10, one JSON file per transaction id.
- The four verdict files published after round two: `6-rekey/results-schedule.json`, `results-weld.json`,
  `results-planted.json`, `2-twostep/results-crossvault.json`; the re-run `results-wotsplus.json`,
  `qvault/devnet-results.json`, `slhdsa/results.json` and `results-devnet.json`.
- `REVIEW-ROUND3.md`: the review log of the third round (seven seats on both posts), so this round can verify
  that each fix landed.
- `REVIEW-ROUND2.md`: the review log of the second draft (seven seats, every finding with its check and
  disposition), so this round can verify that each fix landed.
- `evidence/template-hash.out`: the output of a parser over the three published mainnet trees (constant offsets,
  template Blake2b256 and SHA-256), now at `skunks/keepalive/template-hash.out` in the repository.
- `research/`: `ROADMAP-update.md` (the 2026-10-10 update section of `research/pq/ROADMAP.md`), `q2-RESULT.md`
  (the WOTS measurements and the per-block method), `lattice-RESULT.md` (SK-105: native verifier cost estimates).

Not here: the attack harnesses for the planted-box, cross-vault, weld and key-schedule rows (`old-*`, `new-*`,
`v2-*`, `v3-*`, `sched-*` in the READMEs) are kept outside the repository; the READMEs' tables are their public
record.

A devnet "case" or "row" was judged by an Ergo node 6.0.7. ACCEPT is the node's check returning 200; REFUSE is the
node's "should pass verification", or its wallet's "Script reduced to false". The `results*.json` files record each
verdict and its source. Costs are the node's mempool figures on devnet parameters (`inputCost` 2,000; mainnet 2,407).

Nothing here needs to be run. Judge from the files.
