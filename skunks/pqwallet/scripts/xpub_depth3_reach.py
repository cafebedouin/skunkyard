# Pure-python BIP32 witness: what a depth-3 xpub m/44'/429'/0' reaches given a discrete-log oracle.
# The "oracle" is simulated: we take the account scalar from the seed derivation and hand ONLY
# (k_acct, c_acct) to the attacker functions; the attacker never sees the seed or master.
import hashlib, hmac, unicodedata

P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def add(p, q):
    if p is None: return q
    if q is None: return p
    if p[0] == q[0] and (p[1] + q[1]) % P == 0: return None
    if p == q: l = 3 * p[0] * p[0] * pow(2 * p[1], -1, P) % P
    else: l = (q[1] - p[1]) * pow(q[0] - p[0], -1, P) % P
    x = (l * l - p[0] - q[0]) % P
    return (x, (l * (p[0] - x) - p[1]) % P)

def mul(k, p=G):
    r = None
    while k:
        if k & 1: r = add(r, p)
        p = add(p, p); k >>= 1
    return r

def ser(pt): return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, 'big')
H = 0x80000000

def ckd_priv(k, c, i):
    data = (b'\x00' + k.to_bytes(32, 'big') if i >= H else ser(mul(k))) + i.to_bytes(4, 'big')
    I = hmac.new(c, data, hashlib.sha512).digest()
    return (int.from_bytes(I[:32], 'big') + k) % N, I[32:]

def ckd_pub(K, c, i):
    assert i < H
    I = hmac.new(c, ser(K) + i.to_bytes(4, 'big'), hashlib.sha512).digest()
    return add(mul(int.from_bytes(I[:32], 'big')), K), I[32:]

def path(k, c, idx):
    for i in idx: k, c = ckd_priv(k, c, i)
    return k, c

mn = "abandon " * 11 + "about"
seed = hashlib.pbkdf2_hmac('sha512', unicodedata.normalize('NFKD', mn).encode(), b'mnemonic', 2048)
I = hmac.new(b'Bitcoin seed', seed, hashlib.sha512).digest()
km, cm = int.from_bytes(I[:32], 'big'), I[32:]

# Victim side: depth-3 account node, exported as xpub (K_acct, c_acct)
k_acct, c_acct = path(km, cm, [44 + H, 429 + H, 0 + H])
K_acct = mul(k_acct)
# Attacker side: xpub plus DL oracle -> k_acct (simulated); attacker holds only (k_acct, c_acct)
k_att, c_att = k_acct, c_acct
assert mul(k_att) == K_acct

# 1. Every EIP-3 address key below the node, used or not
for j in (0, 7, 1000):
    want, _ = path(km, cm, [44 + H, 429 + H, 0 + H, 0, j])
    got, _ = path(k_att, c_att, [0, j])
    print(f"m/44'/429'/0'/0/{j}: attacker == victim:", got == want)
# 2. Hardened descendants below the node too (needs the private key, which the oracle gave)
want, _ = path(km, cm, [44 + H, 429 + H, 0 + H, 5 + H, 3 + H])
got, _ = path(k_att, c_att, [5 + H, 3 + H])
print("m/44'/429'/0'/5'/3' (hardened under the node): attacker == victim:", got == want)
# 3. Without the oracle, the xpub alone still yields every non-hardened public key below
Kp, cp = ckd_pub(K_acct, c_acct, 0); Kp, cp = ckd_pub(Kp, cp, 7)
print("xpub-only public key m/44'/429'/0'/0/7 matches:", Kp == mul(path(km, cm, [44+H,429+H,0+H,0,7])[0]))
# 4. Nodes NOT below the account node: the attacker's material is (k_acct, c_acct); these values are
#    functions of (km, cm) or of the seed through a path that never passes the account node.
others = {
    "m/44'/429'/1'": path(km, cm, [44 + H, 429 + H, 1 + H])[0],
    "m/44'/429'":    path(km, cm, [44 + H, 429 + H])[0],
    "m/8391'/429'/0'/1'/0'/0'": path(km, cm, [8391 + H, 429 + H, 0 + H, 1 + H, 0 + H, 0 + H])[0],
}
for name, v in others.items():
    print(f"{name}: not on the account node's subtree (requires parent private key AND parent chain code above m/44'/429'/0')")
rootB = hmac.new(b'ergo-pq/v1', seed, hashlib.sha512).digest()
print("rule-B root key half:", rootB[:32].hex())
print("account xpub chain code:", c_acct.hex(), " pub:", ser(K_acct).hex())
