#!/usr/bin/env python3 -I
"""address-vector.py <tree-hex-file> <compressed-pubkey-hex> [--check <address-file>]: substitute the 33-byte owner
key at the KeepAlive address tree's constant 1 (bytes 8..40 inclusive, 0-based) and print the mainnet P2S address
(Base58 of 0x03 ++ tree ++ the first 4 bytes of Blake2b256(0x03 ++ tree)). With --check, first reproduces the
published address from the tree as is, so the encoding is validated before any substitution."""
import sys, hashlib
A='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58(b):
    n=int.from_bytes(b,'big'); s=''
    while n: n,r=divmod(n,58); s=A[r]+s
    return '1'*(len(b)-len(b.lstrip(b'\0')))+s
def p2s(tree):
    body=b'\x03'+tree
    return b58(body+hashlib.blake2b(body,digest_size=32).digest()[:4])
tree=bytes.fromhex(open(sys.argv[1]).read().strip()); key=bytes.fromhex(sys.argv[2]); assert len(key)==33
if '--check' in sys.argv:
    pub=open(sys.argv[sys.argv.index('--check')+1]).read().strip()
    print(f"check published={'OK' if p2s(tree)==pub else 'MISMATCH'} chars={len(pub)}")
assert tree[6:8]==b'\x0e\x21', "constant 1 is not a 33-byte Coll[Byte] at offset 6"
new=tree[:8]+key+tree[41:]; assert len(new)==len(tree)
print(f"key={key.hex()}")
print(f"tree_bytes={len(new)} tree_sha256={hashlib.sha256(new).hexdigest()}")
print(f"address={p2s(new)} chars={len(p2s(new))}")
