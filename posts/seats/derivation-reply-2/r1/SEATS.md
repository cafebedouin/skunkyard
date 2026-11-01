# Reply to topic 5385 post 2 — review round 1 (2026-11-01)

Draft v1 → six reviews → draft v2 (`posts/2026-11-derivation-reply-2-draft.md`).

| reviewer | file | taken |
|---|---|---|
| Derivation (Claude, blind, source first) | seat-derivation.md | "depth-3 extended public key"; Ledger confirmation is skipped for a known app token; SAFEW and Minotaur added (both re-read from source before use: SAFEW `1fcf4a9e` `src/ergo-related/ledger.js:14-26,44,72,99,216,260`; Minotaur `2c1ba72c` `apps/wallet/src/action/wallet.ts:66-73`, `packages/utils/src/address.ts:8`); survey line fixes; its BIP32 script copied to `skunks/pqwallet/scripts/xpub_depth3_reach.py` and re-run (root key half matches the published vector). |
| Fidelity (Claude) | seat-fidelity.md | "none of these wallets" (not the Ledger app); credit line added; survey must be pushed before posting. Mobile wallet builds against an appkit snapshot: noted in the survey. |
| Maintainer (Claude) | seat-maintainer.md | correction moved to the top as the short answer; "nothing here asks a wallet to change"; host log/cache back in not-checked; EIP step offered rather than announced (operator's call). |
| Grok (grok-4.7-build) | out/grok-*.raw.txt | confirmation wording; Satergo "store" wording; Nautilus stores the `/0` node with depth/fingerprint bytes zeroed (`hdKey.ts:61-68`) → "keep the `/0` node". Its doubt whether Nautilus derives `/0` was checked: `ledger-ergo-js` 0.2.1 returns an object (`dist/erg.d.ts:29-31,225`), so the path is applied. |
| Gemini | out/agy-*.raw.txt | confirmation wording; correction verified; raised that the Ledger app would refuse any `m/8391'` path (true; post 1 already says hardware gets no PQ signer — not added). |
| Muse | out/muse-*.answer.md | correction buried → moved up; last sentence overclaimed → softened, "five hardened levels" dropped. |

Not re-reviewed after revision.
