**Title:** "Template hash" means BLAKE2b-256 on the node and SHA-256 on the explorer: same name, incompatible values

**What happens.** The node's extra index and the explorer both offer "boxes by ErgoTree template hash", and both hash
the same thing (the ErgoTree with its segregated constants removed), but with different functions:

- node: `bytesToId(Algos.hash(tree.template))`, BLAKE2b-256 (`IndexedContractTemplate.scala:58`; OpenAPI:
  "blake2b256 hash of an ErgoTree template", `/blockchain/box/byTemplateHash/{hash}`, added in #2219 for #2218)
- explorer: `Sha256.hash(tree.template)`, falling back to SHA-256 of the raw tree bytes when the tree does not parse
  (`explorer-backend/modules/explorer-core/.../protocol/sigma.scala:52`; API docs: "SHA-256 hash of ErgoTree
  template", `/api/v1/boxes/byErgoTreeTemplateHash/{hash}`)

So a template hash taken from one cannot be used with the other, and nothing in either API says the other exists.

**Reproduction** (mainnet, 2026-10-09). The EIP-31 Babel fee contract, the example #2218 was written for, for SigUSD
(`03faf2cb…bf04`):

| hash of the same template | explorer `byErgoTreeTemplateHash` | node `unspent/byTemplateHash` |
|---|---|---|
| SHA-256 `4e83fa68ef3ed9794bbab5d8799998a9e09fb10a0afe8d1bf928936dfd11c465` | 22 boxes | 0 |
| BLAKE2b-256 `ad6fbaa2fa57169ae9ccf7f548a8abce983e4124ed30d0b73eed5d75225f5574` | 0 | 22 boxes |

**Why it matters.** Tools that discover contracts by template (Babel fees, DEX orders, upkeep executors such as the
Lithos client's keyless jobs) have to know which service they are talking to and hash accordingly. We found it when a
job that worked against the explorer found nothing on a node. The explorer's fallback also puts two kinds of value in
one field: a template hash for parseable trees and a whole-tree hash for the rest.

**No standard defines it.** EIP-5 defines the template serialization but no hash; ergo-scala-compiler#11 proposed a
global template id and the reply was that it belongs in sigma as `ErgoTree.templateId`; that was never added.

**Proposal, for maintainers to decide:**
1. Define one canonical template hash in sigmastate (`ErgoTree.templateHash`), BLAKE2b-256 of `template`, as every
   other Ergo identifier (box, transaction and token ids, P2SH) is BLAKE2b-256 and the node already uses it.
2. The explorer adds the canonical hash as a second field and query route, keeping SHA-256 for existing clients
   (breaking it would break tools that have used it for years), and states the fallback for unparseable trees.
3. Both API docs name the other definition until then.

Happy to send the documentation change, or the explorer's additional field, once the direction is agreed.
