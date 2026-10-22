import io
import json
from pathlib import Path

import pytest

from csvdelta import CsvDeltaError, diff_files, diff_tables, load_table, render
from csvdelta.cli import EXIT_DIFF, EXIT_ERROR, EXIT_SAME, main

OLD = """id,name,price,rating
1,Cafe Aroma,120,4.5
2,Brew Bros,150,4.1
3,Bean There,90,3.9
"""

NEW = """id,name,price,rating,phone
1,Cafe Aroma,130,4.5,555-0101
2,Brew Bros,150,4.1,555-0102
4,Daily Grind,110,4.7,555-0104
"""


def table(text, key=("id",), **kw):
    return load_table(io.StringIO(text), key, **kw)


def test_added_removed_changed():
    r = diff_tables(table(OLD), table(NEW), ["id"])
    assert [row["id"] for row in r.added] == ["4"]
    assert [row["id"] for row in r.removed] == ["3"]
    assert len(r.changed) == 1
    change = r.changed[0]
    assert change.key == ("1",)
    assert [(f.column, f.old, f.new) for f in change.changes] == [("price", "120", "130")]
    assert r.unchanged_count == 1
    assert r.columns_added == ["phone"]
    assert r.columns_removed == []
    assert r.has_changes


def test_identical_has_no_changes():
    r = diff_tables(table(OLD), table(OLD), ["id"])
    assert not r.has_changes
    assert r.summary()["unchanged"] == 3


def test_ignore_columns():
    r = diff_tables(table(OLD), table(NEW), ["id"], ignore_columns=["price", "phone"])
    assert r.changed == []
    assert r.columns_added == []


def test_numeric_tolerance():
    old = table("id,v\n1,1.00\n2,abc\n")
    new = table("id,v\n1,1.04\n2,abd\n")
    r = diff_tables(old, new, ["id"], numeric_tolerance=0.05)
    assert [c.key for c in r.changed] == [("2",)]


def test_strip_and_ignore_case():
    old = table("id,name\n1, Cafe \n")
    new = table("id,name\n1,CAFE\n")
    assert diff_tables(old, new, ["id"]).changed
    old = table("id,name\n1, Cafe \n", strip=True, ignore_case=True)
    new = table("id,name\n1,CAFE\n", strip=True, ignore_case=True)
    assert not diff_tables(old, new, ["id"]).has_changes


def test_composite_key():
    old = table("city,shop,open\nPune,A,yes\nMumbai,A,yes\n", key=("city", "shop"))
    new = table("city,shop,open\nPune,A,no\nMumbai,A,yes\n", key=("city", "shop"))
    r = diff_tables(old, new, ["city", "shop"])
    assert [c.key for c in r.changed] == [("Pune", "A")]


def test_missing_key_column():
    with pytest.raises(CsvDeltaError, match="key column"):
        table(OLD, key=("sku",))


def test_duplicate_key():
    with pytest.raises(CsvDeltaError, match="duplicate key 1"):
        table("id,v\n1,a\n1,b\n")


def test_removed_column():
    r = diff_tables(table(NEW), table(OLD), ["id"])
    assert r.columns_removed == ["phone"]


def test_render_formats():
    r = diff_tables(table(OLD), table(NEW), ["id"])
    text = render(r, "text")
    assert "+ 4" in text and "- 3" in text and "price: '120' -> '130'" in text
    data = json.loads(render(r, "json"))
    assert data["summary"]["added"] == 1
    assert data["changed"][0]["changes"][0] == {"column": "price", "old": "120", "new": "130"}
    md = render(r, "markdown")
    assert "| 1 | price | 120 | 130 |" in md
    with pytest.raises(ValueError):
        render(r, "xml")


def test_markdown_escapes_pipes():
    r = diff_tables(table("id,v\n1,a\n"), table("id,v\n1,a|b\n"), ["id"])
    assert "a\\|b" in render(r, "markdown")


@pytest.fixture
def files(tmp_path: Path):
    old, new = tmp_path / "old.csv", tmp_path / "new.csv"
    old.write_text(OLD, encoding="utf-8")
    new.write_text(NEW, encoding="utf-8")
    return old, new


def test_diff_files_with_bom(tmp_path: Path):
    old = tmp_path / "a.csv"
    new = tmp_path / "b.csv"
    old.write_text("﻿id,v\n1,a\n", encoding="utf-8")
    new.write_text("id,v\n1,b\n", encoding="utf-8")
    assert len(diff_files(old, new, ["id"]).changed) == 1


def test_cli_exit_codes(files, capsys):
    old, new = files
    assert main([str(old), str(old), "-k", "id"]) == EXIT_SAME
    assert main([str(old), str(new), "-k", "id"]) == EXIT_DIFF
    assert "1 added, 1 removed, 1 changed" in capsys.readouterr().out
    assert main([str(old), str(new), "-k", "nope"]) == EXIT_ERROR
    assert "key column" in capsys.readouterr().err
    assert main([str(old), "missing.csv", "-k", "id"]) == EXIT_ERROR


def test_cli_json_output_file(files, tmp_path: Path):
    old, new = files
    out = tmp_path / "report.json"
    assert main([str(old), str(new), "-k", "id", "-f", "json", "-o", str(out)]) == EXIT_DIFF
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["removed"] == 1


def test_cli_comma_separated_options(files, capsys):
    old, new = files
    code = main([str(old), str(new), "-k", "id", "-i", "price,phone"])
    assert code == EXIT_DIFF  # still has added/removed rows
    assert "0 changed" in capsys.readouterr().out


def test_cli_tab_delimiter(tmp_path: Path):
    a, b = tmp_path / "a.tsv", tmp_path / "b.tsv"
    a.write_text("id\tv\n1\tx\n", encoding="utf-8")
    b.write_text("id\tv\n1\tx\n", encoding="utf-8")
    assert main([str(a), str(b), "-k", "id", "-d", "\\t"]) == EXIT_SAME
