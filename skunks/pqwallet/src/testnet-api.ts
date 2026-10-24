// A public Ergo node's REST API, the few calls the testnet flow needs (pqwallet step 4). No API key: /info,
// /utxo/byId, /blocks/lastHeaders, POST /transactions are open on public nodes; /blockchain/* needs the node's extra
// index (the node named in the result has it). Every answer is returned with its raw text so the result file can quote
// the node verbatim.
export type Api = { base: string };

export type HttpResult = { status: number; text: string; json: unknown };

export async function http(api: Api, path: string, init?: RequestInit, timeoutMs = 60_000): Promise<HttpResult> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(api.base.replace(/\/+$/, '') + path, { ...init, signal: ctl.signal });
    const text = await r.text();
    let json: unknown;
    try { json = JSON.parse(text); } catch { /* not JSON */ }
    return { status: r.status, text, json };
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw new Error(`${path}: no answer within ${timeoutMs / 1000} s`);
    throw new Error(`${path}: ${(e as Error).message}`);
  } finally {
    clearTimeout(t);
  }
}

export function expectOk(r: HttpResult, what: string): unknown {
  if (r.status < 200 || r.status > 299) throw new Error(`${what}: HTTP ${r.status}: ${r.text.slice(0, 500)}`);
  return r.json;
}

export type Info = { appVersion: string; network: string; fullHeight: number; headersHeight: number; name: string; parameters: Params };
export type Params = {
  storageFeeFactor: number; minValuePerByte: number; maxBlockSize: number; tokenAccessCost: number; inputCost: number;
  dataInputCost: number; outputCost: number; maxBlockCost: number; blockVersion: number;
};

export async function info(api: Api): Promise<Info> {
  return expectOk(await http(api, '/info'), 'info') as Info;
}

export async function height(api: Api): Promise<number> {
  return (await info(api)).fullHeight;
}

/** A box as the node returns it (/utxo/byId, /blockchain/box/...): values are numbers, registers serialized hex. */
export type NodeBox = {
  boxId: string; transactionId: string; index: number; value: number; ergoTree: string; creationHeight: number;
  assets: { tokenId: string; amount: number }[]; additionalRegisters: Record<string, string>; inclusionHeight?: number;
};

/** The box in the shape Fleet's builders take (string amounts). */
export type FleetBox = {
  boxId: string; transactionId: string; index: number; value: string; ergoTree: string; creationHeight: number;
  assets: { tokenId: string; amount: string }[]; additionalRegisters: Record<string, string>;
};

export function toFleetBox(b: NodeBox): FleetBox {
  return {
    boxId: b.boxId, transactionId: b.transactionId, index: b.index, value: String(b.value), ergoTree: b.ergoTree,
    creationHeight: b.creationHeight, assets: (b.assets ?? []).map((t) => ({ tokenId: t.tokenId, amount: String(t.amount) })),
    additionalRegisters: { ...(b.additionalRegisters ?? {}) },
  };
}

export async function boxById(api: Api, id: string): Promise<NodeBox> {
  return expectOk(await http(api, `/utxo/byId/${id}`), `box ${id}`) as NodeBox;
}

/** Unspent boxes at an address (POST /blockchain/box/unspent/byAddress, body: the address as a JSON string). */
export async function unspentByAddress(api: Api, address: string): Promise<NodeBox[]> {
  const r = await http(api, '/blockchain/box/unspent/byAddress?limit=100', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(address),
  });
  return (expectOk(r, 'unspent by address') as NodeBox[]) ?? [];
}

export type HeaderJson = {
  id: string; parentId: string; version: number; timestamp: number; height: number; nBits: number; votes: string;
  stateRoot: string; adProofsRoot: string; transactionsRoot: string; extensionHash: string; unparsedBytes?: string;
  powSolutions: { pk: string; w: string; n: string; d: number | string };
};

export async function lastHeaders(api: Api, n = 10): Promise<HeaderJson[]> {
  const hs = expectOk(await http(api, `/blocks/lastHeaders/${n}`), 'last headers') as HeaderJson[];
  return [...hs].sort((a, b) => b.height - a.height);
}

/** The node JSON of a transaction as POST /transactions takes it. */
export type NodeTx = {
  inputs: { boxId: string; spendingProof: { proofBytes: string; extension: Record<string, string> } }[];
  dataInputs: { boxId: string }[];
  outputs: { value: number; ergoTree: string; creationHeight: number; assets: { tokenId: string; amount: number }[]; additionalRegisters: Record<string, string> }[];
};

export type Submitted = { ok: boolean; status: number; id?: string; body: string };

/** POST /transactions; the body text is kept verbatim (a rejection is the node's own words). */
export async function submit(api: Api, tx: NodeTx): Promise<Submitted> {
  const r = await http(api, '/transactions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tx) }, 120_000);
  const ok = r.status >= 200 && r.status <= 299;
  let id: string | undefined;
  if (ok) id = typeof r.json === 'string' ? r.json : (r.json as { id?: string })?.id;
  return { ok, status: r.status, id, body: r.text };
}

/** The node's own verdict without submitting (POST /transactions/check); same body shape as submit. */
export async function check(api: Api, tx: NodeTx): Promise<Submitted> {
  const r = await http(api, '/transactions/check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tx) }, 120_000);
  const ok = r.status >= 200 && r.status <= 299;
  return { ok, status: r.status, id: ok ? (typeof r.json === 'string' ? r.json : undefined) : undefined, body: r.text };
}

export type TxState = { state: 'unknown' | 'mempool' | 'confirmed'; height?: number; numConfirmations?: number };

export async function txState(api: Api, id: string): Promise<TxState> {
  const c = await http(api, `/blockchain/transaction/byId/${id}`);
  if (c.status === 200) {
    const j = c.json as { inclusionHeight: number; numConfirmations: number };
    return { state: 'confirmed', height: Number(j.inclusionHeight), numConfirmations: Number(j.numConfirmations) };
  }
  const m = await http(api, `/transactions/unconfirmed/byTransactionId/${id}`);
  if (m.status === 200) return { state: 'mempool' };
  return { state: 'unknown' };
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Poll until the transaction is in a block; `onTick` gets each observation. */
export async function waitConfirmed(api: Api, id: string, timeoutMs: number, onTick?: (s: TxState, elapsedS: number) => void): Promise<TxState> {
  const t0 = Date.now();
  let last: TxState = { state: 'unknown' };
  while (Date.now() - t0 < timeoutMs) {
    last = await txState(api, id);
    onTick?.(last, Math.round((Date.now() - t0) / 1000));
    if (last.state === 'confirmed') return last;
    await sleep(20_000);
  }
  return last;
}
