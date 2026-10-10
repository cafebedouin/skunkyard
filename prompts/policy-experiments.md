# Handoff: box-side policy experiments on a devnet, then suggestions

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` (and `~/.claude/CLAUDE.md`: evidence
before conclusions, mark [UNVERIFIED], findings that contradict or extend the docs get the detail).

Then read, in this order:
1. `research/policy/README.md`: the map you are testing. Building blocks, foreseeable problems, Ergo constraints,
   six experiments.
2. `research/policy/evidence/ergo-capabilities.md`: what a guard can see. A guard can see the spending tx id
   (`OUTPUTS(0).creationInfo._2.slice(0, 32)`, checked in source) and 9 headers, not 10.
3. `skunks/keepalive/README.md` and `KeepAliveAddress.es`: the keyless-maintenance block, on mainnet.
4. `skunks/qvault/README.md`, `QVault.es`, `QDay.es`, `devnet-test.py`: the signal-trigger and hash-key blocks.
   They show the harness pattern to copy; devnet 18/18.

**Your job.** Run the experiments below on a local devnet, record what happened, then write suggestions grounded in
the results. This is exploration, not a design: the user wants to learn what is possible and what it costs. Report
negative results as fully as positive ones.

## Rules

- **Devnet only.** No mainnet or testnet transactions, and no use of `~/.config/skunkyard/mainnet-wallet.txt` or the
  mainnet signer.
- **Every verdict is the node's.** ACCEPT is a 200 from `/transactions/check`. REFUSE is the node's "should pass
  verification", or, for a key path, the wallet's "Script reduced to false" from `/wallet/transaction/sign`. Anything
  else (malformed, unbalanced, a box gone) is a harness bug: fix it and rerun, and record that it happened.
- **Before each experiment's harness:** compile its contracts alone on the node first, to catch compile errors.
- **Commits:** one per experiment, on `main`, pushed, ending with the attribution lines your system reminder gives.
  Do not touch `research/agents/`, `skunks/upkeep/` or the Duckpools work (parked until Cheese answers).
- **Processes:** never `pkill`/`pgrep`/`ps | awk` by pattern from your shell. It kills the harness shell (exit 144).
  Stop things by pid or with `rig/devnet.sh down`.
- **No GitHub Actions dispatches** (see `CLAUDE.md`).

## The devnet (peeryard, no root needed)

```
cd ~/bin/peeryard
PEERYARD_JAR=$HOME/bin/ergo-node/ergo-6.0.7.jar rig/devnet.sh up ~/bin/skunkyard/skunks/policy/devnet-topology.json policy
rig/devnet.sh expose A 9181 policy        # REST API on http://127.0.0.1:9181, api_key "hello"
rig/devnet.sh status policy
rig/devnet.sh down policy                 # when finished; chain kept
```

The topology is one mining node, 20 s blocks, extra index on, minimal fee 0, wallet funded by mining.

Leave peeryard's checked-out branch alone (`soft-partition-split`); the devnet tool works from it. The devnet named
`keepalive` holds the qvault chain; use your own name (`policy`).

Quirks found on 2026-10-10:
- **Compiling:** `/script/p2sAddress` needs `{"source": ..., "treeVersion": 1}` on 6.0.7. For 6.0 methods
  (`getVarFromInput`, `Box.getReg`, `Header.checkPow`, `UnsignedBigInt`, `serialize`), check whether tree version 3
  is needed and say so.
- **Parsing:** `!flags(0).R4[Boolean].get` parses as `(!flags)(0)…`. Use `== false`.
- **Lambdas:** two-argument lambdas don't compile in some positions. Use one tuple argument (as `amt` in
  `KeepAliveAddress.es`).
- **Test boxes and the wallet:** the node wallet spends boxes at its own addresses as change. Keep test boxes you
  need later at a script address, or at the curve generator's key (`0008cd` + G, `kt.G`), which nobody holds.
- **Balance:** inputs must cover outputs plus any fee output. On the devnet a fee-less transaction is fine.
- **Signing:** `/wallet/transaction/sign` takes `{tx, inputsRaw, dataInputsRaw}` (box bytes from
  `/utxo/byIdBinary/{id}`). The wallet holds the first address's key and any keys from `/wallet/deriveNextKey`.
- **Helpers:** `skunks/keepalive/devnet-test.py` (`call`, `must`, `height`, `wait_height`, `wait_tx_outputs`,
  `FEE_TREE`, `G`).
- **WOTS:** `skunks/oneshot/scripts/wots-cli.mts` (`npx tsx scripts/wots-cli.mts commit|sign …`, from
  `skunks/oneshot`).
- **Long runs:** run harnesses with `python3 -u` in the background and follow them with a filtered monitor; don't
  chain sleeps.

## The experiments (from `research/policy/README.md`, in this order)

Put each in `skunks/policy/<n>-<name>/`: the contracts, `devnet-test.py`, `results.json` and a short `README.md` with
the case table. Each must include the adversarial cases that would break it, not just the happy path.

1. **One parameterised template.** One contract where each building block is switched by a constant:
   - owner key;
   - hash key (WOTS);
   - signal flag plus backstop;
   - KeepAlive maintenance;
   - two-step withdrawal;
   - spending limit.

   Compile the useful combinations. Measure tree bytes and the node's script cost per path. Measure the cost of
   unused blocks: does a switched-off block still cost bytes and evaluation? Compare with the separate contracts
   (KeepAliveAddress 404 B, QVault 1,177 B). Then work out the rent: bytes × 1,250,000 nanoERG.

   The question: is one standard template affordable, or is a small family better? A first measurement needs no
   transactions at all: compile and compare sizes. Cost needs `/transactions/check` runs.
2. **Two-step withdrawal vault.** The BIP-345 / Chia withdrawal-gate shape:
   - the owner announces a withdrawal into a "pending" box with a deadline and its destination fixed;
   - after N blocks anyone completes it;
   - before that, the owner (or a recovery key) can cancel it back to the vault.

   Adversarial cases: completing early, changing the destination, cancelling after the deadline, a stranger
   cancelling, two pendings satisfied by one output.
3. **Miner-signalled flag.** First prove a Merkle membership of an existing extension key (every block extension
   carries keys, e.g. interlinks and parameters) against `CONTEXT.headers(i).extensionRoot` in a script. The leaf
   and tree hashing are in `evidence/ergo-capabilities.md` §extension. Then try a custom key: does the stock
   devnet miner let you add one? Is there a node setting or API? If not, say what a custom miner would need.

   Record the cost, and the limits: presence only, at most 9 blocks back.
4. **Inheritance alongside KeepAlive.** An owner-activity register updated only by owner-key spends, and an heir
   path after N blocks of owner inactivity, read from that register and not from box age. Keyless refreshes must
   not reset it.

   Adversarial cases: a refresh that tampers with the register, an heir spending early, the owner resetting it
   after the heir's window opens.
5. **Hash-weakness canary.** A flag box that flips when anyone submits two distinct inputs whose hash agrees on its
   first k bytes. Use a small k on the devnet (e.g. 2–3 bytes, found by brute force) to exercise the path. Then a
   vault that reads it, like `QVault` reads `QDay`. Discuss what k and which hash would make a meaningful mainnet
   canary.
6. **Rekey in place.** A vault whose key (secp, or the WOTS commitment) sits in a register; the owner path lets
   the successor carry a new key; maintenance must keep it unchanged.

   Adversarial cases: a keyless refresh changing the key, a rekey without the old key, a hash-key rekey.

If an experiment can't be done (a missing primitive, compiler limits), stop it, record exactly why with the error,
and move on.

## Deliverables

- `skunks/policy/<n>-<name>/` per experiment, as above.
- **`research/policy/EXPERIMENTS.md`:** per experiment, what was tried, the case table, sizes and costs, what
  failed and why, and what it changes in `research/policy/README.md`'s map (mark contradictions explicitly).
- **A final section, "Suggestions":** what to build next and what to drop, ranked, each tied to a result.
  Specifically:
  - one template or a family;
  - which building blocks are ready to show the community, and which need a fork or a custom miner;
  - what a wallet would have to support first.
- **Update `research/policy/README.md`** only where results change it, with a pointer to `EXPERIMENTS.md`.
- **Update `NEXT.md`** with one paragraph: where this stands.
- **Last message to the user:** a short summary with the suggestions.
