"""Core diffing logic: load CSV snapshots keyed by one or more columns and compare them."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

Row = dict[str, str]
Key = tuple[str, ...]


class CsvDeltaError(Exception):
    """Raised for user-facing problems such as missing key columns or duplicate keys."""


@dataclass(frozen=True)
class FieldChange:
    column: str
    old: str
    new: str


@dataclass(frozen=True)
class RowChange:
    key: Key
    changes: tuple[FieldChange, ...]


@dataclass
class DiffResult:
    key_columns: tuple[str, ...]
    added: list[Row] = field(default_factory=list)
    removed: list[Row] = field(default_factory=list)
    changed: list[RowChange] = field(default_factory=list)
    columns_added: list[str] = field(default_factory=list)
    columns_removed: list[str] = field(default_factory=list)
    unchanged_count: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added or self.removed or self.changed or self.columns_added or self.columns_removed
        )

    def summary(self) -> dict[str, int]:
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "changed": len(self.changed),
            "unchanged": self.unchanged_count,
            "columns_added": len(self.columns_added),
            "columns_removed": len(self.columns_removed),
        }


@dataclass
class Table:
    columns: list[str]
    rows: dict[Key, Row]


def load_table(
    source: str | Path | io.TextIOBase,
    key_columns: Sequence[str],
    *,
    delimiter: str = ",",
    strip: bool = False,
    ignore_case: bool = False,
) -> Table:
    """Read a CSV into a Table indexed by ``key_columns``.

    ``source`` may be a path or an open text stream.
    """
    if isinstance(source, (str, Path)):
        with open(source, newline="", encoding="utf-8-sig") as fh:
            return _read(fh, key_columns, delimiter, strip, ignore_case, str(source))
    return _read(source, key_columns, delimiter, strip, ignore_case, "<stream>")


def _read(
    fh: Iterable[str],
    key_columns: Sequence[str],
    delimiter: str,
    strip: bool,
    ignore_case: bool,
    name: str,
) -> Table:
    reader = csv.DictReader(fh, delimiter=delimiter)
    columns = list(reader.fieldnames or [])
    missing = [k for k in key_columns if k not in columns]
    if missing:
        raise CsvDeltaError(f"{name}: key column(s) not found: {', '.join(missing)}")

    rows: dict[Key, Row] = {}
    for line_no, raw in enumerate(reader, start=2):
        row = {c: _normalise(raw.get(c), strip, ignore_case) for c in columns}
        key = tuple(row[k] for k in key_columns)
        if key in rows:
            raise CsvDeltaError(f"{name}:{line_no}: duplicate key {_fmt_key(key)}")
        rows[key] = row
    return Table(columns, rows)


def _normalise(value: str | None, strip: bool, ignore_case: bool) -> str:
    value = value or ""
    if strip:
        value = value.strip()
    if ignore_case:
        value = value.casefold()
    return value


def _fmt_key(key: Key) -> str:
    return "/".join(key)


def diff_tables(
    old: Table,
    new: Table,
    key_columns: Sequence[str],
    *,
    ignore_columns: Iterable[str] = (),
    numeric_tolerance: float | None = None,
) -> DiffResult:
    """Compare two tables row-by-row on their shared, non-ignored columns."""
    ignored = set(ignore_columns)
    result = DiffResult(key_columns=tuple(key_columns))
    result.columns_added = [c for c in new.columns if c not in old.columns and c not in ignored]
    result.columns_removed = [c for c in old.columns if c not in new.columns and c not in ignored]
    compared = [c for c in old.columns if c in new.columns and c not in ignored]

    for key, row in new.rows.items():
        if key not in old.rows:
            result.added.append(row)
    for key, row in old.rows.items():
        if key not in new.rows:
            result.removed.append(row)
            continue
        changes = tuple(
            FieldChange(c, row[c], new.rows[key][c])
            for c in compared
            if not _equal(row[c], new.rows[key][c], numeric_tolerance)
        )
        if changes:
            result.changed.append(RowChange(key, changes))
        else:
            result.unchanged_count += 1
    return result


def _equal(a: str, b: str, tolerance: float | None) -> bool:
    if a == b:
        return True
    if tolerance is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tolerance
    except ValueError:
        return False


def diff_files(
    old_path: str | Path,
    new_path: str | Path,
    key_columns: Sequence[str],
    **options: object,
) -> DiffResult:
    """Convenience wrapper: load both files and diff them."""
    load_opts: Mapping[str, object] = {
        k: options.pop(k) for k in ("delimiter", "strip", "ignore_case") if k in options
    }
    old = load_table(old_path, key_columns, **load_opts)  # type: ignore[arg-type]
    new = load_table(new_path, key_columns, **load_opts)  # type: ignore[arg-type]
    return diff_tables(old, new, key_columns, **options)  # type: ignore[arg-type]
