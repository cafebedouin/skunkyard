# freedex hardening: invariants written down, properties tested, scanning on, a registry, accessibility

You are hardening FreeDEX, in `/home/scott/bin/freedex` (CC0, live at https://cafebedouin.github.io/freedex/, one
Pages run per push to `main`) with its record in `/home/scott/bin/skunkyard/skunks/dexpage/`. Read first:
`/home/scott/bin/skunkyard/CLAUDE.md` and `PROGRAM.md` (every number names its printed output, nothing outward
without the person's go, and the GitHub Actions budget: tens of runs a day across the whole account, so every new
workflow and every bot that opens pull requests is sized before it is added), then freedex's `README.md`,
`THIRD-PARTY-NOTICES.md`, `test/hashes.test.ts`, `src/sigmafi-contracts.json`, and one builder with its test pair
end to end (`src/amm.ts` with `test/amm.test.ts`) to learn the style. A reviewer's list prompted this session; the
items below are the ones accepted from it, with the reasons they were accepted. No behaviour change to any builder
is allowed in this session; if a property test finds a bug, record it, fix it in the smallest way, and say so.

## Do, in this order

1. **Invariants, written down.** `docs/invariants/` with one file per domain: `pools.md` (ERG and token-to-token
   swaps, deposits, redemptions), `orders.md` (Machina, Babel), `bank.md`, `bonds.md`, `escrow.md`, `clock.md`,
   `option.md`, `upkeep.md`, `signing.md` (EIP-12 and ErgoPay: what the page builds, what the wallet decides, the
   slippage minimum from the quote the user saw). For every builder, in this order: preconditions it checks and
   what it throws; which values the user sets and which are read from the chain; the arithmetic and its rounding
   direction, quoting the contract line it mirrors; what the contract refuses that the builder does not pre-check;
   the test that proves each refusal, by file and case name; and known limits (the creation-height clock, the
   explorer's height lag, the rent reserve rule for token-holding boxes, the one-pool-per-transaction rule). Short,
   factual, no prose beyond what a reviewer needs. Link each file from the README.
2. **Property-based tests** with `fast-check`, pinned, in `test/properties/`. Generators draw pool reserves, fee
   numerators, amounts and decimals from realistic ranges (reserves up to 2^62, amounts up to the reserve). Properties,
   each with the mock chain as the oracle where a transaction is involved: a pool quote never exceeds what the pool's
   own rule allows and a swap built at that quote executes; a swap built with `minOut` one above the quote is refused
   by the builder; the ERG-first and tokens-first deposit quotes agree; `formatUnits(parseUnits(t, d), d)` is the
   identity on canonical decimal strings for every `d` in 0 to 9, and `parseUnits` refuses every non-canonical one;
   the Babel and Machina sizing never return a payout below the brute-force maximum on pools small enough to
   enumerate; a clocked-box leg sized by `sizeLeg` is accepted by the script at its due height and refused one block
   early; an option's exercise and reclaim are accepted and refused on each side of H. Keep runs under ten seconds
   each so CI stays fast.
3. **A contract registry.** `src/registry.json`: for every contract the page builds against, protocol name,
   network, ErgoTree (or template with its placeholders named), template SHA-256, source (repository and commit, or
   the chain), licence, and the date the hash was last checked against a live box on mainnet. Fold
   `sigmafi-contracts.json` into it. `test/hashes.test.ts` reads the registry instead of literals, recompiles the
   contracts whose source is in `contracts/`, and fails if any entry's hash disagrees with its tree. `scripts/
   registry-check.ts` queries the explorer for one live box per entry and prints the count, for the record.
4. **Scanning and dependency hygiene, sized to the budget.** `npm audit --omit=dev` as a CI step (free). A CodeQL
   workflow on a weekly schedule and on pull requests, not on every push. Dependabot for npm, monthly, grouped into
   one pull request, so it costs at most one CI run a month. Branch protection on `main`: the CI check required,
   no force pushes. `SECURITY.md` with the disclosure address the person gives you (ask; do not invent one) and a
   plain statement of what the page does and does not hold. Say in the record how many Actions runs a month these
   add.
5. **One browser test, on pull requests only.** Playwright, pinned, one job in the existing workflow gated to
   `pull_request`: load the built page from `dist/` through a local static server, confirm the CSP meta is present,
   choose "sign with your phone", enter the test wallet address (read-only), build a 0.001 ERG pool swap, and
   assert the QR panel renders and the `ergopay:` link is at most 2,800 characters. This is the one check the
   happy-dom harness cannot do: the WASM instantiating under the CSP in a real browser. Keep it to one browser and
   under two minutes; if Playwright's browser download is slow in CI, cache it.
6. **Explorer resilience.** Retry with backoff (three attempts, 1 s, 2 s, 4 s) inside the failover loop before the
   next backend is tried; a visible "explorer unavailable, retrying" state on every tab while listings are loading
   or failed, in place of a silent empty table; the existing fallback line kept. No telemetry of any kind: the page
   phones nobody.
7. **Accessibility.** Every input labelled (`for`/`id` or `aria-label`), the log and the warning lines announced
   (`role="status"`, `aria-live="polite"`), buttons reachable and operable by keyboard in tab order, focus moved to
   the QR panel when it opens and returned on close, and the confirmation text a user sees before a wallet prompt
   stating the amounts in words. Run an automated accessibility check (`axe-core`, pinned) in the happy-dom harness
   on each tab and fix what it reports.
8. **Housekeeping.** Move the protocol modules under `src/protocols/<name>/` with their tests alongside, pure
   rename, no behaviour change, imports updated, and the invariants files pointing at the new paths. A `CHANGELOG.md`
   starting from the first push, a version tag `v0.1.0` on the commit this session ends on, and a compatibility
   section in the README: wallets (Nautilus and SAFEW by EIP-12; Ergo Mobile Wallet and Terminus by ErgoPay,
   static mode; Satergo untested), explorers (the two backends), node versions the contracts were checked on, and
   the browsers the WASM path was run in (only what the person has confirmed). One run of `vite-bundle-visualizer`,
   its one-line conclusion in the record, nothing else unless it shows a second heavy chunk.
9. **Record and push.** `skunks/dexpage/RESULT.md` gains a dated section with the printed test counts, the property
   runs' counts and seeds, the registry check's output, the Actions-per-month estimate, and the bundle note;
   worklist SK-063 and `NEXT.md` updated; skunkyard committed locally, not pushed; freedex pushed once at the end,
   and the tag pushed with it.

## Do not

- Change what any builder does. If a property test disagrees with a builder, the test is right until proven
  otherwise against the contract on the mock chain; record the disagreement before touching code.
- Add any workflow that runs on every push beyond the one that exists. Count the runs you add and say the number.
- Add telemetry, analytics, error reporting services, or any request to a host the page does not already read.
- Invent a disclosure address or a maintainer name for `SECURITY.md`; ask.
- Submit any mainnet transaction.

## Done when

The invariants files exist for every domain and the README links them; the property suite runs green in under a
minute; the registry is the single source for every hash and the check script printed a live box for each entry;
CodeQL, Dependabot, audit and branch protection are on at the stated cadence; the Playwright job passed on a pull
request and showed the QR panel under the CSP; the accessibility check reports nothing on any tab; lint, typecheck,
tests and build are green; the tag is pushed; and the record says what changed and what it cost in runs.
