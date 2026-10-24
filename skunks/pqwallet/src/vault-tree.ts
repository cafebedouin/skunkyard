// The quantum-day vault's trees for a key, by substitution into pinned files (pqwallet step 4).
//
// skunks/qvault/QVault2.es and QDay.es were compiled ONCE (scripts/pin-trees.ts, the node's /script/p2sAddress with
// treeVersion 1, the compiler the devnet run used) with the mainnet schedule constants and distinctive placeholder
// bytes for every per-owner constant; the trees are pinned in trees/QVault2.tree and trees/QDay.tree, the placeholder
// offsets in trees/pins.json. A wallet builds an address by writing its constants over the placeholder bytes at those
// offsets; nothing is recompiled per key (the rule adopted after the gate's seat round: substitution into a pinned
// tree, never template equality, never a per-key compile). Every load checks that each placeholder occurs exactly the
// pinned number of times, that every substituted value has the placeholder's length, and that substituting the
// placeholder values back reproduces the pinned file byte for byte.
//
// BACKSTOP is an Int constant (zigzag VLQ): a real backstop must encode to as many bytes as the placeholder
// (777,777: three bytes, like every height in 8,192 .. 1,048,575), which backstopOk() checks before substitution.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { blake2b256, cat, hex, unhex, utf8 } from './bytes.js';

const HERE = dirname(fileURLToPath(import.meta.url));
export const TREES_DIR = join(HERE, '..', 'trees');
export const QVAULT_DIR = join(HERE, '..', '..', 'qvault');

/** The mainnet schedule constants (QVault2.es header), fixed in the pinned trees. */
export const SCHEDULE = { PERIOD: 1_051_200, WINDOW: 21_600, PER_INPUT: 500_000, REFRESH: 2_000_000, SLACK: 10 };

/**
 * Placeholder bytes, distinctive and deterministic: the 32-byte ones are blake2b256("pqwallet/placeholder/<NAME>");
 * the two points are the canonical BIP39 test mnemonic's EIP-3 keys 0 and 1 (valid curve points, never funded);
 * BACKSTOP 777,777 (a three-byte zigzag VLQ).
 */
export const PLACEHOLDER = {
  OWNER: '02b7da363cb84d41d10193c97e4fcdc35189e12ff963e39f386aba766fa796ea50', // test mnemonic m/44'/429'/0'/0/0
  ORACLE: '02ba70903563f312de15a348cae383316618d6c0d731633567fb8496e20b571722', // test mnemonic m/44'/429'/0'/0/1
  QDAY_NFT: hex(blake2b256(utf8('pqwallet/placeholder/QDAY_NFT'))),
  PKSEED: hex(blake2b256(utf8('pqwallet/placeholder/PKSEED'))),
  PKCOMMIT: hex(blake2b256(utf8('pqwallet/placeholder/PKCOMMIT'))),
  SUCCESSOR: hex(blake2b256(utf8('pqwallet/placeholder/SUCCESSOR'))),
  BACKSTOP: 777_777,
};

/** Ergo's Int constant encoding: zigzag, then VLQ (SInt constants and Int fields of the tree). */
export function zigzagVlq(v: number): Uint8Array {
  if (!Number.isInteger(v) || v < -2147483648 || v > 2147483647) throw new Error(`not an Int: ${v}`);
  let z = v >= 0 ? v * 2 : -v * 2 - 1;
  const out: number[] = [];
  do { let b = z & 0x7f; z = Math.floor(z / 128); if (z > 0) b |= 0x80; out.push(b); } while (z > 0);
  return Uint8Array.from(out);
}

export function backstopOk(h: number): boolean {
  return zigzagVlq(h).length === zigzagVlq(PLACEHOLDER.BACKSTOP).length;
}

export type QVault2Constants = { OWNER: string; QDAY_NFT: string; PKSEED: string; PKCOMMIT: string; SUCCESSOR: string; BACKSTOP: number };
export type QDayConstants = { ORACLE: string };

/** QVault2.es with every `$NAME` replaced textually: the map devnet-test-v2.py uses (`$PER_INPUTL` -> "500000L"). */
export function qvault2Source(c: QVault2Constants): string {
  let s = readFileSync(join(QVAULT_DIR, 'QVault2.es'), 'utf8');
  const subs: Record<string, string> = {
    '$OWNER': c.OWNER, '$QDAY_NFT': c.QDAY_NFT, '$BACKSTOP': String(c.BACKSTOP), '$PKCOMMIT': c.PKCOMMIT,
    '$PKSEED': c.PKSEED, '$SUCCESSOR': c.SUCCESSOR, '$PER_INPUTL': `${SCHEDULE.PER_INPUT}L`, '$REFRESHL': `${SCHEDULE.REFRESH}L`,
    '$PERIOD': String(SCHEDULE.PERIOD), '$WINDOW': String(SCHEDULE.WINDOW), '$SLACK': String(SCHEDULE.SLACK),
  };
  for (const [k, v] of Object.entries(subs)) s = s.split(k).join(v);
  if (s.includes('$')) throw new Error('QVault2.es: a placeholder was not substituted');
  return s;
}

export function qdaySource(c: QDayConstants): string {
  let s = readFileSync(join(QVAULT_DIR, 'QDay.es'), 'utf8');
  const subs: Record<string, string> = { '$ORACLE': c.ORACLE, '$PERIOD': String(SCHEDULE.PERIOD), '$WINDOW': String(SCHEDULE.WINDOW), '$SLACK': String(SCHEDULE.SLACK) };
  for (const [k, v] of Object.entries(subs)) s = s.split(k).join(v);
  if (s.includes('$')) throw new Error('QDay.es: a placeholder was not substituted');
  return s;
}

// ---- the pinned trees

export type Pin = {
  /** placeholder name -> every offset of its bytes in the pinned tree (all are substituted) */
  offsets: Record<string, number[]>;
  /** placeholder name -> the placeholder's bytes as they stand in the tree (hex) */
  placeholders: Record<string, string>;
  bytes: number;
  header: string;
  zeroedHash: string;
};
export type Pins = { compiler: Record<string, unknown>; QVault2: Pin; QDay: Pin };

export function loadPins(): Pins {
  return JSON.parse(readFileSync(join(TREES_DIR, 'pins.json'), 'utf8')) as Pins;
}

export function loadPinnedTree(name: 'QVault2' | 'QDay'): Uint8Array {
  return unhex(readFileSync(join(TREES_DIR, `${name}.tree`), 'utf8').trim());
}

/** Every offset at which `needle` occurs in `hay`. */
export function findAll(hay: Uint8Array, needle: Uint8Array): number[] {
  const out: number[] = [];
  outer: for (let i = 0; i + needle.length <= hay.length; i++) {
    for (let j = 0; j < needle.length; j++) if (hay[i + j] !== needle[j]) continue outer;
    out.push(i);
  }
  return out;
}

/** The pinned tree, checked against pins.json: each placeholder occurs exactly at the pinned offsets and nowhere else. */
export function checkedTemplate(name: 'QVault2' | 'QDay'): { tree: Uint8Array; pin: Pin } {
  const pin = loadPins()[name];
  const tree = loadPinnedTree(name);
  if (tree.length !== pin.bytes) throw new Error(`${name}.tree is ${tree.length} bytes, pinned ${pin.bytes}`);
  for (const [k, ph] of Object.entries(pin.placeholders)) {
    const found = findAll(tree, unhex(ph));
    const want = pin.offsets[k];
    if (found.length !== want.length || found.some((o, i) => o !== want[i])) {
      throw new Error(`${name}: placeholder ${k} found at ${JSON.stringify(found)}, pinned ${JSON.stringify(want)}`);
    }
  }
  return { tree, pin };
}

/** Write `values` (name -> bytes) over the placeholders of the pinned tree; lengths must match. */
export function substitute(name: 'QVault2' | 'QDay', values: Record<string, Uint8Array>): Uint8Array {
  const { tree, pin } = checkedTemplate(name);
  const out = tree.slice();
  for (const [k, offs] of Object.entries(pin.offsets)) {
    const v = values[k];
    if (!v) throw new Error(`${name}: no value for ${k}`);
    const ph = unhex(pin.placeholders[k]);
    if (v.length !== ph.length) throw new Error(`${name}: ${k} is ${v.length} bytes, the placeholder ${ph.length}`);
    for (const o of offs) out.set(v, o);
  }
  for (const k of Object.keys(values)) if (!(k in pin.offsets)) throw new Error(`${name}: unknown constant ${k}`);
  return out;
}

export function placeholderValues(name: 'QVault2' | 'QDay'): Record<string, Uint8Array> {
  const pin = loadPins()[name];
  return Object.fromEntries(Object.entries(pin.placeholders).map(([k, v]) => [k, unhex(v)]));
}

/** Check (c): substituting the placeholder values reproduces the pinned file byte for byte. */
export function checkRoundTrip(name: 'QVault2' | 'QDay'): boolean {
  const got = substitute(name, placeholderValues(name));
  return hex(got) === hex(loadPinnedTree(name));
}

export function qvault2Tree(c: QVault2Constants): Uint8Array {
  if (!backstopOk(c.BACKSTOP)) throw new Error(`BACKSTOP ${c.BACKSTOP} does not encode to ${zigzagVlq(PLACEHOLDER.BACKSTOP).length} bytes`);
  return substitute('QVault2', {
    OWNER: unhex(c.OWNER), QDAY_NFT: unhex(c.QDAY_NFT), PKSEED: unhex(c.PKSEED), PKCOMMIT: unhex(c.PKCOMMIT),
    SUCCESSOR: unhex(c.SUCCESSOR), BACKSTOP: zigzagVlq(c.BACKSTOP),
  });
}

export function qdayTree(c: QDayConstants): Uint8Array {
  return substitute('QDay', { ORACLE: unhex(c.ORACLE) });
}

/** The pinned tree with every per-owner constant zeroed (BACKSTOP's VLQ bytes too), hashed: the template's identity. */
export function zeroedHash(name: 'QVault2' | 'QDay'): string {
  const pin = loadPins()[name];
  const zeros = Object.fromEntries(Object.entries(pin.placeholders).map(([k, v]) => [k, new Uint8Array(v.length / 2)]));
  return hex(blake2b256(substitute(name, zeros)));
}

export { cat };
