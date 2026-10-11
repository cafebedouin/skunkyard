# qvault: a quantum-day vault with KeepAlive

A receive address that is safe from a quantum attacker and from storage rent, with no fork. kushti suggested it in
dev chat (2026-10-10): a vault spendable by `proveDlog` until an oracle or a miner signal declares quantum day, and
only by a hash-based signature after. The rent half is KeepAlive's (`skunks/keepalive/`), unchanged.

- `QDay.es` (148 bytes since round 3; 117 before): the quantum-day flag. A box holding a singleton NFT, R4 a Boolean.
  - It can go false → true only with the oracle's key, and never back.
  - Anyone may recreate it unchanged, which keeps it alive past rent age, but only in the last WINDOW blocks of each
    PERIOD (round 3: KeepAlive's refresh window; without it anyone could churn the box every block and void every
    pending owner spend, rows 7a–7f).
> **Hash key upgraded to WOTS+ (SK-053 swap, 2026-10-10).** The sign-once hash key is now WOTS+ (`WotsPlus.es`,
> simple tweakable-hash instantiation), not plain WOTS: every chain hash is keyed by a per-vault public seed
> (`PKSEED`) and the (chain, step) address, closing SK-035's multi-target gap. The suite re-ran on the policy devnet
> with the swap, **18/18 as before**. Cost rose about 18% (the tweak's per-step ops; 17.6% at 480 hashed steps,
> 18.8% at a random message's mean 506, `../policy/6-rekey/results-wotsplus-fit.json`).
> Round 2 (2026-10-10) adds a signature-length guard (`sig.size == 2144`) and the Cryptography-seat negatives on the
> hash key (rows 6a append, 6b truncate, 6c deep-flip, all REFUSE); the full suite is 21/21.

- `QVault.es` (1,247 bytes at devnet constants, 1,248 for the vault with the farther backstop; with the
  signature-length guard, `devnet-results.json` `vaults`): the vault. Three ways to spend it:
  - **owner key:** `proveDlog(OWNER)`, only while the flag box, shown as a data input and found by its NFT, says
    false, and `HEIGHT < BACKSTOP`. Leaving the flag box out, or showing a look-alike, closes this path rather than
    opening it.
  - **hash key:** a WOTS+ signature (n 32, w 16, Blake2b; `WotsPlus.es`) in context variable 1, over
    `blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef)`, each chain hash keyed by `PKSEED` and the (chain, step)
    address, checked against the owner's commitment `PKCOMMIT` (which binds `PKSEED`). Only one box of the vault per
    transaction, since a one-time key signs once.
  - **maintenance, no key:** KeepAlive's merge and lone refresh, as in `KeepAliveAddress.es`. It touches no key,
    so it gives a quantum attacker nothing.
- **The owner's way through quantum day:** first merge every payment into one box (keyless), then spend that box
  once with the hash key into a fresh vault.
- `devnet-test.py`: the harness. The spend message digest comes from `skunks/oneshot/scripts/wots-cli.mts`; the WOTS+
  key and signature are built in the harness (`wotsplus_keygen` / `wotsplus_sign`) against `WotsPlus.es`.

## Devnet result (2026-10-10): 18 of 18 as expected; 21 of 21 after round 2; 39 of 39 after round 3 (2026-10-11)

peeryard devnet `keepalive` (ergo 6.0.7, one mining node, 20 s blocks; `rig/devnet.sh expose A 9180 keepalive`).
The node wallet holds the owner key and a second, derived oracle key. Two vaults, each with its own WOTS key:
- FAR, whose backstop is far away;
- NEAR, whose backstop is 45 blocks after the start.

Results: `devnet-results.json`.

| # | case | expected | got |
|---|---|---|---|
| 1 | owner key spends A, flag box (false) as a data input | ACCEPT | ACCEPT |
| 2 | owner key spends A with no flag box | REFUSE | REFUSE |
| 3 | owner key spends A with a look-alike flag (another token) | REFUSE | REFUSE |
| 4 | hash key spends A | ACCEPT | ACCEPT |
| 5 | hash key: signed for one set of outputs, sent with another | REFUSE | REFUSE |
| 6 | hash key spends B and C together (a one-time key twice) | REFUSE | REFUSE |
| 6a | hash key, signature with 32 bytes appended (round 2) | REFUSE | REFUSE |
| 6b | hash key, signature truncated by 32 bytes (round 2) | REFUSE | REFUSE |
| 6c | hash key, a byte flipped deep in the signature (chain 33) (round 2) | REFUSE | REFUSE |
| 7 | keyless merge of B and C | ACCEPT (mined) | ACCEPT |
| 8 | lone refresh of A in the KeepAlive window, no key | ACCEPT | ACCEPT |
| 9 | owner key spends D after NEAR's backstop (flag still false) | REFUSE | REFUSE |
| 10 | hash key spends D after the backstop | ACCEPT (mined) | ACCEPT |
| 11 | flag false → true with no key | REFUSE | REFUSE |
| 12 | flag false → true by the oracle | ACCEPT (mined) | ACCEPT |
| 13 | flag true → false by the oracle | REFUSE | REFUSE |
| 14 | flag box refreshed unchanged, no key | ACCEPT | ACCEPT |
| 15 | owner key spends A, flag box (true) as a data input | REFUSE | REFUSE |
| 16 | owner key spends A with no flag box | REFUSE | REFUSE |
| 17 | keyless merge of A, the B+C box and a new payment E | ACCEPT (mined) | ACCEPT |
| 18 | hash key spends the merged box to the owner | ACCEPT (mined) | ACCEPT |

Round 3 (2026-10-11, the policy devnet; `devnet-results.json` is now this run, the round-2 file is in git at
`ba9df42`). Row 14 changed meaning with `QDay.es`'s window: it is now the refresh right after the oracle's flip.

| # | case | expected | got |
|---|---|---|---|
| 6d | hash key: another WOTS+ key's signature (same PKSEED) on A's digest | REFUSE | REFUSE |
| 6e | hash key: A's valid signature replayed on A2 (same vault, same outputs) | REFUSE | REFUSE |
| 7a | an owner spend of A citing the flag box, signed and held | signed | signed |
| 7b | the flag box refreshed unchanged, in its window, no key | ACCEPT (mined) | ACCEPT |
| 7c | the held owner spend submitted after 7b | REFUSE | REFUSE ("Every data input of the transaction should be in UTXO") |
| 7d | the refreshed flag box refreshed again at once (churn) | REFUSE | REFUSE (outside the window) |
| 7e, 7e2 | control: a flag box under the pre-window `QDay.es`, refreshed twice in a row | ACCEPT (mined) | ACCEPT, ACCEPT |
| 7f | the owner spend rebuilt on the refreshed flag box | ACCEPT | ACCEPT |
| 8a | FAR2 (its flag NFT minted with amount 2): owner spend with the real flag (false) | ACCEPT | ACCEPT |
| 8b | the oracle sets that flag true; owner spend with it | REFUSE | REFUSE |
| 8c | owner spend with the NFT's **second unit**, at a key address, R4 = false | ACCEPT | **ACCEPT**: the vault cannot tell |
| 8d | FAR3 (its flag NFT minted amount 1 **into a key address**, R4 = false): owner spend | ACCEPT | **ACCEPT**: the vault cannot tell |
| m1 | after NEAR's backstop and its hash-key spend (row 10), a new payment F1: owner key spends it | REFUSE | REFUSE |
| m2 | keyless merge of F1 and F2 at NEAR | ACCEPT (mined) | ACCEPT |
| m3 | NEAR's already-used hash key signs again, spending the merged box | ACCEPT | ACCEPT: the only way to move it |
| 14 | the flag box refreshed unchanged right after the oracle's flip (outside its window) | REFUSE | REFUSE |
| 14b | the same refresh once its window opens | ACCEPT | ACCEPT |

**What the round-3 rows settle.**
- **Churn (7a–7f) and the decision.** A pending owner spend cites the flag box by id; any refresh replaces that id, so
  the spend fails before any script runs (7c). Without a window anyone could do this every block (7e, 7e2). Decided:
  `QDay.es` gets KeepAlive's window: an unchanged refresh only in the last WINDOW blocks of each PERIOD, into a
  successor stamped at least HEIGHT − SLACK. On mainnet constants that is at most one refresh in about four years
  (PERIOD 1,051,200, WINDOW 21,600). Tree 117 → 148 B, template blake2b256 `4969eda9…`. The oracle's flip is unchanged.
- **Provenance (8a–8d).** The vault reads the flag by the NFT's token id alone, so a second unit, or a unit outside
  `QDay.es`, carrying R4 = false keeps the owner path open after quantum day. The contract does not check supply or
  mint; the wallet must, by reading the NFT's issuing transaction (amount 1, minted straight into `QDay.es`) before it
  builds a vault on that flag. A script check of the flag box's script would close 8d but not 8c.
- **After migration (m1–m3).** Once the hash key has signed (row 10), a later payment to the vault can be merged
  keylessly but leaves only by a second signature under that key: forced reuse of a one-time key. A wallet should
  stop publishing the address after migrating.

Rows 6a–6c are the Cryptography seat's negatives (round 2), each a mutation of row 4's honest hash-key spend; with
the length guard the full suite is 21 of 21 (`devnet-results.json`, re-run 2026-10-10). The other-key and replay
negatives were run on `WotsPlus.es` itself (`../policy/6-rekey/results-wotsplus.json`, `wp-otherkey`, `wp-replay`),
whose chain code is the hash key here, and in round 3 against `QVault.es` too (rows 6d, 6e).

**Where each refusal comes from:**
- **Key paths** (2, 3, 9, 13, 15, 16): the node's wallet answered "Script reduced to false". It evaluated the script
  in that exact context and found no path it could prove.
- **The rest** (5, 6, 6a–6c, 11): the node's own check, "Scripts of all transaction inputs should pass verification".

**What failed on the way:** two harness bugs, neither in the contracts.
- The node wallet spent the look-alike flag box as change. It now sits at a key nobody holds.
- The flag transactions added a fee with no input to pay it. On mainnet the refresher pays the fee from their own
  box; on the devnet (minimum fee 0) these transactions are fee-less, to test the script alone.

**Compiler note:** `!flags(0).R4[Boolean].get` parses as `(!flags)(0)…`. The script uses `== false`.

## Not done

- **The miner signal.** A script sees only the last 10 headers, so a miner flag would have to be written once into
  the monotone flag box. Anyone could flip it by proving the signal, if a Merkle proof against a header's extension
  root can be checked in script. Not tried. The devnet uses an oracle key.
- **Many-time hash keys** (SK-029's Merkle tree of WOTS leaves) instead of one WOTS key per vault, so the hash key
  survives more than one spend.
- **Mainnet constants** (PERIOD 1,051,200, WINDOW 21,600) and a mainnet flag box. Who runs the oracle is a
  governance question, not a contract one.
- **Size.** 1,178 bytes (1,233 after the WOTS+ swap, 1,247 with the length guard) against about 80 for an ordinary address. If such a box were left to rent, a claim would
  take about 1.5 ERG; KeepAlive's refresh is what makes that moot.
