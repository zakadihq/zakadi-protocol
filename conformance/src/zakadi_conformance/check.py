"""Conformance checks over the generated schemas and vectors."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator
from referencing import Registry, Resource

from . import SCHEMA_BASE, jws
from .chain import (
    Chain,
    ChainError,
    b64_decode,
    b64url_decode,
    h0,
    jti_bytes_from_token,
    summary_message,
)
from .framing import (
    FramingError,
    Header,
    decode_header,
    encode_header,
    parse_audio_batch,
    parse_probe_payload,
)

ERROR_CLOSES = {4001, 4002, 4003, 4004, 4005, 4006, 4008, 4011}
END_CLOSES = {1000, 4007, 4009, 4010}

# spec 02-api.md 2.2: `ses_` and a ULID, 26 Crockford base32 characters of which the first is at most 7.
SESSION_ID_RE = re.compile(r"^ses_[0-7][0-9A-HJKMNP-TV-Z]{25}$")
JTI_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
TOKEN_CLAIMS = (
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
)
TOKEN_TTL_S = 300
PRIVATE_JWK_MEMBERS = ("d", "p", "q", "dp", "dq", "qi", "oth", "k")

# spec 03 3.4 step 7: in these phases, no cue for 1200 ms makes the server emit a holding cue.
WATCHED_PHASES = ("framing", "action", "listening")
SILENCE_MS = 1200
FRAMING_CAP_MS = 15000  # spec 01 1.6
LONGEST_CUE_MS = 4000  # spec 01 1.10
# How late a turn that falls due may start: after the longest cue and the longest pause.
TURN_SLACK_MS = LONGEST_CUE_MS + SILENCE_MS
STREAMING_PING_MS = 1000  # spec 01 1.1: a server ping every 1 s while media streams


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def ok(self) -> None:
        self.checks += 1

    def fail(self, msg: str) -> None:
        self.checks += 1
        self.failures.append(msg)

    def expect(self, cond: bool, msg: str) -> None:
        if cond:
            self.ok()
        else:
            self.fail(msg)


def load_schemas(root: Path) -> tuple[dict[str, dict], Registry]:
    schemas: dict[str, dict] = {}
    for p in sorted((root / "schemas" / "v1").rglob("*.schema.json")):
        schemas[p.relative_to(root / "schemas" / "v1").as_posix()] = json.loads(
            p.read_text(encoding="ascii")
        )
    registry = Registry().with_resources(
        [(s["$id"], Resource.from_contents(s)) for s in schemas.values()]
    )
    return schemas, registry


def validator(schemas: dict[str, dict], registry: Registry, rel: str) -> Validator:
    return Draft202012Validator(schemas[rel], registry=registry)


def check_schemas(root: Path, schemas: dict, registry: Registry, rep: Report) -> None:
    for rel, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
            rep.expect(
                schema.get("$id") == SCHEMA_BASE + rel,
                "schema %s: $id does not match its path" % rel,
            )
        except Exception as exc:  # noqa: BLE001
            rep.fail("schema %s is not a valid 2020-12 schema: %s" % (rel, exc))


def load_keys(root: Path, rep: Report) -> dict:
    """The public JWKS of the vectors' test key (spec 01 1.12, D89): P-256 keys whose kid names them
    test keys, and no private member."""
    path = root / "vectors" / "keys" / "jwks.json"
    try:
        keys = json.loads(path.read_text(encoding="ascii"))
    except (OSError, ValueError) as exc:
        rep.fail("keys/jwks.json unreadable: %s" % exc)
        return {"keys": []}
    entries = keys.get("keys") if isinstance(keys, dict) else None
    rep.expect(
        isinstance(entries, list) and bool(entries), "keys/jwks.json has no keys"
    )
    for k in entries or []:
        kid = k.get("kid", "")
        rep.expect(
            k.get("kty") == "EC"
            and k.get("crv") == "P-256"
            and k.get("alg") == "ES256",
            "keys/jwks.json key %s is not an ES256 P-256 key" % kid,
        )
        rep.expect(
            "test" in kid, "keys/jwks.json kid %r does not name a test key" % kid
        )
        leaked = [m for m in PRIVATE_JWK_MEMBERS if m in k]
        rep.expect(
            not leaked,
            "keys/jwks.json key %s carries private members %s" % (kid, leaked),
        )
    return keys if isinstance(keys, dict) else {"keys": []}


def check_token(
    label: str,
    token: str,
    keys: dict,
    rep: Report,
    sub: str | None = None,
    jti: str | None = None,
    nonce: str | None = None,
) -> None:
    """A vector token: an ES256 JWS that verifies against keys/jwks.json and carries the claims of
    spec 02 2.2, with exp 300 s after iat; sub, jti and nonce equal the given values when given."""
    try:
        claims = jws.verify(token, keys)
    except jws.TokenError as exc:
        rep.fail("%s: token does not verify against keys/jwks.json: %s" % (label, exc))
        return
    rep.ok()
    missing = [c for c in TOKEN_CLAIMS if c not in claims]
    rep.expect(not missing, "%s: token lacks the claims %s" % (label, missing))
    rep.expect(claims.get("aud") == "ingest", "%s: token aud is not ingest" % label)
    iat, nbf, exp = claims.get("iat"), claims.get("nbf"), claims.get("exp")
    rep.expect(
        isinstance(iat, int)
        and isinstance(nbf, int)
        and isinstance(exp, int)
        and exp == iat + TOKEN_TTL_S
        and iat <= nbf < exp,
        "%s: token exp is not iat + %d s with nbf between them" % (label, TOKEN_TTL_S),
    )
    rep.expect(
        isinstance(claims.get("sub"), str) and bool(SESSION_ID_RE.match(claims["sub"])),
        "%s: token sub is not ses_ and a ULID" % label,
    )
    token_jti = claims.get("jti")
    rep.expect(
        isinstance(token_jti, str)
        and bool(JTI_RE.match(token_jti))
        and len(b64url_decode(token_jti)) == 16,
        "%s: token jti is not 16 bytes of base64url without padding" % label,
    )
    rep.expect(
        isinstance(claims.get("nonce"), str) and _decodes_to_16(claims["nonce"]),
        "%s: token nonce is not 16 bytes of base64" % label,
    )
    rep.expect(
        claims.get("band_max") in ("A", "B", "C"),
        "%s: token band_max is not A, B or C" % label,
    )
    ing = claims.get("ing")
    rep.expect(
        isinstance(ing, list) and bool(ing) and all(isinstance(r, str) for r in ing),
        "%s: token ing is not a list of regions" % label,
    )
    for claim, want in (("sub", sub), ("jti", jti), ("nonce", nonce)):
        if want is not None:
            rep.expect(
                claims.get(claim) == want,
                "%s: token %s %r differs from %r"
                % (label, claim, claims.get(claim), want),
            )


def _decodes_to_16(value: str) -> bool:
    try:
        return len(b64_decode(value)) == 16
    except ValueError:
        return False


def request_hash(session_id: str, attest_nonce: str) -> str:
    """spec 01 1.4: SHA-256 over the session id's UTF-8 bytes then the 16 raw bytes of attest_nonce."""
    return hashlib.sha256(
        session_id.encode("utf-8") + b64_decode(attest_nonce)
    ).hexdigest()


def check_attestation(
    label: str, msg: dict, session_id: str, attest_nonce: str, rep: Report
) -> None:
    """An attestation carries the request_hash of the session and its attest_nonce; an App Attest
    token is base64url JSON whose client_data_hash repeats it, with one of attestation or assertion."""
    try:
        want = request_hash(session_id, attest_nonce)
    except ValueError:
        rep.fail("%s: attest_nonce %r is not base64" % (label, attest_nonce))
        return
    rep.expect(
        msg.get("request_hash") == want,
        "%s: request_hash is not SHA-256 of the session id and attest_nonce" % label,
    )
    if msg.get("kind") != "app_attest":
        return
    try:
        token = json.loads(b64url_decode(msg["token"]))
    except (KeyError, ValueError, UnicodeDecodeError):
        rep.fail("%s: the App Attest token is not base64url JSON" % label)
        return
    rep.expect(
        isinstance(token, dict) and token.get("client_data_hash") == want,
        "%s: the App Attest client_data_hash differs from request_hash" % label,
    )
    rep.expect(
        isinstance(token, dict)
        and isinstance(token.get("key_id"), str)
        and ("attestation" in token) != ("assertion" in token),
        "%s: the App Attest token needs key_id and exactly one of attestation or assertion"
        % label,
    )


def check_messages(
    root: Path, schemas: dict, registry: Registry, keys: dict, rep: Report
) -> None:
    base = root / "vectors" / "messages"
    # The vectors' session, which every hello token and attestation example belongs to.
    try:
        ready = json.loads(
            (base / "server" / "ready" / "valid.json").read_text(encoding="ascii")
        )
        session_id, attest_nonce = ready["session_id"], ready["attest_nonce"]
    except (OSError, ValueError, KeyError) as exc:
        rep.fail("messages/server/ready/valid.json unreadable: %s" % exc)
        return
    rep.expect(
        bool(SESSION_ID_RE.match(session_id)),
        "messages/server/ready/valid.json: session_id is not ses_ and a ULID",
    )
    for direction in ("client", "server"):
        agg = validator(schemas, registry, direction + ".schema.json")
        for tdir in sorted((base / direction).iterdir()):
            if not tdir.is_dir():
                continue
            per_type = validator(
                schemas, registry, "%s/%s.schema.json" % (direction, tdir.name)
            )
            for f in sorted(tdir.glob("*.json")):
                inst = json.loads(f.read_text(encoding="ascii"))
                errors = list(per_type.iter_errors(inst))
                agg_errors = list(agg.iter_errors(inst))
                label = f.relative_to(base).as_posix()
                if f.name.startswith("valid"):
                    rep.expect(
                        not errors,
                        "%s should be valid: %s"
                        % (label, errors[0].message if errors else ""),
                    )
                    rep.expect(
                        not agg_errors,
                        "%s should validate against the %s aggregate"
                        % (label, direction),
                    )
                    if tdir.name == "attestation":
                        check_attestation(label, inst, session_id, attest_nonce, rep)
                else:
                    rep.expect(
                        bool(errors),
                        "%s should be rejected by the per-type schema" % label,
                    )
                    rep.expect(
                        bool(agg_errors),
                        "%s should be rejected by the %s aggregate"
                        % (label, direction),
                    )
                if tdir.name == "hello" and isinstance(inst.get("token"), str):
                    check_token(
                        label,
                        inst["token"],
                        keys,
                        rep,
                        sub=session_id,
                        nonce=attest_nonce,
                    )


def check_framing(root: Path, schemas: dict, registry: Registry, rep: Report) -> None:
    d = root / "vectors" / "framing"
    vschema = validator(schemas, registry, "framing-vector.schema.json")
    for f in sorted(d.glob("*.json")):
        case = json.loads(f.read_text(encoding="ascii"))
        errs = list(vschema.iter_errors(case))
        rep.expect(
            not errs,
            "framing vector %s does not match its schema: %s"
            % (f.name, errs[0].message if errs else ""),
        )
        data = bytes.fromhex(case["hex"])
        if "expect" in case:
            exp = case["expect"]
            binf = d / (case["name"] + ".bin")
            rep.expect(
                binf.exists() and binf.read_bytes() == data,
                "framing %s: .bin missing or differs from hex" % case["name"],
            )
            try:
                h = decode_header(data)
            except FramingError as exc:
                rep.fail("framing %s: unexpected error %s" % (case["name"], exc.code))
                continue
            rep.expect(
                h.as_dict() == exp["header"],
                "framing %s: decoded header differs" % case["name"],
            )
            rep.expect(
                data[8:].hex() == exp["payload_hex"],
                "framing %s: payload differs" % case["name"],
            )
            rep.expect(
                encode_header(Header(**exp["header"])) == data[:8],
                "framing %s: re-encoded header differs" % case["name"],
            )
            if h.type == 2:
                rep.expect(
                    parse_probe_payload(data[8:]) == exp.get("probe_send_time_us"),
                    "framing %s: probe send time differs" % case["name"],
                )
            if h.type == 3:
                got = [
                    {"pts_delta_ms": dlt, "packet_hex": p.hex()}
                    for dlt, p in parse_audio_batch(data[8:])
                ]
                rep.expect(
                    got == exp.get("audio_batch"),
                    "framing %s: audio batch records differ" % case["name"],
                )
        else:
            code = None
            try:
                h = decode_header(data)
                if h.type == 2:
                    parse_probe_payload(data[8:])
                elif h.type == 3:
                    parse_audio_batch(data[8:])
            except FramingError as exc:
                code = exc.code
            rep.expect(
                code == case["error"],
                "framing %s: expected error %s, got %s"
                % (case["name"], case["error"], code),
            )


def check_chain(
    root: Path, schemas: dict, registry: Registry, keys: dict, rep: Report
) -> None:
    vschema = validator(schemas, registry, "chain-vector.schema.json")
    for f in sorted((root / "vectors" / "chain").glob("*.json")):
        case = json.loads(f.read_text(encoding="ascii"))
        errs = list(vschema.iter_errors(case))
        rep.expect(
            not errs,
            "chain vector %s does not match its schema: %s"
            % (f.name, errs[0].message if errs else ""),
        )
        rep.expect(
            bool(SESSION_ID_RE.match(case["session_id"])),
            "chain %s: session_id is not ses_ and a ULID" % case["name"],
        )
        jti = b64url_decode(case["jti"])
        try:
            rep.expect(
                jti_bytes_from_token(case["token"]) == jti,
                "chain %s: token jti differs from jti field" % case["name"],
            )
        except ChainError as exc:
            rep.fail("chain %s: token unreadable: %s" % (case["name"], exc))
        check_token(
            "chain " + case["name"],
            case["token"],
            keys,
            rep,
            sub=case["session_id"],
            jti=case["jti"],
        )
        rep.expect(
            h0(case["session_id"], jti).hex() == case["h0"],
            "chain %s: H0 differs" % case["name"],
        )
        chain = Chain(case["session_id"], jti)
        for i, m in enumerate(case["messages"]):
            chained = chain.feed(bytes.fromhex(m["hex"]))
            rep.expect(
                chained == m["chained"],
                "chain %s message %d: chained flag differs" % (case["name"], i),
            )
            rep.expect(
                chain.hex == m["chain_after"],
                "chain %s message %d: chain value differs" % (case["name"], i),
            )
        rep.expect(
            case["attest"]["chain"] == chain.hex,
            "chain %s: attest chain differs from final value" % case["name"],
        )


def _msg(row: dict, direction: str, t: str) -> dict | None:
    """The message of a transcript row when it goes in direction and its type is t."""
    m = row.get("msg")
    if m is not None and row["dir"] == direction and m.get("t") == t:
        return m
    return None


def _stops(row: dict) -> bool:
    """The row ends the dialogue: the server's end or error, the client's bye, or the close."""
    if "close" in row:
        return True
    m = row.get("msg") or {}
    if row["dir"] == "s2c":
        return m.get("t") in ("end", "error")
    return m.get("t") == "bye"


def _check_session(
    name: str, meta: dict, body: list[dict], keys: dict, rep: Report
) -> dict | None:
    """The transcript's session: meta session_id is ses_ and a ULID, ready carries it and ping p1
    follows ready at once, and every hello token names it (spec 01 1.1, 1.12, 02 2.2, 03 3.3)."""
    session_id = meta["session_id"]
    rep.expect(
        bool(SESSION_ID_RE.match(session_id)),
        "%s: meta session_id %s is not ses_ and a ULID" % (name, session_id),
    )
    ready = None
    for i, row in enumerate(body):
        m = _msg(row, "s2c", "ready")
        if m is None:
            continue
        ready = m
        rep.expect(
            m.get("session_id") == session_id,
            "%s: ready session_id differs from meta session_id" % name,
        )
        after = _msg(body[i + 1], "s2c", "ping") if i + 1 < len(body) else None
        rep.expect(
            after is not None and after.get("id") == "p1",
            "%s: ready is not followed at once by ping p1" % name,
        )
        break
    for row in body:
        m = _msg(row, "c2s", "hello")
        if m is not None and isinstance(m.get("token"), str):
            check_token(
                "%s hello" % name,
                m["token"],
                keys,
                rep,
                sub=session_id,
                jti=meta["jti"],
                nonce=ready.get("attest_nonce") if ready else None,
            )
        m = _msg(row, "c2s", "attestation")
        if m is not None and ready is not None:
            check_attestation(
                "%s attestation" % name, m, session_id, ready["attest_nonce"], rep
            )
    return ready


def _check_pairs(name: str, body: list[dict], rep: Report) -> None:
    """Every ping has exactly one pong, and every say exactly one audio_state started and one ended,
    in that order (spec 01 1.1, 1.5)."""
    pings: dict[tuple[str, str], int] = {}
    pongs: dict[tuple[str, str], int] = {}
    says: dict[str, int] = {}
    playback: dict[str, list[tuple[str, int]]] = {}
    for row in body:
        m = row.get("msg")
        if m is None:
            continue
        t = m.get("t")
        if t == "ping":
            pings[(row["dir"], m["id"])] = row["t_ms"]
        elif t == "pong":
            other = "s2c" if row["dir"] == "c2s" else "c2s"
            pongs[(other, m["re"])] = pongs.get((other, m["re"]), 0) + 1
        elif t == "say" and row["dir"] == "s2c":
            says[m["id"]] = row["t_ms"]
        elif t == "audio_state":
            playback.setdefault(m["re"], []).append((m["event"], row["t_ms"]))
    for (direction, ping_id), t_ms in sorted(pings.items(), key=lambda kv: kv[1]):
        rep.expect(
            pongs.get((direction, ping_id), 0) == 1,
            "%s: ping %s at t=%d has %d pongs, not one"
            % (name, ping_id, t_ms, pongs.get((direction, ping_id), 0)),
        )
    for say_id, t_ms in says.items():
        events = playback.get(say_id, [])
        rep.expect(
            [e for e, _ in events] == ["started", "ended"]
            and t_ms <= events[0][1] <= events[1][1],
            "%s: say %s is not bracketed by one audio_state started then one ended"
            % (name, say_id),
        )


def _check_silence(name: str, body: list[dict], rep: Report) -> None:
    """spec 03 3.4 step 7: while the phase is framing, action or listening, the server never leaves
    more than 1200 ms without a cue playing: from an audio_state ended (or the phase starting) to the
    next say, the phase leaving those three, or the end of the dialogue."""
    phase = None
    playing: set[str] = set()
    quiet_since: int | None = None
    for row in body:
        t = row["t_ms"]
        m = row.get("msg") or {}
        says = row["dir"] == "s2c" and m.get("t") == "say"
        leaves = (
            row["dir"] == "s2c"
            and m.get("t") == "ui"
            and m["state"].get("phase") not in WATCHED_PHASES
        )
        if (says or leaves or _stops(row)) and phase in WATCHED_PHASES:
            if not playing and quiet_since is not None:
                rep.expect(
                    t - quiet_since <= SILENCE_MS,
                    "%s: %d ms without a cue in phase %s before t=%d"
                    % (name, t - quiet_since, phase, t),
                )
        if _stops(row):
            return
        if says:
            playing.add(m["id"])
        elif row["dir"] == "c2s" and m.get("t") == "audio_state":
            if m["event"] in ("ended", "failed"):
                playing.discard(m["re"])
                if not playing:
                    quiet_since = t
        elif row["dir"] == "s2c" and m.get("t") == "ui":
            new = m["state"].get("phase")
            if new in WATCHED_PHASES and phase not in WATCHED_PHASES:
                quiet_since = t
            phase = new


def _is_coaching(cue: str) -> bool:
    """A lighting or framing coaching cue (spec 01 1.6, 1.10)."""
    return (
        cue.startswith("light.")
        or (cue.startswith("frame.") and cue != "frame.perfect")
        or cue == "a11y.framing_adjust"
    )


def _check_framing_cap(name: str, body: list[dict], rep: Report) -> None:
    """spec 01 1.6: FRAMING, from probe_result, is capped at 15 s; past the cap a lighting or framing
    coaching turn follows, and 15 s after the cap the server ends with attempts_exhausted, aborted
    and retry true (D90), unless a challenge began first."""
    start = next(
        (row["t_ms"] for row in body if _msg(row, "s2c", "probe_result")), None
    )
    if start is None:
        return
    cap = start + FRAMING_CAP_MS
    stop = body[-1]
    for row in body:
        if row["t_ms"] < start:
            continue
        m = row.get("msg") or {}
        if _stops(row) or (
            row["dir"] == "s2c"
            and (
                m.get("t") == "action"
                or (m.get("t") == "ui" and m["state"].get("phase") != "framing")
            )
        ):
            stop = row
            break
    end = _msg(stop, "s2c", "end")
    if end is not None and end["reason"] == "attempts_exhausted":
        rep.expect(
            stop["t_ms"] >= cap + FRAMING_CAP_MS,
            "%s: attempts_exhausted at t=%d, before 15 s past FRAMING's cap"
            % (name, stop["t_ms"]),
        )
    if stop["t_ms"] <= cap:
        return
    coaching = [
        row["t_ms"]
        for row in body
        if cap <= row["t_ms"] < stop["t_ms"]
        and (m := _msg(row, "s2c", "say")) is not None
        and _is_coaching(m["cue"])
    ]
    rep.expect(
        bool(coaching) and coaching[0] <= cap + TURN_SLACK_MS,
        "%s: FRAMING passes its 15 s cap at t=%d without a coaching turn" % (name, cap),
    )
    rep.expect(
        stop["t_ms"] <= cap + FRAMING_CAP_MS + TURN_SLACK_MS,
        "%s: FRAMING runs until t=%d, past its cap and 15 s more"
        % (name, stop["t_ms"]),
    )
    if end is not None and stop["t_ms"] >= cap + FRAMING_CAP_MS:
        rep.expect(
            (end["outcome"], end["reason"], end["retry"])
            == ("aborted", "attempts_exhausted", True),
            "%s: FRAMING past its cap ends with %s %s, not aborted attempts_exhausted retry true"
            % (name, end["outcome"], end["reason"]),
        )


def _within(value: float, target: float, tolerance: float) -> bool:
    return abs(value - target) <= tolerance


def _check_cadence(
    name: str,
    what: str,
    times: list[int],
    span: tuple[int, int],
    every: int,
    tol: float,
    rep: Report,
) -> None:
    """Events at a fixed cadence across span: the first within one interval of its start, each gap
    one interval, the last within one interval of its end (tolerance tol)."""
    if not times:
        rep.fail("%s: no %s while media streams" % (name, what))
        return
    gaps = [b - a for a, b in zip([span[0]] + times, times + [span[1]])]
    inner = gaps[1:-1]
    rep.expect(
        gaps[0] <= every + tol
        and gaps[-1] <= every + tol
        and all(_within(g, every, tol) for g in inner),
        "%s: %s do not hold their %d ms cadence while media streams"
        % (name, what, every),
    )


def _check_continuous(
    name: str, meta: dict, body: list[dict], ready: dict | None, rep: Report
) -> None:
    """A transcript with continuous media (meta.expect.media is continuous): every video and audio
    message from config to the end, server pings every 1 s, stats every stats_interval_ms and attest
    every attest_interval_ms of video pts (spec 01 1.1, 1.4), each attest's seqs and chain those of
    the media before it, with the zero-filled payloads of chain.summary_message."""
    if ready is None:
        rep.fail("%s: continuous media without ready" % name)
        return
    stop = next((i for i, row in enumerate(body) if _stops(row)), len(body) - 1)
    end_t = body[stop]["t_ms"]
    fps = 0.0
    frame_ms = 20.0
    config_t = None
    last: dict[int, dict] = {}
    last_t: dict[int, int] = {}
    video: list[dict] = []
    ok = True
    for row in body[:stop]:
        m = _msg(row, "c2s", "config")
        if m is not None:
            fps, frame_ms = m["video"]["fps"], m["audio"].get("frame_ms", 20)
            config_t = row["t_ms"] if config_t is None else config_t
        md = row.get("media")
        if md is None or md["type"] == 2 or not fps:
            continue
        track = 0 if md["type"] == 0 else 1
        prev = last.get(track)
        step = 1000 / fps if track == 0 else frame_ms
        if prev is not None:
            ok &= md["seq"] == (prev["seq"] + 1) & 0xFFFF
            if md["type"] != 3:
                ok &= _within(md["pts_ms"] - prev["pts_ms"], step, 1)
        last[track] = md
        last_t[track] = row["t_ms"]
        if track == 0:
            video.append(row)
    rep.expect(
        ok and 0 in last and 1 in last,
        "%s: video and audio are not continuous in seq and pts" % name,
    )
    if not video or not fps or config_t is None or 1 not in last_t:
        return
    frame = 1000 / fps
    span = (video[0]["t_ms"], end_t)
    rep.expect(
        video[0]["t_ms"] - config_t <= frame + 1
        and end_t - last_t[0] <= frame + 1
        and end_t - last_t[1] <= frame_ms + 1,
        "%s: media does not stream from config to the end at t=%d" % (name, end_t),
    )
    streaming = [row for row in body[:stop] if span[0] <= row["t_ms"]]
    _check_cadence(
        name,
        "server pings",
        [row["t_ms"] for row in streaming if _msg(row, "s2c", "ping")],
        span,
        STREAMING_PING_MS,
        STREAMING_PING_MS / 10,
        rep,
    )
    stats_every = ready["stats_interval_ms"]
    _check_cadence(
        name,
        "stats",
        [row["t_ms"] for row in streaming if _msg(row, "c2s", "stats")],
        span,
        stats_every,
        stats_every / 10,
        rep,
    )
    pts_of = {row["media"]["seq"]: row["media"]["pts_ms"] for row in video}
    attest_pts = [
        pts_of.get(m["video_seq"], -1)
        for row in streaming
        if (m := _msg(row, "c2s", "attest")) is not None
    ]
    _check_cadence(
        name,
        "attest (in video pts)",
        attest_pts,
        (video[0]["media"]["pts_ms"], video[-1]["media"]["pts_ms"]),
        ready["attest_interval_ms"],
        frame + 1,
        rep,
    )
    chain = Chain(meta["session_id"], b64url_decode(meta["jti"]))
    seqs: dict[int, int] = {}
    for row in body:
        md = row.get("media")
        if md is not None and md["type"] != 2:
            chain.feed(summary_message(md))
            seqs[0 if md["type"] == 0 else 1] = md["seq"]
        m = _msg(row, "c2s", "attest")
        if m is not None:
            rep.expect(
                (m["video_seq"], m["audio_seq"], m["chain"])
                == (seqs.get(0), seqs.get(1), chain.hex),
                "%s: attest at t=%d is not the seqs and chain of the media before it"
                % (name, row["t_ms"]),
            )


def check_transcripts(
    root: Path, schemas: dict, registry: Registry, keys: dict, rep: Report
) -> None:
    line_schema = validator(schemas, registry, "transcript-line.schema.json")
    aggs = {
        "c2s": validator(schemas, registry, "client.schema.json"),
        "s2c": validator(schemas, registry, "server.schema.json"),
    }
    for f in sorted((root / "vectors" / "sessions").glob("*.jsonl")):
        name = f.name
        lines = [
            json.loads(row)
            for row in f.read_text(encoding="ascii").splitlines()
            if row.strip()
        ]
        rep.expect(
            bool(lines) and "meta" in lines[0], "%s: first line must be meta" % name
        )
        for i, line in enumerate(lines):
            errs = list(line_schema.iter_errors(line))
            rep.expect(
                not errs, "%s line %d: %s" % (name, i, errs[0].message if errs else "")
            )
            if "msg" in line:
                errs = list(aggs[line["dir"]].iter_errors(line["msg"]))
                rep.expect(
                    not errs,
                    "%s line %d (%s %s): %s"
                    % (
                        name,
                        i,
                        line["dir"],
                        line["msg"].get("t"),
                        errs[0].message if errs else "",
                    ),
                )
        body = [row for row in lines[1:] if "meta" not in row]
        if not body:
            continue
        meta = lines[0]["meta"]
        expect = meta.get("expect", {})
        # ordering and pairing rules
        t_prev = -1
        for i, row in enumerate(body):
            rep.expect(
                row["t_ms"] >= t_prev, "%s: t_ms decreases at body line %d" % (name, i)
            )
            t_prev = row["t_ms"]
        first = body[0]
        rep.expect(
            "msg" in first and first["dir"] == "c2s" and first["msg"]["t"] == "hello",
            "%s: first message must be hello" % name,
        )
        s2c_msgs = [row["msg"] for row in body if row["dir"] == "s2c" and "msg" in row]
        rep.expect(
            bool(s2c_msgs) and s2c_msgs[0]["t"] in ("ready", "error"),
            "%s: first server message must be ready or error" % name,
        )
        pings: dict[str, set[str]] = {"c2s": set(), "s2c": set()}
        says: set[str] = set()
        action_ids: set[str] = set()
        config_seen = False
        last_rung_msg: dict | None = None
        tile_times: list[int] = []
        for i, row in enumerate(body):
            if "msg" in row:
                m, d = row["msg"], row["dir"]
                t = m["t"]
                if t == "ping":
                    pings[d].add(m["id"])
                elif t == "pong":
                    other = "s2c" if d == "c2s" else "c2s"
                    rep.expect(
                        m["re"] in pings[other],
                        "%s: pong %s answers no earlier ping" % (name, m["re"]),
                    )
                elif t == "say":
                    rep.expect(
                        m["id"] not in says, "%s: duplicate say id %s" % (name, m["id"])
                    )
                    says.add(m["id"])
                elif t == "audio_state":
                    rep.expect(
                        m["re"] in says,
                        "%s: audio_state refers to unknown say %s" % (name, m["re"]),
                    )
                elif t == "action":
                    rep.expect(
                        m["id"] not in action_ids,
                        "%s: duplicate action id %s" % (name, m["id"]),
                    )
                    action_ids.add(m["id"])
                    if "say" in m:
                        rep.expect(
                            m["say"] in says,
                            "%s: action %s links unknown say %s"
                            % (name, m["id"], m["say"]),
                        )
                elif t == "config":
                    config_seen = True
                elif t == "rung":
                    last_rung_msg = m
                elif t == "tile":
                    tile_times.append(row["t_ms"])
                    recent = [x for x in tile_times if row["t_ms"] - x < 1000]
                    rep.expect(
                        len(recent) <= 3,
                        "%s: more than three tile changes within one second at t=%d"
                        % (name, row["t_ms"]),
                    )
                elif t == "end" and m["reason"] == "attempts_exhausted":
                    rep.expect(
                        m["outcome"] == "aborted" and m["retry"] is True,
                        "%s: attempts_exhausted must end aborted with retry true (D90)"
                        % name,
                    )
            elif "media" in row:
                md = row["media"]
                if md["type"] in (0, 1, 3) and expect.get("error") != "protocol":
                    rep.expect(
                        config_seen,
                        "%s: media before config at t=%d" % (name, row["t_ms"]),
                    )
                if md["type"] == 2:
                    rep.expect(
                        md["rung"] == 0 and md["pts_ms"] == 0,
                        "%s: probe at t=%d is not summarised at rung 0 and pts 0 (G1)"
                        % (name, row["t_ms"]),
                    )
                if md.get("rung_changed"):
                    rep.expect(
                        last_rung_msg is not None
                        and last_rung_msg["rung"] == md["rung"],
                        "%s: rung_changed media at t=%d without a matching rung message"
                        % (name, row["t_ms"]),
                    )
        last = body[-1]
        rep.expect("close" in last, "%s: last line must be a close" % name)
        if "close" in last:
            code = last["close"]["code"]
            rep.expect(
                expect.get("close") == code,
                "%s: close code %d differs from meta.expect.close" % (name, code),
            )
            prev_s2c = [
                row for row in body[:-1] if row["dir"] == "s2c" and "msg" in row
            ]
            prev_t = prev_s2c[-1]["msg"]["t"] if prev_s2c else None
            if code in END_CLOSES:
                rep.expect(
                    prev_t == "end",
                    "%s: close %d must be preceded by end (got %s)"
                    % (name, code, prev_t),
                )
                if "end" in expect and prev_t == "end":
                    e = prev_s2c[-1]["msg"]
                    rep.expect(
                        all(e.get(k) == v for k, v in expect["end"].items()),
                        "%s: end differs from meta.expect.end" % name,
                    )
            elif code in ERROR_CLOSES:
                rep.expect(
                    prev_t == "error",
                    "%s: close %d must be preceded by error (got %s)"
                    % (name, code, prev_t),
                )
                if "error" in expect and prev_t == "error":
                    rep.expect(
                        prev_s2c[-1]["msg"]["code"] == expect["error"],
                        "%s: error code differs from meta.expect.error" % name,
                    )
        ready = _check_session(name, meta, body, keys, rep)
        _check_pairs(name, body, rep)
        _check_silence(name, body, rep)
        _check_framing_cap(name, body, rep)
        if expect.get("media") == "continuous":
            _check_continuous(name, meta, body, ready, rep)


def run_checks(root: Path) -> Report:
    rep = Report()
    schemas, registry = load_schemas(root)
    rep.expect(bool(schemas), "no schemas found under %s" % (root / "schemas" / "v1"))
    if not schemas:
        return rep
    keys = load_keys(root, rep)
    check_schemas(root, schemas, registry, rep)
    check_messages(root, schemas, registry, keys, rep)
    check_framing(root, schemas, registry, rep)
    check_chain(root, schemas, registry, keys, rep)
    check_transcripts(root, schemas, registry, keys, rep)
    return rep
