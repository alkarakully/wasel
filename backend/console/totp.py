"""
Authenticator app codes (TOTP, RFC 6238): 6 digits, 30-second steps, SHA-1,
as Google Authenticator, Microsoft Authenticator and 1Password expect.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import unicodedata
from urllib.parse import quote

STEP = 30
DIGITS = 6


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code(secret, step):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def current_step(now=None):
    return int((now if now is not None else time.time()) // STEP)


def code_at(secret, now=None):
    return _code(secret, current_step(now))


def verify(secret, code, last_step=0, now=None):
    """
    The time step the code belongs to (allowing one step of clock drift either
    way), or None. Steps at or before `last_step` are refused so a code can't
    be replayed.
    """
    # Arabic-Indic and Persian digits count too (phones typing in Arabic).
    code = "".join(str(unicodedata.digit(ch)) for ch in str(code) if ch.isdigit())
    if len(code) != DIGITS or not secret:
        return None
    step = current_step(now)
    for candidate in (step - 1, step, step + 1):
        if candidate > last_step and hmac.compare_digest(_code(secret, candidate), code):
            return candidate
    return None


def provisioning_uri(secret, email, issuer="Wasel"):
    label = quote(f"{issuer}:{email}", safe=":")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"
