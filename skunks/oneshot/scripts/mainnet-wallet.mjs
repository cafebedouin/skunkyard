// scripts/mainnet-wallet.mjs: a fresh MAINNET wallet for skunkyard tests, the twin of testnet-wallet.mjs.
//
// Generates a BIP39 24-word mnemonic (256 bits of entropy, English wordlist, no passphrase), derives the EIP-3 key
// m/44'/429'/0'/0/0 with @fleet-sdk/wallet, and prints its MAINNET P2PK address and nothing else. The mnemonic goes
// to $HOME/.config/skunkyard/mainnet-wallet.txt and the address to mainnet-wallet.address beside it (directory mode
// 0700, files mode 0600, created exclusively: an existing file is never overwritten). The mnemonic is never printed.
// It restores in any EIP-3 wallet (Nautilus, a node's /wallet/restore) to the same first address; the script reads
// the file back and checks that before it reports success. Real money: keep only what a test needs in it.
//
// Usage: node scripts/mainnet-wallet.mjs            (from skunks/oneshot, after npm ci)
import { chmodSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { Network } from '@fleet-sdk/core';
import { ErgoHDKey, generateMnemonic, validateMnemonic } from '@fleet-sdk/wallet';

const PATH = "m/44'/429'/0'/0/0";
const dir = join(homedir(), '.config', 'skunkyard');
const file = join(dir, 'mainnet-wallet.txt');
const addrFile = join(dir, 'mainnet-wallet.address');

const mnemonic = generateMnemonic(256);
if (mnemonic.split(' ').length !== 24 || !validateMnemonic(mnemonic)) throw new Error('mnemonic generation failed');
const address = ErgoHDKey.fromMnemonicSync(mnemonic, { path: PATH }).address.encode(Network.Mainnet);

mkdirSync(dir, { recursive: true, mode: 0o700 });
chmodSync(dir, 0o700);
for (const [f, body] of [[file, `${mnemonic}\n`], [addrFile, `${address}\n`]]) {
  try {
    // flag 'wx': fail if the file exists
    writeFileSync(f, body, { mode: 0o600, flag: 'wx' });
  } catch (e) {
    if (e && e.code === 'EEXIST') {
      console.error(`refusing to overwrite ${f}; stopping`);
      process.exit(1);
    }
    throw e;
  }
  chmodSync(f, 0o600);
}

// Recoverability: what was written must derive the same address
const back = readFileSync(file, 'utf8').trim();
const again = ErgoHDKey.fromMnemonicSync(back, { path: PATH }).address.encode(Network.Mainnet);
if (!validateMnemonic(back) || again !== address) throw new Error(`read-back mismatch in ${file}`);
console.log(address);
