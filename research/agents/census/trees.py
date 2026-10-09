"""ErgoTree helpers: template hash as the explorer indexes it (SHA-256 of the tree with its segregated constants
removed; checked against /boxes/unspent/byErgoTreeTemplateHash on a SigUSD Babel box, 2026-10-09)."""
import hashlib

BABEL_TEMPLATE = (
    "100604000e20{tokenId}0400040005000500d803d601e30004d602e4c6a70408d603e4c6a7050595e67201d804d604b2a5e4720100"
    "d605b2db63087204730000d606db6308a7d60799c1a7c17204d1968302019683050193c27204c2a7938c720501730193e4c672040408"
    "720293e4c672040505720393e4c67204060ec5a796830201929c998c7205029591b1720673028cb272067303000273047203720792"
    "720773057202")

N2T_POOL_TREE = (
    "1999030f0400040204020404040405feffffffffffffffff0105feffffffffffffffff01050004d00f04000400040605"
    "0005000580dac409d819d601b2a5730000d602e4c6a70404d603db63087201d604db6308a7d605b27203730100d606b2"
    "7204730200d607b27203730300d608b27204730400d6099973058c720602d60a999973068c7205027209d60bc17201d6"
    "0cc1a7d60d99720b720cd60e91720d7307d60f8c720802d6107e720f06d6117e720d06d612998c720702720fd6137e72"
    "0c06d6147308d6157e721206d6167e720a06d6177e720906d6189c72117217d6199c72157217d1ededededededed93c2"
    "7201c2a793e4c672010404720293b27203730900b27204730a00938c7205018c720601938c7207018c72080193b17203"
    "730b9593720a730c95720e929c9c721072117e7202069c7ef07212069a9c72137e7214067e9c720d7e72020506929c9c"
    "721372157e7202069c7ef0720d069a9c72107e7214067e9c72127e7202050695ed720e917212730d907216a19d721872"
    "139d72197210ed9272189c721672139272199c7216721091720b730e")

FEE_TREE = ("1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02"
            "d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac"
            "93b1a57304")


def _vlq(b, i):
    r, s = 0, 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s; s += 7
        if not x & 0x80:
            return r, i


def _parse_type(b, i):
    """Serialized SType -> (type, i). Primitive codes 1..9; collections, options and pairs are encoded on top of
    them (sigmastate TypeSerializer)."""
    c = b[i]; i += 1
    if 1 <= c <= 9:
        return ("p", c), i
    if c in range(97, 107):                     # Any, Unit, Box, AvlTree, Context, String, Header, PreHeader...
        return ("x", c), i
    if c == 96:                                 # STuple: n then n types
        n = b[i]; i += 1
        ts = []
        for _ in range(n):
            t, i = _parse_type(b, i)
            ts.append(t)
        return ("tuple", ts), i
    k, r = divmod(c, 12)
    def inner(i):
        return _parse_type(b, i) if r == 0 else (("p", r), i)
    if k == 1:
        t, i = inner(i); return ("coll", t), i
    if k == 2:
        t, i = inner(i); return ("coll", ("coll", t)), i
    if k == 3:
        t, i = inner(i); return ("opt", t), i
    if k == 4:
        t, i = inner(i); return ("opt", ("coll", t)), i
    if k == 5:                                  # Pair1: (prim r or type, type)
        t1, i = inner(i); t2, i = _parse_type(b, i); return ("tuple", [t1, t2]), i
    if k == 6:                                  # Pair2: (type, prim r or type)
        if r == 0:
            t1, i = _parse_type(b, i); t2, i = _parse_type(b, i)
        else:
            t1, i = _parse_type(b, i); t2 = ("p", r)
        return ("tuple", [t1, t2]), i
    if k == 7:                                  # PairSymmetric
        t, i = inner(i); return ("tuple", [t, t]), i
    if k == 8:                                  # Triple / Quadruple via r
        raise ValueError(f"type code {c} not handled")
    raise ValueError(f"type code {c} not handled")


def _skip_sigma(b, i):
    op = b[i]; i += 1
    if op == 0xcd:                              # ProveDlog
        return i + 33
    if op == 0xce:                              # ProveDHTuple
        return i + 4 * 33
    if op in (0x96, 0x97):                      # CAND, COR: n children
        n, i = _vlq(b, i)
        for _ in range(n):
            i = _skip_sigma(b, i)
        return i
    if op == 0x98:                              # CTHRESHOLD: k, n children
        _, i = _vlq(b, i); n, i = _vlq(b, i)
        for _ in range(n):
            i = _skip_sigma(b, i)
        return i
    if op in (0x7f, 0x80):                      # TrivialProp true/false
        return i
    raise ValueError(f"sigma op {op:#x} not handled")


def _skip_value(b, i, t):
    kind = t[0]
    if kind == "p":
        c = t[1]
        if c in (1, 2):
            return i + 1
        if c in (3, 4, 5):
            _, i = _vlq(b, i); return i
        if c in (6, 9):
            n, i = _vlq(b, i); return i + n
        if c == 7:
            return i + 33
        if c == 8:
            return _skip_sigma(b, i)
    if kind == "coll":
        n, i = _vlq(b, i)
        et = t[1]
        if et == ("p", 1):                      # Coll[Boolean]: bit-packed
            return i + (n + 7) // 8
        if et == ("p", 2):
            return i + n
        for _ in range(n):
            i = _skip_value(b, i, et)
        return i
    if kind == "opt":
        f = b[i]; i += 1
        return _skip_value(b, i, t[1]) if f else i
    if kind == "tuple":
        for et in t[1]:
            i = _skip_value(b, i, et)
        return i
    if kind == "x" and t[1] == 100:             # AvlTree: digest, flags, keyLength, valueLengthOpt
        i += 33 + 1
        _, i = _vlq(b, i)
        f = b[i]; i += 1
        if f:
            _, i = _vlq(b, i)
        return i
    if kind == "x" and t[1] == 98:              # Unit
        return i
    raise ValueError(f"value of type {t} not handled")


def _skip_const(b, i):
    t, i = _parse_type(b, i)
    return _skip_value(b, i, t)


def template_bytes(tree_hex):
    b = bytes.fromhex(tree_hex)
    h = b[0]; i = 1
    if h & 0x08:
        _, i = _vlq(b, i)
    if h & 0x10:
        n, i = _vlq(b, i)
        for _ in range(n):
            i = _skip_const(b, i)
    return b[i:]


def template_hash(tree_hex):
    return hashlib.sha256(template_bytes(tree_hex)).hexdigest()


BABEL_TEMPLATE_HASH = template_hash(BABEL_TEMPLATE.format(tokenId="00" * 32))
N2T_POOL_TEMPLATE_HASH = template_hash(N2T_POOL_TREE)
FEE_TEMPLATE_HASH = template_hash(FEE_TREE)


def constant_coll_bytes(tree_hex, k):
    """Hex of segregated constant k when it is a Coll[Byte]."""
    b = bytes.fromhex(tree_hex)
    h = b[0]; i = 1
    if h & 0x08:
        _, i = _vlq(b, i)
    n, i = _vlq(b, i)
    for j in range(n):
        if j == k:
            assert b[i] == 0x0e
            ln, s = _vlq(b, i + 1)
            return b[s:s + ln].hex()
        i = _skip_const(b, i)
    return None


def babel_token(tree_hex):
    """Token id a Babel box bids for (its constant 1), or None if the tree is not the EIP-31 template. Matches
    on the template hash, so trees with a size field (header 0x18) count as well as the 0x10 form."""
    if template_hash(tree_hex) != BABEL_TEMPLATE_HASH:
        return None
    return constant_coll_bytes(tree_hex, 1)


# ErgoDEX N2T order templates (kind, version, template hex), copied from the Lithos client
# app/transactions/batching/ergodex/ErgoDexContracts.scala (orders). Hashed here the explorer's way (SHA-256).
ERGODEX_N2T_ORDERS = [
    ("SwapSell", "v3", "d804d601b2a4730000d6027301d6037302d6049c73037e730405eb027305d195ed92b1a4730693b1db630872017307d806d605db63087201d606b2a5730800d607db63087206d608b27207730900d6098c720802d60a95730a9d9c7e997209730b067e7202067e7203067e720906edededededed938cb27205730c0001730d93c27206730e938c720801730f92720a7e7310069573117312d801d60b997e7313069d9c720a7e7203067e72020695ed91720b731492b172077315d801d60cb27207731600ed938c720c017317927e8c720c0206720b7318909c7e8cb2720573190002067e7204069c9a720a731a9a9c7ec17201067e731b067e72040690b0ada5d9010b639593c2720b731cc1720b731d731ed9010b599a8c720b018c720b02731f7320"),
    ("SwapSell", "v1", "d803d6017300d602b2a4730100d6037302eb027201d195ed92b1a4730393b1db630872027304d804d604db63087202d605b2a5730500d606b2db63087205730600d6077e8c72060206edededededed938cb2720473070001730893c27205d07201938c72060173099272077e730a06927ec172050699997ec1a7069d9c72077e730b067e730c067e720306909c9c7e8cb27204730d0002067e7203067e730e069c9a7207730f9a9c7ec17202067e7310067e9c73117e7312050690b0ada5d90108639593c272087313c1720873147315d90108599a8c7208018c72080273167317"),
    ("SwapSell", "multiAddressV2", "d802d601b2a4730000d6027301d1ec730295ed93b1a4730393b1db630872017304d804d603db63087201d604b2a5730500d605b2db63087204730600d6067e8c72050206edededededed938cb2720373070001730893c272047309938c720501730a9272067e730b06927ec172040699997ec1a7069d9c72067e730c067e730d067202909c9c7e8cb27203730e00020672027e730f069c9a720673109a9c7ec17201067e7311067e9c73127e7313050690b0ada5d90107639593c272077314c1720773157316d90107599a8c7207018c72070273177318"),
    ("SwapSell", "legacyV0", "d803d6017300d602b2a4730100d6037302eb027201d195ed93b1a4730393b1db630872027304d804d604db63087202d605b2a5730500d606b2db63087205730600d6077e8c72060206ededededed938cb2720473070001730893c27205d07201938c72060173099272077e730a06927ec172050699997ec1a7069d9c72077e730b067e730c067e720306909c9c7e8cb27204730d0002067e7203067e730e069c9a7207730f9a9c7ec17202067e7310067e9c73117e731205067313"),
    ("SwapBuy", "v3", "d802d601b2a4730000d6029c73017e730205eb027303d195ed92b1a4730493b1db630872017305d804d603db63087201d604b2a5730600d60599c17204c1a7d606997e7307069d9c7e7205067e7308067e730906ededededed938cb27203730a0001730b93c27204730c927205730d95917206730ed801d607b2db63087204730f00ed938c7207017310927e8c7207020672067311909c7ec17201067e7202069c7e9a72057312069a9c7e8cb2720373130002067e7314067e72020690b0ada5d90107639593c272077315c1720773167317d90107599a8c7207018c72070273187319"),
    ("SwapBuy", "v1", "d802d6017300d602b2a4730100eb027201d195ed92b1a4730293b1db630872027303d804d603db63087202d604b2a5730400d6059d9c7e99c17204c1a7067e7305067e730606d6068cb2db6308a773070002edededed938cb2720373080001730993c27204d072019272057e730a06909c9c7ec17202067e7206067e730b069c9a7205730c9a9c7e8cb27203730d0002067e730e067e9c72067e730f050690b0ada5d90107639593c272077310c1720773117312d90107599a8c7207018c72070273137314"),
    ("SwapBuy", "multiAddressV2", "d801d601b2a4730000d1ec730195ed93b1a4730293b1db630872017303d804d602db63087201d603b2a5730400d6049d9c7e99c17203c1a7067e7305067e730606d6058cb2db6308a773070002edededed938cb2720273080001730993c27203730a9272047e730b06909c9c7ec17201067e7205067e730c069c9a7204730d9a9c7e8cb27202730e0002067e730f067e9c72057e7310050690b0ada5d90106639593c272067311c1720673127313d90106599a8c7206018c72060273147315"),
    ("SwapBuy", "legacyV0", "d802d6017300d602b2a4730100eb027201d195ed93b1a4730293b1db630872027303d804d603db63087202d604b2a5730400d6059d9c7e99c17204c1a7067e7305067e730606d6068cb2db6308a773070002ededed938cb2720373080001730993c27204d072019272057e730a06909c9c7ec17202067e7206067e730b069c9a7205730c9a9c7e8cb27203730d0002067e730e067e9c72067e730f05067310"),
    ("Deposit", "v3", "d802d601b2a4730000d6027301eb027302d195ed92b1a4730393b1db630872017304d80bd603db63087201d604b2a5730500d605b27203730600d6067e9973078c72050206d6077ec1720106d6089d9c7e72020672067207d609b27203730800d60a7e8c72090206d60b9d9c7e7309067206720ad60cdb63087204d60db2720c730a00ededededed938cb27203730b0001730c93c27204730d95ed8f7208720b93b1720c730ed801d60eb2720c730f00eded92c1720499c1a77310938c720e018c720901927e8c720e02069d9c99720b7208720a720695927208720b927ec1720406997ec1a706997e7202069d9c997208720b720772067311938c720d018c720501927e8c720d0206a17208720b90b0ada5d9010e639593c2720e7312c1720e73137314d9010e599a8c720e018c720e0273157316"),
    ("Deposit", "v1", "d803d6017300d602b2a4730100d6037302eb027201d195ed92b1a4730393b1db630872027304d80bd604db63087202d605b2a5730500d606b27204730600d6077e9973078c72060206d6087ec1720206d6099d9c7e72030672077208d60ab27204730800d60b7e8c720a0206d60c9d9c7e8cb2db6308a773090002067207720bd60ddb63087205d60eb2720d730a00ededededed938cb27204730b0001730c93c27205d0720195ed8f7209720c93b1720d730dd801d60fb2720d730e00eded92c172059999c1a7730f7310938c720f018c720a01927e8c720f02069d9c99720c7209720b720795927209720c927ec1720506997e99c1a7731106997e7203069d9c997209720c720872077312938c720e018c720601927e8c720e0206a17209720c90b0ada5d9010f639593c2720f7313c1720f73147315d9010f599a8c720f018c720f0273167317"),
    ("Deposit", "legacyV1", "d803d6017300d602b2a4730100d6037302eb027201d195ed93b1a4730393b1db630872027304d80bd604db63087202d605b2a5730500d606b27204730600d6077e9973078c72060206d6087ec1720206d6099d9c7e72030672077208d60ab27204730800d60b7e8c720a0206d60c9d9c7e8cb2db6308a773090002067207720bd60ddb63087205d60eb2720d730a00edededed938cb27204730b0001730c93c27205d0720195ed8f7209720c93b1720d730dd801d60fb2720d730e00eded92c172059999c1a7730f7310938c720f018c720a01927e8c720f02069d9c99720c7209720b720795927209720c927ec1720506997e99c1a7731106997e7203069d9c997209720c720872077312938c720e018c720601927e8c720e0206a17209720c7313"),
    ("Deposit", "legacyV0", "d802d6017300d602b2a4730100eb027201d195ed93b1a4730293b1db630872027303d805d603db63087202d604b2a5730400d605b2db63087204730500d606b27203730600d6077e9973078c72060206edededed938cb2720373080001730993c27204d0720192c172049999c1a7730a730b938c7205018c720601927e8c72050206a19d9c7e730c0672077ec17202069d9c7e8cb2db6308a7730d00020672077e8cb27203730e000206730f"),
    ("Redeem", "v3", "d801d601b2a4730000eb027301d195ed92b1a4730293b1db630872017303d806d602db63087201d603b2a5730400d604b2db63087203730500d605b27202730600d6067e8cb2db6308a77307000206d6077e9973088cb272027309000206ededededed938cb27202730a0001730b93c27203730c938c7204018c720501927e99c17203c1a7069d9c72067ec17201067207927e8c720402069d9c72067e8c72050206720790b0ada5d90108639593c27208730dc17208730e730fd90108599a8c7208018c72080273107311"),
    ("Redeem", "v1", "d802d6017300d602b2a4730100eb027201d195ed92b1a4730293b1db630872027303d806d603db63087202d604b2a5730400d605b2db63087204730500d606b27203730600d6077e8cb2db6308a77307000206d6087e9973088cb272037309000206ededededed938cb27203730a0001730b93c27204d07201938c7205018c720601927e9a99c17204c1a7730c069d9c72077ec17202067208927e8c720502069d9c72077e8c72060206720890b0ada5d90109639593c27209730dc17209730e730fd90109599a8c7209018c72090273107311"),
    ("Redeem", "legacyV0", "d802d6017300d602b2a4730100eb027201d195ed93b1a4730293b1db630872027303d806d603db63087202d604b2a5730400d605b2db63087204730500d606b27203730600d6077e8cb2db6308a77307000206d6087e9973088cb272037309000206edededed938cb27203730a0001730b93c27204d07201938c7205018c720601927e9a99c17204c1a7730c069d9c72077ec17202067208927e8c720502069d9c72077e8c720602067208730d"),
]
ORDER_TEMPLATE_HASHES = {hashlib.sha256(bytes.fromhex(h)).hexdigest(): (k, v) for k, v, h in ERGODEX_N2T_ORDERS}


# ---- addresses (U1b): the /blocks/{id} endpoint gives an input's address, not its tree ----------------------

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def address_bytes(addr):
    n = 0
    for ch in addr:
        n = n * 58 + _B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(addr) - len(addr.lstrip("1"))) + raw


def address_tree(addr):
    """ErgoTree hex for a mainnet address, or None for pay-to-script-hash (the tree is not in the address).
    Layout: network+type byte, content, 4-byte checksum; type 1 P2PK (content = 33-byte key), 2 P2SH, 3 P2S."""
    b = address_bytes(addr)
    kind, content = b[0] & 0x0F, b[1:-4]
    if kind == 1:
        return "0008cd" + content.hex()
    if kind == 3:
        return content.hex()
    return None


def grid_orders(serialized):
    """Off the Grid R5, Coll[((Long, Boolean), (Long, Long))] serialized: [(amount, isBuy, buyTotal, sellTotal)].
    The type descriptor is skipped by finding the offset whose count and items consume the register exactly."""
    b = bytes.fromhex(serialized)

    def zz(i):
        v, i = _vlq(b, i)
        return (v >> 1) ^ -(v & 1), i

    for start in range(2, 12):
        try:
            n, i = _vlq(b, start)
            out = []
            for _ in range(n):
                amt, i = zz(i)
                if b[i] not in (0, 1):
                    raise ValueError
                st = b[i] == 1; i += 1
                buy, i = zz(i)
                sell, i = zz(i)
                out.append((amt, st, buy, sell))
            if i == len(b) and n > 0:
                return out
        except (IndexError, ValueError):
            continue
    return None
