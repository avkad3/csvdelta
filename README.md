# csvdelta

[![CI](https://github.com/avkad3/csvdelta/actions/workflows/ci.yml/badge.svg)](https://github.com/avkad3/csvdelta/actions/workflows/ci.yml)

Diff two CSV snapshots **by key**, not by line. `csvdelta` tells you which records were
added, which were removed, and exactly which fields changed in the rest. Row order and
column order don't matter.

It's built for recurring data exports such as competitor listings, product catalogues,
price sheets and CRM dumps, where you want to know *what changed since last time*.

- No dependencies outside the Python standard library (3.9+)
- Composite keys, ignored columns, numeric tolerance, whitespace and case normalisation
- Text, JSON and Markdown output (Markdown drops straight into a PR comment or Slack)
- Exits with a status you can script against: `0` identical, `1` differences, `2` error

## Install

```bash
pip install git+https://github.com/avkad3/csvdelta.git
```

Or from a clone:

```bash
git clone https://github.com/avkad3/csvdelta.git
cd csvdelta
pip install -e ".[dev]"
```

## Usage

```bash
csvdelta examples/shops_old.csv examples/shops_new.csv --key place_id
```

```text
+ column website
+ ChIJ005
- ChIJ003
~ ChIJ001
    rating: '4.5' -> '4.6'
    reviews: '812' -> '851'
    hours: '08:00-22:00' -> '08:00-23:00'
~ ChIJ002
    reviews: '340' -> '343'
1 added, 1 removed, 2 changed, 1 unchanged
```

To report only meaningful changes, ignore noisy columns and small numeric drift:

```bash
csvdelta old.csv new.csv -k place_id --ignore reviews --tolerance 0.05
```

Here's a Markdown report written to a file:

```bash
csvdelta old.csv new.csv -k place_id -f markdown -o report.md
```

### Options

| Option | Description |
|---|---|
| `-k, --key COL` | Key column (required). Repeat or comma-separate for a composite key: `-k city,shop` |
| `-i, --ignore COL` | Column to leave out of the comparison. Repeat or comma-separate |
| `-f, --format` | `text` (default), `json` or `markdown` |
| `-d, --delimiter` | Field delimiter. Use `tab` or `\t` for TSV |
| `--strip` | Trim whitespace around values before comparing |
| `--ignore-case` | Compare values case-insensitively |
| `--tolerance N` | Treat numeric values within `N` of each other as equal |
| `-o, --output FILE` | Write the report to a file |
| `--no-color` | Disable ANSI colours (also honours `NO_COLOR`) |

### In a script or CI job

```bash
if ! csvdelta yesterday.csv today.csv -k sku -f markdown -o changes.md; then
  echo "Catalogue changed, see changes.md"
fi
```

## Python API

```python
from csvdelta import diff_files, render

result = diff_files("old.csv", "new.csv", ["place_id"], ignore_columns=["reviews"])
print(result.summary())   # {'added': 1, 'removed': 1, 'changed': 1, ...}

for change in result.changed:
    for f in change.changes:
        print(change.key, f.column, f.old, "->", f.new)

print(render(result, "json"))
```

## Behaviour notes

- Files are read as UTF-8, and a leading BOM (as Excel writes) is handled.
- Duplicate keys and missing key columns are errors (exit `2`). The message gives the
  file and line.
- Only columns present in both files are compared. Added or removed columns are reported
  separately.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
