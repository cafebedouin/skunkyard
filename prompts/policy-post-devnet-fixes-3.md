# Devnet session, part three: what the protocol-post review round found that only a run can settle

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`, then
`prompts/policy-post-devnet-fixes.md` and `-2.md` for the shape of this work, and `posts/seats/policy-post/REVIEW.md`
"Round 3" and "Round 4" for why. Six seats reviewed the protocol post and each listed what only a devnet run, a
re-measurement or a code change can settle; the lists are consolidated here, grouped by what the posts need. The
posts disclose each item as "not built", "not fixed" or "by reading, not run"; the writing session ports your
numbers afterwards. Do not edit the posts, the review log or the lessons document.

## A. Before the posts go out (each is cited by a post as missing)

1. **A vault that embeds `Pending2`, end to end** (`skunks/policy/2-twostep/Vault.es` with `PENDING_TREE` =
   `Pending2.tree`, 193 B; re-serialise, do not patch). On the `policy` devnet: deposit; announce into a `Pending2`
   box; complete after the deadline (output R4 = the pending box id); announce again and cancel back into the vault
   with the recovery key, and once with the owner key; the honest two-vault batch; the cross-vault theft shape
   refused against two such vaults (completion side) **and the cancel-side theft shape** (two `Pending2` boxes
   cancelled, one output to the vault and one to a stranger: REFUSE), which has never been run; and **row 2b's
   guard-less control** (a vault without `mine.size == 1` announcing two boxes into one pending box: ACCEPT), which
   the post marks "not run". Publish the vault tree, its `skunks/keepalive/template-hash.py` entry appended to
   `skunks/keepalive/template-hash.out`, the rows in a public results file, and the README table; say beside it that
   `results-crossvault.json` used a key address as the vault (`vault_R6`).
2. **The NFT account's hash-key tweak has no key counter** (`RekeyAccount3.es:68`). Add a per-key public seed beside
   the commitment and put it in the tweak; re-run the weld suite (15 rows plus `v3-hashkey`), add a row showing two
   successive hash-key rekeys use distinct tweaks, and **print the mempool cost of `v3-rekey` (secp) and `v3-merge`**
   (both `cost: null` today), so the family table no longer cites the pre-NFT 12,590 and 14,791. Record the tree
   size and the hash-key rekey cost.
3. **The schedule's cross-leaf negative:** a valid signature made at leaf i presented on a box registered at leaf j
   (REFUSE), with the honest row as its sibling. Record it as a test of leaf binding, not of the tweak (the seats'
   point: leaves i and j have independent chain starts, so it refuses with or without the index in the tweak).
4. **The schedule's current-leaf plant:** plant a box at the current leaf once its proof is on chain (the installing
   rekey's context variable 3), merge a payment into it (ACCEPT), show the owner cannot fold it into their own rekey
   (REFUSE: `mine.size == 1`, `regd.size == 1`), and reclaim with a second signature (ACCEPT). The post says "by
   reading, not run".
5. **WOTS+ other-key and replay negatives against `QVault.es` itself** (rows 6d, 6e), and **append, truncate and
   deep-flip rows on the WOTS+ paths of `RekeySchedule.es` and `RekeyAccount3.es`**, which have no negatives of
   their own; the post says "by reading on the two rotating addresses".
6. **A payment after migration:** after the backstop, pay into a vault after its hash-key spend; expect the owner
   path refused and the keyless merge accepted, and show that only a second signature with the spent key moves it.
7. **Flag-box churn:** refresh the flag box between building and submitting an owner spend that cites the old box;
   expect that spend refused. Then decide, and record, whether `QDay.es` gets a refresh window as KeepAlive has
   (a code change); the post states the churn "by reading, not run".
8. **Flag NFT provenance:** a flag box whose NFT was minted with amount 2, or minted into a key address, shown as a
   data input; record what the vault does (the post says the contract does not check supply or mint).
9. **`Pending2` completions into register-reading destinations** (Grok's row list): keyless completion into `RekeySchedule.es` with R5 set, into `KeepAlive.es` and into `Inherit.es` (expect the resulting box unspendable or the spend to throw), and the honest cases into the schedule with R4 only, `KeepAliveAddress.es`, `QVault.es` and `RekeyAccount3.es` (expect spendable). Then decide, and record, whether `Pending2` should carry the id in a register the destinations do not read, or the vault should restrict R4 to script hashes a wallet allowlists. **Wrong-type registers at the rotating addresses** more generally: a plain payment carrying an R4 of another type (an EIP-4 memo,
   or a `Pending2` completion's `Coll[Byte]` R4 into a `RekeyAccount3` address whose R4 is a `GroupElement`; a
   `GroupElement` R4 at a schedule address). The seats read sigma-state as throwing on a wrong-type register read,
   which would strand the payment; settle it with rows.
10. **The schedule's close with variable 0 absent or out of range** (the close path reads it; expect REFUSE), and a
    merge with variable 1 set (expect REFUSE: the merge requires it unset).

## B. Re-measurements the post quotes as estimates

11. **WOTS+ against plain WOTS on the same messages**, several spends each (eight), recording the hashed-step count
    per spend and fitting cost per step as `slhdsa_ref.py` does, so the overhead is quoted at matched step counts
    (today: 17.7% and 16.3% from one spend each on different random messages).
12. **The SLH-DSA cost ceiling on a variant that hashes every step** (a code change to the verifier for the
    measurement only: 3,675 steps, an over-bound), measured once in the harness; the post quotes the fit's 233,600 at
    the checksum-capped 3,570 steps. Also report the eight-spend median correctly: the harness's `median=188247`
    (`run.log:40`, `results.json` `cost_median`, `slhdsa/README.md:22`) is the upper-middle value; the median is
    187,566. Fix the harness's median and the record.
13. **A one-box fixed-key move and the schedule merge at 2, 4 and 8 inputs**, so any cost ratio is like for like
    (today 4,928 is a quarter of a four-box transaction).
14. **SLH-DSA on a devnet with mainnet cost parameters** (`inputCost` 2,407, `outputCost` 298), to measure the
    201,250 the post computes.
15. **Re-run the SK-026 benchmark** (`research/lattice/bench/`) on the 6.0.7 jar on a quiet machine; the 1,890 and
    13,097 figures came from 6.0.6 under load (`research/lattice/RESULT.md` header).
16. **Optional:** a like-for-like hashing-share measurement for SLH-DSA (the stand-in gave 13%, the computation 11%).

## C. Records and comments (no run; trees unchanged; confirm each template hash after)

17. Stale comments: `QVault.es:6,27` ("a WOTS signature", "~18%"), `RekeyAccount3.es:16,22` ("WOTS"),
    `RekeySchedule.es:9,13,18` ("Theft is impossible without a token", "WOTS signature"); confirm the compiled
    template hashes are unchanged.
18. `slhdsa/README.md:43-47` still gives 3.9× and 3.4×; `:195` gives residual 335 where `run.log:66` prints 367;
    `qvault/README.md:13` "~18%"; `SCHEME-SIZING.md:103` "~8%"; the median (item 12). `1-template/PolicyTemplate.es`
    has no length guard: mark it superseded in its README or add the guard.
19. Every record the numbers land on (`2-twostep/README.md`, `6-rekey/README.md`, `SCHEME-SIZING.md`,
    `CHARTER.md`, `qvault/README.md`, `slhdsa/README.md`, `research/pq/ROADMAP.md`), each number with its printed
    line.

Commit on `main` by explicit path, each contract with its rows in one commit; rules as before (no mainnet or
testnet transactions, no Actions dispatch, pattern kills never; the `policy` devnet is a peeryard rig, preflight
before any row). End with: each item's verdicts and numbers, the new trees' sizes and template hashes, which
items you did not do and why, and the commit ids.
