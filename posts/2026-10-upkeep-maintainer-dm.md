# DM to the Lithos lead developer: the upkeep source (final, 2026-10-09)

Status: sent by the user after five independent reviews; the overview issue is
https://github.com/Lithos-Protocol/Lithos-Client/issues/13. Earlier dialogue: `notes/2026-10-05-lithos-reply.md`.

---

Following up on the keeper-executor thread. The upkeep source is built, reviewed and pushed; I opened an issue with the overview rather than PRs, so you can take it in whatever order suits you: https://github.com/Lithos-Protocol/Lithos-Client/issues/13

Three stacked branches on my fork, each one squashed commit, kept apart from your development work:

1. `deployment-override`: a descriptor that installs a private chain's protocol ids in place of the network constants (empty by default, refused on mainnet without allowOnMainnet), a deployer that mints the tokens and creates the protocol boxes with the client's own contract code, and every protocol contract's tree pinned on both networks. This is what let the rest be tested end to end on a devnet.
2. `upkeep-source` (on 1): the upkeep candidate source, modelled on your rent source: a job registry, a ScriptJob base for boxes at one script with a fixed successor, a reference heartbeat job for a due-job box (R4 last beat, R5 period, R6 tip; tree pinned, source kept with the tests), the node's check on every successor, and an observe mode. Off by default, every job too.
3. `upkeep-space-option` (on 2): two more options, off by default: an order by what a beat would actually pay, and an opportunistic count when the mempool leaves room.

Plus `snapshot-spec-wait`, one line for the flaky snapshot spec.

Evidence: full suite on Java 17, 2,772 tests at upkeep-source, 2,800 with the options. On a devnet with 20 s blocks, the deployer deployed the protocol, the client self-joined the collateral queue and a block carried its genesis and an upkeep beat together. A due-job box is live on testnet at the heartbeat's script; since you run testnet, I have left a candidate-mode block carrying a beat there to you.

What holds by construction: nothing changes with the shipped config; no upkeep transaction can spend a box its job did not report and the build did not read back, or one at the wallet's keys, or pay a fee, or send value anywhere but the box's own script or the miner's collection output; bounds match rent's.

Open questions, yours to decide, each a cheap change either way:

1. Do you want the framework before a real protocol job exists? The heartbeat proves it works; a protocol job (your Dexy one) is what proves it is worth having, and it would shape ScriptJob.
2. Where should the reference contract and the box recipe live: with the tests in the client, as now, or in a contract repo the client points to?
3. Opportunistic mode: at the defaults it amounts to maxTxs raised to 20 with a back-off when the mempool is busy. Would you rather have that as a plain congested count below maxTxs, with no mempool read on the build path?
4. A client-wide gap the work surfaced: a rejected package is reported to the sources only as a dropped height, so a successor the node's check accepted and block validation refused is rebuilt next block. Rent has the same exposure. Separate issue?

The whole review record, five independent read-throughs with every finding and what was done about it, is public in my skunkyard repo under skunks/upkeep/. Say the word and I open the PRs in that order, or take the branches directly.
