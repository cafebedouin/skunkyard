// scripts/wots-cli.mts: the WOTS key and signer for harnesses outside TypeScript (run with tsx).
//
//   tsx scripts/wots-cli.mts commit <seedHex> <n> <w>
//       -> {"commitment": hex, "l1", "l2", "chains"}
//   tsx scripts/wots-cli.mts sign <seedHex> <n> <w> <boxIdHex> <outputs.json>
//       -> {"message": hex, "signature": hex}; outputs.json is the transaction's outputs in node JSON order
//          (value, ergoTree, creationHeight, assets, additionalRegisters), the message is the one
//          q2/wots-constant.es checks: blake2b256(boxId ++ outputs' bytesWithoutRef).slice(0, n). The signature is
//          verified here against the commitment before it is printed.
import { readFileSync } from 'node:fs';
import { spendMessage } from '../src/outputs.js';
import { bytesToHex, commitment, deriveKeys, hexToBytes, params, publicKey, sign, verify } from '../src/wots.js';

const [cmd, seedHex, nS, wS, boxId, outFile] = process.argv.slice(2);
const n = Number(nS), w = Number(wS);
const sk = deriveKeys(hexToBytes(seedHex), n, w);
const commit = commitment(publicKey(sk, w));
if (cmd === 'commit') {
  console.log(JSON.stringify({ commitment: bytesToHex(commit), ...params(n, w) }));
} else if (cmd === 'sign') {
  const outputs = JSON.parse(readFileSync(outFile, 'utf8')).map((o: any) => ({
    value: String(o.value), ergoTree: o.ergoTree, creationHeight: Number(o.creationHeight),
    assets: (o.assets ?? []).map((a: any) => ({ tokenId: a.tokenId, amount: String(a.amount) })),
    additionalRegisters: o.additionalRegisters ?? {},
  }));
  const msg = spendMessage(boxId, outputs, n);
  const sig = sign(sk, msg, w);
  if (!verify(commit, msg, sig, n, w)) throw new Error('signature does not verify against the commitment');
  console.log(JSON.stringify({ message: bytesToHex(msg), signature: bytesToHex(sig) }));
} else {
  throw new Error('usage: commit <seed> <n> <w> | sign <seed> <n> <w> <boxId> <outputs.json>');
}
