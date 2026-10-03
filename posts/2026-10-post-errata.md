# Edit note for the post of 2026-10-02 (thread 5369), to be added by the author as an edit, not posted as a reply

Two clarifications, both derivable from the post's own tables:

- The summary's capacity line, about 154 WOTS spends against about 596 P2PK per block, is the cost bound for a
  single-input spend. The size bound in section 3's table is 542 against 4,367, and a native opcode priced at the
  hashing units does not move the size bound, since the signature stays in the transaction.
- Storage rent falls on a box unspent for 1,051,200 blocks, at 1,250,000 nanoERG per byte per period at the
  current factor: about 1.05 ERG per period for a WOTS box of 840 bytes of script, against about 0.13 ERG for a
  P2PK box. "Nothing for holders to do today" is about action; a lock that sits for four years pays for its bytes.
  (The one-time box pays this only if it is never spent; the many-time box of the follow-up resets the clock on
  every spend.)
