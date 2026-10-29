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

## Not done

- No transaction has been signed or submitted. The mainnet wallet session (create, fill, close from the built
  page with Nautilus and pocket change) is the operator's; its transaction ids go here.
- Deployed 2026-10-29 as its own repository, `cafebedouin/freedex` (MIT), Pages set to GitHub Actions; the first
  workflow run is recorded below when it finishes.

## Limits

- Prices are integers in nanoERG per smallest token unit (the contract's R5); the page refuses a price that is
  not such an integer rather than rounding.
- T2T orders are not supported (the SDK's T2T contract placeholder is `0000`); grid orders are not in scope.
- `takerAction` reads R6 as the SDK does: true means takers buy tokens from the box. The page labels orders by
  what the taker does and the create form by what the owner does.
