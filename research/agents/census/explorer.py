"""Explorer access for the U1 census: one `get` with retries, a rate limit and a raw-response cache.

The cache lives under research/agents/census/raw/ (git-ignored). A cached response is reused only for paths
that cannot change once the window is fixed (anything with an explicit height bound, a transaction or box id);
listing endpoints are cached too, keyed by their full path, so a rerun over the same window is offline.
"""
import hashlib, json, os, threading, time, urllib.request

EXPLORER = os.environ.get("ERGO_EXPLORER", "https://api.ergo.aap.cornell.edu/api/v1")
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
MIN_INTERVAL = 0.22  # about 4.5 requests a second
_last = [0.0]
_lock = threading.Lock()  # U1b fetches blocks from a few threads; the rate limit stays global
stats = {"net": 0, "cache": 0}


def _cache_path(path):
    h = hashlib.sha256((EXPLORER + path).encode()).hexdigest()
    return os.path.join(RAW, h[:2], h + ".json")


def _parse(text, path):
    """JSON, or the stream endpoints' concatenated JSON objects (returned as a list)."""
    dec, i, out, n = json.JSONDecoder(), 0, [], len(text)
    while True:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        obj, i = dec.raw_decode(text, i)
        out.append(obj)
    if not out:
        return []
    return out[0] if len(out) == 1 and "/stream" not in path else out


def get(path, cache=True, method="GET", body=None):
    cp = _cache_path(path + (json.dumps(body, sort_keys=True) if body is not None else ""))
    if cache and os.path.exists(cp):
        stats["cache"] += 1
        with open(cp) as f:
            return json.load(f)
    for attempt in range(6):
        with _lock:
            wait = MIN_INTERVAL - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(EXPLORER + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"} if data else {})
            with urllib.request.urlopen(req, timeout=120) as r:
                out = _parse(r.read().decode(), path)
            break
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) == 404:
                return None
            if attempt == 5:
                raise
            time.sleep(2 ** (attempt + 1))
    stats["net"] += 1
    if cache:
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        with open(cp + ".tmp", "w") as f:
            json.dump(out, f)
        os.replace(cp + ".tmp", cp)
    return out


def tip():
    return get("/networkState", cache=False)["height"]
