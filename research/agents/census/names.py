"""Names for template hashes (U1b line f). Hand labels, each with its source, take precedence; otherwise the first
match in census/out/catalog.json (census/catalog.py over local clones of public contract sources); otherwise a
shape guess from the tree, marked as a guess.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trees as T  # noqa: E402


# template hash -> (name, source)
LABELS = {
    T.N2T_POOL_TEMPLATE_HASH: ("ErgoDEX v1 N2T pool (ERG:token)", "ergo-dex contracts/amm/cfmm/v1/n2t/Pool.sc; "
                               "Lithos ErgoDexContracts.scala NativePoolErgoTree"),
    T.BABEL_TEMPLATE_HASH: ("EIP-31 Babel fee box", "eips eip-0031.md; appkit BabelFeeBoxContract.java"),
    T.FEE_TEMPLATE_HASH: ("miner fee contract", "ergo core (the fee proposition); spent by the block's miner"),
    "p2pk": ("P2PK, every key (each key is its own template): keyless only as a storage-rent claim",
             "ergo core: a P2PK box needs a signature; an input with no proof is the miner's rent claim"),
}
_LD = "Lithos client lithos-lib/src/main/scala/lithosdex/contracts/"
LABELS.update({
    "2de640e37a49cc9d95a08f2678da9f5e9aba56e08dfbc0662a64d225093156e3": (
        "LithosDex liquidity pool (ERG:LIT; NFT, LIT, provision)", _LD + "LDContracts.scala:72-151, "
        "LD_LiquidityPool.ergo; mainnet tree test/resources/lithosdex-deployments/erg-lit-pool.hex"),
    "29956fe5b9d86caf63ea7c63dede95091e1e4bdfa3d3641540706e829b383d9c": (
        "LithosDex fee vault", _LD + "LDContracts.scala; erg-lit-vault.hex"),
    "5bcb638153fd3acf8f5032c8d5bad4b0153caf5ee75a917562b4b5b5f8348ec1": (
        "LithosDex provision", _LD + "LDContracts.scala; LD_Provision.ergo"),
    "938b8ae08a1675558e8177b21524f95758ae0217ca41327492fae472c80466c9": (
        "LithosDex provision guard", _LD + "LDContracts.scala"),
    "b4fd5d9be2ed32a5cc516e431bf317033d1033078026bb04baf7ae355c665dfc": (
        "LithosDex SwapSell order", _LD + "LDOrderContracts.scala:150"),
    "7122d56978cf08f66ff5168a160e9e750002c62e79a6d985503da8ad02f11a98": (
        "LithosDex SwapBuy order", _LD + "LDOrderContracts.scala:164"),
    "28027ccf9c2a5ac3d31178e97a387aae3207ddec642b5662e63af30bbe642c17": (
        "LithosDex Deposit order", _LD + "LDOrderContracts.scala:178"),
    "d67c6f6e4dfaba9b7aefce23c63add22dbc5fdd34a27946771965be943baeb04": (
        "LithosDex Redeem order", _LD + "LDOrderContracts.scala:194"),
    "3c09deff3b5f49329149d18e02aab675ef6957bf6559a5c7dba817fee883fb3e": (
        "ErgoDEX v1 T2T pool (token:token)", "ergo-dex contracts/amm/cfmm/v1/t2t/Pool.sc; Lithos "
        "ErgoDexContracts.scala TokenPoolErgoTree"),
})
for _h, (_k, _v) in T.ORDER_TEMPLATE_HASHES.items():
    LABELS[_h] = (f"ErgoDEX N2T {_k} order {_v}", "Lithos ErgoDexContracts.scala orders; Spectrum backend "
                  "N2TCFMMTemplates.scala")

# templates a contract source says are keyless on some path; filled from the sources read for (f)
KNOWN_KEYLESS = {}

_CAT = None


def catalog():
    global _CAT
    if _CAT is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "catalog.json")
        _CAT = json.load(open(p)) if os.path.exists(p) else {}
    return _CAT


def name(th, tree=None):
    if th in LABELS:
        return {"name": LABELS[th][0], "source": LABELS[th][1], "how": "label"}
    c = catalog().get(th)
    if c:
        return {"name": c[0]["name"], "source": "; ".join(sorted({x["name"] for x in c})[:4]), "how": "catalog"}
    return {"name": "unknown", "source": None, "how": None}
