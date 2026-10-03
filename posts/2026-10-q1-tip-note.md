# Note for the thread: the census at the tip (quote from the developer chat, 2026-10-03)

Prepared with Claude Code (Anthropic, Claude Fable 5.1) for cafebedouin; the figures are a community member's, reported
in the developer chat with leave to quote, not reproduced here (`q1/RESULT.md`, last section).

The post asked for someone with a synced node to run the census at the tip. Someone did, in the developer chat, with
the unmodified scanner at height 1,886,343: traversed root equal to the stored root, 6,383,135 nodes with no label
mismatch, and the sum of all boxes equal to the genesis sum. Of non-protocol ERG, 96.58% sits under a visible key
(92.84% bare P2PK, 3.48% P2S scripts containing a key), against 96.54% in the post's dry run at height 753,934: the
share has not moved in 1.1 million blocks. Exposed and already storage-rent eligible: 231 boxes holding 1,450.94 ERG,
so the rent cohort the post mentioned is small. The top 20 exposed boxes hold 17.06% of exposed ERG; no per-box
detail was posted and none is asked for. With thanks to the person who ran it.
