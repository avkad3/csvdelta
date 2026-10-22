"""Command-line interface: ``csvdelta OLD NEW --key id``."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from . import __version__
from .core import CsvDeltaError, diff_files
from .render import FORMATS, render

EXIT_SAME, EXIT_DIFF, EXIT_ERROR = 0, 1, 2


def _split(values: list[str]) -> list[str]:
    return [part.strip() for v in values for part in v.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="csvdelta",
        description="Diff two CSV snapshots by key column(s). "
        "Exit status: 0 = identical, 1 = differences, 2 = error.",
    )
    p.add_argument("old", help="the earlier CSV file")
    p.add_argument("new", help="the later CSV file")
    p.add_argument(
        "-k", "--key", action="append", required=True,
        help="key column; repeat or comma-separate for a composite key",
    )
    p.add_argument(
        "-i", "--ignore", action="append", default=[],
        help="column to ignore when comparing; repeat or comma-separate",
    )
    p.add_argument("-f", "--format", choices=FORMATS, default="text")
    p.add_argument("-d", "--delimiter", default=",", help="field delimiter (default ',')")
    p.add_argument("--strip", action="store_true", help="trim whitespace around values")
    p.add_argument("--ignore-case", action="store_true", help="compare values case-insensitively")
    p.add_argument(
        "--tolerance", type=float, default=None, metavar="N",
        help="treat numeric values within N of each other as equal",
    )
    p.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colours in text output")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    delimiter = "\t" if args.delimiter in ("\\t", "tab") else args.delimiter
    try:
        result = diff_files(
            args.old,
            args.new,
            _split(args.key),
            delimiter=delimiter,
            strip=args.strip,
            ignore_case=args.ignore_case,
            ignore_columns=_split(args.ignore),
            numeric_tolerance=args.tolerance,
        )
    except (CsvDeltaError, OSError) as exc:
        print(f"csvdelta: error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    color = (
        args.format == "text" and not args.output and not args.no_color
        and sys.stdout.isatty() and "NO_COLOR" not in os.environ
    )
    report = render(result, args.format, color=color)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
    else:
        # Legacy Windows code pages can't encode every value; don't crash on them.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")
        print(report)
    return EXIT_DIFF if result.has_changes else EXIT_SAME


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
