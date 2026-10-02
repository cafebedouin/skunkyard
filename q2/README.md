# Q2 Pilot: ErgoScript Lamport and Winternitz (WOTS) Verifiers

This directory contains executable ErgoScript verifiers and measurement harnesses for hash-based signatures in ErgoTree, answering Question Q2 from `SCOPE.md` and `PILOT-Q2.md`.

## Verifier Scripts

- `lamport.es`: Lamport one-time signature verifier written in ErgoScript using existing operations (`blake2b256`, collection slicing, `forall`, context variables, and register `R4`).
- `wots.es`: Winternitz one-time signature (WOTS) verifier in ErgoScript with full checksum verification and iterative hash chaining (`fold`, `forall`, `blake2b256`).
- `wots-compact.es`: the same WOTS verifier without the public key in the transaction (6.0.x only; see "Compact verifier" below).
- `wots-constant.es`: the compact verifier with the public-key commitment compiled in as a constant instead of read from R4 (6.0.x only; see "Per-key address verifier" below).

Both scripts commit to the public key as a single 32-byte Blake2b256 hash in register `R4`, with the signature and full key material provided in context extension variables. Both scripts verify a message digest binding `SELF.id` and all transaction output candidates (`OUTPUTS.flatMap(b => b.bytesWithoutRef)`), binding the one-time signature strictly to the spending transaction.

## Initial 5.0.2 Measurement Table

Original baseline table from `sigma-state_2.12:5.0.2`:

```
scheme n w accepted_valid rejected_forged cost sig_bytes key_bytes
lamport 16 2 true true 6283 2048 4096
lamport 32 2 true true 12381 8192 16384
wots 16 4 true true 10451 1088 1088
wots 16 16 true true 19582 560 560
wots 16 256 true true 123870 288 288
wots 32 4 true true 20327 4256 4256
wots 32 16 true true 37955 2144 2144
wots 32 256 true true 232508 1088 1088
```

## Running the Pilot

Execute from the repository root with the target `sigma-state` version:

```bash
bash q2/run.sh 5.0.2
bash q2/run.sh 6.0.x
```

Both targets are pinned via Coursier (`scala-library:2.12.18`, `slf4j-nop:1.7.36`, and `sigma-state_2.12:5.0.2` or `sigma-state_2.12:6.0.7`).

---

## Measured Output: sigma-state 5.0.2

Printed output from `bash q2/run.sh 5.0.2`:

```
# Fixed seed for random messages: 424242
# Lamport message dependence analysis (20 messages):
# Cryptographic hash operations in Lamport are strictly constant: exactly 8*n Blake2b256
# hashes are evaluated regardless of message bits. A minor variance (~1%) arises from
# ErgoScript arithmetic (sign-extension conditional on negative byte values: b < 0).
# Lamport n=16 20 message costs: min=6219 median=6258 max=6296 (all: 6283, 6232, 6219, 6271, 6258, 6245, 6232, 6219, 6283, 6271, 6271, 6296, 6258, 6232, 6271, 6258, 6271, 6219, 6245, 6258)
# Lamport n=32 20 message costs: min=12381 median=12471 max=12509 (all: 12381, 12420, 12471, 12484, 12484, 12433, 12471, 12445, 12471, 12471, 12509, 12471, 12458, 12497, 12484, 12471, 12497, 12458, 12509, 12484)

sigma scheme n w accepted_valid rejected_forged cost min median max worst sig_bytes key_bytes tx_bytes fits_block fits_relay
5.0.2 lamport 16 2 true true 6283 6219 6258 6296 6296 2048 4096 6455 true true
5.0.2 lamport 32 2 true true 12381 12381 12471 12509 12509 8192 16384 24888 true true
5.0.2 wots 16 4 true true 10451 10320 10431 10538 10674 1088 1088 3053 true true
5.0.2 wots 16 16 true true 19582 19495 19778 20036 20385 560 560 1965 true true
5.0.2 wots 16 256 true true 123870 122189 123870 125778 128556 288 288 1837 true true
5.0.2 wots 32 4 true true 20327 20261 20394 20539 20880 4256 4256 9525 true true
5.0.2 wots 32 16 true true 37955 37572 37869 38227 39077 2144 2144 5175 true true
5.0.2 wots 32 256 true true 232508 230374 233187 235688 242919 1088 1088 3458 true true
5.0.2 dlog 32 1 true true 403 403 403 403 403 56 33 138 true true

# Baseline proveDlog(pk) spend: cost = 403, tx_bytes = 138, sig_bytes = 56, key_bytes = 33, fits_block = true, fits_relay = true
```

---

## Measured Output: sigma-state 6.0.x (mainnet)

Printed output from `bash q2/run.sh 6.0.x` (`sigma-state 6.0.7`, `activatedScriptVersion = 3`, ErgoTree v0):

```
# Fixed seed for random messages: 424242
# Lamport message dependence analysis (20 messages):
# Cryptographic hash operations in Lamport are strictly constant: exactly 8*n Blake2b256
# hashes are evaluated regardless of message bits. A minor variance (~1%) arises from
# ErgoScript arithmetic (sign-extension conditional on negative byte values: b < 0).
# Lamport n=16 20 message costs: min=6219 median=6258 max=6296 (all: 6283, 6232, 6219, 6271, 6258, 6245, 6232, 6219, 6283, 6271, 6271, 6296, 6258, 6232, 6271, 6258, 6271, 6219, 6245, 6258)
# Lamport n=32 20 message costs: min=12381 median=12471 max=12509 (all: 12381, 12420, 12471, 12484, 12484, 12433, 12471, 12445, 12471, 12471, 12509, 12471, 12458, 12497, 12484, 12471, 12497, 12458, 12509, 12484)

sigma scheme n w accepted_valid rejected_forged cost min median max worst sig_bytes key_bytes tx_bytes fits_block fits_relay
6.0.x lamport 16 2 true true 6283 6219 6258 6296 6296 2048 4096 6455 true true
6.0.x lamport 32 2 true true 12381 12381 12471 12509 12509 8192 16384 24888 true true
6.0.x wots 16 4 true true 10431 10332 10432 10543 10675 1088 1088 3063 true true
6.0.x wots 16 16 true true 19582 19495 19778 20036 20385 560 560 1965 true true
6.0.x wots 16 256 true true 124507 122147 123914 125553 128556 288 288 1849 true true
6.0.x wots 32 4 true true 20417 20213 20407 20552 20880 4256 4256 9535 true true
6.0.x wots 32 16 true true 37955 37572 37869 38227 39077 2144 2144 5175 true true
6.0.x wots 32 256 true true 233144 230829 233187 235463 242920 1088 1088 3470 true true
6.0.x dlog 32 1 true true 403 403 403 403 403 56 33 138 true true

# Baseline proveDlog(pk) spend: cost = 403, tx_bytes = 138, sig_bytes = 56, key_bytes = 33, fits_block = true, fits_relay = true
```

Since branch `q2-compact` the same command prints two further blocks after these lines; they are reproduced in the
next section. The lines above are unchanged byte for byte.

---

## Compact verifier (no public key in the transaction)

`wots.es` takes the full public key (the concatenated chain ends) in context variable 1, checks
`blake2b256(pk) == R4` and compares each recomputed chain end with a slice of it. `wots-compact.es` drops
variable 1: it recomputes every chain end from its signature element with the same fold, concatenates the chain ends
in chain order and checks `blake2b256(concat) == R4`. Message binding, checksum, parameters and compile-time
constants are those of `wots.es`; R4 is the same value (`Runner6.wotsPk` already returns the concatenated chain
ends, so the key derivation, signing and seeds of the `wots` rows are reused unchanged). `key_bytes` is 0 because
nothing key-related is sent; `tx_bytes` is the serialized spending transaction with only variable 0. The rows are
measured in `q2/Runner6.scala` (`runWots(n, w, WOTS_COMPACT)`); the 5.0.2 runner is unchanged and has no such rows.

Command (repository root), run twice with identical output:

```bash
bash q2/run.sh 6.0.x
```

Printed after the table above:

```
# Compact verifier (q2/wots-compact.es): no public key in the transaction; R4 = blake2b256(concatenated chain ends)
sigma scheme n w accepted_valid rejected_forged cost min median max worst sig_bytes key_bytes tx_bytes fits_block fits_relay
6.0.x wots_compact 16 4 true true 10076 10014 10110 10200 10351 1088 0 1947 true true
6.0.x wots_compact 16 16 true true 19623 19339 19611 19857 20218 560 0 1377 true true
6.0.x wots_compact 16 256 true true 124420 122103 124010 126101 128468 288 0 1533 true true
6.0.x wots_compact 32 4 true true 20045 19875 20036 20169 20517 4256 0 5251 true true
6.0.x wots_compact 32 16 true true 37820 37364 37685 38128 38893 2144 0 3003 true true
6.0.x wots_compact 32 256 true true 232004 230960 233234 235593 242825 1088 0 2354 true true

# Public key variable (context variable 1) in the original wots spending transaction: bytes and share of tx_bytes
scheme n w pk_var_bytes tx_bytes pk_var_share compact_tx_bytes
wots 16 4 1092 3063 0.3565 1947
wots 16 16 564 1965 0.2870 1377
wots 16 256 292 1849 0.1579 1533
wots 32 4 4260 9535 0.4468 5251
wots 32 16 2148 5175 0.4151 3003
wots 32 256 1092 3470 0.3147 2354
```

`pk_var_bytes` is the serialized size of the original spending transaction minus the size of the same transaction
with context variable 1 removed (the key bytes plus the variable's id, type and length bytes). `compact_tx_bytes`
is the `wots_compact` row's `tx_bytes`; it differs from `tx_bytes - pk_var_bytes` by a few bytes because the
output box in the harness carries the compiled tree, and the compact tree is a different size.

**Formulations tried.** Four ways to build the concatenation, all with the same chain-end fold, measured with the same
harness (`bash q2/compact-variants/run.sh`, which compiles `q2/Runner6.scala` and
`q2/compact-variants/Variants.scala` with the pins of `run.sh`, then passes the same four scripts through the 5.0.2
compiler with `q2/compact-variants/Compile5.scala`, compile only):

- `fold.es`: `chainIndices.fold(Coll[Byte](), { (acc, c) => ...; acc ++ computedEnd })`
- `map-flatmap.es`: `chainIndices.map({ c => ...; computedEnd })` then `.flatMap({ (e: Coll[Byte]) => e })`
- `map-fold.es`: `chainIndices.map(...)` then `.fold(Coll[Byte](), { (acc, e) => acc ++ e })`
- `wots-compact.es` (kept): `chainIndices.flatMap({ c => ...; computedEnd })`

```
# q2/compact-variants/fold.es
6.0.x wots_compact 16 4 true true 10482 10336 10439 10556 10683 1088 0 1961 true true
6.0.x wots_compact 16 16 true true 19614 19517 19763 20009 20369 560 0 1391 true true
6.0.x wots_compact 16 256 true true 123673 121948 123856 125764 128540 288 0 1547 true true
6.0.x wots_compact 32 4 true true 20882 20715 20852 21009 21325 4256 0 5265 true true
6.0.x wots_compact 32 16 true true 37961 37515 37961 38269 39158 2144 0 3017 true true
6.0.x wots_compact 32 256 true true 232964 230603 233190 236919 242922 1088 0 2368 true true
# q2/compact-variants/map-flatmap.es
6.0.x wots_compact 16 4 true true 10163 10069 10173 10355 10423 1088 0 1954 true true
6.0.x wots_compact 16 16 true true 19551 19378 19638 19920 20257 560 0 1384 true true
6.0.x wots_compact 16 256 true true 123806 122351 123849 125897 128490 288 0 1540 true true
6.0.x wots_compact 32 4 true true 20161 20038 20170 20356 20655 4256 0 5258 true true
6.0.x wots_compact 32 16 true true 37520 37421 37743 38076 38964 2144 0 3010 true true
6.0.x wots_compact 32 256 true true 234769 230770 233130 235631 242863 1088 0 2361 true true
# q2/compact-variants/map-fold.es
6.0.x wots_compact 16 4 true true 10397 10318 10422 10543 10673 1088 0 1963 true true
6.0.x wots_compact 16 16 true true 19697 19548 19745 20018 20365 560 0 1393 true true
6.0.x wots_compact 16 256 true true 124900 122174 123855 126808 128539 288 0 1549 true true
6.0.x wots_compact 32 4 true true 20781 20644 20819 20968 21303 4256 0 5267 true true
6.0.x wots_compact 32 16 true true 38027 37607 37950 38309 39148 2144 0 3019 true true
6.0.x wots_compact 32 256 true true 234415 229781 233144 235278 242919 1088 0 2370 true true
# q2/wots-compact.es
6.0.x wots_compact 16 4 true true 10076 10014 10110 10200 10351 1088 0 1947 true true
6.0.x wots_compact 16 16 true true 19623 19339 19611 19857 20218 560 0 1377 true true
6.0.x wots_compact 16 256 true true 124420 122103 124010 126101 128468 288 0 1533 true true
6.0.x wots_compact 32 4 true true 20045 19875 20036 20169 20517 4256 0 5251 true true
6.0.x wots_compact 32 16 true true 37820 37364 37685 38128 38893 2144 0 3003 true true
6.0.x wots_compact 32 256 true true 232004 230960 233234 235593 242825 1088 0 2354 true true
q2/compact-variants/fold.es: compiles under 5.0.2
q2/compact-variants/map-flatmap.es: rejected by the 5.0.2 compiler: scalan.Base$StagingException: Unsupported lambda in flatMap: allowed usage `xs.flatMap(x => x.property)`
q2/compact-variants/map-fold.es: compiles under 5.0.2
q2/wots-compact.es: rejected by the 5.0.2 compiler: scalan.Base$StagingException: Unsupported lambda in flatMap: allowed usage `xs.flatMap(x => x.property)`
```

The `flatMap` form has the lowest `worst` for every (n, w) and the smallest tree (lowest `tx_bytes`), so it is the one
kept. Its median is not the lowest everywhere (n=32 w=256: 233234 against 233130 for `map-flatmap.es`). The two
`flatMap` forms with a computed body compile with the sigma-state 6.0.7 compiler only: the 5.0.2 compiler rejects
them (last four lines above); `fold.es` and `map-fold.es` compile under both. The kept form has been evaluated only in this interpreter harness (`activatedScriptVersion = 3`,
ErgoTree v0), not on a node.

---

## Per-key address verifier (commitment as a constant)

`wots-constant.es` is `wots-compact.es` with one change: the 32-byte commitment blake2b256(concatenated chain ends)
is not read from `SELF.R4` but is the compile-time constant `pkCommitment: Coll[Byte]`, substituted into the
script the way `n`, `w`, `l1`, `l2`, `chainIndices` and `steps` are; the script reads no register. Every key
therefore compiles to its own ErgoTree and P2S address, and a box is locked by sending to that address with no
registers. The rows are measured in `q2/Runner6.scala` (`runWots(n, w, WOTS_CONSTANT)`) with the same keys, seeds,
messages and worst-case substitution as the `wots_compact` rows; the harness boxes carry no register.
`Runner6.wotsConstantTree(n, w, commitment)` builds the per-key tree (`ErgoTree.fromProposition`, which segregates
constants: header `0x10`).

Command (repository root), run twice with identical output (and the lines printed before this block unchanged from
the two blocks above, byte for byte):

```bash
bash q2/run.sh 6.0.x
```

Printed after the public-key-variable table:

```
# Per-key address verifier (q2/wots-constant.es): commitment blake2b256(concatenated chain ends) compiled in as the constant pkCommitment; no register
sigma scheme n w accepted_valid rejected_forged cost min median max worst sig_bytes key_bytes tx_bytes fits_block fits_relay
6.0.x wots_constant 16 4 true true 10113 9965 10105 10201 10349 1088 0 1978 true true
6.0.x wots_constant 16 16 true true 19584 19360 19608 19941 20215 560 0 1408 true true
6.0.x wots_constant 16 256 true true 123781 121873 123781 126098 128466 288 0 1564 true true
6.0.x wots_constant 32 4 true true 19966 19897 20029 20185 20513 4256 0 5282 true true
6.0.x wots_constant 32 16 true true 37727 37240 37692 38039 38890 2144 0 3034 true true
6.0.x wots_constant 32 256 true true 234319 230320 233090 235590 242822 1088 0 2385 true true

# Per-key trees for two keys (key 1 = the row's key, seed 424242 + 1000n + w; key 2 = seed + 1); mainnet P2S addresses
n=32 w=16 compact_tree_bytes=809 constant_tree_bytes=840,840 header=0x10,0x10 constants=79,79
n=32 w=16 key1 commitment=bf20685942f79bff2dc6de27bfbea3c021b129d67c2e3699f45885a402f7562a template_hash=505f48e5aa20f46f9c3ce675befc90a218de3807d136810b17bcd773ae955f55 tree_hash=80cf8355778b4dbd375ccce31f5b0878e4e66350776d067fe501169aa146e394
n=32 w=16 key1 address_chars=1153 address=eJW5c9ybRYXreviGggg2ZkNcwBHuiLtq5L5MJUuk6ogCwC9q8H95XXaV8Ujxbbe7xJQ9optP3GbR7mg4ogfy3j16PSW78KRimMgBGsYChNKXeZ5aZbrkMH3F6BGxzEnhMNq4ukjnmiXWLQ59T713G43AtJVdbPeoWNoXztkEgyr8FEbTAD4efyyvC3TbYEekzRPXBR764Ytj7Gis7B2N1akKjfwX7NrDFAgeNw6aaToZobwvz9b2TZaPsP6M1EWodqU3WFz7mKDdU58sHzFBwTHS6Wv8i7LGWPfiEcc9EMwqe5garCWnhs5GRCnxMkL7KXXUpWfdkv1yH97GNTC9bFM48Va73TiNHZ19g9t7fLWBT7QDvLuuhbuFob4LmkzuzfHHHVzx6Sdada71J72euu74hfAKAjzDT5NwNoxs6hWkDBAnGjAs9HsR2gg62cNNUgCKqDThszAmd6vJL5X71wukYHQ4XuL6Aes3tbCt53LamgfNGwkx2414zi8zRyFnM61Btd7wezGeUL9mk5T6QHQvzi3zi4Qi4yYzRg3JrvyDurn8NhsxGLYW2ytwhChoL4zrBK9p68J5ShtoCD6xs7QHprBpeCVFMKXqn57NFbAaxzXJMYZDusrxZFFZxPvVgs7sbZ6CFzGdWGih7ujyadVLQQzVvf1gPDQ2DAcArHgiUQ5Whz1QLd6UNQdvGo8nbfy6t8czkUeChz7V5JdaAQhvyDnQgS5SoPPsuD2qC6f19j8dFR6nGiH2yhkab73SYMHc4PmpceitYuY2ShRDuwPnmXW8FoVxUBeTnivwoEVSMtxkuXXoWbCEEiwVd1PfQWtWWdjZsoCuEMXpB54NjKZ3YKwbe41Bu6yU5iFEkscAtXs4nBcgsbciy2UezumTEUdW3iaoNAuompzP233PLN26wk7Y9ZvYT8uNeUBG8NjttLE1sZDNhT7s7TTZ63o9upAccgCpo9VZSS9KWVDJHxyHgBppsgmwR8Q5pGmdYBSmghDAGmk4DUFiWhuDkruY5DTDbzd829xG9UKfgXeNpxmUwtsTEgLfUKuS6wjFFMNx17tDz4y51G7iaYbXfsrNhY4p4gmPjmpyTq6EbZMQD5UNYfF8GGnXnJgJZUtZx5o1W4NGZmdDdEADbmhtFQGwj
n=32 w=16 key2 commitment=ea63e62b5c6315a3d6d013cb266749f5f915040c9a0fcc74f8ca10d642b278b8 template_hash=505f48e5aa20f46f9c3ce675befc90a218de3807d136810b17bcd773ae955f55 tree_hash=73294f70a95689d300858762a524d3da38130b3841372409a9c2595042addeae
n=32 w=16 key2 address_chars=1153 address=eJW5c9ybRYXreviGggg2ZkNcwBHuiLtq5L5MJUuk6ogCwC9q8H95XXaV8Ujxbbe7xJQ9optP3GbR7mg4ogfy3j16PSW78KRimMgBGsYChNKXeZ5aZbrkMH3F6BGxzEnhMNq4ukjnmiXWLQ59T713G43AtJVdbPeoWNoXztkEgyr8FEbTAD4efyyvC3TbYEekzRPXBR764Ytj7Gis7B2N1akKjfwX7NrDFAgeNw6aaToZobwvz9b2TZaPsP6M1EWodqU3WFz7mKDdU58sHzFBwTHS6Wv8i7LGWPfiEcc9EMwqe5garCWnhs5GRCnxMkL7KXXUpWfdkv1yH97GNTC9bFM48Va73TiNHZ19g9t8he2FY6zLwB4MSAKSaRBALkNuk1sG3NmT8EVADx5HbqKbrhip2vqTDgDi6cLHxL3n87ZaF22AbC72m7Qon4PuWQtpZXWqJfbyt8UPYQtKGPq7Wz9qgSAZjDfPqYBRACGbnPnhxyLvFAVBR3ReUGr7PitKfFGaed7EUzkW1iLikid9bZ3YdmavtQvVCyNMfn3LW5aLNBbAn17WHRW9sypYNYbB5MUx36AQmbENSRGidqCY9qTdCa952dQuNJun8dY6E59pQ8rZEsseBuSgEdSM7Vkdxtoyiz5KYvWrn11PM8mmwE9oHV7e3CMTgLtknuv5ER8p2WEw9sPLpZCTdKDjwhd1zrYHmK2a4bhuZhwdNKRAFEeSqMZ6FHrFAgwxwvHiZZa8J8bburWqPcbZXLXUevZLwc13B52sg3zJHmFVPyiy6uY5Wj9rzUbYcvERKjBW5592JKJhi9wk9XrVGyLci3Z1SbHEaygZnDtEshmsMW9xrus1eFLcS14vPF596WNkQ6oC33zq4eMjd3fP1wusmHyEPT1U4b3hoH67Pz97yXbdysTh5AoLi5mW1gdi4mUDpeYx8ALJ96gxk2jdUzZykGpvkpK2CYwBZBw7JXwdeQ2jtD2cc6KaY8EiZu4522b4j8KhZqzF5uVuYwtsVHMAk6wx5tS3QFZD3u62X47zf5UGwfURy2QEPh1dXuhnnjkxSHf6hsa1qZFLdEorK5vjEEbgxZzUTEnc75ZosnpGSVFySGAwVtUSutropRDgU1Yy7MP764kwXfTnXqW2yqsqq7NE5
n=32 w=16 templates_equal=true trees_equal=false addresses_equal=false
n=32 w=256 compact_tree_bytes=1216 constant_tree_bytes=1247,1247 header=0x10,0x10 constants=83,83
n=32 w=256 key1 commitment=5bd3d045fe84cdfc744a6ad23185789d8fcb1928c03d35bba2965649583f8cfd template_hash=0ccd520e5d1f2b54eeda1ca93d3164582b6d1b045f5c8f65a30acbdc4aa4762a tree_hash=0236a2c0d3af7226061a100af756ebd029b6247e1cc88a4099dc530fd7ca1677
n=32 w=256 key1 address_chars=1709 address=KB4koF224tkDbqQ7SSHsSdwBisVTUWrB6HgEzzF9Ey4F6U4ESiundr7r8EaAfiKTFu511SAHnQauzxMXR3t3uTGmDya7d4bJqgmiHnHajSYJCK2B1wDBNqEG8grzJcvrhzgcNCof4w6ux1CN1mRPETxis5JDVRFAqf4fQw791NnmfiT8YMkyhc5JHrFCXxvPPoYeBVVUUN3WqjnxvLrECWh7knjur8n7CKtCN2he13Gjf3Sx2TFyb8d2VoJpdu1BjvCQJ3gm794uwvyhaJcThfgxae2ffjUsLoMdr2QSLetB2b5wLvQUhFwiKJQgeRKGP9QWTg1WvAhq3eShHvQ4Du6QwGP9HfspbQ7wCjhraEB4X3JDzzyZasWqh8sDZXzSpednv8sjQXBhQJC1S7rsaLmyYKtc76uPgLtg6BCZQxaBhH8rX8Qi2ADEW1aPEnkafUyDJqYoYbX8FaByZ5pVJbcqeK2D3bAEsn9AhEz13J1oPcGdDPAB9aaWUkbqShRWq799dAPuVdRXiJbJLxc1uPrwLBcgNf2X8ZoNr5Pce6WoHqRk21Rmk7NfvxceiuCJq1HhYn9dDqcLyxPgTWCbDWTfTasPcqHAAw1X4Kiy4XYXUq4mouPRUeL7Kwr6ZNZQfYsS9VgR1yPsFR4gpXw35yqiigAMub1rY1MbY5GQpPrhLJTnPx2vfMw7QUbpVuBPNnWYy4dgE7DfuGN9rFCaxKTf1uiV9H8PQFU5pWVYbWFw3vvGoQAf7VMUtCJxRDSjgPezLewCqmAoQms8k3w66sruMXAL4V8A3PHRNLaLEP6vQdxARwdboYprDxBg3atvGEVYQ18xmKrsaAXsUf6fzVrkYGvzpuA3kXT7FPhrs6Zb4sMwEqujaU6HrAhszzEGF7NaTa5fjVpCPyYgfcdWTKonzchhJ8pdoCTFjxQU1emeTpw3GE7YG9xZGbjEZjfVaFnM5fndA6TC7ebxNHFuEtp6FPY9yj8FzM82bB2urDRepev6gdcNdnEKLtebrhynXKMNxdteidsWGFJ7XGP2pCz6Nx92bP96aszYhuJ12ta8MVxZRENCH6mixADL7nLRUzVYhzuAp8evbbXdTpsdS429uHVQfDbaQWgSAop8n5fMShef9sUQpKUvNJHW6b4feLJzXxLUTkkU3GhU1nffKaxFk6ZmpVAktCopRz5MtEg4BJr4NCYN2VSmPu2izQc1X21uLCyZdZXogd27no47Mjbwk7PARAbdifvcJHcHkCdEcnvaSuuVdhQNhXW6oZ5rBid4ikSzoRStSxhamnuFefTZSZUPPEwieUanGsLGHsitHgw1ffjVTdBvKbMxKb7o9gd7RR2w5E2yesQjnBNBNnGWYtAWnsA4whbaFDSKLDe2644cY3bzXYaVPfjaFhTLD81LhkBpPRf1y4B7RRMbPaQBSm6huNCWFhkigXG4J8L656Kc2TZnWhvQ5wLgLKHytmBg62LpEwzQnjHLUd7xwJEQnK7BY5U9Q6RRHkxp6TNcj74Ses9kqTFCEGUPvZZDty64ZoorSdJRKHMYeuBW98XRCLAiadnGMQFeQzbQXUBtKasmhVUNuA5ovJBMKEbqjTx5YPBprnjeaGKZuh2kvuBtTHkXv8v6Jrc9NmQcnLYVDznanNYW1givqj97QLmawnaeWfn7MxNUKDu6BNkvcCqq1vS5LapZ8FmBdp1xpXWD1
n=32 w=256 key2 commitment=8306acd02ae55a389a9d7230ec6aae9270d15010eda353d928fae2a45b79de62 template_hash=0ccd520e5d1f2b54eeda1ca93d3164582b6d1b045f5c8f65a30acbdc4aa4762a tree_hash=dd00889c132a96e3adfbac2ff92d1ca712da772be54df0bbd581e829010b2d23
n=32 w=256 key2 address_chars=1709 address=KB4koF224tkDbqQ7SSHsSdwBisVTUWrB6HgEzzF9Ey4F6U4ESiundr7r8EaAfiKTFu511SAHnQauzxMXR3t3uTGmDya7d4bJqgmiHnHajSYJCK2B1wDBNqEG8grzJcvrhzgcNCof4w6ux1CN1mRPETxis5JDVRFAqf4fQw791NnmfiT8YMkyhc5JHrFCXxvPPoYeBVVUUN3WqjnxvLrECWh7knjur8n7CKtCN2he13Gjf3Sx2TFyb8d2VoJpdu1BjvCQJ3gm794uwvyhaJcThfgxae2ffjUsLoMdr2QSLetB2b5wLvQUhFwiKJQgeRKGP9QWTg1WvAhq3eShHvQ4Du6QwGP9HfspbQ7wCjhraEB4X3JDzzyZasWqh8sDZXzSpednv8sjQXBhQJC1S7rsaLmyYKtc76uPgLtg6BCZQxaBhH8rX8Qi2ADEW1aPEnkafUyDJqYoYbX8FaByZ5pVJbcqeK2D3bAEsn9AhEz13J1oPcGdDPAB9aaWUkbqShRWq799dAPuVdRXiJbJLxc1uPrwLBcgNf2X8ZoNr5Pce6WoHqRk21Rmk7NfvxceiuCJq1HhYn9dDqcLyxPgTWCbDWTfTasPcqHAAw1X4Kiy4XYXUq4mouPRUeL7Kwr6ZNZQfYsS9VgR1yPsFR4gpXw35yqiigAMub1rY1MbY5GQpPrhLJTnPx2vfMw7QUbpVuBPNnWYy4dgE7DfuGN9rFCaxKTf1uiV9H8PQFU5pWVYbWFw3vvGoQAf7VMUtCJxRDSjgPezLewCqmAoQms8k3w66sruMXAL4V8A3PHRNLaLEP6vQdxARwdboYprDxBg3atvGEVYQ18xmKrsaAXsUf6fzVrkYGvzpuA3kXT7FPhrs6Zb4sMwEqujaU6HrAhszzEGF7NaTa5fjVpCPyYgfvyuaangBvADrpy6tFYMBhTRDa7d3dc8stsfXAoyyh2aDjg59TobNXyFxy6tSfgLEhJnrz7ZMUYLUqmk43WaVqRYD4uTZKXKhpJkGuqEYVwo7pYGGZc96QdGZ2SrvbeW945YHQQrTgkYv2D54UJs6ahajAwfArmGUzDmataHYtGTY9QoKduzN9cwsRz8cim1nSoBHYbZXGAPUjMN1SNWW88myChULdxozg6sc8t2wbM7QvKUF8if3UPzMNY9hbcQLieHDJNCtsCccDtMYE2TtpvozibiKcAYAAMysA9FdSYhUjxQdqAQTQvfTtabjEntDbbo3zFGWB994gvadayTzGheSm9Ewaa36TwPfU5yq9ZqA63QnxHUAh7GEYBnscqZv1xvcNV5NyWyD66NquYQwiHmKJs3UxRbH152f3gSZSZDLBtSGU416FeCVkd8evQMiZQeSkeJi8MXW5TmBiJCyiztggUobfR42gqXtVAnwdxuLE3j2a9pkUmq2mBQ6mkjDjuzAHSEwBjAzThFaUPpQfYd4Avh8EjCoSLpg6T3gubbKpaydkfrW7s1LLXr5bHi4FXMNKTFbSBuNGbRkXGJvMraF6ThESW57twC4uC1Yi3WTq1gnR2UCvTABpBndRvqUxKGNhuFkseYHC3AyjgpA4fAABR4fh5L6p9hLMQjamwQesVSgTPcRE7YPH4Hft4vvnYS8nCabpWBgkPwqok9LW8XKaGszeBzE9T8iak528Du5s7z7JXHEFF26nuuyLk5vPukmrepwwhCpbSU8R4wxgjGcAeX2
n=32 w=256 templates_equal=true trees_equal=false addresses_equal=false
```

`template_hash` is blake2b256 of `ErgoTree.template` (the tree with every segregated constant replaced by its
placeholder); `tree_hash` is blake2b256 of the whole serialized tree. For each (n, w) the two keys give the same
template and different trees and addresses. The two addresses of one (n, w) share a long prefix (they first
differ at character 359 of 1153 for w=16 and 913 of 1709 for w=256, counted from the lines above). `constant_tree_bytes`
is 31 bytes above `compact_tree_bytes` at both parameter sets, and `tx_bytes` in the table is 31 bytes above the
`wots_compact` row because the harness output box re-uses the verifier tree.

---

## Hashing versus interpretation

How much of the `wots-constant.es` worst-case cost is Blake2b256 and how much is the interpreter (slices, folds,
lambda dispatch, digit arithmetic, collection building). Measured by `q2/hash-share/HashShare.scala`, which reuses
`Runner6` (same key seed `424242 + 1000n + w`, same worst-case message with every message digit 0, same source
substitution as the `worst` column, same context, sigma-state 6.0.7, `activatedScriptVersion = 3`), and evaluates
the original and four variants. Each variant replaces a Blake2b256 call by a slice of the same output size, so every
fold runs the same number of iterations over values of the same byte size:

- `no_chain_hash` (`q2/hash-share/no-chain-hash.es`): the chain step `blake2b256(curr).slice(0, n)` becomes
  `curr.slice(0, n)`. The slice that followed the hash stays, so only the hash node is removed.
- `no_commit_hash` (`q2/hash-share/no-commit-hash.es`): the final `blake2b256(concat) == pkCommitment` becomes
  `concat.slice(0, 32) == pkCommitment`. This adds one 32-byte slice (`Slice.costKind = PerItemCost(10, 2, 100)`,
  12 JIT, 1.2 units), which the `expected_net_of_substitute` column subtracts.
- `no_msg_hash` (source `wots-constant.es`, change made in the worst-case substitution): the line that still computes the
  real message in the worst-case run, `blake2b256(SELF.id ++ txBytes).slice(0, n)`, becomes `(SELF.id ++ txBytes).slice(0, n)`.
- `no_hash_at_all` (`q2/hash-share/no-chain-no-commit-hash.es` plus the message change): all three.

The constant `pkCommitment` of each variant is computed the way that variant computes it (chain ends without hashing,
commitment as the first 32 bytes of the concatenation), so every variant evaluates to `true` on the worst-case
signature; the variants are cost probes, not verifiers. `expected_from_table` is Blake2b calls x
`CalcBlake2b256.costKind = PerItemCost(20, 7, 128)` (JIT 20 + 7 per 128-byte chunk, chunks = (bytes - 1) / 128 + 1,
`sigma/ast/CostKind.scala:26`, `sigma/ast/trees.scala:582` in the 6.0.7 sources jar) divided by 10. The `original`
rows reproduce the `wots_constant` `worst` column above (38,890 and 242,822).

Command (repository root), run twice with identical output:

```bash
bash q2/hash-share/run.sh
```

```
# Hashing versus interpretation in q2/wots-constant.es, worst-case message (all message digits 0), sigma-state 6.0.7, activatedScriptVersion 3
# variant: no_chain_hash = blake2b256(curr).slice(0, n) -> curr.slice(0, n); no_commit_hash = blake2b256(concat) -> concat.slice(0, 32);
#          no_msg_hash = blake2b256(SELF.id ++ txBytes).slice(0, n) -> (SELF.id ++ txBytes).slice(0, n); no_hash_at_all = all three

n w variant worst evaluates_true
32 16 original 38890 true
32 16 no_chain_hash 36217 true
32 16 no_commit_hash 38879 true
32 16 no_msg_hash 38882 true
32 16 no_hash_at_all 36198 true
component blake2b_calls input_bytes expected_from_table(JIT/10) expected_net_of_substitute measured_difference
chain_hash 990 32 990x27=2673.0 2673.0 2673
commitment_hash 1 2144 139=13.9 12.7 11
message_hash 1 923 76=7.6 7.6 8
all_three_removed_together 992 - 2694.5 2693.3 2692
summary n=32 w=16 worst=38890 hashing(sum of three differences)=2692 remainder(interpretation)=36198 hashing_share=0.0692 chain_hash_share=0.0687 no_hash_at_all=36198

n w variant worst evaluates_true
32 256 original 242822 true
32 256 no_chain_hash 220101 true
32 256 no_commit_hash 242816 true
32 256 no_msg_hash 242812 true
32 256 no_hash_at_all 220085 true
component blake2b_calls input_bytes expected_from_table(JIT/10) expected_net_of_substitute measured_difference
chain_hash 8415 32 8415x27=22720.5 22720.5 22721
commitment_hash 1 1088 83=8.3 7.1 6
message_hash 1 1330 97=9.7 9.7 10
all_three_removed_together 8417 - 22738.5 22737.3 22737
summary n=32 w=256 worst=242822 hashing(sum of three differences)=22737 remainder(interpretation)=220085 hashing_share=0.0936 chain_hash_share=0.0936 no_hash_at_all=220085
```

The chain hashes account for 2,673 of 38,890 (n=32 w=16) and 22,721 of 242,822 (n=32 w=256), equal to the table
value within one unit. The commitment hash measures 11 and 6 against 12.7 and 7.1 expected net of the added slice;
the gap of 1.1 to 1.7 units is not explained here (the cost total is a sum of JIT units divided by 10, so each
difference carries rounding of up to one unit, which does not cover 1.7). All three hashes together: 2,692 of 38,890,
**0.0692** at w=16, and 22,737 of 242,822, **0.0936** at w=256. The rest, 36,198 and 220,085, is what the verifier
costs with no hash in it.

---

## Verifier Properties & Limits

- **Reproducibility:** Every valid signature is accepted (`accepted_valid = true`), and bit-flipped forged signatures are rejected (`rejected_forged = true`).
- **Distribution:** 200 random messages (seed `424242`) establish min, median, and max costs for each WOTS configuration.
- **Worst Case:** The verifier-maximizing message (all message digits set to zero, forcing the verifier to execute the maximum number of hash operations across both message and checksum chains) is evaluated as `worst`.
- **Schnorr Baseline:** Plain `proveDlog(pk)` spend in the same harness and interpreter consumes `cost = 403`, `tx_bytes = 138`, `sig_bytes = 56`, `key_bytes = 33`.
- **Fit Line:** Every evaluated hash-based signature parameter set satisfies consensus block limit `fits_block` (`worst <= 8001091`) and relay mempool limits `fits_relay` (`worst <= 4900000` and `tx_bytes <= 98304`).
