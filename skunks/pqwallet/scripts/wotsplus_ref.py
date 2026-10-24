#!/usr/bin/env python3
"""Reference WOTS+ keygen for the cross-check: the functions of skunks/qvault/devnet-test.py (wotsplus_keygen,
_wp_chain), copied verbatim except for the optional tweak prefix (the schedule's leaf index, RekeySchedule.es line 82).
Usage: wotsplus_ref.py <pkseed_hex> <secret_hex> [prefix_hex]   -> prints the commitment hex."""
import hashlib, sys

WL = 67

def _bl(b):
    return hashlib.blake2b(b, digest_size=32).digest()

def _wp_chain(pkseed, prefix, c, a, b, x):
    for s in range(a, b):
        x = _bl(pkseed + prefix + bytes([c, s]) + x)
    return x

def wotsplus_keygen(pkseed, secret, prefix=b""):
    sk = [_bl(secret + bytes([c])) for c in range(WL)]
    pk = b"".join(_wp_chain(pkseed, prefix, c, 0, 15, sk[c]) for c in range(WL))
    return sk, _bl(pkseed + pk)

if __name__ == "__main__":
    pkseed, secret = bytes.fromhex(sys.argv[1]), bytes.fromhex(sys.argv[2])
    prefix = bytes.fromhex(sys.argv[3]) if len(sys.argv) > 3 else b""
    print(wotsplus_keygen(pkseed, secret, prefix)[1].hex())
