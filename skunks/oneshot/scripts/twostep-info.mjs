// scripts/twostep-info.mjs: print the test wallet's two-step trees and addresses' trees as JSON (public keys only;
// the mnemonic is read to derive them and never printed). For skunks/policy/2-twostep/mainnet/demo.py.
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { hex } from '@fleet-sdk/crypto';
import { ErgoHDKey } from '@fleet-sdk/wallet';
import { twostepTrees } from './twostep-trees.mjs';

const m = readFileSync(join(homedir(), '.config', 'skunkyard', 'mainnet-wallet.txt'), 'utf8').trim();
const owner = ErgoHDKey.fromMnemonicSync(m, { path: "m/44'/429'/0'/0/0" });
const recovery = ErgoHDKey.fromMnemonicSync(m, { path: "m/44'/429'/0'/0/1" });
const t = twostepTrees(hex.encode(owner.publicKey), hex.encode(recovery.publicKey));
console.log(JSON.stringify({ walletTree: '0008cd' + hex.encode(owner.publicKey), recoveryTree: '0008cd' + hex.encode(recovery.publicKey),
  vault: t.vault, pending: t.pending, delay: t.delay }));
