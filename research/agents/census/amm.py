"""Integer rules for the U1 census. Every function mirrors a contract check exactly; rounding goes against the
arbitrageur (the arbitrageur pays the ceiling and receives the floor).

ErgoDEX v1 N2T pool (ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:56-60, X = ERG = box value, Y = tokens(2)):
    dX > 0:  Y0 * dX * fee >= -dY * (X0 * 1000 + dX * fee)
    dX <= 0: X0 * dY * fee >= -dX * (Y0 * 1000 + dY * fee)
and successor.value > 10,000,000 (Pool.sc:28).

EIP-31 Babel box: (tokensAdded) * R5 >= ergTaken and ergTaken >= 0.

SigmaUSD bank v0.4 (Emurgo/age-usd ageusd-smart-contracts/v0.4/AgeUSD.scala:95-139): see bank_* below.
"""

FEE_DENOM = 1000
POOL_MIN_VALUE = 10_000_000          # Pool.sc:4,28 (strict >)


def cdiv(a, b):
    return -((-a) // b)


# ---- ErgoDEX v1 N2T pool -------------------------------------------------------------------------------------

def pool_tokens_out(X0, Y0, fee, dX):
    """Most tokens the pool gives for dX > 0 nanoERG in."""
    return (Y0 * dX * fee) // (X0 * FEE_DENOM + dX * fee)


def pool_erg_in_for(X0, Y0, fee, T):
    """Least nanoERG in that buys T tokens (0 < T < Y0)."""
    # Y0*dX*fee >= T*(X0*1000 + dX*fee)  <=>  dX*fee*(Y0 - T) >= T*X0*1000
    return cdiv(T * X0 * FEE_DENOM, fee * (Y0 - T))


def pool_erg_out(X0, Y0, fee, dY):
    """Most nanoERG the pool gives for dY > 0 tokens in, respecting the successor's minimum value."""
    out = (X0 * dY * fee) // (Y0 * FEE_DENOM + dY * fee)
    return min(out, X0 - POOL_MIN_VALUE - 1)


def check_pool_swap(X0, Y0, fee, dX, dY):
    if X0 + dX <= POOL_MIN_VALUE:
        return False
    if dX > 0:
        return Y0 * dX * fee >= -dY * (X0 * FEE_DENOM + dX * fee)
    return X0 * dY * fee >= -dX * (Y0 * FEE_DENOM + dY * fee)


def _isqrt(n):
    if n <= 0:
        return 0
    x = int(n ** 0.5)
    while x * x > n:
        x -= 1
    while (x + 1) * (x + 1) <= n:
        x += 1
    return x


def argmax_int(f, lo, hi):
    """Maximum of a unimodal (up to rounding) integer function on [lo, hi]: ternary search, then a local scan."""
    if hi < lo:
        return None, None
    a, b = lo, hi
    while b - a > 40:
        m1 = a + (b - a) // 3
        m2 = b - (b - a) // 3
        if f(m1) < f(m2):
            a = m1 + 1
        else:
            b = m2 - 1
    best = max(range(max(lo, a - 40), min(hi, b + 40) + 1), key=f)
    return best, f(best)


# ---- line (a): Babel box against a pool ----------------------------------------------------------------------

def babel_vs_pool(X0, Y0, fee, bid, avail):
    """Best one-transaction cycle: X nanoERG into the pool for T tokens, T tokens into the Babel box for
    Y = min(T*bid, avail) nanoERG. Returns (profit, X, T, Y) with profit = Y - X, or None if nothing is positive.
    Closed form: T* = Y0 - sqrt(1000 * X0 * Y0 / (fee * bid)), then integer search around it."""
    if bid <= 0 or avail <= 0 or Y0 <= 1:
        return None
    t_cap = min(Y0 - 1, cdiv(avail, bid))

    def profit(T):
        if T <= 0:
            return 0
        return min(T * bid, avail) - pool_erg_in_for(X0, Y0, fee, T)

    t_star = Y0 - _isqrt(cdiv(FEE_DENOM * X0 * Y0, fee * bid))
    cands = {1, t_cap, t_cap - 1}
    for d in range(-3, 4):
        cands.add(t_star + d)
    if t_cap > 1:
        T, _ = argmax_int(profit, 1, t_cap)
        cands.add(T)
    best = None
    for T in cands:
        if T is None or T < 1 or T > t_cap:
            continue
        p = profit(T)
        if best is None or p > best[0]:
            best = (p, T)
    if best is None or best[0] <= 0:
        return None
    p, T = best
    X = pool_erg_in_for(X0, Y0, fee, T)
    Y = min(T * bid, avail)
    assert check_pool_swap(X0, Y0, fee, X, -T), "pool rule"
    assert T * bid >= Y >= 0, "babel rule"
    return p, X, T, Y


# ---- line (c): pool against pool (two transactions) ----------------------------------------------------------

def pool_vs_pool(a, b):
    """Buy T tokens in pool a with ERG, sell them into pool b for ERG. a, b = (X0, Y0, fee).
    Returns (profit, capital, T) or None."""
    Xa, Ya, fa = a
    Xb, Yb, fb = b
    if Ya <= 1:
        return None
    # marginal sell price in b (fb*Xb / (1000*Yb)) must beat the marginal buy price in a (1000*Xa / (fa*Ya))
    if Xb * fb * fa * Ya <= Xa * FEE_DENOM * FEE_DENOM * Yb:
        return None

    def profit(T):
        return pool_erg_out(Xb, Yb, fb, T) - pool_erg_in_for(Xa, Ya, fa, T)

    T, p = argmax_int(profit, 1, Ya - 1)
    if T is None or p <= 0:
        return None
    X = pool_erg_in_for(Xa, Ya, fa, T)
    out = pool_erg_out(Xb, Yb, fb, T)
    assert check_pool_swap(Xa, Ya, fa, X, -T) and check_pool_swap(Xb, Yb, fb, -out, T)
    return p, X, T


# ---- line (b): SigmaUSD bank v0.4 ----------------------------------------------------------------------------

def _tdiv(a, b):
    """Scala/JVM Long division (truncates toward zero)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


class Bank:
    """Bank v0.4 state. R = reserve (box value), sc = R4 SigUSD circulating, rc = R5 SigRSV circulating,
    rate = oracle R4 / 100 (AgeUSD.scala:43), in nanoERG per 0.01 USD (one SigUSD unit)."""
    MIN_RR, MAX_RR, FEE_PCT = 400, 800, 2          # AgeUSD.scala:17,24,25 (HEIGHT > coolingOffHeight 377770)
    RC_DEFAULT = 1_000_000                          # AgeUSD.scala:13
    MIN_STORAGE = 10_000_000                        # AgeUSD.scala:15

    def __init__(self, R, sc, rc, oracle_r4):
        self.R, self.sc, self.rc = R, sc, rc
        self.rate = _tdiv(oracle_r4, 100)

    def _liab(self):
        return max(min(self.R, self.sc * self.rate), 0)

    def sc_price(self):
        if self.sc == 0:
            return self.rate
        return min(self.rate, _tdiv(self._liab(), self.sc))

    def rc_price(self):
        eq = self.R - self._liab()
        if eq == 0:
            return self.RC_DEFAULT
        return self.RC_DEFAULT if self.rc == 0 else _tdiv(eq, self.rc)

    def _delta_with_fee(self, price, d):
        br = price * d
        fee = abs(_tdiv(br * self.FEE_PCT, 100))
        return br + fee                             # the bank's reserve change (AgeUSD.scala:127-136)

    def _rr_out(self, R_out, sc_out):
        need = sc_out * self.rate
        if need == 0:
            return None                             # treated as maxReserveRatioPercent
        return _tdiv(R_out * 100, need)

    def exchange(self, coin, d):
        """Reserve change for d units (d > 0 mint: ERG paid in; d < 0 redeem: ERG paid out is the negative),
        or None if the reserve-ratio rule forbids it (AgeUSD.scala:104-115)."""
        if coin == "sc":
            delta = self._delta_with_fee(self.sc_price(), d)
            R_out, sc_out = self.R + delta, self.sc + d
            if sc_out < 0:
                return None
            if d > 0:
                rr = self._rr_out(R_out, sc_out)
                if rr is not None and rr < self.MIN_RR:
                    return None
        else:
            delta = self._delta_with_fee(self.rc_price(), d)
            R_out, sc_out = self.R + delta, self.sc
            if self.rc + d < 0:
                return None
            rr = self._rr_out(R_out, sc_out)
            if d > 0:
                if rr is not None and rr > self.MAX_RR:
                    return None
            elif rr is not None and rr < self.MIN_RR:
                return None
        if R_out < self.MIN_STORAGE:
            return None
        return delta

    def max_units(self, coin, sign, limit):
        """Largest n in [0, limit] with exchange(coin, sign*n) allowed (the rule is monotone in n)."""
        if limit <= 0 or self.exchange(coin, sign) is None:
            return 0
        lo, hi = 1, limit
        while lo < hi:
            m = (lo + hi + 1) // 2
            if self.exchange(coin, sign * m) is not None:
                lo = m
            else:
                hi = m - 1
        return lo


def bank_vs_pool(bank, coin, pool):
    """Two transactions on the arbitrageur's capital. Returns the better of
    mint-at-bank-sell-to-pool and buy-from-pool-redeem-at-bank: (direction, profit, capital, units) or None."""
    X0, Y0, fee = pool
    best = None
    # mint d at the bank, sell d into the pool
    dmax = bank.max_units(coin, +1, Y0 * 10)
    if dmax > 0:
        def p_mint(d):
            return pool_erg_out(X0, Y0, fee, d) - bank.exchange(coin, d)
        d, p = argmax_int(p_mint, 1, dmax)
        if d and p > 0:
            best = ("mint->pool", p, bank.exchange(coin, d), d)
    # buy d from the pool, redeem d at the bank
    circ = bank.sc if coin == "sc" else bank.rc
    dmax = bank.max_units(coin, -1, min(Y0 - 1, circ))
    if dmax > 0:
        def p_red(d):
            return -bank.exchange(coin, -d) - pool_erg_in_for(X0, Y0, fee, d)
        d, p = argmax_int(p_red, 1, dmax)
        if d and p > 0 and (best is None or p > best[1]):
            best = ("pool->redeem", p, pool_erg_in_for(X0, Y0, fee, d), d)
    return best
