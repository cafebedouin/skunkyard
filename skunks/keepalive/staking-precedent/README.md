# The staking precedent against the shared-output finding (2026-10-11)

The protocol post names the ErgoPad-style staking incentive boxes (6,847 merged before rent age,
`skunks/upkeep/mainnet/README.md`) as KeepAlive's precedent: a keyless consolidation path with a per-box bounty. The
post also describes the shared-output theft against a keyless merge that checks only "at least the total less the
bounty". This records whether the precedent has that shape. **It does not.**

## The read

Trees: one box of each template, fetched from the mainnet explorer (`staking-278ccff2.tree`, box `32ebd7a6…`, 729 B;
`staking-b924a4f7.tree`, box `8cdd87f6…`, 714 B; ErgoTree v0, 47 constants). Template hashes by
`../template-hash.py`: SHA-256 (the explorer's) `278ccff223ae2d7debac0626704be6046ade899969970565cf6395793ee84d02`
and `b924a4f735730da5d8dc4cd658ef2308fb520d38510aed08db549be989db2943`; Blake2b256 (the node index's)
`343683d6f488cac9349bc66a3ce5f3ee2d6e9d3d1a5a7f0462419c686a5dc807` and
`699dedd649bb60a9ae53457884ae38fbb71748b24aec834fca30f981cb3bd3c8`.

Decompiled with sigma-state 6.0.7 (`Decomp.scala`; output in `decompiled-*.txt`). Both templates carry the same
consolidation clause, one of their paths:

```
SELF.value <= 100000000
&& OUTPUTS.size == 3
&& OUTPUTS(0).value > SELF.value && OUTPUTS(0).propositionBytes == SELF.propositionBytes
&& OUTPUTS(1).value == 500000 * INPUTS.filter(same script).size
&& OUTPUTS(2).value == 1000000
```

The transaction has exactly three outputs, and two of them have exact values, so conservation puts every other
nanoERG, merged or brought by a foreign input, into OUTPUTS(0) at the staking script. An executor takes the bounty,
plus OUTPUTS(2) if it routes that to itself instead of the miner. A third-party payout cannot stand in for the
successor and carry the merged value away. The protection is the pinned output count and values, not tokens: the
boxes carry none.

## The run

Policy devnet (node 6.0.7), boxes created at the exact mainnet trees (`devnet-staking-shared-output.py`,
`results-staking-shared-output.json`; `devnet-staking-tokrow.py`, `results-staking-tokrow.json`), 10 rows, all as
expected:

| row | 278ccff2 | b924a4f7 |
|---|---|---|
| honest consolidation, two boxes | ACCEPT | ACCEPT |
| shared-output theft, the take in a fourth output | EVAL-ERROR; REFUSE with a token-bearing foreign box | REFUSE |
| shared-output theft, the take folded into OUTPUTS(1) | EVAL-ERROR; REFUSE with a token-bearing foreign box | REFUSE |
| a foreign input, three outputs: the foreign value lands at the staking script | ACCEPT | ACCEPT |

The EVAL-ERROR rows: when the consolidation clause is false, `278ccff2`'s stake-operation path reads
`INPUTS(0).tokens(0)`, which throws on a token-less foreign box. That is a refusal too; with a token-bearing foreign
box the script returns false.
