"""ES256 JWS for the vector tokens (spec 02-api.md 2.2, spec 01-protocol.md 1.12, D83, D89).

The vectors' client tokens are signed with a P-256 test key whose private JWK lives next to this
module and nowhere else: `generate` writes only its public half to `vectors/keys/jwks.json`, and
neither the npm package nor the signed archive ships `conformance/`. Signing is deterministic
(RFC 6979), so regenerating the vectors gives byte-identical tokens.
"""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

from .chain import b64url_decode, b64url_encode

KEY_FILE = Path(__file__).with_name("test-key.private.jwk.json")
PUBLIC_MEMBERS = ("kty", "crv", "kid", "use", "alg", "x", "y")


class TokenError(ValueError):
    pass


def _uint256(value: str) -> int:
    """A JWK member holding 32 big-endian bytes in base64url: a P-256 coordinate or private scalar."""
    try:
        raw = b64url_decode(value)
    except ValueError as exc:
        raise TokenError("a P-256 JWK member is not base64url") from exc
    if len(raw) != 32:
        raise TokenError("a P-256 JWK member is 32 bytes, got %d" % len(raw))
    return int.from_bytes(raw, "big")


def _json(value: dict) -> str:
    return b64url_encode(json.dumps(value, separators=(",", ":")).encode("ascii"))


def load_private_jwk(path: Path = KEY_FILE) -> dict:
    return json.loads(path.read_text(encoding="ascii"))


def private_key(jwk: dict) -> ec.EllipticCurvePrivateKey:
    """The key of a private P-256 JWK, checked against the public point the JWK names."""
    key = ec.derive_private_key(_uint256(jwk["d"]), ec.SECP256R1())
    point = key.public_key().public_numbers()
    if (point.x, point.y) != (_uint256(jwk["x"]), _uint256(jwk["y"])):
        raise TokenError("the private JWK's d does not match its x and y")
    return key


def public_jwk(jwk: dict) -> dict:
    return {k: jwk[k] for k in PUBLIC_MEMBERS if k in jwk}


def jwks(path: Path = KEY_FILE) -> dict:
    """The public JWKS of the test key, as `vectors/keys/jwks.json` publishes it."""
    jwk = load_private_jwk(path)
    private_key(jwk)
    return {"keys": [public_jwk(jwk)]}


def sign(
    claims: dict,
    key: ec.EllipticCurvePrivateKey | None = None,
    kid: str | None = None,
) -> str:
    """A compact ES256 JWS over the claims; the test key and its kid unless others are given."""
    if key is None:
        key = private_key(load_private_jwk())
    if kid is None:
        kid = load_private_jwk()["kid"]
    signing_input = (
        _json({"alg": "ES256", "typ": "JWT", "kid": kid}) + "." + _json(claims)
    )
    der = key.sign(
        signing_input.encode("ascii"),
        ec.ECDSA(hashes.SHA256(), deterministic_signing=True),
    )
    r, s = decode_dss_signature(der)
    return (
        signing_input
        + "."
        + b64url_encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    )


def _decode_json(segment: str, what: str) -> dict:
    try:
        value = json.loads(b64url_decode(segment))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TokenError("the %s is not base64url JSON" % what) from exc
    if not isinstance(value, dict):
        raise TokenError("the %s is not a JSON object" % what)
    return value


def verify(token: str, keys: dict) -> dict:
    """The claims of a compact ES256 JWS whose kid names a P-256 key of the JWKS and whose
    signature verifies with it; raises TokenError otherwise."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("not a JWS compact serialisation")
    header = _decode_json(parts[0], "header")
    if header.get("alg") != "ES256":
        raise TokenError("alg is not ES256")
    kid = header.get("kid")
    match = [
        k
        for k in keys.get("keys", [])
        if k.get("kid") == kid and k.get("kty") == "EC" and k.get("crv") == "P-256"
    ]
    if not kid or not match:
        raise TokenError("kid %r names no P-256 key of the JWKS" % kid)
    try:
        signature = b64url_decode(parts[2])
    except ValueError as exc:
        raise TokenError("the signature is not base64url") from exc
    if len(signature) != 64:
        raise TokenError("the signature is not 64 bytes")
    x, y = _uint256(match[0]["x"]), _uint256(match[0]["y"])
    try:
        public = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    except ValueError as exc:
        raise TokenError("the JWKS key %r is not a point on P-256" % kid) from exc
    der = encode_dss_signature(
        int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    )
    try:
        public.verify(
            der,
            (parts[0] + "." + parts[1]).encode("ascii"),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature as exc:
        raise TokenError("the signature does not verify") from exc
    return _decode_json(parts[1], "payload")
