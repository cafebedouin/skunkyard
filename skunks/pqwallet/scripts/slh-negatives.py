#!/usr/bin/env python3
"""Structural negatives for the harness's `negatives` command, built from two honest noble spends (A, B) of one key in a
sigs file, with the reference's tweakable hash for the chain-forward cases. Also prints idx_tree / idx_leaf (raw field
bits and reduced) for every spend in the file. Usage: slh-negatives.py <sigs.json> <slhdsa dir> <extra named json or -> <out.json>"""
import importlib.util, json, sys
from pathlib import Path
sigs, slh, extra, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
spec = importlib.util.spec_from_file_location("slhdsa_ref", slh / "slhdsa_ref.py"); ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
k = json.load(open(sigs))["keys"][0]; pk = bytes.fromhex(k["pk"]); sp = k["spends"]
A, B = sp[0], sp[1]; sa, sb = bytes.fromhex(A["sig"]), bytes.fromhex(B["sig"]); ma = bytes.fromhex(A["msg"])
N, FORS_LEN, HT_LAYER = 16, 2912, 704
named = []
def add(name, sig, expected="REFUSE"): named.append({"name": name, "sig": sig.hex(), "expected": expected})
# per-node flips: every 16-byte node of A (491 nodes), bit 7 of the node's first byte
for node in range(len(sa) // N):
    s = bytearray(sa); s[node * N] ^= 0x80; add(f"flip_node_{node:03d}", bytes(s))
# grafts: A's R + FORS with B's hypertree; each hypertree layer of B into A
add("graft_A_fors_B_hypertree", sa[:N + FORS_LEN] + sb[N + FORS_LEN:])
for j in range(7):
    s = bytearray(sa); o = N + FORS_LEN + j * HT_LAYER; s[o:o + HT_LAYER] = sb[o:o + HT_LAYER]; add(f"graft_layer_{j}_from_B", bytes(s))
add("graft_B_R_into_A", sb[:N] + sa[N:])
# lengths: one under, one over, empty, 16 bytes, 65,536 bytes, a 32-byte rotation (legal length)
add("len_7855", sa[:-1]); add("len_7857", sa + b"\x00"); add("len_0", b""); add("len_16", sa[:16]); add("len_65536", (sa * 9)[:65536]); add("rotate_32", sa[32:] + sa[:32])
add("all_zero_7856", bytes(7856))
# checksum coupling in layer 0's WOTS+: replace a checksum chain element (chain 32..34) with its next hash forward, using the
# reference's tweakable hash at the right address; and swap two message chains' elements
tr = {}; assert ref.verify(ma, b"", sa, pk, tr)
idx_tree, idx_leaf = tr["idx_tree"], tr["idx_leaf"]
def adrs_chain(layer, tree, leaf, chain, step):
    a = ref.Adrs(); a.set_layer(layer) if hasattr(a, "set_layer") else None; a.set_tree(tree); a.set_type_and_clear(ref.WOTS_HASH); a.set_key_pair(leaf); a.set_chain(chain); a.set_hash(step); return a
l0 = N + FORS_LEN
digits0 = tr["layers"][0]["digits"]
for chain in (32, 33, 34):
    d = digits0[chain]
    if d >= 15: continue
    x = sa[l0 + chain * N: l0 + (chain + 1) * N]
    fwd = ref.th(pk[:N], adrs_chain(0, idx_tree, idx_leaf, chain, d), x)   # one step forward on that chain
    s = bytearray(sa); s[l0 + chain * N: l0 + (chain + 1) * N] = fwd; add(f"layer0_checksum_chain_{chain}_hashed_forward_from_digit_{d}", bytes(s))
s = bytearray(sa); s[l0:l0 + N], s[l0 + N:l0 + 2 * N] = sa[l0 + N:l0 + 2 * N], sa[l0:l0 + N]; add("layer0_chains_0_1_swapped", bytes(s))
# a message chain hashed forward (digit rises by one) with the original message: the checksum no longer matches
for chain in range(32):
    if digits0[chain] < 15:
        x = sa[l0 + chain * N: l0 + (chain + 1) * N]; fwd = ref.th(pk[:N], adrs_chain(0, idx_tree, idx_leaf, chain, digits0[chain]), x)
        s = bytearray(sa); s[l0 + chain * N: l0 + (chain + 1) * N] = fwd; add(f"layer0_message_chain_{chain}_hashed_forward", bytes(s)); break
if extra != "-":
    for e in json.load(open(extra))["named"]: named.append(e)
# indices for every spend in the file
rows = []
for s0 in sp:
    t = {}; ok = ref.verify(bytes.fromhex(s0["msg"]), b"", bytes.fromhex(s0["sig"]), pk, t)
    sig = bytes.fromhex(s0["sig"]); r = sig[:N]
    dg = ref.h_msg(r, pk[:N], pk[N:], bytes([0, 0]) + bytes.fromhex(s0["msg"]))
    raw_tree = int.from_bytes(dg[21:28], "big"); raw_leaf = int.from_bytes(dg[28:30], "big")
    rows.append({"i": s0["i"], "valid": ok, "idx_tree": t["idx_tree"], "idx_leaf": t["idx_leaf"], "raw_tree_field": raw_tree, "tree_bits_discarded_nonzero": raw_tree >> 54 != 0, "raw_leaf_field": raw_leaf, "leaf_bits_discarded_nonzero": raw_leaf >> 9 != 0})
nz_t = sum(r["tree_bits_discarded_nonzero"] for r in rows); nz_l = sum(r["leaf_bits_discarded_nonzero"] for r in rows)
print(f"indices spends={len(rows)} tree_field_high_bits_nonzero={nz_t} leaf_field_high_bits_nonzero={nz_l} idx_leaf_ge_256={sum(r['idx_leaf'] >= 256 for r in rows)} idx_leaf_min={min(r['idx_leaf'] for r in rows)} idx_leaf_max={max(r['idx_leaf'] for r in rows)}")
json.dump({"pk": k["pk"], "spends": sp[:2], "named": named, "indices": rows}, open(out, "w"))
print(f"slh-negatives named={len(named)} -> {out}")
