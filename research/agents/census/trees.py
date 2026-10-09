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


def _skip_const(b, i):
    t = b[i]; i += 1
    if t in (4, 5, 3):          # Int, Long, Short: zigzag VLQ
        _, i = _vlq(b, i)
    elif t == 1 or t == 2:      # Boolean, Byte
        i += 1
    elif t == 0x0e or t == 0x06:  # Coll[Byte], BigInt
        n, i = _vlq(b, i); i += n
    elif t == 0x10:             # Coll[Int]
        n, i = _vlq(b, i)
        for _ in range(n):
            _, i = _vlq(b, i)
    elif t == 0x08:             # SigmaProp: ProveDlog only
        assert b[i] == 0xcd; i += 34
    elif t == 0x07:             # GroupElement
        i += 33
    else:
        raise ValueError(f"constant type {t:#x} not handled")
    return i


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


def babel_token(tree_hex):
    """Token id a Babel box bids for (its constant 1), or None if the tree is not the EIP-31 template."""
    if not tree_hex.startswith("100604000e20") or template_hash(tree_hex) != BABEL_TEMPLATE_HASH:
        return None
    return tree_hex[12:76]
