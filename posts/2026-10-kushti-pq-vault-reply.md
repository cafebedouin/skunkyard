Reply to kushti in dev chat (2026-10-10), on "hash based signature verification in ErgoScript? ... a vault which
is spendable via provedlog until special oracle (or miners flag in block extension maybe) signalling quantum day,
after, alternative p2sh path for hash based signature works only". For the user to post.

---

Yes, with no fork: Winternitz one-time signatures (WOTS, Blake2b) verified in ErgoScript.
- One-time lock (oneshot), spent on public testnet. At n=32, w=16 the signature is 2,144 bytes in a context
  variable, the tree 840 bytes, the spend 2,340 bytes, script cost about 37.5k. At n=16 the signature is 560 bytes.
  Writeup: https://www.ergoforum.org/t/post-quantum-readiness-on-ergo-measured-exposure-a-no-fork-hash-based-spend-and-what-it-costs/5369
- Many-time keys: a Merkle tree of WOTS leaves with a singleton tracking the leaf index, so a key is never signed
  with twice. Passed on devnet and public testnet. One finding there: a rent spend runs no script, so the design had
  to make a deposit require the singleton to have advanced.
- Code: https://github.com/cafebedouin/skunkyard/tree/main/skunks (oneshot, manytime)

Your quantum-day vault is close to something on our list: a sunset box spendable by the secp key until height X,
by the hash-based path only after. Your trigger is better than a fixed height. How I'd build it:

    (!qday && proveDlog(pk)) || wotsSpend

- qday read from a data input: a singleton box whose flag can only go from false to true, so it can't be switched
  back.
- A height backstop, so a captured oracle can't keep the secp path open forever.
- Each flip direction does different damage:
  - too early is harmless to an owner who holds the hash key (they just use it);
  - too late is the real risk, since the secp path stays open to a quantum attacker.

  So the trigger should be easy to fire and impossible to undo.
- A miner flag fits that, but a script only sees the last 10 headers, so the flag needs to be written once into
  that monotone box. Anyone could flip it by proving the signal, assuming a Merkle proof against the headers'
  extension root can be checked in script [not yet tried].

It also fits the storage-rent work. The keep-alive vault's keyless refresh needs no signature, so adding it to the
quantum vault doesn't weaken it: dormant coins, the ones most exposed to a quantum attacker, could sit for decades,
kept by anyone, spendable only by the owner's hash key after quantum day. Happy to build the combined contract on
a devnet if that's useful.
