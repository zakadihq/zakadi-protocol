"""Valid example messages (one per type, taken from the specification) and the session transcripts.

Transcripts are hand-authored, schema-valid recordings of the control channel in both directions, used by
the SDKs' fake-server harness and by the edge's client simulator. Media is summarised, not carried.
"""

from __future__ import annotations

SESSION_ID = "ses_01J8VECTOR000000000001"
JTI = "AAECAwQFBgcICQoLDA0ODw"  # base64url of bytes 0x00..0x0f
NONCE = "8J0wYw6NMQxRk4b3wvkAgA"  # base64url of 16 fixed bytes
TOKEN = ("eyJhbGciOiJFUzI1NiIsImtpZCI6InRlc3QifQ."
         "eyJpc3MiOiJhcGkuemFrYWRpLmRldiIsImF1ZCI6ImluZ2VzdCIsInN1YiI6InNlc18wMUo4VkVDVE9SMDAwMDAwMDAwMDAxIiwidGlkIjoidGVuYW50IiwianRpIjoiQUFFQ0F3UUZCZ2NJQ1FvTERBME9EdyIsImlhdCI6MTc1ODU0MjQwMCwibmJmIjoxNzU4NTQyNDAwLCJleHAiOjE3NTg1NDI3MDAsInBvbCI6MTIsImJhbmRfbWF4IjoiQiIsImluZyI6WyJldS13ZXN0LTIiXSwibm9uY2UiOiI4SjB3WXc2Tk1ReFJrNGIzd3ZrQWdBIiwibGFuZyI6ImVuLU5HIn0."
         "dGVzdC1zaWduYXR1cmUtbm90LXZhbGlk")

LADDER = [
    {"rung": 0, "w": 480, "h": 640, "fps": 20, "video_kbps": 900, "audio_kbps": 24},
    {"rung": 1, "w": 480, "h": 640, "fps": 20, "video_kbps": 600, "audio_kbps": 24},
    {"rung": 2, "w": 480, "h": 640, "fps": 15, "video_kbps": 400, "audio_kbps": 24},
    {"rung": 3, "w": 336, "h": 448, "fps": 12, "video_kbps": 250, "audio_kbps": 16},
    {"rung": 4, "w": 288, "h": 384, "fps": 10, "video_kbps": 150, "audio_kbps": 12},
]

HELLO = {
    "t": "hello", "v": 1, "token": TOKEN,
    "sdk": {"platform": "web", "name": "@zakadi/web-core", "version": "1.4.2", "os": "Android 13", "device": "TECNO KI5q",
            "browser": "Chrome 128", "wrapper": {"name": "@zakadi/react", "version": "1.0.3"}},
    "caps": {"profile": "webcodecs", "video": ["avc1.42E01F", "vp8"], "audio": ["opus", "aac"], "hw_encode": True,
             "keyframe_on_demand": True, "bitrate_reconfig": True, "max_resolution": {"w": 720, "h": 1280}, "max_fps": 30,
             "attestation": "none"},
    "prompt_pack": {"lang": "en-NG", "version": "2026.09.1"},
    "a11y": {"screen_reader": False, "captions": True, "reduced_motion": False, "extended_time": False},
    "consent": {"biometric": True, "recording": True, "at_ms_wall": 1758542400000},
}

CONFIG = {
    "t": "config",
    "video": {"codec": "avc1.42E01F", "w": 480, "h": 640, "fps": 15, "bitrate_kbps": 400, "annexb": True, "container": None,
              "mirrored": False, "rotation": 0, "gop_ms": 2000},
    "audio": {"codec": "opus", "sample_rate": 16000, "channels": 1, "bitrate_kbps": 24, "frame_ms": 20, "muxed_in_video": False,
              "echo_cancellation": False, "noise_suppression": False, "auto_gain": False},
    "rung": 2, "clock_source": "shared",
}


def config_at(rung: int) -> dict:
    c = {k: (dict(v) if isinstance(v, dict) else v) for k, v in CONFIG.items()}
    entry = LADDER[rung]
    c["video"].update({"w": entry["w"], "h": entry["h"], "fps": entry["fps"], "bitrate_kbps": entry["video_kbps"]})
    c["audio"]["bitrate_kbps"] = entry["audio_kbps"]
    c["rung"] = rung
    return c


CAMERA_META = {
    "t": "camera_meta", "source": "getUserMedia",
    "devices": [{"kind": "videoinput", "label": "camera2 1, facing front",
                 "device_id_hash": "5f1b2c9e0d4a7b6c8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d",
                 "group_id_hash": "0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d"}],
    "capabilities": {"width": {"min": 1, "max": 1280}, "height": {"min": 1, "max": 720}, "frameRate": {"min": 1, "max": 30}},
    "settings": {"width": 640, "height": 480, "frameRate": 30, "facingMode": "user"},
    "encoder": {"impl": "hardware", "is_config_supported": {"avc1.42E01F": True, "vp8": True}},
    "probe": [
        {"request": {"height": 3001}, "reported": {"w": 1280, "h": 720}, "observed": {"w": 1280, "h": 720, "fps": 29.6}, "reconfig_ms": 143, "method": "rvfc"},
        {"request": {"height": 11}, "reported": {"w": 160, "h": 120}, "observed": {"w": 160, "h": 120, "fps": 30.1}, "reconfig_ms": 121, "method": "rvfc"},
        {"request": {"height": 640}, "reported": {"w": 480, "h": 640}, "observed": {"w": 480, "h": 640, "fps": 29.8}, "reconfig_ms": 98, "method": "rvfc"},
        {"request": {"height": 240}, "reported": {"w": 320, "h": 240}, "observed": {"w": 320, "h": 240, "fps": 30.0}, "reconfig_ms": 95, "method": "rvfc"},
        {"request": {"height": 2001}, "reported": {"w": 1280, "h": 720}, "observed": {"w": 1280, "h": 720, "fps": 29.9}, "reconfig_ms": 140, "method": "rvfc"},
        {"request": {"height": 22}, "reported": {"w": 160, "h": 120}, "observed": {"w": 160, "h": 120, "fps": 30.0}, "reconfig_ms": 118, "method": "rvfc"},
        {"request": {"height": 1001}, "reported": {"w": 1280, "h": 720}, "observed": {"w": 1280, "h": 720, "fps": 29.7}, "reconfig_ms": 139, "method": "rvfc"},
        {"request": {"fps": 200}, "reported": {"w": 640, "h": 480, "fps": 30}, "observed": {"w": 640, "h": 480, "fps": 30.0}, "reconfig_ms": 88, "method": "rvfc"},
        {"request": {"fps": 1}, "reported": {"w": 640, "h": 480, "fps": 1}, "observed": {"w": 640, "h": 480, "fps": 1.0}, "reconfig_ms": 402, "method": "rvfc"},
        {"request": {"fps": 60}, "reported": {"w": 640, "h": 480, "fps": 30}, "observed": {"w": 640, "h": 480, "fps": 29.9}, "reconfig_ms": 90, "method": "rvfc"},
        {"request": {"fps": 120}, "skipped": True},
        {"request": {"fps": 5}, "skipped": True},
        {"request": {"fps": 30}, "skipped": True},
    ],
}

READY = {
    "t": "ready", "session_id": SESSION_ID, "server_ms": 0, "ladder": LADDER, "start_rung": 2,
    "probe": {"count": 8, "bytes": 8192, "window_ms": 1500}, "gop_ms": 2000, "stats_interval_ms": 500,
    "attest_interval_ms": 1000, "attest_nonce": NONCE, "max_media_ms": 60000, "ping_interval_ms": 10000,
    "features": {"nonce_tile": True, "keyframe_requests": True},
}

UI_ACTION = {
    "t": "ui", "state": {
        "phase": "action",
        "self_view": {"oval": True, "oval_emphasis": "normal", "fill": "none"},
        "arc": {"visible": True, "direction": "user_left", "progress": 0.0},
        "character": {"anim": "demo_head_turn_left"},
        "caption": {"text": "Turn your head slowly, like this.", "pictogram": "head_turn_left"},
        "digits": {"visible": False, "values": []},
        "surround": {"brightness": 0.9, "flood": False},
        "badge": "automated",
        "progress": {"step": 1, "of": 2},
        "controls": {"repeat": True, "more_time": True, "cancel": True},
    },
}


def ui(phase: str, **changes) -> dict:
    """UI state message derived from UI_ACTION with a new phase and field overrides (idempotent full state)."""
    state = {k: (dict(v) if isinstance(v, dict) else v) for k, v in UI_ACTION["state"].items()}
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
    "probe_done": {"t": "probe_done", "sent": 8, "bytes": 65536, "first_send_us": 1200450, "last_send_us": 1201980},
    "rung": {"t": "rung", "rung": 3, "reason": "backpressure", "from_video_seq": 1042, "from_audio_seq": 511},
    "stats": {"t": "stats", "queued_bytes": 48213, "queue_ms": 210, "enc_queue": 1, "encoded_kbps": 410, "pre_encode_drops": 7,
              "captured_fps": 14.8, "rtt_ms": 205, "battery_low": False, "thermal": "nominal"},
    "camera_meta": CAMERA_META,
    "attestation": {"t": "attestation", "kind": "play_integrity", "token": "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMjU2R0NNIn0.opaque",
                    "request_hash": "9f2c4b8e1d3a5c7f9e0b2d4f6a8c0e1f3b5d7f9a1c3e5b7d9f1a3c5e7b9d1f3a"},
    "audio_state": {"t": "audio_state", "re": "s17", "event": "started", "at_ms": 8420},
    "attest": {"t": "attest", "video_seq": 1200, "audio_seq": 600,
               "chain": "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b"},
    "ui_event": {"t": "ui_event", "event": "more_time_requested", "detail": {}, "at_ms": 12040},
    "pong": {"t": "pong", "re": "p17", "at_ms": 9110},
    "ping": {"t": "ping", "id": "c17", "at_ms": 9500},
    "bye": {"t": "bye", "reason": "user_cancel", "detail": "cancel pressed on the call screen"},
}

VALID_SERVER: dict[str, dict] = {
    "ready": READY,
    "probe_result": {"t": "probe_result", "goodput_kbps": 640, "rtt_ms": 190, "start_rung": 2},
    "ui": UI_ACTION,
    "say": {"t": "say", "id": "s17", "cue": "digits.say", "params": {"digits": [4, 7, 2]}, "interrupt": False,
            "caption": "Say these numbers out loud: four, seven, two."},
    "action": {"t": "action", "id": "a1", "kind": "head_turn", "params": {"direction": "user_left", "min_deg": 18, "hold_ms": 250},
               "deadline_ms": 7000, "keyframe": True, "say": "s17"},
    "tile": {"t": "tile", "symbol": 5, "min_ms": 400},
    "keyframe": {"t": "keyframe", "id": "k3", "reason": "apex", "boost_kbps": 1200, "boost_ms": 600},
    "set_rung": {"t": "set_rung", "rung": 1, "reason": "headroom"},
    "feedback": {"t": "feedback", "code": "too_dark", "severity": "hint"},
    "ping": {"t": "ping", "id": "p17", "server_ms": 9100, "rtt_ms": 190, "rx_kbps": 410},
    "pong": {"t": "pong", "re": "c17", "server_ms": 9600},
    "end": {"t": "end", "outcome": "completed", "reason": "ok", "retry": False},
    "error": {"t": "error", "code": "admission", "detail": "retry_after=5"},
}

# Extra valid examples exercising alternative branches (one list per type).
EXTRA_VALID_CLIENT: dict[str, list[dict]] = {
    "config": [config_at(4) | {"video": config_at(4)["video"] | {"codec": "vp8", "annexb": False}},
               {"t": "config", "video": {"codec": "avc1.42E01E", "w": 480, "h": 640, "fps": 15, "bitrate_kbps": 400, "annexb": False,
                                          "container": "webm", "mirrored": False, "rotation": 0},
                "audio": {"codec": "opus", "sample_rate": 48000, "channels": 1, "bitrate_kbps": 24, "muxed_in_video": True,
                          "echo_cancellation": False}, "rung": 2}],
    "stats": [{"t": "stats", "queued_bytes": 0, "queue_ms": 0, "encoded_kbps": 0, "captured_fps": 0, "rtt_ms": None, "thermal": "critical"}],
    "attestation": [{"t": "attestation", "kind": "app_attest", "token": "eyJrZXlfaWQiOiJhYmMiLCJhc3NlcnRpb24iOiJ4eXoiLCJjbGllbnRfZGF0YV9oYXNoIjoiOWYyYyJ9",
                     "request_hash": "9f2c4b8e1d3a5c7f9e0b2d4f6a8c0e1f3b5d7f9a1c3e5b7d9f1a3c5e7b9d1f3a"}],
    "bye": [{"t": "bye", "reason": "floor_breached"}],
}
EXTRA_VALID_SERVER: dict[str, list[dict]] = {
    "action": [
        {"t": "action", "id": "a2", "kind": "fingers", "params": {"count": 3, "hand": "either", "placement": "beside_face"}, "deadline_ms": 7000, "keyframe": True},
        {"t": "action", "id": "a3", "kind": "digits", "params": {"values": [4, 7, 2, 9], "lang": "en-NG"}, "deadline_ms": 8000},
        {"t": "action", "id": "a4", "kind": "distance", "params": {"target": "closer", "scale_ratio": 1.4, "hold_ms": 300}, "deadline_ms": 7000, "keyframe": True},
        {"t": "action", "id": "a5", "kind": "blink", "params": {"count": 2, "window_ms": 3000}, "deadline_ms": 5000},
        {"t": "action", "id": "a6", "kind": "expression", "params": {"kind": "smile"}, "deadline_ms": 5000},
        {"t": "action", "id": "a7", "kind": "hand_over_face", "params": {"hand": "right", "region": "mouth", "hold_ms": 500}, "deadline_ms": 7000},
        {"t": "action", "id": "a8", "kind": "look_profile", "params": {"direction": "user_right", "min_deg": 50}, "deadline_ms": 7000},
    ],
    "ping": [{"t": "ping", "id": "p1", "server_ms": 130, "rtt_ms": None, "rx_kbps": None}],
    "say": [{"t": "say", "id": "s3", "cue": "action.fingers.demo", "params": {"count": 3}, "caption": "Show three fingers beside your face."}],
    "ui": [ui("done", arc={"visible": False}, character={"anim": "celebrate"}, caption={"text": "All done. Thank you.", "pictogram": "done"},
              progress={"step": 2, "of": 2}, controls={"repeat": False, "more_time": False, "cancel": False})],
    "end": [{"t": "end", "outcome": "aborted", "reason": "floor_breached", "retry": True}],
    "error": [{"t": "error", "code": "protocol", "detail": "second message was not config"}],
}

# Hand-authored invalid instances that the schemas must reject, beyond the mechanically derived ones.
INVALID_CLIENT: dict[str, list[tuple[str, dict]]] = {
    "hello": [("consent-false", HELLO | {"consent": {"biometric": False, "recording": True, "at_ms_wall": 1}}),
              ("no-video-codec", HELLO | {"caps": HELLO["caps"] | {"video": []}})],
    "config": [("bad-rotation", CONFIG | {"video": CONFIG["video"] | {"rotation": 45}}),
               ("bad-codec-string", CONFIG | {"video": CONFIG["video"] | {"codec": "h264"}})],
    "attest": [("uppercase-hex", VALID_CLIENT["attest"] | {"chain": "3A7BD3E2360A3D29EEA436FCFB7E44C735D117C42D1C1835420B6B9942DD4F1B"})],
    "rung": [("seq-too-large", VALID_CLIENT["rung"] | {"from_video_seq": 70000})],
}
INVALID_SERVER: dict[str, list[tuple[str, dict]]] = {
    "action": [("head-turn-min-deg-out-of-range", VALID_SERVER["action"] | {"params": {"direction": "user_left", "min_deg": 40, "hold_ms": 250}}),
               ("digits-three-values", {"t": "action", "id": "a3", "kind": "digits", "params": {"values": [4, 7, 2], "lang": "en-NG"}, "deadline_ms": 8000}),
               ("fingers-count-six", {"t": "action", "id": "a2", "kind": "fingers", "params": {"count": 6, "hand": "left", "placement": "beside_face"}, "deadline_ms": 7000})],
    "tile": [("symbol-eight", {"t": "tile", "symbol": 8, "min_ms": 400}),
             ("min-ms-too-fast", {"t": "tile", "symbol": 1, "min_ms": 100})],
    "ready": [("empty-ladder", READY | {"ladder": []})],
    "ui": [("progress-above-one", ui("action", arc={"visible": True, "direction": "up", "progress": 1.5}))],
}


def _line(t_ms: int, direction: str, msg: dict) -> dict:
    return {"t_ms": t_ms, "dir": direction, "msg": msg}


def _media(t_ms: int, typ: int, seq: int, pts_ms: int, rung: int, nbytes: int, **flags) -> dict:
    m = {"type": typ, "seq": seq, "pts_ms": pts_ms, "rung": rung, "bytes": nbytes}
    m.update(flags)
    return {"t_ms": t_ms, "dir": "c2s", "media": m}


def _close(t_ms: int, code: int, reason: str = "") -> dict:
    c = {"code": code}
    if reason:
        c["reason"] = reason
    return {"t_ms": t_ms, "dir": "s2c", "close": c}


def _meta(name: str, description: str, expect: dict) -> dict:
    return {"meta": {"name": name, "protocol": "zakadi.v1", "session_id": SESSION_ID, "jti": JTI, "description": description, "expect": expect}}


def _setup(lines: list, camera_meta: dict = CAMERA_META) -> int:
    """Common opening: hello, ready, first ping, probe burst, probe_result, config, camera_meta. Returns the next t_ms."""
    lines.append(_line(0, "c2s", HELLO))
    lines.append(_line(120, "s2c", READY))
    lines.append(_line(130, "s2c", {"t": "ping", "id": "p1", "server_ms": 130, "rtt_ms": None, "rx_kbps": None}))
    lines.append(_line(140, "c2s", {"t": "pong", "re": "p1", "at_ms": 0}))
    t = 150
    for i in range(8):
        lines.append(_media(t, 2, i, 0, 2, 8192))
        t += 20
    lines.append(_line(t, "c2s", {"t": "probe_done", "sent": 8, "bytes": 65536, "first_send_us": 150000, "last_send_us": 290000}))
    lines.append(_line(520, "s2c", {"t": "probe_result", "goodput_kbps": 640, "rtt_ms": 190, "start_rung": 2}))
    lines.append(_line(530, "c2s", CONFIG))
    lines.append(_line(535, "c2s", camera_meta))
    return 540


def _stream(lines: list, t_from: int, t_to: int, seq_v: int, seq_a: int, rung: int = 2, fps: int = 15) -> tuple[int, int]:
    """Summarised media at fps and 50 audio packets per second; returns the next video and audio seq."""
    t = t_from
    step = 1000 // fps
    while t < t_to:
        lines.append(_media(t, 0, seq_v, t - 540, rung, 3300, keyframe=(seq_v % (2 * fps) == 0), param_sets=(seq_v % (2 * fps) == 0)))
        seq_v += 1
        t += step
    return seq_v, seq_a


def transcript_happy() -> list[dict]:
    lines = [_meta("happy-two-actions", "Complete session: framing, a head turn and a finger count, then a clean end.",
                   {"end": {"outcome": "completed", "reason": "ok"}, "close": 1000, "actions": ["head_turn", "fingers"]})]
    t = _setup(lines)
    lines.append(_line(560, "s2c", ui("framing", arc={"visible": False}, character={"anim": "wave"},
                                      caption={"text": "Hi. Quick automated check, about twenty seconds.", "pictogram": "wave"}, progress={"step": 0, "of": 2})))
    lines.append(_line(562, "s2c", {"t": "say", "id": "s1", "cue": "greet.intro", "caption": "Hi. Quick automated check, about twenty seconds."}))
    sv, sa = _stream(lines, 540, 1000, 0, 0)
    lines.append(_line(610, "c2s", {"t": "audio_state", "re": "s1", "event": "started", "at_ms": 70}))
    lines.append(_line(1000, "s2c", {"t": "ping", "id": "p2", "server_ms": 1000, "rtt_ms": 190, "rx_kbps": 405}))
    lines.append(_line(1040, "c2s", {"t": "pong", "re": "p2", "at_ms": 500}))
    lines.append(_line(1040, "c2s", {"t": "stats", "queued_bytes": 12000, "queue_ms": 120, "enc_queue": 1, "encoded_kbps": 420,
                                     "pre_encode_drops": 0, "captured_fps": 15.0, "rtt_ms": 190, "battery_low": False, "thermal": "nominal"}))
    sv, sa = _stream(lines, 1000, 1560, sv, sa)
    lines.append(_line(1540, "c2s", {"t": "attest", "video_seq": sv - 1, "audio_seq": 49,
                                     "chain": "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b"}))
    lines.append(_line(3010, "c2s", {"t": "audio_state", "re": "s1", "event": "ended", "at_ms": 2470}))
    lines.append(_line(3100, "s2c", {"t": "say", "id": "s2", "cue": "frame.arm_length", "caption": "Hold your phone at arm's length."}))
    lines.append(_line(3150, "c2s", {"t": "audio_state", "re": "s2", "event": "started", "at_ms": 2610}))
    lines.append(_line(5200, "c2s", {"t": "audio_state", "re": "s2", "event": "ended", "at_ms": 4660}))
    lines.append(_line(5300, "s2c", {"t": "feedback", "code": "too_dark", "severity": "hint"}))
    lines.append(_line(5300, "s2c", ui("framing", arc={"visible": False}, character={"anim": "listen"},
                                       caption={"text": "Put the light in front of you.", "pictogram": "light_front"}, surround={"brightness": 1.0, "flood": True})))
    lines.append(_line(5302, "s2c", {"t": "say", "id": "s3", "cue": "light.front", "caption": "Put the light in front of you."}))
    lines.append(_line(7400, "s2c", {"t": "say", "id": "s4", "cue": "frame.perfect", "caption": "Perfect."}))
    # action 1: head turn
    lines.append(_line(8000, "s2c", {"t": "say", "id": "s5", "cue": "action.head_turn.demo", "caption": "Turn your head slowly, like this."}))
    lines.append(_line(8000, "s2c", UI_ACTION))
    lines.append(_line(8010, "s2c", {"t": "tile", "symbol": 5, "min_ms": 400}))
    lines.append(_line(8012, "s2c", {"t": "action", "id": "a1", "kind": "head_turn", "params": {"direction": "user_left", "min_deg": 18, "hold_ms": 250},
                                     "deadline_ms": 7000, "keyframe": True, "say": "s5"}))
    lines.append(_line(8050, "c2s", {"t": "audio_state", "re": "s5", "event": "started", "at_ms": 7510}))
    lines.append(_line(8450, "s2c", {"t": "tile", "symbol": 2, "min_ms": 400}))
    lines.append(_line(8900, "s2c", {"t": "tile", "symbol": 7, "min_ms": 400}))
    lines.append(_line(9600, "s2c", {"t": "keyframe", "id": "k1", "reason": "apex", "boost_kbps": 1200, "boost_ms": 600}))
    lines.append(_media(9660, 0, 137, 9120, 2, 21000, keyframe=True, param_sets=True))
    lines.append(_line(9700, "c2s", {"t": "audio_state", "re": "s5", "event": "ended", "at_ms": 9160}))
    lines.append(_line(10400, "s2c", {"t": "say", "id": "s6", "cue": "ack.nice", "caption": "Nice."}))
    lines.append(_line(10400, "s2c", ui("holding", arc={"visible": False}, character={"anim": "nod"}, caption={"text": "Nice.", "pictogram": "check"})))
    # action 2: fingers
    lines.append(_line(11500, "s2c", {"t": "say", "id": "s7", "cue": "action.fingers.demo", "params": {"count": 3}, "caption": "Show three fingers beside your face."}))
    lines.append(_line(11500, "s2c", ui("action", arc={"visible": False}, character={"anim": "demo_fingers_3"},
                                        caption={"text": "Show three fingers beside your face.", "pictogram": "fingers_3"}, progress={"step": 2, "of": 2})))
    lines.append(_line(11510, "s2c", {"t": "tile", "symbol": 1, "min_ms": 400}))
    lines.append(_line(11512, "s2c", {"t": "action", "id": "a2", "kind": "fingers", "params": {"count": 3, "hand": "either", "placement": "beside_face"},
                                      "deadline_ms": 7000, "keyframe": True, "say": "s7"}))
    lines.append(_line(11550, "c2s", {"t": "audio_state", "re": "s7", "event": "started", "at_ms": 11010}))
    lines.append(_line(11950, "s2c", {"t": "tile", "symbol": 6, "min_ms": 400}))
    lines.append(_line(13300, "c2s", {"t": "audio_state", "re": "s7", "event": "ended", "at_ms": 12760}))
    lines.append(_line(14000, "s2c", {"t": "keyframe", "id": "k2", "reason": "apex", "boost_kbps": 1200, "boost_ms": 600}))
    lines.append(_media(14070, 0, 203, 13530, 2, 20400, keyframe=True, param_sets=True))
    lines.append(_line(14800, "s2c", {"t": "say", "id": "s8", "cue": "ack.got_it", "caption": "Got it, thank you."}))
    lines.append(_line(15900, "s2c", ui("done", arc={"visible": False}, character={"anim": "celebrate"},
                                        caption={"text": "All done. Thank you.", "pictogram": "done"}, progress={"step": 2, "of": 2},
                                        controls={"repeat": False, "more_time": False, "cancel": False})))
    lines.append(_line(15902, "s2c", {"t": "say", "id": "s9", "cue": "done.thanks", "caption": "All done. Thank you."}))
    lines.append(_line(17500, "c2s", {"t": "attest", "video_seq": 254, "audio_seq": 848,
                                      "chain": "5e0b1c4a8d7f2e3a9c6b0d4e1f8a7c2b3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90"}))
    lines.append(_line(17600, "s2c", {"t": "end", "outcome": "completed", "reason": "ok", "retry": False}))
    lines.append(_close(17650, 1000))
    return lines


def transcript_digits_retry() -> list[dict]:
    lines = [_meta("digits-retry", "A spoken-digits challenge fails once (misheard) and is retried with new values, then passes.",
                   {"end": {"outcome": "completed", "reason": "ok"}, "close": 1000, "actions": ["distance", "digits", "digits"]})]
    _setup(lines)
    lines.append(_line(560, "s2c", ui("framing", arc={"visible": False}, character={"anim": "wave"}, caption={"text": "Hi.", "pictogram": "wave"}, progress={"step": 0, "of": 2})))
    lines.append(_line(562, "s2c", {"t": "say", "id": "s1", "cue": "greet.short", "caption": "Hi. Quick automated check."}))
    lines.append(_line(600, "c2s", {"t": "audio_state", "re": "s1", "event": "started", "at_ms": 60}))
    lines.append(_line(2400, "c2s", {"t": "audio_state", "re": "s1", "event": "ended", "at_ms": 1860}))
    lines.append(_line(6000, "s2c", {"t": "say", "id": "s2", "cue": "action.closer.demo", "caption": "Come a little closer."}))
    lines.append(_line(6000, "s2c", ui("action", arc={"visible": True, "direction": "closer", "progress": 0.0}, character={"anim": "demo_closer"},
                                       caption={"text": "Come a little closer.", "pictogram": "closer"})))
    lines.append(_line(6010, "s2c", {"t": "tile", "symbol": 3, "min_ms": 400}))
    lines.append(_line(6012, "s2c", {"t": "action", "id": "a1", "kind": "distance", "params": {"target": "closer", "scale_ratio": 1.4, "hold_ms": 300},
                                     "deadline_ms": 7000, "keyframe": True, "say": "s2"}))
    lines.append(_line(6050, "c2s", {"t": "audio_state", "re": "s2", "event": "started", "at_ms": 5510}))
    lines.append(_line(7600, "c2s", {"t": "audio_state", "re": "s2", "event": "ended", "at_ms": 7060}))
    lines.append(_line(8900, "s2c", {"t": "say", "id": "s3", "cue": "ack.perfect", "caption": "Perfect."}))
    lines.append(_line(10000, "s2c", {"t": "say", "id": "s4", "cue": "digits.say", "params": {"digits": [4, 7, 2, 9]},
                                      "caption": "Say these numbers out loud: four, seven, two, nine."}))
    lines.append(_line(10000, "s2c", ui("listening", arc={"visible": False}, character={"anim": "listen"},
                                        caption={"text": "Say these numbers out loud.", "pictogram": "speak"}, digits={"visible": False, "values": []},
                                        progress={"step": 2, "of": 2})))
    lines.append(_line(10010, "s2c", {"t": "tile", "symbol": 0, "min_ms": 400}))
    lines.append(_line(10012, "s2c", {"t": "action", "id": "a2", "kind": "digits", "params": {"values": [4, 7, 2, 9], "lang": "en-NG"}, "deadline_ms": 8000, "say": "s4"}))
    lines.append(_line(10050, "c2s", {"t": "audio_state", "re": "s4", "event": "started", "at_ms": 9510}))
    lines.append(_line(13200, "c2s", {"t": "audio_state", "re": "s4", "event": "ended", "at_ms": 12660}))
    lines.append(_line(13200, "s2c", ui("listening", arc={"visible": False}, character={"anim": "listen"},
                                        caption={"text": "Say these numbers out loud.", "pictogram": "speak"}, digits={"visible": True, "values": [4, 7, 2, 9]},
                                        progress={"step": 2, "of": 2})))
    lines.append(_line(17000, "s2c", {"t": "feedback", "code": "noisy_audio", "severity": "hint"}))
    lines.append(_line(17000, "s2c", {"t": "say", "id": "s5", "cue": "retry.louder", "caption": "Let's try that once more, a little louder."}))
    lines.append(_line(17050, "c2s", {"t": "audio_state", "re": "s5", "event": "started", "at_ms": 16510}))
    lines.append(_line(19200, "c2s", {"t": "audio_state", "re": "s5", "event": "ended", "at_ms": 18660}))
    lines.append(_line(19300, "s2c", {"t": "say", "id": "s6", "cue": "digits.say", "params": {"digits": [9, 1, 3, 8]},
                                      "caption": "Say these numbers out loud: nine, one, three, eight."}))
    lines.append(_line(19310, "s2c", {"t": "tile", "symbol": 4, "min_ms": 400}))
    lines.append(_line(19312, "s2c", {"t": "action", "id": "a3", "kind": "digits", "params": {"values": [9, 1, 3, 8], "lang": "en-NG"}, "deadline_ms": 8000, "say": "s6"}))
    lines.append(_line(19350, "c2s", {"t": "audio_state", "re": "s6", "event": "started", "at_ms": 18810}))
    lines.append(_line(22500, "c2s", {"t": "audio_state", "re": "s6", "event": "ended", "at_ms": 21960}))
    lines.append(_line(22500, "s2c", ui("listening", arc={"visible": False}, character={"anim": "listen"},
                                        caption={"text": "Say these numbers out loud.", "pictogram": "speak"}, digits={"visible": True, "values": [9, 1, 3, 8]},
                                        progress={"step": 2, "of": 2})))
    lines.append(_line(26800, "s2c", {"t": "say", "id": "s7", "cue": "ack.got_it", "caption": "Got it, thank you."}))
    lines.append(_line(27900, "s2c", ui("done", arc={"visible": False}, character={"anim": "celebrate"}, caption={"text": "All done.", "pictogram": "done"},
                                        digits={"visible": False, "values": []}, progress={"step": 2, "of": 2}, controls={"repeat": False, "more_time": False, "cancel": False})))
    lines.append(_line(27902, "s2c", {"t": "say", "id": "s8", "cue": "done.thanks", "caption": "All done. Thank you."}))
    lines.append(_line(29400, "c2s", {"t": "attest", "video_seq": 432, "audio_seq": 1440,
                                      "chain": "5e0b1c4a8d7f2e3a9c6b0d4e1f8a7c2b3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90"}))
    lines.append(_line(29500, "s2c", {"t": "end", "outcome": "completed", "reason": "ok", "retry": False}))
    lines.append(_close(29550, 1000))
    return lines


def transcript_floor_breached() -> list[dict]:
    lines = [_meta("floor-breached", "The uplink collapses; the client steps down to rung 4, cannot sustain it for 3 s, and ends with bye floor_breached.",
                   {"end": {"outcome": "aborted", "reason": "floor_breached"}, "close": 1000, "rungs": [2, 3, 4]})]
    _setup(lines)
    lines.append(_line(560, "s2c", ui("framing", arc={"visible": False}, character={"anim": "wave"}, caption={"text": "Hi.", "pictogram": "wave"}, progress={"step": 0, "of": 2})))
    lines.append(_line(562, "s2c", {"t": "say", "id": "s1", "cue": "greet.short", "caption": "Hi. Quick automated check."}))
    lines.append(_line(1040, "c2s", {"t": "stats", "queued_bytes": 60000, "queue_ms": 700, "enc_queue": 2, "encoded_kbps": 420, "pre_encode_drops": 0,
                                     "captured_fps": 15.0, "rtt_ms": 190, "battery_low": False, "thermal": "nominal"}))
    lines.append(_line(1440, "c2s", {"t": "rung", "rung": 3, "reason": "backpressure", "from_video_seq": 14, "from_audio_seq": 45}))
    lines.append(_line(1445, "c2s", config_at(3)))
    lines.append(_media(1460, 0, 14, 920, 3, 2100, rung_changed=True, keyframe=True, param_sets=True))
    lines.append(_line(2540, "c2s", {"t": "stats", "queued_bytes": 140000, "queue_ms": 1700, "enc_queue": 3, "encoded_kbps": 265, "pre_encode_drops": 6,
                                     "captured_fps": 12.0, "rtt_ms": 410, "battery_low": False, "thermal": "nominal"}))
    lines.append(_line(2545, "c2s", {"t": "rung", "rung": 4, "reason": "backpressure", "from_video_seq": 27, "from_audio_seq": 100}))
    lines.append(_line(2550, "c2s", config_at(4)))
    lines.append(_media(2560, 0, 27, 2020, 4, 1500, rung_changed=True, keyframe=True, param_sets=True))
    for t in (3040, 3540, 4040, 4540, 5040, 5540):
        lines.append(_line(t, "c2s", {"t": "stats", "queued_bytes": 200000, "queue_ms": 2400, "enc_queue": 4, "encoded_kbps": 160, "pre_encode_drops": 20,
                                      "captured_fps": 10.0, "rtt_ms": 900, "battery_low": False, "thermal": "nominal"}))
    lines.append(_line(5600, "c2s", {"t": "attest", "video_seq": 52, "audio_seq": 250,
                                     "chain": "5e0b1c4a8d7f2e3a9c6b0d4e1f8a7c2b3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90"}))
    lines.append(_line(5610, "c2s", {"t": "bye", "reason": "floor_breached", "detail": "rung 4 queue above 1500 ms for 3 s"}))
    lines.append(_line(5700, "s2c", {"t": "end", "outcome": "aborted", "reason": "floor_breached", "retry": True}))
    lines.append(_close(5720, 1000))
    return lines


def transcript_admission_rejected() -> list[dict]:
    lines = [_meta("admission-rejected", "The pod is at capacity: error admission then close 4008 with the retry delay in the reason.",
                   {"close": 4008, "error": "admission"})]
    lines.append(_line(0, "c2s", HELLO))
    lines.append(_line(90, "s2c", {"t": "error", "code": "admission", "detail": "retry_after=5"}))
    lines.append(_close(95, 4008, "retry_after=5"))
    return lines


def transcript_user_cancel() -> list[dict]:
    lines = [_meta("user-cancel", "The user presses cancel during the first action; end aborted user_cancel, close 4010.",
                   {"end": {"outcome": "aborted", "reason": "user_cancel"}, "close": 4010})]
    _setup(lines)
    lines.append(_line(560, "s2c", ui("framing", arc={"visible": False}, character={"anim": "wave"}, caption={"text": "Hi.", "pictogram": "wave"}, progress={"step": 0, "of": 2})))
    lines.append(_line(562, "s2c", {"t": "say", "id": "s1", "cue": "greet.short", "caption": "Hi. Quick automated check."}))
    lines.append(_line(6000, "s2c", {"t": "say", "id": "s2", "cue": "action.head_turn.demo", "caption": "Turn your head slowly, like this."}))
    lines.append(_line(6000, "s2c", UI_ACTION))
    lines.append(_line(6010, "s2c", {"t": "tile", "symbol": 5, "min_ms": 400}))
    lines.append(_line(6012, "s2c", {"t": "action", "id": "a1", "kind": "head_turn", "params": {"direction": "user_right", "min_deg": 20, "hold_ms": 250},
                                     "deadline_ms": 7000, "keyframe": True, "say": "s2"}))
    lines.append(_line(7300, "c2s", {"t": "ui_event", "event": "cancel_pressed", "detail": {}, "at_ms": 6760}))
    lines.append(_line(7305, "c2s", {"t": "attest", "video_seq": 101, "audio_seq": 338,
                                     "chain": "5e0b1c4a8d7f2e3a9c6b0d4e1f8a7c2b3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90"}))
    lines.append(_line(7310, "c2s", {"t": "bye", "reason": "user_cancel"}))
    lines.append(_line(7400, "s2c", {"t": "end", "outcome": "aborted", "reason": "user_cancel", "retry": False}))
    lines.append(_close(7420, 4010))
    return lines


def transcript_max_duration() -> list[dict]:
    lines = [_meta("max-duration", "The media clock passes 60 s without completion: end aborted max_duration, close 4009.",
                   {"end": {"outcome": "aborted", "reason": "max_duration"}, "close": 4009})]
    _setup(lines)
    lines.append(_line(560, "s2c", ui("framing", arc={"visible": False}, character={"anim": "wave"}, caption={"text": "Hi.", "pictogram": "wave"}, progress={"step": 0, "of": 2})))
    lines.append(_line(562, "s2c", {"t": "say", "id": "s1", "cue": "greet.short", "caption": "Hi. Quick automated check."}))
    for i in range(1, 4):
        lines.append(_line(15000 * i, "s2c", {"t": "say", "id": "s%d" % (i + 1), "cue": "frame.center", "caption": "Move to the centre of the oval."}))
        lines.append(_line(15000 * i + 40, "c2s", {"t": "audio_state", "re": "s%d" % (i + 1), "event": "started", "at_ms": 15000 * i - 500}))
        lines.append(_line(15000 * i + 1900, "c2s", {"t": "audio_state", "re": "s%d" % (i + 1), "event": "ended", "at_ms": 15000 * i + 1360}))
    lines.append(_line(58000, "s2c", {"t": "say", "id": "s5", "cue": "frame.center", "caption": "Move to the centre of the oval."}))
    lines.append(_line(58040, "c2s", {"t": "audio_state", "re": "s5", "event": "started", "at_ms": 57500}))
    lines.append(_media(60560, 0, 900, 60020, 2, 3300))
    lines.append(_line(60600, "s2c", {"t": "end", "outcome": "aborted", "reason": "max_duration", "retry": True}))
    lines.append(_close(60620, 4009))
    return lines


def transcript_protocol_error() -> list[dict]:
    lines = [_meta("protocol-error", "The client sends media before config: error protocol then close 4006.",
                   {"close": 4006, "error": "protocol"})]
    lines.append(_line(0, "c2s", HELLO))
    lines.append(_line(120, "s2c", READY))
    lines.append(_media(200, 0, 0, 0, 2, 3300, keyframe=True, param_sets=True))
    lines.append(_line(230, "s2c", {"t": "error", "code": "protocol", "detail": "media before config"}))
    lines.append(_close(235, 4006, "protocol"))
    return lines


def finish(lines: list[dict]) -> list[dict]:
    """Stable-sorts the body by t_ms (builders append logically, not chronologically) and keeps the meta line first."""
    return [lines[0]] + sorted(lines[1:], key=lambda l: l["t_ms"])


TRANSCRIPTS = {
    "happy-two-actions": transcript_happy,
    "digits-retry": transcript_digits_retry,
    "floor-breached": transcript_floor_breached,
    "admission-rejected": transcript_admission_rejected,
    "user-cancel": transcript_user_cancel,
    "max-duration": transcript_max_duration,
    "protocol-error": transcript_protocol_error,
}
