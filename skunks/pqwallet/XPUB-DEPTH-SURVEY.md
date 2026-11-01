# Which extended public key do Ergo wallets hold or export? (2026-11-01)

Question from forum topic 5385 (post 2): does any Ergo wallet export the account-level xpub (depth 3,
`m/44'/429'/account'`) rather than EIP-3's depth-4 node (`m/44'/429'/account'/0`)?

Method: read the default branch of each codebase on 2026-11-01. Nothing was run. Every line below is "read". The
downward half of the reach statement at the end was run: `scripts/xpub_depth3_reach.py` (pure Python, BIP39 test
mnemonic) hands only the account scalar and chain code to the derivation and reproduces `m/44'/429'/0'/0/0`, `/0/7`,
`/0/1000` and the hardened `m/44'/429'/0'/5'/3'`; it also prints rule B's root key half, equal to the published vector.
That the climb stops at `account'` is BIP32's hardened step (read), not something the script tests.

| codebase | commit | what it does | where |
|---|---|---|---|
| Ergo Ledger app (`tesseract-one/ledger-app-ergo`) | `decf9d03584cb35b411e6f788dfbce2cf81eadc3` | `GET_EXTENDED_PUBLIC_KEY` accepts a path only if it starts `44'/429'` and every element from index 2 on is hardened (`BIP32_PATH_VALIDATE_ACCOUNT_GE3`); so depth 3 is the shallowest node it exports and the EIP-3 change node `.../0` is refused. The device asks for confirmation unless the caller holds a known app token. | `src/commands/extpubkey/epk_handler.c:48-52,63-72`, `src/common/bip32_ext.c:32,47-53` |
| Nautilus (`nautls/nautilus-wallet`) Ledger connect | `5a1ab42d186db0f0db92312782d05f0e8c8aead2` | requests `m/44'/429'/0'` from the device, derives `m/0` on the host, stores that depth-4 xpub | `src/views/add/LedgerConnectView.vue:96,104`; `src/chains/ergo/hdKey.ts:30-37` (an object key takes the path; `ledger-ergo-js` 0.2.1 returns `{publicKey, chainCode}`, `dist/erg.d.ts:29-31,225`); the stored serialization has bytes 4-11 (depth, fingerprint, part of the child number) zeroed, `hdKey.ts:61-68` |
| Nautilus mnemonic wallets | same | `ErgoHDKey.fromMnemonic` with no path → fleet-sdk default `ERGO_CHANGE_PATH = "m/44'/429'/0'/0"` (depth 4) | `src/chains/ergo/hdKey.ts:27-28`; fleet-sdk `packages/wallet/src/ergoHDKey.ts:10,83-99` at `8fd834a94a7534069ed78af3538f518068ca1e2e` (master; Nautilus pins `^0.12.0`, not checked against that release) |
| Satergo (`Satergo/Satergo`) Ledger | `6908178e351effe0adf764c19b9fe3c8a52710ac` | requests `{44',429',0'}` from the device and returns `.child(0)` (depth 4) | `src/main/java/com/satergo/hw/ledger/ErgoLedgerAppkit.java:54-58` |
| Satergo mnemonic | same | parent key derived at `m/44'/429'/0'/0` | `src/main/java/com/satergo/keystore/WalletKey.java:204` |
| Ergo mobile wallet (`ergoplatform/ergo-wallet-app`) | `540e5edbe0e337e78474e6ce6759c482f3d66cd7` | the xpub shown in wallet config is appkit's `Bip32Serialization.serializeExtendedPublicKeyToHex(masterKey)`, which derives `eip3DerivationParent()` = `m/44'/429'/0'/0` first | `common-jvm/src/main/java/org/ergoplatform/ErgoFacade.kt:98-105`; appkit `common/src/main/java/org/ergoplatform/appkit/Bip32Serialization.java:34-52` at `2142620416b516b728726c14eb62ab4c19730b6c`; sigma-state 6.0.7 `JavaHelpers.scala:389-392`, `Constants.scala:36` (the app builds against an appkit snapshot, not this tag; the path is the same there) |
| SAFEW (`ThierryM1212/SAFEW`) Ledger | `1fcf4a9e28c3e61ff259d90fcd742770ad288bf6` (last commit 2023-05-18) | requests `m/44'/429'/N'` for each account N, derives `0/index` on the host, keeps addresses | `src/ergo-related/ledger.js:14-26,44,72,99,216,260` |
| Minotaur (`minotaur-ergo/minotaur-wallet`) mnemonic | `2c1ba72ca5314a1b06d8c491cb038b1ff794e56e` | stores `master.derivePath("m/44'/429'/0'/0").neutered()`; no Ledger code found by grep | `apps/wallet/src/action/wallet.ts:66-73`, `packages/utils/src/address.ts:8` |

Node wallet (`ergoplatform/ergo` `v6.0.11`, light check): `allExtendedPublicKeys()` is used in `WalletApiRoute.scala:497` only to find a key's path; grep found no endpoint that returns an extended key.

Structural point: the Ledger app refuses every non-hardened node, and EIP-3 addresses sit under the non-hardened `.../0`, so a host that computes Ledger addresses itself must receive the depth-3 account node.

Answer, as far as these go: none of them gives the user a depth-3 xpub to export; every Ledger-backed flow among them
receives one from the device over the host connection and keeps only the depth-4 child. Not checked: Keystone or
other hardware, the node's wallet beyond the grep above, and whether any host logs or caches the depth-3 response.

Reach (BIP32 arithmetic, read): with a discrete log, a depth-3 public key gives the account private key, and hence
every key under the account, hardened children included. The climb stops at the hardened edge `account'`. It does not
reach `m/8391'/…` (rule A, a sibling of `m/44'` under the master) or rule B's separate root.
