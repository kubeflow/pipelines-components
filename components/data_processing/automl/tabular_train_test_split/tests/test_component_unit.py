"""Unit tests for the tabular_train_test_split component.

pandas and sklearn are mocked via sys.modules so the real packages are not required.
Tests are designed to achieve high coverage of the component source code.
"""

import sys
from contextlib import contextmanager
from unittest import mock

import pytest


@pytest.fixture(autouse=True, scope="module")
def isolated_sys_modules():
    """Patch sys.modules so pandas/sklearn mocks are only present during this test module.

    This prevents import pollution that could affect other tests in a session.
    """
    with mock.patch.dict(sys.modules, clear=False) as mocked_modules:
        _mock_pd = mock.MagicMock()
        _mock_sklearn = mock.MagicMock()
        _mock_sklearn_model_selection = mock.MagicMock()
        _mock_sklearn.model_selection = _mock_sklearn_model_selection
        mocked_modules["pandas"] = _mock_pd
        mocked_modules["sklearn"] = _mock_sklearn
        mocked_modules["sklearn.model_selection"] = _mock_sklearn_model_selection
        yield


from ..component import tabular_train_test_split  # noqa: E402


def _make_mock_dataframe_and_series():
    """Create mock df, X, y and train_test_split return values for component flow."""
    mock_df = mock.MagicMock()
    mock_X = mock.MagicMock()
    mock_y = mock.MagicMock()
    mock_df.drop.return_value = mock_X
    mock_df.__getitem__ = mock.MagicMock(return_value=mock_y)

    # Primary split outputs
    mock_X_train = mock.MagicMock()
    mock_X_test = mock.MagicMock()
    mock_y_train = mock.MagicMock()
    mock_y_test = mock.MagicMock()

    # Secondary split outputs (selection vs extra)
    mock_X_sel = mock.MagicMock()
    mock_X_extra = mock.MagicMock()
    mock_y_sel = mock.MagicMock()
    mock_y_extra = mock.MagicMock()

    mock_sel_combined = mock.MagicMock()
    mock_extra_combined = mock.MagicMock()
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
        "X_sel": mock_X_sel,
        "X_extra": mock_X_extra,
        "y_sel": mock_y_sel,
        "y_extra": mock_y_extra,
        "sel_combined": mock_sel_combined,
        "extra_combined": mock_extra_combined,
        "test_combined": mock_test_combined,
    }


@contextmanager
def _mock_pandas_and_sklearn(mocks=None):
    """Configure pandas/sklearn mocks (from fixture) so the component runs without real dependencies."""
    if mocks is None:
        mocks = _make_mock_dataframe_and_series()

    mock_pd = sys.modules.get("pandas")
    mock_sklearn_model_selection = sys.modules.get("sklearn.model_selection")
    if mock_pd is None or mock_sklearn_model_selection is None:
        raise RuntimeError(
            "pandas/sklearn mocks not in sys.modules (tests must run with isolated_sys_modules fixture)."
        )

    mock_pd.read_csv.return_value = mocks["df"]
    mock_pd.concat.side_effect = [mocks["sel_combined"], mocks["extra_combined"], mocks["test_combined"]]
    mock_sklearn_model_selection.train_test_split.side_effect = [
        (mocks["X_train"], mocks["X_test"], mocks["y_train"], mocks["y_test"]),
        (mocks["X_sel"], mocks["X_extra"], mocks["y_sel"], mocks["y_extra"]),
    ]

    try:
        yield mocks
    finally:
        mock_pd.read_csv.reset_mock()
        mock_pd.concat.reset_mock()
        mock_sklearn_model_selection.train_test_split.reset_mock()


class TestTrainTestSplitUnitTests:
    """Unit tests for tabular_train_test_split component logic."""

    def test_component_function_exists(self):
        """Component is callable and has python_func and component_spec."""
        assert callable(tabular_train_test_split)
        assert hasattr(tabular_train_test_split, "python_func")
        assert hasattr(tabular_train_test_split, "component_spec")

    def test_invalid_task_type_raises_value_error(self):
        """Invalid task_type raises ValueError before any pandas/sklearn use."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = "/tmp/test.csv"
            sampled_test.uri = "/tmp/test"

            with pytest.raises(ValueError, match=r"Invalid task_type.*Must be one of"):
                tabular_train_test_split.python_func(
                    dataset_path="/tmp/input.csv",
                    task_type="invalid",
                    label_column="target",
                    workspace_path="/tmp/workspace",
                    split_config={"test_size": 0.2},
                    sampled_test_dataset=sampled_test,
                )

    def test_regression_uses_no_stratify(self, tmp_path):
        """Regression task_type passes stratify=None to train_test_split."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            result = tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={"test_size": 0.2, "random_state": 123},
                sampled_test_dataset=sampled_test,
            )

            train_test_split = sys.modules["sklearn.model_selection"].train_test_split
            assert train_test_split.call_count == 2
            # Primary split
            call_kw = train_test_split.call_args_list[0][1]
            assert call_kw["stratify"] is None
            assert call_kw["test_size"] == 0.2
            assert call_kw["random_state"] == 123
            # Secondary split
            call_kw2 = train_test_split.call_args_list[1][1]
            assert call_kw2["stratify"] is None
            assert result.split_config["test_size"] == 0.2
            assert result.sample_row == '[{"a":1,"b":2}]'

    def test_binary_with_stratify_true_uses_stratify_y(self, tmp_path):
        """Binary task_type with stratify=True passes y as stratify."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="binary",
                label_column="label",
                workspace_path=str(tmp_path / "workspace"),
                split_config={"test_size": 0.2, "stratify": True},
                sampled_test_dataset=sampled_test,
            )

            # Primary split should use y as stratify
            call_kw = sys.modules["sklearn.model_selection"].train_test_split.call_args_list[0][1]
            assert call_kw["stratify"] is mocks["y"]
            # Secondary split should use y_train as stratify
            call_kw2 = sys.modules["sklearn.model_selection"].train_test_split.call_args_list[1][1]
            assert call_kw2["stratify"] is mocks["y_train"]

    def test_multiclass_default_stratify_uses_y(self, tmp_path):
        """Multiclass with default split_config uses stratify=y (stratify defaults to True)."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="multiclass",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={},
                sampled_test_dataset=sampled_test,
            )

            call_kw = sys.modules["sklearn.model_selection"].train_test_split.call_args_list[0][1]
            assert call_kw["stratify"] is mocks["y"]
            assert call_kw["test_size"] == 0.2
            assert call_kw["random_state"] == 42

    def test_multiclass_stratify_false_uses_none(self, tmp_path):
        """Multiclass with stratify=False passes stratify=None."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="multiclass",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={"stratify": False},
                sampled_test_dataset=sampled_test,
            )

            call_kw = sys.modules["sklearn.model_selection"].train_test_split.call_args_list[0][1]
            assert call_kw["stratify"] is None

    def test_split_config_defaults_applied(self, tmp_path):
        """Missing test_size and random_state in split_config use defaults 0.2 and 42."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            result = tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={},
                sampled_test_dataset=sampled_test,
            )

            call_kw = sys.modules["sklearn.model_selection"].train_test_split.call_args_list[0][1]
            assert call_kw["test_size"] == 0.2
            assert call_kw["random_state"] == 42
            assert result.split_config["test_size"] == 0.2

    def test_read_csv_and_drop_called_correctly(self, tmp_path):
        """Component reads dataset_path and drops label_column."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            dataset_path = str(tmp_path / "data.csv")
            tabular_train_test_split.python_func(
                dataset_path=dataset_path,
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={"test_size": 0.2},
                sampled_test_dataset=sampled_test,
            )

            sys.modules["pandas"].read_csv.assert_called_once_with(dataset_path)
            mocks["df"].drop.assert_called_once_with(columns=["target"], inplace=True)
            mocks["df"].__getitem__.assert_called_with("target")

    def test_uri_appended_with_csv(self, tmp_path):
        """Test artifact URI gets '.csv' appended."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = "/artifacts/test"

            tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={},
                sampled_test_dataset=sampled_test,
            )

            assert sampled_test.uri == "/artifacts/test.csv"

    def test_to_csv_called_on_all_outputs(self, tmp_path):
        """Selection-train, extra-train, and test combined dataframes are written to output paths."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            workspace_path = str(tmp_path / "workspace")
            result = tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=workspace_path,
                split_config={},
                sampled_test_dataset=sampled_test,
            )

            # Selection train and extra train written to workspace
            mocks["sel_combined"].to_csv.assert_called_once_with(result.models_selection_train_path, index=False)
            mocks["extra_combined"].to_csv.assert_called_once_with(result.extra_train_data_path, index=False)
            # Test written to artifact
            mocks["test_combined"].to_csv.assert_called_once_with(sampled_test.path, index=False)

    def test_return_value_has_all_fields(self, tmp_path):
        """Return value is NamedTuple with sample_row, split_config, and new path fields."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            result = tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={"test_size": 0.25},
                sampled_test_dataset=sampled_test,
            )

            assert hasattr(result, "sample_row")
            assert hasattr(result, "split_config")
            assert hasattr(result, "models_selection_train_path")
            assert hasattr(result, "extra_train_data_path")
            assert isinstance(result.sample_row, str)
            assert result.sample_row == '[{"a":1,"b":2}]'
            mocks["test_combined"].head.assert_called_once_with(1)
            mocks["test_combined"].head.return_value.to_json.assert_called_once_with(orient="records")
            assert result.split_config["test_size"] == 0.25
            assert result.split_config["random_state"] == 42
            assert result.split_config["stratify"] is False  # regression
            assert "models_selection_train.csv" in result.models_selection_train_path
            assert "extra_train_dataset.csv" in result.extra_train_data_path

    def test_pd_concat_called_three_times(self, tmp_path):
        """pd.concat is called for selection_train, extra_train, and test."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={},
                sampled_test_dataset=sampled_test,
            )

            assert sys.modules["pandas"].concat.call_count == 3
            first_call = sys.modules["pandas"].concat.call_args_list[0]
            second_call = sys.modules["pandas"].concat.call_args_list[1]
            third_call = sys.modules["pandas"].concat.call_args_list[2]
            # Selection train: X_sel + y_sel
            assert first_call[0][0] == [mocks["X_sel"], mocks["y_sel"]]
            assert first_call[1] == {"axis": 1}
            # Extra train: X_extra + y_extra
            assert second_call[0][0] == [mocks["X_extra"], mocks["y_extra"]]
            assert second_call[1] == {"axis": 1}
            # Test: X_test + y_test
            assert third_call[0][0] == [mocks["X_test"], mocks["y_test"]]
            assert third_call[1] == {"axis": 1}

    def test_secondary_split_uses_selection_train_size(self, tmp_path):
        """Secondary split uses test_size=(1 - selection_train_size)."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            tabular_train_test_split.python_func(
                dataset_path=str(tmp_path / "input.csv"),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={},
                sampled_test_dataset=sampled_test,
                selection_train_size=0.3,
            )

            train_test_split = sys.modules["sklearn.model_selection"].train_test_split
            # Secondary split should use test_size = 1 - 0.3 = 0.7
            secondary_call_kw = train_test_split.call_args_list[1][1]
            assert secondary_call_kw["test_size"] == pytest.approx(0.7)

    def test_full_dataset_removed_from_pvc(self, tmp_path):
        """The input full_dataset CSV is deleted from PVC after splitting."""
        mocks = _make_mock_dataframe_and_series()
        with _mock_pandas_and_sklearn(mocks):
            sampled_test = mock.MagicMock()
            sampled_test.path = str(tmp_path / "test.csv")
            sampled_test.uri = str(tmp_path / "test")

            # Create a real file so unlink can be verified
            input_file = tmp_path / "full_dataset.csv"
            input_file.write_text("a,b\n1,2\n")
            assert input_file.exists()

            tabular_train_test_split.python_func(
                dataset_path=str(input_file),
                task_type="regression",
                label_column="target",
                workspace_path=str(tmp_path / "workspace"),
                split_config={},
                sampled_test_dataset=sampled_test,
            )

            assert not input_file.exists(), "full_dataset.csv should be removed after splitting"
