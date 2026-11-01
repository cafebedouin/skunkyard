# Maintainer (recipient) seat: derivation reply 2, round 1

Recipients: the author of post 2 in ergoforum topic 5385, and Ergo wallet developers reading the thread
(Nautilus, Satergo, Ergo mobile wallet, Ergo Ledger app).

Inputs read: the thread (`/raw/5385/1`, `/raw/5385/2`, `/t/5385.json`, fetched 2026-11-01; two posts, the second by
`davidmoore`, trust level 0, hidden profile); the draft `posts/2026-11-derivation-reply-2-draft.md` (265 words);
`skunks/pqwallet/XPUB-DEPTH-SURVEY.md`.

Spot checks run by this seat, on the pinned commits through `gh api` (read, not built):

- Ledger app `decf9d0`, `epk_handler.c:48-72`: path validated with `BIP32_PATH_VALIDATE_ACCOUNT_GE3`
  (`bip32_ext.c:32,47-53`: length > 2, `44'/429'` prefix, every element from index 2 hardened). Then
  `if (is_known_application(access_token, app_connected_app_id())) return send_response_extended_pubkey(...)`;
  otherwise `ui_display_account(...)`. The confirmation is skipped for a known app token.
- Nautilus `5a1ab42`, `LedgerConnectView.vue:93-104`: passes `appId: ledgerApp.authToken`, calls
  `getExtendedPublicKey("m/44'/429'/0'")`, stores `HdKey.fromPublicKey(ledgerXpk, "m/0")`. Matches the draft.
- Satergo `6908178`, `ErgoLedgerAppkit.java:54-58`: requests `{h(44), h(429), h(0)}`, returns `.child(0)`. Matches.
- Ergo mobile wallet `540e5ed`: no path containing "ledger", "keystone" or "hardware" in the 836-file tree, so it has
  no Ledger flow and "every Ledger-backed wallet among them" means Nautilus and Satergo only. Its read-only import
  (`AddReadOnlyWalletUiLogic.kt:21-24`) accepts any serialized xpub.
- skunkyard: `skunks/pqwallet/XPUB-DEPTH-SURVEY.md` is **untracked** (`git status`: `??`). The draft cites it, so a
  forum reader who follows the citation today finds nothing.

## Verdicts on the questions asked

**1. Does it answer post 2, at forum length?** Mostly yes. Post 2 raised three things: the depth-3 survey question,
the claim that a depth-3 export would expose rule A and move the fork point, and agreement on the domain string and on
HMAC-from-seed over a second phrase. The draft answers the first two and the domain string; it does not acknowledge
the second-phrase point (one clause fixes it). At 265 words the length is right; the changes below should keep it
under about 320.

**2. Is the correction of post 2 clear, courteous, well placed?** Courteous, yes. Clear, not quite: the paragraph
"What it would reach: ..." never says it disagrees with post 2, so a reader who skims takes the survey as answering
post 2's premise ("that changes which nodes the PQ branch has to fork above") and may conclude the Ledger detail
moves the fork point. Placement is the main issue. Post 2's premise is that the survey decides the fork point; the
correction says it does not. Put that first, in one short paragraph, and the survey reads as information rather than
as a threat assessment, which also defuses the Ledger line. Make the disagreement explicit without quoting post 2
back at its author, e.g. "A depth-3 export would not reach either rule, so the answer below does not move the fork
point." The last sentence ("Rule A's own weakness is an extended key exported from its branch") is good: it tells the
author what they were probably reaching for. Pointing at post 1's table row for it helps.

**3. Accurate and actionable for wallet developers?**

- Accurate except one point a Ledger app maintainer would correct at once: "after a confirmation on the device" is
  unconditional in the draft, but the handler returns the key without a prompt when the caller's access token is
  known (`epk_handler.c:63-65`), and Nautilus passes one. The survey already states it; the draft dropped it.
- "every Ledger-backed wallet among them" is correct (Nautilus, Satergo) but reads as including the mobile wallet;
  "the two Ledger flows" is unambiguous.
- "hold or export depth 4" lumps two behaviours: Nautilus and Satergo hold it; the mobile wallet shows it as its
  exportable xpub. Splitting them costs four words.
- Not actionable as written, because it never says whether anyone should do anything. The first question every wallet
  maintainer has is "is this asking me to change something?" The answer is no, and the draft should say so.

**4. The Ledger device handing depth 3 to the host: worth naming? phrased without alarm?** Worth naming, since it is the
only depth-3 key in any flow surveyed and the poster asked exactly this. As phrased ("but every Ledger-backed wallet
among them receives one from the device") it reads as a finding against Ledger flows, with nothing saying what it
costs. Give the one-line consequence: the keys these wallets use today all sit under `/0`, so for them the depth-3
key exposes nothing the stored depth-4 key does not; it would matter only for a key placed under the account. The
refusal of non-hardened paths is the app's design and should read as such. Keep "whether a host logs or caches the
device's depth-3 response" in the not-checked list (the survey has it, the draft dropped it); it is the honest edge of
the read and a host developer can answer it in one line.

**5. Closing next step (short EIP draft fixing the domain string).** Operator's call. View: the content is right (post
2's argument, fix the string before a second implementation, is sound and cheap), but the framing shifts the default
set in post 1. Post 1 ended "If a wallet team names what it would take, that is the next item; otherwise this and the
vectors are the reference, and the rule stays a proposal." The draft's "Unless a wallet team wants something
different, the next item is a short EIP draft" proceeds without any wallet team having spoken, on one reply from a
new account. An EIP for a derivation no wallet implements, while discovery, address length and the one-signature
invariant (post 1 §4) are open, may read to the EIP editors as early. Two acceptable forms:
- (a) as drafted: announces the EIP as the next item;
- (b) offers it: "A short EIP draft fixing `ergo-pq/v1`, the five hardened levels and the vectors can follow;
  comments from wallet developers who would build against it are what would shape it."
This seat leans (b), scoped to derivation only, because it keeps post 1's stance and invites the recipients who have
not yet replied.

**6. AI-credit line.** Yes, carry one. The house rule is per outward report, and this reply reports new work (a
source read of four codebases plus spot checks) that the opening post's credit does not cover. One clause on the first
line, naming only the models and outside reviewers actually used for this reply (take the list from this round's
outputs; do not copy post 1's). Example: "Source read with Claude (Anthropic); the reply was also read by
[outside models used]." No which-model-found-what in the body.

**Form.** Neutral voice holds ("Thanks" is fine). No internal ids, no apparatus words, no session links. "rule A /
rule B" are post 1's own terms.

## Required changes

1. Commit and push `skunks/pqwallet/XPUB-DEPTH-SURVEY.md` before posting (operator's go), and say "in the same
   repository" so the citation resolves for a reader who starts at post 2.
2. Move the reach paragraph to the top as a one-line bottom line that explicitly answers post 2's premise: a depth-3
   export reaches neither rule, so the survey does not move the fork point.
3. Ledger bullet: confirmation on the device "unless the connecting app holds an access token the device already
   accepted" (matches the survey and `epk_handler.c:63-65`).
4. After the survey: say the depth-3 key in the Ledger flows exposes nothing beyond the stored depth-4 key for the keys
   in use today (all under `/0`), and that nothing here asks any of these wallets to change.
5. Restore "whether a host logs or caches the device's depth-3 response" to the not-checked list.
6. Add the AI-credit clause to the first line.

Optional: "the two Ledger flows" for "every Ledger-backed wallet among them"; split "hold or export"; acknowledge the
second-phrase point in the agreement line ("On the domain string, and on deriving from the existing seed, agreed.").

## Suggested text (one way to apply the above; closing left to the operator)

> Thanks. Source read with Claude (Anthropic); the reply was also read by [outside models used].
>
> First, a depth-3 export would not reach either rule, so the answer below does not move the fork point. Rule A's
> branch, `m/8391'/…`, sits beside `m/44'` under the master, not under it, and rule B has its own root. With a
> discrete log, a depth-3 key gives the account's private key and every key below it, hardened ones included, and
> stops at `account'`. It would matter for a post-quantum branch placed under the account, which neither rule does.
> Rule A's own weakness is an extended key exported from its own branch (post 1, the table).
>
> On which depth wallets export, from reading the current source of four codebases (default branches on 2026-11-01;
> read, not run; commits and line citations in `skunks/pqwallet/XPUB-DEPTH-SURVEY.md` in the same repository):
>
> - The Ergo Ledger app exports an extended public key only for `m/44'/429'/account'` and paths below it with every
>   level hardened, after a confirmation on the device unless the connecting app holds an access token the device
>   already accepted. Depth 3 is the shallowest it gives; EIP-3's depth-4 node, `.../0`, is not hardened, so the
>   device refuses it.
> - Nautilus and Satergo, when connecting a Ledger, ask the device for `m/44'/429'/0'`, derive `/0` on the host, and
>   store the depth-4 key.
> - For mnemonic wallets, Nautilus (through fleet-sdk's default path) and Satergo hold depth 4, and the Ergo mobile
>   wallet (through appkit) shows depth 4 as its xpub.
>
> So none of these offers the user a depth-3 xpub to export; the two Ledger flows receive one from the device and keep
> the depth-4 child. The keys these wallets use today all sit under `/0`, so the depth-3 key exposes nothing for them
> that the depth-4 key does not, and nothing here asks any of these wallets to change. Not checked: SAFEW, Minotaur,
> the node's wallet, other hardware, and whether a host logs or caches the device's depth-3 response.
>
> On the domain string, and on deriving from the existing seed, agreed. [closing: (a) or (b) above, operator's call]
