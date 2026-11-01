# Derivation seat (blind), reply 2 to ergoforum 5385, round 1 (2026-11-01)

Order kept: phase 1 from source only, written down before the survey and draft were opened; phase 2 against them.
Other seat files in this directory were not read.

Clones read (shallow, default branch):

| codebase | commit | date |
|---|---|---|
| tesseract-one/ledger-app-ergo | `decf9d03584cb35b411e6f788dfbce2cf81eadc3` | 2025-07-20 |
| nautls/nautilus-wallet | `5a1ab42d186db0f0db92312782d05f0e8c8aead2` | 2026-10-31 |
| Satergo/Satergo | `6908178e351effe0adf764c19b9fe3c8a52710ac` | 2026-05-23 |
| ergoplatform/ergo-wallet-app | `540e5edbe0e337e78474e6ce6759c482f3d66cd7` | 2026-05-25 |
| fleet-sdk `packages/wallet/src/ergoHDKey.ts` (scratch copy) | identical to `8fd834a9…` (`gh api` + `diff`, no output) | 2026-03-01 |
| ergo-appkit (subjects/) | `2142620416b516b728726c14eb62ab4c19730b6c` (v6.0.1) | |
| sigma-state_2.12 6.0.7 sources jar | | |
| ThierryM1212/SAFEW (cloned this seat) | `1fcf4a9e28c3e61ff259d90fcd742770ad288bf6` | 2023-05-18 |
| minotaur-ergo/minotaur-wallet (cloned this seat) | `2c1ba72ca5314a1b06d8c491cb038b1ff794e56e` | 2026-10-23 |
| ergo node (subjects/ergo, v6.0.4) | `c313356950fe69ef406c2ee031204079a05ea7d7` | |

## Phase 1: from source

### (a) Ledger app

- `src/commands/extpubkey/epk_handler.c:48-54`: `GET_EXTENDED_PUBLIC_KEY` calls `bip32_path_validate(path, len, 44', 429', BIP32_PATH_VALIDATE_ACCOUNT_GE3)` and returns `SW_BIP32_BAD_PATH` on failure.
- `src/common/bip32_ext.c:32`: rejects `len <= 2` or a first two elements other than `44'`, `429'`. `:47-53` (`ACCOUNT_GE3`): every element from index 2 on must be `>= 0x80000000`. So: depth 3 (`m/44'/429'/a'`) and any deeper all-hardened path under it are exported; `m/44'/429'/a'/0` (EIP-3's node) is refused; any other purpose, including `8391'`, is refused.
- Unit test pins the refusal: `unit-tests/test_bip32.c:58` (`input5 = {44', 429', 0', 0}`) asserted ERR for `ACCOUNT_GE3` at `:77`; depth 3, 4 and 5 all-hardened asserted OK at `:33-35`.
- Confirmation: `epk_handler.c:63-65` returns the key silently when `is_known_application(access_token, app_connected_app_id())`; otherwise `:67-72` → `ui_display_account` (`epk_ui_nbgl.c:66-72`, "Export Extended Public Key", Confirm/Cancel). `session_id.h:16-18`: known only if both tokens nonzero and equal. The saved token is set only on approval (`epk_ui_nbgl.c:74-75`). So: first export per token is confirmed on device; later exports with the same token, until the app restarts (RAM), are not. A request without a token is always confirmed.
- The device also refuses `8391'` for address derivation and signing (`ADDRESS_GE5`, `bip32_ext.c:58-73`, used by `da_handler.c:57`, `stx_handler.c:40`).

### (b) Ledger hosts

- Nautilus: `src/views/add/LedgerConnectView.vue:86-88` opens the app `.useAuthToken()`; `:96` `getExtendedPublicKey("m/44'/429'/0'")`; `:104` `HdKey.fromPublicKey(ledgerXpk, "m/0")` (constructor derives the path when there is no private key, `src/chains/ergo/hdKey.ts:12-14`) and passes its `extendedPublicKey` to `putWallet`; `src/stores/appStore.ts:129-141` stores `publicKey`/`chainCode` of that depth-4 node. No other `getExtendedPublicKey` call in `src/`.
- Satergo: `src/main/java/com/satergo/hw/ledger/ErgoLedgerAppkit.java:54-58` requests `{44',429',0'}` with a null token (always confirmed on device) and returns `.child(0)`. `keystore/LedgerKey.java:111-127` stores only the 33-byte public key of that depth-4 node (no chain code) in the encrypted wallet file; `:97-104` (`initCaches`) asks the device for the depth-3 node again every time the wallet is opened (`LedgerPrompt.java:93`) and checks it against the stored bytes. So the depth-3 export recurs at every open, each time with a device confirmation.
- SAFEW (not in the draft's list): `src/ergo-related/ledger.js:44,72,99,216,260` request `m/44'/429'/N'` for every account N (discovery walks accounts 0, 1, 2, … at `:216`), then derive `0/index` on the host (`:16-25`). It keeps addresses, not the xpub. Last commit 2023-05-18.

Structural point the code settles: since the device refuses every non-hardened node, and EIP-3 addresses sit under the non-hardened `.../0`, a Ledger host that derives addresses itself can only do it from the depth-3 account node. Every such host necessarily receives depth 3. The alternative is a device call per address (`DERIVE_ADDRESS`).

### (c) Mnemonic wallets

- Nautilus: `hdKey.ts:27-28` → `ErgoHDKey.fromMnemonic(mnemonic)`; fleet `ergoHDKey.ts:10` `ERGO_CHANGE_PATH = "m/44'/429'/0'/0"`, `:97-99` default path. Nautilus's `pnpm-lock.yaml:52-54` resolves `@fleet-sdk/wallet` 0.12.0, whose `ergoHDKey.ts` has the same `ERGO_CHANGE_PATH` (`gh api …?ref=@fleet-sdk/wallet@0.12.0`; diff against master is one type line, `privateKey: Uint8Array | bigint`). Export: `ExportPublicKeyDialog.vue:26` + `common/serializer.ts:2` serialize the stored depth-4 key with the depth, fingerprint and child-number fields zeroed (`0488b21e 00 00000000 00000000`); `hdKey.ts:66-68` does the same. So Nautilus's exported xpub says depth 0 while being the depth-4 node.
- Satergo: `keystore/WalletKey.java:202-205` derives `m/44'/429'/0'/0` and holds its public key; no xpub export or read-only import found (grep for `xpub|extended.*key|readOnly|watch` outside keystore/hw: none relevant).
- Ergo mobile wallet: `common-jvm/.../ErgoFacade.kt:98-105` → appkit `Bip32Serialization.serializeExtendedPublicKeyToHex(masterKey)`; `Bip32Serialization.java:35-37` requires a master key, `:39-40` derives `JavaHelpers.eip3DerivationParent()` = sigma-state `JavaHelpers.scala:389-392` = `Constants.eip3DerivationPath` (`Constants.scala:36`, `m/44'/429'/0'/0/0`) minus the last element. Depth byte written is `path.depth - 1` (`:48`), and `DerivationPath.depth` counts the leading master element (`DerivationPath.scala:14`, `fromEncoded` at `:75` starts from `List(0)`), so the byte is 4; appkit's own test expects `…04…` (`MnemonicSpec.scala:44`). Mnemonic wallets store no xpub (`SaveWalletUiLogic.kt:142,153` set it null); it is computed on the "display xpub" screen. No Ledger support in the repo (grep: none).
- Minotaur (not in the draft's list): `apps/wallet/src/action/wallet.ts:68-72` stores `master.derivePath("m/44'/429'/0'/0").neutered()` (`packages/utils/src/address.ts:8`); shown and copyable in settings (`pages/settings/WalletExtendedPublicKey.tsx:34-38,67,76`). No Ledger code found.
- Node wallet (v6.0.4, not the current release): `http/api/WalletApiRoute.scala` uses `allExtendedPublicKeys()` only inside `getPrivateKey` (`:490-500`) to find a path; no endpoint returning an xpub found by grep of `http/`.
- Read-only import, in all three that have it, ignores the serialized depth and treats the key as the EIP-3 change node: appkit `Bip32Serialization.java:88-91` forces path `m/44'/429'/0'/0`; Nautilus `hdKey.ts:31-33` and Minotaur `address.ts:21-27` derive `child(index)` directly. A pasted depth-3 key would give wrong addresses, not wider reach.

### (d) Reach, by BIP32 arithmetic

Witness script `/tmp/claude-1000/-home-scott-bin-ergo-logic/c6b06f96-0ee1-46cc-af7e-1d423aa0f65c/scratchpad/bip32_depth3.py` (session scratchpad, wiped on restart; copy it in if it is to be kept) (pure Python secp256k1; the "oracle" is simulated by handing the attacker functions only `(k_acct, c_acct)`), output:

```
m/44'/429'/0'/0/0: attacker == victim: True
m/44'/429'/0'/0/7: attacker == victim: True
m/44'/429'/0'/0/1000: attacker == victim: True
m/44'/429'/0'/5'/3' (hardened under the node): attacker == victim: True
xpub-only public key m/44'/429'/0'/0/7 matches: True
rule-B root key half: 6fb665e5d01fa298da3586ac1d91c97396920acc43b1661f82d3dd64af8d6a3a
```

The last line matches post 1's printed rule-B root key half (independent re-implementation).

Arithmetic (read): a depth-3 xpub is `(K_acct, c_acct)`. A discrete log gives `k_acct`; with `c_acct` that is the account's extended private key, so every descendant, hardened or not. Upward: `k_acct = IL + k_parent` with `IL = HMAC-SHA512(c_parent, 0x00‖k_parent‖be32(a'))`; the attacker has neither `c_parent` nor `k_parent`, and the parent public key is not in the serialization (only a 4-byte fingerprint). Even a discrete log of a published `m/44'/429'` public key would give `k_parent` without `c_parent`. So the reach is exactly the subtree of `m/44'/429'/a'`: not other accounts, not `m/44'/429'`, not the master, not `m/8391'/…` (a child of the master, sibling of `m/44'`), and not `HMAC-SHA512("ergo-pq/v1", seed)`, which needs the seed (no BIP32 key reveals it: the master is `HMAC-SHA512("Bitcoin seed", seed)`).

What a depth-3 export would change: only a PQ branch placed inside `m/44'/429'/a'/…`. Post 2's sentence "Rule A's secp256k1 branch inherits the exact discrete-log exposure" does not hold for rule A as specified.

## Phase 2: survey (`skunks/pqwallet/XPUB-DEPTH-SURVEY.md`)

| line | claim / citation | verdict |
|---|---|---|
| 10 | Ledger: `44'/429'` + all-hardened from index 2; depth 3 shallowest; `.../0` refused; confirmation unless known token | verified |
| 10 | `epk_handler.c:48-52` | verified (call spans 48-54) |
| 10 | `epk_handler.c:63-74` | off by one: the file has 72 lines (`wc -l`), 73 as numbered; the block is `:63-72`. Fix the range |
| 10 | `bip32_ext.c:47-53` | verified for the hardened rule; "starts `44'/429'`" and "depth 3 is the shallowest" rest on `bip32_ext.c:32` (and the `44'`,`429'` arguments at `epk_handler.c:50-51`), not cited. Add `:32` |
| 11 | Nautilus Ledger, `LedgerConnectView.vue:96,104` | verified; storage is at `appStore.ts:129-141` if a cite for "stores" is wanted |
| 12 | `hdKey.ts:27-28`, fleet `:10,83-99` at `8fd834a9…` | verified (file identical to that commit) |
| 12 | "Nautilus pins `^0.12.0`, not checked against that release" | now checkable: lockfile resolves 0.12.0, same default path (see (c)). Replace with that |
| 13 | Satergo Ledger `ErgoLedgerAppkit.java:54-58` | verified. Omits that Satergo re-requests depth 3 at every wallet open and stores only the public key bytes (`LedgerKey.java:97-104,111-127`) |
| 14 | `WalletKey.java:204` | verified |
| 15 | `ErgoFacade.kt:98-105`, `Bip32Serialization.java:34-52` | verified |
| 15 | `JavaHelpers.scala:387-390` | off: `def eip3DerivationParent()` is `:389-392` (387 is the doc comment, 391 the `dropRight`). Also cite `Constants.scala:36` for the base path |
| 17-18 | "every Ledger-backed flow … keeps only the depth-4 child" | verified for Nautilus and Satergo; SAFEW keeps addresses only |
| 18-19 | "Not checked: SAFEW, Minotaur, the node's wallet" | now checked (see (b), (c)); update |
| 21-23 | reach | verified (witness + arithmetic) |

## Phase 2: draft (`posts/2026-11-derivation-reply-2-draft.md`)

| line | load-bearing claim | verdict |
|---|---|---|
| 3 | four codebases, default branches, read not run | verified as a description of the survey. Would become six if SAFEW and Minotaur are added |
| 5 | Ledger exports only `m/44'/429'/account'` and all-hardened paths below it | verified (`bip32_ext.c:32,47-53`, test `:77`) |
| 5 | "after a confirmation on the device" | partly: true for the first request per app token; later requests with the same token are silent (`epk_handler.c:63-65`). Suggest "after a confirmation on the device (once per connecting app)" or drop the clause; as written it implies every export is confirmed |
| 5 | depth 3 shallowest; `.../0` refused because not hardened | verified |
| 6 | Nautilus and Satergo ask for `m/44'/429'/0'`, derive `/0`, store depth 4 | verified for Nautilus. Satergo: stores the depth-4 public key only and asks the device for depth 3 again at each wallet open. "store the depth-4 key" is defensible; adding "(Satergo asks again each time the wallet opens)" is more exact |
| 7 | mnemonic: Nautilus, mobile wallet, Satergo hold or export depth 4 | verified. Optional nuance: Nautilus's exported serialization zeroes the depth byte (`serializer.ts:2`); the node is depth 4 but the key says 0 |
| 9 | none offers the user a depth-3 xpub; every Ledger-backed one receives one | verified. Stronger form the code supports: the Ledger app cannot give any host depth 4, so any host that derives Ledger addresses itself receives depth 3 |
| 9 | "Not checked: SAFEW, Minotaur, the node's wallet, other hardware" | stale after this seat: SAFEW requests depth 3 from Ledger for every account (`ledger.js:216`), holds no xpub; Minotaur holds/exports depth 4, no Ledger; node v6.0.4 exposes no xpub endpoint (light grep; current release not checked). Other hardware (Keystone etc.): not checked by this seat either |
| 11 | `m/8391'/…` sits beside `m/44'` | verified |
| 11 | depth-3 + discrete log → account private key and everything below, stops there, reaches neither rule | verified (witness lines 1-4; arithmetic above). Wording: "a depth-3 key" should be "a depth-3 extended public key"; the public key alone with a discrete log gives the account scalar but not its children |
| 11 | matters only for a PQ branch under the account | verified |
| 11 | "Rule A's own weakness is an extended key exported from its branch" | consistent with post 1 §2 table; not re-derived beyond the arithmetic above (same mechanism) |
| 13 | next item is an EIP draft | commitment, not a claim; it changes post 1's "if a wallet team names what it would take, that is the next item". Operator's call |

Would cut: nothing load-bearing. Would correct: the confirmation clause (l.5) and the "Not checked" list (l.9).

Possible extension, operator's call (scope): the Ergo Ledger app refuses `m/8391'/…` for export, address derivation and signing (`bip32_ext.c:32`, `ADDRESS_GE5` users). Post 1 keeps rule A "only as a device-internal path for hardware that already implements BIP32"; on the one Ergo hardware app read here, rule A's path would need an app change. That is a fact about rule A, not about the depth-3 question, so it may not belong in this reply.

## Couldn't verify

- Whether any host logs or caches the depth-3 response (Nautilus holds it in a local, `LedgerConnectView.vue:96-104`; not traced through the runtime).
- `ledger-ergo-js` internals beyond the constructor/token handling (`gh api` read of `anon-br/ledger-ergo-js` `src/erg.ts`): what SAFEW's second argument `true` does was not confirmed.
- Keystone, Yoroi's (retired) Ergo support, other hardware or wallets.
- The current node release's wallet API (only v6.0.4 in `subjects/ergo`).
