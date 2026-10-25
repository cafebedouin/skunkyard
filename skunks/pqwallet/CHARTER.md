# Skunk: pqwallet

**Status (2026-10-25):** step 5, first artifact posted: the derivation post is ergoforum topic 5385 (new topic, 2026-10-25, landed text equals the committed draft; `posts/2026-10-derivation-post-POST.md`). Second artifact, the vault's "what a wallet needs" note, next. Steps 1 to 4 passed (`RESULT.md`): derivation options with vectors; the signers and the assurance gate (three seats, `posts/seats/pqwallet-gate/r1/`); one signature per key (SK-055 variant 2, `skunks/qvault/QVault2.es`) on a devnet; the vault end to end on public testnet with every signature from the TypeScript signers (`testnet/RESULT-testnet.md`). Next: step 5, the hand-off. Born from the protocol post (thread 5372) and the roadmap's
forward path (`research/pq/ROADMAP.md`, "Update 2026-10-10", steps 2 and 3): the quantum-day vault runs on a devnet,
but no wallet signs its hash key, no derivation from a seed exists, and the SLH-DSA verifier has one oracle.

The groundwork for the day a hash-based spend path is wanted on Ergo: how a wallet derives post-quantum keys from
the seed it already has, a signer for the two hash schemes the vault and the rotating address use, and the vault
run end to end from one tool on testnet. Nothing here carries value until the assurance gate passes.

## Heilmeier

- **What.** Three things, in order. (1) A derivation of post-quantum key material from a wallet seed, with the
  options written out and implemented side by side, so the choice can be argued on the forum from running code
  rather than from preference. (2) A TypeScript signer for WOTS+ (the vault's sign-once key, `WotsPlus.es`) and for
  SLH-DSA-SHA2-128s (via `@noble/post-quantum`), each checked byte for byte against the Scala and Python vectors and
  against FIPS 205 known-answer vectors; the SLH-DSA half is also the gate's "second independent implementation".
  (3) The quantum-day vault end to end on testnet from the oneshot tool: seed to address, deposit, keyless merge, a
  demo flag fired by a demo oracle, the one hash-key migration into a fresh vault.
- **Today, and its limits.** The vault is judged on a devnet (39 of 39, `skunks/qvault/`), its WOTS+ key is built by a
  Python harness from random bytes, the SLH-DSA verifier has accepted signatures from one BouncyCastle key pair, and
  the oneshot page signs plain WOTS only. EIP-3 wallets derive `m/44'/429'/0'/0/i` with the last two levels
  non-hardened and export the depth-4 xpub for read-only wallets, so that xpub plus one quantum-recovered child key
  recovers the depth-4 private key and every descendant (computed, `test/derive.test.ts` check 7; the first draft
  of this sentence said "account key", which overstates it: a hardened branch above that node is not reached):
  post-quantum keys must not hang under any node whose xpub a wallet may export.
- **What is new.** A derivation whose root shares nothing with the secp keys but the BIP39 seed bytes; a signer that
  a wallet or a page can take as is; a differential run that gives the SLH-DSA verifier a second and third oracle;
  the vault as a flow a person can click through, not a harness row.
- **Who cares.** Wallet teams, who get a derivation to argue with and a signer to try; the maintainers, who get the
  derivation question on the forum before anyone needs an answer; holders, later.
- **Risks.** A signer that disagrees with the verifier on one vector means one of them is wrong, and the verifier is
  the one that would lose funds. Forced reuse after migration (SK-055): a payment arriving after the hash-key spend
  can leave only by a second signature under the one-time key; the flow is not finished until the script enforces
  one signature per key. Governance of the mainnet flag: the oracle key's holder, or a miner signal, is not ours to
  decide; the testnet flow uses a demo oracle and says so.
- **Cost.** One person and a model; four to six sessions. Dependencies: `@noble/post-quantum`, `@noble/hashes`,
  the existing oneshot tooling. One devnet session for SK-055; testnet ERG for the flow.
- **Checks.** Each step has one printed line that passes or fails (below). Final: a testnet transaction chain for
  the vault from deposit to migration, every signature produced by the TypeScript signer, every forgery row refused.

## Kill criteria

- The WOTS+ signer does not reproduce the Python harness's keys, commitment and signature byte for byte after one
  session of debugging: stop and find out which side is wrong before anything else is built.
- noble and BouncyCastle disagree with the script on any vector, or the one-byte-flip control does **not** refuse:
  the differential is not trusted, and no value-bearing claim is made until the disagreement is explained.
- Neither SK-055 option enforces one signature per key on the devnet without stranding a late payment: the vault
  flow ships with the wallet warning only ("stop publishing the address before migrating") and says so in the post.

## Sequence

1. **Derivation, options implemented.** `DERIVATION.md`: the options with their failure modes, at least these:
   (A) hardened children under the EIP-3 account key (rejected if the xpub argument above holds); (B) a separate
   root, `HMAC-SHA512(key = a fixed domain string, data = BIP39 seed bytes)`, SLIP-0010 style, hardened-only
   children, per-use leaves derived by a PRF: WOTS+ chain secrets and the per-vault public seed, and the 3n-byte
   SLH-DSA keygen seed; (C) a second mnemonic. Implemented in `src/derive.ts` for (A) and (B) with printed vectors
   (`vectors/derive-*.json`). Pass: the same seed phrase yields the same vault address and the same SLH-DSA public
   key across two runs and in a test, and (A) and (B) produce different keys from the same account.
2. **Signers and the gate.** `src/wotsplus.ts` against the Python harness vectors (`skunks/policy/6-rekey/`,
   `skunks/qvault/devnet-test.py`); `src/slhdsa.ts` wrapping noble, against `slhdsa/vectors.json`, FIPS 205 KATs,
   and a differential over many keys and messages with the script verifier in the q2 harness and BouncyCastle; the
   flip control first; a chosen-digest spend near the 3,570-step cap. Pass: zero disagreements after the control
   refused, printed, under `skunks/policy/6-rekey/slhdsa/` next to the existing results.
3. **One signature per key (SK-055), devnet.** Two shapes on the vault, same row set: option 1 from the worklist
   (the leaf signs `H(C' ‖ payBoxId ‖ H(outputs))`, a keyless forward path moves any other box at the key to C'
   using the published signature); and a variant to compare, a successor address committed at creation and a
   keyless forward to it open only after quantum day or the backstop, no signature needed (cheaper by one
   verification per box; fixes C' at creation, which the seed makes recoverable). Pass: `r3-reclaim-2`'s shape
   becomes a keyless forward and ACCEPTs, no row needs a second signature, a forward to anything but C' REFUSEs,
   the schedule's rows unchanged. Record which shape the flow takes and why.
4. **The flow on testnet.** The vault tree with step 3's shape, keys from step 1, signed by step 2, driven by the
   oneshot tool (CLI first, the page if cheap): deposit, keyless merge, demo flag fired, migration spend into a
   fresh vault, a late payment forwarded. Pass: the transaction ids printed in `RESULT.md`, a forged migration
   refused by the node.
5. **Hand-off.** A forum post on the derivation options with the vectors (the discussion the derivation needs); the
   "what a wallet needs" note for the vault, labelled with the gate's result; both through the seats. Kushti's two
   trigger paths are both recorded: the oracle flag (built) and a miner flag in the block extension, which a stock
   6.0.7 miner cannot write and a patched one can (`skunks/policy/3-extension/`); the miner path is a node or
   Lithos item, not this skunk's.

## Not in scope

The mainnet flag box and its governance; a hardware-wallet signer; the rotating SLH-DSA receive-address contract
(the verifier exists, the contract does not; it follows once the signer and the gate exist); any mainnet vault.
