"""Conformance checks over the generated schemas and vectors."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator
from referencing import Registry, Resource

from . import SCHEMA_BASE
from .chain import Chain, ChainError, b64url_decode, h0, jti_bytes_from_token
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


def check_messages(root: Path, schemas: dict, registry: Registry, rep: Report) -> None:
    base = root / "vectors" / "messages"
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


def check_chain(root: Path, schemas: dict, registry: Registry, rep: Report) -> None:
    vschema = validator(schemas, registry, "chain-vector.schema.json")
    for f in sorted((root / "vectors" / "chain").glob("*.json")):
        case = json.loads(f.read_text(encoding="ascii"))
        errs = list(vschema.iter_errors(case))
        rep.expect(
            not errs,
            "chain vector %s does not match its schema: %s"
            % (f.name, errs[0].message if errs else ""),
        )
        jti = b64url_decode(case["jti"])
        try:
            rep.expect(
                jti_bytes_from_token(case["token"]) == jti,
                "chain %s: token jti differs from jti field" % case["name"],
            )
        except ChainError as exc:
            rep.fail("chain %s: token unreadable: %s" % (case["name"], exc))
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


def check_transcripts(
    root: Path, schemas: dict, registry: Registry, rep: Report
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
            elif "media" in row:
                md = row["media"]
                if md["type"] in (0, 1, 3) and expect.get("error") != "protocol":
                    rep.expect(
                        config_seen,
                        "%s: media before config at t=%d" % (name, row["t_ms"]),
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
                        e["outcome"] == expect["end"]["outcome"]
                        and e["reason"] == expect["end"]["reason"],
                        "%s: end outcome/reason differ from meta.expect.end" % name,
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


def run_checks(root: Path) -> Report:
    rep = Report()
    schemas, registry = load_schemas(root)
    rep.expect(bool(schemas), "no schemas found under %s" % (root / "schemas" / "v1"))
    if not schemas:
        return rep
    check_schemas(root, schemas, registry, rep)
    check_messages(root, schemas, registry, rep)
    check_framing(root, schemas, registry, rep)
    check_chain(root, schemas, registry, rep)
    check_transcripts(root, schemas, registry, rep)
    return rep
