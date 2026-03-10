"""Minimal mocked pandas implementation for unit tests without the real pandas dependency.

Provides MockedDataFrame and a mocked pandas module so the tabular_data_loader component
can run with sys.modules['pandas'] patched. Used together with _mock_boto3_and_pandas() in tests.
"""

import csv
import io
import random
from collections import Counter


class MockedDataFrame:
    """Minimal DataFrame-like object: columns (list) and rows (list of lists, one per row)."""

    BYTES_PER_ROW = 100  # Used for memory_usage(deep=True).sum()

    def __init__(self, columns, rows):
        """Store column names and row data."""
        self._columns = list(columns)
        self._rows = list(rows)

    @property
    def columns(self):
        """Return the list of column names."""
        return self._columns

    @property
    def empty(self):
        """Return True if there are no rows."""
        return len(self._rows) == 0

    def __len__(self):
        """Return the number of rows."""
        return len(self._rows)

    def memory_usage(self, deep=True):
        """Return a mock object whose sum() is BYTES_PER_ROW times row count."""

        class SumResult:
            def sum(self):
                return len(self._df._rows) * MockedDataFrame.BYTES_PER_ROW

        class MemUsage:
            """Mock memory usage object with sum() returning byte estimate."""

            def __init__(self, df):
                """Store reference to the dataframe."""
                self._df = df

            def sum(self):
                """Return BYTES_PER_ROW times number of rows."""
                return len(self._df._rows) * MockedDataFrame.BYTES_PER_ROW

        return MemUsage(self)

    def head(self, n):
        """Return a new MockedDataFrame with the first n rows."""
        return MockedDataFrame(self._columns, self._rows[:n])

    def dropna(self, subset=None):
        """Drop rows with missing values in the given columns."""
        if not subset:
            return self
        col_indices = [self._columns.index(c) for c in subset]
        new_rows = [row for row in self._rows if all(row[i] != "" and row[i] is not None for i in col_indices)]
        return MockedDataFrame(self._columns, new_rows)

    def _col_index(self, col):
        """Return the index of the given column name."""
        return self._columns.index(col)

    def _value_counts_for_column(self, col):
        """Return MockedValueCounts for the given column."""
        idx = self._col_index(col)
        counts = Counter(row[idx] for row in self._rows)
        return MockedValueCounts(counts)

    def __getitem__(self, key):
        """Return column as MockedSeries or filter rows by mask."""
        if isinstance(key, (list, tuple)):
            return self
        # Boolean "mask" style: df[df[col] != val]
        if hasattr(key, "_column") and hasattr(key, "_value"):
            col_idx = self._col_index(key._column)
            val = key._value
            return MockedDataFrame(
                self._columns,
                [row for row in self._rows if row[col_idx] != val],
            )
        return self

    def __ne__(self, other):
        """Return a mask object for filtering rows by column != value."""

        class Mask:
            _column = None
            _value = other

        Mask._column = getattr(self, "_last_column", None)
        return Mask

    def value_counts(self):
        """Return value counts for the column (used via MockedSeries)."""
        col = getattr(self, "_value_counts_column", None)
        if col is not None:
            return self._value_counts_for_column(col)
        return MockedValueCounts({})

    def groupby(self, by, group_keys=False):
        """Return a MockedGroupBy for stratified sampling."""
        return MockedGroupBy(self, by)

    def sample(self, frac=1.0, random_state=None):
        """Return a new MockedDataFrame with a random sample of rows."""
        rng = random.Random(random_state)
        n = max(1, int(len(self._rows) * frac)) if frac < 1.0 else len(self._rows)
        n = min(n, len(self._rows))
        indices = rng.sample(range(len(self._rows)), n)
        new_rows = [self._rows[i] for i in indices]
        return MockedDataFrame(self._columns, new_rows)

    def reset_index(self, drop=True):
        """Return self (no-op for mock)."""
        return self

    def to_csv(self, path, index=False):
        """Write the data to a CSV file at the given path."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self._columns)
            writer.writerows(self._rows)


class MockedValueCounts:
    """Minimal value_counts() result: supports .index.values and comparison for singleton detection."""

    def __init__(self, count_dict):
        """Store a mapping of value -> count."""
        self._counts = dict(count_dict)

    @property
    def index(self):
        """Return an object with .values listing the distinct values."""

        class Index:
            def __init__(self, keys):
                """Store index keys"""
                self._keys = keys

            @property
            def values(self):
                return self._keys

        return Index(list(self._counts.keys()))

    def __eq__(self, other):
        """Return an object whose .index.values are keys with count equal to other."""
        matching_keys = [k for k, v in self._counts.items() if v == other]

        class FilteredResult:
            @property
            def index(self):
                class Idx:
                    values = matching_keys

                return Idx()

        return FilteredResult()


class MockedGroupBy:
    """Minimal groupby().apply(fn).reset_index(drop=True) for stratified sampling."""

    def __init__(self, df, by):
        """Store the dataframe and the column to group by."""
        self._df = df
        self._by = by

    def apply(self, fn, **kwargs):
        """Group rows by column, apply fn to each group, and concatenate results."""
        col_idx = self._df._col_index(self._by)
        groups = {}
        for row in self._df._rows:
            key = row[col_idx]
            groups.setdefault(key, []).append(row)
        result_rows = []
        for key in sorted(groups.keys()):
            group_df = MockedDataFrame(self._df._columns, groups[key])
            sampled = fn(group_df)
            if hasattr(sampled, "_rows"):
                result_rows.extend(sampled._rows)
            else:
                result_rows.extend(sampled)
        return MockedDataFrame(self._df._columns, result_rows)

    def reset_index(self, drop=True):
        """Return stored result or self (no-op for mock)."""
        return self._result if hasattr(self, "_result") else self


def _read_csv_chunks(text_stream, chunksize):
    """Parse CSV from text_stream and yield MockedDataFrame chunks."""
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
    for start in range(0, len(rows), chunksize):
        chunk_rows = rows[start : start + chunksize]
        yield MockedDataFrame(header, chunk_rows)


def _concat(dfs, ignore_index=True):
    """Concatenate a list of MockedDataFrames into one."""
    if not dfs:
        return MockedDataFrame([], [])
    columns = dfs[0]._columns
    rows = []
    for df in dfs:
        rows.extend(df._rows)
    return MockedDataFrame(columns, rows)


def make_mocked_pandas_module():
    """Build a module-like object that can be used as sys.modules['pandas']."""
    import types

    mod = types.ModuleType("pandas")
    mod.read_csv = lambda stream, chunksize=10000: _read_csv_chunks(stream, chunksize)
    mod.concat = _concat
    mod.DataFrame = lambda: MockedDataFrame([], [])

    # value_counts is called as df[col].value_counts(); our MockedDataFrame.__getitem__ for
    # a column name needs to return something with value_counts(). So we need to support
    # df[label_column] returning an object that has .value_counts() and also supports != val.
    # In the component: chunk_df[label_column].value_counts() and chunk_df[chunk_df[label_column] != idx].
    # So __getitem__(col) should return an object that has .value_counts() and when used in
    # df[df[col] != idx] we need to get a mask. In pandas, df[col] is a Series and df[col] != idx
    # is a boolean Series, and df[boolean_series] filters rows. So we need:
    # - df[col] to return something with .value_counts() and that we can store col for the != mask
    # - df[mask] where mask has column and value, to filter rows
    # So let's make __getitem__(col) when col is a string return a "series" that has
    # .value_counts() and when compared with != val we store column and value so that df[mask]
    # can filter.
    class MockedSeries:
        """Minimal series-like object for df[col] and value_counts()."""

        def __init__(self, df, column):
            """Store reference to parent dataframe and column name."""
            self._df = df
            self._column = column

        def value_counts(self):
            """Return value counts for this column."""
            return self._df._value_counts_for_column(self._column)

        def __ne__(self, other):
            """Return a mask for filtering rows where this column != other."""

            class Mask:
                _column = self._column
                _value = other
                _mask_series = True

            return Mask

    _original_getitem = MockedDataFrame.__getitem__

    def getitem(self, key):
        """Return MockedSeries for column name, or filter by mask."""
        if isinstance(key, str) and key in self._columns:
            return MockedSeries(self, key)
        return _original_getitem(self, key)

    MockedDataFrame.__getitem__ = getitem

    return mod
