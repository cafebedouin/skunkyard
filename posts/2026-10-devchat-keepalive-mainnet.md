Follow-up on storage rent: the keep-alive vault from my last note is built, tested on a devnet, and running on
mainnet.

It's a P2S address per owner. Anyone can pay it like a normal address. The owner's key moves everything at any
time. Anyone else can only merge boxes paid to it into one, or refresh a lone box in the last 30 days before rent
age. Either way the new box keeps the same script and every token, can't grow, and loses at most a small bounty:
0.0005 ERG per merged box, never more than the boxes other than the largest bring, and 0.002 ERG for a refresh. All
vaults share one template hash, so executors find them all with one query.

Devnet: all 23 cases came out as expected, including a stolen token, a bounty overdraw, a merge into another owner's
vault, double satisfaction and dust draining. Mainnet today, the merge path (the lone refresh can't run there for
four years):
- deposit, minting a demo token into the vault:
  https://explorer.ergoplatform.com/en/transactions/8ab9fe8f525a934c3a4c0e9803581153b4d8d21e678defb32d2e50958e947941
- a merge with no signature at all, the bounty paying the fee:
  https://explorer.ergoplatform.com/en/transactions/92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546
- a sponsored merge, where a third party pays the fee and the vault keeps every nanoERG:
  https://explorer.ergoplatform.com/en/transactions/6e1c55f9fbf41f7bc93579d221e9be1225a61749c1e161eda46f713dc9dc6f26

The sponsored case is the one for NFTs. A box with almost no ERG can be kept alive by its project, a wallet service
or an archive for about 0.001 ERG every four years.

One thing the numbers make clear: miners are the wrong people to rely on for this. Rent claims are own-block only
since 6.0.7, so for a miner letting a box decay pays more than a small refresh bounty. Our consolidation last week
earned 3.42 ERG; at 1.7% of blocks a miner would expect 7.4 ERG of the rent it saved by doing nothing. Non-mining
node operators have no such conflict, since they can't claim rent. A small sidecar on a non-mining node that runs
these keyless jobs (refreshes, merges, Duckpools liquidations, order fills) earns a little and is the natural
executor. Owners and sponsors can always do it themselves too.

What's still missing is wallet support: receive tokens into your keep-alive address by default, or a one-time
"protect this NFT" move. Contract, tests and transactions:
https://github.com/cafebedouin/skunkyard/tree/main/skunks/keepalive
