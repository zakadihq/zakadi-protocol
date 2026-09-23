"""Command line: generate the vectors, or check them."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .check import run_checks
from .vectors import generate

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zakadi-conformance", description="Zakadi protocol conformance tools")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root holding schemas/ and vectors/")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate", help="regenerate schemas/ and vectors/ deterministically")
    sub.add_parser("check", help="validate schemas, message vectors, framing vectors, chain vectors and transcripts")
    args = parser.parse_args(argv)
    if args.command == "generate":
        generate(args.root)
        print("generated schemas and vectors under %s" % args.root)
        return 0
    rep = run_checks(args.root)
    for f in rep.failures:
        print("FAIL: " + f)
    print("%d checks, %d failures" % (rep.checks, len(rep.failures)))
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())
