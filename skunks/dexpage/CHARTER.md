# dexpage: a self-hosted static page for Machina limit orders (SK-063, tier 1)

Chartered 2026-10-29. The first stage of SK-063 (`research/agents/ROADMAP.md` R5): the conceptual endpoint is
what mewfinance.com offers, served as static pages anyone can host. This skunk is the smallest piece that tests
the whole static stack on mainnet: one DEX (Machina limit orders), one wallet path (Nautilus, EIP-12, the way
SigmaFi does it), no server.

## Heilmeier

- **What.** A page of static files that lists every open Machina ERG-to-token limit order on mainnet, lets a
  connected wallet create one, fill one, or close its own, and never holds a key. Build with Fleet and the Machina
  SDK in the browser, read from a public explorer, sign and submit in the wallet.
- **Today, and its limits.** Machina's own front end and Mew's DEX are hosted services with closed source
  (Mew Lock excepted); tokenjay.app runs a server; agente drives Machina orders from a node wallet's API key. A user
  who wants to trade without trusting a hosted front end has no page to run.
- **What is new.** Nothing cryptographic. The measurement is whether the whole flow works from a static host with
  no backend of its own: the explorer's CORS, the template-hash listing, Fleet's builders against the audited
  contract, and a browser wallet's signing, each checked on the real chain.
- **Who cares.** Anyone who would self-host a DEX front end; the Machina maintainers (a second client for their
  SDK); SK-005, whose client half this becomes once the page can hold a fenced key.
- **Risks.** A malformed box under the template crashes the listing (handled: skipped); the explorer changes its
  search API; a wallet refuses the context extension the fill needs; the page shows a price in the wrong unit and a
  user trades at it. The last is the one to test with pocket change before anyone else uses it.
- **Cost.** One session to build and test on the mock chain (done 2026-10-29); one wallet session by the operator
  on mainnet with pocket change; one deploy to GitHub Pages.
- **Checks.** Mock chain: create, partial fill, full fill, close, and two refusals (`test/orders.test.ts`).
  Mainnet: one order created, filled or closed from the deployed page, transaction ids recorded in `RESULT.md`.

## Kill criterion

If the deployed page cannot complete create, fill and close on mainnet without a server of its own, this skunk
closes with that note, and SK-063's client half is a Fleet helper only. No server is added to rescue it.

## Hand-off

- A repository anyone can fork and deploy to GitHub Pages (`deploy/pages.yml`, one run per push).
- A pointer to the Machina maintainers (the SDK's second client) and, after the fence exists, the fenced-key stage.

## Not in scope

Grid orders, token-to-token orders (the SDK marks T2T unsupported), the mobile ErgoPay path (SK-063's three checks),
price feeds, charts, any server.
