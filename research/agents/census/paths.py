"""U1c line m: the spending paths of a script, from the explorer's decompilation, classified.

The explorer returns each box's script decompiled (`ergoTreeScript`, segregated constants as `placeholder[T](i)`)
and the constants rendered (`ergoTreeConstants`, "i: value" lines). This module parses that text into a small AST,
substitutes the box's constants, folds constant conditions, and splits the top-level proposition into paths: a path
is one conjunction of leaf conditions, one per way the script can be true (`||`, `anyOf`, both arms of an `if`).

Each path is then classified by its leaves:
  key                    a leaf needs a signature: proveDlog, proveDHTuple, a SigmaProp constant holding a key,
                         a SigmaProp read from a register or a context variable, atLeast over keys
  key (miner)            proveDlog of the block's miner key (the miner-fee contract)
  key (secret)           a hash of a context variable compared with a constant (a preimage only the owner knows)
  keyless with input     the path reads another input's tokens, id or script, or a data input: someone must supply
                         that box (a token, an NFT box, an oracle) [obtainability is judged by hand]
  keyless later          the path compares HEIGHT, a timestamp or a creation height
  keyless now            none of the above
  unreachable            (per box) the path, or a value evaluated before its branch, reads SELF.Rn.get and the box
                         has no Rn
This is a reading of the text, not an evaluation: every classification it makes is SUSPECTED until traced by hand.
A path can also fail on output arithmetic the reader cannot judge (a successor that must hold more than the box has).

Values bound by `val` in a block are evaluated eagerly in the order written (sigmastate BlockValue), so a register
read in a val fails every path below that block if the box lacks the register; this is how the six Machina boxes
without R6 are stranded (U1b g).
"""
import re

# ---- tokenizer --------------------------------------------------------------------------------------------------

_TOK = re.compile(r"\s*(?:(?P<num>\d+L?)|(?P<id>[A-Za-z_][A-Za-z_0-9]*)|(?P<op>\|\||&&|==|!=|<=|>=|=>|[-+*/%<>!=(){}\[\],.:^|&]))")


class ParseError(Exception):
    pass


_ECP = re.compile(r"ECPoint\(([0-9a-f]+),([0-9a-f]+),\.\.\.\)")


def tokenize(s):
    s = _ECP.sub(lambda m: f"ECPoint_{m.group(1)}_{m.group(2)}", s)   # inline points: one identifier
    out, i, n = [], 0, len(s)
    while i < n:
        m = _TOK.match(s, i)
        if not m or m.end() == i:
            if s[i:].strip() == "":
                break
            raise ParseError(f"bad char at {i}: {s[i:i + 20]!r}")
        nl = "\n" in s[i:m.start(m.lastgroup)]
        kind = m.lastgroup
        out.append((kind, m.group(kind), nl))
        i = m.end()
    return out


# ---- parser (Pratt) ---------------------------------------------------------------------------------------------
# AST: ("name", s) ("num", int) ("bool", b) ("const", type, text) ("call", f, targs, args) ("sel", obj, field, targs)
#      ("bin", op, l, r) ("un", op, e) ("if", c, a, b) ("block", [(name, rhs)], e) ("lam", params, body)
#      ("tuple", items)

BIN = {"||": 1, "&&": 2, "==": 3, "!=": 3, "<": 4, ">": 4, "<=": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6,
       "%": 6, "^": 2, "|": 1, "&": 2}


class P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else (None, None, False)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, v):
        tok = self.next()
        if tok[1] != v:
            raise ParseError(f"expected {v!r} got {tok[1]!r} at token {self.i}")
        return tok

    def types(self):
        """[ ... ] balanced, returned as text."""
        self.expect("[")
        depth, out = 1, []
        while depth:
            k, v, _ = self.next()
            if v is None:
                raise ParseError("eof in type")
            if v == "[":
                depth += 1
            elif v == "]":
                depth -= 1
                if not depth:
                    break
            out.append(v)
        return "".join(x if x != "," else ", " for x in out)

    def args(self):
        self.expect("(")
        out = []
        if self.peek()[1] == ")":
            self.next()
            return out
        while True:
            out.append(self.expr(0))
            k, v, _ = self.next()
            if v == ")":
                return out
            if v != ",":
                raise ParseError(f"expected , or ) got {v!r}")

    def lam_or_block(self):
        self.expect("{")
        # lambda: { ( name : type ) => body }
        if self.peek()[1] == "(" and self.peek(1)[0] == "id" and self.peek(2)[1] == ":":
            self.next()
            params = []
            while True:
                _, nm, _ = self.next()
                self.expect(":")
                depth, ty = 0, []
                while True:
                    _, v, _ = self.peek()
                    if depth == 0 and v in (",", ")"):
                        break
                    if v in "([":
                        depth += 1
                    if v in ")]":
                        depth -= 1
                    ty.append(self.next()[1])
                params.append((nm, "".join(ty)))
                if self.next()[1] == ")":
                    break
            self.expect("=>")
            body = self.block_body("}")
            self.expect("}")
            return ("lam", params, body)
        paren = False
        if self.peek()[1] == "(" and self.peek(1)[1] == "val":
            self.next()
            paren = True
        body = self.block_body(")" if paren else "}")
        if paren:
            self.expect(")")
        self.expect("}")
        return body

    def block_body(self, end):
        vals = []
        while self.peek()[1] == "val":
            self.next()
            _, nm, _ = self.next()
            self.expect("=")
            vals.append((nm, self.expr(0)))
        e = self.expr(0)
        return ("block", vals, e) if vals else e

    def atom(self):
        k, v, _ = self.next()
        if k == "num":
            return ("num", int(v.rstrip("L")))
        if v == "(":
            if self.peek()[1] == "val":            # ( val ... ) as a block
                body = self.block_body(")")
                self.expect(")")
                return body
            items = [self.expr(0)]
            while self.peek()[1] == ",":
                self.next()
                items.append(self.expr(0))
            self.expect(")")
            return items[0] if len(items) == 1 else ("tuple", items)
        if v == "{":
            self.i -= 1
            return self.lam_or_block()
        if v in ("!", "-"):
            x = self.unary_operand()
            return ("num", -x[1]) if v == "-" and x[0] == "num" else ("un", v, x)
        if v == "val":                              # a block written inline after an operator
            self.i -= 1
            return self.block_body(None)
        if v == "if":
            self.expect("(")
            c = self.expr(0)
            self.expect(")")
            a = self.branch()
            self.expect("else")
            b = self.branch()
            return ("if", c, a, b)
        if k == "id":
            if v in ("true", "false"):
                return ("bool", v == "true")
            node = ("name", v)
            if self.peek()[1] == "[":
                targs = self.types()
                if self.peek()[1] == "(":
                    return ("call", node, targs, self.args())
                return ("tname", v, targs)
            return node
        raise ParseError(f"unexpected {v!r} at token {self.i}")

    def branch(self):
        if self.peek()[1] == "{":
            return self.lam_or_block()
        return self.expr(0)

    def unary_operand(self):
        return self.postfix(self.atom())

    def postfix(self, e):
        while True:
            k, v, nl = self.peek()
            if v == ".":
                self.next()
                _, f, _ = self.next()
                targs = self.types() if self.peek()[1] == "[" else None
                e = ("sel", e, f, targs)
            elif v == "(" and not nl:
                e = ("call", e, None, self.args())
            elif v == "{" and not nl and self.peek(1)[1] == "(" and e[0] == "sel":   # x.map {(a: T) => ..}
                e = ("call", e, None, [self.lam_or_block()])
            else:
                return e

    def expr(self, minp):
        left = self.postfix(self.atom())
        while True:
            k, v, nl = self.peek()
            p = BIN.get(v) if k == "op" else None
            if p is None or p < minp:
                return left
            self.next()
            right = self.expr(p + 1)
            left = ("bin", v, left, right)


def parse(script):
    toks = tokenize(script)
    p = P(toks)
    e = p.branch() if toks and toks[0][1] == "{" else p.expr(0)
    if p.i != len(toks):
        raise ParseError(f"trailing tokens at {p.i}/{len(toks)}: {toks[p.i][1]!r}")
    return e


# ---- constants --------------------------------------------------------------------------------------------------

def parse_constants(text):
    out = {}
    for line in (text or "").splitlines():
        m = re.match(r"(\d+): (.*)$", line)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def const_hex(text):
    """Coll(-1,2,...) of signed bytes -> hex; else None."""
    m = re.fullmatch(r"Coll\(([-\d,]*)\)", text)
    if not m:
        return None
    vals = [int(x) for x in m.group(1).split(",") if x != ""]
    if any(x < -128 or x > 255 for x in vals):
        return None
    return bytes(x & 0xFF for x in vals).hex()


def subst(e, consts):
    """Replace placeholder[T](i) by ("const", T, value text) (Booleans and integers by literals)."""
    k = e[0]
    if k == "call" and e[1] == ("name", "placeholder") and e[2] and len(e[3]) == 1 and e[3][0][0] == "num":
        ty, txt = e[2], consts.get(e[3][0][1], "?")
        if ty == "Boolean" and txt in ("true", "false"):
            return ("bool", txt == "true")
        if ty in ("Int", "Long", "Short", "Byte") and re.fullmatch(r"-?\d+", txt):
            return ("num", int(txt))
        if ty == "Coll[Byte]":
            h = const_hex(txt)
            if h is not None:
                return ("const", ty, h)
        return ("const", ty, txt)
    s = lambda x: subst(x, consts)  # noqa: E731
    if k == "call":
        return ("call", s(e[1]), e[2], [s(a) for a in e[3]])
    if k == "sel":
        return ("sel", s(e[1]), e[2], e[3])
    if k == "bin":
        return ("bin", e[1], s(e[2]), s(e[3]))
    if k == "un":
        return ("un", e[1], s(e[2]))
    if k == "if":
        return ("if", s(e[1]), s(e[2]), s(e[3]))
    if k == "block":
        return ("block", [(n, s(r)) for n, r in e[1]], s(e[2]))
    if k == "lam":
        return ("lam", e[1], s(e[2]))
    if k == "tuple":
        return ("tuple", [s(x) for x in e[1]])
    return e


# ---- rendering --------------------------------------------------------------------------------------------------

def render(e, env=None, depth=0):
    env = env or {}
    if depth > 40:
        return "…"
    r = lambda x: render(x, env, depth + 1)  # noqa: E731
    k = e[0]
    if k == "name":
        if e[1] in env and env[e[1]] is not None:
            return r(env[e[1]])
        return e[1]
    if k == "num":
        return str(e[1])
    if k == "bool":
        return "true" if e[1] else "false"
    if k == "const":
        t = e[2]
        if e[1] == "Coll[Byte]" and len(t) > 16:
            return f"0x{t[:12]}…"
        if t.startswith("SigmaProp(ProveDlog"):
            return "pk(" + t[t.index("(", 20) + 1:t.index(",")] + "…)"
        return t if len(t) < 40 else t[:36] + "…"
    if k == "tname":
        return f"{e[1]}[{e[2]}]"
    if k == "call":
        f = r(e[1]) if e[1][0] != "name" or env.get(e[1][1]) is not None else e[1][1]
        ta = f"[{e[2]}]" if e[2] else ""
        return f"{f}{ta}({', '.join(r(a) for a in e[3])})"
    if k == "sel":
        ta = f"[{e[3]}]" if e[3] else ""
        return f"{r(e[1])}.{e[2]}{ta}"
    if k == "bin":
        return f"({r(e[2])} {e[1]} {r(e[3])})"
    if k == "un":
        return f"{e[1]}{r(e[2])}"
    if k == "if":
        return f"if ({r(e[1])}) {r(e[2])} else {r(e[3])}"
    if k == "block":
        env2 = dict(env)
        for n, rhs in e[1]:
            env2[n] = rhs
        return render(e[2], env2, depth + 1)
    if k == "lam":
        env2 = dict(env)
        for n, _ in e[1]:
            env2[n] = None
        return "{(" + ", ".join(n for n, _ in e[1]) + ") => " + render(e[2], env2, depth + 1) + "}"
    if k == "tuple":
        return "(" + ", ".join(r(x) for x in e[1]) + ")"
    return str(e)


def oneline(e, env, limit=260):
    s = render(e, env)
    s = re.sub(r"^\((.*)\)$", r"\1", s)
    return s if len(s) <= limit else s[:limit - 1] + "…"


# ---- paths ------------------------------------------------------------------------------------------------------

MAX_PATHS = 256


def _resolve(e, env):
    while e[0] == "name" and env.get(e[1]) is not None:
        e = env[e[1]]
    return e


def _coll_items(e):
    """Coll[T](a, b, ...) -> items, else None."""
    if e[0] == "call" and e[1] == ("name", "Coll") and e[3] is not None:
        return e[3]
    return None


def paths(e, env, evaluated=()):
    """-> list of (leaves, evaluated): leaves are (expr, env, negated); evaluated are the block vals evaluated on the
    way (for register reads that fail before the branch)."""
    e = _resolve(e, env)
    k = e[0]
    if k == "call" and e[2] is None:                 # a lambda applied in place: bind its parameters
        f = _resolve(e[1], env)
        if f[0] == "lam" and len(f[1]) == len(e[3]):
            env2 = dict(env)
            for (n, _), a in zip(f[1], e[3]):
                env2[n] = a
            return paths(f[2], env2, evaluated)
    if k == "block":
        env2 = dict(env)
        ev = list(evaluated)
        for n, rhs in e[1]:
            env2[n] = rhs
            ev.append((rhs, env2))
        return paths(e[2], env2, tuple(ev))
    if k == "bool":
        return [([], evaluated)] if e[1] else []
    if k == "call" and e[1] == ("name", "sigmaProp") and len(e[3]) == 1:
        return paths(e[3][0], env, evaluated)
    if k == "const" and e[1] == "SigmaProp" and "TrivialProp(true)" in e[2]:
        return [([], evaluated)]
    if k == "const" and e[1] == "SigmaProp" and "TrivialProp(false)" in e[2]:
        return []
    if k == "bin" and e[1] == "||":
        return _cap(paths(e[2], env, evaluated) + paths(e[3], env, evaluated))
    if k == "bin" and e[1] == "&&":
        return _cap(_and(paths(e[2], env, evaluated), paths(e[3], env, ())))
    if k == "call" and e[1] in (("name", "anyOf"), ("name", "allOf")) and len(e[3]) == 1:
        items = _coll_items(_resolve(e[3][0], env))
        if items is not None:
            if e[1][1] == "anyOf":
                out = []
                for it in items:
                    out += paths(it, env, evaluated)
                return _cap(out)
            acc = [([], evaluated)]
            for it in items:
                acc = _cap(_and(acc, paths(it, env, ())))
            return acc
    if k == "if":
        c = _resolve(e[1], env)
        if c[0] == "bool":
            return paths(e[2] if c[1] else e[3], env, evaluated)
        if not (_has_sigma(e[2], env) or _has_sigma(e[3], env) or _is_false(e[2], env) or _is_false(e[3], env)):
            return [([(e, env, False)], evaluated)]      # a Boolean if with no key in either arm: one leaf
        a = [([(c, env, False)] + lv, ev) for lv, ev in paths(e[2], env, ())]
        b = [([(c, env, True)] + lv, ev) for lv, ev in paths(e[3], env, ())]
        return _cap([(lv, evaluated + ev) for lv, ev in a + b])
    return [([(e, env, False)], evaluated)]


def _is_false(e, env):
    e = _resolve(e, env)
    while e[0] == "block":
        e = e[2]
    return e == ("bool", False) or (e[0] == "call" and e[1] == ("name", "sigmaProp") and e[3] == [("bool", False)])


def _has_sigma(e, env):
    for n, en in walk(e, env):
        if n[0] == "call" and n[1][0] == "name" and n[1][1] in ("proveDlog", "proveDHTuple", "atLeast", "sigmaProp"):
            return True
        if n[0] == "const" and n[1] == "SigmaProp":
            return True
        if (n[0] == "sel" and n[3] == "SigmaProp") or (n[0] == "call" and n[2] == "SigmaProp"):
            return True
    return False


class TooMany(Exception):
    pass


def _cap(ps):
    if len(ps) > MAX_PATHS:
        raise TooMany(len(ps))
    return ps


def _and(xs, ys):
    return [(a + b, ea + eb) for a, ea in xs for b, eb in ys]


# ---- leaf features ----------------------------------------------------------------------------------------------

def walk(e, env, seen=None, depth=0):
    """Every node under e, following val names into their definitions (once each)."""
    seen = set() if seen is None else seen
    if depth > 200 or not isinstance(e, tuple):
        return
    yield e, env
    k = e[0]
    if k == "name":
        if e[1] in env and env[e[1]] is not None and (e[1], id(env)) not in seen:
            seen.add((e[1], id(env)))
            yield from walk(env[e[1]], env, seen, depth + 1)
        return
    if k == "block":
        env2 = dict(env)
        for n, rhs in e[1]:
            env2[n] = rhs
        for n, rhs in e[1]:
            yield from walk(rhs, env2, seen, depth + 1)
        yield from walk(e[2], env2, seen, depth + 1)
        return
    if k == "lam":
        env2 = dict(env)
        for n, _ in e[1]:
            env2[n] = None
        yield from walk(e[2], env2, seen, depth + 1)
        return
    for x in e[1:]:
        if isinstance(x, tuple):
            yield from walk(x, env, seen, depth + 1)
        elif isinstance(x, list):
            for y in x:
                if isinstance(y, tuple) and y and isinstance(y[0], str) and y[0] in _KINDS:
                    yield from walk(y, env, seen, depth + 1)


_KINDS = {"name", "num", "bool", "const", "call", "sel", "bin", "un", "if", "block", "lam", "tuple", "tname"}
_REG = re.compile(r"R[4-9]")


def features(e, env):
    f = set()
    regs = set()
    for n, en in walk(e, env):
        k = n[0]
        if k == "call" and n[1][0] == "name":
            fn = n[1][1]
            if fn in ("proveDlog", "proveDHTuple"):
                inner = render(n[3][0], en) if n[3] else ""
                f.add("miner" if "minerPubKey" in inner or "minerPk" in inner else "key")
            elif fn == "atLeast":
                f.add("key")
            elif fn == "DeserializeContext":
                f.add("deser")
            elif fn == "getVar":
                f.add("ctxvar")
                if n[2] == "SigmaProp":
                    f.add("key")
            elif fn in ("blake2b256", "sha256") and n[3]:
                a = _resolve(n[3][0], en)
                if a[0] == "sel" and a[2] == "get":
                    a = _resolve(a[1], en)
                if a[0] == "call" and a[1] == ("name", "getVar"):
                    f.add("hashvar")
        if k == "const" and n[1] == "SigmaProp" and ("ProveDlog" in n[2] or "ProveDHTuple" in n[2]
                                                     or "THRESHOLD" in n[2].upper() or "CAND" in n[2] or "COR" in n[2]):
            f.add("key")
        if k == "const" and n[1] == "GroupElement":
            f.add("ge")
        if k == "sel":
            fld = n[2]
            if _REG.fullmatch(fld) and n[3] == "SigmaProp":
                f.add("key")
            if _REG.fullmatch(fld) and n[1] == ("name", "SELF"):
                regs.add(fld)
            if fld in ("dataInputs",):
                f.add("datainput")
            if fld in ("timestamp",):
                f.add("time")
        if k == "name" and n[1] == "HEIGHT":
            f.add("height")
        if k == "name" and n[1] == "minerPubKey":
            f.add("minerpk")
        if k == "call" and n[1] == ("name", "INPUTS") and n[3]:
            f.add("inputs_idx")
        if k == "sel" and n[1] == ("name", "INPUTS"):
            f.add("inputs_all")
        if k == "sel" and n[2] == "creationInfo":
            f.add("creation")
    return f, regs


def _register_gets(e, env):
    """SELF registers read with .get anywhere under e (a value evaluated before the branch)."""
    out = set()
    for n, _ in walk(e, env):
        if n[0] == "sel" and n[2] == "get" and n[1][0] == "sel" and n[1][1] == ("name", "SELF") \
                and _REG.fullmatch(n[1][2]):
            out.add(n[1][2])
    return out


def key_leaf(e, env):
    """A leaf left after splitting && / || / sigmaProp(bool) is a signature requirement iff it is SigmaProp-typed:
    proveDlog / proveDHTuple / atLeast, a SigmaProp constant, a SigmaProp read from a register or context variable.
    -> None, "key" or "key (miner)"."""
    e = _resolve(e, env)
    k = e[0]
    if k == "call" and e[1][0] == "name" and e[1][1] in ("proveDlog", "proveDHTuple", "atLeast"):
        inner = render(e, env)
        return "key (miner)" if ("minerPubKey" in inner or "minerPk" in inner) else "key"
    if k == "const" and e[1] == "SigmaProp":
        return "key"
    if k == "call" and e[1][0] == "name" and e[1][1] in ("SigmaProp", "ProveDlog", "ProveDHTuple"):
        return "key"                                 # a key written inline (not segregated)
    if k == "sel" and e[2] == "get" and e[1][0] in ("sel", "call") and (
            (e[1][0] == "sel" and e[1][3] == "SigmaProp") or (e[1][0] == "call" and e[1][2] == "SigmaProp")):
        return "key"
    if k == "call" and e[1] == ("name", "getVar") and e[2] == "SigmaProp":
        return "key"
    return None


def _height_const(e, env, H):
    """HEIGHT compared with a constant: True (holds at H and every later height), False (fails at H and every
    later height), or None (anything else, or it changes later)."""
    e = _resolve(e, env)
    if H is None or e[0] != "bin" or e[1] not in ("<", "<=", ">", ">="):
        return None
    l, r = _resolve(e[2], env), _resolve(e[3], env)
    unwrap = lambda x: x[1] if x[0] == "sel" and x[2] in ("toLong", "toInt") else x  # noqa: E731
    l, r = unwrap(l), unwrap(r)
    op = e[1]
    if r == ("name", "HEIGHT") and l[0] == "num":
        l, r, op = r, l, {"<": ">", "<=": ">=", ">": "<", ">=": "<="}[op]
    if l != ("name", "HEIGHT") or r[0] != "num":
        return None
    c = r[1]
    if op == "<":
        return False if H >= c else None
    if op == "<=":
        return False if H > c else None
    if op == ">=":
        return True if H >= c else None
    return True if H > c else None


def classify_path(leaves, evaluated, H=None):
    feats, regs = set(), set()
    quotes = []
    expired = False
    for e, env, neg in leaves:
        hc = _height_const(e, env, H)
        if hc is not None:
            if hc == neg:
                expired = True
            quotes.append(("!" if neg else "") + oneline(e, env, 200))
            continue
        f, _ = features(e, env)
        f.discard("key")
        f.discard("miner")
        kl = key_leaf(e, env)
        if kl:
            f.add("miner" if kl == "key (miner)" else "key")
        feats |= f
        regs |= _register_gets(e, env)
        quotes.append(("!" if neg else "") + oneline(e, env, 200))
    for rhs, env in evaluated:
        regs |= _register_gets(rhs, env)
    if expired:
        cls = "unreachable"
        feats.add("height-expired")
    elif "key" in feats:
        cls = "key"
    elif "miner" in feats:
        cls = "key (miner)"
    elif "hashvar" in feats and "deser" not in feats:
        cls = "key (secret)"
    elif "deser" in feats:
        cls = "keyless with input"
    elif feats & {"inputs_idx", "datainput"} or ("inputs_all" in feats and any(
            "INPUTS" in q and "tokens" in q for q in quotes)):
        cls = "keyless with input"
    elif feats & {"height", "time", "creation"}:
        cls = "keyless later"
    else:
        cls = "keyless now"
    out = {"class": cls, "features": sorted(feats), "needsRegisters": sorted(regs), "condition": " && ".join(quotes)}
    if cls == "keyless with input" and feats & {"height", "time", "creation"}:
        out["alsoLater"] = True
    return out


def analyse(script, constants_text, H=None):
    """-> {"parsed": bool, "error": str|None, "paths": [...]}"""
    if not script:
        return {"parsed": False, "error": "no decompilation", "paths": []}
    # executeFromVar: the explorer cannot print it; kept as an opaque leaf (a script the spender supplies in a
    # context variable, usually checked against a hash constant)
    script = script.replace("DeserializeContext is currently not implemented", "DeserializeContext()")
    try:
        ast = subst(parse(script), parse_constants(constants_text))
    except (ParseError, RecursionError, ValueError, IndexError, KeyError) as ex:
        return {"parsed": False, "error": f"parse: {ex}"[:200], "paths": []}
    try:
        ps = paths(ast, {})
    except TooMany as ex:
        return {"parsed": True, "error": f"more than {MAX_PATHS} paths ({ex})", "paths": []}
    except RecursionError:
        return {"parsed": True, "error": "recursion", "paths": []}
    out, seen = [], set()
    for lv, ev in ps:
        c = classify_path(lv, ev, H)
        key = (c["class"], c["condition"])
        if key not in seen:
            seen.add(key)
            out.append(c)
    return {"parsed": True, "error": None, "paths": out}
