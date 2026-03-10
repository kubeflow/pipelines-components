"""Unit tests for the tabular_train_test_split component.

pandas and sklearn are mocked via sys.modules so the real packages are not required.
Tests are designed to achieve high coverage of the component source code.
"""

# Assisted-by: Cursor

import sys
from contextlib import contextmanager
from unittest import mock

import pytest

# Install mocks before component is imported so component's imports see them when running.
_mock_pd = mock.MagicMock()
_mock_sklearn = mock.MagicMock()
_mock_sklearn_model_selection = mock.MagicMock()
_mock_sklearn.model_selection = _mock_sklearn_model_selection
sys.modules["pandas"] = _mock_pd
sys.modules["sklearn"] = _mock_sklearn
sys.modules["sklearn.model_selection"] = _mock_sklearn_model_selection

from ..component import tabular_train_test_split  # noqa: E402


def _make_mock_dataframe_and_series():
    """Create mock df, X, y and train_test_split return values for component flow."""
    mock_df = mock.MagicMock()
    mock_X = mock.MagicMock()
    mock_y = mock.MagicMock()
    mock_df.drop.return_value = mock_X
    mock_df.__getitem__ = mock.MagicMock(return_value=mock_y)

    mock_X_train = mock.MagicMock()
    mock_X_test = mock.MagicMock()
    mock_y_train = mock.MagicMock()
    mock_y_test = mock.MagicMock()

    mock_train_combined = mock.MagicMock()
    mock_test_combined = mock.MagicMock()
    mock_test_combined.head.return_value.to_json.return_value = '[{"a":1,"b":2}]'

    return {
        "df": mock_df,
        "X": mock_X,
        "y": mock_y,
        "X_train": mock_X_train,
        "X_test": mock_X_test,
        "y_train": mock_y_train,
        "y_test": mock_y_test,
        "train_combined": mock_train_combined,
        "test_combined": mock_test_combined,
    }


@contextmanager
def _mock_pandas_and_sklearn(mocks=None):
    """Inject mock pandas and sklearn so the component runs without real dependencies."""
    if mocks is None:
        mocks = _make_mock_dataframe_and_series()

    _mock_pd.read_csv.return_value = mocks["df"]
    _mock_pd.concat.side_effect = [mocks["train_combined"], mocks["test_combined"]]
    _mock_sklearn_model_selection.train_test_split.side_effect = None
    _mock_sklearn_model_selection.train_test_split.return_value = (
        mocks["X_train"],
        mocks["X_test"],
        mocks["y_train"],
        mocks["y_test"],
    )

    with mock.patch.dict(
        sys.modules,
        {"pandas": _mock_pd, "sklearn": _mock_sklearn, "sklearn.model_selection": _mock_sklearn_model_selection},
    ):
        try:
            yield mocks
        finally:
            _mock_pd.read_csv.reset_mock()
            _mock_pd.concat.reset_mock()
            _mock_sklearn_model_selection.train_test_split.reset_mock()


class TestTrainTestSplitUnitTests:
    """Unit tests for tabular_train_test_split component logic."""

    def test_component_function_exists(self):
        """Component is callable and has python_func."""
        assert callable(tabular_train_test_split)
        assert hasattr(tabular_train_test_split, "python_func")

    def test_invalid_task_type_raises_value_error(self):
        """Invalid task_type raises ValueError before any pandas/sklearn use."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = "/tmp/input.csv"
            sampled_train = mock.MagicMock()
            sampled_train.path = "/tmp/train.csv"
            sampled_train.uri = "/tmp/train"
            sampled_test = mock.MagicMock()
            sampled_test.path = "/tmp/test.csv"
            sampled_test.uri = "/tmp/test"

            with pytest.raises(ValueError, match=r"Invalid task_type.*Must be one of"):
                tabular_train_test_split.python_func(
                    dataset=dataset,
                    task_type="invalid",
                    label_column="target",
                    split_config={"test_size": 0.3},
                    sampled_train_dataset=sampled_train,
                    sampled_test_dataset=sampled_test,
                )

    def test_regression_uses_no_stratify(self, tmp_path):
        """Regression task_type passes stratify=None to train_test_split."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            result = tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={"test_size": 0.2, "random_state": 123},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            _mock_sklearn_model_selection.train_test_split.assert_called_once()
            call_kw = _mock_sklearn_model_selection.train_test_split.call_args[1]
            assert call_kw["stratify"] is None
            assert call_kw["test_size"] == 0.2
            assert call_kw["random_state"] == 123
            assert result.split_config["test_size"] == 0.2
            assert result.sample_row == '[{"a":1,"b":2}]'

    def test_binary_with_stratify_true_uses_stratify_y(self, tmp_path):
        """Binary task_type with stratify=True passes y as stratify."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="binary",
                label_column="label",
                split_config={"test_size": 0.3, "stratify": True},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            call_kw = _mock_sklearn_model_selection.train_test_split.call_args[1]
            assert call_kw["stratify"] is mocks["y"]

    def test_multiclass_default_stratify_uses_y(self, tmp_path):
        """Multiclass with default split_config uses stratify=y (stratify defaults to True)."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="multiclass",
                label_column="target",
                split_config={},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            call_kw = _mock_sklearn_model_selection.train_test_split.call_args[1]
            assert call_kw["stratify"] is mocks["y"]
            assert call_kw["test_size"] == 0.3
            assert call_kw["random_state"] == 42

    def test_multiclass_stratify_false_uses_none(self, tmp_path):
        """Multiclass with stratify=False passes stratify=None."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="multiclass",
                label_column="target",
                split_config={"stratify": False},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            call_kw = _mock_sklearn_model_selection.train_test_split.call_args[1]
            assert call_kw["stratify"] is None

    def test_split_config_defaults_applied(self, tmp_path):
        """Missing test_size and random_state in split_config use defaults 0.3 and 42."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            result = tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            call_kw = _mock_sklearn_model_selection.train_test_split.call_args[1]
            assert call_kw["test_size"] == 0.3
            assert call_kw["random_state"] == 42
            assert result.split_config["test_size"] == 0.3

    def test_read_csv_and_drop_called_correctly(self, tmp_path):
        """Component reads dataset.path and drops label_column."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "data.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={"test_size": 0.3},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            _mock_pd.read_csv.assert_called_once_with(dataset.path)
            mocks["df"].drop.assert_called_once_with(columns=["target"], inplace=True)
            mocks["df"].__getitem__.assert_called_with("target")

    def test_uri_appended_with_csv(self, tmp_path):
        """Output artifact URIs get '.csv' appended."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = "/artifacts/train"
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = "/artifacts/test"

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            assert sampled_train.uri == "/artifacts/train.csv"
            assert sampled_test.uri == "/artifacts/test.csv"

    def test_to_csv_called_on_both_outputs(self, tmp_path):
        """Train and test combined dataframes are written to output paths."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            mocks["train_combined"].to_csv.assert_called_once_with(sampled_train.path, index=False)
            mocks["test_combined"].to_csv.assert_called_once_with(sampled_test.path, index=False)

    def test_return_value_has_sample_row_and_split_config(self, tmp_path):
        """Return value is NamedTuple with sample_row (str) and split_config (dict)."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            result = tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={"test_size": 0.25},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            assert hasattr(result, "sample_row")
            assert hasattr(result, "split_config")
            assert isinstance(result.sample_row, str)
            assert result.sample_row == '[{"a":1,"b":2}]'
            assert result.split_config == {"test_size": 0.25}

    def test_pd_concat_called_twice_for_train_and_test(self, tmp_path):
        """pd.concat is called once for train (X_train, y_train) and once for test (X_test, y_test)."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            dataset = mock.MagicMock()
            dataset.path = str(tmp_path / "input.csv")
            sampled_train = mock.MagicMock()
            sampled_train.path = str(tmp_path / "train.csv")
            sampled_train.uri = str(tmp_path / "train")
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset=dataset,
                task_type="regression",
                label_column="target",
                split_config={},
                sampled_train_dataset=sampled_train,
                sampled_test_dataset=sampled_test,
            )

            assert _mock_pd.concat.call_count == 2
            first_call = _mock_pd.concat.call_args_list[0]
            second_call = _mock_pd.concat.call_args_list[1]
            assert first_call[0][0] == [mocks["X_train"], mocks["y_train"]]
            assert second_call[0][0] == [mocks["X_test"], mocks["y_test"]]
            assert first_call[1] == {"axis": 1}
            assert second_call[1] == {"axis": 1}
