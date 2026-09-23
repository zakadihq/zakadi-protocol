"""Hash chain attested by the client every 1000 ms of video pts (spec 01-protocol.md, `attest`).

H0 = SHA256(utf8(session_id) || jti_bytes), no separator, where jti_bytes are the 16 raw bytes of the
token's `jti` claim (base64url without padding in the JWT). For each media message of type 0, 1 or 3 in
send order, Hn = SHA256(Hn-1 || header8 || payload). Probes (type 2) are excluded. `chain` is lowercase hex.
"""

from __future__ import annotations

import base64
import hashlib
import json

from .framing import CHAINED_TYPES, HEADER_LEN, decode_header


class ChainError(ValueError):
    pass


def b64url_decode(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def jti_bytes_from_token(token: str) -> bytes:
    """Reads the jti claim from an unverified JWT (the client never verifies the token)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ChainError("token is not a JWT")
    try:
        claims = json.loads(b64url_decode(parts[1]))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ChainError("token payload is not JSON") from exc
    jti = claims.get("jti")
    if not isinstance(jti, str):
        raise ChainError("token has no jti claim")
    raw = b64url_decode(jti)
    if len(raw) != 16:
        raise ChainError("jti must decode to 16 bytes, got %d" % len(raw))
    return raw


def h0(session_id: str, jti: bytes) -> bytes:
    if len(jti) != 16:
        raise ChainError("jti must be 16 bytes")
    return hashlib.sha256(session_id.encode("utf-8") + jti).digest()


def advance(state: bytes, message: bytes) -> bytes:
    return hashlib.sha256(state + message[:HEADER_LEN] + message[HEADER_LEN:]).digest()


class Chain:
    """Feeds media messages in send order and exposes the current chain value."""

    def __init__(self, session_id: str, jti: bytes) -> None:
        self.state = h0(session_id, jti)
        self.count = 0

    def feed(self, message: bytes) -> bool:
        """Returns True when the message was chained (types 0, 1, 3), False when skipped (probe)."""
        header = decode_header(message)
        if header.type not in CHAINED_TYPES:
            return False
        self.state = advance(self.state, message)
        self.count += 1
        return True

    @property
    def hex(self) -> str:
        return self.state.hex()
