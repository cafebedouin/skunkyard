I've read the draft and the evidence. One thing the draft gets wrong: the node has the same fallback it blames on the explorer. Here is the maintainer response.

---

# Maintainer response: "Template hash" BLAKE2b vs SHA-256

**As I'd post it:**

> Thanks, the repro is clear and I can see the mismatch. On the node side this is working as intended. #2218 asked for `blake2b256(ergoTree.template)`, #2219 did that, and the OpenAPI spec says "blake2b256 hash of an ErgoTree template". So there's nothing for the node to fix, and I won't change the node's hash: every indexed node would have to reindex. One correction: the node has the same fallback you describe for the explorer. If `tree.template` throws, it indexes `Algos.hash(tree.bytes)` (`IndexedContractTemplate.scala:63`). So "two kinds of value in one field" is true of both services, not just the explorer. The explorer's SHA-256 is the odd one out, and that belongs in explorer-backend. Please send a PR there that fixes the API descriptions. If you want, open a second issue for a BLAKE2b field and route, but that means a migration that rewrites a column over every output, so the explorer maintainers have to agree to it. A canonical `ErgoTree.templateHash` belongs in sigmastate-interpreter; greenhat said the same on ergo-scala-compiler#11. If sigma adds it, the node will switch to calling it, and that changes no values. I'm closing this here and labelling it `docs`. Please link the explorer and sigma issues when you open them. Also, #2218 should have been closed by #2219. I'll close it now.

## 1. Right repository?
No. The node does what #2218 specified and what its OpenAPI says (`openapi.yaml` lines ~19 and ~71 of the excerpt). Every action in the proposal falls on someone else:
- **explorer-backend:** fix the docs (`BoxQuery.scala:37` and `BoxAssetsQuery.scala:19` only say "SHA-256 hash of ErgoTree template") and optionally add a BLAKE2b field.
- **sigmastate-interpreter:** add `ErgoTree.templateHash`.
- **eips (optional):** an EIP that defines the hash, so that sigma-rust, Fleet and AppKit agree on it.

File it in explorer-backend and sigmastate-interpreter, with cross-links. At most, comment on #2218 in the node repo. Don't open a node issue.

## 2. Actionable as written?
Not in this repo. I'd close it as working-as-intended with a `docs` label and point the author to explorer-backend. The reproduction is good. The problem is that it asks the node maintainer to settle a policy question ("for maintainers to decide") that the node can't settle alone.

## 3. The proposal
- **`ErgoTree.templateHash` in sigma, BLAKE2b-256: yes.** It's cheap: one method, no consensus impact. It matches box, tx and token ids, and it matches the values the node already indexes. Two things need deciding in sigma: the fallback for trees whose template can't be extracted (I'd return `Option` or throw rather than silently hash the whole tree), and which `VersionContext` to use (the node pins `withVersions(3,3)`). Cost: a sigma release, plus ports to sigma-rust and the JS SDKs.
- **Node switches to SHA-256: no.** Every extra-index node would have to reindex, `/byTemplateHash` would break for current users, and the node would move away from every other Ergo identifier.
- **Explorer adds a BLAKE2b field and route:** this is the right fix if anyone wants interoperability. The cost is a backfill migration over all outputs (like `RegistersAndConstantsMigration`), a new index, and DB growth on the explorer's side. The explorer team has to make that call.
- **Docs only:** almost free and fixes the immediate confusion. Do this first whatever else happens.

## 4. What I'd ask for first
- A check of the node's own fallback (`IndexedContractTemplate.scala:55–64`). The draft says the fallback only happens on the explorer.
- Whether either service ever hits its fallback on mainnet. A count of trees where `template` throws would show whether the fallback is a real problem or only a theoretical one. The explorer's `Try` only runs after `deserializeErgoTree` has succeeded (`sigma.scala:49–52`). If the tree doesn't parse, the whole derivation fails. So the comment "if tree can't be parsed" is wrong, and that fallback path is narrower than the draft says.
- What happens to trees that aren't constant-segregated. #2218 proposed skipping them, and the comment on #2218 claims the node does, but neither `hashTreeTemplate` nor the `ExtraIndexer` excerpt shows a skip [UNVERIFIED]. If the node indexes them under a hash of a template that still contains its constants, that matters more to me than SHA vs BLAKE.
- Whether the explorer maintainers will accept the migration.

## 5. What would waste my time
- It's filed against the one component that is correct, and then asks me to arbitrate between two other repos.
- The fallback criticism is one-sided, as noted above. Once I spot that, I stop trusting the rest of the draft.
- "Upkeep executors such as the Lithos client's keyless jobs" reads like a plug and isn't needed. "Tools have to know which service they're talking to" is enough.
- The bold section headings plus a three-step numbered proposal read like a template, maybe written by an agent. Length is fine (~35 lines), and the tone is polite.
- The repro queries a public node at a raw IP. That's fine, but say which node version you read the source from (6.0.7) and which you tested (6.1.2), and that the hash code is the same in both.

## 6. The one change
Re-target it. Make it an explorer-backend issue (docs fix, and optionally a BLAKE2b field) plus a sigmastate-interpreter issue for `ErgoTree.templateHash`, and fix the fallback claim so it covers both services. If it must touch the node repo, leave a two-line comment on #2218 that links those issues.

---

I couldn't save this to the plan file because I only had read and search tools in this session, so the response is above.
