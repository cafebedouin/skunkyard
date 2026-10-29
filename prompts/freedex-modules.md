# freedex: one module per tab, UI tests, and the small things the reviews left

You are working in `/home/scott/bin/freedex`, the canonical repository of FreeDEX for Ergo (CC0, published to
https://cafebedouin.github.io/freedex/ by one GitHub Pages run per push to `main`). Its record lives in
`/home/scott/bin/skunkyard/skunks/dexpage/` (`CHARTER.md`, `RESULT.md`, `mainnet/README.md`); read those first, then
freedex's `README.md` and `THIRD-PARTY-NOTICES.md`. Read `/home/scott/bin/skunkyard/CLAUDE.md` and `PROGRAM.md` for
the house rules: every number names its script and printed output, nothing outward without the person's go, and the
GitHub Actions budget (tens of runs a day; each push here is one run, so batch your pushes).

## What exists

A static page with no server and no fee of its own: six tabs (Swap on ErgoDEX v1 ERG and token-to-token pools with
the SigmaUSD bank quoted beside, Limit orders on Machina, Pool, Bank, Bonds on SigmaFi, Escrow on TokenJay's
contract) and keyless chain upkeep for a connected visitor. Every transaction builder is a pure function in `src/`
with a mock-chain test against the deployed contract bytes (42 cases, `npm test`), and 25 mainnet transactions back
them. The whole UI is `src/main.ts`, about 1,100 lines of global state, DOM rendering and handlers in clearly
delimited sections, with no UI tests. Two reviews on 2026-10-30 asked for the split and the tests; the security and
slippage findings from those reviews are already fixed.

## Do, in this order

1. **One module per tab.** `src/ui/wallet.ts`, `swap.ts`, `orders.ts`, `pool.ts`, `bank.ts`, `bonds.ts`,
   `escrow.ts`, `upkeep.ts`, plus `src/ui/dom.ts` (the `$`, `td`, `tdCode`, `thead`, `dl`, `log` helpers) and
   `src/ui/store.ts`, a small typed store for the shared state (wallet, explorer, tokens, pools, t2tPools, bank,
   the selected assets) with `subscribe` so a tab re-renders when the wallet or the listings change. `main.ts`
   becomes the tab switcher and boot. No behaviour change: the built bundle must do exactly what it does now.
   Keep the rule that chain-sourced strings only ever become text nodes; grep for `innerHTML` must stay at zero.
2. **UI tests** with `happy-dom` in Vitest (add it as a dev dependency, pinned). Test the pure parts of the UI first:
   route resolution in the swap tab (ERG pool, direct T2T pool, "no direct pool"), the quote rows including the
   stale-quote refusal, deposit amounts from either side, the bank's "allowed" line, and the orders grouping and
   ordering. Render `index.html` into happy-dom with the explorer and wallet stubbed, drive the inputs, and assert on
   the DOM text. Add a test that no element in the rendered page has an `on*` attribute or inline script.
3. **Prettier and ESLint**, pinned, with a print width of 120, run in CI before the tests. Fix what they report; do
   not reformat the contract-bytes constants into unreadable line breaks (exclude the JSON and the long hex lines).
4. **Small features the reviews and the user asked for, each with a test:**
   - List EIP-31 Babel boxes on the Limit orders tab as "buy tokens" orders beside Machina's (same template-hash
     query as `src/babel.ts`; takers sell tokens into them; a `buildFillBabel` builder with a mock-chain case).
   - A keyless upkeep job that hands matured SigmaFi collateral to the lender when the connected visitor is that
     lender (the path is keyless; the miner fee comes from the visitor's change, so only when they benefit).
   - "Your positions" at the top of the Bonds and Escrow tabs: the visitor's own rows first, before the market.
   - A one-line status in the header when the explorer fell back to its second backend.
5. **Sync the record.** Copy `src/`, `test/`, `scripts/`, `index.html` and the workflow back into
   `/home/scott/bin/skunkyard/skunks/dexpage/`, add a dated section to its `RESULT.md` saying what changed and what
   the tests print, and commit skunkyard locally (do not push skunkyard). Push freedex once at the end.

## Do not

- Add any fee, address or default that routes value to the operator. The page's whole claim is that it has none.
- Change the contract builders in `src/*.ts` except to add the Babel fill. They are verified on mainnet as they are.
- Submit any mainnet transaction. The test wallet and its guarded signer (`skunks/oneshot/scripts/mainnet-sign.mjs`)
  are for the person to use; this session is UI work and needs none.
- Reach for a framework. The page is plain TypeScript and DOM on purpose; the modules should be too.

## Later, not this session

The clocked box (SK-064), the timed-escrow option (SK-065), Duckpools borrowing, and the mobile ErgoPay path are
chartered in `/home/scott/bin/skunkyard/WORKLIST.md` and each is its own session with its own contract work.

## Done when

`npm run lint`, `npm run typecheck`, `npm test` and `npm run build` are green; `src/main.ts` is under 150 lines;
the UI tests cover the five behaviours above; the Pages run on the push passes; and the person can open the live
page and see no difference except the new rows and the header line.
