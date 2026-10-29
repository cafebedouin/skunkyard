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
- The phone path (ErgoPay static mode, built 2026-10-29, section below) has not been scanned by a person yet: the
  reduction and the page are checked in Node and happy-dom; the camera, the wallet's signing screen and the WASM
  load in a real browser are the person's rows in that section's table.
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

## The tranche sale, two clocked-box fixes, the Bonds tab reordered, 2026-10-29 (synced from freedex `18e7575`)

The clocked box's second session is recorded in `skunks/clockbox/RESULT.md` (second session) and
`skunks/clockbox/mainnet/README.md`; this copy carries the same `contracts/ClockSell.es`, `src/clock.ts`,
`src/upkeep.ts`, `src/ui/programs.ts` and `test/clock.test.ts`, with `scripts/mainnet-run.ts` gaining
`clock-create-sell`. The Bonds tab now leads with the request form, then the visitor's positions, then the market
collapsed in the Limit orders style with counts on the summary lines (`test/ui/positions.test.ts`). Printed by the
freedex checks before the commit:

```
All matched files use Prettier code style!
 Test Files  26 passed (26)
      Tests  107 passed (107)
✓ built in 482ms
```

The clock cases' lines are in `run-test-clock.log`:

```
buy program box: 666 bytes, locked 34500000 nanoERG, rent reserve 0 (one rent fee would be 832500000); tree 504 bytes
sell program box: 716 bytes, rent reserve 895000000 nanoERG, minimum 257760, locked 899757760; tree 517 bytes
cost of one buy leg: clock script 332, pool script 186; tree 504 bytes
cost of one sell leg: clock script 340, pool script 186; tree 517 bytes
```

## Signing from the phone: ErgoPay static mode, 2026-10-29 (synced from freedex `e595a95`)

The second signing path. A `Signer` (`src/wallet.ts`: kind, address, `height`, `utxos`, `balance`, `sign`) over the
EIP-12 wallet as before and over the phone (`src/ergopay.ts`): the visitor types a mainnet address once ("sign with
your phone" in the header; the address is kept in `localStorage` under `freedex.phone`), boxes and balances come
from the explorer by address, and `sign` reduces the EIP-12 transaction with sigma-rust's `ergo-lib-wasm-browser`
0.28.0 (fetched only on this path, through `vite-plugin-wasm` 3.6.0) against the explorer's last ten headers, shows
the reduced bytes as a QR code (`qrcode-generator` 2.0.4 on a canvas, error correction L, white background) and as
an `ergopay:` link (EIP-20 option 2, URL-safe base64, padded), then polls the explorer every ten seconds for up to
twenty minutes for the id, which is the same before and after signing. No server, no relay. Every tab and the two
signed upkeep jobs go through the same `send()`. The CSP's `script-src` gains `'wasm-unsafe-eval'` and
`connect-src` gains `'self'` (the WASM is fetched from the page's own origin). The tabs wrap on a narrow screen.

**Check 1, the reduced length, settled in Node against mainnet state.** `scripts/reduce.ts` builds a 0.005 ERG pool
swap from the test wallet's boxes exactly as the Swap tab does and reduces it. Printed (`run-reduce.log`):

```
explorer: reading from https://api.ergo.aap.cornell.edu
explorer: reading from https://api.ergoplatform.com
height 1905196; 10 headers from https://api.ergoplatform.com, 1905196 down to 1905187
9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc: 36 boxes, 20.937793339 ERG
pool RSN (cadac6db…), 240345.795702362 ERG deep; 0.005 ERG pays 118
unsigned: 2 inputs, 0 data inputs, 4 outputs; EIP-12 JSON 3981 bytes
reduced: 891 bytes in 26 ms; id 28f55832673dc9ffcffe11ee7f6efa56979e138122dc87efe3d644b23f3dcb13
ergopay link: 1196 characters (limit 2800); fits a QR code
parses back: same id
```

The explorer's header JSON (`/api/v1/blocks/headers?limit=10`, newest first, fields id, parentId, version,
timestamp, height, nBits, votes, stateRoot, adProofsRoot, transactionsRoot, extensionHash, powSolutions) parses
through `BlockHeaders.from_json` as is; the 0.28.0 `ErgoStateContext` constructor takes a third argument, the chain
`Parameters` (`Parameters.default_parameters()` here), which the brief's two-argument form did not have. The
"2 inputs" are the pool box and one of the wallet's; the earlier measurement in the brief (893 bytes for a swap) was
for the same shape. A 1,196-character link is a version-25 QR code (117×117 modules); 2,800 characters would be
version 39 (173×173), printed by `qrcode-generator` for strings of those lengths. The explorer's own timing matters
on this path: on 2026-10-29 `api.ergoplatform.com` answered the headers request in 50.2 s once and 0.3 s another
time, while `api.ergo.aap.cornell.edu` answered in 0.3 s; the page's 15 s timeout fails over, as the run's first
two lines show. `/api/v1/mempool/transactions/byAddress/<p2pk>` answers `{"items":[],"total":0}` in 0.3 s and is
the only mempool lookup the explorer offers, so the wait asks it with the phone's address beside
`/api/v1/transactions/<id>`.

**Check 2, the wallet taking a static code, settled in the wallet's source (not yet on a phone).**
`ergoplatform/ergo-wallet-app` (develop, pushed 2026-09-14; latest release v2.4.2313 of 2026-05-25; Apache-2.0),
`common-jvm/src/main/java/org/ergoplatform/transactions/ErgoPay.kt` (last commit afa99d6ee4, 2023-05-21):

```
fun isErgoPayStaticRequest(requestData: String) =
    isErgoPaySigningRequest(requestData) && !isErgoPayDynamicRequest(requestData)
fun isErgoPayDynamicRequest(requestData: String) =
    requestData.startsWith("$uriSchemePrefix//", true)
private fun parseErgoPaySigningRequestFromUri(uri: String): ErgoPaySigningRequest {
    val uriWithoutPrefix = uri.substring(uriSchemePrefix.length)
    val reducedTx = Base64Coder.decode(uriWithoutPrefix, true)
    return ErgoPaySigningRequest(reducedTx)
}
object ErgoPay {
    fun buildStaticSigningRequest(reducedTx: ByteArray) =
        uriSchemePrefix + String(Base64Coder.encode(reducedTx, Base64Coder.urlsafeMap))
```

and `uilogic/MainAppUiLogic.kt`, `handleRequests`: `else if (isErgoPaySigningRequest(data)) { navigateToErgoPay(data) }`
before the cold-signing chunk branches, which are the only multi-part QR path. So a scanned `ergopay:<base64>` of
any length the camera decodes goes straight to the signing screen, and the page's encoder (URL-safe alphabet,
padded with `=`) matches the wallet's own. Terminus is the iOS target of the same code (`ios/` in the repository).
What the source cannot say: whether the phone's camera reads a 117-module code from a laptop screen, and what the
signing screen shows for a pool swap; those are the person's rows below.

**Check 3, Satergo:** untouched; a row below.

**ErgoDEX for comparison** (`spectrum-finance/interface`, CC0): its ErgoPay wallet entry stores the address in
`localStorage` (`ergopay-wallet`) and reads boxes with `searchUnspentBoxesByAddress`, the same client shape as
here, but `submitErgopayTx` posts the unsigned transaction to `ergopayUrl/unsignedTx` and the code shown is the
dynamic `ergopay://…/unsignedTx/<id>` link; the reduction is on its backend. `spectrum-finance/ergo-dex` holds the
contracts only. Nothing was cribbed for the reduction; the white-background QR is the one detail taken.

**Tests.** `test/ergopay.test.ts` (Node): the link encoding (`-_8=` for `fb ff`), the guard at 2,800 (a
2,094-byte reduction is 2,800 characters and fits; 2,100 bytes is 2,808 and is refused), the address check
(testnet and garbage refused), a real reduction through `ergo-lib-wasm-nodejs` 0.28.0 of a mock-chain transaction
against the ten mainnet headers kept in `test/fixtures/headers.json` (id equal to Fleet's, parses back, the same
transaction valid on the chain), and the signer's loop against a hand-made explorer (polls until seen, then leaves
those inputs out; times out; cancels; refuses the oversize code before showing it). `test/ui/phone.test.ts`
(happy-dom, the binding stubbed by `test/fake-ergolib.ts`): the address asked once and kept, a non-mainnet address
refused, a swap showing the code and link and resolving when the explorer lists the id, cancel, the upkeep's
matured-bond hand-over through the phone, the oversize refusal. Printed by the freedex checks before the commit
(`run-checks.log` in the session; lint and typecheck print nothing on success):

```
All matched files use Prettier code style!
 Test Files  31 passed (31)
      Tests  160 passed (160)
dist/index.html                                19.87 kB │ gzip:   5.99 kB
dist/assets/ergo_lib_wasm_bg-vDt_QTSr.wasm  2,766.71 kB │ gzip: 977.86 kB
dist/assets/ergo_lib_wasm-ZQFDxfON.js         125.34 kB │ gzip:  19.57 kB │ map: 457.47 kB
dist/assets/index-DMhgWUlV.js                 214.84 kB │ gzip:  68.69 kB │ map: 787.14 kB
✓ built in 377ms
```

The main bundle reaches the binding only through a lazy import, so a Nautilus visitor never fetches the 2.77 MB;
from `dist/assets/index-DMhgWUlV.js`:

```
var Mo=()=>jo(()=>import(`./ergo_lib_wasm-ZQFDxfON.js`),[],import.meta
```

**Deployed.** Pages run 40905540178 for `e595a95`: build `success` 15:50:09 to 15:50:37 UTC, deploy `success`
15:50:41 to 15:51:12 (`gh run view`). The live page then answered 200 with `assets/index-DMhgWUlV.js` (the local
build's hash), `script-src 'self' 'wasm-unsafe-eval';` in its CSP and the `id="ergopay"` panel, and
`assets/ergo_lib_wasm_bg-vDt_QTSr.wasm` answered 200 with `content-type: application/wasm`, `content-length:
2766716`, which is the type streaming instantiation requires (`curl -I`).

**The person's check** (nothing here was scanned; no browser on the build machine). On the live page
https://cafebedouin.github.io/freedex/:

1. On the desktop, open the page, choose "sign with your phone", paste the test wallet's address
   `9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc` into the prompt. The header should read
   `phone: 9gnBiuBA…TNcfc`, and the Swap tab's balance line should show the explorer's figure (20.94 ERG on
   2026-10-29). Untick "Chain upkeep" first if you do not want the upkeep's own prompts.
2. Swap tab: 0.005 ERG to the default token, "Build, sign in wallet, submit". The log should say `reduced to N
   bytes, a M-character link` and the "Sign on your phone" panel should show the code. Note N and M.
3. Scan with the Ergo mobile wallet (Android) or Terminus (iOS). Note whether the signing screen opens, what it
   shows (inputs, outputs, fee), and sign. The page's log should then say `submitted <id>` within a poll (ten
   seconds). Note the id and whether the explorer shows it.
4. On the phone itself, open the page in the phone's browser, repeat step 2, and tap the "open in an ErgoPay
   wallet" link. Note whether the wallet opens with the transaction.
5. If a Satergo desktop wallet is at hand, click the link there (or paste it). Note whether Satergo opens it.

| row | what | evidence to paste |
| --- | --- | --- |
| 1 | address accepted, balance from the explorer | header text, balance line |
| 2 | code shown for a 0.005 ERG swap | the log's `reduced to … bytes, a … link` line |
| 3 | Ergo mobile wallet or Terminus scans, shows, signs | wallet screen summary; the page's `submitted <id>`; explorer link |
| 4 | the link opens the wallet on the phone | yes/no, wallet version |
| 5 | Satergo opens the link | yes/no, Satergo version |

**Limits.** The reduction's context is the newest header as pre-header (height H) while the node validates at H+1,
the same as Nautilus; a script that turns on exactly at H+1 reduces differently from how it is checked. The chain
`Parameters` passed are the genesis defaults, not the live ones. The explorer's unspent-by-address listing may still
include a box a phone-signed transaction spent until it is mined, so the signer leaves the inputs it used out of the
next build for fifteen minutes; a box spent by another wallet meanwhile is not known to the page until the explorer
drops it. The WASM instantiation under the page's CSP in a real browser is not exercised by any test here (happy-dom
has no WebAssembly streaming); row 2 covers it.
