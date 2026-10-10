# Template-hash issue: revised after five seats (2026-10-10)

Filed 2026-10-10 as ergoplatform/explorer-backend#289 (body unwrapped for GitHub; `#2218` written as
`ergoplatform/ergo#2218`). Review record: `posts/seats/template-hash/REVIEW.md`. Banked until a maintainer replies:
the docs PR (direction 1). The comment on ergo#2218 below was posted 2026-10-10
(https://github.com/ergoplatform/ergo/issues/2218#issuecomment-6092648611).

---

**Title:** `ergoTreeTemplateHash` is SHA-256 here and BLAKE2b-256 on the node's index: same name, incompatible values

Explorer: api.ergoplatform.com, explorer-backend master `f811ccd` (sigma-state 6.0.2). Node: 6.1.2 mainnet, height
1,891,228; source read at v6.0.7. Checked 2026-10-09.

**What happens.** The explorer and the node's extra index both serve "boxes by ErgoTree template hash", and both hash
the same bytes, `tree.template` read under version context 3, with different functions:

- explorer: `Sha256.hash(tree.template)` in `deriveErgoTreeTemplateHash`
  ([sigma.scala#L48-L55](https://github.com/ergoplatform/explorer-backend/blob/f811ccd/modules/explorer-core/src/main/scala/org/ergoplatform/explorer/protocol/sigma.scala#L48-L55));
  the request fields of `BoxQuery` and `BoxAssetsQuery` describe it as "SHA-256 hash of ErgoTree template"; the
  `byErgoTreeTemplateHash` route descriptions name no function.
- node: `Algos.hash(tree.template)`, which is `Blake2b256`
  ([IndexedContractTemplate.scala#L55-L65](https://github.com/ergoplatform/ergo/blob/v6.0.7/src/main/scala/org/ergoplatform/nodeView/history/extra/IndexedContractTemplate.scala#L55-L65)),
  as ergoplatform/ergo#2218 specified ("a `blake2b256` hash of the box's `ergoTree.template`") and its OpenAPI
  documents for `/blockchain/box/byTemplateHash/{hash}`.

Both values are 64 hex characters, so nothing in a stored hash says which definition produced it, and a hash from one
service returns an empty result, not an error, on the other.

Both services also fall back to hashing the whole tree when `tree.template` throws: the explorer to SHA-256 of the
input bytes (only after the tree has deserialized; a tree that does not deserialize gets no hash), the node to
BLAKE2b-256 of `tree.bytes`. Neither API mentions this.

**Reproduction.** The EIP-31 Babel fee contract: its constants are segregated, so every token's Babel boxes share one
template.

```
T=d803d601e30004d602e4c6a70408d603e4c6a7050595e67201d804d604b2a5e4720100d605b2db63087204730000d606db6308a7d60799c1a7c17204d1968302019683050193c27204c2a7938c720501730193e4c672040408720293e4c672040505720393e4c67204060ec5a796830201929c998c7205029591b1720673028cb272067303000273047203720792720773057202
echo -n $T | xxd -r -p | sha256sum      # 4e83fa68ef3ed9794bbab5d8799998a9e09fb10a0afe8d1bf928936dfd11c465
echo -n $T | xxd -r -p | b2sum -l 256   # ad6fbaa2fa57169ae9ccf7f548a8abce983e4124ed30d0b73eed5d75225f5574
```

| hash of the same template | explorer `/api/v1/boxes/unspent/byErgoTreeTemplateHash/{h}` (`total`) | node `/blockchain/box/unspent/byTemplateHash/{h}?limit=100` (length) |
|---|---|---|
| SHA-256 `4e83fa68…c465` | 22 | 0 |
| BLAKE2b-256 `ad6fbaa2…5574` | 0 | 22 |

**Expected:** one definition of "template hash", or each API naming its own. **Actual:** one name, two functions, and a
silent empty result across services. We noticed it moving a template query from the explorer to a node's index.

**Possible direction (the explorer maintainers' call).** The node is unlikely to change: it does what #2218 asked and
documents it, and switching would mean reindexing every node's template index.

1. Documentation, now: state SHA-256 on the `byErgoTreeTemplateHash` routes, note the node's BLAKE2b-256 definition,
   and describe the whole-tree fallback. I can send this PR.
2. Optionally, a second field with a name that cannot be mistaken for the first (say
   `ergoTreeTemplateHashBlake2b256`) and matching routes and search parameters, keeping `ergoTreeTemplateHash` as
   SHA-256 for existing clients. That needs a backfill over every output, like the migration that filled the
   current field, so it is a cost the explorer would carry.
3. Separately, a shared helper in sigmastate (an `ErgoTree.templateHash`) would give new code one definition; that is
   a sigmastate issue, not this one.

---

**Comment for ergoplatform/ergo#2218** (the node side needs no change):

> For anyone mixing node and explorer queries: the explorer's `ergoTreeTemplateHash` is SHA-256 of the same template
> bytes, not the BLAKE2b-256 this endpoint uses, so hashes do not carry over between them. Reproduction and proposal:
> ergoplatform/explorer-backend#289.
