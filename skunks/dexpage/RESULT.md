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

## Hardening, 2026-10-29 (synced from freedex `402e53a`, tagged `v0.1.0`)

The reviewer's second list, accepted as `prompts/freedex-hardening.md`, done in the order the brief gives except
that the module move (item 8) came first so every file written after it cites the final paths. No builder's
behaviour changed except one new refusal a property test found (below). Freedex pull request #1 carried the
work (`4a1e03c`, then `402e53a` for the one CodeQL alert below) so the browser job ran before the fast-forward to
`main`.

**Printed by the freedex checks before the commit** (`npm run lint` and `npm run typecheck` print nothing on
success; `npm audit --omit=dev`, `npm test`, `npm run build`):

```
All matched files use Prettier code style!
found 0 vulnerabilities
 Test Files  38 passed (38)
      Tests  206 passed (206)
   Duration  13.89s (tests 64%, import 29%, environment 5%, transform 2%)
dist/index.html                                21.60 kB │ gzip:   6.37 kB
dist/assets/ergo_lib_wasm_bg-vDt_QTSr.wasm  2,766.71 kB │ gzip: 977.86 kB
dist/assets/ergo_lib_wasm-ZQFDxfON.js         125.34 kB │ gzip:  19.57 kB │ map: 457.47 kB
dist/assets/index-4s0FbZ44.js                 231.99 kB │ gzip:  74.08 kB │ map: 810.45 kB
✓ built in 348ms
```

160 tests in 31 files before the session (`run-test.log` of the phone session); the 46 added are the 20 property
cases, 4 explorer retry cases, 14 registry cases replacing the 9 hash cases, 3 explorer-down cases and 2 axe
cases, plus one Long-guard case inside the pool properties.

**Invariants** (item 1): `docs/invariants/` holds nine files (pools 11.6 kB, orders 9.8, bank 5.8, bonds 10.3,
escrow 5.9, clock 14.7, option 11.6, upkeep 11.4, signing 10.0), linked from the README. Three forks of the session
wrote them from the code and the fetched sources (`spectrum-finance/ergo-dex` `8fe94e1`, EIP-31 at `81edece`,
`Emurgo/age-usd` `e810b19`, the TokenJay script from tokenjay.app, the SigmaFi port at `309c1ac`); SigmaFi's
ErgoScript is not published anywhere the forks could find, so `bonds.md` marks every contract line [UNVERIFIED]
and cites the deployed tree's segregated constants instead (`Long 500`, `Long 100000`, `Long 400`, the dev
`SigmaProp`, the bond-tree blake2b). Findings the files record against the code's own comments: `machina-arb.ts`
says the SDK checks the 0.0001 ERG remainder, but the SDK checks only that the payout fits the order's ERG (the box
minimum is Fleet's build-time check); `option.test.ts`'s header says the builders refuse one block earlier than the
script, but at the mock chain's `HEIGHT = h + 1` the guards coincide with `open = HEIGHT <= expiry` exactly; the
clock builder is one block more conservative than `Clock.es`'s `due` (the existing case "refused at HEIGHT H+N and
accepted at H+N+1" shows it); the Limit orders tab's default fill amount (`floor(value / price)`) can be refused by
the SDK on a nearly empty order. None changed code.

**Property tests** (item 2), `test/properties/`, fast-check 4.10.2 pinned, one seed for every suite printed with its
run count (`run-properties.log`, `npx vitest run test/properties --silent=false`):

```
property pools: quote bound N2T: 2000 runs, seed 20261029
property pools: quote bound T2T: 2000 runs, seed 20261029
property pools: Long overflow guard: 200 runs, seed 20261029
property pools: swap executes N2T: 40 runs, seed 20261029
property pools: swap executes T2T: 40 runs, seed 20261029
property pools: deposit quotes agree N2T: 2000 runs, seed 20261029
property pools: deposit quotes agree T2T: 2000 runs, seed 20261029
property pools: deposit executes from either side: 30 runs, seed 20261029
property units: round trip: 2000 runs, seed 20261029
property units: non-canonical accepted forms normalise: 1500 runs, seed 20261029
property units: refused strings: 2000 runs, seed 20261029
property units: too many decimals refused: 1000 runs, seed 20261029
property units: price round trip: 2000 runs, seed 20261029
property sizing: Babel equals brute force: 300 runs, seed 20261029
property sizing: Machina into-order equals brute force: 300 runs, seed 20261029
property sizing: Machina from-order equals brute force: 300 runs, seed 20261029
property clock: buy leg at the due height: 25 runs, seed 20261029
property clock: sell leg at the due height: 25 runs, seed 20261029
property option: call exercise and reclaim at the expiry: 12 runs, seed 20261029
property option: put exercise and reclaim at the expiry: 12 runs, seed 20261029
      Tests  20 passed (20)
   Duration  3.10s (tests 73%, import 26%, transform 1%)
```

`FC_SEED=7` reruns every suite under another seed (checked: `property units: round trip: 2000 runs, seed 7`).
Two of the brief's properties were narrowed to what the code does, recorded rather than changed: (a) "the
ERG-first and tokens-first deposit quotes agree" holds to within one rounding step, not exactly (`tokenIn = ceil(e
* y / x)` then `e' = ceil(tokenIn * x / y)` gives `e <= e' <= e + ceil(x / y)` and a never-smaller LP out; the
example in `liquidity.test.ts` happens to divide evenly), so the property asserts those bounds and that a deposit
built from either side executes on the mock chain; (b) "`parseUnits` refuses every non-canonical string" is
narrower than `units.ts`, which accepts leading and trailing zeros, a bare trailing dot and surrounding whitespace
by design (`test/units.test.ts` "parses decimals exactly"), so the property refuses the grammar's outside (a sign,
an exponent, a letter, a second dot, a comma, no digit, too many fraction digits) and checks the accepted forms
normalise to the canonical string.

**The one bug found, fixed in the smallest way.** The first run of the swap oracle, drawing reserves up to 2^62 as
the brief asked, printed from sigmastate-js:

```
Caused by: java.lang.ArithmeticException: long overflow
 ❯ $c_Ljava7_compat_Math$.multiplyExact__J__J__J node_modules/sigmastate-js/dist/main.js:9278:13
```

`Pool.sc`'s `validSwap` reads `reservesY0.toBigInt * deltaReservesX * feeNum0 >= -deltaReservesY *
(reservesX0.toBigInt * FeeDenom + deltaReservesX * feeNum0)`: the term `deltaReservesX * feeNum0` is a Long times
an Int (a Long in the T2T script) before any widening, so a swap input above `(2^63 - 1) / feeNum` (about 9.2
million ERG, or 9.2e15 token units) makes the deployed script throw and the node reject the transaction, with no
refusal from the page. The quote itself is exact at any size (the pure bound property passes over the full 2^62
range). `buildSwap` and `buildSwapT2T` now throw `the amount times the pool's fee numerator does not fit a Long:
the pool script cannot evaluate it` first (one `if` each, `src/protocols/ergodex/amm.ts`), the oracle draws inputs
within what the script can multiply, and a 200-run property checks the refusal. Recorded in `pools.md` and the
changelog.

**The registry** (item 3). `src/registry.json`, 18 entries, generated once from the modules' pinned literals and the
live bank and oracle trees (722 and 413 bytes, read from the explorer) and then hand-maintained; every module reads
its trees and hashes through `src/registry.ts`, `sigmafi-contracts.json` is gone (its extraction script now prints
the registry's shape), `test/hashes.test.ts` checks every entry's hash against its template (templates filled with
three different byte values), the SDK-built Machina order against its sample, and recompiles the four contracts in
`contracts/`. `scripts/registry-check.ts` (`run-registry-check.log`):

```
registry: 18 entries; explorer https://api.ergoplatform.com; height 1905489
ergodex-n2t-pool               2dcc7830afe8… live: box 47343e98a48ae775… at height 874866
ergodex-t2t-pool               3c09deff3b5f… live: box 2cb83d72b08e41ff… at height 858185
eip31-babel                    4e83fa68ef3e… live: box fc3aa86922611be2… at height 873592
machina-e2t-limit-order        03ef002b73a8… live: box d5ae5eac6245dc62… at height 1903246
sigmafi-order-on-close-erg     525298e97a92… live: box 1c3dd9d14bcfb37b… at height 943490; 1 of 20 listed carry other constants
sigmafi-order-on-close-token   05208404b335… live: box 988a9640e29e0cb0… at height 930342
sigmafi-order-fixed-erg        8af6777c9b70… none, ever
sigmafi-order-fixed-token      6f38fd7514e8… none, ever
sigmafi-bond-erg               44830db1e02b… live: box 5335fa98ee05818e… at height 922218
sigmafi-bond-token             edacb0e6bc89… live: box e1b6409a8735634b… at height 972857
sigmafi-dev-fee-recipient      55e36dd33c1a… live: recipient 9hgm8enrcP… db5fbe65cf5368ca
tokenjay-escrow                b2c3338d244f… spent: box 0916dac4c53c37bb… settled at height 761208, 47 all time
sigmausd-bank                  246e14059ac2… live: box d0d74b7f2176e1a2… at height 1905194
sigmausd-oracle                19e4db356244… live: box 10892ac65357d5db… at height 1905486
clock-buy                      a1df056602fa… spent: box 9d54c61fd815006f… settled at height 1905031, 6 all time
clock-sell                     7bf4e2d6ba91… spent: box 600da595cb83a46d… settled at height 1905121, 3 all time
option-call                    da26dcb30f5b… spent: box 5a1e895eeee14821… settled at height 1905148, 3 all time
option-put                     1296e3affd09… spent: box 2273d3dae3906fab… settled at height 1905149, 3 all time
16 of 18 entries have a mainnet box (unspent, or spent where none is open) with the pinned bytes
```

The brief's "a live box for each entry" cannot be met for the six contracts whose boxes are all spent today
(this project's four, every one closed on mainnet in the earlier sessions; TokenJay's 47 escrows, all taken) without
submitting a mainnet transaction, which the brief forbids, so the script falls back to the explorer's all-time
listing (`/api/v1/boxes/byErgoTreeTemplateHash/<hash>`) and names the newest spent box with the pinned bytes.
SigmaFi's two fixed-term order contracts have never had a box on mainnet (listed for completeness, `liveBoxCheckedOn:
null`). The first run, with `limit=1`, returned for the SigmaFi ERG order a box (`dd0b2f9f…`, height 907669) whose
tree differs from the pinned one in the 32-byte constant after `0e20` at hex offset 108, the bond-tree blake2b:
another deployment of the same script with another bond contract, under the same template hash. The page's
`describeOrder` refuses it by its exact-tree check, so it never reaches the Bonds tab; 19 of the 20 unspent boxes
under the hash carry the pinned bytes.

**Scanning and the budget** (item 4). `npm audit --omit=dev` is a step of the existing build job (0 vulnerabilities;
the full audit reports 2 low in the test harness, `diff` under `@fleet-sdk/mock-chain`, and the `happy-dom` high
was closed by moving to 21.0.4, all 206 tests passing on it). `.github/workflows/codeql.yml`: weekly (Monday 06:23
UTC) and on pull requests to `main`, never on a push. `.github/dependabot.yml`: npm, monthly, one grouped pull
request, limit 1. Actions runs a month added, with no human pull request: about 4.3 CodeQL runs from the schedule
plus, for Dependabot's one pull request, one pages run (two jobs: the build and the browser) and one CodeQL run,
so about 6.3 runs a month, roughly 25 runner-minutes; each human pull request adds one CodeQL run and the browser
job inside the pages run it already triggered; nothing new runs on a push. This session cost five runs: two
pushes to the pull request (each a pages run of two jobs, build and browser, and a CodeQL run) and the
fast-forward push's pages run. CodeQL's `init` warns that without an `on.push` hook the Security tab shows no
alerts for the default branch; that is the budget's choice (pull requests and the weekly schedule only) and the
schedule's runs analyse `main`.
`SECURITY.md` names GitHub's private vulnerability reporting as the channel and states what the page holds; no
address was invented. Two repository settings could not be changed from this session (the harness refused the
calls as account changes): turning private vulnerability reporting on (`gh api -X PUT
repos/cafebedouin/freedex/private-vulnerability-reporting`) and branch protection on `main` (the `build` check
required, force pushes and deletion off); both are the person's to run, and SECURITY.md's link only works once the
first is on.

**The browser test** (item 5). `test/browser/phone.spec.ts`, Playwright 1.64.1 pinned, Chromium only, the built
`dist/` served by `vite preview`, gated to `pull_request` in `pages.yml` with the browser download cached by
Playwright's version. It asserts the CSP meta, unticks the upkeep (so nothing is submitted), chooses "sign with your
phone" with the test wallet's address (read-only), picks RSN as the target (0.001 ERG into SigUSD quotes 0 units:
two decimals), builds a 0.001 ERG swap and sees the QR panel render with a 64-hex id, an `ergopay:` link within
2,800 characters, a square canvas titled with its module count, and the focus on the panel. Locally (Chrome Headless
Shell 156.0.8078.4):

```
  ✓  1 [chromium] › test/browser/phone.spec.ts:11:1 › the CSP is set, the WASM path reduces a swap, and the QR panel shows a link within the limit (13.9s)
  1 passed (15.4s)
```

The explorer's first poll for the unsigned id answers 404 by design; the browser logs every failed resource load,
so that one is excluded from the test's "no console error" assertion.

**Explorer resilience** (item 6). `src/explorer.ts` retries a failed try (a network error, a timeout, a 5xx, a 429)
on the same backend after 1 s, 2 s and 4 s (`RETRY_DELAYS_MS`, so four tries a backend) before the next backend;
a 404 is an answer, not a failure. `onStatus` reports each failed try, the final failure and the first success
after one; the store carries it, the header line shows "explorer unavailable (host, try n failed), retrying…" on
every tab, each listing shows the same while loading and "explorer unavailable (reason) [retry]" after a failure,
the Swap route and the Pool tab say it in place of "no pool", the pool listing is re-asked every 30 s until it
loads. Four Node cases (`test/explorer.test.ts`) and three page cases (`test/ui/explorer-down.test.ts`, the harness
zeroing the waits). Worst case with both backends hanging: eight tries of 15 s plus 14 s of waits before the
error, against 30 s before; the brief asked for the retries inside the failover loop and the record notes the cost.
No telemetry; the page still phones nobody but the backends.

**Accessibility** (item 7). Every input labelled (`aria-label` on the Swap and Pool amount fields and selects, the
unit spans turned into `<label for>`), the tabs wired with `aria-controls` to `role="tabpanel"` sections inside a
`<main>`, the log and the status lines `role="status" aria-live="polite"`, the QR panel `tabindex="-1"` focused on
open and the focus returned on close, the actions column of every table named "actions" for screen readers only,
and a sentence in words before every wallet prompt (`send(store, build, what)`, 24 call sites: "Swap 1 ERG for 19.8
SigUSD (at least 19.6 after slippage), miner fee 0.001 ERG. Your wallet will ask you to confirm."). axe-core 4.14.0
runs in happy-dom over all eight tabs without a wallet, with one, and with the QR panel open (colour contrast off:
happy-dom lays nothing out); the first run reported `landmark-one-main` and `region` (fixed with `<main>`), the
second `empty-table-header` (fixed with the hidden "actions" head), the third nothing.

**Housekeeping** (item 8). `src/protocols/{ergodex,machina,babel,sigmausd,sigmafi,tokenjay,clock,option}/` with the
tests beside the modules, a pure move with imports rewritten by a script (`git mv`, 21 files; 160 tests green
before any other change). `CHANGELOG.md` from the first push. The README's compatibility section lists only what has
run: Nautilus and SAFEW by EIP-12 (stubbed connector in the tests; the mainnet transactions went through the
project's guarded signer), the mobile wallet and Terminus by static ErgoPay (the wallet's source; the scan is still
the person's row), Satergo untested, the two explorer backends, the mock chain's `sigmastate-js` as the node
interpreter, and Chromium 156 as the one browser the WASM path has run in. One run of `vite-bundle-visualizer` 1.2.1
(`-t raw-data`): two chunks, the main one 355 kB unminified (224.65 kB minified before the session's UI additions,
231.99 kB after; gzip 74.08 kB) and the lazy `ergo_lib_wasm` chunk 207 kB plus the 2.77 MB `.wasm` fetched only on
the phone path; the largest modules in the main chunk are `qrcode-generator` 42.7 kB, Fleet core 41.9 kB, the
serializer 29.8 kB and `src/registry.json` 26.9 kB (the trees and the prose; about 3 kB gzipped over the old SigmaFi
JSON). Conclusion: no second heavy chunk; nothing to split.

**On the pull request** (`gh pr checks 1`, run 40989252462 for `4a1e03c`): `build pass 42s`, `browser pass 43s`
(Chromium downloaded, no cache yet), the CodeQL `analyze` job `pass 58s`, and the CodeQL check `fail 6s` with "1
new alert including 1 high severity security vulnerability": `js/incomplete-url-substring-sanitization` at
`test/explorer.test.ts:45`, the retry test's fake fetch routing by `url.startsWith("https://a.example")`. A test
double, not page code, but the check gates the pull request, so `402e53a` routes by `new URL(url).origin` instead
(an amend was not available to the session; the second commit is the fix). The second run (`gh pr checks 1`,
runs 40989600448 and 40989600434 for `402e53a`): `build pass 1m2s`, `browser pass 44s`, `analyze pass 1m11s`,
`CodeQL pass 2s`, zero open alerts on the pull request. Merged by a fast-forward of `main` to `402e53a` at
02:06:53 UTC on 2026-10-30, tag `v0.1.0` pushed with it; the push's Pages run 40989781132 (`build success`,
`browser skipped`, `deploy success`) and the live page answered 200 with `assets/index-4s0FbZ44.js`, the local
build's hash, and seven `role="status"` lines (`curl`, 02:08 UTC).

**Limits of this session.** The browser job's pass on the pull request is recorded above and below;
the invariants files cite code lines that will drift with the next edit (the UI and explorer cites were reduced to
file names for that reason, the `amm.ts` cites shifted by the guard's lines); the registry's `liveBoxCheckedOn`
dates are set by hand from the check script, not by it; the brief's "three attempts, 1 s, 2 s, 4 s" was read as
three retries after the first try.
