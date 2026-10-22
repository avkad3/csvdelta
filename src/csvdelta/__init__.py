"""csvdelta: diff CSV snapshots by key column(s)."""

__version__ = "0.1.0"

from .core import (  # noqa: E402
    CsvDeltaError,
    DiffResult,
    FieldChange,
    RowChange,
    Table,
    diff_files,
    diff_tables,
    load_table,
)
from .render import render  # noqa: E402

__all__ = [
    "CsvDeltaError",
    "DiffResult",
    "FieldChange",
    "RowChange",
    "Table",
    "diff_files",
    "diff_tables",
    "load_table",
    "render",
    "__version__",
]
