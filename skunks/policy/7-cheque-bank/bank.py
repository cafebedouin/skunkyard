"""Experiment 7 helpers: the AVL+ prover (AvlProver.scala) wrapper, AvlTree / collection encodings, and secp256k1
arithmetic for Schnorr cheques and hash-to-point (pure Python, affine coordinates; devnet test keys only)."""
import hashlib, json, os, secrets, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import vlq, coll_bytes  # noqa: E402

CP = (HERE / "target" / "cp.txt").read_text().strip() if (HERE / "target" / "cp.txt").exists() else None
STATE = HERE / "state"


def blake(b):
    return hashlib.blake2b(b, digest_size=32).digest()


# ---- AVL+ prover
def avl(log, vlen, ops, commit=False):
    args = ["java", "-cp", CP, "AvlProver", str(STATE / log), "none" if vlen is None else str(vlen)]
    if commit:
        args.append("--commit")
    out = subprocess.run(args + list(ops), capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError("AvlProver: " + out.stderr[-600:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def avl_tree_c(digest_hex, flags, vlen):
    """AvlTree constant: type 0x64, digest (33 B), enabled-operations flags (insert 1, update 2, remove 4),
    keyLength 32, valueLengthOpt."""
    v = "00" if vlen is None else "01" + vlq(vlen)
    return "64" + digest_hex + f"{flags:02x}" + vlq(32) + v


def kv_coll(pairs):
    """Coll[(Coll[Byte], Coll[Byte])]: type 0x0c 0x3c 0x0e 0x0e (Coll of Pair1 with two non-primitive types; code
    0x54 with element 0 would be read as a quadruple)."""
    s = "0c3c0e0e" + vlq(len(pairs))
    for k, v in pairs:
        s += vlq(len(k) // 2) + k + vlq(len(v) // 2) + v
    return s


def keys_coll(keys):
    """Coll[Coll[Byte]]: type 0x1a (Coll of Coll[Byte])."""
    return "1a" + vlq(len(keys)) + "".join(vlq(len(k) // 2) + k for k in keys)


def ge_coll(points):
    """Coll[GroupElement]: type 0x13 (Coll of GroupElement, primitive 7)."""
    return "13" + vlq(len(points)) + "".join(points)


# ---- secp256k1
P = 2 ** 256 - 2 ** 32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
Gpt = (GX, GY)


def add(p, q):
    if p is None:
        return q
    if q is None:
        return p
    if p[0] == q[0] and (p[1] + q[1]) % P == 0:
        return None
    if p == q:
        l = 3 * p[0] * p[0] * pow(2 * p[1], -1, P) % P
    else:
        l = (q[1] - p[1]) * pow(q[0] - p[0], -1, P) % P
    x = (l * l - p[0] - q[0]) % P
    return (x, (l * (p[0] - x) - p[1]) % P)


def mul(k, p=Gpt):
    k %= N
    r = None
    while k:
        if k & 1:
            r = add(r, p)
        p = add(p, p)
        k >>= 1
    return r


def enc(p):
    return ("02" if p[1] % 2 == 0 else "03") + f"{p[0]:064x}"


def dec(h):
    x = int(h[2:], 16)
    y = pow((x ** 3 + 7) % P, (P + 1) // 4, P)
    if y % 2 != int(h[:2], 16) % 2:
        y = P - y
    return (x, y)


def hash_to_point(seed):
    """Try-and-increment: decompress 0x02 ++ blake2b256(seed ++ counter) until x is on the curve."""
    c = 0
    while True:
        x = int.from_bytes(blake(seed + c.to_bytes(4, "big")), "big")
        if x < P:
            y2 = (x ** 3 + 7) % P
            y = pow(y2, (P + 1) // 4, P)
            if y * y % P == y2:
                return enc((x, y if y % 2 == 0 else P - y)), c
        c += 1


def bigint_bytes(n):
    """Signed big-endian two's complement, minimal (Java BigInteger.toByteArray), as byteArrayToBigInt reads it."""
    length = (n.bit_length() + 8) // 8
    return n.to_bytes(length, "big", signed=True)


def schnorr_sign(x, msg):
    """ChainCash's construct (contracts/onchain/note.es): e = byteArrayToBigInt(blake2b256(R ++ msg ++ pk)), signed;
    s = r + e x mod n, retried until s < 2^255 so it fits a signed 256-bit BigInt. Returns (R hex, s bytes hex)."""
    pk = bytes.fromhex(enc(mul(x)))
    while True:
        r = secrets.randbelow(N - 1) + 1
        R = bytes.fromhex(enc(mul(r)))
        e = int.from_bytes(blake(R + msg + pk), "big", signed=True)
        s = (r + e * x) % N
        if s < 2 ** 255:
            return R.hex(), bigint_bytes(s).hex()


def schnorr_verify(pk_hex, msg, R_hex, s_hex):
    e = int.from_bytes(blake(bytes.fromhex(R_hex) + msg + bytes.fromhex(pk_hex)), "big", signed=True)
    s = int.from_bytes(bytes.fromhex(s_hex), "big", signed=True)
    return mul(s) == add(dec(R_hex), mul(e, dec(pk_hex)))
