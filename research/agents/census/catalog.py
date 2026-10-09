"""Known contract templates for U1b line (f): every ErgoTree or template hex in public contract sources, hashed the
explorer's way (SHA-256 of the template bytes, census/trees.py). Names are `source:path:identifier`.

Sources are local clones (not vendored; paths in CENSUS-U1B.md). A hex string that parses as a whole tree is
hashed through template_bytes; one that does not (a bare template, as the Spectrum SDK and the Lithos client pin
them) is hashed as is.

usage: catalog.py SRC_DIR [SRC_DIR ...] > catalog.json
"""
import hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trees as T  # noqa: E402

EXT = (".ts", ".js", ".scala", ".sc", ".es", ".md", ".json", ".py", ".rs", ".kt", ".java", ".ergotree", ".hex",
       ".txt", ".ergo", ".conf", ".tsx")
JOIN = re.compile(r"""(["'])\s*\+\s*(["'])""")
HEX = re.compile(r"""(?:["']|^)([0-9a-fA-F]{120,})(?:["']|$)""", re.M)
ADDR = re.compile(r"""\b([1-9A-HJ-NP-Za-km-z]{60,})\b""")   # P2S addresses (mainnet prefix 0x03)
NAME = re.compile(r"""(?:const|val|var|def|function|let|export const|lazy val)\s+([A-Za-z_][A-Za-z0-9_]*)""")


def hashes(h):
    """(template hash, how) for one hex string, or [] when it is neither a tree nor plausible template."""
    out = []
    try:
        tb = T.template_bytes(h)
        if 0 < len(tb) < len(h) // 2 + 1 and h[:2] in ("00", "08", "10", "18", "19", "09", "11", "1a", "1b"):
            out.append((hashlib.sha256(tb).hexdigest(), "tree"))
    except Exception:  # noqa: BLE001
        pass
    out.append((hashlib.sha256(bytes.fromhex(h)).hexdigest(), "template"))
    return out


def scan(root):
    cat = {}
    for dp, _, fs in os.walk(root):
        if "/.git" in dp or "node_modules" in dp:
            continue
        for f in fs:
            if not f.endswith(EXT):
                continue
            p = os.path.join(dp, f)
            if f.endswith(".ergotree") and open(p, "rb").read(1) in (b"\x00", b"\x10", b"\x18", b"\x19"):
                raw = open(p, "rb").read()      # a binary tree file (Off the Grid cli/grid_multi.ergotree)
                th = T.template_hash(raw.hex())
                cat.setdefault(th, []).append({"name": f"{os.path.basename(root.rstrip('/'))}:"
                                               f"{os.path.relpath(p, root)}:binary", "how": "tree", "len": len(raw)})
                continue
            try:
                s = open(p, errors="ignore").read()
            except OSError:
                continue
            s2 = JOIN.sub("", s)
            for m in HEX.finditer(s2):
                h = m.group(1).lower()
                if len(h) % 2:
                    continue
                names = NAME.findall(s2[max(0, m.start() - 400):m.start()])
                name = f"{os.path.basename(root.rstrip("/"))}:{os.path.relpath(p, root)}:{names[-1] if names else '?'}"
                for th, how in hashes(h):
                    cat.setdefault(th, []).append({"name": name, "how": how, "len": len(h) // 2})
            for m in ADDR.finditer(s2):
                try:
                    b = T.address_bytes(m.group(1))
                    if b[0] != 0x03 or hashlib.blake2b(b[:-4], digest_size=32).digest()[:4] != b[-4:]:
                        continue
                    th = T.template_hash(b[1:-4].hex())
                except Exception:  # noqa: BLE001
                    continue
                names = NAME.findall(s2[max(0, m.start() - 400):m.start()])
                name = f"{os.path.basename(root.rstrip("/"))}:{os.path.relpath(p, root)}:{names[-1] if names else '?'}"
                cat.setdefault(th, []).append({"name": name, "how": "address", "len": len(b) - 5})
    return cat


if __name__ == "__main__":
    cat = {}
    for r in sys.argv[1:]:
        for k, v in scan(r).items():
            cat.setdefault(k, []).extend(v)
    json.dump(cat, sys.stdout, indent=0)
