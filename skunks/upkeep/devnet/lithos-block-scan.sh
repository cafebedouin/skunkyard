#!/usr/bin/env bash
# lithos-block-scan.sh <node> <deployment.json> [from] [to]: list blocks whose first non-coinbase transaction spends a box
# holding the deployment's collateral token (a Lithos block), with the ids of any transaction creating a DueJob box.
set -uo pipefail
NODE=${1:-http://127.0.0.1:9152}; DESC=${2:?deployment.json}; COLLAT=$(jq -r .collatToken "$DESC"); EMNFT=$(jq -r .emissionNft "$DESC")
TREE=1b8f01040400040005000400d804d601e4c6a70504d602e4c6a70605d603b2a5730000d604c1a7d1edededededededededed9172017301927202730293c5b2a4730300c5a7927ea3059a7ee4c6a70404057e72010593c27203c2a793db63087203db6308a793e4c672030404a3938cc7720301a393e4c672030504720193e4c672030605720292c17203997204a172027204
TIP=$(curl -s "$NODE/info" | jq -r .fullHeight); FROM=${3:-$((TIP-60))}; TO=${4:-$TIP}; [[ $FROM -lt 1 ]] && FROM=1
for ((k=FROM; k<=TO; k++)); do hid=$(curl -s "$NODE/blocks/at/$k" | jq -r '.[0] // empty'); [[ -n "$hid" ]] || continue
  txs=$(curl -s "$NODE/blocks/$hid/transactions" | jq -c '.transactions'); n=$(jq 'length' <<<"$txs")
  gen=$(jq -c '.[1] // empty' <<<"$txs"); [[ -n "$gen" ]] || continue
  gin=$(jq -r '.inputs[0].boxId' <<<"$gen")
  # a collateral box holds exactly one collateral token and no emission NFT (the emission box holds the token supply)
  holds=$(curl -s "$NODE/blockchain/box/byId/$gin" | jq -r --arg t "$COLLAT" --arg e "$EMNFT" 'if ([.assets[]? | select(.tokenId==$t and .amount==1)] | length) == 1 and ([.assets[]? | select(.tokenId==$e)] | length) == 0 then "1" else "0" end' 2>/dev/null)
  beats=$(jq -r --arg tree "$TREE" '[.[] | select(.outputs[]? | .ergoTree == $tree) | .id[:8]] | join(",")' <<<"$txs")
  if [[ "$holds" == "1" ]]; then echo "block $k: LITHOS (genesis $(jq -r .id <<<"$gen" | cut -c1-8) spends collateral $gin) txs=$n beats=[$beats]"
  elif [[ -n "$beats" ]]; then echo "block $k: txs=$n beats=[$beats] (not a Lithos block)"; fi
done
