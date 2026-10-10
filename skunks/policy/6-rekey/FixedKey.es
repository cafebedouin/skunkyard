{
  // Fixed-key receive address: the owner's key is a compiled-in constant (the mainnet KeepAliveAddress shape,
  // reduced to its floor). A plain payment to it is just another box the owner can spend, so it is safe with no
  // token, no registers and no watcher. The cost is that rekey is not in place: to rotate the key the owner MOVES
  // every box at the old address to a new fixed-key address in one owner-signed transaction. This contract is the
  // baseline for the rekey-cost comparison (6-rekey/README.md): the per-box cost of that move is what an in-place
  // rotating-key variant (NFT account, key schedule) must beat.
  //
  // Constant: OWNER (compressed key). This is the readable form; the deployed and measured address is the native
  // P2PK tree (0008cd || key), the cheapest fixed key, which the baseline uses as the floor. (Writing it as
  // proveDlog(decodePoint(...)) instead compiles to a slightly larger P2S that decodes the point at run time.)
  proveDlog(decodePoint(fromBase16("$OWNER")))
}
