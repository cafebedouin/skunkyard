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
//   node scripts/mainnet-run.ts swap-t2t <inTokenId> <outTokenId> <amountIn> [slippageBps]  direct token-to-token swap
//   node scripts/mainnet-run.ts deposit <tokenName> <nanoErg>               add liquidity (tokens at the pool's ratio)
//   node scripts/mainnet-run.ts redeem <tokenName> <lpUnits>                remove liquidity
//   node scripts/mainnet-run.ts clock-create <tokenName> <sliceNano> <legs> <interval> <feeNano> [tolBps] [maxPriceNano]
//   node scripts/mainnet-run.ts clock-create-sell <tokenName> <units> <sliceUnits> <interval> <feeNano> [tolBps] [minPriceNano]
//   node scripts/mainnet-run.ts clock-cancel <boxId>
//   node scripts/mainnet-run.ts option-write <call|put> <tokenId> <units> <strikeNano> <expiryBlocks> <premiumNano>
//   node scripts/mainnet-run.ts option-buy <boxId>                         anyone pays the premium, becomes the buyer
//   node scripts/mainnet-run.ts option-exercise <boxId>                    the named buyer (sign the box: --sign-tree)
//   node scripts/mainnet-run.ts option-reclaim <boxId>                     the writer after expiry or while unsold (--sign-tree)
// Set EXCLUDE=<boxId>[,<boxId>] to keep wallet boxes a pending transaction already spends out of the selection.
// Writes mainnet/<step>-<time>.json and prints the summary and, for a create, the --allow-tree for the signer.
import { readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { EIP12UnsignedTransaction } from "@fleet-sdk/common";
import { ErgoAddress } from "@fleet-sdk/core";
import { Explorer, toFleetBox } from "../src/explorer.ts";
import { buildClose, buildCreate, buildFill, describe } from "../src/orders.ts";
import { buildCreateEscrow, buildTakeEscrow } from "../src/escrow.ts";
import { buildLend, buildOpenOrder, buildRepay } from "../src/bonds.ts";
import { buildMint as buildBankMint, buildRedeem as buildBankRedeem, loadBank } from "../src/bank.ts";
import { buildDeposit, buildRedeem, buildSwap, buildSwapT2T, depositQuote, describePool, describeT2TPool, quote, quoteT2T, redeemQuote, type SwapDirection } from "../src/amm.ts";
import { buildCancelClock, buildCreateClock, buildCreateClockSell, describeClock, sizeProgram, sizeProgramSell } from "../src/clock.ts";
import { buildBuy as buildOptionBuy, buildExercise, buildReclaim, buildWrite, describeOption, sizeWrite } from "../src/option.ts";

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
} else if (step === "swap-t2t") {
  const [inId, outId] = [args[0], args[1]];
  const has = (b: { assets: { tokenId: string }[] }, id: string) => b.assets[2].tokenId === id || b.assets[3].tokenId === id;
  const entry = (await explorer.t2tPools(500)).filter((e) => has(e.box, inId) && has(e.box, outId))[0];
  if (!entry) throw new Error("no direct pool");
  const fresh = await explorer.t2tPoolByNft(entry.box.assets[0].tokenId);
  const pool = describeT2TPool(fresh.box);
  const amountIn = BigInt(args[2]);
  const q = quoteT2T(pool, inId, amountIn);
  const minOut = q - (q * BigInt(args[3] ?? "100")) / 10_000n;
  console.log(`t2t pool ${pool.boxId.slice(0, 12)} ${fresh.xName}/${fresh.yName}: x ${pool.x} y ${pool.y} fee ${pool.feeNum}; ${amountIn} ${inId.slice(0, 8)} in -> quote ${q} ${outId.slice(0, 8)} out, min ${minOut}`);
  tx = buildSwapT2T({ height, inputs, user: owner, poolBox: fresh.box, inId, amountIn, minOut });
} else if (step === "deposit" || step === "redeem") {
  const pools = await explorer.pools(500);
  const entry = pools
    .filter((p) => p.tokenName === args[0] || p.box.assets[0].tokenId === args[0])
    .sort((a, b) => (b.box.value > a.box.value ? 1 : -1))[0];
  if (!entry) throw new Error(`no pool for ${args[0]}`);
  const fresh = await explorer.poolByNft(entry.box.assets[0].tokenId);
  const pool = describePool(fresh.box);
  if (step === "deposit") {
    const ergIn = BigInt(args[1]);
    const q = depositQuote(pool, ergIn);
    console.log(`pool ${pool.boxId.slice(0, 12)} ${fresh.tokenName}: x ${pool.x} y ${pool.y}; deposit ${ergIn} nanoERG + ${q.tokenIn} units -> ${q.lpOut} LP`);
    tx = buildDeposit({ height, inputs, user: owner, poolBox: fresh.box, ergIn });
  } else {
    const lpIn = BigInt(args[1]);
    const q = redeemQuote(pool, lpIn);
    console.log(`pool ${pool.boxId.slice(0, 12)} ${fresh.tokenName}: redeem ${lpIn} LP -> ${q.ergOut} nanoERG + ${q.tokenOut} units`);
    tx = buildRedeem({ height, inputs, user: owner, poolBox: fresh.box, lpIn });
  }
} else if (step === "escrow-create") {
  // escrow-create <tokenId> <units> <priceNano> [buyerAddress=the wallet]
  const buyer = args[3] ? ErgoAddress.fromBase58(args[3]) : owner;
  tx = buildCreateEscrow({ height, inputs, seller: owner, buyer, tokenId: args[0], amount: BigInt(args[1]), price: BigInt(args[2]) });
  allow = tx.outputs[0].ergoTree;
} else if (step === "escrow-take") {
  tx = buildTakeEscrow({ height, inputs, buyer: owner, escrowBox: await box(args[0]) });
} else if (step === "loan-open") {
  // loan-open <principalNano> <repaymentNano> <termBlocks> <collateralNano>
  tx = buildOpenOrder({ height, inputs, borrower: owner, principalId: "ERG", principal: BigInt(args[0]), repayment: BigInt(args[1]), term: Number(args[2]), collateralErg: BigInt(args[3]) });
  allow = tx.outputs[0].ergoTree;
} else if (step === "loan-lend") {
  tx = buildLend({ height, inputs, lender: owner, orderBox: await box(args[0]) });
  allow = tx.outputs[0].ergoTree + "," + tx.outputs[2].ergoTree; // the bond, and the developer fee address
} else if (step === "loan-repay") {
  tx = buildRepay({ height, inputs, borrower: owner, bondBox: await box(args[0]) });
} else if (step === "bank-mint" || step === "bank-redeem") {
  // bank-mint|bank-redeem stable|reserve <units>
  const bank = await loadBank(explorer);
  const coin = args[0] as "stable" | "reserve";
  tx = (step === "bank-mint" ? buildBankMint : buildBankRedeem)({ height, inputs, user: owner, bank, coin, amount: BigInt(args[1]) });
  if (step === "bank-mint") allow = tx.outputs.filter((o) => o.ergoTree !== owner.ergoTree).map((o) => o.ergoTree).join(",");
} else if (step === "clock-create") {
  // clock-create <tokenName> <sliceNano> <legs> <intervalBlocks> <executorFeeNano> [toleranceBps=0] [maxPriceNano=0]
  // SK-064: a clocked program on the token's deepest ERG pool; the rent reserve is added by sizeProgram
  const pools = await explorer.pools(500);
  const entry = pools
    .filter((p) => p.tokenName === args[0] || p.box.assets[0].tokenId === args[0])
    .sort((a, b) => (b.box.value > a.box.value ? 1 : -1))[0];
  if (!entry) throw new Error(`no pool for ${args[0]}`);
  const fresh = await explorer.poolByNft(entry.box.assets[0].tokenId);
  const program = {
    owner, tokenId: fresh.box.assets[2].tokenId, poolBox: fresh.box, slice: BigInt(args[1]), legs: Number(args[2]),
    interval: Number(args[3]), executorFee: BigInt(args[4]), toleranceBps: BigInt(args[5] ?? "0"), maxPrice: BigInt(args[6] ?? "0"),
  };
  const sized = sizeProgram(program);
  const p = describePool(fresh.box);
  console.log(`pool ${p.boxId.slice(0, 12)} ${fresh.tokenName} (nft ${p.nft.slice(0, 12)}): x ${p.x} y ${p.y} fee ${p.feeNum}; ${program.legs} legs of ${program.slice} every ${program.interval} blocks, fee ${program.executorFee}; box ${sized.bytes} bytes, rent reserve ${sized.rentReserve}, value ${sized.value}`);
  tx = buildCreateClock({ ...program, height, inputs });
  allow = tx.outputs[0].ergoTree;
} else if (step === "clock-create-sell") {
  // clock-create-sell <tokenName> <units> <sliceUnits> <intervalBlocks> <executorFeeNano> [toleranceBps=0] [minPriceNano=0]
  // SK-064: a tranche sale on the token's deepest ERG pool; legs = units / slice; the full rent reserve and the box
  // minimum are added by sizeProgramSell
  const pools = await explorer.pools(500);
  const entry = pools
    .filter((p) => p.tokenName === args[0] || p.box.assets[0].tokenId === args[0])
    .sort((a, b) => (b.box.value > a.box.value ? 1 : -1))[0];
  if (!entry) throw new Error(`no pool for ${args[0]}`);
  const fresh = await explorer.poolByNft(entry.box.assets[0].tokenId);
  const program = {
    owner, tokenId: fresh.box.assets[2].tokenId, poolBox: fresh.box, tokens: BigInt(args[1]), slice: BigInt(args[2]),
    interval: Number(args[3]), executorFee: BigInt(args[4]), toleranceBps: BigInt(args[5] ?? "0"), minPrice: BigInt(args[6] ?? "0"),
  };
  const sized = sizeProgramSell(program);
  const p = describePool(fresh.box);
  console.log(`pool ${p.boxId.slice(0, 12)} ${fresh.tokenName} (nft ${p.nft.slice(0, 12)}): x ${p.x} y ${p.y} fee ${p.feeNum}; ${sized.legs} legs of ${program.slice} units every ${program.interval} blocks, fee ${program.executorFee}; box ${sized.bytes} bytes, rent reserve ${sized.rentReserve}, minimum ${sized.minBox}, value ${sized.value}`);
  tx = buildCreateClockSell({ ...program, height, inputs });
  allow = tx.outputs[0].ergoTree;
} else if (step === "clock-cancel") {
  const clockBox = await box(args[0]);
  console.log(`${describeClock(clockBox).side} program ${describeClock(clockBox).boxId.slice(0, 12)}: legs left ${describeClock(clockBox).legsLeft}`);
  tx = buildCancelClock({ height, owner, clockBox });
} else if (step === "option-write") {
  // option-write <call|put> <tokenId> <units> <strikeNano> <expiryBlocks> <premiumNano>
  // SK-065: a call locks the tokens and one rent fee for the box's bytes; a put locks strike x amount of ERG
  const t = {
    side: args[0] as "call" | "put", writer: owner, tokenId: args[1], amount: BigInt(args[2]), strike: BigInt(args[3]),
    expiry: height + Number(args[4]), premium: BigInt(args[5]),
  };
  const sized = sizeWrite(t, height);
  console.log(`${t.side} on ${t.amount} units of ${t.tokenId.slice(0, 12)}: strike ${t.strike} nanoERG/unit (${t.strike * t.amount} in all), expiry ${t.expiry} (height ${height} + ${args[4]}), premium ${t.premium}; box ${sized.bytes} bytes, rent reserve ${sized.rentReserve}, value ${sized.value}`);
  tx = buildWrite({ ...t, height, inputs });
  allow = tx.outputs[0].ergoTree;
} else if (step === "option-buy" || step === "option-exercise" || step === "option-reclaim") {
  const optionBox = await box(args[0]);
  const v = describeOption(optionBox);
  console.log(`${v.side} ${v.boxId.slice(0, 12)}: ${v.amount} units of ${v.tokenId.slice(0, 12)}, strike ${v.strike} (${v.strikeTotal} in all), expiry ${v.expiry} (height ${height}), premium ${v.premium}, ${v.sold ? `sold to ${v.buyer}` : "unsold"}, value ${v.value}`);
  if (step === "option-buy") tx = buildOptionBuy({ height, inputs, buyer: owner, optionBox });
  else if (step === "option-exercise") tx = buildExercise({ height, inputs, buyer: owner, optionBox });
  else tx = buildReclaim({ height, inputs, writer: owner, optionBox });
  if (step !== "option-buy") console.log(`--sign-tree ${optionBox.ergoTree}`);
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
