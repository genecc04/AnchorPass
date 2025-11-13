import base64, hmac, hashlib, struct, time, urllib.parse, binascii
from typing import Optional, Tuple

def _b32decode(secret_b32: str) -> bytes:
    s = (secret_b32 or "").strip().replace(" ", "").replace("-", "").upper()
    if not s:
        return b""
    s += "=" * ((8 - (len(s) % 8)) % 8)
    try:
        return base64.b32decode(s, casefold=True)
    except (binascii.Error, Exception):
        return b""

def _counter(ts: float | None = None, period: int = 30) -> int:
    if ts is None:
        ts = time.time()
    return int(ts // period)

def hotp(secret: str | bytes, counter: int, digits: int = 6, algorithm: str = "sha1") -> str:
    if isinstance(secret, str):
        key = _b32decode(secret)
    else:
        key = secret
    if not key:
        return ""
    try:
        digest = getattr(hashlib, algorithm.lower())
    except AttributeError:
        digest = hashlib.sha1
    try:
        h = hmac.new(key, struct.pack(">Q", counter), digest).digest()
        o = h[-1] & 0x0F
        code_int = (struct.unpack(">I", h[o:o + 4])[0] & 0x7fffffff) % (10 ** digits)
        return str(code_int).zfill(digits)
    except Exception:
        return ""

def totp(secret: str, digits: int = 6, period: int = 30, algorithm: str = "sha1", ts: float | None = None) -> str:
    if not secret:
        return ""
    try:
        return hotp(secret, _counter(ts, period), digits, algorithm)
    except Exception:
        return ""

def seconds_remaining(period: int = 30, ts: float | None = None) -> int:
    if ts is None:
        ts = time.time()
    return (period - 1) - (int(ts) % period)

def parse_otpauth(uri: str) -> dict | None:
    try:
        p = urllib.parse.urlparse(uri)
        if p.scheme != "otpauth":
            return None
        q = urllib.parse.parse_qs(p.query)
        return {
            "secret": q.get("secret", [""])[0],
            "issuer": q.get("issuer", [""])[0],
            "digits": int(q.get("digits", ["6"])[0]),
            "period": int(q.get("period", ["30"])[0]),
            "algorithm": q.get("algorithm", ["SHA1"])[0].lower(),
        }
    except Exception:
        return None

def coerce_secret(text: str) -> Tuple[str, int, int, str]:
    if not text:
        return "", 6, 30, "sha1"
    s = text.strip()
    if s.lower().startswith("otpauth://"):
        parsed = parse_otpauth(s) or {}
        return (
            parsed.get("secret", "") or "",
            int(parsed.get("digits", 6)),
            int(parsed.get("period", 30)),
            (parsed.get("algorithm", "sha1") or "sha1").lower(),
        )
    return s, 6, 30, "sha1"

def totp_from_uri_or_secret(text: str, ts: Optional[float] = None) -> Tuple[str, int, int]:
    secret, digits, period, algo = coerce_secret(text or "")
    code = totp(secret, digits=digits, period=period, algorithm=algo, ts=ts)
    rem = seconds_remaining(period=period, ts=ts)
    return code, rem, period
