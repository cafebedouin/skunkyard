# Pilot: a Winternitz (WOTS+) verifier in ErgoScript, measured

**Claim tested.** A one-time hash-based signature can authorize spending an Ergo box using only existing ErgoTree
operations, within consensus limits.

**What counts against it.** Any of: the verifier's cost exceeds the per-transaction or per-block cost limit for a
practical parameter set; the public key or signature does not fit the register / context-variable / box-size limits;
a needed operation (hash in a loop, byte slicing, folding over a collection) is unavailable or prohibitively priced.

**Plan.**
1. Pick parameters: hash Blake2b256 truncated to n = 16 or 32 bytes; Winternitz w = 4, 16, 256; message = the
   transaction's `messageToSign` digest (or a commitment to OUTPUTS, if the message is unavailable to scripts: check
   what ErgoTree exposes and say so).
2. Write the verifier: per chain, hash the signature element (w-1-digit) times and compare with the public-key
   element; the public key committed in a register as a hash (one 32-byte root), the full key or signature in context
   variables. Variants: WOTS+ with the checksum; plain Lamport as the simplest baseline.
3. Measure with sigma-state's cost accounting (a cost harness over the interpreter, or appkit's reduce):
   cost per parameter set, against the limits read from the node's current parameters (cite them).
4. Execute on a devnet (peeryard can host a two-node network): a box locked by the script, spent with a valid
   signature (accepted) and with a forged one (rejected); record transaction size and cost.
5. Report: a table of parameter sets (n, w) x (cost, signature bytes, fits?) and the yes/no answer with the limiting
   factor, plus the scripts.

**Known limits to state, not solve, in the pilot:** one-time use (key reuse breaks WOTS); binding the signature to
the spending transaction (what message a script can see); a stateful many-time scheme (XMSS/SPHINCS+) is out of
scope until the one-time cost is known.
