"""Output formats for a DiffResult: text, json and markdown."""

from __future__ import annotations

import json

from .core import DiffResult, Row

FORMATS = ("text", "json", "markdown")


def render(result: DiffResult, fmt: str = "text", *, color: bool = False) -> str:
    if fmt == "text":
        return render_text(result, color=color)
    if fmt == "json":
        return render_json(result)
    if fmt == "markdown":
        return render_markdown(result)
    raise ValueError(f"unknown format: {fmt!r} (choose from {', '.join(FORMATS)})")


def _key_of(result: DiffResult, row: Row) -> str:
    return "/".join(row[k] for k in result.key_columns)


def render_text(result: DiffResult, *, color: bool = False) -> str:
    def paint(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if color else s

    lines: list[str] = []
    for c in result.columns_added:
        lines.append(paint("32", f"+ column {c}"))
    for c in result.columns_removed:
        lines.append(paint("31", f"- column {c}"))
    for row in result.added:
        lines.append(paint("32", f"+ {_key_of(result, row)}"))
    for row in result.removed:
        lines.append(paint("31", f"- {_key_of(result, row)}"))
    for change in result.changed:
        lines.append(paint("33", f"~ {'/'.join(change.key)}"))
        for fc in change.changes:
            lines.append(f"    {fc.column}: {fc.old!r} -> {fc.new!r}")

    s = result.summary()
    lines.append(
        f"{s['added']} added, {s['removed']} removed, {s['changed']} changed, "
        f"{s['unchanged']} unchanged"
    )
    return "\n".join(lines)


def render_json(result: DiffResult) -> str:
    payload = {
        "key_columns": list(result.key_columns),
        "summary": result.summary(),
        "columns_added": result.columns_added,
        "columns_removed": result.columns_removed,
        "added": result.added,
        "removed": result.removed,
        "changed": [
            {
                "key": list(c.key),
                "changes": [{"column": f.column, "old": f.old, "new": f.new} for f in c.changes],
            }
            for c in result.changed
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _md(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def render_markdown(result: DiffResult) -> str:
    s = result.summary()
    out = [
        "## CSV diff",
        "",
        f"**{s['added']}** added | **{s['removed']}** removed | "
        f"**{s['changed']}** changed | {s['unchanged']} unchanged",
    ]
    if result.columns_added or result.columns_removed:
        out += ["", "### Schema"]
        out += [f"- added column `{c}`" for c in result.columns_added]
        out += [f"- removed column `{c}`" for c in result.columns_removed]
    if result.added:
        out += ["", "### Added", ""] + [f"- `{_md(_key_of(result, r))}`" for r in result.added]
    if result.removed:
        out += ["", "### Removed", ""] + [f"- `{_md(_key_of(result, r))}`" for r in result.removed]
    if result.changed:
        out += ["", "### Changed", "", "| Key | Column | Old | New |", "|---|---|---|---|"]
        for c in result.changed:
            for f in c.changes:
                out.append(
                    f"| {_md('/'.join(c.key))} | {_md(f.column)} | {_md(f.old)} | {_md(f.new)} |"
                )
    return "\n".join(out)
