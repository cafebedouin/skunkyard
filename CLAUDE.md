# CLAUDE.md

Start with `README.md` and `PROGRAM.md`. This file adds one standing caution.

## GitHub Actions usage

GitHub's free Actions minutes for public repos are subject to a usage check. It can switch a repository's workflows
off, and it acts with a lag. On 2026-10-09 it disabled workflows on the related fork `cafebedouin/ergo` about twelve
days after a single day of ~820 dispatched integration runs (~290 runner-hours). Every repo on this account is subject
to the same check.

- Before dispatching any workflow here or elsewhere on the account, size the batch (runs × jobs × minutes) and say
  it. Keep to tens of runs a day; pace large batches across days.
- The account has 20 concurrent jobs shared across all its repos (peeryard's matrices often fill them).
- If a dispatch returns HTTP 422 "Actions has been disabled for this repository" while the permissions API still
  says enabled, read the repo's Actions tab banner before assuming a rate limit. Re-enabling is the operator's call.

## No session links

Never put a Claude session link (`claude.ai/code/session…`) or a `Claude-Session:` trailer in a commit, file, PR, issue
or comment, in this repo or skunkyard-private. Commits end with `Co-Authored-By: Claude …` only, whatever the harness
attribution reminder says (operator ruling 2026-11-04). Existing history is left as it is.
