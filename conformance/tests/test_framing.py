import pytest

from zakadi_conformance.framing import (FramingError, Header, build_audio_batch, decode_header, encode_header, encode_message,
                                        next_seq, parse_audio_batch, parse_probe_payload)


def test_header_roundtrip_all_fields():
    h = Header(type=3, seq=65535, pts_ms=4294967295, rung=15, keyframe=True, param_sets=True, rung_changed=True)
    assert decode_header(encode_header(h)) == h
    assert len(encode_header(h)) == 8


def test_header_bit_layout():
    raw = encode_header(Header(type=1, seq=0x0102, pts_ms=0x01020304, rung=2, keyframe=True))
    assert raw == bytes([0x18, 0x20, 0x02, 0x01, 0x04, 0x03, 0x02, 0x01])


@pytest.mark.parametrize("raw,code", [
    (b"\x40" + b"\x00" * 7, "unsupported_version"),
    (b"\x01" + b"\x00" * 7, "reserved_bit_set"),
    (b"\x00\x0f" + b"\x00" * 6, "reserved_bits_set"),
    (b"\x00" * 7, "short_header"),
])
def test_header_errors(raw, code):
    with pytest.raises(FramingError) as exc:
        decode_header(raw)
    assert exc.value.code == code


def test_probe_and_batch_payloads():
    assert parse_probe_payload((1234).to_bytes(8, "little") + b"xx") == 1234
    with pytest.raises(FramingError):
        parse_probe_payload(b"\x01")
    records = [(0, b"a"), (20, b"bc"), (40, b"")]
    assert parse_audio_batch(build_audio_batch(records)) == records
    with pytest.raises(FramingError) as exc:
        parse_audio_batch(build_audio_batch([(20, b"a"), (0, b"b")]))
    assert exc.value.code == "batch_out_of_order"


def test_seq_wraps():
    assert next_seq(65535) == 0
    assert encode_message(Header(type=0, seq=0, pts_ms=0), b"p")[8:] == b"p"
