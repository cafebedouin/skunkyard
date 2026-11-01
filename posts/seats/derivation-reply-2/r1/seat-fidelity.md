# Fidelity seat, derivation reply 2, round 1 (2026-11-01)

Input: `posts/2026-11-derivation-reply-2-draft.md` (v1), forum `raw/5385/1` and `raw/5385/2` (fetched this pass),
`skunks/pqwallet/XPUB-DEPTH-SURVEY.md`, the four shallow clones under the session scratchpad `wallets/`, the
appkit subject clone, the sigma-state 6.0.7 sources jar. Stance: the findings are taken as real; the question is
whether the text says more, less or other than the cited code shows.

Everything below was read, not run, except: `git rev-parse` / `gh api` checks that each clone is the default-branch
head (all four match: ledger-app-ergo `main` decf9d03, nautilus `master` 5a1ab42d, Satergo `master` 6908178e,
ergo-wallet-app `develop` 540e5edb; fleet `master` 8fd834a9), a fetch of the published `ledger-ergo-js@0.2.1` and
`@fleet-sdk/wallet@0.12.0` files from unpkg, and `tools/comment-lint --kind reply`.

## Per-claim verdicts

**C1. Line 3: "current source of four codebases (default branches on 2026-11-01; read, not run)".**
VERIFIED. All four clones are the default-branch heads (see above). "Read, not run" is honest: nothing in the survey
was executed. Nit: the citations also go into fleet-sdk, appkit and sigma-state, so "four wallet codebases and the
libraries they call" is more exact. Optional.

**C2. Line 5: Ledger app exports an xpub only for `m/44'/429'/account'` and all-hardened paths below; depth 3 is the
shallowest; `.../0` is refused.**
VERIFIED. `epk_handler.c:48-52` calls `bip32_path_validate(..., 44', 429', BIP32_PATH_VALIDATE_ACCOUNT_GE3)`;
`bip32_ext.c:32` rejects `len <= 2` or a wrong `44'/429'` prefix; `bip32_ext.c:47-53` requires every element from
index 2 on to be hardened. So depth 3 is the minimum and `m/44'/429'/0'/0` fails. The survey's `:47-53` cite omits
the length guard at `:32` that makes "depth 3 is the shallowest" true; add `:32` to the survey cite.
Caveat worth one clause, not a fix: this is the repo's `main`; the repository has no tags or releases on GitHub
(`gh api .../tags` → 0), and both files were last changed in 2024-2025, so which firmware build users run is not
established. "Current source" in line 3 already scopes this.

**C3. Line 5: "after a confirmation on the device".**
SLIGHTLY UNDERSTATED SCOPE. `epk_handler.c:63-64`: if the caller presents the access token of an app the user
already approved (`is_known_application`, `helpers/session_id.h:16-18`; the id is set on approval in
`epk_ui_*.c`), the key is returned with no prompt. Nautilus uses this (`.useAuthToken()`, LedgerConnectView.vue:88).
Fix (optional): "after a confirmation on the device (an app already approved in that session is not asked again)".
Low stakes; the first export is always confirmed.

**C4. Line 6: Nautilus and Satergo request `m/44'/429'/0'`, derive `/0` on the host, store depth 4.**
VERIFIED. Nautilus `LedgerConnectView.vue:96` requests `m/44'/429'/0'`; `:104` builds
`HdKey.fromPublicKey(ledgerXpk, "m/0")`. The path is applied only when `ledgerXpk` is an object, not a string
(`hdKey.ts:12-15,31-37`); the published `ledger-ergo-js@0.2.1` types declare
`getExtendedPublicKey(path): Promise<ExtendedPublicKey>` with `{publicKey, chainCode}` (`dist/erg.d.ts:29-31,225`),
so the object branch runs and the stored key is depth 4. The survey does not cite this; add it, since the claim
depends on it. Satergo `ErgoLedgerAppkit.java:55-58` requests `{44',429',0'}` and returns `.child(0)`.

**C5. Line 7: mnemonic wallets of Nautilus (fleet default path), mobile wallet (appkit), Satergo hold or export
depth 4.**
VERIFIED in substance; two survey-citation fixes.
- Nautilus: `hdKey.ts:27-28` calls `ErgoHDKey.fromMnemonic(mnemonic)` with no path; fleet `ergoHDKey.ts:10,93`
  default `m/44'/429'/0'/0`. The survey's caveat "Nautilus pins `^0.12.0`, not checked against that release" can
  now be closed: the published `@fleet-sdk/wallet@0.12.0` `dist/index.mjs:11,57` has the same constant and default.
  Nautilus also exports: `ExportPublicKeyDialog.vue:26` shows the stored key (depth 4) as QR/text. Not cited in the
  survey; it supports the word "export".
- Mobile wallet: `ErgoFacade.kt:98-105` → `Bip32Serialization.serializeExtendedPublicKeyToHex(masterKey)`.
  MIS-CITED VERSION in the survey: the app builds against `ergo-appkit_2.11:44fddd97-SNAPSHOT`
  (`common-jvm/build.gradle:12`), not appkit `2142620` + sigma-state 6.0.7. At the app's own pin the behaviour is
  the same: appkit `44fddd97` `common/src/main/java/org/ergoplatform/appkit/Bip32Serialization.java:26,40`, and
  `JavaHelpers.scala:602-605` (`eip3DerivationParent` = `m/44'/429'/0'/0`, then serialised at that node). Replace or
  add the `44fddd97` cite in the survey row.
- Satergo: `WalletKey.java:204` derives `m/44'/429'/0'/0`. VERIFIED.

**C6. Line 9: "So none of these offers the user a depth-3 xpub to export, but every Ledger-backed wallet among them
receives one from the device."**
WORDING FIX. "None of these" includes the Ledger app, which line 5 says does give depth 3 (to the host). Fix:
"none of the three wallets offers the user a depth-3 xpub to export, but each Ledger-backed one (Nautilus, Satergo)
receives one from the device." Search capability for "none": the absence rests on reading the cited flows; a grep
for `getExtendedPublicKey|extendedPublicKey|xpub` over Nautilus `src`, Satergo `src/main/java` and the mobile wallet
`common-jvm` found no other export path (one edge, not a contradiction: a Nautilus read-only wallet re-exports
whatever xpub the user imported). The survey's other caveat, "whether any host logs or caches the depth-3
response", is not in the draft; harmless given the reach paragraph, keep it in the survey.

**C7. Line 9: "Not checked: SAFEW, Minotaur, the node's wallet, other hardware."**
VERIFIED HONEST. With "partial answer" in line 3 and "none of these", the draft does not imply an exhaustive
survey. Good.

**C8. Line 11: "With a discrete log, a depth-3 key gives the account's private key and every key below it, and
stops there."**
PRECISION FIX, one word. Under BIP32 this holds for the depth-3 *extended* public key (public key + chain code): the
discrete log gives the account scalar, the chain code from the xpub then gives every descendant, hardened ones
included; the parent `429'` is unreachable because `account'` is a hardened step (the child is `IL + parent` with
`IL` keyed on the parent's private key and chain code, neither of which the xpub carries; it holds only the parent's
fingerprint). A bare depth-3 public key gives only the account scalar, not "every key below it". Fix: "a depth-3
extended public key" (or "a depth-3 xpub"). Neither stronger nor weaker after that change.

**C9. Line 11: rule A's branch `m/8391'/…` sits beside `m/44'`; a depth-3 key reaches neither rule A nor rule B; it
matters for a PQ branch under the account, which neither rule does.**
VERIFIED against the opening post (rule A `m/8391'/429'/account'/…` all hardened from the master; rule B a separate
HMAC root; section 1 already says "the safe fork point is above the account level. Both rules below already are").

**C10. Line 11: the correction of post 2.**
ACCURATE; COURTEOUS BUT IMPLICIT. Post 2 says: "If even one wallet hands out a depth-3 xpub, Rule A's secp256k1
branch inherits the exact discrete-log exposure described." The draft's line 11 refutes this correctly (A is a
sibling of `44'`, not under it) without saying it is answering that sentence, so a reader may not see the
correction. Suggested: "On rule A: its branch, `m/8391'/…`, sits beside `m/44'`, not under it, so a depth-3 xpub
does not reach it (the opening post's section 1 says both rules fork above the account level)." Pointing back to
the post's own sentence keeps it neutral and puts the fact where it already was.

**C11. Line 11: "Rule A's own weakness is an extended key exported from its branch."**
VERIFIED: matches the opening post's table row "reach of a leaked extended key on the branch".

**C12. Line 13: "On the domain string, agreed." / next item: a short EIP draft fixing `ergo-pq/v1`, the five
hardened levels and the vectors.**
"Five hardened levels" matches the opening post (`coin'/account'/scheme'/use'/index'`). FLAG FOR THE OPERATOR, not
judged: the sentence is a public commitment to write an EIP draft, conditional only on no wallet team objecting.
Note it also replaces the opening post's close ("If a wallet team names what it would take, that is the next item;
otherwise ... the rule stays a proposal") with a commitment to act without a wallet team's ask.

**C13. The citation pointer `skunks/pqwallet/XPUB-DEPTH-SURVEY.md`.**
NOT YET PUBLIC. `git status` in skunkyard: `?? skunks/pqwallet/XPUB-DEPTH-SURVEY.md` (untracked, never committed).
The reply points readers at a file that does not exist on github.com/cafebedouin/skunkyard. It must be committed
and pushed (with the C2/C4/C5 survey fixes) before the reply is posted. The survey also names the session-scratch
clones only implicitly (by commit), which is fine; it must not gain a local `/tmp` path when fixed. Consider naming
the repo in the pointer ("in the skunkyard repository, `skunks/pqwallet/…`"), since a reply may be read without the
opening post.

## Form rules

- First person / we: none found (scan for `I|we|our|us`).
- Internal ids (`X-NNN`, `GHSA`), apparatus words (seat, lens, prereg), session links: none found.
- `tools/comment-lint --kind reply`: 1 FAIL, rule 15, 256 words against an 80-word reply budget. Reported for the
  Maintainer seat and the operator; length is a judgment call for a detailed technical answer.
- AI credit: the reply carries new evidence (a code survey) that Claude read, and the house rule is a credit line
  in the first line of every outward report. The opening post's credit covered that post's work, not this one.
  Precedent in the same repo: `posts/2026-10-manytime-reply.md` (a reply) opens with its own credit line.
  Recommendation: add one short first line, e.g. "Survey read by Claude (Anthropic) for cafebedouin; reviewed by
  [the seats actually run this round]." Name the model only if known from the run; no which-model-found-what.

## Fixes, in priority order

1. Push the survey (with fixes 4-6) before posting, or the pointer is dead. (C13)
2. Line 11: "a depth-3 key" → "a depth-3 extended public key". (C8)
3. Line 9: "none of these" → "none of the three wallets"; "every Ledger-backed wallet among them" → "each
   Ledger-backed one". (C6)
4. Survey, mobile-wallet row: cite appkit `44fddd97` (the app's pin) `Bip32Serialization.java:26,40` and
   `JavaHelpers.scala:602-605`. (C5)
5. Survey, Nautilus rows: add `ledger-ergo-js@0.2.1` `erg.d.ts:29-31,225` (object return, so `m/0` is applied) and
   `ExportPublicKeyDialog.vue:26`; close the fleet `^0.12.0` caveat (`@fleet-sdk/wallet@0.12.0`
   `dist/index.mjs:11,57`). (C4, C5)
6. Survey, Ledger row: add `bip32_ext.c:32` (length guard). (C2)
7. Optional: make the post-2 correction explicit and point back to the opening post's section 1. (C10)
8. Optional: the token-skip clause on device confirmation. (C3)
9. Operator: credit line (recommended yes); the EIP-draft commitment (C12); word count (lint rule 15).
