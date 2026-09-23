import hashlib

from zakadi_conformance import examples
from zakadi_conformance.chain import (
    Chain,
    b64url_decode,
    b64url_encode,
    h0,
    jti_bytes_from_token,
)
from zakadi_conformance.framing import Header, encode_message


def test_h0_definition():
    jti = bytes(range(16))
    assert h0("ses_x", jti) == hashlib.sha256(b"ses_x" + jti).digest()


def test_probe_excluded_and_order_matters():
    jti = bytes(range(16))
    a = encode_message(Header(type=0, seq=0, pts_ms=0), b"a")
    b = encode_message(Header(type=1, seq=0, pts_ms=0), b"b")
    probe = encode_message(Header(type=2, seq=0, pts_ms=0), (1).to_bytes(8, "little"))
    c1 = Chain("ses_x", jti)
    assert c1.feed(a) and not c1.feed(probe) and c1.feed(b)
    c2 = Chain("ses_x", jti)
    c2.feed(b)
    c2.feed(a)
    assert c1.hex != c2.hex
    c3 = Chain("ses_x", jti)
    c3.feed(a)
    c3.feed(b)
    assert c1.hex == c3.hex


def test_token_jti_extraction():
    assert jti_bytes_from_token(examples.TOKEN) == b64url_decode(examples.JTI)
    assert b64url_encode(bytes(range(16))) == examples.JTI
