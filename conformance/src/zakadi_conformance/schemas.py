"""JSON Schema (draft 2020-12) builders for every zakadi.v1 control message and for the vector files.

The schemas validate the fields the protocol defines and leave unknown fields alone, because the
protocol requires both sides to ignore unknown fields and unknown message types.
"""

from __future__ import annotations

from . import SCHEMA_BASE

DRAFT = "https://json-schema.org/draft/2020-12/schema"
COMMON = SCHEMA_BASE + "common.schema.json"

CLIENT_TYPES = ["hello", "config", "probe_done", "rung", "stats", "camera_meta", "attestation",
                "audio_state", "attest", "ui_event", "pong", "ping", "bye"]
SERVER_TYPES = ["ready", "probe_result", "ui", "say", "action", "tile", "keyframe", "set_rung",
                "feedback", "ping", "pong", "end", "error"]

CHALLENGE_KINDS = ["head_turn", "distance", "fingers", "digits", "blink", "expression", "hand_over_face", "look_profile"]
CLOSE_CODES = [1000, 4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009, 4010, 4011]
END_REASONS = ["ok", "floor_breached", "max_duration", "user_cancel", "attempts_exhausted", "server_error", "admission"]
BYE_REASONS = ["user_cancel", "app_background", "permission_revoked", "floor_breached", "capture_error", "encoder_error", "unknown"]
FEEDBACK_CODES = ["too_dark", "too_bright", "too_close", "too_far", "no_face", "multiple_faces", "off_center", "blurry",
                  "move_slower", "noisy_audio", "headphones_detected"]
UI_EVENTS = ["repeat_requested", "more_time_requested", "cancel_pressed", "app_backgrounded", "app_foregrounded",
             "permission_revoked", "headphones_changed"]
ERROR_CODES = ["protocol", "unsupported_caps", "token", "internal", "admission"]
KNOWN_PHASES = ["connecting", "framing", "action", "listening", "holding", "done", "error"]


def ref(name: str) -> dict:
    return {"$ref": COMMON + "#/$defs/" + name}


def obj(properties: dict, required: list[str] | None = None, **extra) -> dict:
    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    schema.update(extra)
    return schema


def enum(values: list, description: str = "") -> dict:
    d: dict = {"enum": values}
    if description:
        d["description"] = description
    return d


def integer(minimum: int | None = 0, maximum: int | None = None, description: str = "") -> dict:
    d: dict = {"type": "integer"}
    if minimum is not None:
        d["minimum"] = minimum
    if maximum is not None:
        d["maximum"] = maximum
    if description:
        d["description"] = description
    return d


def number(minimum: float | None = 0, maximum: float | None = None, description: str = "") -> dict:
    d: dict = {"type": "number"}
    if minimum is not None:
        d["minimum"] = minimum
    if maximum is not None:
        d["maximum"] = maximum
    if description:
        d["description"] = description
    return d


def string(description: str = "", pattern: str | None = None, max_length: int | None = None) -> dict:
    d: dict = {"type": "string"}
    if pattern:
        d["pattern"] = pattern
    if max_length:
        d["maxLength"] = max_length
    if description:
        d["description"] = description
    return d


BOOL = {"type": "boolean"}


def common_schema() -> dict:
    return {
        "$schema": DRAFT,
        "$id": COMMON,
        "title": "Zakadi protocol common definitions",
        "$defs": {
            "id": string("Correlation id, at most 32 characters", max_length=32) | {"minLength": 1},
            "ms": integer(0, None, "Milliseconds"),
            "atMs": integer(0, None, "Milliseconds on the client's session media clock (0 before the first captured frame)"),
            "serverMs": integer(0, None, "Milliseconds on the server's monotonic clock"),
            "rung": integer(0, 15, "Ladder rung; index 0 is the highest quality"),
            "seq16": integer(0, 65535, "Per-type sequence number, wraps at 65535"),
            "hex64": string("Lowercase hex SHA-256", pattern="^[0-9a-f]{64}$"),
            "cueId": string("Prompt-pack cue identifier", pattern="^[a-z0-9_]+(\\.[a-z0-9_]+)+$"),
            "videoCodec": string("H.264 codec string with profile and level, or vp8", pattern="^(avc1\\.[0-9A-Fa-f]{6}|vp8)$"),
            "audioCodec": enum(["opus", "aac"]),
            "container": enum(["webm", "mp4"]),
            "profile": enum(["webcodecs", "native", "mediarecorder"]),
            "platform": enum(["web", "android", "ios"]),
            "challengeKind": enum(CHALLENGE_KINDS),
            "headDirection": enum(["user_left", "user_right", "up", "down"], "Directions in the user's own body frame"),
            "arcDirection": enum(["user_left", "user_right", "up", "down", "closer", "further"]),
            "closeCode": enum(CLOSE_CODES, "WebSocket close codes used by zakadi.v1"),
            "endReason": enum(END_REASONS),
            "byeReason": enum(BYE_REASONS),
            "feedbackCode": enum(FEEDBACK_CODES),
            "uiEvent": enum(UI_EVENTS),
            "errorCode": enum(ERROR_CODES),
            "digit": integer(0, 9),
            "sessionId": string("Session identifier", pattern="^ses_[A-Za-z0-9]+$"),
            "base64_16": string("16 bytes, base64 or base64url, padding optional", pattern="^[A-Za-z0-9+/_-]{22}(==)?$"),
            "ladderEntry": obj({
                "rung": ref("rung"), "w": integer(16), "h": integer(16), "fps": integer(1, 60),
                "video_kbps": integer(1), "audio_kbps": integer(1)},
                ["rung", "w", "h", "fps", "video_kbps", "audio_kbps"]),
        },
    }


def message(name: str, direction: str, properties: dict, required: list[str], description: str) -> dict:
    props = {"t": {"const": name}, "id": ref("id")}
    props.update(properties)
    return {
        "$schema": DRAFT,
        "$id": SCHEMA_BASE + direction + "/" + name + ".schema.json",
        "title": "zakadi.v1 %s message `%s`" % ("client-to-server" if direction == "client" else "server-to-client", name),
        "description": description,
        "type": "object",
        "properties": props,
        "required": ["t"] + required,
    }


def client_schemas() -> dict[str, dict]:
    s: dict[str, dict] = {}
    s["hello"] = message("hello", "client", {
        "v": {"const": 1},
        "token": string("The client_token from POST /v1/sessions, sent once and never in the URL") | {"minLength": 1},
        "sdk": obj({
            "platform": ref("platform"), "name": string(), "version": string(), "os": string(), "device": string(),
            "browser": string("Present only on web"),
            "wrapper": obj({"name": string(), "version": string()}, ["name", "version"]),
        }, ["platform", "name", "version"]),
        "caps": obj({
            "profile": ref("profile"),
            "video": {"type": "array", "items": ref("videoCodec"), "minItems": 1},
            "audio": {"type": "array", "items": ref("audioCodec")},
            "hw_encode": BOOL, "keyframe_on_demand": BOOL, "bitrate_reconfig": BOOL,
            "max_resolution": obj({"w": integer(1), "h": integer(1)}, ["w", "h"]),
            "max_fps": integer(1),
            "attestation": enum(["play_integrity", "app_attest", "webauthn", "none"]),
        }, ["profile", "video", "audio", "keyframe_on_demand", "bitrate_reconfig"]),
        "prompt_pack": obj({"lang": string(), "version": string()}, ["lang", "version"]),
        "a11y": obj({"screen_reader": BOOL, "captions": BOOL, "reduced_motion": BOOL, "extended_time": BOOL}),
        "consent": obj({"biometric": {"const": True}, "recording": {"const": True}, "at_ms_wall": integer(0)},
                       ["biometric", "recording", "at_ms_wall"]),
    }, ["v", "token", "sdk", "caps", "prompt_pack", "consent"],
        "First message on the socket. Both consent flags must be true; the server closes with 4006 otherwise.")
    s["config"] = message("config", "client", {
        "video": obj({
            "codec": ref("videoCodec"), "w": integer(16), "h": integer(16), "fps": integer(1, 60), "bitrate_kbps": integer(1),
            "annexb": BOOL, "container": {"oneOf": [{"type": "null"}, ref("container")]}, "mirrored": BOOL,
            "rotation": enum([0, 90, 180, 270]), "gop_ms": integer(1),
        }, ["codec", "w", "h", "fps", "bitrate_kbps", "annexb", "mirrored", "rotation"]),
        "audio": obj({
            "codec": ref("audioCodec"), "sample_rate": integer(8000), "channels": integer(1, 2), "bitrate_kbps": integer(1),
            "frame_ms": integer(1), "muxed_in_video": BOOL, "container": {"oneOf": [{"type": "null"}, ref("container")]},
            "echo_cancellation": BOOL, "noise_suppression": BOOL, "auto_gain": BOOL,
        }, ["codec", "sample_rate", "channels", "bitrate_kbps", "echo_cancellation"]),
        "rung": ref("rung"),
        "clock_source": enum(["shared", "aligned"], "Default shared; aligned when the web SDK had no common capture clock"),
    }, ["video", "audio", "rung"], "Sent before the first media message and after every encoder reconfiguration.")
    s["probe_done"] = message("probe_done", "client", {
        "sent": integer(1), "bytes": integer(1), "first_send_us": integer(0), "last_send_us": integer(0),
    }, ["sent", "bytes", "first_send_us", "last_send_us"], "Ends the uplink probe burst.")
    s["rung"] = message("rung", "client", {
        "rung": ref("rung"), "reason": enum(["backpressure", "headroom", "server", "keyframe_guard"]),
        "from_video_seq": ref("seq16"), "from_audio_seq": ref("seq16"),
    }, ["rung", "reason", "from_video_seq", "from_audio_seq"], "Announces a rung change and the sequence numbers it applies from.")
    s["stats"] = message("stats", "client", {
        "queued_bytes": integer(0), "queue_ms": integer(0), "enc_queue": integer(0), "encoded_kbps": number(0),
        "pre_encode_drops": integer(0), "captured_fps": number(0), "rtt_ms": {"oneOf": [{"type": "null"}, integer(0)]},
        "battery_low": BOOL, "thermal": enum(["nominal", "fair", "serious", "critical"]),
    }, ["queued_bytes", "queue_ms", "encoded_kbps", "captured_fps"], "Transport and encoder statistics every stats_interval_ms.")
    probe_entry = obj({
        "request": {"type": "object"}, "reported": {"type": "object"}, "observed": {"type": "object"},
        "reconfig_ms": integer(0), "skipped": BOOL, "method": enum(["getSettings", "rvfc", "mstp", "native"]),
    }, ["request"])
    s["camera_meta"] = message("camera_meta", "client", {
        "source": string("Platform capture API name"),
        "devices": {"type": "array", "items": obj({"kind": string(), "label": string(), "device_id_hash": string(), "group_id_hash": string()})},
        "capabilities": {"type": "object"}, "settings": {"type": "object"},
        "encoder": obj({"impl": string(), "is_config_supported": {"type": "object", "additionalProperties": BOOL}}),
        "probe": {"type": "array", "items": probe_entry},
    }, ["source", "probe"], "Raw camera and encoder metadata plus the constraint-probe results; device ids are salted hashes.")
    s["attestation"] = message("attestation", "client", {
        "kind": enum(["play_integrity", "app_attest"]), "token": string() | {"minLength": 1}, "request_hash": ref("hex64"),
    }, ["kind", "token", "request_hash"], "Opaque platform attestation token bound to sha256(session_id || attest_nonce).")
    s["audio_state"] = message("audio_state", "client", {
        "re": ref("id"), "event": enum(["started", "ended", "failed"]), "at_ms": ref("atMs"),
    }, ["re", "event", "at_ms"], "Playback bracket for a say cue.")
    s["attest"] = message("attest", "client", {
        "video_seq": ref("seq16"), "audio_seq": ref("seq16"), "chain": ref("hex64"),
    }, ["video_seq", "audio_seq", "chain"], "Rolling hash chain over media messages of types 0, 1 and 3.")
    s["ui_event"] = message("ui_event", "client", {
        "event": ref("uiEvent"), "detail": {"type": "object"}, "at_ms": ref("atMs"),
    }, ["event", "at_ms"], "User or platform events that the server may react to.")
    s["pong"] = message("pong", "client", {"re": ref("id"), "at_ms": ref("atMs")}, ["re", "at_ms"], "Reply to a server ping.")
    s["ping"] = message("ping", "client", {"at_ms": ref("atMs")}, ["id", "at_ms"], "Client-initiated ping, at most once per second.")
    s["bye"] = message("bye", "client", {"reason": ref("byeReason"), "detail": string()}, ["reason"], "Client ends the session.")
    return s


def action_params_schema() -> dict:
    hand = enum(["left", "right", "either"])
    return {
        "type": "object",
        "allOf": [
            {"if": {"properties": {"kind": {"const": "head_turn"}}}, "then": {"properties": {"params": obj({
                "direction": ref("headDirection"), "min_deg": integer(15, 25), "hold_ms": integer(150, 300)},
                ["direction", "min_deg", "hold_ms"])}}},
            {"if": {"properties": {"kind": {"const": "distance"}}}, "then": {"properties": {"params": obj({
                "target": enum(["closer", "further"]), "scale_ratio": number(1.25, 1.6), "hold_ms": integer(100, 1000)},
                ["target", "scale_ratio", "hold_ms"])}}},
            {"if": {"properties": {"kind": {"const": "fingers"}}}, "then": {"properties": {"params": obj({
                "count": integer(1, 5), "hand": hand, "placement": enum(["beside_face", "crossing_face"])},
                ["count", "hand", "placement"])}}},
            {"if": {"properties": {"kind": {"const": "digits"}}}, "then": {"properties": {"params": obj({
                "values": {"type": "array", "items": ref("digit"), "minItems": 4, "maxItems": 4}, "lang": string()},
                ["values", "lang"])}}},
            {"if": {"properties": {"kind": {"const": "blink"}}}, "then": {"properties": {"params": obj({
                "count": integer(1, 2), "window_ms": integer(1000, 10000)}, ["count", "window_ms"])}}},
            {"if": {"properties": {"kind": {"const": "expression"}}}, "then": {"properties": {"params": obj({
                "kind": enum(["smile", "open_mouth"])}, ["kind"])}}},
            {"if": {"properties": {"kind": {"const": "hand_over_face"}}}, "then": {"properties": {"params": obj({
                "hand": hand, "region": enum(["mouth", "nose", "left_eye", "right_eye"]), "hold_ms": integer(100, 2000)},
                ["hand", "region", "hold_ms"])}}},
            {"if": {"properties": {"kind": {"const": "look_profile"}}}, "then": {"properties": {"params": obj({
                "direction": ref("headDirection"), "min_deg": integer(45, 60)}, ["direction", "min_deg"])}}},
        ],
    }


def server_schemas() -> dict[str, dict]:
    s: dict[str, dict] = {}
    s["ready"] = message("ready", "server", {
        "session_id": ref("sessionId"), "server_ms": ref("serverMs"),
        "ladder": {"type": "array", "items": ref("ladderEntry"), "minItems": 1},
        "start_rung": ref("rung"),
        "probe": obj({"count": integer(1), "bytes": integer(64), "window_ms": integer(1)}, ["count", "bytes", "window_ms"]),
        "gop_ms": integer(1), "stats_interval_ms": integer(100), "attest_interval_ms": integer(100),
        "attest_nonce": ref("base64_16"), "max_media_ms": integer(1000), "ping_interval_ms": integer(1000),
        "features": {"type": "object", "additionalProperties": BOOL},
    }, ["session_id", "server_ms", "ladder", "start_rung", "probe", "gop_ms", "stats_interval_ms", "attest_interval_ms",
        "attest_nonce", "max_media_ms", "ping_interval_ms"], "Session parameters, sent once after a valid hello.")
    s["probe_result"] = message("probe_result", "server", {
        "goodput_kbps": number(0), "rtt_ms": integer(0), "start_rung": ref("rung"),
    }, ["goodput_kbps", "rtt_ms", "start_rung"], "Result of the uplink probe.")
    s["ui"] = message("ui", "server", {
        "state": obj({
            "phase": string("Open value set; known values: " + ", ".join(KNOWN_PHASES)),
            "self_view": obj({"oval": BOOL, "oval_emphasis": enum(["normal", "highlight"]), "fill": enum(["none", "dim"])}),
            "arc": obj({"visible": BOOL, "direction": ref("arcDirection"), "progress": number(0, 1)}),
            "character": obj({"anim": string("Open value set of character animations")}),
            "caption": obj({"text": string(), "pictogram": string()}),
            "digits": obj({"visible": BOOL, "values": {"type": "array", "items": ref("digit")}}),
            "surround": obj({"brightness": number(0, 1), "flood": BOOL}),
            "badge": string(),
            "progress": obj({"step": integer(0), "of": integer(0)}),
            "controls": obj({"repeat": BOOL, "more_time": BOOL, "cancel": BOOL}),
        }, ["phase"]),
    }, ["state"], "Full declarative UI state; idempotent, not a delta.")
    s["say"] = message("say", "server", {
        "cue": ref("cueId"),
        "params": obj({"digits": {"type": "array", "items": ref("digit"), "minItems": 1, "maxItems": 8}, "count": integer(1, 5)}),
        "interrupt": BOOL, "caption": string(),
    }, ["id", "cue"], "Play a prompt-pack cue, optionally followed by digit or count clips, as one playback.")
    action = message("action", "server", {
        "kind": ref("challengeKind"), "params": {"type": "object"}, "deadline_ms": integer(1000, 30000),
        "keyframe": BOOL, "say": ref("id"),
    }, ["id", "kind", "params", "deadline_ms"], "Issue one challenge with server-chosen parameters.")
    action["allOf"] = action_params_schema()["allOf"]
    s["action"] = action
    s["tile"] = message("tile", "server", {"symbol": integer(0, 7), "min_ms": integer(333)}, ["symbol", "min_ms"],
                        "Set the host tile nonce region to palette entry symbol within one display frame.")
    s["keyframe"] = message("keyframe", "server", {
        "reason": enum(["apex", "recovery", "start"]), "boost_kbps": integer(1), "boost_ms": integer(1),
    }, ["id", "reason"], "Request an IDR; boost_kbps is an absolute ceiling for boost_ms.")
    s["set_rung"] = message("set_rung", "server", {"rung": ref("rung"), "reason": enum(["headroom", "server_load"])},
                            ["rung", "reason"], "Server-driven rung change; the client must answer with rung.")
    s["feedback"] = message("feedback", "server", {"code": ref("feedbackCode"), "severity": enum(["hint", "block"])},
                            ["code", "severity"], "Informational quality feedback.")
    s["ping"] = message("ping", "server", {
        "server_ms": ref("serverMs"), "rtt_ms": {"oneOf": [{"type": "null"}, integer(0)]},
        "rx_kbps": {"oneOf": [{"type": "null"}, number(0)]},
    }, ["id", "server_ms"], "Keepalive carrying the server-measured RTT and media receive rate.")
    s["pong"] = message("pong", "server", {"re": ref("id"), "server_ms": ref("serverMs")}, ["re", "server_ms"],
                        "Reply to a client-initiated ping.")
    s["end"] = message("end", "server", {"outcome": enum(["completed", "aborted"]), "reason": ref("endReason"), "retry": BOOL},
                       ["outcome", "reason", "retry"], "Last message before the socket closes with 1000, 4007, 4009 or 4010.")
    s["error"] = message("error", "server", {"code": ref("errorCode"), "detail": string()}, ["code"],
                         "Precedes a close with 4001-4006, 4008 or 4011 when the connection state allows.")
    return s


def aggregate_schema(direction: str, names: list[str]) -> dict:
    return {
        "$schema": DRAFT,
        "$id": SCHEMA_BASE + direction + ".schema.json",
        "title": "Any zakadi.v1 %s message" % ("client-to-server" if direction == "client" else "server-to-client"),
        "description": "Discriminated by t. Unknown message types are valid on the wire and must be ignored; this aggregate only validates known types.",
        "oneOf": [{"$ref": SCHEMA_BASE + direction + "/" + n + ".schema.json"} for n in names],
    }


def transcript_schema() -> dict:
    return {
        "$schema": DRAFT,
        "$id": SCHEMA_BASE + "transcript-line.schema.json",
        "title": "One line of a sessions/*.jsonl transcript",
        "description": "The first line is a meta line; every other line carries exactly one of msg, media or close.",
        "oneOf": [
            obj({"meta": obj({"name": string(), "protocol": {"const": "zakadi.v1"}, "session_id": ref("sessionId"),
                              "jti": ref("base64_16"), "description": string(), "expect": {"type": "object"}},
                             ["name", "protocol", "session_id", "jti"])}, ["meta"], additionalProperties=False),
            obj({"t_ms": ref("ms"), "dir": enum(["c2s", "s2c"]), "msg": {"type": "object", "required": ["t"]}},
                ["t_ms", "dir", "msg"], additionalProperties=False),
            obj({"t_ms": ref("ms"), "dir": {"const": "c2s"}, "media": obj({
                "type": integer(0, 3), "seq": ref("seq16"), "pts_ms": integer(0, 4294967295), "rung": ref("rung"),
                "keyframe": BOOL, "param_sets": BOOL, "rung_changed": BOOL, "bytes": integer(8)},
                ["type", "seq", "pts_ms", "rung", "bytes"])}, ["t_ms", "dir", "media"], additionalProperties=False),
            obj({"t_ms": ref("ms"), "dir": {"const": "s2c"}, "close": obj({"code": ref("closeCode"), "reason": string()}, ["code"])},
                ["t_ms", "dir", "close"], additionalProperties=False),
        ],
    }


def framing_vector_schema() -> dict:
    header = obj({"ver": {"const": 0}, "type": integer(0, 3), "keyframe": BOOL, "param_sets": BOOL, "rung_changed": BOOL,
                  "rung": ref("rung"), "seq": ref("seq16"), "pts_ms": integer(0, 4294967295)},
                 ["ver", "type", "keyframe", "param_sets", "rung_changed", "rung", "seq", "pts_ms"])
    return {
        "$schema": DRAFT,
        "$id": SCHEMA_BASE + "framing-vector.schema.json",
        "title": "A vectors/framing/*.json case",
        "type": "object",
        "properties": {
            "name": string(), "description": string(), "hex": string(pattern="^([0-9a-f]{2})*$"),
            "expect": obj({"header": header, "payload_hex": string(pattern="^([0-9a-f]{2})*$"),
                           "probe_send_time_us": integer(0), "audio_batch": {"type": "array", "items": obj({
                               "pts_delta_ms": integer(0, 65535), "packet_hex": string(pattern="^([0-9a-f]{2})*$")})}},
                          ["header", "payload_hex"]),
            "error": enum(["short_header", "unsupported_version", "reserved_bit_set", "reserved_bits_set", "short_probe",
                           "truncated_batch_record", "batch_out_of_order", "empty_batch"]),
        },
        "required": ["name", "hex"],
        "oneOf": [{"required": ["expect"]}, {"required": ["error"]}],
    }


def chain_vector_schema() -> dict:
    return {
        "$schema": DRAFT,
        "$id": SCHEMA_BASE + "chain-vector.schema.json",
        "title": "A vectors/chain/*.json case",
        "type": "object",
        "properties": {
            "name": string(), "description": string(), "session_id": ref("sessionId"),
            "jti": ref("base64_16"), "token": string("A syntactically valid but unsigned JWT carrying the jti claim"),
            "h0": ref("hex64"),
            "messages": {"type": "array", "items": obj({
                "hex": string(pattern="^([0-9a-f]{2})+$"), "chained": BOOL, "chain_after": ref("hex64")},
                ["hex", "chained", "chain_after"])},
            "attest": {"type": "object", "required": ["t", "video_seq", "audio_seq", "chain"]},
        },
        "required": ["name", "session_id", "jti", "h0", "messages", "attest"],
    }


def all_schemas() -> dict[str, dict]:
    """Returns {relative path under schemas/v1: schema}."""
    out: dict[str, dict] = {"common.schema.json": common_schema()}
    for name, schema in client_schemas().items():
        out["client/" + name + ".schema.json"] = schema
    for name, schema in server_schemas().items():
        out["server/" + name + ".schema.json"] = schema
    out["client.schema.json"] = aggregate_schema("client", CLIENT_TYPES)
    out["server.schema.json"] = aggregate_schema("server", SERVER_TYPES)
    out["transcript-line.schema.json"] = transcript_schema()
    out["framing-vector.schema.json"] = framing_vector_schema()
    out["chain-vector.schema.json"] = chain_vector_schema()
    return out
