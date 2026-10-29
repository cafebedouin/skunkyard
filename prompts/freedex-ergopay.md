# Ergo Mobile Wallet and Terminus: signing from the phone with ErgoPay, no server

You are adding a second signing path to FreeDEX, in `/home/scott/bin/freedex` (CC0, live at
https://cafebedouin.github.io/freedex/, one Pages run per push) with its record in
`/home/scott/bin/skunkyard/skunks/dexpage/`. Read first: `/home/scott/bin/skunkyard/CLAUDE.md` and `PROGRAM.md`
(every number names its printed output, nothing outward without the person's go, the GitHub Actions budget), then
`research/agents/ROADMAP.md` R5 (the three checks this session closes) and `skunks/dexpage/RESULT.md`. Then in
freedex: `src/ui/wallet.ts` and `src/wallet.ts` (the EIP-12 path every tab already goes through), `src/ui/store.ts`,
`src/explorer.ts` (headers are not fetched yet; you will add that), `index.html` (the Content-Security-Policy meta
tag), and `test/ui/` for the happy-dom harness.

## What exists, and the facts that decide the design

- Every tab builds an unsigned transaction with Fleet and hands it to one `send()` in `src/ui/wallet.ts`, which
  today means Nautilus or SAFEW through EIP-12: the wallet signs and submits. Terminus is the iOS build of the Ergo
  mobile wallet, one codebase, and it has no dApp connector: it signs through ErgoPay (EIP-20) only.
- EIP-20's static mode puts the reduced transaction inside the QR code or link itself, `ergopay:<base64url>`, with
  no server; the wallet signs and submits, and the page learns the result by polling the explorer with the
  transaction id, which is the same before and after signing. The EIP says links and QR codes handle up to about
  2,900 characters. Measured on 2026-10-29 with sigma-rust's WASM binding over three of the page's real mainnet
  transactions: a limit-order fill reduces to 705 bytes (948 characters encoded), a pool swap to 893 (1,199), a
  liquidity deposit to 929 (1,247). Everything the page builds fits, at under half the limit.
- Fleet cannot reduce a transaction. `ergo-lib-wasm-browser` 0.28.0 can (`ReducedTransaction.from_unsigned_tx`
  with the inputs, data inputs and an `ErgoStateContext` built from the last ten block headers). Its WASM is 2.4 MB,
  so it loads only when the phone path is chosen. The headers the explorer serves at `/api/v1/blocks/headers` carry
  the fields the binding's `BlockHeaders.from_json` needs (id, parentId, version, timestamp, nBits, height, votes,
  stateRoot, adProofsRoot, transactionsRoot, extensionHash, powSolutions); parsing them through the binding is the
  one step not yet run, and it is the first thing to run.
- The static mode has no address placeholder and no reply URL. The visitor types or pastes their address once,
  the page keeps it in this browser, and reads their boxes and balances from the explorer by address.
- The mobile wallet's cold-signing flow uses multi-part QR codes; whether a static ErgoPay QR of 1,200 characters
  is accepted by the current app is unverified. Mew and ErgoDEX prove the wallet's ErgoPay path, in dynamic mode.

## Do, in this order

1. **The reduction, in Node, against mainnet state.** `scripts/reduce.ts`: fetch the last ten headers from the
   explorer, build the state context through `ergo-lib-wasm-nodejs` (pinned 0.28.0, dev dependency), reduce one
   unsigned transaction the page's builders produce for the test wallet's address (a pool swap, read-only, nothing
   submitted), print the reduced size in bytes and the `ergopay:` string's length. If the explorer's headers do not
   parse, say exactly which field, and fall back to the Cornell mirror's node-shaped headers for the record. This is
   the first of the three checks and it decides whether to continue.
2. **A `Signer` abstraction** in `src/wallet.ts`: `{ kind: "eip12" | "ergopay"; address; utxos(); balance(id);
   sign(tx): Promise<txId> }`. The EIP-12 implementation is today's code. The ErgoPay implementation reduces the
   transaction (dynamic import of `ergo-lib-wasm-browser` 0.28.0, pinned; the state context from the explorer's
   headers, read fresh for each transaction), encodes it base64url, shows a QR code and an `ergopay:` link, then
   polls the explorer for the id every ten seconds for up to twenty minutes, and resolves with the id when it
   appears in the mempool or a block. A QR library pinned to an exact version at least two weeks old, rendered
   into a canvas; no external script.
3. **The header control**: beside "connect Nautilus", a "sign with your phone" option that asks for the address
   once (validated as a mainnet address), stores it in this browser, and selects the ErgoPay signer. Every tab
   keeps calling `send()`; nothing else changes. The upkeep timer stays keyless and unaffected; the two signed
   upkeep jobs (the lender's collateral, the writer's reclaim) go through the same signer and so show a QR too.
4. **The CSP.** The WASM needs `'wasm-unsafe-eval'` in `script-src`; add only that, keep everything else.
5. **Size guard.** Before showing a QR, measure the encoded length; above 2,800 characters, say the transaction is
   too large for a QR code and suggest fewer inputs (the explorer lists the visitor's boxes, so the builder can
   limit selection), rather than show an unreadable code.
6. **Tabs wrap.** The nav is a flex row; give it `flex-wrap: wrap` and a small row gap so the tabs stack into rows
   on a narrow screen. Keep the page's maximum width as it is.
7. **Tests.** The harness can stub the wallet; add a stubbed ErgoPay signer test that walks the tab's `send()`
   through a reduced-transaction stub, shows the QR element, and resolves on a polled id. Unit-test the base64url
   encoding and the size guard. The real reduction has its Node script from step 1 and its printed numbers.
8. **The person's check.** You cannot scan a QR. Write the exact steps for the person into `RESULT.md`: open the
   live page on the desktop, choose "sign with your phone", enter the test wallet's address, build a 0.005 ERG pool
   swap, scan with the Ergo mobile wallet (or Terminus), sign, and read the id the page reports; then on the phone
   itself, open the page in the phone's browser and tap the `ergopay:` link; then, if a Satergo desktop wallet is
   available, click the link there and note whether Satergo opens it (the third check, still unverified). Leave the
   result table with those rows empty for the person to fill, each with the printed evidence it needs.
9. **Record and push**: `skunks/dexpage/RESULT.md` gains a dated section with the reduction numbers from step 1 and
   the empty mainnet rows; `research/agents/ROADMAP.md` R5's three checks are updated with what this session
   settled and what waits on the phone; worklist SK-063 and `NEXT.md` updated; skunkyard committed locally, not
   pushed; freedex pushed once at the end with the README's "Use it" section covering the phone path and the
   cost table unchanged (the phone path adds no fee; the wallet submits).

## Do not

- Add a server, a relay, or any dynamic ErgoPay endpoint. If the static mode cannot work, say so and stop; a page
  that needs a server is tokenjay, and it exists.
- Load the WASM for Nautilus users, or load any script from outside the page's own origin.
- Store anything but the visitor's chosen address and explorer in the browser.
- Submit any mainnet transaction yourself; the phone path is the person's to exercise.

## Done when

Step 1 prints a reduced size for a real transaction against mainnet headers; the ErgoPay signer is live on the page
behind the header option with the QR, the link, the poll and the size guard; the tabs wrap; lint, typecheck, tests
and build are green; the Pages run passes; and `RESULT.md` holds the numbers and the person's checklist with its
rows waiting.
