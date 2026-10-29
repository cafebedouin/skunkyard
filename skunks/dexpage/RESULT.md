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

Nine transactions on 2026-10-29, all built by the page's code, signed and checked by the guarded signer, mined:
fill a stranger's order (A), place an order (B), partial fill of it (C), close it (D), a direct pool swap each way
(S1, S2), a liquidity deposit (L1) and its redemption (L2). Transaction ids and
the wallet's net per step are in that file. Fee 0.001 ERG on each.

## Swap, pool and the second contract (added 2026-10-29)

The page gained a Swap tab on ErgoDEX v1 ERG-to-token pools (direct swap against the pool box, no order box, no
executor, no interface fee; quote, price impact and a slippage guard from the pool's own rule) and a Pool tab
(add and remove liquidity by the same rule). `test/amm.test.ts` and `test/liquidity.test.ts` run both against the
real pool ErgoTree on the mock chain, 7 cases including three refusals by the pool script (one token too many on a
swap, one LP too many on a deposit, one nanoERG too many on a redemption). `run-test.log` is from the first build;
the current suite is 13 cases.

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
