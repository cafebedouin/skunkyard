Review the code in the directory {{SLICE}}. Read {{SLICE}}/README-SLICE.md first. Everything here is public. Work with your file-reading tools only: do not run shell commands and do not use the network.
Two signature verifiers are written in ErgoScript, the contract language of the Ergo blockchain: {{SLICE}}/slhdsa/SlhDsa.es claims to implement FIPS 205 SLH-DSA-SHA2-128s verification (Algorithms 20 and 24), and {{SLICE}}/wotsplus/WotsPlus.es a WOTS+ one-time verifier with a simple tweakable hash. A TypeScript signer and a key-derivation scheme go with them under {{SLICE}}/pqwallet/. The tests run so far are listed in README-SLICE.md and {{SLICE}}/pqwallet/RESULT.md. No value is behind these verifiers yet; the question is whether it could be.
Give a review the author could act on, as a single markdown document:
1. Verdict: the verifiers are ready to guard value, ready with these fixes, or not ready, with one paragraph of reasons.
2. Read SlhDsa.es against FIPS 205 as you know it. Name every place where the script checks less than the standard, more than the standard, or depends on something the harness provides rather than the chain, with file and line, and say what input would exploit it.
3. Read WotsPlus.es and pqwallet/src/wotsplus.ts together. Are they the same construction? Is it sound? Could a signature for one message be turned into a signature for another?
4. Read pqwallet/DERIVATION.md and src/derive.ts. Is the argument about EIP-3's exported extended public key correct? Are the two derivation options sound, and which would you recommend to a wallet, and why?
5. Which tests are still missing before value could sit behind these verifiers? Name them concretely.
Distinguish what you verified in the files from what you infer or know from the standards. Do not pad.
