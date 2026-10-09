"""U1b line (j): U1's two-transaction takes (lines b and c) with the taker's capital capped (the test wallet's
10 ERG), same integer rules as census/amm.py. Capital is what the first leg spends: the ERG into the buying pool,
or the ERG paid to the bank for a mint.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amm as A  # noqa: E402


def _max_t(cost, hi, cap):
    """Largest t in [0, hi] with cost(t) <= cap (cost increasing)."""
    if hi < 1 or cost(1) > cap:
        return 0
    lo = 1
    while lo < hi:
        m = (lo + hi + 1) // 2
        if cost(m) <= cap:
            lo = m
        else:
            hi = m - 1
    return lo


def pool_vs_pool(a, b, cap):
    Xa, Ya, fa = a
    Xb, Yb, fb = b
    if Ya <= 1 or Xb * fb * fa * Ya <= Xa * A.FEE_DENOM * A.FEE_DENOM * Yb:
        return None
    tmax = _max_t(lambda t: A.pool_erg_in_for(Xa, Ya, fa, t), Ya - 1, cap)
    if not tmax:
        return None

    def profit(t):
        return A.pool_erg_out(Xb, Yb, fb, t) - A.pool_erg_in_for(Xa, Ya, fa, t)

    t, p = A.argmax_int(profit, 1, tmax)
    if t is None or p <= 0:
        return None
    return p, A.pool_erg_in_for(Xa, Ya, fa, t), t


def bank_vs_pool(bank, coin, pool, cap):
    X0, Y0, fee = pool
    best = None
    dmax = bank.max_units(coin, +1, Y0 * 10)
    dmax = _max_t(lambda d: bank.exchange(coin, d) or 10 ** 30, dmax, cap) if dmax else 0
    if dmax > 0:
        def p_mint(d):
            return A.pool_erg_out(X0, Y0, fee, d) - bank.exchange(coin, d)
        d, p = A.argmax_int(p_mint, 1, dmax)
        if d and p > 0:
            best = ("mint->pool", p, bank.exchange(coin, d), d)
    circ = bank.sc if coin == "sc" else bank.rc
    dmax = bank.max_units(coin, -1, min(Y0 - 1, circ))
    dmax = _max_t(lambda d: A.pool_erg_in_for(X0, Y0, fee, d), dmax, cap) if dmax else 0
    if dmax > 0:
        def p_red(d):
            return -bank.exchange(coin, -d) - A.pool_erg_in_for(X0, Y0, fee, d)
        d, p = A.argmax_int(p_red, 1, dmax)
        if d and p > 0 and (best is None or p > best[1]):
            best = ("pool->redeem", p, A.pool_erg_in_for(X0, Y0, fee, d), d)
    return best
