# Devnet session, part three: the `Pending2` vault end to end, the NFT account's key counter, the cross-leaf negative

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`, then
`prompts/policy-post-devnet-fixes.md` and `-2.md` for the shape of this work and `posts/seats/policy-post/REVIEW.md`
"Round 3" for why. Three items, each a contract-level gap the third review round found; the posts disclose each as
"not built" or "not fixed" and the writing session will port your numbers.

1. **A vault that embeds `Pending2`, run end to end.** `skunks/policy/2-twostep/Vault.es` compiled with
   `PENDING_TREE` = `Pending2.tree` (193 B; the constant's length changes, so re-serialise, do not patch). On the
   `policy` devnet: deposit, announce into a `Pending2` box, complete after the deadline to the destination (output
   R4 = the pending box id), announce again and cancel back into the vault with the recovery key, and the honest
   two-vault batch; the cross-vault theft shape refused against two such vaults. Publish the vault tree
   (`Vault2.tree` or the name the README chooses), its `template-hash.py` entry appended to
   `skunks/keepalive/template-hash.out`, the rows in a public results file, and the README table. The existing
   `results-crossvault.json` used a key address as the vault (`vault_R6`); say so beside the new table.
2. **The NFT account's hash-key tweak has no key counter** (`RekeyAccount3.es:68`: the NFT id and (chain, step)
   only), so every key the account installs over its life shares one hash family. Add a per-key public seed stored
   beside the commitment (a register, or derived from the commitment's own bytes) and put it in the tweak; re-run
   the weld suite (15 rows plus `v3-hashkey`), record the tree size and the hash-key rekey cost.
3. **The schedule's cross-leaf negative:** a valid signature made at leaf i presented on a box registered at leaf j
   (REFUSE), with the honest row as its sibling, added to `devnet-test-schedule.py` and `results-schedule.json`.
   While there: the stale comments in `QVault.es` (lines 6 and 27), `RekeyAccount3.es` (16, 22) and
   `RekeySchedule.es` (9) say plain WOTS, "~18%" and "theft is impossible without a token"; fix the comments
   (they do not change the trees; confirm the template hash is unchanged after).

Records: `2-twostep/README.md`, `6-rekey/README.md`, `SCHEME-SIZING.md`, `CHARTER.md`, `qvault/README.md`,
`research/pq/ROADMAP.md`, each number with its printed line. Do not edit the posts, the review log or the lessons
document. Commit on `main` by explicit path; rules as before (no mainnet or testnet transactions, no Actions
dispatch, pattern kills never). End with: the vault tree's size and template hash, each row's verdict, the NFT
account's new tree size and rekey cost, the cross-leaf verdict, and the commit ids.
