# dexpage

A static page for Machina Finance ERG-to-token limit orders on Ergo mainnet. It lists open orders from a public
explorer, builds transactions in the browser with Fleet and `@nautls/machinafi-sdk`, and hands them to an EIP-12
wallet (Nautilus, SAFEW) to sign and submit. No server, no keys in the page. Charter: `CHARTER.md`.

## Run it

```
npm ci
npm test          # the builders against the real contract on Fleet's mock chain
npm run dev       # http://localhost:5173 with Nautilus installed in the browser
npm run build     # dist/, static files for any host
```

Set `VITE_EXPLORER` to use another explorer (`VITE_EXPLORER=https://api.ergo.aap.cornell.edu npm run build`).

## Self-host on GitHub Pages

1. Put this directory at the root of a repository of your own.
2. Copy `deploy/pages.yml` to `.github/workflows/pages.yml`.
3. In the repository settings, set Pages to "GitHub Actions".
4. Push to `main`. One workflow run builds `dist/` and publishes it.

## Layout

- `src/orders.ts`: the three builders (`buildCreate`, `buildFill`, `buildClose`) and `describe` for display. Pure.
- `src/explorer.ts`: height, token metadata, open orders by ErgoTree template hash.
- `src/wallet.ts`: EIP-12 connect, UTXOs, sign and submit.
- `src/main.ts`, `index.html`: the page.
- `test/orders.test.ts`: mock-chain tests.
- `scripts/template-hash.mjs`: how the template hash in `explorer.ts` was computed.

## Units

The contract's price is nanoERG per smallest token unit, an integer. The page shows and takes ERG per whole token
and converts with the token's decimals from the explorer; a price that is not a whole number of nanoERG per
smallest unit is refused rather than rounded.
