# peeryard: a devnet hook for the Babel arbitrage control (SK-049)

Repository: peeryard, branch `lithos-devnet`. Create branch `lithos-babel-arb` from its tip and push to it. The rig
needs no root, only unprivileged user namespaces (`unshare -Urmn`, `rig/README.md` prerequisites), plus the node
jar, Java 17 and the client's staged distribution. Check whether `unshare -Urmn true` works in your sandbox; if it
does and the rest can be built, run the hook; if not, write it and say plainly what you could not run. It is run
locally either way before anything is merged.

Read `AGENTS.md`, `rig/PHASES.md`, `rig/README.md` (the lithos rows), and above all
`rig/examples/lithos-upkeep.sh` and `.json`: the new example is that one with a different setup and a different
PASS. Also read `rig/examples/lithos-block.sh` for how the client is started from its staged distribution.

## What it proves

That the Lithos client's `babel-arb` upkeep job (branch `upkeep-babel-arb` on `cafebedouin/Lithos-Client`; brief in
that repository at `prompts/phase-8-babel-arb.md`) closes a price gap between an EIP-31 Babel box and an ErgoDEX v1
ERG pool in one transaction in the miner's own block, with no wallet input and no fee.

## The hook, `rig/examples/lithos-babel-arb.sh` (+ `.json`, same chain as lithos-upkeep: one indexed miner A,
v4, 20 s blocks, zero fee floor)

1. Wait for block version 4 and for A's wallet to hold enough ERG (as lithos-upkeep does).
2. From A's wallet, issue three tokens (`/wallet/assets/issue`): a pool NFT (1), LP tokens (a large supply), and
   token Y. Wait for each to confirm before using it.
3. Create the pool: one box at the ErgoDEX v1 native pool tree (the client's
   `ErgoDexContracts.NativePoolErgoTree`; convert it to an address through the node, do not hand-encode) holding
   about 100 ERG, or what A's devnet wallet allows (keep the reserves far above the trade), tokens in
   the order NFT, LP (all but a small minted share, as a real pool reserves them), Y, and R4 = Int 997.
4. Create a Babel box at the EIP-31 template tree for token Y (tree in the phase-8 prompt), R4 = A's key as a
   SigmaProp, R5 = a bid twice the pool's spot price per token unit, holding enough ERG for a trade worth seeing.
   Write every id and the bid into the run directory.
5. Start the client (staged distribution and config passed in as `LITHOS_STAGE`, `LITHOS_CONF`, as lithos-upkeep
   does) with upkeep in candidate mode, `verifyWithNode` on, only the `babel-arb` job enabled for token Y, every
   other source off.
6. **PASS**: within 300 s, a block mined by A holds one transaction with the pool at input 0 and the Babel box among
   its inputs; its outputs are the pool successor at 0 (more ERG, fewer Y), the Babel successor (less ERG, more Y,
   R4 and R5 unchanged, R6 = the old box id), and one revenue output whose value is the difference; no input
   belongs to A's wallet keys; no fee output. Print the profit, and check it against the pool rule
   (`Y0 * dX * 997 >= -dY * (X0 * 1000 + dX * 997)`) and the Babel rule (`addedTokens * R5 >= ergTaken`)
   recomputed in the hook from the boxes themselves.
7. **Negative arm** (the same example, a second phase, or a flag): move the bid to half the spot price and show no
   such transaction for 10 blocks.

Use pid files and stop by pid only; never kill by pattern (`ergo_logic/docs/method/process-discipline.md` in the
user's tree; the rule is in `AGENTS.md` if present). Add the example's row to the README and the suite file the
lithos examples use, marked as needing `LITHOS_STAGE` and `LITHOS_CONF`. One commit for the hook, one for the docs.
Report what you could not run.
