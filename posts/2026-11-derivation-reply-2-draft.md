<!-- Reply to ergoforum topic 5385, post 2 (2026-10-31). Draft v2, 2026-11-01, after seat round r1. Not posted.
     Needs skunks/pqwallet/XPUB-DEPTH-SURVEY.md and scripts/xpub_depth3_reach.py pushed first. -->

Prepared with Claude (Anthropic, Claude Opus 5.5), which read the wallet source below; reviewed by Grok, Gemini and Muse.

Short answer: a depth-3 export would reach neither rule, so it does not move the fork point. Rule A's branch, `m/8391'/…`, sits beside `m/44'` under the master, not under the account. With a discrete log, a depth-3 extended public key gives the account's private key and every key below it, and the climb stops at the hardened `account'` step; rule B's root is an HMAC that no BIP32 key reveals. A depth-3 export matters only for a post-quantum branch placed under the account, which neither rule does.

On whether any wallet hands one out, from reading the current source (default branches on 2026-11-01; read, not run; commits and line citations in `skunks/pqwallet/XPUB-DEPTH-SURVEY.md` in the same repository):

- The Ergo Ledger app exports an extended public key only for `m/44'/429'/account'` and paths below it with every level hardened. EIP-3's `.../0` is not hardened, so the device refuses it, and a host that computes Ledger addresses itself has to ask for depth 3. The device asks for confirmation unless the requesting app already holds an access token it knows.
- With a Ledger, Nautilus, Satergo and SAFEW request `m/44'/429'/account'` and derive `/0` on the host; Nautilus and Satergo keep the `/0` node, SAFEW keeps addresses.
- For mnemonic wallets, Nautilus (through fleet-sdk's default path), Satergo, Minotaur and the Ergo mobile wallet hold or export the `/0` node.

So none of these wallets offers the user a depth-3 key to export, and every Ledger-backed one receives it from the device. Nothing here asks a wallet to change. Not checked: other hardware, and whether a host logs or caches the device's response.

On the domain string, agreed. If it helps, the next step can be a short EIP draft that fixes `ergo-pq/v1` and carries the vectors.
