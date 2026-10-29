import type { Box } from "@fleet-sdk/common";
import { buildSwap, describePool, priceImpactBps, quote, type SwapDirection } from "./amm";
import { Explorer, type PoolEntry, type TokenInfo } from "./explorer";
import { FEE, buildClose, buildCreate, buildFill, capacity, describe, type OrderView, type OwnerSide } from "./orders";
import { ERG_DECIMALS, ergPerTokenToPrice, formatUnits, parseUnits, priceToErgPerToken } from "./units";
import { availableWallets, connect, disconnect, signAndSubmit, utxos, type Wallet } from "./wallet";

const explorer = new Explorer(import.meta.env.VITE_EXPLORER ?? undefined);
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const logEl = $<HTMLDivElement>("log");

let wallet: Wallet | undefined;
let orderBoxes: Box<bigint>[] = [];
let pools: PoolEntry[] = [];
const tokens = new Map<string, TokenInfo>();

function log(msg: string) {
  logEl.textContent = `${new Date().toISOString().slice(11, 19)} ${msg}\n` + logEl.textContent;
}
const err = (e: unknown) => (e instanceof Error ? e.message : String(e));

async function tokenInfo(id: string): Promise<TokenInfo> {
  let t = tokens.get(id);
  if (!t) {
    try {
      t = await explorer.token(id);
    } catch {
      t = { id, name: "", decimals: 0 };
    }
    tokens.set(id, t);
  }
  return t;
}

// ---- tabs --------------------------------------------------------------------------------------

for (const b of document.querySelectorAll<HTMLButtonElement>("nav [role=tab]")) {
  b.onclick = () => {
    for (const o of document.querySelectorAll<HTMLButtonElement>("nav [role=tab]")) o.setAttribute("aria-selected", String(o === b));
    for (const s of ["swap", "orders"]) $(`tab-${s}`).hidden = s !== b.dataset.tab;
  };
}

// ---- wallet ------------------------------------------------------------------------------------

function renderWallet() {
  const el = $<HTMLDivElement>("wallet");
  el.replaceChildren();
  if (wallet) {
    const addr = wallet.changeAddress.encode();
    el.append(`${wallet.name}: ${addr.slice(0, 8)}…${addr.slice(-6)} `);
    const b = document.createElement("button");
    b.textContent = "disconnect";
    b.onclick = async () => {
      await disconnect(wallet!.name);
      wallet = undefined;
      renderWallet();
      renderOrders();
      renderQuote();
    };
    el.append(b);
    return;
  }
  const names = availableWallets();
  if (names.length === 0) {
    el.append("no EIP-12 wallet found (install Nautilus)");
    return;
  }
  for (const name of names) {
    const b = document.createElement("button");
    b.textContent = `connect ${name}`;
    b.onclick = async () => {
      try {
        wallet = await connect(name);
        log(`connected ${name}, change address ${wallet.changeAddress.encode()}`);
      } catch (e) {
        log(`connect failed: ${err(e)}`);
      }
      renderWallet();
      renderOrders();
      renderQuote();
    };
    el.append(b, " ");
  }
}

type Builder = (height: number, inputs: Box<string>[]) => ReturnType<typeof buildCreate>;

async function send(build: Builder): Promise<string> {
  if (!wallet) throw new Error("connect a wallet first");
  const height = await wallet.api.get_current_height();
  const inputs = await utxos(wallet);
  const tx = build(height, inputs);
  log(`built: ${tx.inputs.length} inputs, ${tx.outputs.length} outputs, height ${height}; waiting for the wallet`);
  const txId = await signAndSubmit(wallet, tx);
  log(`submitted ${txId}\n${explorer.txUrl(txId)}`);
  return txId;
}

// ---- swap --------------------------------------------------------------------------------------

const swapIn = $<HTMLInputElement>("swap-in");
const swapOut = $<HTMLInputElement>("swap-out");
const swapFrom = $<HTMLSelectElement>("swap-from");
const swapTo = $<HTMLSelectElement>("swap-to");
const swapGo = $<HTMLButtonElement>("swap-go");
let direction: SwapDirection = "erg-to-token";
let selectedNft = "";

function tokenSelect(sel: HTMLSelectElement) {
  sel.replaceChildren();
  for (const p of pools) {
    const o = document.createElement("option");
    o.value = p.box.assets[0].tokenId;
    const v = describePool(p.box);
    o.textContent = `${p.tokenName || v.tokenId.slice(0, 8)}  (${formatUnits(v.x, ERG_DECIMALS, 0)} ERG pool)`;
    sel.append(o);
  }
  if (selectedNft) sel.value = selectedNft;
}

function renderSwapSelectors() {
  // the token side is a select of pools; the ERG side is fixed text
  const tokenSide = direction === "erg-to-token" ? swapTo : swapFrom;
  const ergSide = direction === "erg-to-token" ? swapFrom : swapTo;
  tokenSelect(tokenSide);
  ergSide.replaceChildren(new Option("ERG", "ERG"));
  tokenSide.onchange = () => {
    selectedNft = tokenSide.value;
    renderQuote();
  };
  selectedNft = tokenSide.value;
}

function selectedPool(): PoolEntry | undefined {
  return pools.find((p) => p.box.assets[0].tokenId === selectedNft);
}

function slippageBps(): bigint {
  const t = $<HTMLInputElement>("slippage").value.trim() || "1";
  return parseUnits(t, 2); // percent with two decimals -> basis points
}

function renderQuote() {
  const dl = $<HTMLDListElement>("swap-quote");
  dl.replaceChildren();
  swapGo.disabled = true;
  const p = selectedPool();
  if (!p) return;
  const pool = describePool(p.box);
  const inDec = direction === "erg-to-token" ? ERG_DECIMALS : p.tokenDecimals;
  const outDec = direction === "erg-to-token" ? p.tokenDecimals : ERG_DECIMALS;
  const name = p.tokenName || pool.tokenId.slice(0, 8);
  const rows: [string, string][] = [];
  const spot = pool.y === 0n ? 0n : (pool.x * 10n ** BigInt(p.tokenDecimals)) / pool.y; // nanoERG per whole token
  rows.push(["Pool price", `${formatUnits(spot, ERG_DECIMALS, 6)} ERG per ${name}`]);
  rows.push(["Pool fee", `${formatUnits(1000n - pool.feeNum, 1)}% to liquidity providers`]);
  let amountIn = 0n;
  try {
    if (swapIn.value.trim()) amountIn = parseUnits(swapIn.value, inDec);
  } catch (e) {
    rows.push(["Amount", err(e)]);
  }
  if (amountIn > 0n) {
    const out = quote(pool, direction, amountIn);
    swapOut.value = formatUnits(out, outDec);
    const minOut = out - (out * slippageBps()) / 10_000n;
    rows.push(["You receive (estimate)", `${formatUnits(out, outDec)} ${direction === "erg-to-token" ? name : "ERG"}`]);
    rows.push(["Minimum after slippage", `${formatUnits(minOut, outDec)}`]);
    rows.push(["Price impact", `${formatUnits(priceImpactBps(pool, direction, amountIn), 2)}%`]);
    rows.push(["Miner fee", `${formatUnits(FEE, ERG_DECIMALS)} ERG (the only fee this page adds)`]);
    swapGo.disabled = !wallet || out <= 0n;
    swapGo.textContent = wallet ? "Swap" : "Connect a wallet to swap";
  } else {
    swapOut.value = "";
  }
  for (const [k, v] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = v;
    dl.append(dt, dd);
  }
}

swapIn.oninput = renderQuote;
$<HTMLInputElement>("slippage").oninput = renderQuote;
$<HTMLButtonElement>("swap-flip").onclick = () => {
  direction = direction === "erg-to-token" ? "token-to-erg" : "erg-to-token";
  swapIn.value = "";
  renderSwapSelectors();
  renderQuote();
};
swapGo.onclick = async () => {
  try {
    const p = selectedPool();
    if (!p) throw new Error("pick a token");
    const inDec = direction === "erg-to-token" ? ERG_DECIMALS : p.tokenDecimals;
    const amountIn = parseUnits(swapIn.value, inDec);
    const fresh = await explorer.poolByNft(selectedNft); // the pool as it stands now, not as it was listed
    const minOut = (() => {
      const q = quote(describePool(fresh.box), direction, amountIn);
      return q - (q * slippageBps()) / 10_000n;
    })();
    await send((height, inputs) => buildSwap({ height, inputs, user: wallet!.changeAddress, poolBox: fresh.box, direction, amountIn, minOut }));
    swapIn.value = "";
    setTimeout(() => void loadPools(), 3000);
  } catch (e) {
    log(`swap failed: ${err(e)}`);
  }
};

async function loadPools() {
  try {
    pools = (await explorer.pools(500)).sort((a, b) => (b.box.value > a.box.value ? 1 : -1)).filter((p) => p.box.value >= 1_000_000_000n);
    if (!selectedNft) {
      const sigusd = pools.find((p) => p.tokenName === "SigUSD");
      selectedNft = (sigusd ?? pools[0])?.box.assets[0].tokenId ?? "";
    }
    renderSwapSelectors();
    renderQuote();
    log(`${pools.length} pools with at least 1 ERG`);
  } catch (e) {
    log(`could not load pools: ${err(e)}`);
  }
}

// ---- limit orders ------------------------------------------------------------------------------

function isMine(v: OrderView): boolean {
  return !!wallet && wallet.usedAddresses.includes(v.owner);
}

async function loadOrders() {
  try {
    orderBoxes = await explorer.limitOrders(200);
    await Promise.all([...new Set(orderBoxes.map((b) => describe(b).tokenId))].map(tokenInfo));
    renderOrders();
  } catch (e) {
    $("orders").textContent = `could not load orders: ${err(e)}`;
  }
}

function renderOrders() {
  const views: { box: Box<bigint>; v: OrderView }[] = [];
  for (const box of orderBoxes) {
    try {
      views.push({ box, v: describe(box) });
    } catch {
      /* a box under the template that the SDK rejects (malformed registers): skip */
    }
  }
  const table = document.createElement("table");
  table.innerHTML = `<thead><tr><th>Token</th><th>Takers</th><th>Price (ERG/token)</th><th>Available</th><th>Owner</th><th></th></tr></thead>`;
  const tbody = document.createElement("tbody");
  for (const { box, v } of views) {
    const t = tokens.get(v.tokenId) ?? { id: v.tokenId, name: "", decimals: 0 };
    const tr = document.createElement("tr");
    if (isMine(v)) tr.className = "mine";
    const cap = capacity(v);
    tr.innerHTML =
      `<td><code title="${v.tokenId}">${t.name || v.tokenId.slice(0, 10)}</code></td>` +
      `<td>${v.takerAction === "buy" ? "buy tokens" : "sell tokens"}</td>` +
      `<td class="num">${priceToErgPerToken(v.price, t.decimals)}</td>` +
      `<td class="num">${formatUnits(cap, t.decimals)}${v.takerAction === "sell" ? ` (${formatUnits(v.value, ERG_DECIMALS)} ERG)` : ""}</td>` +
      `<td><code title="${v.owner}">${v.owner.slice(0, 6)}…</code>${isMine(v) ? " (you)" : ""}</td>`;
    const actions = document.createElement("td");
    if (wallet) {
      if (isMine(v)) {
        const b = document.createElement("button");
        b.textContent = "close";
        b.onclick = () =>
          send((height, inputs) => buildClose({ height, inputs, owner: wallet!.changeAddress, orderBox: box }))
            .then(() => setTimeout(() => void loadOrders(), 3000))
            .catch((e) => log(`close failed: ${err(e)}`));
        actions.append(b);
      } else {
        const amount = document.createElement("input");
        amount.size = 10;
        amount.placeholder = formatUnits(cap, t.decimals);
        const b = document.createElement("button");
        b.textContent = v.takerAction === "buy" ? "buy" : "sell";
        b.onclick = () => {
          try {
            const n = parseUnits(amount.value || amount.placeholder, t.decimals);
            void send((height, inputs) => buildFill({ height, inputs, taker: wallet!.changeAddress, orderBox: box, tokenAmount: n }))
              .then(() => setTimeout(() => void loadOrders(), 3000))
              .catch((e) => log(`fill failed: ${err(e)}`));
          } catch (e) {
            log(`fill: ${err(e)}`);
          }
        };
        actions.append(amount, " ", b);
      }
    }
    tr.append(actions);
    tbody.append(tr);
  }
  table.append(tbody);
  $("orders").replaceChildren(views.length ? table : "no open orders");
}

$<HTMLSelectElement>("side").onchange = () => {
  $("amount-label").textContent = $<HTMLSelectElement>("side").value === "sell-tokens" ? "Token amount" : "ERG to spend";
};

$<HTMLFormElement>("create").onsubmit = async (ev) => {
  ev.preventDefault();
  try {
    const side = $<HTMLSelectElement>("side").value as OwnerSide;
    const tokenId = $<HTMLInputElement>("token").value.trim().toLowerCase();
    const t = await tokenInfo(tokenId);
    const price = ergPerTokenToPrice($<HTMLInputElement>("price").value, t.decimals);
    const amountText = $<HTMLInputElement>("amount").value;
    const params = side === "sell-tokens" ? { tokenAmount: parseUnits(amountText, t.decimals) } : { ergAmount: parseUnits(amountText, ERG_DECIMALS) };
    log(`${side} ${t.name || tokenId.slice(0, 10)} at ${price} nanoERG per unit`);
    await send((height, inputs) => buildCreate({ height, inputs, owner: wallet!.changeAddress, side, quoteTokenId: tokenId, price, ...params }));
    setTimeout(() => void loadOrders(), 3000);
  } catch (e) {
    log(`create failed: ${err(e)}`);
  }
};

// ---- boot --------------------------------------------------------------------------------------

renderWallet();
void loadPools();
void loadOrders();
explorer.height().then((h) => log(`explorer ${explorer.base}, height ${h}`)).catch((e) => log(`explorer: ${err(e)}`));
