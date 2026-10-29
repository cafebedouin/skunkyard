// List ErgoDEX v1 ERG-to-token (N2T) pools on mainnet by the pool contract's template hash, read-only.
// The pool tree is taken from a pool successor the repo already spent (skunks/upkeep/mainnet/tx/ergopad-tx.json).
import { readFileSync } from "node:fs";
import { ErgoTree } from "@fleet-sdk/core";
import { hex, sha256 } from "@fleet-sdk/crypto";

const tx = JSON.parse(readFileSync("../upkeep/mainnet/tx/ergopad-tx.json", "utf8"));
const poolTree: string = tx.outputs[0].ergoTree;
const tpl = new ErgoTree(poolTree).template;
const hash = hex.encode(sha256(tpl));
console.log("pool tree bytes", poolTree.length / 2, "template bytes", tpl.length, "sha256(template)", hash);
const r = await fetch("https://api.ergoplatform.com/api/v1/boxes/unspent/search?limit=500", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ ergoTreeTemplateHash: hash }),
});
const j = (await r.json()) as { total: number; items: any[] };
console.log("pools under the template:", j.total, "(fetched", j.items.length + ")");
const pools = j.items
  .filter((b) => b.assets.length === 3)
  .map((b) => ({ id: b.boxId.slice(0, 10), erg: Number(b.value) / 1e9, token: b.assets[2].tokenId.slice(0, 8), name: b.assets[2].name, units: b.assets[2].amount, dec: b.assets[2].decimals, fee: b.additionalRegisters.R4?.renderedValue, sameTree: b.ergoTree === poolTree }))
  .sort((a, b) => b.erg - a.erg);
console.log("with 3 tokens (NFT, LP, token):", pools.length, "; identical tree:", pools.filter((p) => p.sameTree).length);
for (const p of pools.slice(0, 15)) console.log(p.id, String(p.erg.toFixed(2)).padStart(12), "ERG", p.token, (p.name ?? "").padEnd(12), "dec", p.dec, "fee", p.fee);
