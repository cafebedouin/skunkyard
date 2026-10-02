# Research topic: what a transaction can enforce about its own inclusion and ordering

Opened 2026-10-02 from a developer-chat idea (Grayman, Discord): paying a miner for a block ordering or priority by
prearrangement, hash rental with intentional block construction, with Lithos's LIT token as the instrument. Not
endorsed; measured before judged.

## Heilmeier

- **What.** Find out, on Ergo's chain and script as they are, which inclusion properties a transaction can make
  enforceable by contract rather than by trust: who includes it, by when, in what order relative to other
  transactions, at what position in a block, and what a Lithos miner can do that a stock node cannot.
- **Today, and its limits.** Inclusion is bought with a fee output to the standard fee script, which any miner can
  claim, and the node's candidate builder orders the mempool by fee rate. Lithos gives miners full block control and
  binds a collateral box to the block's own coinbase through `minerPk`. Prearranged ordering exists elsewhere as MEV
  markets (Flashbots bundles, proposer-builder separation), which Ergo has no analogue of.
- **What is new.** Ergo's script context exposes the including miner (`CONTEXT.preHeader.minerPk`, also as
  `minerPubKey`) and the height, so a payment can be conditional on *which* miner includes the transaction and *by
  when*, with no new opcode. What it does not expose is the transaction's position in the block, so absolute ordering
  cannot be enforced by script; relative ordering can, by spending another transaction's output.
- **Who cares.** Lithos (its miners already build their own blocks and its contracts already use the primitive);
  anyone proposing a fee market beyond fee-per-byte; anyone worried about the same primitive being used for censorship
  or for buying consensus-relevant ordering.
- **Risks.** A measurement that works becomes a how-to for ordering markets whose economics centralize mining
  (hash rental for intentional construction is the attacker's tool as well as the partner's). The measurements here
  stop at what the protocol permits and what the stock node does; they do not build a market.
- **Cost.** Devnet runs on the rig, a few sessions.
- **Checks.** Each question below has a printed devnet verdict.

## Questions (preregistered, 2026-10-02)

- **I1. Preferred partner.** A transaction whose fee output is spendable only by miner M (`proveDlog(M)` plus the
  reward delay, instead of the standard `minerPubKey` fee script). On a two-miner devnet: does the stock node's
  candidate builder treat it as a fee at all (the node recognizes fees by the fee script's bytes, read:
  `ErgoTreePredef.feeProposition`), does miner M include it, does the other miner include it, and what does the
  mempool do with a transaction that pays no recognized fee? Expected: the stock node does not count it as a fee, so
  only a miner with a modified builder (Lithos) includes it; to be measured.
- **I2. Deadline.** A fee output that is spendable only if `HEIGHT <= h`. Does a stock miner include it before h and
  refuse after, or include it anyway and leave the fee unspendable? (The node validates the transaction, not the
  fee box's spendability.)
- **I3. Relative order.** Two transactions where B spends an output of A: both in one block, in which order, and under
  input blocks (sub-blocks) which input block each lands in. Then A and B independent: can anything a transaction
  carries make a stock miner place B before A? Expected: no.
- **I4. Lithos.** What a Lithos miner's block builder exposes for inclusion policy (read from the client source;
  `app/mining/CandidateTxBuilder.scala`), and whether a LIT-denominated or collateral-bound payment to the including
  miner is expressible with the collateral contract's `LenderPK == minerPk` pattern.
- **I5. The cost of the mechanism.** Script cost and bytes of a miner-conditional fee output against the standard
  fee output, in the Q2 harness.

## Kill criterion

If I1 shows the stock node ignores miner-conditional fee outputs and Lithos's builder has no hook for them, the
topic reduces to a note: "enforceable inclusion deals on Ergo require a custom block builder", and it closes with
that note and no skunk.

## Not in scope

Building any ordering market; measuring MEV extraction on mainnet; hash-rental economics.
