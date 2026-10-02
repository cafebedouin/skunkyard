// scripts/testnet-wallet.mjs: a fresh testnet wallet to fund the oneshot step 3 spends.
//
// Generates a BIP39 24-word mnemonic (256 bits of entropy, English wordlist, no passphrase), derives the EIP-3 key
// m/44'/429'/0'/0/0 with @fleet-sdk/wallet, and prints its TESTNET P2PK address and nothing else. The mnemonic goes
// to $HOME/.config/skunkyard/testnet-wallet.txt (directory mode 0700, file mode 0600, created exclusively: an existing
// file is never overwritten). It is never printed. Testnet only; do not send mainnet funds to anything derived here.
//
// Usage: node scripts/testnet-wallet.mjs            (from skunks/oneshot, after npm ci)
import { chmodSync, mkdirSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { Network } from '@fleet-sdk/core';
import { ErgoHDKey, generateMnemonic, validateMnemonic } from '@fleet-sdk/wallet';

const PATH = "m/44'/429'/0'/0/0";
const dir = join(homedir(), '.config', 'skunkyard');
const file = join(dir, 'testnet-wallet.txt');

const mnemonic = generateMnemonic(256);
if (mnemonic.split(' ').length !== 24 || !validateMnemonic(mnemonic)) throw new Error('mnemonic generation failed');
const key = ErgoHDKey.fromMnemonicSync(mnemonic, { path: PATH });
const address = key.address.encode(Network.Testnet);

mkdirSync(dir, { recursive: true, mode: 0o700 });
chmodSync(dir, 0o700);
try {
  // flag 'wx': fail if the file exists
  writeFileSync(file, `${mnemonic}\n`, { mode: 0o600, flag: 'wx' });
} catch (e) {
  if (e && e.code === 'EEXIST') {
    console.error(`refusing to overwrite ${file}; nothing written`);
    process.exit(1);
  }
  throw e;
}
chmodSync(file, 0o600);
console.log(address);
