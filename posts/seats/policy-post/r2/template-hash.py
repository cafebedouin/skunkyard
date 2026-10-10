#!/usr/bin/env python3 -I
"""template-hash.py <tree-hex-file>: parse a constant-segregated ErgoTree, print its header, each constant's
type/offset/length, the key constant's byte offset, and the template's Blake2b256 (node index) and SHA-256 (explorer)
hashes. Handles the constant types these policy trees use: Boolean (01), Int (04), Long (05), Coll[Byte] (0e)."""
import sys, hashlib
h = bytes.fromhex(open(sys.argv[1]).read().strip())
def vlq(b, i):
    v = 0; s = 0
    while True:
        c = b[i]; i += 1; v |= (c & 0x7f) << s; s += 7
        if not c & 0x80: return v, i
def zz(u): return (u >> 1) ^ -(u & 1)
i = 0; header = h[i]; i += 1
assert header & 0x10, "not constant-segregated"
size = None
if header & 0x08: size, i = vlq(h, i)
n, i = vlq(h, i)
print(f"header=0x{header:02x} version={header & 7} size={size} constants={n}")
for k in range(n):
    t = h[i]; start = i
    if t == 0x01: val = h[i+1]; i += 2; desc = f"Boolean {bool(val)}"
    elif t == 0x04: u, i = vlq(h, i+1); desc = f"Int {zz(u)}"
    elif t == 0x05: u, i = vlq(h, i+1); desc = f"Long {zz(u)}"
    elif t == 0x0e: ln, j = vlq(h, i+1); desc = f"Coll[Byte] len={ln} bytes@{j}..{j+ln} {h[j:j+ln].hex()[:16]}…"; i = j + ln
    else: raise SystemExit(f"constant {k}: unhandled type 0x{t:02x} at {i}")
    print(f"  const {k}: offset={start} {desc}")
tpl = h[i:]
print(f"template bytes={len(tpl)} (tree bytes={len(h)})")
print(f"template blake2b256={hashlib.blake2b(tpl, digest_size=32).hexdigest()}")
print(f"template sha256={hashlib.sha256(tpl).hexdigest()}")
