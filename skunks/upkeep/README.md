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

Open after the fix round: a due-job box on testnet, an observe-mode log against it, a Lithos devnet candidate carrying a
beat, then the PR. Contract v2 question: an optional owner path (R7) for creators who want an exit.
