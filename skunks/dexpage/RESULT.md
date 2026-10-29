# dexpage: result (in progress)

## Built 2026-10-29

Static page, no server: `index.html`, `src/`, built by Vite into `dist/` (one HTML file and one JavaScript file,
79.32 kB, 25.67 kB gzipped, as `npx vite build` printed). Dependencies pinned in `package.json`: Fleet 0.12.0,
`@nautls/machinafi-sdk` 0.1.0, `@nautilus-js/eip12-types` 0.1.11.

## Mock chain: the builders against the audited E2T contract (`run-test.log`)

```
 ✓ test/orders.test.ts (4 tests)
 Test Files  1 passed (1)
      Tests  4 passed (4)
```

The four cases: the owner sells tokens (create, a partial fill of 40 of 100, the full fill, the owner paid);
the owner buys tokens (create with a 1 ERG budget, a taker sells 30 in, the owner closes the rest and gets the
30 tokens); a taker's attempt to close another's order (refused); a fill that pays for 3 tokens and takes 4
(refused, the order unchanged). The expected values are in `test/orders.test.ts`.

## Mainnet, read-only: the live orders through the page's own code (`run-list.log`)

```
height 1904918; 38 boxes under the template; 38 parsed as orders, 0 rejected; 4 tokens
  7a51950e5f  10  rsBTC (8 decimals)
  f0cac602d6  10  FAKU (2 decimals)
  581d7df258   9  rsFIRO (8 decimals)
  e023c5f382   9  rsADA (6 decimals)
```

`scripts/list-orders.ts` calls `Explorer.limitOrders` (a POST to `/api/v1/boxes/unspent/search` by the template's
SHA-256, `scripts/template-hash.mjs`) and `describe` on every box. The explorer answered a cross-origin POST
preflight with `access-control-allow-origin: *` and `access-control-allow-methods` including POST (curl,
2026-10-29), so the deployed page can make the same call.

## Mainnet, signed: every builder through the test wallet (`mainnet/README.md`)

Ten transactions on 2026-10-29, all built by the page's code, signed and checked by the guarded signer, mined:
fill a stranger's order (A), place an order (B), partial fill of it (C), close it (D), a direct pool swap each way
(S1, S2), a liquidity deposit (L1) and its redemption (L2), a direct token-to-token swap (T1). Transaction ids and
the wallet's net per step are in that file. Fee 0.001 ERG on each.

## Swap, pool and the second contract (added 2026-10-29)

The page gained a Swap tab on ErgoDEX v1 ERG-to-token pools (direct swap against the pool box, no order box, no
executor, no interface fee; quote, price impact and a slippage guard from the pool's own rule) and a Pool tab
(add and remove liquidity by the same rule). `test/amm.test.ts` and `test/liquidity.test.ts` run both against the
real pool ErgoTree on the mock chain, and `test/t2t.test.ts` the token-to-token pool (281 on mainnet under one
tree): swaps both ways, deposit and redeem, and four refusals by the pool scripts. `run-test.log` is from the first
build; the current suite is 17 cases. The Swap tab routes ERG-to-token through the deepest ERG pool and
token-to-token through a direct pool when one exists; the Pool tab offers ERG pairs and token pairs whose tokens are
both on the whitelist, with either side of a deposit typed and the other derived.

## Keyless upkeep (added 2026-10-29)

The page runs keyless jobs for a connected visitor (`src/upkeep.ts`; Babel bids and Machina orders priced across
their pool), submits through the explorer, bounty to the visitor, with an opt-out checkbox; the same runner is the
Node sidecar (`scripts/upkeep-run.ts`). Six mock-chain cases on the real EIP-31, Machina and pool scripts. On
mainnet the Babel job took a live gap with no signature (U1, mined at 1,904,969); the orders job was beaten to a
deliberately mispriced order by an existing bot one block after placement (`mainnet/README.md`).

## Escrow, bonds and the bank (added 2026-10-29)

Three venues on their deployed contracts: TokenJay's escrow (seller, named buyer, fee output returned to the
seller), SigmaFi bonds (request, fund, repay, liquidate after maturity; the contract's 0.5% developer fee shown) and
the SigmaUSD bank (mint and redeem through Fleet's AgeUSD plugin, no implementor fee; quoted beside the pool on the
Swap tab). Nine mock-chain cases and nine mainnet transactions (`mainnet/README.md`), including the bank's refusal
of SigUSD minting and SigRSV redemption at a 312% reserve ratio, which the page reports as "not allowed now".

## Review, 2026-10-30

Two independent reviews of the freedex repository (a no-context Claude, Gemini) agreed on two findings, both
real on inspection: a stored XSS (token names from the chain reached `innerHTML`; any stranger can mint a token
with a hostile name for a fraction of a cent, and the page's origin holds a granted EIP-12 context) and a slippage
guard that could not fire (the minimum was derived from the freshly read pool it was then checked against). Fixed in
freedex the same day: chain-sourced text only ever becomes a text node, a Content-Security-Policy allows no external
script, the swap's minimum is the one from the quote the user saw. Also applied: explorer failover with timeouts and
a 30-second listing cache, a runtime explorer choice, pinned template hashes, tests for units, sizing against brute
force and the keyless id (41 cases), a pull-request CI trigger. Deferred: one module per tab, UI tests.

## Not done

- The browser path (Nautilus signing from the deployed page) has not been exercised by a person yet; the mainnet
  transactions above went through the same builders from Node with the test wallet's signer.
- Deployed 2026-10-29 as its own repository, `cafebedouin/freedex` (MIT), Pages set to GitHub Actions. First run
  40825399595: build (npm ci, test, build) 11 s, deploy 28 s, both `success`; https://cafebedouin.github.io/freedex/
  answers HTTP 200 with the built page (`<title>FreeDEX for Ergo</title>`, script `./assets/index-CNbkrN7z.js`,
  the same bundle hash as the local build). One Actions job pair per push, well inside the budget in `CLAUDE.md`.

## Limits

- Prices are integers in nanoERG per smallest token unit (the contract's R5); the page refuses a price that is
  not such an integer rather than rounding.
- T2T orders are not supported (the SDK's T2T contract placeholder is `0000`); grid orders are not in scope.
- `takerAction` reads R6 as the SDK does: true means takers buy tokens from the box. The page labels orders by
  what the taker does and the create form by what the owner does.

## One module per tab, UI tests, lint, 2026-10-29 (synced from freedex `ccc645d`)

The two items the 2026-10-30 reviews deferred, and four small features. `src/main.ts` is 50 lines (the tab switcher
and the boot); the tabs are `src/ui/swap.ts`, `orders.ts`, `pool.ts`, `bank.ts`, `bonds.ts`, `escrow.ts`, with
`dom.ts` (text-node helpers), `store.ts` (wallet, explorer, tokens, pools, bank, the selected assets, `subscribe`),
`header.ts`, `wallet.ts` (connect, disconnect, `send`) and `upkeep.ts`. Every element id and all 34 handlers of the
old `main.ts` are referenced by the new modules (`comm` over the two id sets printed nothing missing, three new ids:
`bonds-mine`, `escrow-mine`, `explorer-status`); `grep -rn innerHTML src index.html | wc -l` prints `0`, and
`test/ui/page.test.ts` checks the same on every source file and on the rendered page (no `on*` attribute, no inline
script, the CSP present).

`npm test` (vitest 5.0.5, happy-dom 20.14.6 for `test/ui/`) prints:

```
 Test Files  24 passed (24)
      Tests  71 passed (71)
```

`test/ui/harness.ts` writes `index.html` into happy-dom, answers `fetch` from a world of mock-chain boxes in the
explorer's JSON shape (`test/ui/fixtures.ts`: pools, the bank, orders, a Babel box, loans and escrows, with the real
whitelist token ids), stubs an EIP-12 wallet on `ergoConnector`, and boots the real `src/main.ts`. The behaviours
covered by driving the inputs and reading the DOM: route resolution (ERG pool, direct pool, no ERG pool, no direct
pool), the quote rows with the bank beside the pool and the stale-quote refusal, deposits typed from either side on an
ERG pair and a token pair, the bank's "Allowed by the bank" line (yes at 666%, no when a mint would cross 400%),
order grouping and ordering with Babel rows among the sells, the positions sections on Bonds and Escrow, the header's
fallback line, and the upkeep timer asking the wallet once for a matured bond's collateral.

`npm run lint` (prettier 3.9.10 at print width 120, eslint 10.13.0 with typescript-eslint 8.72.1) prints `All
matched files use Prettier code style!` and no ESLint finding; it runs in `deploy/pages.yml` before `typecheck` and
`test`. JSON and `index.html` are in `.prettierignore`, so the contract bytes stay on one line.
`git diff -w --stat` over the builder files (`amm`, `bank`, `bonds`, `escrow`, `orders`, `machina-arb`, `wallet`)
shows line wraps only; `src/units.ts` has one `let` made `const` that ESLint asked for.

New, each with a test:
- EIP-31 Babel boxes on the Limit orders tab as orders takers sell into (marked "Babel"), from the same template
  hash as `src/babel.ts`; `buildFillBabel` recreates the box at output 0 with the tokens added and `tokens * bid`
  less ERG (`test/babel-fill.test.ts`: a fill, a chained second fill, the capacity refusals, one nanoERG more refused
  by the script).
- A matured SigmaFi bond whose lender is the connected visitor: `maturedBondsFor` in `src/upkeep.ts` finds it, the
  page's upkeep timer builds `buildLiquidate` from the visitor's boxes and asks the wallet to sign once per bond.
  The path is keyless on the contract's side: `test/upkeep-lender.test.ts` has a stranger's boxes pay the fee with
  nobody but the stranger signing, and the lender's balance rises by the whole 5 ERG collateral.
- "Your positions" at the top of Bonds and Escrow (the visitor's rows, with their actions), the market below
  without them; the Escrow market now lists without a wallet.
- A header line when the explorer fell back (`Explorer.onBaseChange`): "reading from api.ergo.aap.cornell.edu:
  api.ergoplatform.com did not answer", from `test/ui/header.test.ts` with the first base refusing.
- A footer link to the repository (the user's ask during the session).

Found on the way: happy-dom 20.14.6 has no `Option` constructor, so the page uses `option()` from `dom.ts`
(`document.createElement("option")`), the same DOM. Vitest 5.0.5's peer range for happy-dom is `^20.14.6`, which is
why 20.14.6 and not 21.
