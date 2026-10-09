#!/usr/bin/env bash
# smoke.sh: the devnet smoke test for the upkeep source, against a peeryard devnet node A exposed on $NODE (api key
# "hello") and the appkit proxy on $PROXY. Steps: fund a due-job box from node A's wallet; start the staged Lithos client
# (candidate mode, verifyWithNode, heartbeat found through the node's index); wait for the client to build the beat and
# have the node's check accept it; replay the exact transaction the client sent to the check (recorded by the proxy) into
# the mempool by the proxy itself, inside the same height; confirm the successor box in a block. Prints a PASS/FAIL line. Not a rig hook yet: run by hand.
set -uo pipefail
NODE=${NODE:-http://127.0.0.1:9152}; PROXY=${PROXY:-http://127.0.0.1:9153}; KEY=hello
CLIENT=${CLIENT:-$HOME/bin/lithos-upkeep}; CONF=${CONF:-$HOME/.config/skunkyard/lithos-devnet.conf}
CHECKS=${CHECKS:?path of the recorded check bodies}; OUT=${OUT:-$HOME/bin/skunkyard/skunks/upkeep/devnet}
TREE=1b8f01040400040005000400d804d601e4c6a70504d602e4c6a70605d603b2a5730000d604c1a7d1edededededededededed9172017301927202730293c5b2a4730300c5a7927ea3059a7ee4c6a70404057e72010593c27203c2a793db63087203db6308a793e4c672030404a3938cc7720301a393e4c672030504720193e4c672030605720292c17203997204a172027204
ADDR=BLeBj4M5DTjaKjyEUwPF8JE7b6E4haYuHXwms5Rhf7mCThPdAnTdwPBHVTugWGXSgRzyt156JiWMSp31zuw3J3Vagvw1XGHQf1K7AUULYm64u8yWm6qVNpBQ3vBUWZS3tBkAExSYVFWz54M38YaZbVPLnPUx9HMNpnPiqzTz6Si1AQCPKUXUJS14aCTFc4TfF6RiqeEn2jUfHp
api(){ curl -s -m 20 -H "api_key: $KEY" -H 'Content-Type: application/json' "$@"; }
height(){ curl -s -m 5 "$NODE/info" | python3 -c "import sys,json; print(json.load(sys.stdin)['fullHeight'])"; }
sint(){ python3 "$(dirname "$0")/sint.py" "$1"; }
H=$(height); R4=$(sint $((H-10))); echo "[smoke] height $H; due-job box with R4=$((H-10)) ($R4), period 5, tip 0.01 ERG"
TX=$(api -X POST "$NODE/wallet/transaction/send" -d "{\"requests\":[{\"address\":\"$ADDR\",\"value\":1000000000,\"registers\":{\"R4\":\"$R4\",\"R5\":\"040a\",\"R6\":\"0580dac409\"}}],\"fee\":1000000}" | tr -d '"')
echo "[smoke] funding tx $TX"; BOX=""; end=$((SECONDS + 120))
while [[ -z "$BOX" && $SECONDS -lt $end ]]; do sleep 5
  BOX=$(curl -s -m 10 -X POST -H 'Content-Type: application/json' "$NODE/blockchain/box/unspent/byErgoTree" -d "\"$TREE\"" | python3 -c "import sys,json; bs=json.load(sys.stdin); print(bs[-1]['boxId'] if bs else '')" 2>/dev/null); done
[[ -n "$BOX" ]] || { echo "[smoke] FAIL: the index does not list the due-job box"; exit 1; }
echo "[smoke] box $BOX listed by the index"
: > "$CHECKS"; mkdir -p "$CLIENT/.lithos-devnet"; cd "$CLIENT/.lithos-devnet"
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 PATH=/usr/lib/jvm/java-17-openjdk-amd64/bin:$PATH
nohup ../target/universal/stage/bin/lithos-client -Dconfig.file="$CONF" -Dhttp.port=9100 -Dpidfile.path=/dev/null > client.log 2>&1 &
CPID=$!; echo "[smoke] client pid $CPID"
end=$((SECONDS + 420)); ok=no
while [[ $SECONDS -lt $end ]]; do grep -q "after the node's check" client.log && { ok=yes; break; }; sleep 5; done
grep -E "Upkeep|CandidateBuilder" client.log | grep -v "^\s*at " | cut -c1-220 | tail -12
[[ $ok == yes ]] || { echo "[smoke] FAIL: the client never reported the node's check"; kill $CPID; exit 1; }
N=$(wc -l < "$CHECKS"); echo "[smoke] proxy recorded $N check body(ies)"
BEAT=$(tail -1 "$CHECKS"); BEATID=$(echo "$BEAT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "[smoke] the proxy mirrored beat $BEATID into the mempool at its own height (see the proxy log)"
end=$((SECONDS + 180)); mined=""
while [[ $SECONDS -lt $end ]]; do mined=$(curl -s -m 5 "$NODE/blockchain/transaction/byId/$BEATID" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('inclusionHeight',''))" 2>/dev/null); [[ -n "$mined" ]] && break; sleep 3; done
kill $CPID 2>/dev/null
if [[ -n "$mined" ]]; then
  curl -s -m 10 -X POST -H 'Content-Type: application/json' "$NODE/blockchain/box/unspent/byErgoTree" -d "\"$TREE\"" | python3 -c "
import sys,json; bs=json.load(sys.stdin)
for b in bs: print('[smoke] successor', b['boxId'], b['value'], b['additionalRegisters'])"
  echo "[smoke] PASS: beat $BEATID mined at height $mined (client-built, node-checked, replayed)"
else echo "[smoke] FAIL: beat not mined within 180 s"; exit 1; fi
