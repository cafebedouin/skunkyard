# Research topic: an on-chain spending policy for autonomous agents

Opened 2026-10-02 from reading `Degens-World/agente` (an LLM-driven Ergo trading agent that signs with the node
wallet's API key and limits itself in TypeScript). Every bot in the developer chat runs the same way: a mnemonic or a
node key in config, which is unrestricted spending authority, with the limits enforced by the program the limits are
meant to constrain.

## Heilmeier

- **What.** A box script that enforces, on chain, the policy an agent's prompt or code cannot be trusted to: a
  maximum value out per spend, a minimum interval between spends, outputs only to whitelisted contract templates
  (plus a return path to the owner), change back into the same policy, and an owner key that overrides or sweeps.
  The agent holds a key that can only do what the policy allows; the node rejects everything else.
- **Today, and its limits.** Limits live in the agent's configuration (`MAX_ERG_PER_ORDER`), checked by the agent
  itself. A prompt injection through a token name, a misread price or a bug can empty the wallet. Bitcoin cannot
  express such a policy; Ethereum needs account abstraction; Ergo's eUTXO scripts constrain their own outputs by
  template and value with existing operations.
- **What is new.** Nothing cryptographic. The measurement is whether the whole policy fits one script within the cost
  limits, including a template check against a real DEX order script, and whether every bypass a reviewer can think
  of is rejected by the node rather than by the agent.
- **Who cares.** Anyone running a bot with funds; the DEX and lending teams whose users run them; the agent authors,
  who get a reference contract instead of a warning.
- **Risks.** A policy that is too tight is bypassed by the owner key in practice; a template whitelist that names
  the wrong bytes locks funds; the many-small-spends drain is the attack a per-spend limit invites and the interval
  must close it.
- **Cost.** The Q2 harness for costing, one devnet scenario for the attacks, Fleet for the agent-side build.
- **Checks.** Each attack below has a printed node verdict; one legitimate order is accepted.

## Questions (preregistered)

- **A1. Expressibility and cost.** The policy script compiled; cost with and without the template check; bytes;
  against the fixed per-transaction charge and the block limits.
- **A2. Attacks on a devnet.** Over-limit spend; wrong-template output; too-frequent spend (within the interval,
  using the box's creation height, which the node resets on every spend); drain through many small spends; change
  sent to a non-policy script; a spend with no owner-return path. Expected: all rejected by the script check.
- **A3. The legitimate path.** A Machina Finance order built through Fleet from the policy box, accepted and
  confirmed; the change box carries the policy; the agent key cannot do anything else.
- **A4. The agent repointed.** `agente` (or a minimal stand-in with the same calls) driven against the policy box
  with its own limit removed: the chain holds where the prompt did not. Devnet only, no real funds, no live LLM
  needed (a scripted "model" that always asks for the maximum is the test).
- **A5. Owner override.** The sweep and the policy change by the owner key; what the agent can and cannot observe.

## Kill criterion

If the template check for a real order script cannot be expressed within the relay cost cap, or the interval cannot
be enforced because the creation-height reset can be gamed, the topic closes with that note.

## Not in scope

Trading strategy, LLM evaluation, real funds, any mainnet deployment.
