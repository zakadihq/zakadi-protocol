import json
from pathlib import Path

from zakadi_conformance import jws
from zakadi_conformance.check import run_checks
from zakadi_conformance.cli import main
from zakadi_conformance.vectors import generate


def test_generated_vectors_pass_checks(tmp_path: Path):
    generate(tmp_path)
    rep = run_checks(tmp_path)
    assert rep.failures == []
    assert rep.checks > 8000
    assert main(["--root", str(tmp_path), "check"]) == 0


def test_generation_is_deterministic(tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert main(["--root", str(a), "generate"]) == 0
    assert main(["--root", str(b), "generate"]) == 0
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_only_the_public_key_leaves_conformance(tmp_path: Path):
    generate(tmp_path)
    keys = json.loads(
        (tmp_path / "vectors" / "keys" / "jwks.json").read_text(encoding="ascii")
    )
    assert keys == jws.jwks()
    secret = jws.load_private_jwk()["d"].encode("ascii")
    for path in tmp_path.rglob("*"):
        assert not path.is_file() or secret not in path.read_bytes(), path
