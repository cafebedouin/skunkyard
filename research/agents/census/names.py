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
# identified from the deployed script (explorer decompilation of a sample box) and its tokens; "[inferred]" where
# no source file was matched
_SCRIPT = "decompiled sample box"
for _p, _n, _src in [
    ("707c363f0914", "EIP-27 re-emission proxy (pay-to-reemission), swept into the emission tx [inferred]",
     "Lithos Eip27AdjustmentSpec.scala:36 (EIP-27 proxy tree); eip-0027.md"),
    ("682db8df7a2a", "emission contract (one spend per block)", "ergo core; " + _SCRIPT),
    ("ae9ac8d914dc", "EIP-27 re-emission contract (Reemission Contract NFT)", "eip-0027.md; " + _SCRIPT),
    ("fcbf6946412d", "Oracle pool v2 oracle box (MORACLE/MORT): refresh consumes it keylessly",
     "ergoplatform/oracle-core; " + _SCRIPT),
    ("416babd63f01", "Oracle pool v2 pool box (MPOOL): spendable when INPUTS(0) holds the refresh or update NFT",
     "ergoplatform/oracle-core (EIP-23); " + _SCRIPT),
    ("f6f982fa5002", "Oracle pool v1 (ERGUSD-NFT, SigmaUSD's oracle)", "scalahub/OraclePool v1; " + _SCRIPT),
    ("246e14059ac2", "SigmaUSD bank v0.4 (SUSD Bank V2 NFT)", "Emurgo/age-usd v0.4 AgeUSD.scala"),
    ("0416175ab49d", "Rosen Bridge (rspv3 RWT, Ergo) [inferred]", _SCRIPT + ", tokens rspv3ErgoRWT"),
    ("5cc1ea1a0f7a", "Rosen Bridge (rspv3 RWT, Cardano) [inferred]", _SCRIPT + ", tokens rspv3CardanoRWT"),
    ("9b633bf518fc", "Rosen Bridge RWT repo (rspv3RWTNFT) [inferred]", _SCRIPT),
    ("0c7face721e4", "Rosen Bridge AWC (rspv3ErgoAWC, RSN) [inferred]", _SCRIPT),
    ("856c43fe0610", "Rosen Bridge commitment/event (rspv3ErgoRWT) [inferred]", _SCRIPT),
    ("f083eb657c08", "Rosen Bridge emission (rspv2EmissionNFT, RSN, eRSN) [inferred]", _SCRIPT),
    ("00c90f397b21", "sigmaProp(true): anyone; here created and spent in the same block (chained txs)", _SCRIPT),
    ("e9d13195d73d", "OUTPUTS.size == n only: anyone; created and spent in the same block", _SCRIPT),
    ("02132cc5df11", "key OR (OUTPUTS.size == 1 and HEIGHT == creation height): chained-tx link", _SCRIPT),
    ("4897b8e91e59", "hash-preimage lock (blake2b256(var 0) slice == constant)", _SCRIPT),
    ("278ccff223ae", "unknown contract (no tokens; value <= 0.1 ERG consolidation path); spent here only as rent",
     _SCRIPT),
    ("b924a4f73573", "unknown contract (token-gated paths); spent here only as rent", _SCRIPT),
    ("834687280459", "Lithos emission (LITHOS-EMISSION, LITHOS-QUEUE, LITHOS-COLLAT) [inferred]",
     _SCRIPT + "; Lithos client LIT_Emissions.ergo"),
    ("db686aa7db20", "Lithos collateral queue box (LITHOS-QUEUE, LIT) [inferred]",
     _SCRIPT + "; Lithos client Collateral_Enforcer.ergo"),
    ("3328cef917f9", "Lithos collateral (LITHOS-COLLAT, LIT) [inferred]", _SCRIPT + "; Collateral_Mainnet.ergo"),
    ("5a0f7e9f1c93", "LIT-holding contract (token 87b384) [inferred Lithos rollup]", _SCRIPT),
    ("09d67ac30249", "LIT-holding contract (token 87b384) [inferred Lithos rollup]", _SCRIPT),
    ("41933d09756b", "LIT-holding contract (token ff84ae) [inferred Lithos]", _SCRIPT),
    ("8b1e2b8137db", "dortBuyback (DORT; a Dexy-style buyback) [inferred]", _SCRIPT),
    ("3711297e58fc", "concentrated-liquidity pool tSTB/tUSD [inferred]", _SCRIPT),
    ("406d9b79b183", "anetaBTC smart pool [inferred]", _SCRIPT),
    ("d5f0be11ee59", "raffle contract [inferred]", _SCRIPT),
    ("ee56ecce4217", "unknown (token cbe49f…; the explorer gives no decompilation)", "explorer"),
    ("c5328d694b98", "unknown (R4 Long, INPUTS-size paths)", _SCRIPT),
    ("961e872f7ab7", "time-locked key (HEIGHT >= creation + n && key): keyless only as rent", _SCRIPT),
    ("57b642a829f8", "Duckpools (off-chain-bot consts.py)", "duckpools/off-chain-bot consts.py"),
    ("c63f7fa24d3e", "Duckpools (off-chain-bot consts.py)", "duckpools/off-chain-bot consts.py"),
    ("f9f76671e416", "SkyHarbor ERG sale; spent here only as rent", "skyharbor-market/contracts"),
]:
    _LABEL_PREFIX = _p
    LABELS.setdefault(_p, (_n, _src))
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
    if th[:12] in LABELS and th not in LABELS:
        return {"name": LABELS[th[:12]][0], "source": LABELS[th[:12]][1], "how": "label"}
    if th in LABELS:
        return {"name": LABELS[th][0], "source": LABELS[th][1], "how": "label"}
    c = catalog().get(th)
    if c:
        return {"name": c[0]["name"], "source": "; ".join(sorted({x["name"] for x in c})[:4]), "how": "catalog"}
    return {"name": "unknown", "source": None, "how": None}
