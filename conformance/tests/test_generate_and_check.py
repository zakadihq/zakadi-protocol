from pathlib import Path

from zakadi_conformance.check import run_checks
from zakadi_conformance.vectors import generate


def test_generated_vectors_pass_checks(tmp_path: Path):
    generate(tmp_path)
    rep = run_checks(tmp_path)
    assert rep.failures == []
    assert rep.checks > 300


def test_generation_is_deterministic(tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a)
    generate(b)
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel
