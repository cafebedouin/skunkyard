Fidelity seat. You are reviewing a draft forum reply before it is posted. You have read-only tools; work only from the files under the current directory. Do not use the web.

Layout:
- DRAFT.md: the reply under review, to be posted in a public Ergo forum thread as an answer to the thread's open question about deriving post-quantum keys from a wallet seed.
- thread/5371-opening-post.md: the opening post of the thread it answers.
- pqwallet/: the sources the draft rests on: DERIVATION.md, RESULT.md, testnet/RESULT-testnet.md, src/*.ts, test/derive.test.ts, vectors/derive-A.json, vectors/derive-B.json, wotsplus_ref.py, CHARTER.md, package.json.

Assume the underlying work is real. Your question is only: does the document overclaim, mis-cite, or omit a limit its own sources state?

Procedure:
1. Enumerate the load-bearing claims in DRAFT.md (every number, every printed value, every statement of what a test shows or what ran where, every statement about BIP32 / SLIP-0010 / EIP-3 / FIPS 205). Separate them from framing.
2. For each, find the witness in the slice (a printed line in RESULT.md or testnet/RESULT-testnet.md, a value in the vectors, a line in derive.ts or derive.test.ts). Mark: verified (location), could not verify (what is missing), overclaim or mis-cite (quote and correct). A claim that the sources support only partly is an overclaim; say which part.
3. Check that every limit DERIVATION.md and RESULT.md state about this material appears in the draft or is fairly summarized; list any that the draft drops.
4. Check attribution and voice: the draft credits AI tools up front and must not attribute specific findings to specific models beyond what it says; flag any sentence that reads as a claim about who found what.
5. Check fit: does the draft answer the opening post's open item, and is the first paragraph enough for a wallet developer to classify it?

Output plain markdown: one verdict line (post as is / post with the listed fixes / do not post), then a table with columns claim, status, witness or correction, then a short list of what you would cut. Do not rewrite the draft.
