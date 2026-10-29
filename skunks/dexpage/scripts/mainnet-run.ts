// Build one freedex step for the skunkyard mainnet wallet with the page's own builders, and write it in the shape
// skunks/oneshot/scripts/mainnet-sign.mjs signs (that signer is the only way the wallet is used; it checks on a node,
// caps the loss, and keeps the ledger). Nothing here signs or submits.
//
//   node scripts/mainnet-run.ts fill <orderBoxId> <units>                 taker side of someone's order
//   node scripts/mainnet-run.ts create-sell <tokenId> <units> <priceNano>  owner sells tokens
//   node scripts/mainnet-run.ts create-buy <tokenId> <nanoErg> <priceNano> owner buys tokens with ERG
//   node scripts/mainnet-run.ts close <orderBoxId>                         owner closes
//   node scripts/mainnet-run.ts swap <tokenName> <erg-to-token|token-to-erg> <amountIn> [slippageBps]
//                                                                          direct swap on the token's ErgoDEX v1 pool
// Set EXCLUDE=<boxId>[,<boxId>] to keep wallet boxes a pending transaction already spends out of the selection.
// Writes mainnet/<step>-<time>.json and prints the summary and, for a create, the --allow-tree for the signer.
import { readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { EIP12UnsignedTransaction } from "@fleet-sdk/common";
import { ErgoAddress } from "@fleet-sdk/core";
import { Explorer, toFleetBox } from "../src/explorer.ts";
import { buildClose, buildCreate, buildFill, describe } from "../src/orders.ts";
import { buildSwap, describePool, quote, type SwapDirection } from "../src/amm.ts";

const WALLET = readFileSync(join(homedir(), ".config", "skunkyard", "mainnet-wallet.address"), "utf8").trim();
const owner = ErgoAddress.fromBase58(WALLET);
const explorer = new Explorer();
const [step, ...args] = process.argv.slice(2);

async function walletUtxos() {
  const r = await fetch(`${explorer.base}/api/v1/boxes/unspent/byAddress/${WALLET}?limit=100`);
  const j = (await r.json()) as { items: Parameters<typeof toFleetBox>[0][] };
  return j.items.map(toFleetBox);
}
async function box(id: string) {
  const r = await fetch(`${explorer.base}/api/v1/boxes/${id}`);
  if (!r.ok) throw new Error(`box ${id}: ${r.status}`);
  const b = (await r.json()) as Parameters<typeof toFleetBox>[0] & { spentTransactionId?: string };
  if (b.spentTransactionId) throw new Error(`box ${id} already spent`);
  return toFleetBox(b);
}

const height = await explorer.height();
const exclude = new Set((process.env.EXCLUDE ?? "").split(",").filter(Boolean));
const inputs = (await walletUtxos()).filter((b) => !exclude.has(b.boxId));
let tx: EIP12UnsignedTransaction;
let allow = "";
if (step === "fill") {
  const orderBox = await box(args[0]);
  const v = describe(orderBox);
  console.log(`order ${v.boxId.slice(0, 12)}: takers ${v.takerAction}, price ${v.price} nanoERG/unit, token ${v.tokenId.slice(0, 10)}`);
  tx = buildFill({ height, inputs, taker: owner, orderBox, tokenAmount: BigInt(args[1]) });
} else if (step === "create-sell" || step === "create-buy") {
  const side = step === "create-sell" ? "sell-tokens" : "buy-tokens";
  tx = buildCreate({
    height, inputs, owner, side, quoteTokenId: args[0], price: BigInt(args[2]),
    ...(side === "sell-tokens" ? { tokenAmount: BigInt(args[1]) } : { ergAmount: BigInt(args[1]) }),
  });
  allow = tx.outputs[0].ergoTree;
} else if (step === "swap") {
  const pools = await explorer.pools(500);
  // several pools can carry the same token name (old dust pools included): take the deepest
  const entry = pools
    .filter((p) => p.tokenName === args[0] || p.box.assets[0].tokenId === args[0])
    .sort((a, b) => (b.box.value > a.box.value ? 1 : -1))[0];
  if (!entry) throw new Error(`no pool for ${args[0]}`);
  const fresh = await explorer.poolByNft(entry.box.assets[0].tokenId);
  const pool = describePool(fresh.box);
  const direction = args[1] as SwapDirection;
  const amountIn = BigInt(args[2]);
  const q = quote(pool, direction, amountIn);
  const bps = BigInt(args[3] ?? "100");
  const minOut = q - (q * bps) / 10_000n;
  console.log(`pool ${pool.boxId.slice(0, 12)} ${fresh.tokenName}: x ${pool.x} y ${pool.y} fee ${pool.feeNum}; ${direction} ${amountIn} in -> quote ${q} out, min ${minOut}`);
  tx = buildSwap({ height, inputs, user: owner, poolBox: fresh.box, direction, amountIn, minOut });
} else if (step === "close") {
  tx = buildClose({ height, inputs, owner, orderBox: await box(args[0]) });
} else {
  throw new Error("step: fill | create-sell | create-buy | close");
}

const forSigner = {
  inputs: tx.inputs.map((i) => ({ boxId: i.boxId, spendingProof: { proofBytes: "", extension: i.extension ?? {} } })),
  dataInputs: tx.dataInputs.map((d) => ({ boxId: d.boxId })),
  outputs: tx.outputs.map((o) => ({
    value: o.value, ergoTree: o.ergoTree, creationHeight: o.creationHeight,
    assets: o.assets.map((a) => ({ tokenId: a.tokenId, amount: a.amount })), additionalRegisters: o.additionalRegisters,
  })),
};
const file = `mainnet/${step}-${new Date().toISOString().replace(/[:.]/g, "").slice(0, 15)}.json`;
writeFileSync(file, JSON.stringify(forSigner, null, 1));
console.log(`height ${height}; ${tx.inputs.length} inputs (${tx.inputs.filter((i) => i.ergoTree === owner.ergoTree).length} wallet), ${tx.outputs.length} outputs`);
for (const [k, o] of tx.outputs.entries())
  console.log(`  out ${k}: ${o.value} nanoERG ${o.assets.map((a) => `${a.amount}×${a.tokenId.slice(0, 8)}`).join(" ")} -> ${o.ergoTree === owner.ergoTree ? "wallet" : o.ergoTree.slice(0, 12) + "…"}`);
console.log(`wrote ${file}${allow ? `\n--allow-tree ${allow}` : ""}`);
