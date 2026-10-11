// Owner spend of a KeepAlive-address box on mainnet, signed by ergo-lib (sigma-rust, ergo-lib-wasm-nodejs 0.28.0),
// which reduces the script itself: with no context variable 0 the KeepAlive script is owner || false, so an
// ordinary wallet key proves it. Reads the skunkyard mainnet test wallet's mnemonic (never printed).
// One shape only: inputs = KeepAlive boxes of this wallet's key (the pre-fix or the fixed tree); outputs = the fixed
// KeepAlive tree for this key, the wallet's P2PK, the miner-fee contract. Node /transactions/check first; --submit
// posts and appends to skunks/upkeep/mainnet/ledger.jsonl.
// Needs ergo-lib-wasm-nodejs 0.28.0 (not in package.json: npm install it beside the script).
// usage: node kaa-owner-spend-ergolib.cjs --box <id> [--to fixed|wallet] [--submit --purpose "..."] [--node URL]
const w = require('ergo-lib-wasm-nodejs');
const fs = require('fs'), os = require('os'), path = require('path');
const REPO = '/home/scott/bin/skunkyard';
const CONF = path.join(os.homedir(), '.config/skunkyard');
const FEE_TREE = '1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304';
const FEE = 1000000n;
const a = process.argv.slice(2), opt = {};
for (let i = 0; i < a.length; i++) a[i] === '--submit' ? (opt.submit = true) : (opt[a[i].slice(2)] = a[++i]);
const die = (m) => { console.log('[kaa-owner] REFUSED: ' + m); process.exit(1); };
if (!opt.box) die('--box required'); if (opt.submit && !opt.purpose) die('--purpose required with --submit');
const node = (opt.node || 'http://128.253.41.100:9053').replace(/\/+$/, '');
const get = async (p) => { const r = await fetch(node + p); if (!r.ok) die(`node ${p}: ${r.status}`); return r.json(); };
(async () => {
  const words = fs.readFileSync(path.join(CONF, 'mainnet-wallet.txt'), 'utf8').trim();
  const seed = w.Mnemonic.to_seed(words, '');
  const ext = w.ExtSecretKey.derive_master(seed).derive(w.DerivationPath.new(0, new Uint32Array([0])));
  const pk = Buffer.from(ext.public_key().pub_key_bytes()).toString('hex');
  const walletTree = '0008cd' + pk;
  const G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
  const fixed = fs.readFileSync(`${REPO}/skunks/keepalive/kaa-mainnet-G.tree`, 'utf8').trim().replace(G, pk);
  const published = fs.readFileSync(`${REPO}/skunks/keepalive/kaa-mainnet-wallet.tree`, 'utf8').trim();
  if (fixed !== published) die('the fixed tree for this key is not the published kaa-mainnet-wallet.tree');
  const box = await get(`/utxo/byId/${opt.box}`);
  const kaa = box.ergoTree;
  if (kaa !== fixed && !(kaa.startsWith('1991030f') && kaa.includes(pk))) die('input is not a KeepAlive box of this wallet');
  const h = (await get('/info')).fullHeight;
  const toTree = (opt.to || 'fixed') === 'fixed' ? fixed : walletTree;
  const outVal = BigInt(box.value) - FEE;
  const utx = { inputs: [{ boxId: box.boxId, extension: {} }], dataInputs: [],
    outputs: [{ value: outVal.toString(), ergoTree: toTree, creationHeight: h, assets: box.assets.map(x => ({ tokenId: x.tokenId, amount: String(x.amount) })), additionalRegisters: {} },
              { value: FEE.toString(), ergoTree: FEE_TREE, creationHeight: h, assets: [], additionalRegisters: {} }] };
  for (const o of utx.outputs) if (![fixed, walletTree, FEE_TREE].includes(o.ergoTree)) die('output to a disallowed script');
  const headers = await get('/blocks/lastHeaders/10');
  const bh = w.BlockHeaders.from_json(headers.map(x => JSON.stringify(x)));
  const pre = w.PreHeader.from_block_header(w.BlockHeader.from_json(JSON.stringify(headers[headers.length - 1])));
  const ctx = new w.ErgoStateContext(pre, bh, w.Parameters.default_parameters());
  const sks = new w.SecretKeys(); sks.add(w.SecretKey.dlog_from_bytes(ext.secret_key_bytes()));
  const wallet = w.Wallet.from_secrets(sks);
  const signed = wallet.sign_transaction(ctx, w.UnsignedTransaction.from_json(JSON.stringify(utx)),
    w.ErgoBoxes.from_boxes_json([box]), w.ErgoBoxes.empty());
  const sj = signed.to_json();
  console.log(`[kaa-owner] tx ${signed.id().to_str()} input ${box.boxId} (${box.value} nanoERG, tree ${kaa === fixed ? 'fixed' : 'pre-fix'}) -> ${opt.to || 'fixed'} ${outVal}; fee ${FEE}`);
  if (opt.out) fs.writeFileSync(opt.out, sj);
  const post = async (p) => { const r = await fetch(node + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: sj }); return [r.status, await r.text()]; };
  const [cs, ct] = await post('/transactions/check'); console.log(`[kaa-owner] node check: ${cs} ${ct.slice(0, 300)}`);
  if (cs !== 200) die('node refused');
  if (!opt.submit) return console.log('[kaa-owner] check only');
  const [ss, st] = await post('/transactions'); console.log(`[kaa-owner] submit: ${ss} ${st}`);
  if (ss !== 200) die('submit failed');
  fs.appendFileSync(`${REPO}/skunks/upkeep/mainnet/ledger.jsonl`, JSON.stringify({ time: new Date().toISOString(), id: JSON.parse(st), net: '0', fee: FEE.toString(), purpose: opt.purpose }) + '\n');
})().catch(e => die(String(e && e.stack || e)));
