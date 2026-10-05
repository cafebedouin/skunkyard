<!-- Written by Grok (literature seat), 2026-10-01. Checked by Claude 2026-10-01: block cost 8,001,091 and block size
1,271,009 (local mainnet node, height 1,885,338); maxTransactionCost 4,900,000 (ergo mainnet.conf:86) and
maxTransactionSize 98,304 (application.conf:53); MaxBoxSize 4096 and MaxPropositionBytes 4096 (sigmastate
SigmaConstants.scala:24, :40); CalcBlake2b256 JitCost 20 + 7 per 128 bytes, CalcSha256 80 + 8 per 64 bytes
(trees.scala); block cost = JIT / 10 (JitCost.scala:29). Not checked: external figures (Bitcoin exposure, Kaspa,
EVM costs), which are cited as reported. -->
# Literature check: Ergo post-quantum questions

Checked 2026-10-01. Search and reading only. No code, no commit, no post.

Re-fetched while writing this note, so the numbers below are from the pages themselves: `https://node.ergo.watch/info`, `https://api.ergoplatform.com/api/v1/info`, Ergo `master` sources named under cost limits, forum thread 257 as JSON, BIP-360 and BIP-361 raw text, and the ePrint 2026/374 abstract. Other entries were opened the same day and are cited by URL. A page that did not yield its text is marked **[COULD NOT OPEN]**.

A "does not exist" claim is only as wide as the search scope under that question. Each of those searches names one real hit, or says zero hits.

## Q2. Hash-based signature verifier in ErgoScript / ErgoTree

### Sources

Ergo:

- "Ergo and post-quantum crypto?", scalahub / kushti / runic, https://ergoforum.org/t/ergo-and-post-quantum-crypto/257, 2020-06-23 to 2020-09-15. Four posts. scalahub proposes replacing `proveDlog` with a lattice/LWE sigma protocol. Nobody names Lamport, Winternitz, WOTS, XMSS, or SPHINCS, and nobody gives a size.
- "Verifying Schnorr Signatures in ErgoScript", scalahub, https://ergoforum.org/t/verifying-schnorr-signatures-in-ergoscript/3407, 2022-02-19; kushti revision 2023-04-05. On-chain Schnorr: `GroupElement` public key, `sha256` then (in the revision) `blake2b256` as the Fiat-Shamir challenge, equality of secp256k1 exponentiations. kushti: the on-chain `BigInt` is 256 bits, so the signer must retry until `z.bitLength <= 255`. This checks a discrete-log signature.
- ErgoDocs FAQ, section "Quantum", https://github.com/ergoplatform/ergodocs/blob/master/docs/faq.md (`last_reviewed: 2026-05-26`). Names Lamport signatures as an example of a post-quantum scheme with efficiency and standardization limits, and says it is premature to change the chain. No script and no cost.
- ErgoDocs FUD FAQ, https://github.com/ergoplatform/ergodocs/blob/master/docs/fud-faq.md, date not stated on the page. Same position: Lamport-style schemes are not ready; sigma protocols stay.
- `extension-section.md`, https://github.com/ergoplatform/ergodocs/blob/master/docs/dev/data-model/extension-section.md, date not stated. Lists "post-quantum signatures within the Extension section" as a potential enhancement. Names no scheme.
- "EIP-0045: Native STARK Proof Verification Opcode", a-shannon, https://ergoforum.org/t/eip-0045-native-stark-proof-verification-opcode/5316, 2026-04-29, and https://github.com/ergoplatform/eips/pull/103 (open as of the fetch; not on `eips` master). Proposes `verifyStark`. States a full FRI verification at 128-bit post-quantum security takes about 784,000 JIT units of hashing before field arithmetic. That figure is for a STARK opcode, not a hash-based signature.
- "EIP-0045 × ChainCash", https://ergoforum.org/t/eip-0045-x-chaincash-how-native-stark-verification-solves-privacy-scalability-defi-compatibility/5318, 2026-05-01. Says ML-DSA signatures are kilobytes and would break the 4 KiB box limit, and that a STARK could compress them. Not a WOTS or Lamport measurement.
- "ErgoTree as an Authentication Language", https://ergoforum.org/t/ergotree-as-an-authentication-language/274, 2020-07-12. Spending conditions are sigma predicates (`ProveDlog`) composed with AND/OR/threshold.
- "Know Your Assumptions", https://ergoforum.org/t/know-your-assumptions/4198, 2023-01-31. Ergo signatures are Schnorr on secp256k1. "Hash-based" on that page means authenticated data structures and NiPoPoWs.

Analogues, with the costs the pages state:

- conduition, "OP_CAT Enables Winternitz Signatures", https://groups.google.com/g/bitcoindev/c/Zx_NMqZH65Y/, 2025-06-08, revised 2025-07-07. WOTS (`w = 16`, SHA-256) checked on Bitcoin Inquisition regtest, not mainnet. First witness stack 7,948 bytes, spending transaction 2,070 vbytes. Revised packing: about 7,212 bytes, 1,803 vbytes. Reports Jeremy Rubin's earlier OP_CAT Lamport script as a little under 8,600 bytes of script plus a 2,121-byte witness (Rubin's own post was not opened). Signet mining of the OP_CAT transaction failed.
- BIP-347, Heilman and Sabouri, https://github.com/bitcoin/bips/blob/master/bip-0347.mediawiki, assigned 2023-12-11. Motivation names post-quantum Lamport signatures as something `OP_CAT` would make expressible. No script size.
- "P2WOTS: Post Quantum UTXO Winternitz Signatures", opus-lux, https://delvingbitcoin.org/t/p2wots-post-quantum-utxo-winternitz-signatures/2530, first post 2026-05-24. Native witness-version output. Author claims "my 434 vbyte signing scheme" (the thread does not itemize the 434). Closed Bitcoin Core PR 35488 (2026-06-08, submitted to the wrong repo): 34-byte `scriptPubKey`, commitment to 64 WOTS+ keys, single-sig witness of 34 chain elements of 32 bytes each plus nonce, key index, and a 6-element auth path. Custom Signet only. The 434 vbyte sentence and the PR layout are different documents.
- Predecessor thread, same author, https://delvingbitcoin.org/t/new-post-quantum-bitcoin-proposal-using-winternitz-lamport-auth-chains/2525, 2026-05-22. Claims a Winternitz verifier "live on 16 different EVM chains". No chain ids, no addresses, no gas in the thread.
- WOTS-39, opus-lux, https://ethereum-magicians.org/t/post-quantum-erc-4337-wots-39-winternitz-one-time-signature-wallet-for-ethereum/28715, 2026-06-05. Author's size table at `w=16`: 67 chains, 2,144 bytes, about 503 verify steps; at `w=256`: 34 chains, 1,088 bytes, about 4,335 steps. Moving `w=16` to `w=256` "saves 1,056 bytes of calldata (roughly 16,000 gas)". Says `w=4096` may exceed block gas limits. No contract address on the page. The linked essay host `https://block_opuslux.ar.io/` **[COULD NOT OPEN]** (SPA shell, body was the word "Block").
- "WOTS-Tree", Javier Mateos, https://eprint.iacr.org/2026/374, received 2026-02-24, revised 2026-02-25. Preprint. Stateful WOTS+ plus a Merkle tree, `n=16`, `w=256`. Fast-path witness 353 bytes; fallback at `K=1,024` is 675 bytes; compact mode 515–692 bytes. L1 verification bound 4,601 hashes. Reference implementation, not a reported mainnet spend. Abstract's "deployed as dual leaves within BIP-341" means the specified script structure.
- BitVM `snark.md`, https://github.com/BitVM/bitvm.github.io/blob/main/snark.md, date not stated. Design note: Winternitz state transfer at 26 bytes per bit; 20 kB of signature data per 500-byte state chunk. Not a wallet signature and not a reported mainnet spend.
- ePrint 2026/1684, Sergeevitch, Staniec, Tse, Vanjani, Woll, https://eprint.iacr.org/2026/1684, abstract published 2026-08-13. BitVM Lamport commitments "would cost roughly 40 KvB in public keys and a further 20 KvB in signatures". Paper, not a deployment.
- `aglov413/kaspa-pqv`, https://github.com/aglov413/kaspa-pqv, date not stated on the README. In-script SLH-DSA and LMS on Kaspa testnet-10, using existing opcodes. Author says not run on mainnet. Measured (one input, two outputs): LMS `h=15` `w=2` redeem script 19,717 bytes, tx 24,891 bytes, 375,226 script units, fee 0.0498 TKAS; SLH-DSA-128s redeem 89,235 bytes, tx 97,473 bytes, 1,285,456 script units, fee 0.1949 TKAS. The same README also says LMS script units of 373,146 and a chain-confirmed LMS fee of 0.0597 TKAS. Both pairs are on the page.
- Kaspa Kii quoting Maksim Biriukov, https://x.com/KaspaKii/status/2069861826104340836, 2026-06-24. Testnet-10 XMSS^MT spend, script "about 84 KB" because a loop of about 1,650 hashes is unrolled. Not re-measured from the transaction.
- SPHINCS-, nicocsgy, https://ethresear.ch/t/sphincs-minus-efficient-stateless-post-quantum-signature-verification-on-the-evm/25165, 2026-06-12. Foundry `gasleft()` on a Solidity verifier, no precompile: Keccak SLH-DSA-128-24 at 94k gas, SHA2 SLH-DSA-128-24 at 142k gas, a WOTS+C/FORS+C variant at 127k gas, vanilla SPHINCS+ at 276k gas. The post says shorter Winternitz chains (`w=8`) win on execution gas. No chain or address.
- `skalenetwork/xmss-solidity`, https://github.com/skalenetwork/xmss-solidity, date not stated. Library, "no deployment". RFC 8391 XMSS-SHA2, `n=32`, `w=16`. Foundry: 745,003 gas at height 20 (about 712k at height 10). Signature 2,820 bytes at height 20.
- QuipNetwork `hashsigs-rs` README, https://github.com/QuipNetwork/hashsigs-rs, gas column dated 2026-07-13 in the README. SHRINCS-256s-keccak stateful verify 190,792 gas; stateless 1,660,931 gas. No address. (README text taken from the rendered repo page.)
- Sepolia Lamport account factory, https://sepolia.etherscan.io/address/0xF698E6E1cE4757fC7ffEB5458a9e92EfdC98D943. Contract calls `verify_u256` and exposes `LamportAccountFactory`. The opened page states no gas.

Cardano: no Plutus Lamport, Winternitz, or WOTS validator turned up. See search scope.

### Settled

No implementation, cost measurement, or concrete proposal of a Lamport, Winternitz/WOTS+, XMSS, SPHINCS+/SLH-DSA, or Merkle many-time verifier in ErgoScript or ErgoTree showed up in the Ergo forum, in `org:ergoplatform` code, issues, pull requests, and discussions, or in the ErgoHack and ePrint queries below. The docs mention Lamport as an example of a scheme they are not adopting.

The closest on-chain signature script is Schnorr (forum thread 3407). It uses `blake2b256` or `sha256` as a challenge hash over elliptic-curve points. A WOTS or Lamport verifier would instead iterate a hash on revealed preimages and compare to a committed public key.

Where other systems have actually executed a hash-based verifier, the reported cost is large: Bitcoin OP_CAT WOTS at about 1,803–2,070 vbytes on Inquisition regtest; Kaspa testnet-10 redeem scripts of about 20–89 KB and six-figure script units; EVM verifiers of full SPHINCS-family signatures at about 94k–276k gas, XMSS at about 745k gas. WOTS-Tree's 353/675-byte witnesses are a preprint layout (4,601 SHA-256 evaluations at `K=1,024`), not an Ergo or Bitcoin-mainnet measurement. Nothing in those numbers is an Ergo block-cost figure. EIP-0045's 784,000 JIT units are for FRI hashing.

### Open

Whether a practical `(n, w)` WOTS+ or Lamport verifier fits Ergo's block-cost, box, and transaction-size limits. No Ergo measurement exists to copy. The pilot in `PILOT-Q2.md` is that measurement.

What the two named kushti AMAs say about doing hash-based signatures in contracts. The watch pages respond and advertise an English auto-caption track, but the timedtext endpoint returned an empty body, so the spoken words were not recovered. See Q3.

Private forks, unpublished gists, and Telegram/Discord history. `t.me/ergoplatform` was not fetched. **[COULD NOT OPEN]** as a searchable corpus.

P2WOTS's 434 vbytes versus the closed PR's witness layout. They were not reconciled. `block_opuslux.ar.io` **[COULD NOT OPEN]**.

Which EVM deployments exist. "Live on 16 chains" has no address on the pages that rendered. The only address in hand is the Sepolia Lamport factory, with no gas figure.

Kaspa's LMS script-unit pair (375,226 vs 373,146) and fee pair (0.0498 vs 0.0597 TKAS) are both printed on one README and were not reconciled. Mainnet execution is explicitly unclaimed.

No Plutus execution-unit number exists in the queries that were run.

### Search scope

Forum Discourse JSON, 2026-10-01:

- `Winternitz`, `WOTS`, `SPHINCS`, `XMSS` at `https://ergoforum.org/search.json?q=…`: zero posts (`Winternitz` `search_log_id` 72046).
- `Lamport`: one post, TLA+ in "An Informal Approach To Specifying Multi-Stage Contracts", https://ergoforum.org/t/an-informal-approach-to-specifying-multi-stage-contracts/202, 2020-04-18.
- `post-quantum`: thread 257.
- `hash-based`: "Ergo terminology: a Box and a Register", https://ergoforum.org/t/ergo-terminology-a-box-and-a-register/32 (hash-based data structure, not a signature).
- `"hash-based" signature`: thread 5318 (FRI "entirely hash-based").
- `one-time signature`: thread 239, ErgoMix, not a one-time signature scheme.
- `Merkle signature`: thread 63, Autolykos overview.
- `Picnic`: thread 257 only.

Web:

- `Lamport OR Winternitz OR WOTS OR SPHINCS OR XMSS site:ergoforum.org`. Hit: "Know Your Assumptions", thread 4198. No verifier.
- `ErgoHack (Lamport OR Winternitz OR WOTS OR "post-quantum" OR SPHINCS)`. Hit: https://ergohack.io/ (ErgoHack 10, AI theme). The ErgoHack index at https://docs.ergoplatform.com/events/ergohack/ lists "Quantum Swap" under ErgoHack VI; the extract is a P2P exchange, not a signature verifier.
- `"ErgoScript" OR "ErgoTree" (Lamport OR Winternitz OR WOTS OR SPHINCS)`. Hit: https://docs.ergoplatform.com/dev/scs/ergoscript. No such verifier in the result.
- `site:eprint.iacr.org Ergo (Winternitz OR Lamport OR SPHINCS)`. Hit: https://eprint.iacr.org/2026/2142, "PRAWNS" (threshold hash-based signatures). The extract does not mention Ergo. Ergo hit from `"ErgoScript" OR "ErgoTree" site:eprint.iacr.org`: https://eprint.iacr.org/2020/560, Zerojoin, sigma protocols under DDH.
- `site:arxiv.org ErgoScript (Lamport OR Winternitz)`. Hit: https://ar5iv.labs.arxiv.org/html/2103.12448, quantum-access security of Winternitz. No ErgoScript.

GitHub, `org:ergoplatform`:

- Issues API `Winternitz`, `Lamport`, `WOTS`, `SPHINCS`, `XMSS`, and the OR of those: `total_count` 0. Example: https://api.github.com/search/issues?q=org%3Aergoplatform%20Winternitz.
- Issues API `"hash-based" signature`. Hit: https://github.com/ergoplatform/awesome-ergo/pull/15 (Blake2b256 commitments in registers, not a verifier).
- Issues API `post-quantum`. Hit: https://github.com/ergoplatform/eips/pull/103.
- Authenticated code search: zero files for `Winternitz`, `WOTS`, `SPHINCS`, `XMSS`, `"hash-based signature"`. `Lamport` hit `llncs.cls` (`% by Lamport.`) plus the FAQ pages above. That Lamport hit is the control that code search was returning files.
- HTML discussions search `org:ergoplatform Winternitz`: "0 results". Same for Lamport, WOTS, SPHINCS, XMSS discussions. XMSS pull-request HTML returned HTTP 429. **[COULD NOT OPEN]** that one page. Unauthenticated HTML code search demanded sign-in; the authenticated search and a Sourcegraph search of `sigmastate-interpreter`, `ergo`, `eips`, `ergo-appkit`, and `sigma-rust` covered the same strings (Sourcegraph `matchCount` 0 for Winternitz, WOTS, SPHINCS, XMSS).
- `site:github.com/ergoplatform (Winternitz OR Lamport OR WOTS OR SPHINCS OR "hash-based signature")`. First result was https://github.com/QuipNetwork/hashsigs-solidity, which is not an Ergo repository.

Analogues:

- `site:delvingbitcoin.org Winternitz OR Lamport OR WOTS`. Hit: the P2WOTS thread above.
- `site:eprint.iacr.org Winternitz (bitcoin OR ethereum OR utxo)`. Hit: 2026/374.
- `Plutus (Lamport OR Winternitz OR WOTS)` and `Cardano Plutus "Lamport" OR "Winternitz" OR "WOTS" validator`. Hit: https://developers.cardano.org/docs/developers/curriculum/smart-contracts/write-a-validator/ (an `always_succeed` validator). No hash-based signature validator in the results. IOG's Schnorr spec (https://input-output-hk.github.io/cryptography_spec/specs/schnorr.html) is Schnorr/ECDSA.
- `Kaspa (Lamport OR Winternitz OR WOTS OR SPHINCS)`. Hit: `aglov413/kaspa-pqv`.
- `"Lamport" solidity gas`. Hit: the Sepolia factory above. Pauli Group `lamportVerifier` states no gas.

## Q1. Quantum-exposed value

### Sources

Ergo (mechanism, not a measurement):

- "Ergo Addresses", Ergo Platform, https://ergoplatform.org/en/blog/2019_07_24_ergo_address/, 2019-07-24. Also https://ergoforum.org/t/ergo-addresses-details/40, 2019-07-16, and https://docs.ergoplatform.com/dev/wallet/address/address_types/. Type byte 0x01 is P2PK (serialized compressed public key), 0x02 is P2SH (192-bit Blake2b256 of the script), 0x03 is P2S (serialized script). Mining rewards go to P2S. No balances.
- "Public Keys", https://docs.ergoplatform.com/dev/scs/ergoscript/public-keys/. `proveDlog` proves knowledge of the discrete log of a 33-byte compressed secp256k1 point. No value attached.
- "Q&A on mining", https://ergoforum.org/t/q-a-on-mining-for-pool-operators-and-solo-miners/587, 2021-02-01. Mining-reward scripts are P2S and still embed the miner public key, with a 720-block timelock. The node exposes the key at `/mining/rewardPublicKey`. No aggregate ERG.
- r/ergonauts, https://www.reddit.com/r/ergonauts/comments/w6yjwh/ergo_token_supply_p2pk_addresses_vs_contracts/, 2022-07-24. Chart of *other tokens'* supply in contracts versus P2PK. No ERG total and no quantum framing.
- ErgoVision, https://explorer.erg.vn/llms.txt, index dated 2026-09-27. Rich list by balance band and a UTXO count. No split by script type.
- RunOnFlux, "Four Years, Eighteen Minutes", https://runonflux.com/four-years-eighteen-minutes-ergo-storage-rent/, 2026-09-23. Storage rent: a box unmoved for 1,051,200 blocks (about four years) can be claimed without evaluating the guard. Figures in the post are FLUX rent flows, not exposed-key value.
- Ergo forum storage-rent translation, https://ergoforum.org/t/ergo/4412, 2023-07-17. Cites a Bitcoin "nearly 20% unmoved in 5 years" figure and describes Ergo rent. The 20% is not an Ergo measurement.

Bitcoin studies that walk, or cite a walk of, the UTXO set:

- ChainQuery, "Bitcoin Quantum Exposure", https://chainquery.com/reports/quantum-exposure, page updated 2026-09-27. Full UTXO walk joined to addresses revealed in inputs and outputs. 7,142,033 BTC, about 35.5% of 20,091,873 BTC circulating, block 968,788. Always-exposed (P2PK, bare multisig, P2TR) 1,933,846 BTC. Reuse-exposed 5,208,187 BTC. P2PK: 39,465 addresses, 1,715,026.60 BTC. P2SH/P2WSH counted only when the revealed script actually pushes a pubkey and uses CHECKSIG or CHECKMULTISIG ("STRICT"). They say an earlier parser bug had P2PK near 0.85M and the headline near 30.5%.
- 21Shares Research, Bitcoin Quantum Risk Tracker, https://dune.com/21sharesresearch/bitcoin-quantum-vulnerability-monitor/70b98eb5-dde1-40c8-9f1e-d467e66f2120, index dated 2026-09-28. "Single-scan classification of Bitcoin's full UTXO set." 7,143,919 BTC verified exposed. Permanently exposed 1,714,829 BTC; exposed by design (the P2TR-scale bucket in their tiers) 218,626 BTC; reuse 5,210,464 BTC; hidden 12,943,891 BTC. Separate callout: 1,078,316 BTC in unspent P2PK created in 2009.
- Jameson Lopp, "Quantum Attack Game Theory", https://blog.lopp.net/quantum-attack-game-theory/, 2026-05-21. Cites Wicked, not a scan of his own: 6,927,060 BTC, 34.6% of supply. Also: over 1,715,000 BTC in about 34,000 P2PK keys. His "roughly 2,600,000 BTC" lost-and-exposed figure is an inference from a hodl wave, which he says also contains unexposed coins.
- Wicked Smart Bitcoin, https://wickedsmartbitcoin.com/quantum_exposure. **[COULD NOT OPEN]** the figures (page shell only). Secondhand: Lopp's 6,927,060 / 34.6%; ChainQuery says Wicked measures 34.55% at block 951,000 and that diffing Wicked's pipeline caught the P2PK undercount.
- Glassnode, "Measuring Bitcoin's Quantum-Exposed Supply", https://insights.glassnode.com/measuring-bitcoins-quantum-exposed-supply/, 2026-05-19. **[COULD NOT OPEN]** the article body (Cloudflare interstitial). Search index and Blockspace (https://blockspace.media/insight/bitcoin-quantum-risk-glassnode-2026/, 2026-05-19): 6.04M BTC, 30.2% of issued supply. Structural 1.92M (9.6%), operational/reuse 4.12M (20.6%).
- Anthony Milton and Clara Shikhelman, "Quantifying Bitcoin's Quantum Vulnerability - Part 1", https://pq-bitcoin.org/posts/bitcoin-qva-1, 2025-07-15. **[COULD NOT OPEN]** the article body (header only). Search index of that URL: at block 900,000 (2025-06-06), about 6.51M BTC (32.7%). Reuse 4.49M; inherently vulnerable 1.87M, of which P2PK 1.72M and P2TR 153k. Fork exposure (spent on Bitcoin Cash, unspent on Bitcoin) 0.15M.
- Milton and Shikhelman, Chaincode Labs, "Bitcoin and Quantum Computing: Current Status and Future Directions", https://chaincode.com/bitcoin-post-quantum.pdf, PDF dated 2025-05-28. Executive summary: theft of about 6.26 million BTC, attributed to Project Eleven as of 2025-01-17 (about 11.1 million addresses). Introduction's "20–50% (4–10 million BTC)" is a range they attribute to others (Deloitte; a 2019 Pieter Wuille tweet they gloss as almost 10 million). Script-type stocks they cite are Mark Erhardt's Dune query, not a reuse scan: P2PK about 1,720,747 BTC. They separate long-range (key already on chain) from short-range (mempool window), and they list xpubs, Lightning keys, and fork spends as leaks a UTXO scan cannot see. The body once says "mid January 2015" against a January 2025 reference; read 2015 as a typo unless the PDF sentence is rechecked.
- Deloitte, Itan Barmes, Bram Bosch, Olaf Haalstra, "Quantum computers and the Bitcoin blockchain", https://www.deloitte.com/nl/en/services/risk-advisory/perspectives/quantum-computers-and-the-bitcoin-blockchain.html, current page undated. Wayback of the old URL is 2019-12-12; a 2022 Deloitte PDF still says "as of July 2022, 25%". "Over 4 million BTC (about 25%)": p2pk about 2M, reused p2pkh about 2.5M. They do not count SegWit, Taproot, or P2SH. They also describe the short-range window between broadcast and confirmation.
- River, "Will quantum computing break Bitcoin?", https://river.com/learn/will-quantum-computing-break-bitcoin/. Page mentions "as of December 2025" for the proposal landscape and does not state a chain height or a method. "Approximately 1.72 million BTC" in P2PK, "another 4.9 million" in reused addresses of other types, together 6.8 million.
- Ahmed Raza, discussed on Delving Bitcoin, https://delvingbitcoin.org/t/quantum-sunset-economics-a-working-paper-analyzing-pact-adoption/2645, 2026-06-24 to 2026-06-29. BigQuery cohort. Treating all P2SH/P2WSH as safe: about 5.018 million BTC, 25.30%. After counting script-hash addresses as exposed once a spend revealed the script: 35.30% (about 1.3M BTC newly exposed P2SH and 685k P2WSH). Alternative with script-hash reuse and P2TR exposed only after spend: 6,854,421 BTC, 34.57%. A multisig expansion double-count inflated classified totals by about 210,000 BTC; he says the headline exposed figure was not the inflated one. SSRN PDF **[not opened]**.
- Google Quantum AI and coauthors, "Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities", https://arxiv.org/html/2603.28846v2, PDF dated 2026-04-17 in the fetch. "A little over 1.7 million bitcoin (nearly 9%)" in P2PK; "about 6.9M total bitcoin across all protocols are vulnerable" from BigQuery. A figure caption says about 6.7M for a top-100,000 cut. A separate "about 16.8 million BTC" P2TR figure is 2025 *flow*, not the unspent stock.
- Divesh Aggarwal, Gavin K. Brennen, Troy Lee, Miklos Santha, Marco Tomamichel, "Quantum attacks on Bitcoin, and how to protect against them", https://arxiv.org/abs/1710.10377, submitted 2017-10-28. Estimates when a quantum computer could break ECDSA. Does not report a UTXO stock, a P2PK total, or a snapshot height. The qualitative rule is: spending reveals the key, so do not reuse the address, and the dangerous window is broadcast until confirmation.
- BIP-360, https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki, assigned 2024-12-18, version 0.12.1 as fetched. Qualitative vulnerability table (P2PK, P2MS, and P2TR exposed at rest; hashed types exposed once a spend reveals a key). No measured BTC amount.
- BIP-361, https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki, assigned 2026-02-11. "As of March 1, 2026, over 34% of all bitcoin have revealed a public key on-chain." No block height, no category table, no method.
- CoinShares, Christopher Bendiksen, primary PDF **[COULD NOT OPEN]**. The Block, 2026-02-08, https://www.theblock.co/news/ecosystems/2026-02-08-coinshares-says-only-10200-btc-face-real-quantum-risk-pushing-back-on-overblown-estimates-388969: he narrows to legacy P2PK, about 1.6 million BTC (about 8%), and then to about 10,200 BTC in outputs he considers large enough to move the market. This is a subset, not a competing full-UTXO total.
- Coinbase Independent Advisory Board, primary PDF **[not opened]**. The Block, 2026-06-13: roughly 7 million BTC exposed, about 1.7 million in legacy P2PK. The "~20,000 addresses" in that article does not match ChainQuery's 39,465 pubkey addresses.
- Mark Erhardt, Bitcoin Stack Exchange revision, https://bitcoin.stackexchange.com/revisions/119339/4, 2023-08-17, and Dune query https://dune.com/queries/2962958. Value by output type, not by exposure. P2PK 1,733,700 BTC (9.3%) on that date. Useful as the stock a reuse join is applied to.
- duncan0k, bitcoin-dev, https://mirror.b10c.me/lists/bitcoindev/010001a06dd4cdd9-b8082042-8750-4e9a-917e-2053c919e4c4-000000@email.amazonses.com/, date not stated in the fetch. Not a measurement. Says published estimates "range from roughly 25% to over 34%" and that the spread is definitional. Draft levels: exposed at rest, exposed on spend, not exposed, undetermined.
- Project Eleven, Bitcoin Risq List, https://bitcoin-risq-list.projecteleven.com/. Direct fetch returned only "Crunching latest numbers...". **[COULD NOT OPEN]** the rendered table. Search index of that URL dated 2026-09-07: 8,019,025 BTC at block 965,912. A FAQ index dated 2026-09-14: 8,177,337 BTC at block 966,848. Their January 2025 figure, as cited by the Chaincode PDF, was 6.26M. The September 2026 gap above ChainQuery was not resolved. Older URL https://www.projecteleven.com/btc-at-risk is a 404.
- Galaxy, https://www.galaxy.com/newsroom/galaxy-launches-bitcoin-quantum-readiness-initiative, 2026-09-28. Grant announcement. No exposed-BTC measurement. No earlier Galaxy UTXO census turned up under `Galaxy Research OR "Galaxy Digital" quantum bitcoin exposed supply UTXO`.

### Settled

No published measurement of quantum-exposed ERG or tokens was found: no P2PK share of supply, no proveDlog-versus-other split, no dormancy census of exposed boxes.

The mechanism an Ergo scan has to encode is documented. A P2PK box carries the compressed public key from creation. A mining-reward box is P2S by address type and still carries the miner point. "P2S" is not "unexposed". Storage rent (1,051,200 blocks) is a separate loss mode from quantum theft: past that age the guard is not evaluated.

The Bitcoin method worth mirroring is a full UTXO walk at a named height, with three stocks reported separately: exposed because the script contains the key (P2PK, bare multisig, and, in the 2026 scans, P2TR), exposed because a hashed address was reused, and still hash-protected. Once reused P2SH/P2WSH is included, 2026 scans cluster near 34–36% of supply and near 6.9–7.1 million BTC (BIP-361's "over 34%" on 2026-03-01 with no method; Wicked/Lopp 34.6% / 6,927,060 on 2026-05-21; ChainQuery 35.5% / 7,142,033 at block 968,788 on 2026-09-27; 21Shares 7,143,919 the next day). Legacy P2PK is stable across these scans at about 1.72 million BTC and is a small number of keys. Aggarwal et al. 2017 did not count coins. Deloitte's about 4 million / 25% counts P2PK plus reused P2PKH only.

Definition choices move the headline by about ten percentage points. Raza's v1 (script-hash treated as safe) is 25.30%; adding script-hash reuse makes 35.30%. Glassnode's 30.2%, with a structural bucket (1.92M) that matches ChainQuery's always-exposed bucket (1.93M) and a smaller reuse bucket (4.12M vs about 5.2M), is the same kind of gap. ChainQuery also documents a parser bug, separate from the definition choice, that had undercounted P2PK by about 0.87M.

### Open

Any ERG amount, token amount, age histogram, or dormant-box total under bare `proveDlog`, under P2S that embeds a point, or under scripts with no group element.

What fraction of mining-reward boxes are still on the timelock script. The forum describes the mechanism and does not count them.

A dormancy histogram of the whole Bitcoin exposed set. Lopp's 2.6M is a hodl-wave inference. 21Shares publishes a 2009 P2PK total, not an age table of every exposed output.

Project Eleven's September 2026 index (about 8.0–8.2M) sits about 0.9–1.0M above ChainQuery. The live page did not render, so the cause was not checked.

Pages whose bodies were not read: Wicked, Glassnode, pq-bitcoin.org, the Project Eleven dashboard, the Coinbase PDF, the CoinShares PDF, the Raza SSRN PDF, the Wuille tweet, and Stewart et al. (ePrint 2018/213, cited by Chaincode as the commit-delay-reveal design, not opened here).

Off-chain leaks (xpubs, signed messages, bridge witnesses). Chaincode and Raza flag them and do not put a number on them.

### Search scope

- `site:ergoforum.org P2PK (balance OR supply OR "public key" OR quantum OR dormant)`. Hit: https://ergoforum.org/t/ergo-addresses-details/40. No exposed-value figure.
- `site:ergoplatform.org P2PK (distribution OR "address type")`. Hit: the 2019-07-24 address blog. No distribution statistics.
- `"Ergo" P2PK (supply OR percent OR percentage OR UTXO OR distribution)`. Hit: the r/ergonauts token chart. Also the FLUX rent post and explorer.erg.vn's balance-band API.
- `ergo.watch supply distribution address type P2PK P2S`. Hit: ErgoDocs address types. No ergo.watch script-type supply share in the results.
- `"Ergo" quantum (P2PK OR proveDlog OR "public key" OR exposed OR vulnerable) (supply OR balance)`. Hit: ErgoDocs public-key page. Other hits were Bitcoin quantum pages.
- `site:ergoforum.org (quantum OR "Shor" OR post-quantum OR "public key" exposed balance)`. Hit: thread 5318. Zero hits that quantify exposed ERG.
- Bitcoin: `quantum vulnerable bitcoin UTXO`, `"exposed public key" bitcoin (UTXO OR supply)`, `Deloitte quantum bitcoin`, `site:delvingbitcoin.org quantum (UTXO OR "public key" OR exposed)`, `BIP-360` motivation, and the named 2025–2026 reports above. Hits are the studies in the source list. `Galaxy Research OR "Galaxy Digital" quantum bitcoin exposed supply UTXO` returned the 2026-09-28 grant announcement and no census.

## Q3. Migration proposals

### Sources

Ergo:

- Forum thread 257, dates and URL above. scalahub, 2020-06-23: replace `proveDlog` with a quantum-secure sigma protocol (lattices/LWE) and a way to switch. kushti, 2020-06-25: lattice post-quantum sigma protocols exist; "they usually got broken after some investigation", real-world parameters are not well known, there are no standards. runic, 2020-09-15: asks about Picnic (https://microsoft.github.io/Picnic/). kushti the same day: the abstracts look good, and concrete efficiency and size numbers still need checking; "we maybe have a good candidate". The thread ends there.
- ErgoDocs sigma protocols, https://docs.ergoplatform.com/dev/scs/sigma/, page marked 2026-09-22. Two elementary protocols: `proveDlog` (Schnorr) and `proveDHTuple`. Same statement at https://docs.ergoplatform.com/sig-scheme/.
- `ergoplatform/eips` master tree, https://github.com/ergoplatform/eips (tree listing fetched; `truncated: false`). Files present: EIP-0001 through EIP-0006, 0015, 0017, 0019–0022, 0024, 0025, 0027, 0029, 0031, 0034, 0037, 0039, 0043, 0044. No file whose title is a post-quantum signature, a lattice sigma protocol, SPHINCS, Dilithium, Falcon, or a `proveDlog` replacement. EIP-0029 (revoked) states "A box cannot be more than 4 kbytes" as background and does not change it.
- EIP-0045 pull request, https://github.com/ergoplatform/eips/pull/103, 2026-04-29, not on master. Native `verifyStark`, and a proposal to raise `maxTransactionSize` from 96 KiB to 256 KiB, because a minimal STARK proof is about 97.9 KiB. Interpreter PR https://github.com/ergoplatform/sigmastate-interpreter/pull/1116 says it is not an activation PR. The ChainCash essay (thread 5318) says wrapping Schnorr in a STARK does not make it post-quantum, and that STARKs could compress ML-DSA signatures that do not fit in 4 KiB. That is an opcode-and-size proposal, not an ML-DSA EIP.
- EIP-0050 "Sigma 6.0", not on current master. Historical blob https://github.com/ergoplatform/eips/blob/6102112617fff96fe88013858c307c2cf363babf/eip-0050.md, header Created 25-Nov-2024, status Proposed. Adds `UnsignedBigInt` and serialization changes. Does not add a post-quantum signature. Docs, https://docs.ergoplatform.com/dev/protocol/sigma-6/ (page marked 2026-09-08), say Sigma 6.0 activated on mainnet in October 2025. Docs also say there is no accepted or activated STARK verifier EIP: https://docs.ergoplatform.com/dev/protocol/zkp/.
- "Ergo's Hybrid Method for Counting Costs", https://ergoplatform.org/en/blog/2022-02-09-ergos-hybrid-method-for-counting-costs/, 2022-02-09. JIT during script reduction, ahead-of-time for the crypto checks, so a block can hold more transactions. Not motivated there as room for post-quantum signatures. ErgoDocs JIT page calls this "(EIP-39)", https://docs.ergoplatform.com/node/jitc/. The file `eip-0039.md` on master is the monotonic box-creation-height rule, a different proposal. The number collision was not resolved.
- "Know Your Assumptions", thread 4198, 2023-01-31. Schnorr on secp256k1 is an assumption the protocol relies on. Not a migration plan.
- kushti AMA, "Ergo PoW Blockchain - Weekly Update & AMA - December 19th 2024", https://www.youtube.com/watch?v=z0vlCVoNFAw, page date 2024-12-20. **Spoken content [COULD NOT OPEN].** The watch page is playable and lists an English auto-caption track; the timedtext URL returned an empty body.
- Community AMA, https://www.youtube.com/watch?v=rICaZBdO6q4, page date 2025-08-01. **Spoken content [COULD NOT OPEN]**, same empty timedtext response.
- A separate Ergo Clips cut, "Quantum Computing and Resistance", https://www.youtube.com/watch?v=A5SJy7c3bfs, page date 2023-02-27, sourced to the 2022-03-11 AMA. Transcript that did open: planning for quantum adversaries is "fighting ghosts" until the machines exist; no Lamport, WOTS, EIP, or TPS figure.
- Alexander Chepurnoy, "Past, Present, and Future of Blockchain…", https://www.youtube.com/watch?v=JUMWImWEvMI, published 2026-07-29. Not one of the two assigned AMA URLs. A research pass reported auto-captions in which he says Dilithium-class signatures are on the order of 60× current size and would congest Bitcoin and Ethereum. Those captions were not re-fetched for this note, so the 60× sentence stays unverified here.
- ePrint search `q=Chepurnoy`, https://eprint.iacr.org/search?q=Chepurnoy&title=1&abstract=1&content=1&authors=1. The page says "No results" and also "Dates are inconsistent", so the empty result is a weak zero. Web query `"sigma protocol" lattice (Ergo OR kushti OR Chepurnoy)` returned Ergo sigma explainers and other authors' lattice-sigma papers (Beullens, ePrint 2019/490; Zhang, Gao, Xiao, ePrint 2025/313). No Chepurnoy lattice-sigma paper in that result set.

Bitcoin, as comparison:

- Agustin Cruz, bitcoin-dev, "Proposal for Quantum-Resistant Address Migration Protocol (QRAMP) BIP", https://gnusha.org/pi/bitcoindev/08a544fa-a29b-45c2-8303-8c5bde8598e7n@googlegroups.com, 2025-02-11. Mandatory migration of coins in legacy ECDSA addresses to quantum-resistant addresses, with a deadline, weighing permanent lockup against quantum theft. He calls it a BIP; the draft path is `bip-xxxxx.md` (number not assigned). https://github.com/chucrut/bips/blob/master/bip-xxxxx.md **[COULD NOT OPEN]** (GitHub 404). CoinDesk, 2025-04-05, describes it as a hard fork after which nodes reject ECDSA spends of those coins: https://www.coindesk.com/tech/2025/04/05/bitcoin-developer-proposes-hard-fork-to-protect-btc-from-quantum-computing-threats.
- Cruz, earlier and different, bitcoin-dev, 2024-10-17, "Proposal for Quantum-Resistant Cryptography in Bitcoin". Proposes SPHINCS+ and Dilithium, new Bech32 addresses, and larger signatures via a soft fork. Draft URL `bip-xxxx.md` was not fetched.
- BIP-360, Hunter Beast, Ethan Heilman, Isabel Foxen Duke, https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki. As fetched: title **Pay-to-Merkle-Root (P2MR)**, status Draft, type Specification, assigned 2024-12-18, version 0.12.1, requires BIPs 340, 341, 342. Soft fork. SegWit version 2, addresses `bc1z`. Same script-tree machinery as Taproot with the key-path spend removed, so the output commits to a Merkle root and not to an internal key. Control block is `1 + 32*m` bytes. The text says it "does not include the introduction of post-quantum signature schemes" and that ML-DSA or SLH-DSA "should be scrutinized before use" in a separate future proposal. Long-exposure resistance comes from not putting an elliptic-curve key in the output. Short-exposure (mempool) resistance is deferred. Depth-0 trees are anyone-can-spend. Changelog in the same file: the document was previously titled P2QRH, then P2TSH (0.10.0, 2025-09-17), then P2MR (0.11.0). A secondary guide that still says P2QRH "supports" SLH-DSA, ML-DSA, and Falcon (https://www.quanchain.ai/guides/bitcoin-bip-360-p2qrh-quantum-resistance, 2026-08-14) contradicts the current file.
- BIP-361, Jameson Lopp, Christian Papathanasiou, Ian Smith, Joe Ross, Steve Vaile, Pierre-Luc Dallaire-Demers, https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki. As fetched: title "Post Quantum Migration and Legacy Signature Sunset", status Draft, type Informational, assigned 2026-02-11, requires "TBD Post Quantum Signature BIP". Phase A: permitted sends are from legacy scripts to post-quantum scripts, 160,000 blocks (about 3 years) after activation. Phase B: "Restricts ECDSA/Schnorr spends by encumbering them with a quantum-safe rescue protocol", flag day five years after activation (table: 2 years after Phase A). Rescue is unspecified (BIP-32 hardened derivation, a ZK-STARK, or commit/reveal). "It remains to be seen how much of the legacy Bitcoin supply can be theoretically covered." P2PK has no known rescue; the authors support an "Hourglass" style rule for P2PK. The Hourglass document itself was not opened. News from 2026-04-15 (https://news.bitcoin.com/bitcoin-developers-propose-freezing-coins-that-skip-quantum-safe-migration-under-bip-361/) describes an earlier wording in which Phase B made legacy signatures invalid. The raw file after the 2026-04-20 correction is the rescue-encumbrance wording. VanEck, 2026-09-24, still summarizes the older wording and says both BIPs remained drafts as of September.
- BIP-360 related-work section points at commit-reveal designs (a 2018 mailing-list note, a 2025 Fawkescoin variant, and Tadge Dryja's "Lifeboat" talk) and at Vitalik Buterin's Ethereum emergency-fork note. Those were not opened past the BIP's citations. No hybrid Schnorr-plus-post-quantum BIP text was opened. NIST IR 8547's hybrid exception appears in BIP-360 as background, not as a Bitcoin hybrid-signature BIP.

### Settled

Ergo's written record of a `proveDlog` replacement is the 2020 forum suggestion: lattices or, later in the same thread, Picnic, with kushti asking for sizes that were never posted. Master of `ergoplatform/eips` contains no post-quantum signature EIP. The deployed elementary protocols are still `proveDlog` and `proveDHTuple`.

EIP-0045 is an open, explicitly unactivated proposal for a STARK opcode and a larger transaction cap. Its authors use ML-DSA as an example of a signature that does not fit in a 4 KiB box. It does not sunset `proveDlog`.

On Bitcoin, the document numbered BIP-360 is a draft soft fork for a new output type (P2MR) that removes Taproot's key-path spend and does not commit to a post-quantum signature algorithm. The name P2QRH is a previous title of that same document. BIP-361 is a draft sunset whose header says it still depends on a post-quantum signature BIP that is not yet specified. QRAMP is Cruz's 2025-02-11 mailing-list proposal for a deadline after which legacy ECDSA spends fail. It was not assigned a BIP number, and the draft body 404'd.

Against the two shapes in the pilot: P2MR is "soft-fork a new output that still does not verify a post-quantum signature". QRAMP and BIP-361 are deadline rules that assume such an output already exists. EIP-0045 is "soft-fork a new verifier, and raise the transaction cap". None of the opened Ergo documents is a measured "verify WOTS in today's ErgoScript" path. That path is Q2, and it is unmeasured.

### Open

What kushti said on 2024-12-19 and what was said on 2025-07-31. `SCOPE.md` attributes to the December AMA a 10×–100× TPS cost for post-quantum signatures, and to the July AMA a "fork once protocols mature". The video pages exist. The caption bytes did not download, so those sentences are not confirmed here. A 2022 AMA clip that did transcribe contains neither sentence.

Whether a Chepurnoy paper sketches a lattice sigma protocol for Ergo. The queries above did not find one. The ePrint author index that returned "No results" also warned that its dates are inconsistent, so "he has no eprints" is not a finding.

The full QRAMP text (deadline height, the signature algorithm, and whether unmoved coins are burned or recoverable). **[COULD NOT OPEN]** https://github.com/chucrut/bips/blob/master/bip-xxxxx.md.

EIP-0050's absence from master versus the docs' "activated October 2025", and which file is the JIT-costing EIP (docs say EIP-39; `eip-0039.md` is a different proposal). Neither is a signature-scheme change.

Whether anyone later computed the Picnic sizes kushti asked for in September 2020. The Picnic forum search hit only thread 257.

### Search scope

- `site:ergoforum.org (post-quantum OR "post quantum" OR lattice) (proveDlog OR sigma OR signature)`. Hits: thread 257 and the 2026 EIP-0045 threads.
- `site:github.com/ergoplatform/eips (post-quantum OR lattice OR SPHINCS OR Dilithium OR Falcon)`. Web search did not return files in that repo (a same-search hit was https://github.com/paulmillr/noble-post-quantum). The master tree was then listed directly: no merged file is about those terms. The Ergo-repo hit with those words is unmerged PR 103.
- `"sigma protocol" lattice (Ergo OR kushti OR Chepurnoy)`. Hit: Beullens, ePrint 2019/490, which is not an Ergo proposal.
- `site:eprint.iacr.org Chepurnoy (lattice OR "sigma protocol" OR post-quantum)`, and the on-site search URL above. On-site: "No results", with the UI warning. A same-family web hit is Blockstream, "Lattice-based Signature Schemes for Bitcoin", https://eprint.iacr.org/2026/1628, 2026-08-06, authors Zakharov, Kudinov, Balatska, Chopa. Not Chepurnoy.
- `Ergo (Dilithium OR Falcon OR SPHINCS OR ML-DSA) (EIP OR fork OR "soft fork")`. No Ergo soft fork adopting those schemes. Hits: Ethereum EIP-8051 (ML-DSA precompile, draft, created 2025-10-15) and Ergo thread 5318, which mentions ML-DSA as a payload a STARK might compress.
- `BIP-360`, `P2QRH`, `QRAMP`, `BIP-361`. Hits are the files and the mailing-list post above.

## Ergo cost and size limits

Live values are from `https://node.ergo.watch/info`, fetched 2026-10-01. `fullHeight` 1,885,335, `bestFullHeaderId` `dbf85993853d329206c10de3b13d62504f567e994e118b93018fef73d9e558d2`, `appVersion` `5.0.21-0-1a417f44-20240401-1043-SNAPSHOT`. The `parameters` object is stamped at height 1,885,184 (the epoch boundary; voting epochs are 1,024 blocks):

| Field | Value |
| --- | --- |
| `maxBlockCost` | 8,001,091 |
| `maxBlockSize` | 1,271,009 |
| `blockVersion` | 4 |
| `inputCost` | 2,407 |
| `outputCost` | 298 |
| `dataInputCost` | 100 |
| `tokenAccessCost` | 100 |
| `storageFeeFactor` | 1,250,000 |
| `minValuePerByte` | 360 |

`https://api.ergoplatform.com/api/v1/info` returned the same `lastBlockId` and height 1,885,335, and a stale `params` object: `height` 506,880, `maxBlockCost` 7,030,268, `blockVersion` 2, `inputCost` 2,000, `outputCost` 100. Do not take script-cost limits from that endpoint.

Code is `master` of `ergoplatform/ergo` and `ergoplatform/sigmastate-interpreter` as fetched the same day. Line numbers are from those files.

### Per-block script cost

- **Mainnet value:** 8,001,091 block-cost units, parameters height 1,885,184.
- **Defined at:** `ergo-core/src/main/scala/org/ergoplatform/settings/Parameters.scala` line 68, `lazy val maxBlockCost: Int = parametersTable(MaxBlockCostIncrease)`, comment "Max total computation cost of a block." Vote id `MaxBlockCostIncrease = 4` at line 272. Launch default `MaxBlockCostDefault = 1000000` at line 318. Voting floor `16 * 1024` at line 354. Parameter 4 is absent from `maxValues` (lines 363–367), so the code ceiling is `Int.MaxValue / 2`. The step is `currentValue / 100` because parameter 4 is also absent from `stepsTable` (`updateParams`, and `stepsTable` at line 346).
- **Miner vote:** yes, parameter id 4.
- **What it counts:** a running total across every transaction in the block. `ErgoTransaction.scala` line 120 sets `maxCost` from `currentParameters.maxBlockCost`, and line 159 rejects the block when the accumulated cost exceeds it (rule message in `ValidationRules.scala`, rule id 307, "Accumulated cost of block transactions should not exceed <maxBlockCost>."). The budget includes per-input, per-output, per-data-input, and per-token costs from the parameter table, not only script opcodes (`ErgoTransaction.scala` around lines 381 and 398).

No EIP opened here sets 8,001,091. The value is the voted parameter, about eight times the launch default, which matches repeated +1% steps. The vote history was not reconstructed.

### Per-transaction script cost

There is no second consensus parameter. One transaction may consume whatever block budget remains, up to 8,001,091 if it is the only costed transaction (`ErgoTransaction.scala` lines 120 and 135, `costLimit = maxCost - currentTxCost`).

Propagation is separate. `src/main/resources/application.conf` line 50: `maxTransactionCost = 1000000`, comment "maximum cost of transaction for it to be propagated". `src/main/resources/mainnet.conf` line 86 overrides that to `4900000`. This is node config, not parameter id 4, so miners do not vote it. A public endpoint that reports the running node's `maxTransactionCost` was not found. 4,900,000 is the value shipped in `mainnet.conf`, not a reading of the ergo.watch process.

### Max box size

- **Value:** 4,096 bytes.
- **Defined at:** `sigmastate-interpreter` `core/shared/src/main/scala/sigma/data/SigmaConstants.scala` lines 24–26, `MaxBoxSize = 4 * 1024`, constant-table id 1. Not a row in `parametersTable`.
- **Enforced at:** `ErgoTransaction.scala` line 175, rule `txBoxSize`: `out.bytes.length <= MaxBoxSize.value`. Line 176, rule `txBoxPropositionSize`: `out.propositionBytes.length <= MaxPropositionBytes.value`, and `MaxPropositionBytes` is also 4,096 (`SigmaConstants.scala` lines 40–41, id 5).
- **Miner vote:** no.
- EIP-0004 and revoked EIP-0029 restate "4 kilobytes" / "4 kbytes". They do not define the constant.

`MaxBoxSizeWithoutRefs` is 4,062 (`SigmaConstants.scala` lines 44–46). Whether that constant is its own validation rule was not traced.

### Registers and context variables

- **Registers:** `MaxRegisters = 10` (`SigmaConstants.scala` lines 36–37, id 4). R0–R9. No per-register byte cap was found beyond the 4,096-byte box and the type caps: `MaxBigIntSizeInBytes = 32` (line 49), `MaxSigmaPropSizeInBytes = 1024` (line 53).
- **Context variables:** `ContextExtension.scala` lines 46–47 reject more than `Byte.MaxValue` entries. Lines 53–58 read the count and each id with a signed byte and reject a negative count or a negative id. So at most 127 variables, ids 0 through 127. No per-variable byte cap in that serializer. `GetVar` is a fixed JIT cost in `transformers.scala` (the search recorded `JitCost(10)` near line 589; that line was not re-read while writing).

A `Coll[Byte]` in R4–R9 or in a context variable is bounded by the box (4,096) and by the transaction fitting the block (and, to be relayed, the 98,304-byte mempool cap below).

### Block size and transaction size

- **Max block transactions section:** 1,271,009 bytes on mainnet. `Parameters.scala` line 43, `maxBlockSize`, vote id `MaxBlockSizeIncrease = 3` at line 269. Default `512 * 1024` at line 314. `MaxBlockSizeMax = 1024 * 1024` at line 315 is not in `maxValues`, and the live value is already above 1,048,576, so that constant is not the enforced cap. Miner-votable, parameter id 3. Checked as `fb.blockTransactions.size <= currentParameters.maxBlockSize` (rule id 306; cited from `ErgoStateContext.scala` in the search, not re-opened while writing).
- **Max transaction size for mempool and API:** `application.conf` line 53, `maxTransactionSize = 98304` with comment "96 kb". `mainnet.conf` does not override it. Not a voted parameter. Docs "Maximum transaction size: 96kb" match this figure (https://docs.ergoplatform.com/mining/gov/voting/). A stock node can refuse a transaction that would still fit in a 1,271,009-byte block.

### What a cost unit is, and what a hash costs

`JitCost.scala` lines 4 and 29: JIT cost is a 10× scale, and `toBlockCost` is `value / 10`. The block limit counts block-cost units, after that division of the accumulated JIT total.

`trees.scala` lines 555–583, `CalcBlake2b256`: the comment says the old 1,000,000 block-cost budget was aimed at 1 second, so 1 block-cost unit was aimed at 1 microsecond, and then sets

```
PerItemCost(baseCost = JitCost(20), perChunkCost = JitCost(7), chunkSize = 128)
```

`CalcSha256`, lines 601–605:

```
PerItemCost(baseCost = JitCost(80), perChunkCost = JitCost(8), chunkSize = 64)
```

The executable numbers are those `PerItemCost` lines. The comment's "1 cost unit per 128-byte Blake2b" does not match the stored base 20 plus 7, and the comment's "factor of 10" does not match the stored 7. Both sentences are in the same doc comment.

`fold` and `map` exist. `transformers.scala` lines 52–53, map overhead `JitCost` base 20 plus 1 per 10 elements; lines 236–237, fold overhead base 3 plus 1 per 10 elements. The evaluator then runs the lambda per element (`foldLeft` at line 230, `map` at line 45), so a hash in the body is paid once per element on top of that overhead. The language overview that lists these operations and does not list a general `while` is `docs/LangSpec.md` in sigmastate-interpreter (opened during the search; not re-fetched while writing).

### Settled

The limits a WOTS pilot has to fit, on mainnet as of height 1,885,335:

- Block cost 8,001,091, miner-votable parameter 4. One transaction can use the remainder of that budget. Relay cap shipped in `mainnet.conf` is 4,900,000.
- Box 4,096 bytes, proposition bytes 4,096, neither voted.
- Ten registers, no separate per-register byte cap. Context extension: at most 127 variables, no per-variable byte cap in the serializer.
- Block transactions section 1,271,009 bytes, parameter 3. Relay transaction size 98,304 bytes, config.
- Blake2b256 and Sha256 costed as the `PerItemCost` values above, in JIT units, summed, then divided by 10.

### Open

Whether any miner's running config differs from `maxTransactionCost = 4900000`. Not queried from a live process.

The exact sequence of parameter-4 votes that produced 8,001,091. Not decoded from block extensions.

`MaxBoxSizeWithoutRefs` (4,062) as an enforced rule. Constant only.

How many Blake2b256 calls fit in 8,001,091 after `interpreterInitCost` and the per-input costs. The table above is enough to compute it; it was not computed here. `interpreterInitCost = 10000` was read from `Interpreter.scala` during the search (recorded at line 513) and was not re-opened while writing.

## Unverified leads (added 2026-10-04 from an outside-model landscape summary; check every item against its primary source before anything quotes it)

None of these has been read here. Each needs the primary source (BIP text, research post, EF/Foundation announcement,
paper, repository) and its date confirmed; drop any that do not check out.

- **Bitcoin.** Blockstream Research argued (reported May 2026) for a native hash-based opcode, `OP_CHECKSHRINCS`, built
  on SHRINCS and SHRIMPS, with SHRINCS reportedly demonstrated on Liquid. Bitcoin Optech's quantum-resistance topic page
  (BIP-361, a SHRINCS draft BIP, lattice proposals, commit/reveal rescue schemes). Relevance: precedent for the native
  verifier question (SK-028) and a third "shape" (stateful/stateless hybrid) beside WOTS+/XMSS and SLH-DSA.
- **Bitcoin exposure figure.** "About 7.1 million BTC, roughly 35% of supply, at addresses whose pubkey is already
  revealed", from a weekly UTXO walk. Needs the source and its definition of "revealed" (P2PK outputs, reused P2PKH,
  Taproot key-path) before any comparison with our 96.58% of non-protocol ERG; published estimates vary widely with
  the definition.
- **Ethereum.** A Foundation post-quantum team (January 2026); a December 2029 target for a quantum-resistant L1
  (reported September 2026); consensus aimed at leanXMSS (stateful hash-based) with zkVM aggregation; user accounts via
  account abstraction (EIP-8141, aimed at the Hegotá fork) and verification precompiles. Relevance: the precompile route
  is the same opcode question at protocol scale; leanXMSS supports the stateful line.
- **Solana.** Winternitz vault (January 2025) — already cited in skunks/manytime/LITERATURE.md; the new leads are
  Winterwallet, later tokens on the primitive, and a Project Eleven post-quantum signature testnet.
- **Sui.** NIST ML-DSA-65 for native accounts (testnet late 2026, mainnet early 2027 reported) and SLH-DSA verified
  inside Move contracts for large-value vaults, "so the hash scheme can change without a core upgrade". Relevance:
  argues for a generic primitive over a fixed WOTS opcode (ROADMAP item 7).
- **Algorand.** Falcon-signed state proofs; Falcon transactions on mainnet; a 2027 resilience roadmap.
- **QRL.** XMSS since 2018 (already cited); 2.0 testnet reportedly moving toward ML-DSA — check, it bears on the
  stateful-vs-lattice choice.
- **Aptos.** Grouped with Solana in hardening coverage — vague; find a primary source or drop.
