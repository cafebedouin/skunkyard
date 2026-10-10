# qvault: a quantum-day vault with KeepAlive

A receive address that is safe from a quantum attacker and from storage rent, with no fork. kushti suggested it in
dev chat (2026-10-10): a vault spendable by `proveDlog` until an oracle or a miner signal declares quantum day, and
only by a hash-based signature after. The rent half is KeepAlive's (`skunks/keepalive/`), unchanged.

- `QDay.es` (117 bytes): the quantum-day flag. A box holding a singleton NFT, R4 a Boolean.
  - It can go false → true only with the oracle's key, and never back.
  - Anyone may recreate it unchanged, which keeps it alive past rent age.
- `QVault.es` (1,177 bytes at devnet constants): the vault. Three ways to spend it:
  - **owner key:** `proveDlog(OWNER)`, only while the flag box, shown as a data input and found by its NFT, says
    false, and `HEIGHT < BACKSTOP`. Leaving the flag box out, or showing a look-alike, closes this path rather than
    opening it.
  - **hash key:** a WOTS signature (n 32, w 16, Blake2b; `q2/wots-constant.es` specialised) in context variable
    1, over `blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef)`, checked against the owner's commitment `PKCOMMIT`.
    Only one box of the vault per transaction, since a one-time key signs once.
  - **maintenance, no key:** KeepAlive's merge and lone refresh, as in `KeepAliveAddress.es`. It touches no key,
    so it gives a quantum attacker nothing.
- **The owner's way through quantum day:** first merge every payment into one box (keyless), then spend that box
  once with the hash key into a fresh vault.
- `devnet-test.py`: the harness. WOTS keys and signatures come from `skunks/oneshot/scripts/wots-cli.mts` (the
  oneshot signer, byte-exact against the sigma-state vectors).

## Devnet result (2026-10-10): 18 of 18 as expected

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

**Where each refusal comes from:**
- **Key paths** (2, 3, 9, 13, 15, 16): the node's wallet answered "Script reduced to false". It evaluated the script
  in that exact context and found no path it could prove.
- **The rest** (5, 6, 11): the node's own check, "Scripts of all transaction inputs should pass verification".

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
- **Size.** 1,177 bytes against about 80 for an ordinary address. If such a box were left to rent, a claim would
  take about 1.5 ERG; KeepAlive's refresh is what makes that moot.
