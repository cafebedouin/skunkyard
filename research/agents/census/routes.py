"""U1b line (h): routes through ErgoDEX v1 token-to-token (T2T) pools, in integers.

T2T pool (ergo-dex contracts/amm/cfmm/v1/t2t/Pool.sc): tokens NFT, LP, X, Y at 0..3 (:6-9), fee R4 over 1000
(:2-3), successor at OUTPUTS(0) (:11), ERG value may not fall (:23), swap rule (:54-58)
    dX > 0:  Y0 * dX * fee >= -dY * (X0 * 1000 + dX * fee)
    dX <= 0: X0 * dY * fee >= -dX * (Y0 * 1000 + dY * fee)
the N2T rule with token X in place of ERG. Both pool kinds take their successor at OUTPUTS(0), so a route
through two pools is two transactions, through three pools three, each on the taker's capital.

A cycle ERG -> A (N2T pool of A) -> B (T2T pool A:B) -> ERG (N2T pool of B), or the reverse, is evaluated as
the composition of the integer rules, each leg giving the most its rule allows (floor), searched over the ERG
put in (profit is concave up to rounding; census/amm.argmax_int).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amm as A  # noqa: E402


def out_given_in(R_in, R_out, fee, d):
    """Most of the out-reserve a CFMM v1 pool pays for d > 0 of the in-reserve (either orientation)."""
    if d <= 0:
        return 0
    return (R_out * d * fee) // (R_in * A.FEE_DENOM + d * fee)


def n2t_buy(p, x):
    """Tokens for x nanoERG into N2T pool p = (X, Y, fee)."""
    return min(out_given_in(p[0], p[1], p[2], x), p[1] - 1)


def n2t_sell(p, t):
    """nanoERG for t tokens into N2T pool p (successor keeps more than 0.01 ERG)."""
    return A.pool_erg_out(p[0], p[1], p[2], t) if t > 0 else 0


def t2t_swap(p, a_is_x, d):
    """Out-token for d in-token into T2T pool p = (X, Y, fee); a_is_x: the token put in is X."""
    X, Y, fee = p
    if a_is_x:
        return min(out_given_in(X, Y, fee, d), Y - 1)
    return min(out_given_in(Y, X, fee, d), X - 1)


def cycle(p1, p2, a_is_x, p3, cap):
    """Best ERG -> A (p1) -> B (p2) -> ERG (p3) with at most cap nanoERG in.
    Returns (profit, x, a, b, erg_out) or None."""
    def f(x):
        a = n2t_buy(p1, x)
        b = t2t_swap(p2, a_is_x, a)
        return n2t_sell(p3, b) - x

    # concave with f(0) = 0: if it is not positive at 0.001, 0.01 and 0.1 ERG it is not positive above them
    if all(f(min(v, cap)) <= 0 for v in (1_000_000, 10_000_000, 100_000_000)):
        return None
    x, p = A.argmax_int(f, 1, cap)
    if x is None or p <= 0:
        return None
    a = n2t_buy(p1, x)
    b = t2t_swap(p2, a_is_x, a)
    return p, x, a, b, n2t_sell(p3, b)
