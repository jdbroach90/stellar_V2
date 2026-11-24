"""Short-lived, first-party demo-engagement attestations for lead measurement.

The browser supplies playback data and can be spoofed by an adversarial client;
these tokens are NOT proof that a human watched. They reduce accidental, bot
preview, page-load and seeking-only conversions. A normal inquiry is always
accepted independently of these optional marketing measurements.
"""

import hashlib
import hmac
import math
import secrets
import time
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

START_TTL = 20 * 60
QUALIFIED_TTL = 30 * 60
MIN_WALL_SECONDS = 25
MIN_DURATION_SECONDS = 15
MAX_DURATION_SECONDS = 4 * 60 * 60
MIN_COVERAGE_RATIO = 0.50
COOKIE_NAME = "cj_demo_flow"


def derive_secret(configured_secret, analytics_origin_secret=""):
    """Keep marketing tokens separate from the configured root secrets.

    An explicit 32+ char secret is preferred; use an already configured
    analytics origin secret to avoid silently disabling the funnel on rollout.
    Both are hashed with a domain-separation label, never sent to the browser.
    """
    root = configured_secret if len(configured_secret or "") >= 32 else analytics_origin_secret
    if not isinstance(root, str) or len(root) < 32:
        return None
    return hashlib.sha256(b"codejet-demo-lead-v1\0" + root.encode()).hexdigest()


def serializer(secret):
    return URLSafeTimedSerializer(secret, salt="codejet-demo-engagement-v1")


def issue_start(secret, now=None):
    if not secret:
        return None
    nonce = secrets.token_urlsafe(20)
    stamp = int(time.time() if now is None else now)
    return serializer(secret).dumps({"v": 1, "p": "start", "nonce": nonce, "started": stamp}), nonce


def _decode(secret, token, purpose, max_age):
    if not secret or not isinstance(token, str) or not 12 < len(token) < 2048:
        return None
    try:
        value = serializer(secret).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None
    if (not isinstance(value, dict) or value.get("v") != 1 or value.get("p") != purpose or
            not isinstance(value.get("nonce"), str) or not 12 <= len(value["nonce"]) <= 100):
        return None
    return value


def _matches_cookie(nonce, cookie):
    return isinstance(cookie, str) and hmac.compare_digest(nonce, cookie)


def qualify(secret, start_token, cookie, played_seconds, duration_seconds, now=None):
    """Issue a lead token only for a clicked, plausibly watched demo.

    Coverage originates from Stream's actual played ranges; seeks do not advance
    them. Elapsed wall time adds protection against instant scripted completion.
    This remains client-reported measurement, not attested human attention.
    """
    start = _decode(secret, start_token, "start", START_TTL)
    if not start or not _matches_cookie(start["nonce"], cookie):
        return None
    if isinstance(played_seconds, bool) or isinstance(duration_seconds, bool):
        return None
    try:
        played = float(played_seconds)
        duration = float(duration_seconds)
    except (ValueError, TypeError, OverflowError):
        return None
    if not (math.isfinite(played) and math.isfinite(duration)):
        return None
    if not (MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS and
            0 <= played <= duration + 0.1 and played / duration >= MIN_COVERAGE_RATIO):
        return None
    elapsed = (time.time() if now is None else now) - start.get("started", 0)
    # 2x playback is valid; a seek to the end or instant automation is not.
    if not isinstance(elapsed, (int, float)) or elapsed < max(MIN_WALL_SECONDS, played / 2 - 2):
        return None
    payload = {"v": 1, "p": "qualified", "nonce": start["nonce"],
               "coverage": int(min(100, 100 * played / duration))}
    return serializer(secret).dumps(payload)


def validate_qualified(secret, token, cookie):
    value = _decode(secret, token, "qualified", QUALIFIED_TTL)
    if not value or not _matches_cookie(value["nonce"], cookie):
        return None
    if not isinstance(value.get("coverage"), int) or value["coverage"] < 50:
        return None
    # This is a random per-watch identifier, suitable as a GTM transaction_id.
    # It is not an email, IP, cookie, or user identifier.
    return value["nonce"]
