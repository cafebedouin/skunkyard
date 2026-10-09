# Deployment override and deployer for private chains; every protocol contract's tree pinned

## What

The client compiles its protocol contracts from token ids fixed per network, so on a chain with no Lithos
deployment it finds no collateral box and never builds a Lithos block. Two pieces change that, and they are what let the
client be tested end to end on a devnet rather than on mainnet:

- `node.deployment.file`: a JSON descriptor of a deployment (the token ids, the genesis dictionary box, the
  protocol box ids) that `Deployment.install` reads at startup in place of the network's constants. Empty by
  default; refused on mainnet unless `allowOnMainnet = true`; a descriptor that does not parse, names a
  malformed id, or names another network stops the client with the key at fault.
- `tools.DeployProtocol`: a deployer that mints the eight protocol tokens, creates the emission, config, fraud
  control and dictionary genesis boxes with the client's own contract code, writes the descriptor, and can
  fund operator keys with ERG and LIT. One transaction per step, each waited for. `DEVNET.md` documents both.

A spec pins every protocol contract's tree on mainnet and testnet (`test/resources/deployment/contract-pins.txt`)
so that neither piece can move a mainnet tree unnoticed; the pins were recorded from the base commit's own
compiler and this branch matches them. A second spec checks that an override reaches the thirteen contracts that
compile an id in and leaves `payout` and the other network unchanged. Reaching any mainnet id compiles nothing: the
one address mainnet has no constant for is pinned too.


## Off by default

`node.deployment.file` is empty in the shipped config. With no override every id getter returns its constant, and
reaching a mainnet id compiles nothing: the one address mainnet has no constant for is pinned, and `DeployPlanSpec`
holds the compiled script to it. The deployer refuses `--network MAINNET` unless `--allow-mainnet` is given, as the
client refuses a mainnet descriptor without `allowOnMainnet`.

## Testing

- `ProtocolContractsDeploymentSpec`: with no override every tree is the pinned one; an override reaches the thirteen
  contracts that compile an id in and leaves `payout` and the other network alone; it is not served from a cache filled
  before it was installed. The pins were recorded from this base commit's own compiler and checked against it.
- `DeploymentSpec`, `DeploymentConfigSpec`: the descriptor's parse, its refusals (malformed id, wrong network, mainnet
  without `allowOnMainnet`), the keys it carries.
- `DeployPlanSpec`: the plan (mint, protocol boxes, descriptor, funding) against a fake node, the self-join a funded
  operator can make with the client's own builders, the refusal of funding below one join, the command line (the
  mainnet guard, `--reward-delay`).
- End to end: on a private chain with 20-second blocks, the deployer deployed the protocol, the client joined the
  collateral queue with its own ERG and LIT, and a block carried the client's genesis transaction. `DEVNET.md` says
  what any private-chain run needs.
