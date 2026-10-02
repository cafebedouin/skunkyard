# How skunkyard works

skunkyard asks questions about Ergo that only measurement on its own chain and script can answer, and turns the
answers into small projects that someone can pick up. Two kinds of thing live here, and the rule is that the second
only comes from the first.

| Kind | Lives in | What it is | Done when |
|---|---|---|---|
| **Research** | `research/<topic>/` | A question with a scope, a literature check, the scripts that measure it, and a result that quotes printed output | The question has a measured answer, its limits are stated, and the result has been posted where the maintainers read |
| **Skunk** | `skunks/<name>/` | A proof of concept born from a finding: a charter, the code, a result, and a hand-off | The hand-off exists: a pull request, an issue with a reference implementation, or a page someone else can run |

Outward text (`posts/`), dated reads behind claims (`notes/`), and shared tooling (`tools/`) serve both.

## Prior art this borrows from

- **Heilmeier's catechism** (DARPA, 1975), the questions a program must answer before it is funded: what are you
  trying to do, in plain words; how is it done today and what are the limits; what is new and why would it work;
  who cares; what are the risks; what does it cost; how long; what are the mid-term and final checks. Every research
  scope and every skunk charter answers these, in that order, in a page.
- **Kelly Johnson's rules** (Lockheed Skunk Works, 1943 on): a small team with authority over its work, reporting
  that is timely rather than voluminous, few outside reviews but real ones, and a record of what was done. Here that
  means one person and a model per project, a result file instead of status reports, and the seat reviews before
  anything goes outward.
- **Kill criteria** (the X moonshot practice): each charter names, before work starts, the measurement that would end
  the project. A skunk that cannot be killed by evidence is not a skunk.
- **ergo_logic's apparatus**, the sibling repository: one directory per investigation that never moves once cited,
  raw output captured before analysis, outside seats run blind on a slice, and GitHub-hosted runs as the place of
  proof for any public claim.

## Rules

1. **Every number names its script and its printed output.** Derived figures are labeled derived; claims from reading
   code or documents are listed in `notes/` with file and line. An estimate is called an estimate.
2. **A result file quotes, it does not restate.** `RESULT.md` carries the printed lines the conclusion rests on and the
   limits of the method, in that order.
3. **Outward text goes through the seats.** Before a post or a pull request: the three internal seats (derivation,
   fidelity, maintainer) and at least one outside seat on a clean slice, with the review log kept in `posts/`.
4. **Nothing is posted, pushed or filed without the person's go on the final text.**
5. **No target lists.** Aggregates are results; ranked lists of large exposed boxes or keys are not published, and the
   scripts do not print them unless asked.
6. **A skunk hands off or dies.** The charter names the recipient of the hand-off and the kill criterion; the result
   file says which happened.
7. **Layers decide where a question is settled.** `script`, `chain` and `tooling` questions are settled here; `node`
   questions (a network, an adversary, a version comparison) are peeryard scenarios registered in ergo_logic, and a
   skunkyard item is not scheduled before the foundation it rests on has a measured answer (`WORKLIST.md`,
   Foundations).
8. **Paths do not move once cited.** A directory a post links to stays where it is; reorganization happens before
   publication or by leaving a pointer behind.

## Current map

The hand-maintained register is `WORKLIST.md` (ids SK-nnn, lanes now/next/later/done); this table is the summary.

| | Status | Where |
|---|---|---|
| Research: post-quantum readiness, measured | Q1 dry run done, final run waits on sync; Q2 executed on a devnet; post drafted (v3) | `SCOPE.md`, `LITERATURE.md`, `q1/`, `q2/`, `posts/` (to move to `research/pq/`) |
| Research: TSNP | specification and reply archived; pilot planned; anonymity-set finding recorded in the session, to be written into the pilot | `tsnp/` (to move to `research/tsnp/`) |
| Skunk: oneshot | chartered, not started | `skunks/oneshot/CHARTER.md` |

The move to `research/` happens before the first post is published, with the forum draft's paths updated in the same
commit, so that the paths readers see are the final ones.
