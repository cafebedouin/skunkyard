# Foreseeable problems for coin holders, 5-30 years: evidence collection

Compiled 2026-10-10. Evidence only, no designs. "Policy-addressable" means an opt-in guard script on a box can act on
it without a protocol change. Web figures come from search-result summaries and secondary press unless a primary URL
is given. Figures with no source are marked [UNVERIFIED]. Repo figures are from this repo's own chain scans.

## 1. Quantum: Shor against secp256k1 (Schnorr/ECDSA)

- **What.** A cryptographically relevant quantum computer (CRQC) running Shor's algorithm can recover a private key from
  a public key. Ergo's `proveDlog` is a Schnorr signature on secp256k1.
- **Evidence.**
  - Google Quantum AI and others, arXiv 2603.28846 (2026): ECDLP-256 needs at most 1,200 logical qubits and 90M
    Toffoli gates, or 1,450 logical qubits and 70M Toffoli gates. That is under 500,000 physical qubits with a runtime
    of minutes. https://arxiv.org/html/2603.28846v2
  - Gidney (May 2025): RSA-2048 in under a week with fewer than 1M noisy qubits, down from 20M in 2019.
    https://arxiv.org/abs/2505.15917
  - Post-Quantum.com reports 2026 preprints claiming RSA-2048 with under 100k physical qubits. [UNVERIFIED]
  - Global Risk Institute expert survey, 2024 edition: CRQC within 10 years about 34% on the optimistic reading, about
    19% on the pessimistic one; within 5 years about 14%.
    https://globalriskinstitute.org/publication/2024-quantum-threat-timeline-report/
  - GRI 2025 edition: 28-49% within 10 years, 51-70% within 15.
    https://globalriskinstitute.org/publication/quantum-threat-timeline-report-2025b/
  - NIST published FIPS 203 (ML-KEM), FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) on 2024-08-13. HQC was selected in
    March 2025.
  - NIST IR 8547, still a draft (2024-11-12), proposes deprecating 112-bit RSA/ECC after 2030 and disallowing it after
    2035.
- **Exposure.**
  - On Ergo, a P2PK address is the public key, so every P2PK box is exposed from the moment it is created. At height
    753,934, 96.5% of non-protocol ERG sat under a script containing a key (repo `research/pq/README.md`, Q1, a dry
    run; the final run waits on node sync).
  - Bitcoin 2026 scans:
    - ChainQuery, block 968,788: 7.14M BTC exposed (35.5%), 1.72M of it in P2PK.
      https://chainquery.com/reports/quantum-exposure
    - Project Eleven: 8.0-8.2M; the gap to ChainQuery is unresolved (repo `LITERATURE.md`).
  - Signatures and keys face different harvest risks:
    - Signatures need no "decrypt later". The harvestable item is the public key already on chain. Every exposed key
      can be broken whenever a CRQC exists ("long-range" in Chaincode's terms).
    - Hash-hidden keys are exposed only during the mempool window of the spend that reveals them ("short-range").
      https://chaincode.com/bitcoin-post-quantum.pdf
    - HNDL in the encryption sense applies to off-chain data (wallet backups, encrypted seeds, TLS traffic to
      custodians) [UNVERIFIED for any crypto-specific incident].
- **Who is exposed.** Mostly dormant holders and heirs, because they cannot migrate. Active users can move to
  hash-locked or post-quantum scripts. Protocol boxes guarded by keys (multisig treasuries, oracle operator keys) are
  also exposed.
- **Policy-addressable: partly.**
  - A box can commit to a hash-based fallback key now (repo Q2: WOTS verified in ErgoTree on 6.0.6, 4,488 bytes).
  - A box whose only spending path is `proveDlog` cannot be rescued by its own script after a CRQC exists.
  - The short-range (mempool) attack is not policy-addressable unless the spend uses a commit-reveal.
  - The protocol-level answers are a soft-fork verifier opcode or a sunset of ECDSA/Schnorr spends (BIP-360/361,
    QRAMP).
- **Trigger signals.**
  - None on chain today.
  - Candidates: an oracle or flag box (the repo's `qvault` uses a monotone oracle flag); a miner-vote soft-fork bit; an
    on-chain proof of quantum capability. A puzzle box whose key is a nothing-up-my-sleeve point would serve as a
    canary [UNVERIFIED as a deployed practice on any chain].
  - A fixed height derived from NIST's 2035 date.

## 2. Grover against hashes, and hash or crypto weakening generally

- **What.**
  - Grover gives a square-root speedup on preimage search, so 256-bit hashes keep about 128-bit preimage security.
  - Classical cryptanalysis can break a primitive outright.
- **Evidence (SHA-1).**
  - NIST deprecated SHA-1 in 2011 and barred it for signatures after 2013.
  - SHAttered, the first collision (Google/CWI, 2017-02-23), took 6,500 CPU-years plus 110 GPU-years.
    https://csrc.nist.gov/news/2017/research-results-on-sha-1-collisions
  - "SHA-1 is a Shambles" (Leurent and Peyrin, January 2020): a chosen-prefix collision for about US$45k.
    https://www.usenix.org/conference/usenixsecurity20/presentation/leurent
  - Git chose SHA-256 in 2018. Git 2.51 (August 2025) still defaults to SHA-1.
    https://www.helpnetsecurity.com/2025/08/19/git-2-51-sha-256/
  - Taken together: about 9 years from deprecation to the first collision, and at least 7 years of migration still
    not finished.
- **Who is exposed.** Everyone. Ergo's PoW (Autolykos), box ids, Merkle roots and P2SH all use Blake2b256 [Autolykos
  and P2SH hash choice UNVERIFIED here].
- **Policy-addressable: partly.**
  - A script can choose which hash commits to its fallback key, for example `sha256` or `blake2b256`.
  - Consensus hashes (box ids, state root, PoW) are protocol-level only.
- **Trigger signals.** A published collision is a public event with no on-chain form. An oracle or vote would have to
  carry it. A contract can check a submitted collision pair (two different preimages with the same digest) itself.
  That is the only fully on-chain trigger for this problem.

## 3. Key loss and inheritance

- **Evidence.**
  - Chainalysis (2017) estimated 2.78-3.79M BTC lost, assuming early-mined coins are gone.
    https://fortune.com/2017/11/25/lost-bitcoins
  - The "2.3-3.7M" figure is widely attributed to Chainalysis and appears only in secondary sources [UNVERIFIED
    primary].
- **Ergo.** Storage rent ends dormancy. In a 21,600-block window (heights 1,869,418-1,891,017), miners claimed 76,926
  P2PK boxes worth 357,658 ERG and took 6,282 ERG. 17,032 boxes were consumed whole (repo
  `research/agents/CENSUS-U1B.md`).
- **Who is exposed.** Dormant holders, heirs, people who die without a plan.
- **Policy-addressable: yes.** Dead-man switches, timelocked heir keys and social recovery are all expressible in
  ErgoScript today.
- **Trigger signal.** `HEIGHT` minus the last activity, kept in a register and refreshed by the owner, or the box's
  own creation height.

## 4. Storage rent and state bloat

- **Ergo mechanism.**
  - From block 1,051,200 (2023-07-20), a box untouched for 1,051,200 blocks (about 4 years) can be charged
    `storageFeeFactor` × its size. The default is 1,250,000 nanoERG per byte, adjustable by vote in [0, 2,500,000].
  - A box whose value does not cover the fee can be taken whole. The guard script is not evaluated.
    https://docs.ergoplatform.com/dev/protocol/storage-rent/
  - Draft EIP-0048 (64-bit fee arithmetic) is not active.
- **Evidence it bites.** See the census above.
  - 113 contract templates were spent only as rent: 2,450 boxes, with 11,719 more still unspent.
  - Since node 6.0.7 the large pools stopped including rent claims, at about height 1,883,800 (operator report in the
    census).
- **Who is exposed.** Dormant holders and abandoned protocol boxes. Token-only boxes with little ERG are consumed
  whole first.
- **Policy-addressable: partly.**
  - A box cannot block rent: the guard is bypassed.
  - A policy can make a keyless refresh path (KeepAlive) that recreates the box before it reaches 4 years old. That
    path needs someone to submit the transaction.
- **Trigger.** Height: creation height + 1,051,200.

## 5. Theft by key compromise, phishing, approval drainers, address poisoning

- **Chainalysis 2025 totals.**
  - Over $3.4B stolen in 2025. Bybit alone (2025-02-21, DPRK-attributed) was about $1.5B, 44% of the total.
  - DPRK-attributed: $2.02B.
  - Personal-wallet compromises: 158,000 incidents, $713M.
  - https://www.theblock.co/post/382477/crypto-hack-2025-chainalysis
- **Scam Sniffer, EVM drainers.**
  - $83.85M in 2025 from 106,106 victims, against about $494M in 2024. Permit signatures were the main vector.
  - EIP-7702 malicious delegations first appeared in August 2025.
  - https://drops.scamsniffer.io/scam-sniffer-2025-crypto-phishing-losses-fall-83-to-84-million/
- **Address poisoning.** Single losses of $50M (December 2025) and $12.25M (January 2026), reported by Decrypt.
- **Ergo relevance.** The eUTXO model has no standing token approvals like ERC-20 `approve`. A user signs whole
  transactions, so a malicious dApp transaction is still possible [mechanism; no Ergo incident count found].
- **Policy-addressable: yes for most.**
  - Vault or covenant scripts can add a withdrawal delay with a cancel key, spending limits per period, or allow-listed
    destinations.
  - These limit a stolen key. They do not stop a user who knowingly signs the delayed transaction and lets it complete.
- **Trigger.** In-script: an amount over a limit within a window of `HEIGHT`s, or a destination not in the allow-list.

## 6. Wrench and coercion attacks

- **Evidence.**
  - Lopp's GitHub list counts 41 physical attacks in 2024 and more than 70 in 2025. 2021 had been the record year, with
    36.
  - Chainalysis said 2025 was on track for about twice the record year, and that attacks correlate with the BTC price.
  - https://github.com/jlopp/physical-bitcoin-attacks; https://cointelegraph.com/news/bitcoin-wrench-attacks-to-double-2021-peak
  - The January 2025 Ledger co-founder kidnapping (finger severed) is cited in coverage.
- **Who is exposed.** Known holders, executives, publicly doxxed users.
- **Policy-addressable: partly.**
  - Timelocked vaults with a delay, and multisig spread across places or people, make an immediate transfer impossible.
  - They do not prevent violence. Reducing the payout is the intended deterrent [UNVERIFIED that deterrence works].
- **Trigger.** None external. The box enforces its delay unconditionally.

## 7. Custody and exchange failure

- **Evidence.**
  - Mt. Gox lost about 850,000 BTC (disclosed in 2014). About 20% was recovered, and repayments began in July 2024.
  - FTX collapsed in November 2022 with a customer shortfall of about $8B. The estate reports repaying more than 100%
    of claims in November-2022 dollars.
  - Bybit was a hot/cold wallet signing compromise (§5).
- **Who is exposed.** Exchange customers. Protocols that keep reserves on exchanges.
- **Policy-addressable: no for funds held at a custodian** (no box of the user's). Partly for self-custody alternatives
  such as multisig-with-provider.
- **Trigger.** Off-chain (a withdrawal halt). A proof-of-reserves oracle [UNVERIFIED that any exists on Ergo].

## 8. Long-run security budget when emission ends

- **Ergo.**
  - EIP-27 activated at block 777,217 (June 2022).
  - 12 ERG per block goes to re-emission while the reward is at least 15 ERG; below that, reward − 3. The re-emission
    contract pays 3 ERG per block until about 2045.
  - Total supply is 97,739,925 ERG.
  - Sources: https://docs.ergoplatform.com/mining/standards/eip27/ and
    https://ergoplatform.org/en/blog/Ergos-Reemission-Vote-EIP27-A-Path-to-Sustained-Growth/
  - Exact end height not found [UNVERIFIED].
  - Storage rent was designed as a post-emission miner income ("Storage Rent and the Future of Mining", 2022). The
    census measured 0.29 ERG per block from rent in late 2026.
- **Theory.**
  - Carlsten et al. (CCS 2016): with fees only, reward variance makes forking and undercutting profitable, and selfish
    mining becomes profitable at any hashrate share.
    https://www.cs.princeton.edu/~arvindn/publications/mining_CCS.pdf
  - Budish (NBER w24717, 2018): miners' recurring payments must be large relative to the one-off gains from an attack.
- **Who is exposed.** Every holder, through reorg and double-spend risk. Exchanges and bridges that accept deposits
  after few confirmations are exposed most.
- **Policy-addressable: no** at the consensus level. Partly, a contract can require more confirmations or a
  `HEIGHT` delay before value moves.
- **Trigger.** Height (the end of emission). Observable hashrate or difficulty through `CONTEXT.headers` (`nBits`).
  Deep reorgs are not visible to a script.

## 9. Miner extraction (MEV) and censorship

- **Evidence.**
  - Flashbots measured at least $314M of extracted MEV on Ethereum from January 2020 (early lower bound). Paradigm: the
    total "is impossible to say".
  - OFAC-compliant Ethereum blocks peaked at 79% (2022-11-21/22) and were 27% by May 2023.
    https://www.theblock.co/post/230179
  - Ergo: the repo census lists keyless takes a block builder can make, with rent the only large one (CENSUS-U1B).
- **Who is exposed.** Active DeFi users, liquidators, and anyone whose spend must land before a deadline.
- **Policy-addressable: partly.**
  - Slippage bounds and commit-reveal are possible in-script.
  - Censorship is not addressable by a script. Long timeouts reduce its harm.
- **Trigger.** None reliable on chain. Censorship appears as the absence of inclusion.

## 10. Oracle failure or capture

- **Evidence.**
  - Mango Markets (October 2022): about $110M taken by pushing the MNGO price up more than 1,000% in 20 minutes and
    borrowing against it. Eisenberg's convictions were vacated on 2025-05-23. https://www.theblock.co/post/355666
  - MakerDAO Black Thursday (2020-03-12): oracles lagged and keepers were priced out. 1,462 of 3,994 auctions were won
    with zero bids, losing $8.32M; the protocol was $4M short.
- **Who is exposed.** Protocols, and their borrowers and stablecoin holders.
- **Policy-addressable: partly.** A box can require several oracles, freshness (`HEIGHT` minus the oracle epoch), and
  deviation limits. Capture of the oracle set itself is not addressable.
- **Trigger.** A stale epoch in the oracle box register, or a deviation beyond a bound against a second source.

## 11. Bridge failures

- **Evidence.**
  - Ronin (March 2022): $625M.
  - Wormhole (February 2022): $326M [UNVERIFIED in this pass; the search did not confirm the amount].
  - Nomad (August 2022): $190M.
  - Harmony Horizon (June 2022): $100M.
  - Chainalysis: bridges took 69% of 2022 theft up to August.
    https://forklog.com/en/news/chainalysis-estimates-2bn-in-losses-from-cross-chain-protocol-hacks-so-far-this-year
- **Who is exposed.** Holders of wrapped assets; the bridge's reserve.
- **Policy-addressable: no for the holder's wrapped token**, whose value depends on the other chain. Partly for the
  reserve: rate limits and delays.
- **Trigger.** A drop in reserve or supply parity, readable by a script only if the bridge publishes it on chain.

## 12. Smart-contract bugs (Ergo case)

- **Evidence.** USE/DexyGold LP drain:
  - 2026-09-08, height 1,868,204: 284,695.59 ERG taken from the LP.
  - The replay corpus has the deployed swap tree passing the exploit and the fixed tree rejecting it.
  - The USE bank vault, with 292,615 ERG, was untouched since 1,867,725 when decoded.
  - https://github.com/arkadianet/ergo-forge/tree/main/examples/incidents
- **Who is exposed.** LPs and the protocol's token holders.
- **Policy-addressable: no for the buggy contract itself**, which is immutable. Partly through circuit-breakers
  designed in from the start: a per-block outflow cap, or a pause after a reserve drop.
- **Trigger.** A reserve change beyond a bound within N blocks, readable in-script from the pool box.

## 13. Governance capture

- **Evidence.** Beanstalk (2022-04-17): about $1B in flash loans won a 67% vote and executed immediately, with no
  delay. $182M was drained and the net theft was about $76-80M. https://rekt.news/beanstalk-rekt
- **Ergo.**
  - Parameters, including `storageFeeFactor`, change by miner vote.
  - Soft forks need 90% of blocks in a voting epoch [90% per EIP-27 coverage; general rule UNVERIFIED here].
- **Policy-addressable: partly.** A box can refuse to follow parameter changes it did not opt into (hard-coded
  constants), and add time delays and opt-out windows. It cannot resist a hard fork.
- **Trigger.** A parameter value read through `CONTEXT` [a script reading `storageFeeFactor` is UNVERIFIED], or a
  vote outcome box.

## 14. Regulatory freezes and blacklists

- **Evidence.**
  - Tether blacklisted 4,163 addresses in 2025, freezing $1.26B; about $698M of that was later destroyed. The
    cumulative figure by July 2026 is about 9,597 addresses and $5.69B (BlockSec, vendor data).
    https://blocksec.com/blog/1-26-billion-frozen-usdt-blacklisting-on-ethereum-and-tron-in-2025
  - Tornado Cash: sanctioned by OFAC 2022-08-08. The Fifth Circuit (Van Loon, 2024-11-26) held that immutable
    contracts are not property under IEEPA. Delisted 2025-03-21.
- **Who is exposed.** Holders of issuer-controlled tokens. Users of front-ends, exchanges and validators that comply.
- **Policy-addressable: no** for the issuer's freeze. Native ERG has no freeze function.
- **Trigger.** The issuer's on-chain blacklist event (EVM); none for ERG.

## 15. Privacy erosion

- **Evidence.**
  - Meiklejohn et al. (IMC 2013) used multi-input and change heuristics to collapse more than 12M addresses to about
    4M. https://smeiklej.com/files/imc13.pdf
  - The IRS used Chainalysis Reactor to trace 69,370 BTC in November 2020.
  - No Ergo-specific clustering study was found.
- **Who is exposed.** Everyone. Doxxed holders face higher wrench risk (§6).
- **Policy-addressable: partly.** Ergo has ring/threshold sigma protocols and mixers (ErgoMixer) [deployment status
  UNVERIFIED]. Leaks at the network layer are not addressable.
- **Trigger.** None.

## 16. Time and clock manipulation

- **Evidence.**
  - Bitcoin's timewarp bug lets a majority miner drive difficulty to its minimum in about 38 days. The fix is in
    BIP-54 (Draft/proposed). https://bips.dev/54
  - Ergo rule 205: the header timestamp must exceed the parent's.
    https://docs.ergoplatform.com/node/modifiers-validation/
  - Ergo's future-drift limit was not checked [UNVERIFIED].
- **Who is exposed.** Contracts that use `preHeader.timestamp` for deadlines.
- **Policy-addressable: yes.** Using `HEIGHT` rather than timestamps avoids it. Height can still drift against wall
  time if hashrate changes.
- **Trigger.** Not needed. It is a design rule.

## 17. Protocol ossification

- **Evidence.**
  - Git's SHA-256 migration is unfinished after 7 years (§2). BIP-54 fixes a 2009 bug and was still not activated in
    2026.
  - The Bitcoin post-quantum proposals (BIP-360, 2024-12-18) are unactivated (repo `LITERATURE.md`).
- **Who is exposed.** Holders who need a new primitive, such as a post-quantum verifier opcode, before it ships.
- **Policy-addressable: partly.** This is the case for opt-in script policy: it works within today's opcodes (WOTS in
  ErgoTree, repo Q2). It is limited by cost: a WOTS spend is about 3.9× a P2PK spend in per-block capacity.
- **Trigger.** Not applicable.

## 18. Dependence on off-chain bots and keepers

- **Evidence (Ergo, repo `research/agents/UPKEEP.md`).**
  - Duckpools' main liquidator last transacted at 1,810,795. The interest box last moved at 1,840,030.
  - 19 live loans hold 31,551 ERG. The first expiries are at 1,920,164.
  - The Dexy volunteer bot froze for 51-81 hours.
- **Evidence (Ethereum).** Black Thursday (§10).
- **Who is exposed.** Borrowers, whose repay requests go unprocessed. Lenders, who hold bad debt. Holders of KeepAlive
  or rent-refresh boxes that rely on a third party.
- **Policy-addressable: yes, if the path is keyless.** A contract with keyless liquidate or refresh paths lets any
  block builder act. The repo's Lithos upkeep jobs are this.
- **Trigger.** Height past an expiry, or a health ratio, read from boxes.

## 19. Long-term data availability and archival

- **Evidence.**
  - Ethereum partial history expiry (EIP-4444) went live in all execution clients on 2025-07-08, saving 300-500 GB.
    Rolling expiry is still open. https://blog.ethereum.org/2025/07/08/partial-history-exp
  - Ergo nodes can prune blocks (`blocksToKeep`) [UNVERIFIED default].
  - The repo's explorer mirror (Cornell) is a single third-party dependency.
- **Who is exposed.**
  - Heirs and dormant holders who need old transaction data or off-chain secrets: script source, WOTS state, P2SH
    preimages.
  - The repo shows sigma-rust P2SH boxes cannot be spent by any prover (finding 5).
- **Policy-addressable: partly.** Keep everything needed to spend in registers on chain. Off-chain one-time-key
  state is a liability.
- **Trigger.** None.

## Summary table

| Problem | Exposed party | Policy-addressable? | Trigger signal | Severity / horizon (as sourced) |
|---|---|---|---|---|
| Shor vs secp256k1 | dormant holders, heirs; key-guarded protocol boxes | partly (pre-committed hash fallback; not for proveDlog-only boxes) | oracle flag, miner vote, canary-key spend [UNVERIFIED practice], NIST-derived height | GRI 2025: 28-49% in 10 y, 51-70% in 15 y; NIST IR 8547 draft disallows 2035; ~35% of BTC exposed |
| Hash weakening / Grover | all | partly (choice of hash in script) | on-chain collision pair; oracle | SHA-1: 9 y deprecation to first collision; Grover halves bits |
| Key loss / inheritance | heirs, dormant | yes | HEIGHT since last activity | 2.8-3.8M BTC lost (Chainalysis 2017) |
| Storage rent | dormant, abandoned protocol boxes | partly (keyless refresh, not bypass) | creation height + 1,051,200 | 6,282 ERG taken from 76,926 boxes in 21,600 blocks (repo) |
| Theft / phishing / drainers | active users, exchanges | yes (delay, limits, allow-list) | in-script amount/destination | $3.4B in 2025 (Chainalysis); $84M drainers |
| Wrench attacks | known holders | partly (delays, distributed multisig) | none external | >70 in 2025, about 2× record (Lopp) |
| Custody / exchange failure | custodial users | no | off-chain | Mt Gox 850k BTC; FTX ~$8B |
| Fee-only security | all, exchanges, bridges | no (consensus); partly (confirm delays) | height (~2045 Ergo); nBits | theoretical instability (Carlsten 2016, Budish 2018) |
| MEV / censorship | DeFi users, deadline spends | partly | none reliable | ≥$314M early MEV floor; 79% OFAC blocks peak |
| Oracle failure / capture | protocols, borrowers | partly | stale epoch, deviation | Mango ~$110M; Black Thursday $8.32M |
| Bridge failure | wrapped-asset holders | no (holder); partly (reserve) | reserve parity if on chain | Ronin $625M; 69% of 2022 H1 theft |
| Contract bugs | LPs, protocol holders | partly (pre-built breakers) | reserve delta per N blocks | USE/DexyGold 284,696 ERG, 2026-09-08 |
| Governance capture | protocol users; parameter changes | partly | parameter / vote box | Beanstalk $76-182M |
| Regulatory freeze | issued-token holders | no | issuer blacklist event | USDT $1.26B frozen 2025 |
| Privacy erosion | all | partly | none | 12M → 4M addresses (2013) |
| Clock manipulation | timestamp-based contracts | yes (use HEIGHT) | n/a | timewarp: min difficulty in ~38 days (BTC) |
| Ossification | holders needing new primitives | partly (today's opcodes) | n/a | BIP-54/360 unactivated |
| Bots / keepers stop | borrowers, lenders, KeepAlive users | yes if keyless path | expiry height, health ratio | Duckpools liquidator silent since 1,810,795 |
| Data availability | heirs, P2SH/WOTS users | partly (state on chain) | none | EIP-4444 drops 300-500 GB |
