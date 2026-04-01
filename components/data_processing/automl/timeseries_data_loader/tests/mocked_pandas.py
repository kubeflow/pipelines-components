"""Minimal mocked pandas for timeseries_data_loader unit tests (no real pandas).

Mirrors the tabular_data_loader tests approach: patch ``sys.modules['pandas']`` with
``read_csv`` (chunked iterator), ``concat``, and a small DataFrame-like type that supports
the operations used in ``component.load_timeseries_data_truncate`` and the split logic.
"""

import csv
import io
import json
import types


class MockedDataFrame:
    """Columns + rows; supports the subset of pandas API used by timeseries_data_loader."""

    BYTES_PER_ROW = 100  # Same convention as tabular mock for memory_usage().sum()

    def __init__(self, columns, rows):
        """Store column names and row values (list of lists)."""
        self._columns = list(columns)
        self._rows = list(rows)

    @property
    def columns(self):
        """Column names."""
        return self._columns

    def __len__(self):
        """Row count."""
        return len(self._rows)

    def memory_usage(self, deep=True):
        """Return an object whose ``sum()`` estimates bytes (for size truncation loop)."""

        class MemUsage:
            def __init__(self, df):
                self._df = df

            def sum(self):
                return len(self._df._rows) * MockedDataFrame.BYTES_PER_ROW

        return MemUsage(self)

    def head(self, n):
        """First n rows."""
        return MockedDataFrame(self._columns, self._rows[:n])

    def tail(self, n):
        """Last n rows."""
        return MockedDataFrame(self._columns, self._rows[-n:])

    def copy(self, deep=True):
        """Shallow copy of rows."""
        return MockedDataFrame(self._columns, [list(r) for r in self._rows])

    def sort_values(self, by, ascending=True):
        """Sort rows lexicographically by the given column name(s)."""
        _ = ascending
        cols = list(by) if isinstance(by, (list, tuple)) else [by]
        col_indices = [self._columns.index(c) for c in cols]

        def sort_key(row):
            return tuple(row[i] for i in col_indices)

        sorted_rows = sorted(self._rows, key=sort_key)
        return MockedDataFrame(self._columns, sorted_rows)

    def reset_index(self, drop=True):
        """No index column in mock; return self."""
        return self

    @property
    def iloc(self):
        """Integer-location slice (``df.iloc[a:b]`` only)."""
        return _IlocIndexer(self)

    def to_csv(self, path, index=False):
        """Write CSV (index ignored; mock has no row index column)."""
        _ = index
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self._columns)
            writer.writerows(self._rows)

    def to_json(self, orient="records"):
        """JSON records like pandas."""
        if orient == "records":
            records = []
            for row in self._rows:
                records.append(dict(zip(self._columns, row)))
            return json.dumps(records)
        raise NotImplementedError(f"to_json orient={orient!r} not supported in mock")

    def groupby(self, by, sort=True):
        """Group rows by one column (``by``); yields ``(key, MockedDataFrame)`` like pandas."""
        return MockedGroupBy(self, by, sort=sort)


class MockedGroupBy:
    """Minimal ``DataFrame.groupby`` for a single column."""

    def __init__(self, df, by, sort=True):
        """Store parent frame, column name, and whether to sort group keys."""
        self._df = df
        self._by = by
        self._sort = sort

    def __iter__(self):
        """Yield ``(group_key, group_df)`` in first-seen key order if ``sort=False``."""
        col_idx = self._df._columns.index(self._by)
        groups: dict = {}
        key_order: list = []
        for row in self._df._rows:
            key = row[col_idx]
            if key not in groups:
                key_order.append(key)
                groups[key] = []
            groups[key].append(row)
        keys = sorted(key_order) if self._sort else key_order
        for k in keys:
            yield k, MockedDataFrame(self._df._columns, groups[k])


class _IlocIndexer:
    """Supports only slice indexing along rows (as used by the component)."""

    def __init__(self, df):
        self._df = df

    def __getitem__(self, key):
        if isinstance(key, slice):
            return MockedDataFrame(self._df._columns, self._df._rows[key])
        raise TypeError(f"mock iloc does not support {type(key)!r}")


def _read_csv_chunks(text_stream, chunksize):
    """Parse CSV and yield MockedDataFrame chunks."""
    if hasattr(text_stream, "read"):
        content = text_stream.read()
    else:
        content = text_stream
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    header = next(reader, None)
    if not header:
        return
    rows = list(reader)
    if not rows:
        yield MockedDataFrame(header, [])
        return
    for start in range(0, len(rows), chunksize):
        chunk_rows = rows[start : start + chunksize]
        yield MockedDataFrame(header, chunk_rows)


def _concat(dfs, ignore_index=True, axis=0):
    """Concatenate MockedDataFrames along rows (axis=0)."""
    _ = ignore_index
    if not dfs:
        return MockedDataFrame([], [])
    columns = dfs[0]._columns
    rows = []
    for df in dfs:
        rows.extend(df._rows)
    return MockedDataFrame(columns, rows)


def make_mocked_pandas_module():
    """Build a module suitable for ``sys.modules['pandas']``."""
    mod = types.ModuleType("pandas")

    def _read_csv(stream, chunksize=None):
        if chunksize is not None:
            return _read_csv_chunks(stream, chunksize)
        chunks = list(_read_csv_chunks(stream, 10000))
        return _concat(chunks) if chunks else MockedDataFrame([], [])

    def _dataframe(*args, **kwargs):
        """Support ``DataFrame(columns=...)`` for empty frames (concat with no parts)."""
        cols = kwargs.get("columns")
        if cols is not None:
            return MockedDataFrame(list(cols), [])
        return MockedDataFrame([], [])

    mod.read_csv = _read_csv
    mod.concat = _concat
    mod.DataFrame = _dataframe
    return mod
