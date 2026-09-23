"""Deterministic generation of schemas and test vectors into the repository."""

from __future__ import annotations

import copy
import json
import struct
from pathlib import Path

from . import examples
from .chain import Chain, b64url_decode, h0
from .framing import Header, build_audio_batch, encode_message
from .schemas import all_schemas


def _dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="ascii")


def _pattern(n: int, seed: int) -> bytes:
    """Deterministic pseudo-random bytes (LCG), so regeneration is stable without a RNG dependency."""
    out = bytearray()
    x = seed & 0xFFFFFFFF
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def _annexb(nal_types: list[int], seed: int) -> bytes:
    out = bytearray()
    for i, nt in enumerate(nal_types):
        out += b"\x00\x00\x00\x01" + bytes([0x60 | nt]) + _pattern(24 + 8 * i, seed + i)
    return bytes(out)


def _derived_invalids(schema: dict, valid: dict) -> list[tuple[str, dict]]:
    """Mechanically derived invalid instances: each required field missing, and the first non-t required field mistyped."""
    cases: list[tuple[str, dict]] = []
    required = [r for r in schema.get("required", []) if r != "t"]
    for r in required:
        bad = copy.deepcopy(valid)
        bad.pop(r, None)
        cases.append(("missing-" + r, bad))
    if required:
        r = required[0]
        prop = schema["properties"].get(r, {})
        bad = copy.deepcopy(valid)
        bad[r] = 12345 if prop.get("type") == "object" else {"bad": True}
        cases.append(("wrong-type-" + r, bad))
    bad = copy.deepcopy(valid)
    bad["t"] = "bogus_" + valid["t"]
    cases.append(("wrong-t", bad))
    return cases


def write_schemas(root: Path) -> None:
    for rel, schema in all_schemas().items():
        _dump(root / "schemas" / "v1" / rel, schema)


def write_message_vectors(root: Path) -> None:
    schemas = all_schemas()
    for direction, valid_map, extra_map, invalid_map in (
        ("client", examples.VALID_CLIENT, examples.EXTRA_VALID_CLIENT, examples.INVALID_CLIENT),
        ("server", examples.VALID_SERVER, examples.EXTRA_VALID_SERVER, examples.INVALID_SERVER),
    ):
        for t, valid in valid_map.items():
            d = root / "vectors" / "messages" / direction / t
            _dump(d / "valid.json", valid)
            for i, extra in enumerate(extra_map.get(t, []), start=1):
                _dump(d / ("valid-%d.json" % i), extra)
            schema = schemas[direction + "/" + t + ".schema.json"]
            for name, bad in _derived_invalids(schema, valid):
                _dump(d / ("invalid-" + name + ".json"), bad)
            for name, bad in invalid_map.get(t, []):
                _dump(d / ("invalid-" + name + ".json"), bad)


def framing_cases() -> list[dict]:
    cases: list[dict] = []

    def valid(name: str, description: str, header: Header, payload: bytes, **extra) -> None:
        msg = encode_message(header, payload)
        expect = {"header": header.as_dict(), "payload_hex": payload.hex()}
        expect.update(extra)
        cases.append({"name": name, "description": description, "hex": msg.hex(), "expect": expect, "_bin": msg})

    def invalid(name: str, description: str, data: bytes, error: str) -> None:
        cases.append({"name": name, "description": description, "hex": data.hex(), "error": error})

    valid("video-idr-with-params", "Video IDR at rung 2 with SPS and PPS preceding the slice (Annex-B start codes).",
          Header(type=0, seq=1042, pts_ms=8420, rung=2, keyframe=True, param_sets=True), _annexb([7, 8, 5], 1))
    valid("video-p-frame", "Video non-IDR slice, no parameter sets.",
          Header(type=0, seq=1043, pts_ms=8487, rung=2), _annexb([1], 2))
    valid("video-rung-changed", "First video message after a rung change to rung 3; a rung JSON message must accompany it.",
          Header(type=0, seq=1044, pts_ms=8554, rung=3, keyframe=True, param_sets=True, rung_changed=True), _annexb([7, 8, 5], 3))
    valid("audio-opus-packet", "One 20 ms Opus packet at rung 2.",
          Header(type=1, seq=511, pts_ms=8420, rung=2), _pattern(61, 4))
    batch = [(0, _pattern(58, 5)), (20, _pattern(60, 6)), (40, _pattern(57, 7))]
    valid("audio-batch-three-records", "Three Opus packets batched at rung 4; the batch consumes one audio seq value.",
          Header(type=3, seq=512, pts_ms=8440, rung=4), build_audio_batch(batch),
          audio_batch=[{"pts_delta_ms": d, "packet_hex": p.hex()} for d, p in batch])
    probe_payload = struct.pack("<Q", 1200450) + _pattern(48, 8)
    valid("probe", "Probe message: uint64 little-endian send time in microseconds, then filler; probes have their own seq space.",
          Header(type=2, seq=0, pts_ms=0, rung=0), probe_payload, probe_send_time_us=1200450)
    valid("seq-max", "seq at its maximum value; the next message of this type carries seq 0.",
          Header(type=0, seq=65535, pts_ms=60000, rung=2), _annexb([1], 9))
    valid("seq-wrapped", "The message following seq 65535 carries seq 0 (wraparound is not a gap).",
          Header(type=0, seq=0, pts_ms=60067, rung=2), _annexb([1], 10))
    valid("pts-max", "pts_ms at its maximum uint32 value.",
          Header(type=1, seq=7, pts_ms=4294967295, rung=1), _pattern(40, 11))
    valid("all-flags-rung-15", "Every flag set and rung 15 (the header allows rungs the ladder does not use).",
          Header(type=0, seq=1, pts_ms=1, rung=15, keyframe=True, param_sets=True, rung_changed=True), _annexb([7, 8, 5], 12))

    good = encode_message(Header(type=0, seq=1, pts_ms=1, rung=2, keyframe=True), _annexb([5], 13))
    invalid("invalid-version", "Framing version bits set to 1.", bytes([good[0] | 0x40]) + good[1:], "unsupported_version")
    invalid("invalid-reserved-bit0", "Byte 0 bit 0 set.", bytes([good[0] | 0x01]) + good[1:], "reserved_bit_set")
    invalid("invalid-reserved-byte1", "Byte 1 low nibble set.", good[:1] + bytes([good[1] | 0x05]) + good[2:], "reserved_bits_set")
    invalid("short-header", "Only five bytes.", good[:5], "short_header")
    invalid("short-probe", "Probe payload shorter than the 8-byte send time.",
            encode_message(Header(type=2, seq=1, pts_ms=0), b"\x01\x02\x03\x04"), "short_probe")
    invalid("truncated-batch", "Batch record declares 100 bytes but carries 3.",
            encode_message(Header(type=3, seq=2, pts_ms=100, rung=4), struct.pack("<HH", 100, 0) + b"\x01\x02\x03"), "truncated_batch_record")
    invalid("batch-out-of-order", "Batch records with decreasing pts_delta_ms.",
            encode_message(Header(type=3, seq=3, pts_ms=100, rung=4), build_audio_batch([(20, b"\x01"), (0, b"\x02")])), "batch_out_of_order")
    invalid("empty-batch", "Audio batch with no records.",
            encode_message(Header(type=3, seq=4, pts_ms=100, rung=4), b""), "empty_batch")
    return cases


def write_framing_vectors(root: Path) -> None:
    d = root / "vectors" / "framing"
    for case in framing_cases():
        case = dict(case)
        raw = case.pop("_bin", None)
        _dump(d / (case["name"] + ".json"), case)
        if raw is not None:
            (d / (case["name"] + ".bin")).write_bytes(raw)


def chain_cases() -> list[dict]:
    jti = b64url_decode(examples.JTI)
    cases = []
    for name, description, messages in (
        ("basic", "Five media messages including one probe (excluded) and one audio batch (included).", [
            encode_message(Header(type=0, seq=0, pts_ms=0, rung=2, keyframe=True, param_sets=True), _annexb([7, 8, 5], 21)),
            encode_message(Header(type=1, seq=0, pts_ms=0, rung=2), _pattern(61, 22)),
            encode_message(Header(type=2, seq=0, pts_ms=0, rung=0), struct.pack("<Q", 5000) + _pattern(56, 23)),
            encode_message(Header(type=3, seq=1, pts_ms=20, rung=2), build_audio_batch([(0, _pattern(60, 24)), (20, _pattern(59, 25))])),
            encode_message(Header(type=0, seq=1, pts_ms=67, rung=2), _annexb([1], 26)),
        ]),
        ("empty", "No media yet: the chain equals H0.", []),
        ("probes-only", "Only probes were sent: the chain still equals H0.", [
            encode_message(Header(type=2, seq=i, pts_ms=0, rung=0), struct.pack("<Q", 1000 + i) + _pattern(56, 30 + i)) for i in range(3)]),
    ):
        chain = Chain(examples.SESSION_ID, jti)
        entries = []
        vseq = aseq = 0
        for m in messages:
            chained = chain.feed(m)
            typ = (m[0] >> 4) & 3
            if typ == 0:
                vseq = struct.unpack("<H", m[2:4])[0]
            elif typ in (1, 3):
                aseq = struct.unpack("<H", m[2:4])[0]
            entries.append({"hex": m.hex(), "chained": chained, "chain_after": chain.hex})
        cases.append({
            "name": name, "description": description, "session_id": examples.SESSION_ID, "jti": examples.JTI,
            "token": examples.TOKEN, "h0": h0(examples.SESSION_ID, jti).hex(), "messages": entries,
            "attest": {"t": "attest", "video_seq": vseq, "audio_seq": aseq, "chain": chain.hex},
        })
    return cases


def write_chain_vectors(root: Path) -> None:
    for case in chain_cases():
        _dump(root / "vectors" / "chain" / (case["name"] + ".json"), case)


def write_transcripts(root: Path) -> None:
    d = root / "vectors" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    for name, builder in examples.TRANSCRIPTS.items():
        lines = examples.finish(builder())
        (d / (name + ".jsonl")).write_text("".join(json.dumps(line, sort_keys=False) + "\n" for line in lines), encoding="ascii")


STREAMS_README = """# Golden media streams

Placeholder. `streams/` will hold real captures at every ladder rung from the reference devices (Tecno,
Infinix, itel, Samsung A-series, Pixel, iPhone SE 2, iPhone 12, iPhone 15) and from Chrome, Samsung
Internet and Safari, each with an `expected.json` of decode statistics (frame count, IDR positions and
sizes, SPS/PPS fields, frame-interval distribution). They are produced by the phase 0 measurement
programme (`zakadi/spec/09-data-and-mlops.md` section 9.11), not synthesised, because their purpose is to
pin down real encoder behaviour. Until then, decoder tests use the framing vectors, whose payloads are
structurally Annex-B but not decodable video.
"""

VECTORS_README = """# Conformance vectors

All vectors are generated by `conformance/` (`uv run zakadi-conformance generate`) except the streams.

- `messages/<direction>/<type>/valid*.json` must validate against `schemas/v1/<direction>/<type>.schema.json`
  and against the direction aggregate; `invalid-*.json` must be rejected by the per-type schema.
- `framing/*.json` describe one binary media message each as hex with either the expected decoded header
  and payload (`expect`) or the expected error code (`error`); valid cases also ship as `*.bin`.
- `chain/*.json` give a session id, the jti (base64url) and an unsigned token carrying it, H0, every media
  message in send order with the chain value after it, and the resulting `attest` message.
- `sessions/*.jsonl` are control-channel transcripts: a meta line, then one line per message (`msg`),
  summarised media message (`media`) or socket close (`close`), with `t_ms` on the transcript clock.
  An SDK's fake-server harness replays the `s2c` lines and expects the `c2s` lines; the edge's client
  simulator does the reverse.
- `streams/` is a placeholder until phase 0 delivers real device captures.
"""


def generate(root: Path) -> None:
    write_schemas(root)
    write_message_vectors(root)
    write_framing_vectors(root)
    write_chain_vectors(root)
    write_transcripts(root)
    (root / "vectors" / "streams").mkdir(parents=True, exist_ok=True)
    (root / "vectors" / "streams" / "README.md").write_text(STREAMS_README, encoding="ascii")
    (root / "vectors" / "README.md").write_text(VECTORS_README, encoding="ascii")
