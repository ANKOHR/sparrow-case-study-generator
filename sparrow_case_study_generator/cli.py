"""Local file CLI. All writes use atomic replacement."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from .core import SchemaError, compute
from .fixtures import expectations, fixture_data
from .report import json_text, render


class InputError(ValueError):
    """Named file parse or missing-input error."""


def load(path):
    try:
        encoded = path.read_bytes()
    except FileNotFoundError:
        raise InputError(f"MissingInput: {path}: use scsg fixtures --out DIR or create records.json")
    try:
        raw = encoded.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        line = encoded.count(b"\n", 0, exc.start) + 1
        raise InputError(f"ParseError: {path}: line {line}: invalid UTF-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}")
    # Scan valid JSON tokens to locate duplicate object keys at their actual line.
    # A string followed by a colon is an object key, never an array value.
    frames = []
    key_suffix = re.compile(r"\s*:")
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}\[\]]', raw):
        lexeme = token.group()
        if lexeme in ("{", "["):
            frames.append(set() if lexeme == "{" else None)
        elif lexeme in ("}", "]"):
            frames.pop()
        elif key_suffix.match(raw, token.end()):
            key = json.loads(lexeme)
            if key in frames[-1]:
                line = raw.count("\n", 0, token.start()) + 1
                raise InputError(f"ParseError: {path}: line {line}: duplicate JSON key {key}")
            frames[-1].add(key)
    return value


def read_input(directory):
    if not directory.is_dir():
        raise InputError(f"MissingInput: {directory}: use scsg fixtures --out DIR")
    files = sorted(directory.iterdir())
    if not files:
        return {"schema_version": 1, "synthetic": False, "as_of": "2026-09-30", "records": []}
    unexpected = [p.name for p in files if p.name not in ("records.json", "expectations.json")]
    if unexpected:
        raise InputError(f"SchemaError: {directory}: unsupported input files {unexpected}; use records.json")
    return load(directory / "records.json")


def atomic_write(path, content):
    temp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
            temp = Path(handle.name)
            handle.write(content)
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def parser():
    p = argparse.ArgumentParser(description="Convert explicit completed work into publishable evidence. Local files only.")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: scsg fixtures --out demo")
    f.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("run", help="Compute and save evidence results", epilog="Example: scsg run --input demo")
    r.add_argument("--input", type=Path, required=True)
    r.add_argument("--state", type=Path, default=Path(".scsg/results.json"))
    report = sub.add_parser("report", help="Render saved evidence with provenance", epilog="Example: scsg report --format md --out evidence.md")
    report.add_argument("--format", choices=("md", "json"), default="md")
    report.add_argument("--state", type=Path, default=Path(".scsg/results.json"))
    report.add_argument("--out", type=Path)
    audit = sub.add_parser("audit", help="Check eligibility and name exclusions without saving state", epilog="Example: scsg audit --input demo")
    audit.add_argument("--input", type=Path, required=True)
    case = sub.add_parser("case", help="Render one eligible case study with traced measurements", epilog="Example: scsg case --input demo --id 000-A")
    case.add_argument("--input", type=Path, required=True)
    case.add_argument("--id", required=True)
    case.add_argument("--format", choices=("md", "json"), default="md")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            if args.out.exists() and any(args.out.iterdir()):
                raise InputError(f"FixtureError: {args.out}: output directory must be empty")
            atomic_write(args.out / "records.json", json_text(fixture_data()))
            atomic_write(args.out / "expectations.json", json_text(expectations()))
            print("Created 200 SYNTHETIC records; all figures are illustrative.")
        elif args.command in ("run", "audit", "case"):
            data = read_input(args.input)
            try:
                result = compute(data)
            except SchemaError as exc:
                raise InputError(f"{args.input / 'records.json'}: {exc}")
            if args.command == "run":
                # Save validated source, not cached computed figures: report recomputes.
                atomic_write(args.state, json_text(data))
                print(render(result, "json"), end="")
            elif args.command == "audit":
                print(render(result, "json"), end="")
            else:
                if args.id not in [c["id"] for c in result["cases"]]:
                    raise InputError(f"CaseError: {args.id}: unknown or ineligible; use scsg audit --input DIR")
                one = dict(data, records=[r for r in data["records"] if r["id"] == args.id])
                print(render(compute(one), args.format), end="")
        else:
            try:
                output = render(compute(load(args.state)), args.format)
            except SchemaError as exc:
                raise InputError(f"{args.state}: {exc}")
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        return 0
    except (InputError, SchemaError, OSError, UnicodeError) as exc:
        name = "WriteOrReadError: " if isinstance(exc, (OSError, UnicodeError)) else ""
        print((name + str(exc)).replace(chr(8212), "-"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
