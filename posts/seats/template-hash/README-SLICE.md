# What is here

`ISSUE-DRAFT.md` is a draft GitHub issue, not yet filed, meant for the Ergo node repository (ergoplatform/ergo) and
linking the explorer backend (ergoplatform/explorer-backend). It says the node and the explorer define "template
hash" with different hash functions.

`evidence/` holds the public sources the draft relies on, copied verbatim (files named `*.linesA-B` are excerpts of
those lines):

- `node/`: the Ergo node 6.0.7 extra index (`IndexedContractTemplate.scala`, `ExtraIndexer.scala`,
  `IndexedErgoAddress.scala`), its HTTP routes (`BlockchainApiRoute.scala`) and OpenAPI spec (`openapi.yaml`), and
  where `Algos.hash` comes from (`Algos-ergo-core.scala` extends `ErgoAlgos`, `ErgoAlgos.scala` from
  sigmastate-interpreter v6.0.6).
- `explorer/`: ergoplatform/explorer-backend (master, cloned 2026-10-09): the template-hash derivation
  (`sigma.scala`), the API descriptions (`BoxQuery.scala`, `BoxAssetsQuery.scala`), the routes
  (`BoxesEndpointDefs.scala`), and the migration that backfilled the field.
- `threads/`: ergo#2218 (the issue that asked for template queries), ergo#2219 (the PR that added them),
  ergo-scala-compiler#11 (a proposal for a global template id), each with its comments, fetched 2026-10-09.
- `eips/`: EIP-5 (contract templates) and EIP-31's contract-template section.
- `repro/`: a self-contained script and its output from 2026-10-09 against the public explorer and a public mainnet
  node (6.1.2).

Nothing here needs to be run. Judge from the files.
