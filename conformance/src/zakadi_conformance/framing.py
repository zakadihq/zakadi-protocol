"""Binary media message framing (spec 01-protocol.md section 1.3).

Header, 8 bytes, little-endian multi-byte fields, bit 7 is the most significant bit:
  byte 0: ver (bits 7-6, must be 0) | type (bits 5-4) | keyframe (3) | param_sets (2) | rung_changed (1) | reserved (0)
  byte 1: rung (bits 7-4) | reserved (bits 3-0, must be 0)
  bytes 2-3: seq, uint16, per type
  bytes 4-7: pts_ms, uint32
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

HEADER_LEN = 8
TYPE_VIDEO = 0
TYPE_AUDIO = 1
TYPE_PROBE = 2
TYPE_AUDIO_BATCH = 3
CHAINED_TYPES = (TYPE_VIDEO, TYPE_AUDIO, TYPE_AUDIO_BATCH)
SEQ_MAX = 0xFFFF
PTS_MAX = 0xFFFFFFFF


class FramingError(ValueError):
    """A header or payload that violates the framing rules; `code` is stable and machine-readable."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True)
class Header:
    type: int
    seq: int
    pts_ms: int
    rung: int = 0
    keyframe: bool = False
    param_sets: bool = False
    rung_changed: bool = False
    ver: int = 0

    def as_dict(self) -> dict:
        return {
            "ver": self.ver,
            "type": self.type,
            "keyframe": self.keyframe,
            "param_sets": self.param_sets,
            "rung_changed": self.rung_changed,
            "rung": self.rung,
            "seq": self.seq,
            "pts_ms": self.pts_ms,
        }


def encode_header(h: Header) -> bytes:
    if h.ver != 0:
        raise FramingError("unsupported_version", "only framing version 0 exists")
    if not 0 <= h.type <= 3:
        raise FramingError("bad_type")
    if not 0 <= h.rung <= 15:
        raise FramingError("bad_rung")
    if not 0 <= h.seq <= SEQ_MAX:
        raise FramingError("bad_seq")
    if not 0 <= h.pts_ms <= PTS_MAX:
        raise FramingError("bad_pts")
    b0 = (h.ver << 6) | (h.type << 4) | (int(h.keyframe) << 3) | (int(h.param_sets) << 2) | (int(h.rung_changed) << 1)
    b1 = h.rung << 4
    return bytes([b0, b1]) + struct.pack("<HI", h.seq, h.pts_ms)


def decode_header(data: bytes) -> Header:
    if len(data) < HEADER_LEN:
        raise FramingError("short_header", "fewer than 8 bytes")
    b0, b1 = data[0], data[1]
    ver = b0 >> 6
    if ver != 0:
        raise FramingError("unsupported_version", "framing version %d" % ver)
    if b0 & 0x01:
        raise FramingError("reserved_bit_set", "byte 0 bit 0 must be 0")
    if b1 & 0x0F:
        raise FramingError("reserved_bits_set", "byte 1 bits 3-0 must be 0")
    seq, pts_ms = struct.unpack("<HI", data[2:8])
    return Header(
        ver=0,
        type=(b0 >> 4) & 0x03,
        keyframe=bool(b0 & 0x08),
        param_sets=bool(b0 & 0x04),
        rung_changed=bool(b0 & 0x02),
        rung=b1 >> 4,
        seq=seq,
        pts_ms=pts_ms,
    )


def encode_message(h: Header, payload: bytes) -> bytes:
    return encode_header(h) + payload


def next_seq(seq: int) -> int:
    return (seq + 1) & SEQ_MAX


def parse_probe_payload(payload: bytes) -> int:
    """Returns the client monotonic send time in microseconds (uint64 little-endian)."""
    if len(payload) < 8:
        raise FramingError("short_probe", "probe payload needs at least 8 bytes")
    return struct.unpack("<Q", payload[:8])[0]


def parse_audio_batch(payload: bytes) -> list[tuple[int, bytes]]:
    """Returns (pts_delta_ms, packet) records; records must be ordered by pts_delta_ms."""
    records: list[tuple[int, bytes]] = []
    pos = 0
    last = -1
    while pos < len(payload):
        if len(payload) - pos < 4:
            raise FramingError("truncated_batch_record", "record header needs 4 bytes")
        length, delta = struct.unpack("<HH", payload[pos:pos + 4])
        pos += 4
        if len(payload) - pos < length:
            raise FramingError("truncated_batch_record", "packet shorter than its declared length")
        if delta < last:
            raise FramingError("batch_out_of_order", "pts_delta_ms must not decrease")
        records.append((delta, payload[pos:pos + length]))
        pos += length
        last = delta
    if not records:
        raise FramingError("empty_batch")
    return records


def build_audio_batch(records: list[tuple[int, bytes]]) -> bytes:
    out = bytearray()
    for delta, packet in records:
        out += struct.pack("<HH", len(packet), delta) + packet
    return bytes(out)
