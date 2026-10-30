# freedex inside the Ergo mobile wallet: a keyless sidecar that speaks Mosaik, Swap first, self-hosted on your own network

You are adding the third tier of FreeDEX, in `/home/scott/bin/freedex` (CC0, live at
https://cafebedouin.github.io/freedex/, one Pages run per push to `main`, tagged `v0.1.0`) with its record in
`/home/scott/bin/skunkyard/skunks/dexpage/`. Read first: `/home/scott/bin/skunkyard/CLAUDE.md` and `PROGRAM.md`
(every number names its printed output, nothing outward without the person's go, the GitHub Actions budget), then
`research/agents/ROADMAP.md` R5 (the three tiers; this session is tier 3, and it is the same process tier 2 would
run) and the last two sections of `skunks/dexpage/RESULT.md`. Then in freedex: `src/wallet.ts` and `src/ergopay.ts`
(`reduceTransaction`, `ergopayLink`, `sizeGuard`, `HEADERS_NEEDED`), `scripts/reduce.ts` (the reduction already
running in Node with `ergo-lib-wasm-nodejs`), `scripts/upkeep-run.ts` (the one process freedex already ships, and
the model for this one), `src/explorer.ts`, `src/protocols/ergodex/amm.ts` with `src/ui/swap.ts` (the form you are
translating), `docs/invariants/pools.md` and `signing.md`, and `src/registry.json`.

This is the first freedex component that runs as a process. It holds no keys, keeps no state beyond one request,
charges nothing, and serves what the static page serves, nothing more. Say that in its README in those words.

## What is settled (sources read 2026-10-29; re-read the two marked "verify" before building)

- The mobile wallet adds a dApp by URL. A `mosaikapp://host[:port]/path` URL is fetched over plain http when the
  host is `localhost` or an IPv4 literal and over https otherwise (`ergo-wallet-app`
  `common-jvm/.../mosaik/MosaikAppUri.kt`, `utils/HttpUtils.kt` `isLocalOrIpAddress`). A URL typed without a
  scheme gets `https://`. So a server on the person's own machine, reached by LAN address, needs no domain and no
  TLS. Whether the iOS build (Terminus) allows plain http to a LAN address is unverified; the Android build does.
- The wallet's Mosaik runtime (`common-jvm/.../mosaik/AppMosaikRuntime.kt`) sends a `MosaikContext` as request
  headers on every call: mosaik version 2, a per-host guid, language, wallet app name and version, platform
  (`DESKTOP`, `TABLET`, `PHONE`), time zone offset. The header names are in the Mosaik serializer
  (`MrStahlfelge/mosaik`, `serialization-gson`, `contextHeadersMap`); read them there (verify). The library was last
  pushed 2022-12-07, Apache-2.0; the wallet's runtime using it was pushed 2026-09 (the previous session's read),
  so the format is old and alive.
- The first request is a GET of the app URL; the answer is a `MosaikApp`: a `manifest` (`appName`, `appVersion`,
  `targetMosaikVersion`, `targetCanvasDimension`, `cacheLifetime`, optional `appDescription`, `iconUrl`,
  `onAppLoadedAction`, `errorReportUrl`, `notificationCheckUrl`) plus the root `view` and the `actions` map. If the
  answer is HTML, the runtime follows a `<link rel="mosaik" href="...">` in it (`OkHttpBackendConnector.kt`
  `checkForMosaikRelTag`), which is how a page can point a wallet at its server.
- Input comes back through a `BackendRequestAction`: a POST to its `url` (relative to the app URL) whose body is a
  JSON map of every input element's id to its value; the answer is a `FetchActionResponse` `{appVersion, action}`
  where the action is a `ChangeSiteAction` (a new view), a `DialogAction`, an `ErgoPayAction`, or the others listed
  in `common-model/.../actions/`. Inputs available: `ErgoAddressChooseButton` (the wallet fills in the user's chosen
  address, so no pasting), `ErgAmountInputField`, `DecimalInputField`, `IntegerInputField`, `DropDownList`,
  `CheckboxLabel`, `TextInputField`. Output: `Label`, `ErgAmountLabel`, `TokenLabel`, `Markdown`, `QrCode`,
  `LoadingIndicator`, `LazyLoadBox`, in `Column`, `Row`, `Box`, `Card`, `Grid`. One JSON schema per element in
  `serialization-gson/src/test/resources/schema/`.
- Signing is `ErgoPayAction {type, id, url, onFinished}`. The Android wallet accepts it only if
  `isErgoPaySigningRequest(url)` (`android/.../mosaik/MosaikViewModel.kt` line 83) and then opens its ErgoPay
  signing screen; the previous session read that parser and found the static form `ergopay:<base64url>` accepted
  at any scannable length (verify against `common-jvm/.../transactions/ErgoPay.kt` and cite the line). So the
  server answers the swap request with the same string the page puts in a QR code, and the wallet signs and
  submits. `onFinished` names an action to run when the user comes back.
- The reduction costs about 26 ms in Node (measured on 2026-10-29 by the previous session), above Cloudflare's
  free 10 ms, so a public instance is a VPS, not a free worker. The main explorer stalled for 50 s once in a
  previous session; the server uses the page's `Explorer` class with its retries and Cornell failover unchanged.

## Do, in this order

1. **Verify the two marked points and the executor you will test with.** Read the serializer's header names and
   the wallet's ErgoPay request check; print the lines. Then find something that renders Mosaik on this machine:
   the wallet app's desktop build if a release exists (`ergoplatform/ergo-wallet-app` releases; it has the same
   runtime as the phone), else the library's `desktop-demo` (`gradlew desktop-demo:run`, needs a JDK;
   `JAVA_HOME` for 17 is on this machine for sbt). Say which one you got running. If neither runs, the session
   continues with curl and schema validation and the person's phone is the first real executor; say so.
2. **The server**, in `server/` of freedex: Node's own `node:http`, no framework, TypeScript run by Node's type
   stripping the way `scripts/` already is, one entry `server/index.ts`, `npm run mosaik -- [--host 0.0.0.0]
   [--port 8080]`. It imports the page's builders, `Explorer`, and `reduceTransaction` with
   `ergo-lib-wasm-nodejs` (move it from devDependencies to dependencies, same pinned 0.28.0). Routes: `GET /`
   returns the `MosaikApp` (manifest `appName` "FreeDEX", `targetMosaikVersion` 2, `cacheLifetime` 0,
   `targetCanvasDimension` `COMPACT_WIDTH`) with the Swap view; `POST /quote` and `POST /swap` are the two
   backend actions; `GET /health` prints the explorer in use and the height. Every other path is 404. Each
   response is built from typed view objects in `server/mosaik.ts` that mirror the schema files; keep the
   element set to what the Swap view needs.
3. **The Swap view**, a translation of `src/ui/swap.ts`, not a redesign: the address chooser; a dropdown of the
   same token list the page uses (`src/tokenlist.json`), ERG pools first, with a text field for another token id;
   direction; the amount; the slippage with the page's default. `/quote` reads the pool fresh, answers with a view
   stating the quote in words (amount out, price impact, the pool, the miner fee of 0.001 ERG and "no other fee"),
   the same sentence the page shows before a wallet prompt, and a "sign" button. `/swap` reads the address's boxes
   and the last ten headers, builds with `buildSwap` or `buildSwapT2T` using the minimum from the quote the user
   saw (pass it back through the view, not a server-side cache), reduces, applies `sizeGuard`, and answers with
   an `ErgoPayAction` whose `url` is the `ergopay:` string and whose `onFinished` shows the transaction id and a
   link to the explorer. Every failure (bad amount, the builder's refusal, explorer unavailable, too large for
   the wallet) is a `DialogAction` in plain words, never a 500 with a stack.
4. **Limits and hygiene.** Bind to `127.0.0.1` unless `--host` says otherwise and print the URL to type into the
   wallet (`mosaikapp://<host>:<port>`) on start. Body limit 64 KiB; at most a handful of concurrent reductions
   (a counter, the rest answered "busy, try again"); the explorer cache as the page has it. Log one line per
   request to stderr with the path, status and milliseconds, never the address or the body. No cookies, no
   session, nothing written to disk. The context headers are read only to pick the canvas size and are not stored.
5. **Tests**, in vitest's Node environment beside the page's: the `MosaikApp` and every action response validated
   against the schema files with `ajv` (pinned, dev dependency; the schema files copied into `server/schema/`
   with the Apache-2.0 notice added to `THIRD-PARTY-NOTICES.md`); `/quote` and `/swap` driven through
   `node:http` against a stubbed `Explorer` returning a fixture pool and fixture boxes, asserting the quote text,
   the `minOut` round trip, the `ergopay:` prefix and the size guard; the mock chain executing the built swap
   as `test/properties/pools.test.ts` does; the body limit and the busy answer. Then one real run against mainnet
   from the shell, read-only: start the server, `curl` the root, post a 0.001 ERG quote and swap for the test
   wallet's address, and print the reduced size and link length (nothing is signed; the string is discarded).
6. **The page points at a server when it has one.** A build-time `VITE_MOSAIK_URL`; when set, `index.html`
   carries `<link rel="mosaik" href="...">` so a wallet given the page's URL finds the server. Unset on the
   Pages build, so the public page carries no link until a default instance exists; say so in the README.
7. **Hosting, documented in `docs/hosting.md`, LAN first.** Section one: on your own machine, `npm run mosaik --
   --host 0.0.0.0`, find the machine's LAN address, type `mosaikapp://192.168.x.y:8080` into the wallet's dApp
   URL box, add it as a favourite; what the phone and the machine must share (the same network; no router port
   open); what the server can see (the address the wallet chooses, the request, nothing else). Section two: a
   small VPS with a domain, a `systemd` unit file in `deploy/`, and Caddy in front for TLS (a reverse proxy to
   the port, nothing else), the cost line from the ROADMAP (about 4 to 5.5 euro a month) and the reason the free
   worker tier is out (26 ms against a 10 ms allowance). Write it; do not deploy anything public.
8. **The person's check.** Write the steps into `RESULT.md` with empty rows: start the server on the LAN, add
   the URL in the Ergo mobile wallet (Android) and in Terminus, open the app, choose the test wallet's address,
   quote and sign a 0.001 ERG swap, read the id the `onFinished` view shows; and the same from the desktop
   wallet app if one ran in step 1. Each row names the printed evidence it needs.
9. **Record and push.** `skunks/dexpage/RESULT.md` gains a dated section with the verified lines, the executor
   used, the test counts, the printed mainnet quote and reduced size, and what the person's rows wait on;
   `research/agents/ROADMAP.md` R5 tier 3 updated from "unverified" to what this session settled; worklist
   SK-063, `NEXT.md` and freedex's `CHANGELOG.md` updated; skunkyard committed locally, not pushed; freedex pushed
   once at the end. The server's tests run in the existing CI job; add no workflow. Count the runs: one.

## Do not

- Hold a key, a seed, a session, a database, or any state that outlives the request. If a design needs state,
  pass it through the view's values instead, as the quote's minimum is passed.
- Add a fee, an address of the operator's, or any output the page would not build. The server's transactions are
  byte-for-byte what the page builds for the same inputs; a test says so.
- Add telemetry, a third-party font, image or script URL in any view, or any request to a host the page does not
  already read. `iconUrl` and `errorReportUrl` stay unset.
- Deploy a public instance, buy a domain, or open a port on the person's router. The LAN form is the deliverable;
  the VPS form is a document.
- Submit any mainnet transaction. The one mainnet run in step 5 builds and reduces only.
- Build a second tab. Swap proves the path; the others are the next brief once a phone has signed through this one.

## Done when

The two "verify" lines are quoted with their sources; the server starts, serves a schema-valid `MosaikApp` and
the two actions, answers a real mainnet quote and reduces a real swap for the test address with the printed size;
the tests pass in the existing job with no new workflow; the page's build can carry the `rel="mosaik"` link and
the Pages build does not; `docs/hosting.md` gives the LAN steps first and the VPS form second; lint, typecheck,
tests and build are green; freedex is pushed; and the record holds the numbers and the person's rows waiting on
a phone.
