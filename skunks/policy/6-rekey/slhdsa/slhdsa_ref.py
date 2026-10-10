#!/usr/bin/env python3
"""SLH-DSA-SHA2-128s verification, written from the FIPS 205 pseudo-code, exposing intermediates (SK-053 step 3,
stage 1). Verification only; the signer is BouncyCastle (SlhDsaRunner.scala). Run with `python3 -I`.

    python3 -I slhdsa_ref.py vectors.json          # verify the BC signature in vectors.json, print intermediates
    python3 -I slhdsa_ref.py vectors.json --write  # also write the intermediates back as stage vectors

vectors.json (written by the Scala harness): {"pk": hex (PK.seed ‖ PK.root, 32 B), "msg": hex (the 32-byte spend
digest), "sig": hex (7,856 B), "ctx": hex (empty)}. The script's message is the FIPS 205 pure M' =
toByte(0,1) ‖ toByte(|ctx|,1) ‖ ctx ‖ M (§10.2.1, Algorithm 24), which is what BC's SLHDSASigner signs for ctx = "".

Parameter set SLH-DSA-SHA2-128s (FIPS 205 Table 2): n 16, h 63, d 7, h' 9, a 12, k 14, lg_w 4, m 30.
Tweakable hashes (§11.2.1, "simple" instantiations, category 1):
  F, H, T_l(PK.seed, ADRS, M) = Trunc_16(SHA-256(PK.seed ‖ toByte(0, 48) ‖ ADRS_c ‖ M))
  H_msg(R, PK.seed, PK.root, M) = MGF1-SHA-256(R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M), 30)
ADRS_c (22 B) = ADRS[3] ‖ ADRS[8:16] ‖ ADRS[19] ‖ ADRS[20:32]  (layer 1 B, tree 8 B, type 1 B, three 4-B words).
"""
import hashlib, json, sys

N, H, D, HP, A, K, LG_W, M_LEN = 16, 63, 7, 9, 12, 14, 4, 30
W = 1 << LG_W                 # 16
LEN1 = 2 * N                  # 32 (8n / lg_w)
LEN2 = 3
LEN = LEN1 + LEN2             # 35
SIG_FORS_LEN = K * (1 + A) * N    # 2,912
SIG_HT_LEN = D * (HP + LEN) * N   # 4,928
SIG_LEN = N + SIG_FORS_LEN + SIG_HT_LEN  # 7,856

WOTS_HASH, WOTS_PK, TREE, FORS_TREE, FORS_ROOTS = 0, 1, 2, 3, 4


def sha256(b):
    return hashlib.sha256(b).digest()


# ---- ADRS (FIPS 205 §4.3): a 32-byte array with setters -------------------------------------------------------

class Adrs:
    def __init__(self):
        self.b = bytearray(32)

    def copy(self):
        a = Adrs(); a.b = bytearray(self.b); return a

    def set_layer(self, l):        self.b[0:4] = l.to_bytes(4, "big")
    def set_tree(self, t):         self.b[4:16] = t.to_bytes(12, "big")
    def set_type_and_clear(self, y):
        self.b[16:20] = y.to_bytes(4, "big"); self.b[20:32] = bytes(12)
    def set_key_pair(self, i):     self.b[20:24] = i.to_bytes(4, "big")
    def set_chain(self, i):        self.b[24:28] = i.to_bytes(4, "big")
    def set_hash(self, i):         self.b[28:32] = i.to_bytes(4, "big")
    def set_tree_height(self, i):  self.b[24:28] = i.to_bytes(4, "big")
    def set_tree_index(self, i):   self.b[28:32] = i.to_bytes(4, "big")
    def get_key_pair(self):        return int.from_bytes(self.b[20:24], "big")
    def get_tree_index(self):      return int.from_bytes(self.b[28:32], "big")

    def compressed(self):
        """ADRS_c, §11.2: layer (1 B) ‖ tree address low 8 B ‖ type (1 B) ‖ the three words (12 B) = 22 bytes."""
        return bytes([self.b[3]]) + bytes(self.b[8:16]) + bytes([self.b[19]]) + bytes(self.b[20:32])


# ---- Tweakable hashes (§11.2.1) ------------------------------------------------------------------------------

HASH_CALLS = [0, 0, 0]   # tweakable-hash calls, input bytes, and the interpreter's charge for them in JIT units


def sha256_jit(n_bytes):
    """What the interpreter charges one sha256 call: PerItemCost(baseCost 80, perChunkCost 8, chunkSize 64) in JIT
    units (ergo-capabilities.md §3); block-cost units are JIT / 10 (q2/LIMITS.md §2). The same formula with
    blake2b256's (20, 7, 128) gives 2.7 per 32-byte call, 2,673 for q2's 990 chain hashes: q2/RESULT.md measured 2,673."""
    return 80 + 8 * ((n_bytes + 63) // 64)


def th(pk_seed, adrs, m):
    """F, H and T_l are the same function for SHA2 category 1; only the message length differs."""
    data = pk_seed + bytes(64 - N) + adrs.compressed() + m
    HASH_CALLS[0] += 1
    HASH_CALLS[1] += len(data)
    HASH_CALLS[2] += sha256_jit(len(data))
    return sha256(data)[:N]


def h_msg(r, pk_seed, pk_root, m):
    inner = sha256(r + pk_seed + pk_root + m)
    seed = r + pk_seed + inner
    out = b""
    for counter in range((M_LEN + 31) // 32):        # MGF1-SHA-256, one block for m = 30
        out += sha256(seed + counter.to_bytes(4, "big"))
    return out[:M_LEN]


# ---- Helpers (§4.4) ------------------------------------------------------------------------------------------

def base_2b(x, b, out_len):
    i = bits = total = 0
    out = []
    for _ in range(out_len):
        while bits < b:
            total = (total << 8) + x[i]; i += 1; bits += 8
        bits -= b
        out.append((total >> bits) % (1 << b))
    return out


# ---- WOTS+ (§5) ----------------------------------------------------------------------------------------------

def chain(x, i, s, pk_seed, adrs):
    tmp = x
    for j in range(i, i + s):
        adrs.set_hash(j)
        tmp = th(pk_seed, adrs, tmp)
    return tmp


def wots_pk_from_sig(sig, m, pk_seed, adrs, trace=None):
    msg = base_2b(m, LG_W, LEN1)
    csum = sum(W - 1 - d for d in msg)
    csum <<= (8 - ((LEN2 * LG_W) % 8)) % 8            # 4 for 128s
    msg = msg + base_2b(csum.to_bytes((LEN2 * LG_W + 7) // 8, "big"), LG_W, LEN2)
    tmp = []
    for i in range(LEN):
        adrs.set_chain(i)
        tmp.append(chain(sig[i * N:(i + 1) * N], msg[i], W - 1 - msg[i], pk_seed, adrs))
    pk_adrs = adrs.copy()
    pk_adrs.set_type_and_clear(WOTS_PK)
    pk_adrs.set_key_pair(adrs.get_key_pair())
    pk = th(pk_seed, pk_adrs, b"".join(tmp))
    if trace is not None:
        trace.update(digits=msg, chain_ends=[t.hex() for t in tmp], wots_pk=pk.hex(),
                     wots_pk_adrs_c=pk_adrs.compressed().hex())
    return pk


# ---- XMSS (§6) -----------------------------------------------------------------------------------------------

def xmss_pk_from_sig(idx, sig_xmss, m, pk_seed, adrs, trace=None):
    adrs.set_type_and_clear(WOTS_HASH)
    adrs.set_key_pair(idx)
    sig = sig_xmss[:LEN * N]
    auth = sig_xmss[LEN * N:]
    node = wots_pk_from_sig(sig, m, pk_seed, adrs, trace)
    adrs.set_type_and_clear(TREE)
    adrs.set_tree_index(idx)
    path = []
    for k in range(HP):
        adrs.set_tree_height(k + 1)
        if (idx >> k) % 2 == 0:
            adrs.set_tree_index(adrs.get_tree_index() // 2)
            node = th(pk_seed, adrs, node + auth[k * N:(k + 1) * N])
        else:
            adrs.set_tree_index((adrs.get_tree_index() - 1) // 2)
            node = th(pk_seed, adrs, auth[k * N:(k + 1) * N] + node)
        path.append(node.hex())
    if trace is not None:
        trace.update(xmss_nodes=path, xmss_root=node.hex())
    return node


# ---- Hypertree (§7) ------------------------------------------------------------------------------------------

def ht_verify(m, sig_ht, pk_seed, idx_tree, idx_leaf, pk_root, trace=None):
    adrs = Adrs()
    adrs.set_tree(idx_tree)
    layers = []
    node = m
    for j in range(D):
        if j > 0:
            idx_leaf = idx_tree % (1 << HP)
            idx_tree >>= HP
            adrs.set_layer(j)
            adrs.set_tree(idx_tree)
        t = {"layer": j, "idx_tree": idx_tree, "idx_leaf": idx_leaf, "input": node.hex()}
        sig_tmp = sig_ht[j * (HP + LEN) * N:(j + 1) * (HP + LEN) * N]
        node = xmss_pk_from_sig(idx_leaf, sig_tmp, node, pk_seed, adrs, t)
        layers.append(t)
    if trace is not None:
        trace["layers"] = layers
        trace["ht_root"] = node.hex()
    return node == pk_root


# ---- FORS (§8) -----------------------------------------------------------------------------------------------

def fors_pk_from_sig(sig_fors, md, pk_seed, adrs, trace=None):
    indices = base_2b(md, A, K)
    roots = []
    for i in range(K):
        sk = sig_fors[i * (A + 1) * N:i * (A + 1) * N + N]
        adrs.set_tree_height(0)
        adrs.set_tree_index(i * (1 << A) + indices[i])
        node = th(pk_seed, adrs, sk)
        auth = sig_fors[i * (A + 1) * N + N:(i + 1) * (A + 1) * N]
        for j in range(A):
            adrs.set_tree_height(j + 1)
            if (indices[i] >> j) % 2 == 0:
                adrs.set_tree_index(adrs.get_tree_index() // 2)
                node = th(pk_seed, adrs, node + auth[j * N:(j + 1) * N])
            else:
                adrs.set_tree_index((adrs.get_tree_index() - 1) // 2)
                node = th(pk_seed, adrs, auth[j * N:(j + 1) * N] + node)
        roots.append(node)
    pk_adrs = adrs.copy()
    pk_adrs.set_type_and_clear(FORS_ROOTS)
    pk_adrs.set_key_pair(adrs.get_key_pair())
    pk = th(pk_seed, pk_adrs, b"".join(roots))
    if trace is not None:
        trace.update(fors_indices=indices, fors_roots=[r.hex() for r in roots], fors_pk=pk.hex(),
                     fors_pk_adrs_c=pk_adrs.compressed().hex())
    return pk


# ---- slh_verify_internal (§9.3, Algorithm 20) -----------------------------------------------------------------

def verify_internal(m, sig, pk, trace=None):
    if len(sig) != SIG_LEN:
        return False
    pk_seed, pk_root = pk[:N], pk[N:]
    r = sig[:N]
    sig_fors = sig[N:N + SIG_FORS_LEN]
    sig_ht = sig[N + SIG_FORS_LEN:]
    digest = h_msg(r, pk_seed, pk_root, m)
    md = digest[:(K * A + 7) // 8]                                   # 21 bytes
    tmp_idx_tree = digest[21:21 + (H - H // D + 7) // 8]             # 7 bytes
    tmp_idx_leaf = digest[28:28 + (H // D + 7) // 8]                 # 2 bytes
    idx_tree = int.from_bytes(tmp_idx_tree, "big") % (1 << (H - H // D))   # mod 2^54
    idx_leaf = int.from_bytes(tmp_idx_leaf, "big") % (1 << (H // D))       # mod 2^9
    adrs = Adrs()
    adrs.set_tree(idx_tree)
    adrs.set_type_and_clear(FORS_TREE)
    adrs.set_key_pair(idx_leaf)
    if trace is not None:
        trace.update(m_prime=m.hex(), r=r.hex(), digest=digest.hex(), md=md.hex(),
                     idx_tree=idx_tree, idx_leaf=idx_leaf)
    pk_fors = fors_pk_from_sig(sig_fors, md, pk_seed, adrs, trace)
    return ht_verify(pk_fors, sig_ht, pk_seed, idx_tree, idx_leaf, pk_root, trace)


def verify(m, ctx, sig, pk, trace=None):
    """slh_verify (Algorithm 24): the pure, non-prehash form with a context string."""
    if len(ctx) > 255:
        return False
    m_prime = bytes([0, len(ctx)]) + ctx + m
    return verify_internal(m_prime, sig, pk, trace)


def spends(v):
    """spends.json from the harness: the verifier's measured cost per spend beside the reference's chain-step count,
    a least-squares cost per WOTS+ chain step, and the worst case (every chain 15 steps) extrapolated from it."""
    pk = bytes.fromhex(v["pk"])
    rows = []
    for i, s in enumerate(v["spends"]):
        HASH_CALLS[0] = HASH_CALLS[1] = HASH_CALLS[2] = 0
        trace = {}
        m = bytes.fromhex(s["msg"])
        ok = verify(m, b"", bytes.fromhex(s["sig"]), pk, trace)
        steps = sum(sum(W - 1 - d for d in t["digits"]) for t in trace["layers"])
        rows.append((steps, s["cost"]))
        # H_msg's two sha256 calls: 16 + 16 + 16 + 34 = 82 bytes and 16 + 16 + 32 + 4 = 68 bytes
        hash_units = (HASH_CALLS[2] + sha256_jit(82) + sha256_jit(68)) / 10
        print(f"ref-spend {i} valid={'ACCEPT' if ok else 'REFUSE'} wots_chain_steps={steps} tweakable_calls={HASH_CALLS[0]} "
              f"tweakable_input_bytes={HASH_CALLS[1]} script_cost={s['cost']} sha256_cost={hash_units:.1f} "
              f"hash_share={hash_units / s['cost']:.4f}")
    n = len(rows)
    sx, sy = sum(r[0] for r in rows), sum(r[1] for r in rows)
    sxx, sxy = sum(r[0] ** 2 for r in rows), sum(r[0] * r[1] for r in rows)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    icept = (sy - slope * sx) / n
    worst = D * LEN * (W - 1)
    resid = max(abs(c - (icept + slope * st)) for st, c in rows)
    print(f"ref-fit spends={n} cost_per_chain_step={slope:.1f} fixed={icept:.0f} max_residual={resid:.0f} "
          f"worst_case_steps={worst} cost_worst_est={icept + slope * worst:.0f} [est.: linear fit, not run]")


def main():
    path = sys.argv[1]
    with open(path) as f:
        v = json.load(f)
    if "spends" in v:
        spends(v)
        return
    pk, msg, sig = bytes.fromhex(v["pk"]), bytes.fromhex(v["msg"]), bytes.fromhex(v["sig"])
    ctx = bytes.fromhex(v.get("ctx", ""))
    trace = {}
    HASH_CALLS[0] = HASH_CALLS[1] = HASH_CALLS[2] = 0
    ok = verify(msg, ctx, sig, pk, trace)
    calls, hbytes, jit = HASH_CALLS
    bad = bytearray(sig); bad[0] ^= 1
    flipped = verify(msg, ctx, bytes(bad), pk)
    other = verify(msg[:-1] + bytes([msg[-1] ^ 1]), ctx, sig, pk)
    print(f"ref-verify sig_bytes={len(sig)} pk_bytes={len(pk)} valid={'ACCEPT' if ok else 'REFUSE'} "
          f"one_byte_flipped={'ACCEPT' if flipped else 'REFUSE'} other_message={'ACCEPT' if other else 'REFUSE'}")
    print(f"ref-indices idx_tree={trace['idx_tree']} idx_leaf={trace['idx_leaf']} "
          f"fors_indices={trace['fors_indices']}")
    print(f"ref-fors pk={trace['fors_pk']}")
    for t in trace["layers"]:
        print(f"ref-layer {t['layer']} idx_tree={t['idx_tree']} idx_leaf={t['idx_leaf']} "
              f"wots_pk={t['wots_pk']} xmss_root={t['xmss_root']}")
    print(f"ref-root ht_root={trace['ht_root']} pk_root={pk[N:].hex()} match={trace['ht_root'] == pk[N:].hex()}")
    wots_steps = sum(sum(W - 1 - d for d in t["digits"]) for t in trace["layers"])
    print(f"ref-hash tweakable_calls={calls} tweakable_input_bytes={hbytes} wots_chain_steps={wots_steps} "
          f"(worst case {D * LEN * (W - 1)}) h_msg_sha256_calls=2 sha256_cost_block_units={(jit + sha256_jit(82) + sha256_jit(68)) / 10:.1f}")
    if "--write" in sys.argv:
        # stage-2 vector: F at (layer 0, tree idx_tree, WOTS_HASH, key pair idx_leaf, chain 0, hash 0) on the first
        # WOTS+ signature element of layer 0; H is the first XMSS node of layer 0; T_len is layer 0's WOTS+ public key
        a = Adrs(); a.set_tree(trace["idx_tree"]); a.set_type_and_clear(WOTS_HASH); a.set_key_pair(trace["idx_leaf"])
        a.set_chain(0); a.set_hash(0)
        x0 = sig[N + SIG_FORS_LEN:N + SIG_FORS_LEN + N]
        v["stage2"] = {"x0": x0.hex(), "f0": th(pk[:N], a, x0).hex(), "adrs_c": a.compressed().hex(),
                       "auth0": sig[N + SIG_FORS_LEN + LEN * N:N + SIG_FORS_LEN + (LEN + 1) * N].hex()}
        v["ref"] = {"valid": ok, "flipped": flipped, "other": other, "tweakable_calls": calls,
                    "tweakable_input_bytes": hbytes, "wots_chain_steps": wots_steps, **trace}
        with open(path, "w") as f:
            json.dump(v, f, indent=1)
        print(f"ref-write {path}")
    sys.exit(0 if ok and not flipped and not other else 1)


if __name__ == "__main__":
    main()
