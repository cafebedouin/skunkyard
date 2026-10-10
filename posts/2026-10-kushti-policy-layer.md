@kushti, following up on the quantum-day vault: built it on a devnet today, combined with the keep-alive vault for
storage rent. 18 of 18 cases came out as expected, among them:
- a look-alike flag box;
- leaving the flag out;
- resetting the flag after it fires;
- the backstop closing the secp path while the flag still says false;
- one WOTS key signing for two boxes;
- a merge with no key, then a single hash-key spend after quantum day.

https://github.com/cafebedouin/skunkyard/tree/main/skunks/qvault

The keep-alive half is already on mainnet: a deposit, a merge with no signature at all, and a merge a sponsor paid
for:
https://explorer.ergoplatform.com/en/transactions/92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546

Both point at the same thing: an opt-in policy layer on the box itself. The owner's authority (secp key, hash key)
is wrapped in conditions that read signals on chain (a quantum-day flag, a backstop height) and in keyless
maintenance (rent refresh, merges). It's what Ethereum calls native account abstraction, and on Ergo it works today
without a fork, because any address can be a script.

The design question, if this becomes a standard:
- one parameterised template, so vaults stay findable and audited once;
- signal boxes that are easy to fire and impossible to undo;
- wallets making the vault the default receive address, since the policy only reaches boxes whose owners move into
  it.

Miner voting changes a rule for everyone; this lets each owner choose theirs.
