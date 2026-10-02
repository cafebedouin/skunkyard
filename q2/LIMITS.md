# Current Ergo Cost and Size Limits for Q2

This document details the cost and size limits enforced by the Ergo protocol (consensus rules, miner-voted parameters, and node mempool propagation policies) as of mainnet block height 1,885,335 (epoch boundary 1,885,184), against which the Winternitz and Lamport verifier results are evaluated.

---

## 1. Parameters and Limits Table

| Limit Name | Value | Scope / Type | Source (file:line or endpoint) |
| :--- | :--- | :--- | :--- |
| **Max Block Script Cost** (`maxBlockCost`) | `8,001,091` units | Consensus (voted) | `node.ergo.watch/info` (`parameters.maxBlockCost`); vote id 4 in `ergo-core/src/main/scala/org/ergoplatform/settings/Parameters.scala:68`; enforced in `ergo-core/src/main/scala/org/ergoplatform/modifiers/mempool/ErgoTransaction.scala:120, 159` |
| **Max Transaction Relay Cost** (`maxTransactionCost`) | `4,900,000` units | Node Mempool Relay | `src/main/resources/mainnet.conf:86` (overriding default `1,000,000` in `src/main/resources/application.conf:50`) |
| **Max Box Size** (`MaxBoxSize`) | `4,096` bytes (4 KiB) | Consensus (constant) | `sigmastate-interpreter/core/shared/src/main/scala/sigma/data/SigmaConstants.scala:24-26`; enforced in `ErgoTransaction.scala:175` |
| **Max Proposition Bytes** (`MaxPropositionBytes`) | `4,096` bytes (4 KiB) | Consensus (constant) | `sigmastate-interpreter/core/shared/src/main/scala/sigma/data/SigmaConstants.scala:40-41`; enforced in `ErgoTransaction.scala:176` |
| **Max Registers** (`MaxRegisters`) | `10` (R0–R9) | Consensus (constant) | `sigmastate-interpreter/core/shared/src/main/scala/sigma/data/SigmaConstants.scala:36-37` |
| **Max Context Extension Variables** | `127` variables | Consensus / Serializer | `sigmastate-interpreter/interpreter/shared/src/main/scala/sigmastate/interpreter/ContextExtension.scala:46-47, 53-58` |
| **Max Transaction Size** (`maxTransactionSize`) | `98,304` bytes (96 KiB) | Node Mempool Relay | `src/main/resources/application.conf:53` (`maxTransactionSize = 98304`) |
| **Max Block Transactions Section** (`maxBlockSize`) | `1,271,009` bytes | Consensus (voted) | `node.ergo.watch/info` (`parameters.maxBlockSize`); vote id 3 in `ergo-core/src/main/scala/org/ergoplatform/settings/Parameters.scala:43` |

---

## 2. Unit Costing Details

- **Cost unit scale:** JIT costing scales operations by a factor of 10 (`JitCost.scala:4, 29`), where `toBlockCost = jitCost / 10`. The interpreter returns the final execution cost.
- **Blake2b256 cost:** Defined in `sigmastate-interpreter/core/shared/src/main/scala/sigmastate/utxo/trees.scala:555-583` (`PerItemCost(baseCost = JitCost(20), perChunkCost = JitCost(7), chunkSize = 128)`).
- **Collection operations cost:**
  - `fold`: base cost `JitCost(3)` + `JitCost(1)` per 10 items (`transformers.scala:236-237`).
  - `forall`: evaluates body per element until completion or false (short-circuit).

---

## 3. Pinned Tool and Dependency Versions

- **SigmaState Interpreter:** `org.scorexfoundation:sigma-state_2.12:5.0.2`
- **Scala Compiler / Runtime:** `org.scala-lang:scala-library:2.12.18`, `scalac:2.12.18`
- **Java / JVM:** OpenJDK 21 (build 21.0.12.1)
- **Logging Backend:** `org.slf4j:slf4j-nop:1.7.36`
- **Package Manager / Launcher:** Coursier (`cs`)

---

## 4. Evaluation Against Limits

1. **Script Cost:**
   - Block budget: `8,001,091`. Relay cap: `4,900,000`.
   - Highest measured cost across all parameter sets is WOTS `(n=32, w=256)` at `232,508` units.
   - `232,508` is only **2.91%** of the block limit and **4.75%** of the relay cap.
   - All 8 parameter sets fit well within execution cost limits.

2. **Box Storage (Public Key Commitment):**
   - Public key is committed as a 32-byte Blake2b256 hash in `R4`.
   - The box requires only 32 bytes for the key commitment, easily fitting inside the 4,096-byte `MaxBoxSize` for all parameter sets.

3. **Transaction Size (Context Extension):**
   - The signature (Var 0) and full public key material (Var 1) are supplied in the transaction input's `ContextExtension`.
   - Largest parameter set is Lamport `(n=32)`, requiring `8,192` bytes (sig) + `16,384` bytes (pubkey) = `24,576` bytes total key/signature payload.
   - This fits well inside the `98,304` byte (`96 KiB`) `maxTransactionSize` relay limit and the `1,271,009` byte block limit.
   - For WOTS, payloads are significantly smaller:
     - WOTS `(n=16, w=256)`: 288 bytes signature + 288 bytes key = 576 bytes.
     - WOTS `(n=32, w=256)`: 1,088 bytes signature + 1,088 bytes key = 2,176 bytes.
     - WOTS `(n=32, w=16)`: 2,144 bytes signature + 2,144 bytes key = 4,288 bytes.
