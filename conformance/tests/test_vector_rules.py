"""The checker fails a generated tree that breaks a rule of the vectors (spec 01-protocol.md 1.1, 1.4,
1.6, 1.12, 02-api.md 2.2, 03-backend-services.md 3.3, 3.4)."""

import json
import shutil
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from zakadi_conformance import jws
from zakadi_conformance.chain import b64url_decode, b64url_encode
from zakadi_conformance.check import SESSION_ID_RE, run_checks
from zakadi_conformance.cli import main
from zakadi_conformance.vectors import generate

OTHER_SESSION_ID = "ses_01K5RMQ2G0VECT0R0000000002"


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("generated")
    generate(root)
    return root


@pytest.fixture
def tree(generated: Path, tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(generated, root)
    return root


def transcript(root: Path, name: str) -> Path:
    return root / "vectors" / "sessions" / (name + ".jsonl")


def rows(path: Path) -> list[dict]:
    return [json.loads(r) for r in path.read_text(encoding="ascii").splitlines() if r]


def write(path: Path, lines: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="ascii")


def edit(path: Path, change) -> None:
    """Applies change, which edits the transcript's lines in place, and writes them back."""
    lines = rows(path)
    change(lines)
    write(path, lines)


def failures(root: Path) -> list[str]:
    return run_checks(root).failures


def fails_with(root: Path, text: str) -> None:
    found = failures(root)
    assert any(text in f for f in found), found


def index(lines: list[dict], t: str, **fields) -> int:
    """The index of the first message of type t whose fields match."""
    return next(
        i
        for i, r in enumerate(lines)
        if r.get("msg", {}).get("t") == t
        and all(r["msg"].get(k) == v for k, v in fields.items())
    )


def test_every_transcript_session_is_ses_and_a_ulid_that_ready_carries(generated):
    for path in sorted((generated / "vectors" / "sessions").glob("*.jsonl")):
        lines = rows(path)
        session_id = lines[0]["meta"]["session_id"]
        assert SESSION_ID_RE.match(session_id) and len(session_id) == 30
        assert session_id[4] in "01234567"
        ready = [r["msg"] for r in lines if r.get("msg", {}).get("t") == "ready"]
        assert all(m["session_id"] == session_id for m in ready)


@pytest.mark.parametrize(
    "session_id",
    ["ses_01J8VECTOR000000000001", "ses_81K5RMQ2G0VECT0R0000000001", "ses_01K5RMQ2G0"],
)
def test_a_session_id_that_is_not_a_ulid_fails(tree, session_id):
    path = transcript(tree, "user-cancel")
    edit(path, lambda lines: lines[0]["meta"].update(session_id=session_id))
    fails_with(
        tree,
        "user-cancel.jsonl: meta session_id %s is not ses_ and a ULID" % session_id,
    )


def test_a_ready_naming_another_session_fails(tree):
    path = transcript(tree, "happy-two-actions")
    edit(
        path,
        lambda lines: lines[index(lines, "ready")]["msg"].update(
            session_id=OTHER_SESSION_ID
        ),
    )
    fails_with(
        tree, "happy-two-actions.jsonl: ready session_id differs from meta session_id"
    )


def claims(token: str) -> dict:
    return json.loads(b64url_decode(token.split(".")[1]))


def other_key(token: str) -> str:
    return jws.sign(
        claims(token),
        key=ec.generate_private_key(ec.SECP256R1()),
        kid=jws.load_private_jwk()["kid"],
    )


def other_sub(token: str) -> str:
    return jws.sign(claims(token) | {"sub": OTHER_SESSION_ID})


def swap_token(root: Path, where: str, make) -> str:
    """Replaces the token of one vector and returns the label its failures carry."""
    if where == "transcript":
        path = transcript(root, "happy-two-actions")
        edit(
            path,
            lambda lines: lines[1]["msg"].update(token=make(lines[1]["msg"]["token"])),
        )
        return "happy-two-actions.jsonl hello: token"
    rel = {"message": "messages/client/hello/valid.json", "chain": "chain/basic.json"}[
        where
    ]
    path = root / "vectors" / rel
    data = json.loads(path.read_text(encoding="ascii"))
    data["token"] = make(data["token"])
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return {"message": "client/hello/valid.json: token", "chain": "chain basic: token"}[
        where
    ]


@pytest.mark.parametrize("where", ["transcript", "message", "chain"])
def test_a_token_signed_by_another_key_fails(tree, where):
    label = swap_token(tree, where, other_key)
    fails_with(tree, label + " does not verify against keys/jwks.json")
    assert main(["--root", str(tree), "check"]) == 1


@pytest.mark.parametrize("where", ["transcript", "message", "chain"])
def test_a_token_naming_another_sub_fails(tree, where):
    label = swap_token(tree, where, other_sub)
    fails_with(tree, label + " sub '%s' differs" % OTHER_SESSION_ID)
    assert main(["--root", str(tree), "check"]) == 1


def test_a_token_whose_jti_or_nonce_differs_from_the_transcript_fails(tree):
    path = transcript(tree, "digits-retry")
    edit(path, lambda lines: lines[0]["meta"].update(jti="AAECAwQFBgcICQoLDA0OEA"))
    edit(
        path,
        lambda lines: lines[index(lines, "ready")]["msg"].update(
            attest_nonce="AAAAAAAAAAAAAAAAAAAAAA"
        ),
    )
    fails_with(tree, "digits-retry.jsonl hello: token jti")
    fails_with(tree, "digits-retry.jsonl hello: token nonce")


def test_a_jwks_with_a_private_member_or_without_a_test_kid_fails(tree):
    path = tree / "vectors" / "keys" / "jwks.json"
    keys = json.loads(path.read_text(encoding="ascii"))
    keys["keys"][0]["d"] = jws.load_private_jwk()["d"]
    keys["keys"][0]["kid"] = "zakadi-2026"
    path.write_text(json.dumps(keys), encoding="ascii")
    fails_with(tree, "carries private members ['d']")
    fails_with(tree, "does not name a test key")


def test_a_ready_without_ping_p1_right_after_it_fails(tree):
    path = transcript(tree, "floor-breached")

    def move_ping(lines):
        ping = lines.pop(index(lines, "ping", id="p1"))
        ping["t_ms"] = 160
        first_probe = next(i for i, r in enumerate(lines) if "media" in r)
        lines.insert(first_probe + 1, ping)

    edit(path, move_ping)
    fails_with(tree, "floor-breached.jsonl: ready is not followed at once by ping p1")


def test_a_ping_without_its_pong_fails(tree):
    path = transcript(tree, "framing-timeout")
    edit(path, lambda lines: lines.pop(index(lines, "pong", re="p7")))
    fails_with(tree, "framing-timeout.jsonl: ping p7 at t=6550 has 0 pongs, not one")


def test_a_say_without_one_started_and_one_ended_fails(tree):
    path = transcript(tree, "framing-timeout")
    edit(
        path,
        lambda lines: lines.pop(index(lines, "audio_state", re="s4", event="ended")),
    )
    fails_with(tree, "framing-timeout.jsonl: say s4 is not bracketed")


@pytest.mark.parametrize(
    "t,what",
    [("stats", "stats do not hold their 500 ms"), ("attest", "attest (in video pts)")],
)
def test_a_missing_stats_or_attest_breaks_the_cadence(tree, t, what):
    path = transcript(tree, "framing-timeout")

    def drop_one(lines):
        at = [i for i, r in enumerate(lines) if r.get("msg", {}).get("t") == t]
        lines.pop(at[len(at) // 2])

    edit(path, drop_one)
    fails_with(tree, "framing-timeout.jsonl: " + what)


def test_a_missing_server_ping_breaks_the_cadence(tree):
    path = transcript(tree, "framing-timeout")

    def drop_ping(lines):
        lines.pop(index(lines, "pong", re="p9"))
        lines.pop(index(lines, "ping", id="p9"))

    edit(path, drop_ping)
    fails_with(
        tree, "framing-timeout.jsonl: server pings do not hold their 1000 ms cadence"
    )


def test_a_gap_in_the_media_fails(tree):
    path = transcript(tree, "framing-timeout")

    def drop_frame(lines):
        at = [i for i, r in enumerate(lines) if r.get("media", {}).get("type") == 0]
        lines.pop(at[100])

    edit(path, drop_frame)
    fails_with(tree, "framing-timeout.jsonl: video and audio are not continuous")


def test_an_attest_chain_other_than_the_media_before_it_fails(tree):
    path = transcript(tree, "framing-timeout")

    def grow_frame(lines):
        at = [i for i, r in enumerate(lines) if r.get("media", {}).get("type") == 0]
        lines[at[40]]["media"]["bytes"] += 1

    edit(path, grow_frame)
    fails_with(
        tree, "framing-timeout.jsonl: attest at t=3540 is not the seqs and chain"
    )


def test_more_than_1200_ms_without_a_cue_fails(tree):
    path = transcript(tree, "happy-two-actions")

    def delay_ack(lines):
        for i in (index(lines, "say", id="s8"),) + tuple(
            index(lines, "audio_state", re="s8", event=e) for e in ("started", "ended")
        ):
            lines[i]["t_ms"] += 300
        lines.sort(key=lambda r: r.get("t_ms", -1))

    edit(path, delay_ack)
    fails_with(
        tree,
        "happy-two-actions.jsonl: 1300 ms without a cue in phase action before t=14600",
    )


def test_framing_past_its_cap_without_a_coaching_turn_fails(tree):
    path = transcript(tree, "framing-timeout")

    def no_coaching(lines):
        for r in lines:
            m = r.get("msg", {})
            if m.get("t") == "say" and r["t_ms"] > 15520:
                m["cue"] = "hold.moment"

    edit(path, no_coaching)
    fails_with(
        tree,
        "framing-timeout.jsonl: FRAMING passes its 15 s cap at t=15520 without a coaching turn",
    )


def test_framing_past_its_cap_ending_other_than_attempts_exhausted_fails(tree):
    path = transcript(tree, "framing-timeout")
    edit(
        path,
        lambda lines: lines[index(lines, "end")]["msg"].update(reason="max_duration"),
    )
    fails_with(tree, "not aborted attempts_exhausted retry true")


def test_attempts_exhausted_before_the_cap_and_15_s_more_fails(tree):
    path = transcript(tree, "floor-breached")

    def exhausted_early(lines):
        lines.pop(index(lines, "bye"))
        lines[index(lines, "end")]["msg"].update(reason="attempts_exhausted")

    edit(path, exhausted_early)
    fails_with(
        tree, "floor-breached.jsonl: attempts_exhausted at t=5700, before 15 s past"
    )


def test_attempts_exhausted_without_retry_fails(tree):
    path = transcript(tree, "framing-timeout")
    edit(path, lambda lines: lines[index(lines, "end")]["msg"].update(retry=False))
    fails_with(tree, "attempts_exhausted must end aborted with retry true (D90)")


def test_a_probe_summarised_off_rung_0_fails(tree):
    path = transcript(tree, "digits-retry")

    def rung_2(lines):
        probe = next(r for r in lines if r.get("media", {}).get("type") == 2)
        probe["media"]["rung"] = 2

    edit(path, rung_2)
    fails_with(
        tree,
        "digits-retry.jsonl: probe at t=150 is not summarised at rung 0 and pts 0 (G1)",
    )


def test_an_attestation_whose_hash_differs_fails(tree):
    base = tree / "vectors" / "messages" / "client" / "attestation"
    plain = json.loads((base / "valid.json").read_text(encoding="ascii"))
    plain["request_hash"] = "0" * 64
    (base / "valid.json").write_text(json.dumps(plain), encoding="ascii")
    app = json.loads((base / "valid-1.json").read_text(encoding="ascii"))
    inner = json.loads(b64url_decode(app["token"]))
    inner["client_data_hash"] = "0" * 64
    app["token"] = b64url_encode(json.dumps(inner).encode("ascii"))
    (base / "valid-1.json").write_text(json.dumps(app), encoding="ascii")
    fails_with(tree, "attestation/valid.json: request_hash is not SHA-256")
    fails_with(
        tree, "attestation/valid-1.json: the App Attest client_data_hash differs"
    )
