#!/usr/bin/env python3
"""Tables for CENSUS-U1.md from the scan's JSON (census-u1.py --json) and the Lithos block list read at the
window's end (lithos-blocks-mainnet.py --json). Floats appear only here.

usage: summarize.py census-u1.json lithos-blocks.json
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorer as X  # noqa: E402

E = 1e9


def name(tok):
    t = X.get(f"/tokens/{tok}")
    return (t or {}).get("name") or tok[:8]


def erg(n):
    return f"{n / E:,.4f}"


def main():
    d = json.load(open(sys.argv[1]))
    lj = json.load(open(sys.argv[2]))
    n = d["blocks"]
    share = lj["lithosBlocks"] / lj["spanBlocks"]
    lith_blocks = share * n
    reward, fee = d["rewardNanoErgPerBlockMean"], d["feeNanoErgPerBlockMean"]
    ts = lambda ms: time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(ms / 1000))
    print(f"Window {d['from']:,}..{d['to']:,} ({n:,} blocks), {ts(d['firstBlockTime'])} to {ts(d['lastBlockTime'])}; "
          f"explorer {d['explorer']}; tip at start {d['explorerTipAtStart']:,}.")
    print(f"Reward {erg(reward)} ERG/block (distinct {d['rewardDistinct']}); emission box at the first block "
          f"{d['rewardBoxCheck']} (value, re-emission tokens). Fees {erg(fee)} ERG/block mean, "
          f"{erg(d['feeNanoErgPerBlockMedian'])} median, over {d['feeSampleBlocks']:,} blocks (every "
          f"{d['feeSampleStep']}th).")
    print(f"Lithos: {lj['lithosBlocks']} blocks of {lj['spanBlocks']:,} since {lj['firstLithosBlock']:,} "
          f"(tip {lj['tip']:,}, read {lj['readAt']}): share {share:.4%}; {lith_blocks:.1f} Lithos blocks in a window "
          f"of {n:,} at that share (inferred).\n")

    print("## a\n")
    print("| token | Babel boxes live | pools | blocks open | best bid nanoERG/unit | pool nanoERG/unit at best | X ERG | "
          "profit ERG (one take) |")
    print("|---|---|---|---|---|---|---|---|")
    ta = 0
    for tok, v in sorted(d["a"].items(), key=lambda kv: -kv[1]["lowerNanoErg"]):
        m = v["maxDetail"] or v["firstState"] or {}
        px = f"{m['poolX'] / m['poolY']:.2f}" if m.get("poolY") else "-"
        print(f"| {name(tok)} `{tok[:8]}` | {v['liveBabelBoxes']} | {v['pools']} | {v['blocksOpen']:,} | "
              f"{m.get('bid', '-')} | {px} | {erg(m['X']) if 'X' in m else '-'} | {erg(v['lowerNanoErg'])} |")
        ta += v["lowerNanoErg"]
    t = d["aTakenOnChain"]
    print(f"\nTotal (each token's best, taken once): {erg(ta)} ERG. Babel spends all time {t['babelSpendsAllTime']}, "
          f"in window {t['babelSpendsInWindow']}, last at {t['lastBabelSpend']:,}; Babel spends that also spend an "
          f"ErgoDEX v1 pool: {t['allTime']} all time, {t['inWindow']} in window. Babel boxes created in window: "
          f"{t['babelBoxesCreatedInWindow']}; live at the window's end: {t['babelBoxesLiveAtEnd']}.\n")

    print("## b\n")
    print("| coin | pools | blocks open | states open | direction | lower ERG | upper ERG | best ERG | capital at best ERG | "
          "capital median ERG |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    tb = 0
    for coin, v in d["b"].items():
        m = v["maxDetail"] or {}
        print(f"| {'SigUSD' if coin == 'sc' else 'SigRSV'} | {v['pools']} | {v['blocksOpen']:,} | {v['statesOpen']:,} | "
              f"{', '.join(f'{k} {c}' for k, c in v['directions'].items()) or '-'} | {erg(v['lowerNanoErg'])} | "
              f"{erg(v['upperNanoErg'])} | {erg(v['maxNanoErg'])} | {erg(m.get('capital', 0))} | "
              f"{erg(v['capitalMedianNanoErg'])} |")
        tb += v["lowerNanoErg"]
    bb = d["bBank"]
    for r in bb["bankAt"]:
        print(f"\nBank at {r['height']:,}: reserve {erg(r['reserveNanoErg'])} ERG, SigUSD circ {r['scCirc']:,}, "
              f"SigRSV circ {r['rcCirc']:,}, rate {r['rate']:,} nanoERG/0.01 USD, reserve ratio {r['rrPct']}%, "
              f"SigRSV price {r['rcPrice']:,}.", end="")
    print(f"\nBank boxes in window {bb['bankBoxesInWindow']}, oracle boxes {bb['oracleBoxesInWindow']}; bank tree "
          f"carries the oracle NFT: {bb['bankTreeHasOracleNft']}.\n")

    print("## c\n")
    print("| token | pools | blocks open | states open | lower ERG | upper ERG | best ERG | capital at best ERG | fees at best |")
    print("|---|---|---|---|---|---|---|---|---|")
    tc = 0
    rows = sorted(d["c"].items(), key=lambda kv: -kv[1]["lowerNanoErg"])
    for tok, v in rows:
        tc += v["lowerNanoErg"]
        if v["lowerNanoErg"] < 10_000_000:
            continue
        m = v["maxDetail"] or {}
        print(f"| {name(tok)} `{tok[:8]}` | {v['pools']} | {v['blocksOpen']:,} | {v['statesOpen']} | "
              f"{erg(v['lowerNanoErg'])} | {erg(v['upperNanoErg'])} | {erg(v['maxNanoErg'])} | "
              f"{erg(m.get('capital', 0))} | {m.get('fees')} |")
    small = [v for _, v in rows if 0 < v["lowerNanoErg"] < 10_000_000]
    none = [v for _, v in rows if v["lowerNanoErg"] == 0]
    print(f"\n{len(rows)} tokens with two or more pools; {len(small)} more under 0.01 ERG "
          f"({erg(sum(v['lowerNanoErg'] for v in small))} ERG together); {len(none)} never open. Total lower "
          f"{erg(tc)} ERG, upper {erg(sum(v['upperNanoErg'] for _, v in rows))} ERG.")
    r = d["cRSN"]
    print(f"RSN, the two deepest pools (fees {r['fees']}, combined {r['combinedFee']:.1%}): mid-price gap median "
          f"{r['medianGap']:.2%}, block-weighted mean {r['meanGap']:.2%}, max {r['maxGap']:.2%}; gap above the "
          f"combined fee in {r['blocksGapAboveCombinedFee']:,} of {r['blocks']:,} blocks "
          f"({r['blocksGapAboveCombinedFee'] / r['blocks']:.1%}).\n")

    print("## d, e\n")
    dd, dw, e = d["d"], d["dWindow"], d["e"]
    print(f"Window: swaps {dd.get('swap', 0):,} (ErgoDEX order executions {dd.get('swap_order', 0):,}, other "
          f"{dd.get('swap_direct', 0):,}), deposits {dd.get('deposit', 0)}, redemptions {dd.get('redeem', 0)}, "
          f"other {dd.get('other', 0)}; {dd.get('swap', 0) / (n / 720):.1f} swaps a day at 720 blocks a day.")
    print(f"{dw['from']} to {dw['to']} (heights {dw['heights'][0]:,}..{dw['heights'][1]:,}): swaps {dw.get('swap', 0):,} "
          f"(order executions {dw.get('swap_order', 0):,}, other {dw.get('swap_direct', 0):,}), deposits "
          f"{dw.get('deposit', 0)}, redemptions {dw.get('redeem', 0)}.")
    print(f"Executor fees: {e['orderTxs']} order executions, {erg(e['executorNanoErg'])} ERG "
          f"({erg(e['executorNanoErg'] / max(1, e['orderTxs']))} ERG each); kinds {e['orderKinds']}.\n")

    print("## per Lithos block\n")
    print("| line | window total ERG | per block ERG | x share = Lithos's part ERG | per Lithos block ERG | "
          "vs reward + fees per block |")
    print("|---|---|---|---|---|---|")
    per = reward + fee
    for label, tot in (("a Babel (lower)", ta), ("b bank (lower)", tb),
                       ("b bank (upper)", sum(v["upperNanoErg"] for v in d["b"].values())),
                       ("c pools (lower)", tc), ("c pools (upper)", sum(v["upperNanoErg"] for v in d["c"].values())),
                       ("e executor fees", e["executorNanoErg"])):
        part = tot * share
        print(f"| {label} | {erg(tot)} | {tot / n / E:.6f} | {part / E:,.4f} | {part / lith_blocks / E:.6f} | "
              f"{part / lith_blocks / per:.4%} |")
    print(f"\nReward + fees per block {erg(per)} ERG.")


if __name__ == "__main__":
    main()
