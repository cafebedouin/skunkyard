Read files only. Do not run any shell command, script, or tool other than reading files; a command request will be denied and you will produce no output.

You are reviewing a draft forum reply before it is posted. Work only from the files under {{SLICE}}. Do not use the web.

Layout of {{SLICE}}:
- DRAFT.md: the reply under review. It will be posted in a public Ergo forum thread as an answer to the thread's open question about deriving post-quantum keys from a wallet seed.
- thread/5371-opening-post.md: the opening post of the thread the reply goes into.
- pqwallet/: the sources the draft rests on. DERIVATION.md (the write-up), RESULT.md and testnet/RESULT-testnet.md (printed test and run output), src/derive.ts and the other TypeScript sources, test/derive.test.ts (the checks), vectors/derive-A.json and derive-B.json (the printed vectors), wotsplus_ref.py (a Python cross-check), CHARTER.md, package.json.

Your job, in this order:

1. Read the sources first, before DRAFT.md: derive.ts, derive.test.ts, the vectors, DERIVATION.md. Write down, before you open the draft, what the code actually derives and what the tests actually show. In particular: what exactly does the xpub-recovery test demonstrate, and what does it not; is option B's child step what the code says it is; do the vector values in RESULT.md match the vectors files.

2. Then read DRAFT.md. For every factual claim in it (a number, a printed value, a statement about BIP32, SLIP-0010, EIP-3, FIPS 205, what a test shows, what ran where), classify it as: verified against the slice (say where), could not verify from the slice (say what would be needed), or wrong or overclaimed (quote the sentence and give the correction). Treat a claim that goes beyond what the test or code shows as an overclaim even if it is plausibly true.

3. Check the draft against the opening post: does it answer what that thread asked, and does it fit as a reply there rather than as a new topic? Would a wallet developer be able to act on it in under a minute of reading the first paragraph?

4. Cryptographic reading, independent of the draft: is the recommended rule B sound as a key-derivation rule (domain separation, hardened-only, independence from the secp256k1 tree, any way a leaf or the root could leak through the code paths you see)? Is anything about option A's weakness, as the draft states it, wrong? Are there standard references (BIP32, SLIP-0010, BIP85, FIPS 205 key generation) that the draft misuses or should cite?

5. What would you cut, and what is missing that a reader of that forum would ask first?

Write the review as plain markdown: a short verdict line, then numbered findings, each with the quoted sentence, the classification, and the evidence location in the slice. Do not rewrite the draft. Do not speculate about the authors or their other work.
