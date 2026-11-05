"""Authentification légère : PIN élève (PBKDF2), jetons HMAC signés, anti-force-brute."""
import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
TOKEN_TTL = 12 * 3600            # une session dure 12 h
MAX_FAILS, WINDOW = 5, 300       # 5 erreurs en 5 min => blocage temporaire
_fails: dict[str, list[float]] = {}


def _secret() -> bytes:
    env = os.getenv("FUTURA_SECRET")
    if env:
        return env.encode()
    f = DATA / ".secret"
    if not f.exists():
        DATA.mkdir(exist_ok=True)
        f.write_text(secrets.token_hex(32))
    return f.read_text().encode()


def hash_pin(pin: str) -> str:
    salt = os.urandom(8).hex()
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', pin.encode(), salt.encode(), 100_000).hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    salt, h = stored.split("$")
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex(), h)


def subject(user) -> str:
    """Identité inscrite dans le jeton : change si le PIN change (anciennes sessions invalidées)."""
    return f"{user.name}:{(user.pin_hash or '')[-8:]}"


def make_token(sub: str) -> str:
    payload = f"{sub}|{int(time.time()) + TOKEN_TTL}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def read_token(token: str | None) -> str | None:
    try:
        sub, exp, sig = base64.urlsafe_b64decode((token or "").encode()).decode().rsplit("|", 2)
        good = hmac.new(_secret(), f"{sub}|{exp}".encode(), hashlib.sha256).hexdigest()
        return sub if hmac.compare_digest(sig, good) and int(exp) > time.time() else None
    except Exception:
        return None


def locked(key: str) -> bool:
    _fails[key] = [t for t in _fails.get(key, []) if time.time() - t < WINDOW]
    return len(_fails[key]) >= MAX_FAILS


def register_fail(key: str) -> None:
    _fails.setdefault(key, []).append(time.time())


def clear_fails(key: str) -> None:
    _fails.pop(key, None)
