// scripts/sigma-rust-p2sh-repro.cjs: ergo-lib-wasm 0.28.0 builds a P2SH box script it cannot parse back, without OptionGet.
// No node, no network. Run from skunks/oneshot after npm ci in recon:  node scripts/sigma-rust-p2sh-repro.cjs
const w = require(require('node:module').createRequire(__dirname + '/../recon/package.json').resolve('ergo-lib-wasm-nodejs'));
const addr = 'rNoPVtL9L9cuzgqQqkPsqo9VginDU6dBAtBamSU';
const t = w.Address.from_base58(addr).to_ergo_tree();
const hex = t.to_base16_bytes();
console.log('to_ergo_tree bytes', hex);
const t2 = w.ErgoTree.from_base16_bytes(hex);
console.log('from_base16_bytes ok; methods', Object.getOwnPropertyNames(Object.getPrototypeOf(t2)).join(' '));
for (const m of ['constants_len', 'template_bytes']) { try { console.log(m, String(t2[m]())); } catch (e) { console.log(m, 'throws:', String(e)); } }
try { console.log('recreate', w.Address.recreate_from_ergo_tree(t2).to_base58(w.NetworkPrefix.Testnet)); } catch (e) { console.log('recreate throws:', String(e)); }
try { console.log('recreate(from to_ergo_tree object)', w.Address.recreate_from_ergo_tree(t).to_base58(w.NetworkPrefix.Testnet)); } catch (e) { console.log('recreate throws:', String(e)); }
const fleet = '00ea02d193b4cbe4e3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801';
try { console.log('fleet tree recreate', w.Address.recreate_from_ergo_tree(w.ErgoTree.from_base16_bytes(fleet)).to_base58(w.NetworkPrefix.Testnet)); } catch (e) { console.log('fleet throws:', String(e)); }
