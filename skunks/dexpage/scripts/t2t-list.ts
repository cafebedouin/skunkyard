import { parseExact } from "../src/explorer.ts";
const EXP = "https://api.ergoplatform.com/api/v1";
const H = "3c09deff3b5f49329149d18e02aab675ef6957bf6559a5c7dba817fee883fb3e";
const all = parseExact(await (await fetch(`${EXP}/boxes/unspent/search?limit=500`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ergoTreeTemplateHash: H }) })).text()) as any;
const pools = all.items.filter((b: any) => b.assets.length === 4);
const want = ["SigUSD", "SigRSV", "FAKU", "CYPX", "rsBTC", "RSN", "SPF"];
const trees = new Set(pools.map((b: any) => b.ergoTree));
console.log("pools", pools.length, "distinct trees", trees.size);
console.log("TREE", pools[0].ergoTree);
for (const b of pools) {
  const x = b.assets[2], y = b.assets[3];
  if (want.includes(x.name) && want.includes(y.name))
    console.log(b.boxId.slice(0, 12), `${x.name} ${x.amount} (${x.decimals}d) / ${y.name} ${y.amount} (${y.decimals}d)`, "fee", b.additionalRegisters.R4.renderedValue, "LP left", b.assets[1].amount);
}
