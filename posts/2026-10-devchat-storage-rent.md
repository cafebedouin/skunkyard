On the storage rent discussion (EIP-48/49/51/52/53): I think a large part of it is solvable today at the contract
level, without a fork. Evidence from mainnet today:

https://explorer.ergoplatform.com/en/transactions/785a7ad591b4081e8fd39c5fefff48b3a54cf62c30f02acf35107c2d9db50ef8

That transaction spends 600 boxes of an ErgoPad-style staking incentive contract (28.36 ERG) with no key, merges them
into one fresh 28.06 ERG box at the same script, and pays the executor 0.3 ERG. The contract has had that path since
2022: anyone may merge boxes of the script holding at most 0.1 ERG, for 0.0005 ERG per box. Each box is about 770
bytes, so a rent claim (about 0.96 ERG) takes it whole at four years; in the last 30 days about 1,500 boxes of these
contracts were spent without a key, and every one we sampled was a rent claim. In 14 transactions we merged all
6,847 remaining boxes across five staking setups: 436.9 ERG kept by the protocols, rent clocks restarted, 3.4 ERG
to the executor.

The pattern: a box carries a keyless refresh path that recreates it unchanged (same script, tokens and registers)
minus a small bounty to whoever does it, allowed only near rent age so it cannot be drained. Anyone can execute it,
and it fits a Lithos miner's own block as upkeep. The same path should work for NFTs and tokens held in a P2S
"keep-alive vault" (the owner's key, or the refresh path); at about 0.003 ERG per refresh (bounty plus fee), 0.05 ERG
keeps a box alive for about 60 years. That part is not tested yet; we are writing it for a devnet next.

What it does not cover: abandoned P2PK boxes (no keyless path is possible there) and contracts already deployed
without such a path. Those still need something like EIP-53/51. One gap worth noting in EIP-53: it protects only
expired boxes holding tokens or registers, but all 6,847 boxes above were plain-value contract boxes, protocol
funds that EIP-53 would not have saved.

Transactions, numbers and scripts: https://github.com/cafebedouin/skunkyard/tree/main/skunks/upkeep/mainnet
