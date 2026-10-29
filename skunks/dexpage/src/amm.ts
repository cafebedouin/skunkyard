// Pure builders and quotes for ErgoDEX v1 ERG-to-token (N2T) pools: a direct swap against the pool box, no proxy
// order. The pool's own script checks the constant-product rule; the page only has to build a successor it accepts.
//   inputs:  0 pool (keyless), then the user's boxes
//   outputs: 0 pool successor (same tree, NFT and LP token, reserves moved, R4 copied), the user's output, the fee
import type { Amount, Box, EIP12UnsignedTransaction } from "@fleet-sdk/common";
import { ErgoAddress, OutputBuilder, TransactionBuilder } from "@fleet-sdk/core";
import { SConstant } from "@fleet-sdk/serializer";
import { FEE } from "./orders.ts";

/** The N2T pool ErgoTree, identical for every pool (269 of 269 on mainnet, scripts/pools.ts, 2026-10-29). */
export const POOL_TREE = "1999030f0400040204020404040405feffffffffffffffff0105feffffffffffffffff01050004d00f040004000406050005000580dac409d819d601b2a5730000d602e4c6a70404d603db63087201d604db6308a7d605b27203730100d606b27204730200d607b27203730300d608b27204730400d6099973058c720602d60a999973068c7205027209d60bc17201d60cc1a7d60d99720b720cd60e91720d7307d60f8c720802d6107e720f06d6117e720d06d612998c720702720fd6137e720c06d6147308d6157e721206d6167e720a06d6177e720906d6189c72117217d6199c72157217d1ededededededed93c27201c2a793e4c672010404720293b27203730900b27204730a00938c7205018c720601938c7207018c72080193b17203730b9593720a730c95720e929c9c721072117e7202069c7ef07212069a9c72137e7214067e9c720d7e72020506929c9c721372157e7202069c7ef0720d069a9c72107e7214067e9c72127e7202050695ed720e917212730d907216a19d721872139d72197210ed9272189c721672139272199c7216721091720b730e";
/** SHA-256 of its template, what the explorer's unspent search takes. */
export const POOL_TEMPLATE_SHA256 = "2dcc7830afe8f355b945850c60ff2b41fdb3e8ade07fde0a7c8a3ec498e8c3f6";

export interface PoolView {
  boxId: string;
  nft: string;
  lpTokenId: string;
  tokenId: string;
  /** ERG reserve, nanoERG */
  x: bigint;
  /** token reserve, smallest units */
  y: bigint;
  /** fee numerator over 1000 (997 = 0.3%) */
  feeNum: bigint;
}

export function describePool(box: Box<Amount>): PoolView {
  if (box.ergoTree !== POOL_TREE) throw new Error("not an N2T pool box");
  if (box.assets.length !== 3) throw new Error("pool box must hold NFT, LP token and the token");
  const r4 = box.additionalRegisters.R4;
  if (!r4) throw new Error("pool box has no R4");
  return {
    boxId: box.boxId,
    nft: box.assets[0].tokenId,
    lpTokenId: box.assets[1].tokenId,
    tokenId: box.assets[2].tokenId,
    x: BigInt(box.value),
    y: BigInt(box.assets[2].amount),
    feeNum: BigInt(SConstant.from<number>(r4).data),
  };
}

export type SwapDirection = "erg-to-token" | "token-to-erg";

/** Tokens out for `dx` nanoERG in (floor), or nanoERG out for `dy` tokens in (floor). The pool's rule, rounded against the taker. */
export function quote(p: PoolView, dir: SwapDirection, amountIn: bigint): bigint {
  if (amountIn <= 0n) return 0n;
  if (dir === "erg-to-token") return (p.y * amountIn * p.feeNum) / (p.x * 1000n + amountIn * p.feeNum);
  return (p.x * amountIn * p.feeNum) / (p.y * 1000n + amountIn * p.feeNum);
}

/** The spot price before the trade and the effective price of this trade, as nanoERG per smallest unit times 1e9 (bigint ratio). */
export function priceImpactBps(p: PoolView, dir: SwapDirection, amountIn: bigint): bigint {
  const out = quote(p, dir, amountIn);
  if (out === 0n) return 0n;
  // spot: y per x, or x per y, scaled by the input amount, with the fee applied, minus the realised out
  const spotOut = dir === "erg-to-token" ? (p.y * amountIn * p.feeNum) / (p.x * 1000n) : (p.x * amountIn * p.feeNum) / (p.y * 1000n);
  if (spotOut === 0n) return 0n;
  return ((spotOut - out) * 10_000n) / spotOut;
}

/** The pool must keep at least this much ERG (its script's minimum; the repo's mainnet swap used 0.0005 ERG and the v1 Pool.sc rule is 0.01 ERG). */
export const POOL_MIN_VALUE = 10_000_000n;

export interface SwapParams {
  height: number;
  inputs: Box<Amount>[];
  user: ErgoAddress;
  poolBox: Box<Amount>;
  direction: SwapDirection;
  amountIn: bigint;
  /** refuse to build if the pool would pay less than this (slippage guard, computed by the caller from a quote) */
  minOut: bigint;
}

export function buildSwap(p: SwapParams): EIP12UnsignedTransaction {
  const pool = describePool(p.poolBox);
  const out = quote(pool, p.direction, p.amountIn);
  if (out <= 0n) throw new Error("the trade is too small to receive anything");
  if (out < p.minOut) throw new Error(`the pool would pay ${out}, below the minimum ${p.minOut}`);
  const dx = p.direction === "erg-to-token" ? p.amountIn : -out;
  const dy = p.direction === "erg-to-token" ? -out : p.amountIn;
  if (pool.x + dx < POOL_MIN_VALUE) throw new Error("the trade would take the pool below its minimum ERG");
  if (pool.y + dy <= 0n) throw new Error("the trade would empty the pool's token");

  const successor = new OutputBuilder(pool.x + dx, POOL_TREE)
    .addTokens([
      { tokenId: pool.nft, amount: 1n },
      { tokenId: pool.lpTokenId, amount: BigInt(p.poolBox.assets[1].amount) },
      { tokenId: pool.tokenId, amount: pool.y + dy },
    ])
    .setAdditionalRegisters({ R4: p.poolBox.additionalRegisters.R4 as string });

  const received =
    p.direction === "erg-to-token"
      ? new OutputBuilder(1_000_000n, p.user).addTokens({ tokenId: pool.tokenId, amount: out })
      : new OutputBuilder(out, p.user);

  return new TransactionBuilder(p.height)
    .from([p.poolBox, ...p.inputs])
    .to([successor, received])
    .sendChangeTo(p.user)
    .payFee(FEE)
    .build()
    .toEIP12Object();
}
