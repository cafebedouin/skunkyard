# Skunk: the Lithos upkeep adapter (SK-043)

A general chain-maintenance candidate source for Lithos-Client: keyless, fee-less maintenance of other protocols' boxes
in the miner's own block, from a registry of reviewed jobs, off by default. Code lives in the clone `~/bin/lithos-upkeep`
(branch `upkeep-adapter`, fork `cafebedouin/Lithos-Client`); this directory holds what skunkyard keeps: the review record
and the research questions it answers (`research/agents/UPKEEP.md` U3, `ROADMAP.md` R1).

- `SEATS.md`: the five-seat review of the PR (2026-10-08) with every seat-introduced fact checked and its disposition.
- `seats/2026-10-08/`: prompts, raw answers, provenance, the slice manifest and the slice builder.
- `testnet/`, `devnet/`: the acceptance checks (a due-job box on public testnet; the devnet rig for a candidate carrying a beat).
- Outward drafts: `posts/2026-10-upkeep-summary.md` (executive summary) and `posts/2026-10-upkeep-maintainer-dm.md`
  (the DM to the Lithos lead developer before the PR); both wait on the acceptance results and a seat round.

Built in four cloud sessions (framework; heartbeat job and `DueJob.ergo`; hardening; shape) with the operator compiling and
testing each (one trivial fix in four phases); then the seats; then the fix round (`prompts/phase-5-seats.md` in the clone).

After the fix round (2026-10-09): a due-job box on testnet (`testnet/`); on a devnet, one rig command from a wiped chain to
a block the client built carrying its genesis and the beat (`devnet/FINDINGS.md`, runs 1 to 9 by hand, rig runs 1 to 4;
the rig lives in peeryard `rig/examples/lithos-block.{json,sh}`); mainnet has 30 Lithos blocks, a 1.6% share
(`research/agents/lithos-blocks-mainnet.py`). A seventh cloud session wrote the stacked follow-on (`upkeep-space`:
value-per-byte ordering, an opportunistic share). PR branches, stripped and squashed: `pr/upkeep`, `pr/upkeep-space`,
`snapshot-spec-wait`; texts in `pr/`. Second seat round on both PRs: `seats/2026-10-09/`. Contract v2 question: an
optional owner path (R7) for creators who want an exit. The observe-mode log on testnet is optional and not done.
