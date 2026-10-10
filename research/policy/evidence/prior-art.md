# Prior art: opt-in, owner-chosen spending policy on coins and accounts

Collected 2026-10-10. Facts only. Every claim has a link. [UNVERIFIED] means no primary source was found. Where only secondary press covers something, that is stated.

## 1. Bitcoin

**Taproot script trees (BIP-341/342).** A coin can carry several spend paths (leaves), with key-path spending as the default. This is the base that the vault and post-quantum proposals below build on. Final; activated Nov 2021. https://bips.dev/341/. Activation date is from memory: [UNVERIFIED here].

**BIP-345 OP_VAULT** (O'Beirne and Sanders, assigned 2023-02-03). It adds `OP_VAULT` and `OP_VAULT_RECOVER`. A trigger transaction starts a withdrawal that can finish only after a spend delay. Until then the coins can be swept to a recovery path set in advance. https://bips.dev/345/
- Limitations the BIP itself lists: recovery transactions must be replaceable to avoid pinning; anyone who knows the outpoints can replay an unauthorized recovery; an authorized-recovery key can be lost, or used to grief with low-fee recoveries; fees depend on v3 relay and ephemeral anchors; activation is undetermined.
- Status: **Closed**, with BIP-443 as the proposed replacement (same page). O'Beirne said in May 2025 that OP_VAULT "has been essentially replaced by" OP_CCV (quoted at https://gnusha.org/pi/bitcoindev/6f78b702-4bd0-4aa4-ac51-b881d8df9f01@mattcorallo.com/t). In June 2025 he co-signed a letter asking for CTV and CSFS activation (https://groups.google.com/g/bitcoindev/c/KJF6A55DPJ8).

**BIP-443 OP_CHECKCONTRACTVERIFY** (Ingala, assigned 2025-05-08, Draft). It lets a UTXO commit to data and require that outputs carry a given taptree and data. It has amount modes default, ignore and deduct. Fees must come from outside the checked amounts. The vault application section is still "TODO". https://bips.dev/443/

**BIP-119 OP_CTV** (Rubin, 2020-01-06, Draft). It commits to the spending transaction's outputs, sequences, locktime and input index. The BIP says this makes vaults "without half-spend vulnerabilities" possible. https://bips.dev/119/. The Optech vault topic lists CTV vault code (2022) and a CTV-only vault proof of concept (2026-06-05). It also says CTV alone is limited for vaults. https://bitcoinops.org/en/topics/vaults/

**BIP-347 OP_CAT** (Heilman and Sabouri). Status "Complete" as of 2026-03-01; activation was not established. The BIP says CAT is sufficient for vaults, and that CAT plus CSFS gives covenants without presigned transactions. https://bips.dev/347/. The Optech topic lists a CAT plus Schnorr vault prototype from 2024-02-28.

**Presigned-transaction vaults and Revault.** Vaults built without covenants have been discussed since 2019. Revault, a multiparty vault with presigned unvault, cancel and emergency transactions plus watchtowers, was implemented and presented in 2020. https://bitcoinops.org/en/topics/vaults/, spec at https://github.com/revault/practical-revault
- Current status is not stated anywhere: the repository is not archived, and Wizardsardine's public focus is now Liana. [UNVERIFIED that Revault was abandoned]

**Liana** (Wizardsardine; Optech notes a January 2023 release, https://bitcoinops.org/en/newsletters/2023/11/15/). A miniscript wallet. The primary key can spend at any time. Recovery or heir keys become valid after a relative timelock (`OP_CSV`, up to about 15 months).
- Because a relative timelock restarts when coins move, the owner must refresh coins periodically to keep the heir path closed. This is a dead-man design that requires upkeep.
- v10 made about one year the default recovery delay (https://www.nobsbitcoin.com/liana-wallet-v10-0/). Hardware-wallet support is documented at https://blog.bitbox.swiss/en/exploring-bitcoin-miniscript-with-liana-and-the-bitbox02/
- A paid "Safety Net" service holds a recovery key for customers.
- The refresh-to-reset-the-timelock behavior is inferred from how CSV works. [UNVERIFIED as Liana documentation text]

**BIP-360 P2MR** (formerly P2QRH, then P2TSH; Hunter Beast, Heilman, Foxen Duke; number assigned 2024-12-18, Draft). It is a SegWit v2 output that commits only to a script-tree Merkle root, with no key path. It explicitly does **not** add post-quantum signature opcodes. https://bips.dev/360/. Rename history: https://delvingbitcoin.org/t/changes-to-bip-360-pay-to-quantum-resistant-hash-p2qrh/1811, https://delvingbitcoin.org/t/major-bip-360-update/2170

**BIP-361 "Post Quantum Migration and Legacy Signature Sunset"** (Lopp and five co-authors, assigned 2026-02-11, Draft). https://bips.dev/361/
- Phase A, about 3 years after activation: no sends to quantum-vulnerable outputs.
- Phase B, about 2 years later: legacy ECDSA/Schnorr spends are disallowed except through a quantum-safe "rescue" check. The candidate is a proof of knowledge of a BIP-32 hardened parent, possibly via ZK-STARK.
- P2PK outputs are excluded. The authors defer them to "Hourglass".
- The BIP cites ">34% of all bitcoin" with an exposed public key (2026-03-01). It frames the issue as a "redistribution dilemma".
- Press describe it as controversial ("confiscation"): https://decrypt.co/364450/new-bitcoin-proposal-would-freeze-coins-to-counter-quantum-threat

**QRAMP (Quantum-Resistant Address Migration Protocol)** (Agustín Cruz, bitcoindev, February 2025). Not numbered. It proposes a hard deadline after which coins not yet migrated from ECDSA cannot be spent. https://groups.google.com/g/bitcoindev/c/8PM6iZCeDMc

**Hourglass** (P2PK rate limit). v1 allowed one P2PK input per block. v2 (2026-02-10) caps spends at 1 BTC per block and bans new P2PK outputs. https://delvingbitcoin.org/t/hourglass-v2-update/2246, https://groups.google.com/g/bitcoindev/c/zmg3U117aNc
- Criticism from the list: draining about 1.7M BTC at that rate takes about 32 years, and a rate limit "directly undermines the permissionless property". Both points were summarised from mailing-list excerpts. [secondary]
- Other dormant-coin drafts: QSAVE ("protective custody") and bips PR #2147, "Quantum-Resistant Transition for Dormant P2PKH". https://mirror.b10c.me/bitcoin-bips/2147/

**What the Bitcoin proposals have in common.** All of them are protocol-wide flag days or rate limits. None is a per-coin opt-in trigger. The opt-in tools Bitcoin does have (taproot leaves, CSV, presigned vaults) carry no external signal input.

## 2. Ethereum

**ERC-4337** (created 2021-09-29). Status shows **Final**, and it now lists EIP-7702 as a requirement. https://eips.ethereum.org/EIPS/eip-4337
- Mechanics: UserOperations go to an alternative mempool. Bundlers submit them to a singleton EntryPoint, which runs a validation phase and then an execution phase. Paymasters, which stake or deposit with EntryPoint, pay gas. Validation is restricted by opcode and storage rules and by a reputation system.
- The spec's stated motivations include different signature schemes, multisig and custom recovery.
- Mainnet since March 2023. Vendor and press adoption figures range from about 20M accounts in 2024 (Alchemy) to "40M+" (LCX). [secondary] https://www.alchemy.com/overviews/what-is-account-abstraction.md

**EIP-3074 AUTH/AUTHCALL** (2020-10-15). **Withdrawn**, "Superseded by EIP-7702". https://eips.ethereum.org/EIPS/eip-3074

**EIP-7702** (created 2024-05-07, Final). Live in Pectra on 2025-05-07 (https://blog.ethereum.org/2025/04/23/pectra-mainnet).
- An EOA signs an authorization that writes a persistent delegation designator (`0xef0100||address`) into its code. Delegating to the zero address revokes it. https://eips.ethereum.org/EIPS/eip-7702
- Criticisms in the EIP itself: the original ECDSA key still controls the account, so there is no key rotation. On wallet interfaces for signing authorizations it says "there is no safe way to provide this interface". A `chain_id` of 0 makes an authorization valid on every chain. Delegate code has "unrestricted access".

**Safe** (formerly Gnosis Safe). An m-of-n multisig contract extended by modules and guards. https://docs.safe.global/reference-smart-account/guards/setModuleGuard, https://safefoundation.org/blog/introducing-safe-v1-5-0-module-guards-enhanced-smart-account-features
- Modules can bypass the threshold. Examples given are allowance or spending-limit modules, recurring payments and social recovery.
- Guards are pre- and post-transaction hooks that can veto. A broken guard can cause denial of service.
- Before v1.5.0, modules bypassed guards. v1.5.0 added module guards.

**Argent** (legacy L1 contracts, https://github.com/argentlabs/argent-contracts, last commit 2024-03-27, checked via `gh api`). The README calls the wallet "guarded, recoverable, lockable, and upgradable".
- `SecurityManager.sol` has `recoveryPeriod`, `lockPeriod`, `securityPeriod` and `securityWindow`, with an enforced invariant `recoveryPeriod >= securityPeriod + securityWindow`.
- `TransactionManager.sol` has a whitelist with a `whitelistPeriod`, plus session keys with an expiry (`multiCallWithSession`).
- A 36-hour recovery delay is reported by press. [secondary, https://techcrunch.com/2020/05/18/buzzy-ethereum-wallet-app-argent-comes-out-of-stealth]
- An OpenZeppelin-reported "high severity" bug: https://www.theblock.co/post/68968/high-severity-vulnerability-in-argent-wallet-could-have-allowed-attackers-to-steal-user-funds

**Loopring smart wallet.** A majority of guardians can lock the wallet or restore the key. In June 2024, about $5M was stolen from users whose only guardian was Loopring's own 2FA "Official Guardian". Users with several guardians were not affected. https://www.theblock.co/post/299177/loopring-suffers-5-million-hack-after-guardian-two-factor-authentication-service-is-compromised, https://www.halborn.com/blog/post/explained-the-loopring-hack-june-2024

**Social recovery essay** (Buterin, 2021-01-11). Guardians can only rotate the signing key; they cannot spend. The essay also mentions vaults with delays. https://vitalik.eth.limo/general/2021/01/11/recovery.html (URL from memory) [UNVERIFIED]. Summary at https://ambcrypto.com/ethereums-vitalik-buterin-calls-for-adoption-of-social-recovery-wallets-to-fight-crypto-theft/

**Session keys and spending limits.**
- ERC-7715 (`wallet_grantPermissions`) issues scoped session keys with a spend cap, allowlist and expiry. It pairs with ERC-7710 on-chain delegation. Both are Draft per secondary sources. https://docs.metamask.io/smart-accounts-kit/concepts/advanced-permissions/
- ERC-7579 modular accounts are built from validators, executors and hooks. Spending limits are implemented as hooks or executors. https://eips.ethereum.org/EIPS/eip-7579, https://docs.nethereum.com/docs/account-abstraction/guide-modular-accounts

**Post-quantum emergency hard fork** (Buterin, ethresear.ch, 2024-03-09). https://ethresear.ch/t/how-to-hard-fork-to-save-most-users-funds-in-a-quantum-emergency/18901
- Steps: (1) revert to before large-scale theft; (2) disable EOA transactions; (3) add a smart-wallet transaction type (RIP-7560); (4) add a recovery transaction in which a STARK proves knowledge of a hash preimage (for example a BIP-32 seed) that derives the address, and switches the account to new validation code.
- The post treats account abstraction as preparation, so users can move to post-quantum schemes "on their own schedule".
- Gaps raised in the thread: keys not derived by hashing; locating the start of the attack; BLS and KZG.
- Commenters ShaiW (2024-03-10) and domothy (2024-03-11) propose a "quantum canary", a dormant mechanism that a kill switch activates. domothy's example trigger is someone claiming a large amount of ETH held in a contract secured only by a weaker discrete-log problem. This is the closest prior art found to an on-chain signal for "quantum day". It is a forum proposal, not a specification.

**State and history expiry (the storage-rent analogue).**
- EIP-4444: as of 2025-07-08, all execution clients support *partial* history expiry, dropping pre-Merge blocks and saving 300-500 GB. Rolling expiry is still in development. https://blog.ethereum.org/2025/07/08/partial-history-exp
- State expiry with resurrection by proof: research only. https://hackmd.io/@vbuterin/state_expiry_paths
- Ethereum has no deployed per-account rent.

## 3. Chia (coin set model, closest to Ergo)

**Model.** Chia uses a coin set (UTXO) model in which coins are locked by Chialisp puzzles.
- A singleton is a top layer (`singleton_top_layer_v1_1`) that wraps any inner puzzle, with uniqueness from a launcher coin. NFTs, DIDs and pooling use it. https://chialisp.com/singletons
- Inner puzzles return conditions that outer layers enforce: https://docs.chia.net/guides/crash-course/inner-puzzles

**Prefarm custody tool** (internal; blog 2022-10-29). The prefarm sits in a singleton with a Merkle tree of m-of-n key combinations (default 3-of-5). https://docs.chia.net/guides/custody-tool-description, https://pypi.org/project/chia-internal-custody/
- Withdrawal gate `wt` (30 days since the last action).
- Payment clawback `pc` (90 days), during which m signatures can cancel. After that, *anyone* can complete the payment to the preset address.
- Standard rekey after `rt` (15 days).
- "Slow rekey" with fewer than m keys adds 45 days plus `rt` per missing key; examples run up to 120 days with one key.
- Rekey clawback `rc` (30 days).
- A "lock level increase" raises m immediately and invalidates pending rekeys.

**CHIP-0043 MIPS, Meta Inner Puzzle Spec** (Hauff, created 2025-02-11, Final). A framework for the custody inner puzzles under a fixed outer puzzle.
- Member puzzles authorize by signature or by singleton announcement.
- M-of-N nodes take a Merkle root of N inner puzzles and nest arbitrarily.
- "Restrictions" are validators that cannot add conditions. Delegated-puzzle validators constrain what may be approved; condition validators constrain how.
- No mention of vaults or quantum. https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0043.md

**CHIP-0044 Clawback v2** (Haggstrom, created 2025-03-05, Final). Uses a `p2_1_of_n` Merkle tree with three paths: sender recovery before expiry (`ASSERT_BEFORE_SECONDS_ABSOLUTE`), receiver claim after expiry, and an anyone-can-push "push-through" to the receiver after expiry. The sender can also "Force" early delivery. https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0044.md
- Clawback v1 shipped in reference wallet 1.8.2 (2023), for XCH only. https://docs.chia.net/guides/clawback-primitive-guide, https://www.chia.net/2023/06/28/version-1-8-2-release/

**Chia Vaults / Cloud Wallet** (blog 2025-01-31, beta at the time). Vaults "separate custody from the coins". A spend key (passkey or the Chia Signer phone app) plus a BLS recovery key.
- Recovery is a *rekey*, and coins do not move.
- "Instant Recovery" uses the spend key. "Timelocked Recovery" uses the recovery key and waits out a recovery clawback the owner can cancel.
- Losing both keys means the vault cannot be recovered.
- Sources: https://www.chia.net/2025/01/31/chia-vaults-a-secure-and-flexible-way-to-manage-your-digital-assets/, https://docs.chia.net/cloud-wallet/recovery/, https://docs.chia.net/cloud-wallet/faq/
- That vaults are a singleton plus MIPS, and that the passkey is secp256r1: [UNVERIFIED]. Neither page states it.

**Gaps found.** No CHIP addresses quantum, storage rent or oracle-triggered policy (CHIP index: https://github.com/Chia-Network/chips). Chia has no storage rent.

## 4. Other chains

- **Cardano.** Native scripts (Allegra era) combine signatures, n-of-k and validity-interval bounds (`InvalidBefore`/`InvalidHereafter`). https://cardano-ledger.cardano.intersectmbo.org/cardano-ledger-allegra/Cardano-Ledger-Allegra-Scripts.html
  - Plutus/Aiken "vesting" is the canonical timelock pattern: owner any time, beneficiary after a lock time. https://aiken-lang.org/example--vesting
  - Security guidance says to use the validity-range lower bound for "not before" checks. https://developers.cardano.org/docs/build/smart-contracts/advanced/security/vulnerabilities/time-handling
  - No official vault standard was found.
- **Kaspa.** KIP-10 introspection opcodes ("basic covenants") shipped in the Crescendo hard fork (KIP-14), which activated on 2025-05-05 per developer and third-party pages. https://github.com/kaspanet/kips, https://medium.com/@coderofstuff/post-crescendo-mining-observations-50b99f36721a
  - KIP-17 (full covenants) and KIP-20 (covenant IDs) are listed "Active" in the repo index. They were reported for the "Toccata" fork (https://medium.com/@michaelsuttonil/kaspa-covenants-toccata-hard-fork-outlook-a4d81a40900c). Mainnet activation date: [UNVERIFIED].
  - KIP-9 "storage mass" prices UTXO-set growth at creation. It is not recurring rent.
- **Algorand.** Rekeying: a `rekey-to` transaction sets an account's `auth-addr` to a single key, a multisig or a LogicSig, so the address stays fixed while the key rotates. Closing the account clears it. https://dev.algorand.co/concepts/accounts/rekeying
  - State proofs (2022) are Falcon-signed every 256 rounds. https://dev.algorand.co/concepts/protocol/state-proofs
  - `falcon_verify` opcode since 2024. First mainnet Falcon-authorized LogicSig transaction in November 2025. https://algorand.co/blog/technical-brief-quantum-resistant-transactions-on-algorand-with-falcon-signatures
  - Native post-quantum accounts are targeted for Q3 2026 (shipped: [UNVERIFIED]). https://algorand.co/blog/algorand-targets-broad-quantum-resilience-by-2027
  - Rekey to a Falcon LogicSig is therefore an existing opt-in PQ migration path for a fixed address. This is inferred from the two documented features together.
- **Nervos CKB.** 1 CKByte = 1 byte of cell capacity. "State rent" is paid by dilution from constant secondary issuance. NervosDAO depositors are compensated; occupied capacity is not. Nothing is evicted. https://github.com/nervosnetwork/rfcs/blob/master/rfcs/0015-ckb-cryptoeconomics/0015-ckb-cryptoeconomics.md
- **Solana.** Accounts must be rent-exempt (a deposit). SIMD-0084 (created 2023-11-03, "Implemented") disables rent collection; existing rent-paying accounts must still become rent-exempt before withdrawing. https://github.com/solana-foundation/solana-improvement-documents/blob/main/proposals/0084-disable-rent-fees-collection.md
  - SIMD-0437 is cutting the per-byte rent rate in five steps. [secondary] https://solanacompass.com/news/simd-0437-step-1-goes-live-on-solana-mainnet-beginning-a-five-phase-rent-reduction
- **QRL.** XMSS addresses are stateful: reusing an OTS index is rejected, and a fully exhausted tree locks the funds. https://docs.theqrl.org/developers/ots/
  - Zond replaces XMSS with SPHINCS+ (stateless). https://theqrl.org/blog/embracing-sphincs-a-strategic-shift-for-qrl-project-zond/
  - The enQlave design lets the *last* OTS replace the XMSS key. https://www.theqrl.org/blog/the-qrl-enqlave-project-bringing-post-quantum-security-to-ethereum-and-other-blockchain-platforms/
- **Mina.** Per-account permissions over 13 fields. `setVerificationKey` can be none, impossible, proof, signature or proofOrSignature. After a hard fork that bumps the transaction version, proof-based and impossible settings fall back to signature. https://docs.minaprotocol.com/zkapps/o1js/permissions
- **NEAR.** Multiple keys per account. FullAccess keys can add or remove keys, which gives native key rotation. FunctionCall keys are limited to one receiver and optional methods, with a gas *allowance*, and cannot attach tokens. https://docs.near.org/protocol/access-keys
- **Zcash.** A draft "Quantum resilience" ZIP (Hopwood, Grigg; 2025-03-31) would change Orchard note construction so funds can be recovered after discrete-log breaks; Sapling users are advised to move to Orchard. https://hackmd.io/fF6D7THmRDamvyAAsJN5yw
  - Zcash has no account key rotation (shielded notes). Ironwood (July 2026) made Orchard withdraw-only after a bug. [single secondary source] https://theblock.co/post/409934/zcash-ironwood-upgrade-launching-new-shielded-pool-after-orchard-vulnerability
- **Cosmos SDK.**
  - `x/authz`: a granter delegates Msg types to a grantee. `SendAuthorization` has a decrementing `spend_limit` and an `allow_list`. Grants carry an optional expiration, are pruned when expired, and can be revoked. https://github.com/cosmos/cosmos-sdk/blob/main/x/authz/README.md
  - `x/feegrant`: `BasicAllowance` (spend limit plus expiry) and `PeriodicAllowance`; the granter pays the grantee's fees. https://docs.cosmos.network/sdk/next/modules/feegrant

## 5. Ergo

- **Storage rent.** After 1,051,200 blocks (about 4 years) a box can be charged about 0.14 ERG (minimum box) and recreated. A box that cannot pay may be fully consumed, tokens included. https://ergoplatform.org/en/blog/2022-02-18-ergo-explainer-storage-rent
  - Practice described on community calls: anyone can take underfunded boxes; miners recreate funded ones. The Sigmanauts pool was the first to run collection (AMA 2024-09-12, https://youtube.com/watch?v=ZH_wSPDn7DA).
  - The sigmaspace.io dashboard tracks boxes about to come due (https://youtube.com/watch?v=E4xj8Ad7y2k).
- **EIP-39** (merged 2022-10-05): a monotonic creation-height rule, motivated by contracts anyone can spend being able to emit outputs with old heights that become rent-eligible early.
- **Rent EIPs**, all open PRs at https://github.com/ergoplatform/eips/pulls, listed with `gh pr list`:
  - EIP-33, token burning during rent collection (#68, 2022).
  - EIP-45, redistribution of rent fees (#93, 2023).
  - **EIP-48**, Storage-Rent Repairs (#105, 2026-07-18, arkadianet). Fixes Int overflow in the fee, which leaves boxes of about 1,718 bytes or more rent-immune, and fixes EIP-27 re-emission boxes being permanently exempt.
  - **EIP-49**, prepaid rent with archival and revival (#107, 2026-09-23). Replaces confiscation. Its motivation cites bots claiming eligible boxes "within minutes".
  - **EIP-51**, rent-paying refresh in the grace period (#108, 2026-09-26). A refresher pays one rent into a time-locked output. P2PK boxes pay in tokens, with a share starting at 2^-32 and doubling every 315 blocks up to half.
  - **EIP-52**, miner-attested rent claims (#109). A 30-day measurement found 6,610 claims totalling about 5,150 ERG, of which at most 13% was provably collected by miners.
  - **EIP-53**, storage rent grace period (#110, kushti, 2026-09-26). Boxes with tokens or registers can be charged only down to the minimum value and fully consumed only after 10,080 blocks; reference implementation ergo#2586.
  - **None of these is an opt-in per-box policy.** All are consensus or node-policy changes.
- **Sponsor and fee primitives.** EIP-31, Babel Fees (merged): token-paid fees through boxes that swap ERG for tokens. https://github.com/ergoplatform/eips
- **Multisig and custody.**
  - EIP-11, Distributed Signatures (open, #8, 2020).
  - EIP-19, Cold Wallet (merged 2021).
  - EIP-42, Multi-Signature Wallet (open, #88, 2023, vorujack). Minotaur, a multisig wallet presented at ErgoHack 9 (https://youtube.com/watch?v=Mxdxjq9LT2w).
  - Sigma protocols give native threshold and ring signatures.
- **Timelocks and inheritance.**
  - Cookbook time-locked box with refund (Ergo docs MCP, `content/cookbook/contracts/timelock.md`). ergoscript-by-example "Timed Fund".
  - MewLock: lock until a height, with a single-box spend rule.
  - SigmaLock by Four Eyes (AMA 2024-07-25 and 2025-07-24/08-07: https://youtube.com/watch?v=b0GX_U3uUYw, https://youtube.com/watch?v=dv4Z2ztRFaQ, https://youtube.com/watch?v=x-gTulAcJOE). Unlocks on time or price strike, issues unlock NFTs to beneficiaries, and the creator can keep modify rights. Described as "life insurance / inheritance".
  - Oracle-pool v2 oracle boxes hold `minStorageRent` and let the owner rotate the R4 public key while the script stays fixed (Ergo docs MCP, oracle-contract security notes). This is an in-protocol example of key rotation inside one box.
- **Post-quantum.**
  - Forum 2020-06-23 (https://ergoforum.org/t/ergo-and-post-quantum-crypto/257). scalahub proposed a PQ sigma protocol to replace `proveDlog` "and a mechanism to switch to it when the need arises". kushti noted problems with lattice schemes and called Picnic a possible "good candidate".
  - AMA 2024-12-19: kushti said PoW is hash-based and so not exposed, the risk is in signatures and sigma protocols, and PQ would cut TPS by 10-100x (https://youtube.com/watch?v=z0vlCVoNFAw).
  - AMA 2025-07-31: "fork to quantum-proof protocols once they're mature" (https://youtube.com/watch?v=rICaZBdO6q4).
  - EIP-45, Native STARK Proof Verification Opcode (#103, 2026-04-29, open; activation not proposed).
- **"Account abstraction" on Ergo.** A semantic search of the Ergo Discussion index (to 2026-02-24) for "account abstraction on Ergo" returned only general 2019-2020 posts (FlowCards, crowdfunding), with no on-topic thread. This means none was found, not that none exists.

## 6. Primitive matrix

Y = native or standard feature; P = partial, possible by construction, or proposed only; N = not offered. "Signal trigger" means spend rules change on an external on-chain fact (oracle, canary, flag box), as opposed to height or time.

| Item | Key rotation | Timelock | Clawback/cancel | Spend limit | Recovery/guardian | Inheritance/dead-man | Rent/upkeep | PQ migration | Signal trigger | Sponsor/paymaster | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Taproot trees | N | Y | N | N | P | P | N | N | N | N | Deployed 2021 |
| BIP-345 OP_VAULT | N | Y | Y | N | Y | N | N | N | N | N | Closed 2025 |
| BIP-443 CCV | N | P | P | P | P | P | N | N | N | N | Draft |
| BIP-119 CTV / BIP-347 CAT | N | P | P | N | P | N | N | N | N | N | Draft / not activated |
| Revault | N | Y | Y | P | Y | N | N | N | N | N | Built 2020; status unclear |
| Liana | N | Y | N | N | Y | Y | P (refresh) | N | N | N | Deployed 2023 |
| BIP-360 P2MR | N | N | N | N | N | N | N | P (prep) | N | N | Draft |
| BIP-361 / QRAMP / Hourglass | N | N | N | P (Hourglass rate) | N | N | N | Y (forced) | N (flag day) | N | Draft / proposal |
| ERC-4337 | Y | P | P | P | Y | P | N | P | N | Y | Deployed 2023 |
| EIP-7702 | N | P | P | P | P | P | N | N | N | Y | Deployed 2025-05 |
| EIP-3074 | N | N | N | N | N | N | N | N | N | Y | Withdrawn |
| Safe modules/guards | Y | P | P | Y | Y | P | N | N | N | P | Deployed |
| Argent / Loopring | Y | Y | Y | P | Y | N | N | N | N | Y (relayer) | Deployed; Loopring exploit 2024 |
| ERC-7715/7579 sessions | P | Y (expiry) | N | Y | N | N | N | N | N | P | Draft / implemented |
| Buterin PQ fork | Y (forced) | N | N | N | N | N | N | Y | P (canary in comments) | N | Research 2024 |
| ETH state/history expiry | N | N | N | N | N | N | P | N | N | N | Partial history 2025; state research |
| Chia custody (prefarm) | Y | Y | Y | N | Y | N | N | N | N | N | Deployed 2022 |
| Chia MIPS | Y | P | P | P | Y | P | N | N | P (singleton announcement member) | N | Final 2025 |
| Chia clawback v2 | N | Y | Y | N | N | N | N | N | N | P (push-through) | Final 2025 |
| Chia Vault | Y | Y | Y | N | Y | N | N | N | N | N | Beta 2025 |
| Cardano native/Plutus | N | Y | P | P | P | P | N | N | P (Plutus oracle) | N | Deployed |
| Kaspa KIP-10/17 | N | Y | P | P | P | P | P (storage mass) | N | P | N | Deployed 2025 / later |
| Algorand rekey + Falcon | Y | P (LogicSig) | N | P | N | N | N | P (opt-in LogicSig) | N | P | Deployed |
| Nervos CKB | N | Y (since) | N | N | N | N | Y (dilution) | N | N | N | Deployed |
| Solana rent | N | N | N | N | N | N | Y (deposit) | N | N | N | Deployed; collection off |
| QRL XMSS/Zond | P (last OTS) | N | N | N | N | N | N | Y (native PQ) | N | N | Deployed / Zond pending |
| Mina permissions | Y | P | N | N | N | N | N | N | N | Y (fee payer) | Deployed |
| NEAR access keys | Y | N | N | P (gas allowance) | N | N | P (storage staking) | N | N | N | Deployed |
| Zcash quantum ZIP | N | N | N | N | N | N | N | P | N | N | Draft 2025 |
| Cosmos authz/feegrant | N | Y (expiry) | N | Y | N | N | N | N | N | Y | Deployed |
| Ergo storage rent + EIP-48..53 | N | N | N | N | N | N | Y (protocol) | N | N | N | Deployed / open |
| Ergo timelocks, SigmaLock, multisig | P | Y | P | P | P | Y | N | N | P (SigmaLock price) | P (Babel fees) | Deployed |

Notes on cells:
- P for Cardano and Kaspa "signal" means a script could read an oracle or data input. No standard vault does so.
- NEAR storage staking, the CKB "since" timelock and Mina's fee payer are from general knowledge. [UNVERIFIED in this pass]
- Algorand "opt-in LogicSig" combines rekeying with the `falcon_verify` opcode.

Most matrix cells for well-known features (for example ERC-4337 key rotation) come from the item sections above; cells marked P are judgement calls about what a design allows, not documented features.
