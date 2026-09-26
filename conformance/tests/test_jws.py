import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from zakadi_conformance import examples, jws
from zakadi_conformance.chain import b64url_decode, b64url_encode


def test_signing_is_deterministic_and_verifies_against_the_jwks():
    token = jws.sign(examples.CLAIMS)
    assert token == jws.sign(examples.CLAIMS) == examples.TOKEN
    assert jws.verify(token, jws.jwks()) == examples.CLAIMS
    header = json.loads(b64url_decode(token.split(".")[0]))
    assert header == {"alg": "ES256", "typ": "JWT", "kid": "zakadi-vectors-test-1"}
    assert len(b64url_decode(token.split(".")[2])) == 64


def test_the_jwks_is_the_public_half_of_the_test_key():
    private = jws.load_private_jwk()
    (public,) = jws.jwks()["keys"]
    assert "d" not in public and "test" in public["kid"]
    assert public == {k: private[k] for k in public}
    point = jws.private_key(private).public_key().public_numbers()
    assert b64url_decode(public["x"]) == point.x.to_bytes(32, "big")
    assert b64url_decode(public["y"]) == point.y.to_bytes(32, "big")


def test_another_key_or_an_altered_payload_does_not_verify():
    other = ec.generate_private_key(ec.SECP256R1())
    forged = jws.sign(examples.CLAIMS, key=other, kid="zakadi-vectors-test-1")
    with pytest.raises(jws.TokenError, match="does not verify"):
        jws.verify(forged, jws.jwks())
    head, _, sig = examples.TOKEN.split(".")
    altered = b64url_encode(json.dumps(examples.CLAIMS | {"sub": "ses_x"}).encode())
    with pytest.raises(jws.TokenError, match="does not verify"):
        jws.verify(".".join((head, altered, sig)), jws.jwks())
    with pytest.raises(jws.TokenError, match="names no P-256 key"):
        jws.verify(jws.sign(examples.CLAIMS, kid="another"), jws.jwks())


def test_the_token_carries_the_claims_of_the_api_spec():
    claims = jws.verify(examples.TOKEN, jws.jwks())
    assert list(claims) == [
        "iss",
        "aud",
        "sub",
        "tid",
        "jti",
        "iat",
        "nbf",
        "exp",
        "pol",
        "band_max",
        "ing",
        "nonce",
        "lang",
    ]
    assert claims["exp"] == claims["iat"] + 300
    assert claims["sub"] == examples.SESSION_ID
    assert claims["jti"] == examples.JTI and claims["nonce"] == examples.NONCE
