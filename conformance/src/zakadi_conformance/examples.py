"""Valid example messages (one per type, taken from the specification) and the session transcripts.

Transcripts are hand-authored, schema-valid recordings of the control channel in both directions, used by
the SDKs' fake-server harness and by the edge's client simulator. Media is summarised, not carried.

Every vector belongs to one session: `SESSION_ID`, `JTI` and `NONCE`, carried by `TOKEN`, an ES256 JWS
signed with the published test key (spec 02-api.md 2.2, D83, D89), so an edge that verifies tokens
replays the vectors unmodified.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections import deque
from typing import Any, cast

from . import jws
from .chain import Chain, b64_decode, b64url_decode, b64url_encode, summary_message

# `ses_` and a ULID (26 Crockford base32 characters) whose time part is ISSUED_AT in ms.
SESSION_ID = "ses_01K5RMQ2G0VECT0R0000000001"
JTI = "AAECAwQFBgcICQoLDA0ODw"  # base64url of bytes 0x00..0x0f
NONCE = "8J0wYw6NMQxRk4b3wvkAgA"  # base64url of 16 fixed bytes
ISSUED_AT = 1758542400  # 2025-09-22T12:00:00Z
TOKEN_TTL_S = 300  # exp is iat + 300 s (spec 02-api.md 2.2)
CLAIMS = {
    "iss": "api.zakadi.dev",
    "aud": "ingest",
    "sub": SESSION_ID,
    "tid": "tenant",
    "jti": JTI,
    "iat": ISSUED_AT,
    "nbf": ISSUED_AT,
    "exp": ISSUED_AT + TOKEN_TTL_S,
    "pol": 12,
    "band_max": "B",
    "ing": ["eu-west-2"],
    "nonce": NONCE,
    "lang": "en-NG",
}
TOKEN = jws.sign(CLAIMS)

# spec 01-protocol.md 1.4: lowercase hex SHA-256 over the session id's UTF-8 bytes followed by the 16 raw
# bytes of ready.attest_nonce; an App Attest token's client_data_hash repeats it.
REQUEST_HASH = hashlib.sha256(
    SESSION_ID.encode("utf-8") + b64_decode(NONCE)
).hexdigest()
APP_ATTEST_TOKEN = b64url_encode(
    json.dumps(
        {
            "key_id": base64.b64encode(b"vectors-app-attest-key-id-000001").decode(
                "ascii"
            ),
            "assertion": b64url_encode(b"not a real App Attest assertion"),
            "client_data_hash": REQUEST_HASH,
        },
        separators=(",", ":"),
    ).encode("ascii")
)

LADDER = [
    {"rung": 0, "w": 480, "h": 640, "fps": 20, "video_kbps": 900, "audio_kbps": 24},
    {"rung": 1, "w": 480, "h": 640, "fps": 20, "video_kbps": 600, "audio_kbps": 24},
    {"rung": 2, "w": 480, "h": 640, "fps": 15, "video_kbps": 400, "audio_kbps": 24},
    {"rung": 3, "w": 336, "h": 448, "fps": 12, "video_kbps": 250, "audio_kbps": 16},
    {"rung": 4, "w": 288, "h": 384, "fps": 10, "video_kbps": 150, "audio_kbps": 12},
]

HELLO = {
    "t": "hello",
    "v": 1,
    "token": TOKEN,
    "sdk": {
        "platform": "web",
        "name": "@zakadi/web-core",
        "version": "1.4.2",
        "os": "Android 13",
        "device": "TECNO KI5q",
        "browser": "Chrome 128",
        "wrapper": {"name": "@zakadi/react", "version": "1.0.3"},
    },
    "caps": {
        "profile": "webcodecs",
        "video": ["avc1.42E01F", "vp8"],
        "audio": ["opus", "aac"],
        "hw_encode": True,
        "keyframe_on_demand": True,
        "bitrate_reconfig": True,
        "max_resolution": {"w": 720, "h": 1280},
        "max_fps": 30,
        "attestation": "none",
    },
    "prompt_pack": {"lang": "en-NG", "version": "2026.09.1"},
    "a11y": {
        "screen_reader": False,
        "captions": True,
        "reduced_motion": False,
        "extended_time": False,
    },
    "consent": {"biometric": True, "recording": True, "at_ms_wall": 1758542400000},
}

CONFIG = {
    "t": "config",
    "video": {
        "codec": "avc1.42E01F",
        "w": 480,
        "h": 640,
        "fps": 15,
        "bitrate_kbps": 400,
        "annexb": True,
        "container": None,
        "mirrored": False,
        "rotation": 0,
        "gop_ms": 2000,
    },
    "audio": {
        "codec": "opus",
        "sample_rate": 16000,
        "channels": 1,
        "bitrate_kbps": 24,
        "frame_ms": 20,
        "muxed_in_video": False,
        "echo_cancellation": False,
        "noise_suppression": False,
        "auto_gain": False,
    },
    "rung": 2,
    "clock_source": "shared",
}


def config_at(rung: int) -> dict:
    c: dict[str, Any] = {
        k: (dict(v) if isinstance(v, dict) else v) for k, v in CONFIG.items()
    }
    entry = LADDER[rung]
    c["video"].update(
        {
            "w": entry["w"],
            "h": entry["h"],
            "fps": entry["fps"],
            "bitrate_kbps": entry["video_kbps"],
        }
    )
    c["audio"]["bitrate_kbps"] = entry["audio_kbps"]
    c["rung"] = rung
    return c


CAMERA_META = {
    "t": "camera_meta",
    "source": "getUserMedia",
    "devices": [
        {
            "kind": "videoinput",
            "label": "camera2 1, facing front",
            "device_id_hash": "5f1b2c9e0d4a7b6c8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d",
            "group_id_hash": "0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d",
        }
    ],
    "capabilities": {
        "width": {"min": 1, "max": 1280},
        "height": {"min": 1, "max": 720},
        "frameRate": {"min": 1, "max": 30},
    },
    "settings": {"width": 640, "height": 480, "frameRate": 30, "facingMode": "user"},
    "encoder": {
        "impl": "hardware",
        "is_config_supported": {"avc1.42E01F": True, "vp8": True},
    },
    "probe": [
        {
            "request": {"height": 3001},
            "reported": {"w": 1280, "h": 720},
            "observed": {"w": 1280, "h": 720, "fps": 29.6},
            "reconfig_ms": 143,
            "method": "rvfc",
        },
        {
            "request": {"height": 11},
            "reported": {"w": 160, "h": 120},
            "observed": {"w": 160, "h": 120, "fps": 30.1},
            "reconfig_ms": 121,
            "method": "rvfc",
        },
        {
            "request": {"height": 640},
            "reported": {"w": 480, "h": 640},
            "observed": {"w": 480, "h": 640, "fps": 29.8},
            "reconfig_ms": 98,
            "method": "rvfc",
        },
        {
            "request": {"height": 240},
            "reported": {"w": 320, "h": 240},
            "observed": {"w": 320, "h": 240, "fps": 30.0},
            "reconfig_ms": 95,
            "method": "rvfc",
        },
        {
            "request": {"height": 2001},
            "reported": {"w": 1280, "h": 720},
            "observed": {"w": 1280, "h": 720, "fps": 29.9},
            "reconfig_ms": 140,
            "method": "rvfc",
        },
        {
            "request": {"height": 22},
            "reported": {"w": 160, "h": 120},
            "observed": {"w": 160, "h": 120, "fps": 30.0},
            "reconfig_ms": 118,
            "method": "rvfc",
        },
        {
            "request": {"height": 1001},
            "reported": {"w": 1280, "h": 720},
            "observed": {"w": 1280, "h": 720, "fps": 29.7},
            "reconfig_ms": 139,
            "method": "rvfc",
        },
        {
            "request": {"fps": 200},
            "reported": {"w": 640, "h": 480, "fps": 30},
            "observed": {"w": 640, "h": 480, "fps": 30.0},
            "reconfig_ms": 88,
            "method": "rvfc",
        },
        {
            "request": {"fps": 1},
            "reported": {"w": 640, "h": 480, "fps": 1},
            "observed": {"w": 640, "h": 480, "fps": 1.0},
            "reconfig_ms": 402,
            "method": "rvfc",
        },
        {
            "request": {"fps": 60},
            "reported": {"w": 640, "h": 480, "fps": 30},
            "observed": {"w": 640, "h": 480, "fps": 29.9},
            "reconfig_ms": 90,
            "method": "rvfc",
        },
        {"request": {"fps": 120}, "skipped": True},
        {"request": {"fps": 5}, "skipped": True},
        {"request": {"fps": 30}, "skipped": True},
    ],
}

READY = {
    "t": "ready",
    "session_id": SESSION_ID,
    "server_ms": 0,
    "ladder": LADDER,
    "start_rung": 2,
    "probe": {"count": 8, "bytes": 8192, "window_ms": 1500},
    "gop_ms": 2000,
    "stats_interval_ms": 500,
    "attest_interval_ms": 1000,
    "attest_nonce": NONCE,
    "max_media_ms": 60000,
    "ping_interval_ms": 10000,
    "features": {"nonce_tile": True, "keyframe_requests": True},
}

UI_ACTION = {
    "t": "ui",
    "state": {
        "phase": "action",
        "self_view": {"oval": True, "oval_emphasis": "normal", "fill": "none"},
        "arc": {"visible": True, "direction": "user_left", "progress": 0.0},
        "character": {"anim": "demo_head_turn_left"},
        "caption": {
            "text": "Turn your head slowly, like this.",
            "pictogram": "head_turn_left",
        },
        "digits": {"visible": False, "values": []},
        "surround": {"brightness": 0.9, "flood": False},
        "badge": "automated",
        "progress": {"step": 1, "of": 2},
        "controls": {"repeat": True, "more_time": True, "cancel": True},
    },
}


def ui(phase: str, **changes) -> dict:
    """UI state message derived from UI_ACTION with a new phase and field overrides (idempotent full state)."""
    source = cast(dict[str, Any], UI_ACTION["state"])
    state: dict[str, Any] = {
        k: (dict(v) if isinstance(v, dict) else v) for k, v in source.items()
    }
    state["phase"] = phase
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(state.get(key), dict):
            state[key].update(value)
        else:
            state[key] = value
    return {"t": "ui", "state": state}


VALID_CLIENT: dict[str, dict] = {
    "hello": HELLO,
    "config": CONFIG,
    "probe_done": {
        "t": "probe_done",
        "sent": 8,
        "bytes": 65536,
        "first_send_us": 1200450,
        "last_send_us": 1201980,
    },
    "rung": {
        "t": "rung",
        "rung": 3,
        "reason": "backpressure",
        "from_video_seq": 1042,
        "from_audio_seq": 511,
    },
    "stats": {
        "t": "stats",
        "queued_bytes": 48213,
        "queue_ms": 210,
        "enc_queue": 1,
        "encoded_kbps": 410,
        "pre_encode_drops": 7,
        "captured_fps": 14.8,
        "rtt_ms": 205,
        "battery_low": False,
        "thermal": "nominal",
    },
    "camera_meta": CAMERA_META,
    "attestation": {
        "t": "attestation",
        "kind": "play_integrity",
        "token": "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMjU2R0NNIn0.opaque",
        "request_hash": REQUEST_HASH,
    },
    "audio_state": {"t": "audio_state", "re": "s17", "event": "started", "at_ms": 8420},
    "attest": {
        "t": "attest",
        "video_seq": 1200,
        "audio_seq": 600,
        "chain": "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b",
    },
    "ui_event": {
        "t": "ui_event",
        "event": "more_time_requested",
        "detail": {},
        "at_ms": 12040,
    },
    "pong": {"t": "pong", "re": "p17", "at_ms": 9110},
    "ping": {"t": "ping", "id": "c17", "at_ms": 9500},
    "bye": {
        "t": "bye",
        "reason": "user_cancel",
        "detail": "cancel pressed on the call screen",
    },
}

VALID_SERVER: dict[str, dict] = {
    "ready": READY,
    "probe_result": {
        "t": "probe_result",
        "goodput_kbps": 640,
        "rtt_ms": 190,
        "start_rung": 2,
    },
    "ui": UI_ACTION,
    "say": {
        "t": "say",
        "id": "s17",
        "cue": "digits.say",
        "params": {"digits": [4, 7, 2]},
        "interrupt": False,
        "caption": "Say these numbers out loud: four, seven, two.",
    },
    "action": {
        "t": "action",
        "id": "a1",
        "kind": "head_turn",
        "params": {"direction": "user_left", "min_deg": 18, "hold_ms": 250},
        "deadline_ms": 7000,
        "keyframe": True,
        "say": "s17",
    },
    "tile": {"t": "tile", "symbol": 5, "min_ms": 400},
    "keyframe": {
        "t": "keyframe",
        "id": "k3",
        "reason": "apex",
        "boost_kbps": 1200,
        "boost_ms": 600,
    },
    "set_rung": {"t": "set_rung", "rung": 1, "reason": "headroom"},
    "feedback": {"t": "feedback", "code": "too_dark", "severity": "hint"},
    "ping": {
        "t": "ping",
        "id": "p17",
        "server_ms": 9100,
        "rtt_ms": 190,
        "rx_kbps": 410,
    },
    "pong": {"t": "pong", "re": "c17", "server_ms": 9600},
    "end": {"t": "end", "outcome": "completed", "reason": "ok", "retry": False},
    "error": {"t": "error", "code": "admission", "detail": "retry_after=5"},
}

# Extra valid examples exercising alternative branches (one list per type).
EXTRA_VALID_CLIENT: dict[str, list[dict]] = {
    "config": [
        config_at(4)
        | {"video": config_at(4)["video"] | {"codec": "vp8", "annexb": False}},
        {
            "t": "config",
            "video": {
                "codec": "avc1.42E01E",
                "w": 480,
                "h": 640,
                "fps": 15,
                "bitrate_kbps": 400,
                "annexb": False,
                "container": "webm",
                "mirrored": False,
                "rotation": 0,
            },
            "audio": {
                "codec": "opus",
                "sample_rate": 48000,
                "channels": 1,
                "bitrate_kbps": 24,
                "muxed_in_video": True,
                "echo_cancellation": False,
            },
            "rung": 2,
        },
    ],
    "stats": [
        {
            "t": "stats",
            "queued_bytes": 0,
            "queue_ms": 0,
            "encoded_kbps": 0,
            "captured_fps": 0,
            "rtt_ms": None,
            "thermal": "critical",
        }
    ],
    "attestation": [
        {
            "t": "attestation",
            "kind": "app_attest",
            "token": APP_ATTEST_TOKEN,
            "request_hash": REQUEST_HASH,
        }
    ],
    "bye": [{"t": "bye", "reason": "floor_breached"}],
}
EXTRA_VALID_SERVER: dict[str, list[dict]] = {
    "action": [
        {
            "t": "action",
            "id": "a2",
            "kind": "fingers",
            "params": {"count": 3, "hand": "either", "placement": "beside_face"},
            "deadline_ms": 7000,
            "keyframe": True,
        },
        {
            "t": "action",
            "id": "a3",
            "kind": "digits",
            "params": {"values": [4, 7, 2, 9], "lang": "en-NG"},
            "deadline_ms": 8000,
        },
        {
            "t": "action",
            "id": "a4",
            "kind": "distance",
            "params": {"target": "closer", "scale_ratio": 1.4, "hold_ms": 300},
            "deadline_ms": 7000,
            "keyframe": True,
        },
        {
            "t": "action",
            "id": "a5",
            "kind": "blink",
            "params": {"count": 2, "window_ms": 3000},
            "deadline_ms": 5000,
        },
        {
            "t": "action",
            "id": "a6",
            "kind": "expression",
            "params": {"kind": "smile"},
            "deadline_ms": 5000,
        },
        {
            "t": "action",
            "id": "a7",
            "kind": "hand_over_face",
            "params": {"hand": "right", "region": "mouth", "hold_ms": 500},
            "deadline_ms": 7000,
        },
        {
            "t": "action",
            "id": "a8",
            "kind": "look_profile",
            "params": {"direction": "user_right", "min_deg": 50},
            "deadline_ms": 7000,
        },
    ],
    "ping": [
        {"t": "ping", "id": "p1", "server_ms": 130, "rtt_ms": None, "rx_kbps": None}
    ],
    "say": [
        {
            "t": "say",
            "id": "s3",
            "cue": "action.fingers.demo",
            "params": {"count": 3},
            "caption": "Show three fingers beside your face.",
        }
    ],
    "ui": [
        ui(
            "done",
            arc={"visible": False},
            character={"anim": "celebrate"},
            caption={"text": "All done. Thank you.", "pictogram": "done"},
            progress={"step": 2, "of": 2},
            controls={"repeat": False, "more_time": False, "cancel": False},
        )
    ],
    "end": [
        {"t": "end", "outcome": "aborted", "reason": "floor_breached", "retry": True}
    ],
    "error": [
        {"t": "error", "code": "protocol", "detail": "second message was not config"}
    ],
}

# Hand-authored invalid instances that the schemas must reject, beyond the mechanically derived ones.
INVALID_CLIENT: dict[str, list[tuple[str, dict]]] = {
    "hello": [
        (
            "consent-false",
            HELLO
            | {"consent": {"biometric": False, "recording": True, "at_ms_wall": 1}},
        ),
        ("no-video-codec", HELLO | {"caps": HELLO["caps"] | {"video": []}}),
    ],
    "config": [
        ("bad-rotation", CONFIG | {"video": CONFIG["video"] | {"rotation": 45}}),
        ("bad-codec-string", CONFIG | {"video": CONFIG["video"] | {"codec": "h264"}}),
    ],
    "attest": [
        (
            "uppercase-hex",
            VALID_CLIENT["attest"]
            | {
                "chain": "3A7BD3E2360A3D29EEA436FCFB7E44C735D117C42D1C1835420B6B9942DD4F1B"
            },
        )
    ],
    "rung": [("seq-too-large", VALID_CLIENT["rung"] | {"from_video_seq": 70000})],
}
INVALID_SERVER: dict[str, list[tuple[str, dict]]] = {
    "action": [
        (
            "head-turn-min-deg-out-of-range",
            VALID_SERVER["action"]
            | {"params": {"direction": "user_left", "min_deg": 40, "hold_ms": 250}},
        ),
        (
            "digits-three-values",
            {
                "t": "action",
                "id": "a3",
                "kind": "digits",
                "params": {"values": [4, 7, 2], "lang": "en-NG"},
                "deadline_ms": 8000,
            },
        ),
        (
            "fingers-count-six",
            {
                "t": "action",
                "id": "a2",
                "kind": "fingers",
                "params": {"count": 6, "hand": "left", "placement": "beside_face"},
                "deadline_ms": 7000,
            },
        ),
    ],
    "tile": [
        ("symbol-eight", {"t": "tile", "symbol": 8, "min_ms": 400}),
        ("min-ms-too-fast", {"t": "tile", "symbol": 1, "min_ms": 100}),
    ],
    "ready": [("empty-ladder", READY | {"ladder": []})],
    "ui": [
        (
            "progress-above-one",
            ui("action", arc={"visible": True, "direction": "up", "progress": 1.5}),
        )
    ],
}


MEDIA_T0 = 540  # t_ms of the first captured frame, where the session media clock starts (01 1.3.3)
FRAMING_START = 520  # t_ms of probe_result, where FRAMING begins (01 1.6)
# FRAMING's internal cap; a coaching turn follows, and 15 s later attempts_exhausted (01 1.6).
FRAMING_CAP_MS = 15000
RTT_MS = 190  # the round trip of every ping and pong exchange in the transcripts
CUE_DELAY_MS = 50  # from a say to its audio_state started on the transcript clock
SILENCE_MS = 1200  # the dialogue manager's silence watchdog (03 3.4)

# Captions and playback lengths of the cues the transcripts play (01 1.10: a cue lasts at most 4 s).
CUES: dict[str, tuple[str, int]] = {
    "greet.intro": ("Hi. Quick automated check, about twenty seconds.", 2400),
    "greet.short": ("Hi. Quick automated check.", 1800),
    "frame.arm_length": ("Hold your phone at arm's length.", 2000),
    "frame.center": ("Move to the centre of the oval.", 1800),
    "frame.eye_level": ("Hold the phone at eye level.", 1900),
    "frame.hold_still": ("Hold still for a moment.", 1500),
    "frame.perfect": ("Perfect.", 500),
    "light.front": ("Put the light in front of you.", 1600),
    "light.window": ("Face a window if you can.", 1700),
    "action.head_turn.demo": ("Turn your head slowly, like this.", 1650),
    "action.head_up.demo": ("Tilt your head up, like this.", 1600),
    "action.closer.demo": ("Come a little closer.", 1550),
    "action.fingers.demo": ("Show three fingers beside your face.", 1750),
    "digits.say": ("Say these numbers out loud.", 3150),
    "hold.moment": ("One moment.", 700),
    "hold.almost": ("Almost there.", 700),
    "ack.mmhm": ("Mm-hmm.", 300),
    "ack.nice": ("Nice.", 400),
    "ack.perfect": ("Perfect.", 500),
    "ack.got_it": ("Got it, thank you.", 900),
    "retry.once_more": ("Let's try that once more.", 1500),
    "retry.louder": ("Let's try that once more, a little louder.", 1800),
    "retry.quiet_place": ("Let's find a quieter place.", 1700),
    "fail.one_more_step": ("One more step.", 1500),
    "done.thanks": ("All done. Thank you.", 1200),
}
DIGIT_WORDS = "zero one two three four five six seven eight nine".split()


def _line(t_ms: int, direction: str, msg: dict) -> dict:
    return {"t_ms": t_ms, "dir": direction, "msg": msg}


def _media(
    t_ms: int, typ: int, seq: int, pts_ms: int, rung: int, nbytes: int, **flags
) -> dict:
    m = {"type": typ, "seq": seq, "pts_ms": pts_ms, "rung": rung, "bytes": nbytes}
    m.update(flags)
    return {"t_ms": t_ms, "dir": "c2s", "media": m}


def _close(t_ms: int, code: int, reason: str = "") -> dict:
    c = {"code": code}
    if reason:
        c["reason"] = reason
    return {"t_ms": t_ms, "dir": "s2c", "close": c}


def _meta(name: str, description: str, expect: dict) -> dict:
    return {
        "meta": {
            "name": name,
            "protocol": "zakadi.v1",
            "session_id": SESSION_ID,
            "jti": JTI,
            "description": description,
            "expect": expect,
        }
    }


def _at(t_ms: int) -> int:
    """at_ms on the session media clock for a client event at t_ms (0 before the first frame)."""
    return max(0, t_ms - MEDIA_T0)


def _ping(t_ms: int, n: int, rtt_ms: int | None, rx_kbps: int | None) -> dict:
    return _line(
        t_ms,
        "s2c",
        {
            "t": "ping",
            "id": "p%d" % n,
            "server_ms": t_ms,
            "rtt_ms": rtt_ms,
            "rx_kbps": rx_kbps,
        },
    )


def _pong(t_ms: int, n: int) -> dict:
    return _line(t_ms, "c2s", {"t": "pong", "re": "p%d" % n, "at_ms": _at(t_ms)})


def _stats(t_ms: int, encoded_kbps: int, **overrides) -> dict:
    msg = {
        "t": "stats",
        "queued_bytes": 3030,
        "queue_ms": 60,
        "enc_queue": 1,
        "encoded_kbps": encoded_kbps,
        "pre_encode_drops": 0,
        "captured_fps": 15.0,
        "rtt_ms": RTT_MS,
        "battery_low": False,
        "thermal": "nominal",
    }
    msg.update(overrides)
    return _line(t_ms, "c2s", msg)


def _digits_caption(values: list[int]) -> str:
    return "Say these numbers out loud: %s." % ", ".join(DIGIT_WORDS[v] for v in values)


class _Dialogue:
    """The says of one transcript, numbered s1, s2, ..., each bracketed by exactly one audio_state
    started and one ended (01 1.5)."""

    def __init__(self, lines: list) -> None:
        self.lines = lines
        self.count = 0
        self.sid = ""
        self.ended = 0

    def say(
        self,
        t_ms: int,
        cue: str,
        params: dict | None = None,
        caption: str | None = None,
        dur: int | None = None,
    ) -> str:
        default_caption, default_dur = CUES[cue]
        self.count += 1
        self.sid = "s%d" % self.count
        msg: dict[str, Any] = {"t": "say", "id": self.sid, "cue": cue}
        if params:
            msg["params"] = params
        msg["caption"] = caption or default_caption
        self.lines.append(_line(t_ms, "s2c", msg))
        started = t_ms + CUE_DELAY_MS
        self.ended = started + (dur or default_dur)
        for t, event in ((started, "started"), (self.ended, "ended")):
            self.lines.append(
                _line(
                    t,
                    "c2s",
                    {
                        "t": "audio_state",
                        "re": self.sid,
                        "event": event,
                        "at_ms": _at(t),
                    },
                )
            )
        return self.sid

    def then(self, cue: str, gap: int, **kwargs) -> int:
        """The next say, gap ms after the previous playback ended; returns its t_ms."""
        t_ms = self.ended + gap
        self.say(t_ms, cue, **kwargs)
        return t_ms


def _setup(lines: list, camera_meta: dict = CAMERA_META) -> int:
    """Common opening: hello, ready, ping p1 right after it, the probe burst (rung 0 and pts 0, as
    framing/probe.json), probe_done, the pong, probe_result, config, camera_meta. Returns the next t_ms."""
    lines.append(_line(0, "c2s", HELLO))
    lines.append(_line(120, "s2c", READY))
    lines.append(_ping(130, 1, None, None))
    t = 150
    for i in range(8):
        lines.append(_media(t, 2, i, 0, 0, 8192))
        t += 20
    lines.append(
        _line(
            t,
            "c2s",
            {
                "t": "probe_done",
                "sent": 8,
                "bytes": 65536,
                "first_send_us": 150000,
                "last_send_us": 290000,
            },
        )
    )
    lines.append(_pong(130 + RTT_MS, 1))
    lines.append(
        _line(
            FRAMING_START,
            "s2c",
            {
                "t": "probe_result",
                "goodput_kbps": 640,
                "rtt_ms": RTT_MS,
                "start_rung": 2,
            },
        )
    )
    lines.append(_line(530, "c2s", CONFIG))
    lines.append(_line(535, "c2s", camera_meta))
    return MEDIA_T0


def _stream(
    lines: list,
    t_from: int,
    t_to: int,
    seq_v: int,
    seq_a: int,
    rung: int = 2,
    fps: int = 15,
) -> tuple[int, int]:
    """Summarised video at fps (audio omitted); returns the next video and audio seq."""
    t = t_from
    step = 1000 // fps
    while t < t_to:
        lines.append(
            _media(
                t,
                0,
                seq_v,
                t - MEDIA_T0,
                rung,
                3300,
                keyframe=(seq_v % (2 * fps) == 0),
                param_sets=(seq_v % (2 * fps) == 0),
            )
        )
        seq_v += 1
        t += step
    return seq_v, seq_a


def _idr(t_ms: int, nbytes: int) -> dict:
    """The IDR a keyframe request brings, at rung 2 (15 fps) on a stream that began at MEDIA_T0."""
    pts = t_ms - MEDIA_T0
    return _media(
        t_ms, 0, pts * 15 // 1000, pts, 2, nbytes, keyframe=True, param_sets=True
    )


def _framing_ui(caption: str, pictogram: str, anim: str = "wave", **changes) -> dict:
    return ui(
        "framing",
        arc={"visible": False},
        character={"anim": anim},
        caption={"text": caption, "pictogram": pictogram},
        progress={"step": 0, "of": 2},
        **changes,
    )


def _action_ui(caption: str, pictogram: str, anim: str, step: int, **changes) -> dict:
    return ui(
        "action",
        character={"anim": anim},
        caption={"text": caption, "pictogram": pictogram},
        progress={"step": step, "of": 2},
        **changes,
    )


def _listening_ui(values: list[int], visible: bool, step: int = 2) -> dict:
    return ui(
        "listening",
        arc={"visible": False},
        character={"anim": "listen"},
        caption={"text": "Say these numbers out loud.", "pictogram": "speak"},
        digits={"visible": visible, "values": values if visible else []},
        progress={"step": step, "of": 2},
    )


def _done_ui() -> dict:
    return ui(
        "done",
        arc={"visible": False},
        character={"anim": "celebrate"},
        caption={"text": "All done. Thank you.", "pictogram": "done"},
        digits={"visible": False, "values": []},
        progress={"step": 2, "of": 2},
        controls={"repeat": False, "more_time": False, "cancel": False},
    )


def _holding_ui(caption: str, pictogram: str = "check") -> dict:
    return ui(
        "holding",
        arc={"visible": False},
        character={"anim": "nod"},
        caption={"text": caption, "pictogram": pictogram},
    )


PLACEHOLDER_CHAIN = "5e0b1c4a8d7f2e3a9c6b0d4e1f8a7c2b3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90"


def _attest(
    t_ms: int, video_seq: int, audio_seq: int, chain: str = PLACEHOLDER_CHAIN
) -> dict:
    return _line(
        t_ms,
        "c2s",
        {"t": "attest", "video_seq": video_seq, "audio_seq": audio_seq, "chain": chain},
    )


def _attest_at(t_ms: int) -> dict:
    """An attest in a transcript whose media is sampled: the seqs of rung 2's 15 fps video and 50
    audio packets per second at t_ms, and a placeholder chain."""
    return _attest(t_ms, (t_ms - MEDIA_T0) * 15 // 1000, (t_ms - MEDIA_T0) // 20)


def transcript_happy() -> list[dict]:
    lines = [
        _meta(
            "happy-two-actions",
            "Complete session: framing, a head turn and a finger count, then a clean end.",
            {
                "end": {"outcome": "completed", "reason": "ok"},
                "close": 1000,
                "actions": ["head_turn", "fingers"],
            },
        )
    ]
    _setup(lines)
    d = _Dialogue(lines)
    lines.append(_line(560, "s2c", _framing_ui(CUES["greet.intro"][0], "wave")))
    d.say(562, "greet.intro")
    sv, sa = _stream(lines, MEDIA_T0, 1000, 0, 0)
    lines.append(_ping(1000, 2, RTT_MS, 405))
    lines.append(_pong(1000 + RTT_MS, 2))
    lines.append(_stats(1040, 420, queued_bytes=12000, queue_ms=120))
    sv, sa = _stream(lines, 1000, 1560, sv, sa)
    lines.append(
        _attest(
            1540,
            sv - 1,
            49,
            "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b",
        )
    )
    d.say(3100, "frame.arm_length")
    lines.append(
        _line(5300, "s2c", {"t": "feedback", "code": "too_dark", "severity": "hint"})
    )
    lines.append(
        _line(
            5300,
            "s2c",
            _framing_ui(
                CUES["light.front"][0],
                "light_front",
                anim="listen",
                surround={"brightness": 1.0, "flood": True},
            ),
        )
    )
    d.say(5302, "light.front")
    d.say(7400, "frame.perfect")
    # action 1: head turn
    s = d.say(8000, "action.head_turn.demo")
    lines.append(_line(8000, "s2c", UI_ACTION))
    lines.append(_line(8010, "s2c", {"t": "tile", "symbol": 5, "min_ms": 400}))
    lines.append(
        _line(
            8012,
            "s2c",
            {
                "t": "action",
                "id": "a1",
                "kind": "head_turn",
                "params": {"direction": "user_left", "min_deg": 18, "hold_ms": 250},
                "deadline_ms": 7000,
                "keyframe": True,
                "say": s,
            },
        )
    )
    lines.append(_line(8450, "s2c", {"t": "tile", "symbol": 2, "min_ms": 400}))
    lines.append(_line(8900, "s2c", {"t": "tile", "symbol": 7, "min_ms": 400}))
    lines.append(
        _line(
            9600,
            "s2c",
            {
                "t": "keyframe",
                "id": "k1",
                "reason": "apex",
                "boost_kbps": 1200,
                "boost_ms": 600,
            },
        )
    )
    lines.append(_media(9660, 0, 137, 9120, 2, 21000, keyframe=True, param_sets=True))
    d.say(10400, "ack.nice")
    lines.append(_line(10400, "s2c", _holding_ui("Nice.")))
    # action 2: fingers
    s = d.say(11500, "action.fingers.demo", params={"count": 3})
    lines.append(
        _line(
            11500,
            "s2c",
            _action_ui(
                CUES["action.fingers.demo"][0],
                "fingers_3",
                "demo_fingers_3",
                2,
                arc={"visible": False},
            ),
        )
    )
    lines.append(_line(11510, "s2c", {"t": "tile", "symbol": 1, "min_ms": 400}))
    lines.append(
        _line(
            11512,
            "s2c",
            {
                "t": "action",
                "id": "a2",
                "kind": "fingers",
                "params": {"count": 3, "hand": "either", "placement": "beside_face"},
                "deadline_ms": 7000,
                "keyframe": True,
                "say": s,
            },
        )
    )
    lines.append(_line(11950, "s2c", {"t": "tile", "symbol": 6, "min_ms": 400}))
    lines.append(
        _line(
            14000,
            "s2c",
            {
                "t": "keyframe",
                "id": "k2",
                "reason": "apex",
                "boost_kbps": 1200,
                "boost_ms": 600,
            },
        )
    )
    lines.append(_media(14070, 0, 203, 13530, 2, 20400, keyframe=True, param_sets=True))
    d.say(14300, "ack.got_it")
    lines.append(_line(15900, "s2c", _done_ui()))
    d.say(15902, "done.thanks")
    lines.append(_attest_at(17500))
    lines.append(
        _line(
            17600,
            "s2c",
            {"t": "end", "outcome": "completed", "reason": "ok", "retry": False},
        )
    )
    lines.append(_close(17650, 1000))
    return lines


def transcript_digits_retry() -> list[dict]:
    lines = [
        _meta(
            "digits-retry",
            "A spoken-digits challenge fails once (misheard) and is retried with new values, then passes.",
            {
                "end": {"outcome": "completed", "reason": "ok"},
                "close": 1000,
                "actions": ["distance", "digits", "digits"],
            },
        )
    ]
    _setup(lines)
    d = _Dialogue(lines)
    lines.append(_line(560, "s2c", _framing_ui("Hi.", "wave")))
    d.say(562, "greet.short")
    d.then("frame.arm_length", 188)
    d.then("frame.perfect", 250)
    # action 1: distance
    s = d.say(6000, "action.closer.demo")
    lines.append(
        _line(
            6000,
            "s2c",
            _action_ui(
                CUES["action.closer.demo"][0],
                "closer",
                "demo_closer",
                1,
                arc={"visible": True, "direction": "closer", "progress": 0.0},
            ),
        )
    )
    lines.append(_line(6010, "s2c", {"t": "tile", "symbol": 3, "min_ms": 400}))
    lines.append(
        _line(
            6012,
            "s2c",
            {
                "t": "action",
                "id": "a1",
                "kind": "distance",
                "params": {"target": "closer", "scale_ratio": 1.4, "hold_ms": 300},
                "deadline_ms": 7000,
                "keyframe": True,
                "say": s,
            },
        )
    )
    d.say(8600, "ack.perfect")
    # action 2: digits, misheard
    values = [4, 7, 2, 9]
    s = d.say(
        10000, "digits.say", params={"digits": values}, caption=_digits_caption(values)
    )
    lines.append(_line(10000, "s2c", _listening_ui(values, False)))
    lines.append(_line(10010, "s2c", {"t": "tile", "symbol": 0, "min_ms": 400}))
    lines.append(
        _line(
            10012,
            "s2c",
            {
                "t": "action",
                "id": "a2",
                "kind": "digits",
                "params": {"values": values, "lang": "en-NG"},
                "deadline_ms": 8000,
                "say": s,
            },
        )
    )
    lines.append(_line(d.ended, "s2c", _listening_ui(values, True)))
    d.then("ack.mmhm", 1100)
    t = d.ended + 1150
    lines.append(
        _line(t, "s2c", {"t": "feedback", "code": "noisy_audio", "severity": "hint"})
    )
    d.say(t, "retry.louder")
    # action 3: digits again, new values
    values = [9, 1, 3, 8]
    t = d.then(
        "digits.say",
        150,
        params={"digits": values},
        caption=_digits_caption(values),
        dur=3100,
    )
    lines.append(_line(t, "s2c", _listening_ui(values, False)))
    lines.append(_line(t + 10, "s2c", {"t": "tile", "symbol": 4, "min_ms": 400}))
    lines.append(
        _line(
            t + 12,
            "s2c",
            {
                "t": "action",
                "id": "a3",
                "kind": "digits",
                "params": {"values": values, "lang": "en-NG"},
                "deadline_ms": 8000,
                "say": d.sid,
            },
        )
    )
    lines.append(_line(d.ended, "s2c", _listening_ui(values, True)))
    d.then("ack.mmhm", 1150)
    d.then("ack.got_it", 1050)
    t = d.ended + 550
    lines.append(_line(t, "s2c", _done_ui()))
    d.say(t + 2, "done.thanks")
    lines.append(_attest_at(d.ended + 250))
    lines.append(
        _line(
            d.ended + 350,
            "s2c",
            {"t": "end", "outcome": "completed", "reason": "ok", "retry": False},
        )
    )
    lines.append(_close(d.ended + 400, 1000))
    return lines


def transcript_floor_breached() -> list[dict]:
    lines = [
        _meta(
            "floor-breached",
            "The uplink collapses; the client steps down to rung 4, cannot sustain it for 3 s, and ends with bye floor_breached.",
            {
                "end": {"outcome": "aborted", "reason": "floor_breached"},
                "close": 1000,
                "rungs": [2, 3, 4],
            },
        )
    ]
    _setup(lines)
    d = _Dialogue(lines)
    lines.append(_line(560, "s2c", _framing_ui("Hi.", "wave")))
    d.say(562, "greet.short")
    lines.append(_stats(1040, 420, queued_bytes=60000, queue_ms=700, enc_queue=2))
    lines.append(
        _line(
            1440,
            "c2s",
            {
                "t": "rung",
                "rung": 3,
                "reason": "backpressure",
                "from_video_seq": 14,
                "from_audio_seq": 45,
            },
        )
    )
    lines.append(_line(1445, "c2s", config_at(3)))
    lines.append(
        _media(
            1460, 0, 14, 920, 3, 2100, rung_changed=True, keyframe=True, param_sets=True
        )
    )
    lines.append(
        _stats(
            2540,
            265,
            queued_bytes=140000,
            queue_ms=1700,
            enc_queue=3,
            pre_encode_drops=6,
            captured_fps=12.0,
            rtt_ms=410,
        )
    )
    lines.append(
        _line(
            2545,
            "c2s",
            {
                "t": "rung",
                "rung": 4,
                "reason": "backpressure",
                "from_video_seq": 27,
                "from_audio_seq": 100,
            },
        )
    )
    lines.append(_line(2550, "c2s", config_at(4)))
    lines.append(
        _media(
            2560,
            0,
            27,
            2020,
            4,
            1500,
            rung_changed=True,
            keyframe=True,
            param_sets=True,
        )
    )
    d.say(2600, "frame.arm_length")
    d.then("hold.moment", 150)
    for t in (3040, 3540, 4040, 4540, 5040, 5540):
        lines.append(
            _stats(
                t,
                160,
                queued_bytes=200000,
                queue_ms=2400,
                enc_queue=4,
                pre_encode_drops=20,
                captured_fps=10.0,
                rtt_ms=900,
            )
        )
    lines.append(_attest(5600, 52, 250))
    lines.append(
        _line(
            5610,
            "c2s",
            {
                "t": "bye",
                "reason": "floor_breached",
                "detail": "rung 4 queue above 1500 ms for 3 s",
            },
        )
    )
    lines.append(
        _line(
            5700,
            "s2c",
            {
                "t": "end",
                "outcome": "aborted",
                "reason": "floor_breached",
                "retry": True,
            },
        )
    )
    lines.append(_close(5720, 1000))
    return lines


def transcript_admission_rejected() -> list[dict]:
    lines = [
        _meta(
            "admission-rejected",
            "The pod is at capacity: error admission then close 4008 with the retry delay in the reason.",
            {"close": 4008, "error": "admission"},
        )
    ]
    lines.append(_line(0, "c2s", HELLO))
    lines.append(
        _line(90, "s2c", {"t": "error", "code": "admission", "detail": "retry_after=5"})
    )
    lines.append(_close(95, 4008, "retry_after=5"))
    return lines


def transcript_user_cancel() -> list[dict]:
    lines = [
        _meta(
            "user-cancel",
            "The user presses cancel during the first action; end aborted user_cancel, close 4010.",
            {"end": {"outcome": "aborted", "reason": "user_cancel"}, "close": 4010},
        )
    ]
    _setup(lines)
    d = _Dialogue(lines)
    lines.append(_line(560, "s2c", _framing_ui("Hi.", "wave")))
    d.say(562, "greet.short")
    d.then("frame.arm_length", 188)
    d.then("frame.perfect", 250)
    s = d.say(6000, "action.head_turn.demo")
    lines.append(
        _line(
            6000,
            "s2c",
            _action_ui(
                CUES["action.head_turn.demo"][0],
                "head_turn_right",
                "demo_head_turn_right",
                1,
                arc={"visible": True, "direction": "user_right", "progress": 0.0},
            ),
        )
    )
    lines.append(_line(6010, "s2c", {"t": "tile", "symbol": 5, "min_ms": 400}))
    lines.append(
        _line(
            6012,
            "s2c",
            {
                "t": "action",
                "id": "a1",
                "kind": "head_turn",
                "params": {"direction": "user_right", "min_deg": 20, "hold_ms": 250},
                "deadline_ms": 7000,
                "keyframe": True,
                "say": s,
            },
        )
    )
    t = d.ended + 400
    lines.append(
        _line(
            t,
            "c2s",
            {"t": "ui_event", "event": "cancel_pressed", "detail": {}, "at_ms": _at(t)},
        )
    )
    lines.append(_attest_at(t + 5))
    lines.append(_line(t + 10, "c2s", {"t": "bye", "reason": "user_cancel"}))
    lines.append(
        _line(
            t + 100,
            "s2c",
            {"t": "end", "outcome": "aborted", "reason": "user_cancel", "retry": False},
        )
    )
    lines.append(_close(t + 120, 4010))
    return lines


def _challenge(
    lines: list,
    d: _Dialogue,
    t_ms: int,
    action_id: str,
    kind: str,
    params: dict,
    cue: str,
    view: dict,
    symbol: int,
    say_params: dict | None = None,
    caption: str | None = None,
    deadline_ms: int = 7000,
) -> int:
    """One challenge attempt as 01 1.6 orders it: the demo say, the ui, the tile change (the in-band
    zero point), then the action. Returns the action's deadline on the transcript clock."""
    s = d.say(t_ms, cue, params=say_params, caption=caption)
    lines.append(_line(t_ms, "s2c", view))
    lines.append(
        _line(t_ms + 10, "s2c", {"t": "tile", "symbol": symbol, "min_ms": 400})
    )
    msg: dict[str, Any] = {
        "t": "action",
        "id": action_id,
        "kind": kind,
        "params": params,
        "deadline_ms": deadline_ms,
    }
    if kind != "digits":
        msg["keyframe"] = True
    msg["say"] = s
    lines.append(_line(t_ms + 12, "s2c", msg))
    return t_ms + 12 + deadline_ms


def _hold_until(d: _Dialogue, t_next: int, cues: list[str]) -> None:
    """Holding cues while the silence before the say at t_next would pass 1200 ms (03 3.4): each
    starts at most 1000 ms after the previous playback ended and ends 50 ms before t_next or earlier."""
    n = 0
    while t_next - d.ended > SILENCE_MS:
        cue = cues[n % len(cues)]
        n += 1
        room = t_next - d.ended - CUE_DELAY_MS - CUES[cue][1] - 50
        d.then(cue, max(100, min(1000, room)))


def transcript_max_duration() -> list[dict]:
    lines = [
        _meta(
            "max-duration",
            "Framing succeeds, then head turns, finger counts and spoken digits are retried until the media "
            "clock passes 60 s: end aborted max_duration, close 4009.",
            {"end": {"outcome": "aborted", "reason": "max_duration"}, "close": 4009},
        )
    ]
    _setup(lines)
    d = _Dialogue(lines)
    lines.append(_line(560, "s2c", _framing_ui("Hi.", "wave")))
    d.say(562, "greet.short")
    d.then("frame.arm_length", 188)
    d.then("frame.perfect", 250)
    fillers = ["hold.almost", "hold.almost", "hold.moment"]
    # head turn: the first attempt fails, the second (new direction) passes
    deadline = _challenge(
        lines,
        d,
        6000,
        "a1",
        "head_turn",
        {"direction": "user_left", "min_deg": 18, "hold_ms": 250},
        "action.head_turn.demo",
        UI_ACTION,
        5,
    )
    _hold_until(d, deadline + 88, fillers)
    d.say(deadline + 88, "retry.once_more")
    t = d.ended + 150
    _challenge(
        lines,
        d,
        t,
        "a2",
        "head_turn",
        {"direction": "up", "min_deg": 16, "hold_ms": 200},
        "action.head_up.demo",
        _action_ui(
            CUES["action.head_up.demo"][0],
            "head_up",
            "demo_head_up",
            1,
            arc={"visible": True, "direction": "up", "progress": 0.0},
        ),
        2,
    )
    apex = d.ended + 800
    lines.append(
        _line(
            apex,
            "s2c",
            {
                "t": "keyframe",
                "id": "k1",
                "reason": "apex",
                "boost_kbps": 1200,
                "boost_ms": 600,
            },
        )
    )
    lines.append(_idr(apex + 60, 21000))
    t = d.ended + 1000
    d.say(t, "ack.nice")
    lines.append(_line(t, "s2c", _holding_ui("Nice.")))
    # fingers: the first attempt fails, the second (the left hand) passes
    step_view = {"visible": False}
    t += 1500
    deadline = _challenge(
        lines,
        d,
        t,
        "a3",
        "fingers",
        {"count": 3, "hand": "either", "placement": "beside_face"},
        "action.fingers.demo",
        _action_ui(
            CUES["action.fingers.demo"][0],
            "fingers_3",
            "demo_fingers_3",
            2,
            arc=step_view,
        ),
        6,
        say_params={"count": 3},
    )
    _hold_until(d, deadline + 88, fillers)
    d.say(deadline + 88, "retry.once_more")
    t = d.ended + 150
    _challenge(
        lines,
        d,
        t,
        "a4",
        "fingers",
        {"count": 3, "hand": "left", "placement": "beside_face"},
        "action.fingers.demo",
        _action_ui(
            CUES["action.fingers.demo"][0],
            "fingers_3",
            "demo_fingers_3",
            2,
            arc=step_view,
        ),
        1,
        say_params={"count": 3},
    )
    apex = d.ended + 700
    lines.append(
        _line(
            apex,
            "s2c",
            {
                "t": "keyframe",
                "id": "k2",
                "reason": "apex",
                "boost_kbps": 1200,
                "boost_ms": 600,
            },
        )
    )
    lines.append(_idr(apex + 70, 20400))
    t = d.ended + 1000
    d.say(t, "ack.got_it")
    lines.append(_line(t, "s2c", _holding_ui("Got it, thank you.")))
    # spoken digits: three attempts are misheard
    t = d.ended + 1100
    for n, (values, symbol, retry_cue) in enumerate(
        (
            ([4, 7, 2, 9], 0, "retry.louder"),
            ([9, 1, 3, 8], 4, "retry.quiet_place"),
            ([5, 0, 6, 1], 3, "fail.one_more_step"),
        ),
        start=5,
    ):
        deadline = _challenge(
            lines,
            d,
            t,
            "a%d" % n,
            "digits",
            {"values": values, "lang": "en-NG"},
            "digits.say",
            _listening_ui(values, False),
            symbol,
            say_params={"digits": values},
            caption=_digits_caption(values),
            deadline_ms=8000,
        )
        lines.append(_line(d.ended, "s2c", _listening_ui(values, True)))
        # the answer is misheard 3.5 s after the prompt ended
        t = d.ended + 3500
        _hold_until(d, t, ["ack.mmhm", "hold.moment"])
        lines.append(
            _line(
                t, "s2c", {"t": "feedback", "code": "noisy_audio", "severity": "hint"}
            )
        )
        d.say(t, retry_cue)
        t = d.ended + 150
    # the media clock passes 60 s (01 1.1) while the server holds
    end = MEDIA_T0 + 60060
    _hold_until(d, end, ["hold.moment", "hold.almost"])
    lines.append(_media(end - 40, 0, 900, 60020, 2, 3300))
    lines.append(
        _line(
            end,
            "s2c",
            {"t": "end", "outcome": "aborted", "reason": "max_duration", "retry": True},
        )
    )
    lines.append(_close(end + 20, 4009))
    return lines


def transcript_protocol_error() -> list[dict]:
    lines = [
        _meta(
            "protocol-error",
            "The client sends media before config: error protocol then close 4006.",
            {"close": 4006, "error": "protocol"},
        )
    ]
    lines.append(_line(0, "c2s", HELLO))
    lines.append(_line(120, "s2c", READY))
    lines.append(_ping(130, 1, None, None))
    lines.append(_pong(150, 1))
    lines.append(_media(200, 0, 0, 0, 2, 3300, keyframe=True, param_sets=True))
    lines.append(
        _line(
            230,
            "s2c",
            {"t": "error", "code": "protocol", "detail": "media before config"},
        )
    )
    lines.append(_close(235, 4006, "protocol"))
    return lines


# Continuous media at rung 2 (480x640 at 15 fps, 400 kbps video, 20 ms Opus at 24 kbps): an IDR with
# its parameter sets every 2 s (gop_ms), P frames sized so that a GOP carries 400 kbps.
VIDEO_IDR_BYTES = 12000
VIDEO_P_BYTES = 3030
AUDIO_BYTES = 68  # 8-byte header and a 60-byte Opus packet: 24 kbps at 20 ms


def _continuous_media(lines: list, t_from: int, t_to: int, rung: int = 2) -> None:
    """Every video and audio message from t_from until before t_to, pts_ms on the session media clock."""
    fps = LADDER[rung]["fps"]
    gop = 2 * fps
    k = 0
    while t_from + k * 1000 // fps < t_to:
        pts = k * 1000 // fps
        key = k % gop == 0
        lines.append(
            _media(
                t_from + pts,
                0,
                k,
                pts,
                rung,
                VIDEO_IDR_BYTES if key else VIDEO_P_BYTES,
                keyframe=key,
                param_sets=key,
            )
        )
        k += 1
    j = 0
    while t_from + 20 * j < t_to:
        lines.append(_media(t_from + 20 * j, 1, j, 20 * j, rung, AUDIO_BYTES))
        j += 1


def _fill_continuous(lines: list[dict]) -> list[dict]:
    """Sorts a continuous transcript and computes what its media determines: each attest's seqs and
    chain (over the zero-filled messages of `summary_message`), each stats encoded_kbps and each ping
    rx_kbps (media bytes of the last 2 s, headers included, 01 1.1 and 1.4)."""
    lines = finish(lines)
    chain = Chain(SESSION_ID, b64url_decode(JTI))
    window: deque[tuple[int, int]] = deque()
    recent = 0
    last = {0: 0, 1: 0}
    for row in lines[1:]:
        t = row["t_ms"]
        media = row.get("media")
        if media is not None and media["type"] != 2:
            chain.feed(summary_message(media))
            last[0 if media["type"] == 0 else 1] = media["seq"]
            window.append((t, media["bytes"]))
            recent += media["bytes"]
        while window and t - window[0][0] >= 2000:
            recent -= window.popleft()[1]
        msg = row.get("msg", {})
        if msg.get("t") == "attest":
            msg.update({"video_seq": last[0], "audio_seq": last[1], "chain": chain.hex})
        elif msg.get("t") == "stats":
            msg["encoded_kbps"] = round(recent * 8 / 2000)
        elif msg.get("t") == "ping" and window:
            msg["rx_kbps"] = round(recent * 8 / 2000)
    return lines


def transcript_framing_timeout() -> list[dict]:
    """The no-face session (01 1.6, D90): FRAMING reaches its 15 s cap, one lighting coaching turn
    follows, and 15 s later the server ends with attempts_exhausted, while media streams throughout."""
    lines = [
        _meta(
            "framing-timeout",
            "No face is found: FRAMING reaches its 15 s cap, one lighting coaching turn follows, and 15 s later "
            "the server ends with attempts_exhausted, retry true, then close 1000. Media streams continuously: "
            "server pings every 1 s, stats every 500 ms and attest every 1000 ms of video pts, each attest "
            "chained over the summarised media with zero-filled payloads.",
            {
                "end": {
                    "outcome": "aborted",
                    "reason": "attempts_exhausted",
                    "retry": True,
                },
                "close": 1000,
                "media": "continuous",
            },
        )
    ]
    t0 = _setup(lines)
    cap = FRAMING_START + FRAMING_CAP_MS
    end = cap + FRAMING_CAP_MS
    _continuous_media(lines, t0, end)
    n = 2
    for t in range(t0 + 1010, end, 1000):
        lines.append(_ping(t, n, RTT_MS, 0))
        lines.append(_pong(t + RTT_MS, n))
        n += 1
    for t in range(t0 + 500, end, 500):
        lines.append(_stats(t, 0))
    for t in range(t0 + 1000, end, 1000):
        lines.append(_attest(t, 0, 0, ""))
    d = _Dialogue(lines)
    lines.append(_line(560, "s2c", _framing_ui(CUES["greet.intro"][0], "wave")))
    d.say(562, "greet.intro")
    d.say(3100, "frame.arm_length")
    lines.append(
        _line(5300, "s2c", {"t": "feedback", "code": "no_face", "severity": "hint"})
    )
    lines.append(
        _line(
            5300,
            "s2c",
            _framing_ui(
                CUES["frame.center"][0],
                "center",
                anim="listen",
                self_view={"oval": True, "oval_emphasis": "highlight", "fill": "none"},
            ),
        )
    )
    d.say(5300, "frame.center")
    for cue in (
        "frame.eye_level",
        "hold.moment",
        "frame.hold_still",
        "frame.center",
        "hold.moment",
    ):
        d.then(cue, 250)
    # the cap: one lighting coaching turn
    lines.append(
        _line(cap, "s2c", {"t": "feedback", "code": "no_face", "severity": "block"})
    )
    lines.append(
        _line(
            cap,
            "s2c",
            _framing_ui(
                CUES["light.front"][0],
                "light_front",
                anim="listen",
                surround={"brightness": 1.0, "flood": True},
            ),
        )
    )
    d.say(cap + 2, "light.front")
    for cue in (
        "frame.center",
        "hold.moment",
        "light.window",
        "frame.arm_length",
        "hold.moment",
        "frame.center",
        "light.front",
    ):
        d.then(cue, 250)
    d.then("hold.moment", 150)
    lines.append(
        _line(
            end,
            "s2c",
            {
                "t": "end",
                "outcome": "aborted",
                "reason": "attempts_exhausted",
                "retry": True,
            },
        )
    )
    lines.append(_attest(end + 5, 0, 0, ""))
    lines.append(_close(end + 20, 1000))
    return _fill_continuous(lines)


def finish(lines: list[dict]) -> list[dict]:
    """Stable-sorts the body by t_ms (builders append logically, not chronologically) and keeps the meta line first."""
    return [lines[0]] + sorted(lines[1:], key=lambda row: row["t_ms"])


TRANSCRIPTS = {
    "happy-two-actions": transcript_happy,
    "digits-retry": transcript_digits_retry,
    "floor-breached": transcript_floor_breached,
    "admission-rejected": transcript_admission_rejected,
    "user-cancel": transcript_user_cancel,
    "max-duration": transcript_max_duration,
    "protocol-error": transcript_protocol_error,
    "framing-timeout": transcript_framing_timeout,
}
