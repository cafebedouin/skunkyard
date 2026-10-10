"""Block-extension Merkle tree, rebuilt off-chain (plan S12; node Extension.scala, scrypto MerkleTree):
leaf = 0x02 ++ key(2) ++ value; leaf hash = blake2b256(0x00 ++ leaf); node = blake2b256(0x01 ++ left ++ right);
an odd node is paired with an empty node whose hash is the empty string; leaves in insertion order."""
import hashlib


def h(b):
    return hashlib.blake2b(b, digest_size=32).digest()


def leaf(key_hex, val_hex):
    return bytes([2]) + bytes.fromhex(key_hex) + bytes.fromhex(val_hex)


def levels(fields):
    lvl = [h(b"\x00" + leaf(k, v)) for k, v in fields]
    out = [lvl]
    if len(lvl) == 1:
        lvl = [h(b"\x01" + lvl[0])]
        out.append(lvl)
    while len(lvl) > 1:
        nxt = []
        for i in range(0, len(lvl), 2):
            l = lvl[i]
            r = lvl[i + 1] if i + 1 < len(lvl) else b""
            nxt.append(h(b"\x01" + l + r))
        lvl = nxt
        out.append(lvl)
    return out


def root(fields):
    return levels(fields)[-1][0]


def proof(fields, idx):
    """[(sibling hash, sibling_is_left)] from leaf idx up to the root. An empty sibling has hash b''."""
    path = []
    lv = levels(fields)
    i = idx
    for lvl in lv[:-1]:
        if i % 2 == 0:
            sib = lvl[i + 1] if i + 1 < len(lvl) else b""
            path.append((sib, False))
        else:
            path.append((lvl[i - 1], True))
        i //= 2
    return path


def fold(leaf_bytes, path):
    acc = h(b"\x00" + leaf_bytes)
    for sib, left in path:
        acc = h(b"\x01" + sib + acc) if left else h(b"\x01" + acc + sib)
    return acc
