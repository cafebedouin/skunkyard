// Pin the vault trees ONCE (pqwallet step 4): compile QVault2.es and QDay.es with the mainnet schedule constants and
// the placeholder bytes of src/vault-tree.ts at a node's /script/p2sAddress (treeVersion 1: the node's compiler, the
// one the devnet run used; header 0x19), decode the tree from the P2S address, cross-check it with
// /script/addressToTree, find every placeholder's offsets, and write trees/QVault2.tree, trees/QDay.tree and
// trees/pins.json. Run: npx tsx scripts/pin-trees.ts [--node http://...]. Refuses to overwrite an existing pin
// unless --force is given: the point of a pin is that it does not move.
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { base58 } from '@scure/base';
import { blake2b256, hex, unhex } from '../src/bytes.js';
import { PLACEHOLDER, SCHEDULE, TREES_DIR, findAll, qdaySource, qvault2Source, zigzagVlq, zeroedHash, checkRoundTrip } from '../src/vault-tree.js';

const argv = process.argv.slice(2);
const node = (argv.includes('--node') ? argv[argv.indexOf('--node') + 1] : 'http://213.239.193.208:9052').replace(/\/+$/, '');
const force = argv.includes('--force');

async function post(path: string, body: unknown) {
  const r = await fetch(node + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const t = await r.text();
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}: ${t.slice(0, 300)}`);
  return JSON.parse(t);
}
async function get(path: string) {
  const r = await fetch(node + path);
  const t = await r.text();
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}: ${t.slice(0, 300)}`);
  return JSON.parse(t);
}

/** P2S address -> tree bytes: base58(prefix ++ tree ++ blake2b256(prefix ++ tree)[0..4]). */
function treeFromAddress(addr: string): Uint8Array {
  const b = base58.decode(addr);
  if (b[0] !== 0x13) throw new Error(`not a testnet P2S address (prefix 0x${b[0].toString(16)})`);
  const body = b.slice(0, b.length - 4);
  const sum = blake2b256(body).slice(0, 4);
  if (hex(sum) !== hex(b.slice(b.length - 4))) throw new Error('address checksum mismatch');
  return body.slice(1);
}

async function compile(src: string): Promise<{ tree: Uint8Array; address: string }> {
  const { address } = (await post('/script/p2sAddress', { source: src, treeVersion: 1 })) as { address: string };
  const tree = treeFromAddress(address);
  const { tree: nodeTree } = (await get(`/script/addressToTree/${address}`)) as { tree: string };
  if (nodeTree !== hex(tree)) throw new Error('addressToTree differs from the tree decoded from the address');
  return { tree, address };
}

function locate(name: string, tree: Uint8Array, placeholders: Record<string, Uint8Array>, expectCount: Record<string, number>) {
  const offsets: Record<string, number[]> = {};
  for (const [k, ph] of Object.entries(placeholders)) {
    const found = findAll(tree, ph);
    console.log(`pin ${name} ${k} len=${ph.length} offsets=${JSON.stringify(found)}`);
    if (found.length !== expectCount[k]) throw new Error(`${name}: ${k} occurs ${found.length} times, expected ${expectCount[k]}`);
    offsets[k] = found;
  }
  // no two placeholders may overlap
  const spans = Object.entries(offsets).flatMap(([k, os]) => os.map((o) => [k, o, o + placeholders[k].length] as const));
  for (const a of spans) for (const b of spans) if (a !== b && a[1] < b[2] && b[1] < a[2]) throw new Error(`${name}: ${a[0]} and ${b[0]} overlap`);
  return offsets;
}

async function main() {
  mkdirSync(TREES_DIR, { recursive: true });
  const pinsPath = join(TREES_DIR, 'pins.json');
  if (existsSync(pinsPath) && !force) throw new Error(`${pinsPath} exists; the pin does not move (use --force to re-pin, and say why)`);
  const info = (await get('/info')) as { appVersion: string; network: string; fullHeight: number; name: string };
  console.log(`pin node=${node} appVersion=${info.appVersion} network=${info.network} height=${info.fullHeight}`);

  // QVault2 with placeholders
  const vSrc = qvault2Source({ OWNER: PLACEHOLDER.OWNER, QDAY_NFT: PLACEHOLDER.QDAY_NFT, PKSEED: PLACEHOLDER.PKSEED, PKCOMMIT: PLACEHOLDER.PKCOMMIT, SUCCESSOR: PLACEHOLDER.SUCCESSOR, BACKSTOP: PLACEHOLDER.BACKSTOP });
  const v = await compile(vSrc);
  console.log(`pin QVault2 tree_bytes=${v.tree.length} header=0x${v.tree[0].toString(16)} address=${v.address.slice(0, 24)}… (${v.address.length} chars)`);
  const vPh: Record<string, Uint8Array> = {
    OWNER: unhex(PLACEHOLDER.OWNER), QDAY_NFT: unhex(PLACEHOLDER.QDAY_NFT), PKSEED: unhex(PLACEHOLDER.PKSEED),
    PKCOMMIT: unhex(PLACEHOLDER.PKCOMMIT), SUCCESSOR: unhex(PLACEHOLDER.SUCCESSOR), BACKSTOP: zigzagVlq(PLACEHOLDER.BACKSTOP),
  };
  // BACKSTOP is written twice in the source (beforeQday, afterQday); how many Int constants the compiler emits is
  // read from the tree and pinned, not assumed: count first, then require 1 or 2.
  const backstopCount = findAll(v.tree, vPh.BACKSTOP).length;
  if (backstopCount < 1 || backstopCount > 2) throw new Error(`BACKSTOP placeholder occurs ${backstopCount} times`);
  const vOff = locate('QVault2', v.tree, vPh, { OWNER: 1, QDAY_NFT: 1, PKSEED: 1, PKCOMMIT: 1, SUCCESSOR: 1, BACKSTOP: backstopCount });
  // each Coll[Byte] placeholder must sit right after its `0e <len>` prefix; the Int after its `04` type byte
  for (const [k, os] of Object.entries(vOff)) for (const o of os) {
    const ph = vPh[k];
    if (k === 'BACKSTOP') { if (v.tree[o - 1] !== 0x04) throw new Error(`BACKSTOP at ${o} is not preceded by the Int type byte`); }
    else if (v.tree[o - 2] !== 0x0e || v.tree[o - 1] !== ph.length) throw new Error(`${k} at ${o} is not a Coll[Byte](${ph.length}) constant`);
  }

  // QDay with placeholders
  const qSrc = qdaySource({ ORACLE: PLACEHOLDER.ORACLE });
  const q = await compile(qSrc);
  console.log(`pin QDay tree_bytes=${q.tree.length} header=0x${q.tree[0].toString(16)} address=${q.address.slice(0, 24)}… (${q.address.length} chars)`);
  const qPh: Record<string, Uint8Array> = { ORACLE: unhex(PLACEHOLDER.ORACLE) };
  const qOff = locate('QDay', q.tree, qPh, { ORACLE: 1 });
  if (q.tree[qOff.ORACLE[0] - 2] !== 0x0e || q.tree[qOff.ORACLE[0] - 1] !== 33) throw new Error('ORACLE is not a Coll[Byte](33) constant');

  writeFileSync(join(TREES_DIR, 'QVault2.tree'), hex(v.tree) + '\n');
  writeFileSync(join(TREES_DIR, 'QDay.tree'), hex(q.tree) + '\n');
  const pins = {
    compiler: { node, appVersion: info.appVersion, network: info.network, heightAtPin: info.fullHeight, endpoint: '/script/p2sAddress', treeVersion: 1, pinnedAt: new Date().toISOString().slice(0, 10), sources: ['skunks/qvault/QVault2.es', 'skunks/qvault/QDay.es'], schedule: SCHEDULE },
    QVault2: { offsets: vOff, placeholders: Object.fromEntries(Object.entries(vPh).map(([k, b]) => [k, hex(b)])), bytes: v.tree.length, header: `0x${v.tree[0].toString(16)}`, zeroedHash: '', placeholderAddress: v.address },
    QDay: { offsets: qOff, placeholders: Object.fromEntries(Object.entries(qPh).map(([k, b]) => [k, hex(b)])), bytes: q.tree.length, header: `0x${q.tree[0].toString(16)}`, zeroedHash: '', placeholderAddress: q.address },
  };
  writeFileSync(pinsPath, JSON.stringify(pins, null, 1) + '\n');
  // now that the files exist, compute the zeroed hashes through the substitution path itself and the round trip
  pins.QVault2.zeroedHash = zeroedHash('QVault2');
  pins.QDay.zeroedHash = zeroedHash('QDay');
  writeFileSync(pinsPath, JSON.stringify(pins, null, 1) + '\n');
  console.log(`pin QVault2 round_trip=${checkRoundTrip('QVault2')} zeroed_blake2b256=${pins.QVault2.zeroedHash}`);
  console.log(`pin QDay round_trip=${checkRoundTrip('QDay')} zeroed_blake2b256=${pins.QDay.zeroedHash}`);
  console.log(`pin written ${TREES_DIR}/{QVault2.tree,QDay.tree,pins.json}`);
}

main().catch((e) => { console.error(`pin FAIL: ${(e as Error).message}`); process.exit(1); });
