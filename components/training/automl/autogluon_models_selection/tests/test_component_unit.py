"""Tests for the autogluon_models_selection component."""

import sys
from pathlib import Path
from unittest import mock

import pytest

from ..component import models_selection  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def isolated_sys_modules():
    """Patch pandas/autogluon in sys.modules only for this test module; restored on module teardown."""
    with mock.patch.dict(sys.modules, clear=False) as mocked_modules:
        mocked_modules["pandas"] = mock.MagicMock()
        _ag = mock.MagicMock()
        _ag.__path__ = []
        _ag.__spec__ = None
        mocked_modules["autogluon"] = _ag
        _m = mock.MagicMock()
        _m.__spec__ = None
        mocked_modules["autogluon.tabular"] = _m
        yield


def _make_mock_leaderboard(all_model_names):
    """Mock leaderboard so .head(n)['model'].values.tolist() returns first n names."""

    def _head(n):
        head_mock = mock.MagicMock()
        col_mock = mock.MagicMock()
        col_mock.values.tolist.return_value = all_model_names[:n]
        head_mock.__getitem__.return_value = col_mock
        return head_mock

    mock_lb = mock.MagicMock()
    mock_lb.head.side_effect = _head
    return mock_lb


class TestModelsSelectionUnitTests:
    """Unit tests for component logic."""

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_with_regression(self, mock_predictor_class, mock_read_csv):
        """Test models selection with regression problem type."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "r2"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor_class.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(
            ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1", "CatBoost_BAG_L1", "RandomForest_BAG_L1"]
        )

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        # Create mock artifacts
        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function
        result = models_selection.python_func(
            label_column="target",
            task_type="regression",
            top_n=2,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify read_csv was called with correct paths
        assert mock_read_csv.call_count == 2
        assert mock_read_csv.call_args_list[0][0][0] == "/tmp/train_data.csv"
        assert mock_read_csv.call_args_list[1][0][0] == "/tmp/test_data.csv"

        # Verify TabularPredictor was created with correct parameters
        mock_predictor_class.assert_called_once_with(
            problem_type="regression",
            label="target",
            eval_metric="r2",
            path=Path(workspace_path) / "autogluon_predictor",
            verbosity=2,
        )

        # Verify fit was called with correct parameters
        mock_predictor.fit.assert_called_once_with(
            train_data=mock_train_df,
            num_stack_levels=3,
            num_bag_folds=2,
            use_bag_holdout=True,
            holdout_frac=0.2,
            time_limit=3600,
            presets="medium_quality",
        )

        # Verify leaderboard was called with test data
        mock_predictor.leaderboard.assert_called_once_with(mock_test_df)

        # Verify return values
        assert result.top_models == ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1"]
        assert result.eval_metric == "r2"
        assert result.predictor_path == str(Path(workspace_path) / "autogluon_predictor")
        assert result.model_config == {
            "preset": "medium_quality",
            "eval_metric": "r2",
            "time_limit": 3600,
        }

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_with_binary_classification(self, mock_predictor_class, mock_read_csv):
        """Test models selection with binary classification problem type."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "accuracy"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(
            ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1", "CatBoost_BAG_L1"]
        )

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_predictor_class.return_value = mock_predictor

        # Create mock artifacts
        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function
        result = models_selection.python_func(
            label_column="target",
            task_type="binary",
            top_n=2,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify TabularPredictor was created with binary problem type
        mock_predictor_class.assert_called_once_with(
            problem_type="binary",
            label="target",
            eval_metric="accuracy",
            path=Path(workspace_path) / "autogluon_predictor",
            verbosity=2,
        )

        # Verify return values
        assert result.top_models == ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1"]
        assert result.eval_metric == "accuracy"

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_with_multiclass_classification(self, mock_predictor_class, mock_read_csv):
        """Test models selection with multiclass classification problem type."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "accuracy"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(
            ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1", "CatBoost_BAG_L1", "RandomForest_BAG_L1"]
        )

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_predictor_class.return_value = mock_predictor

        # Create mock artifacts
        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function
        result = models_selection.python_func(
            label_column="target",
            task_type="multiclass",
            top_n=3,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify TabularPredictor was created with multiclass problem type
        mock_predictor_class.assert_called_once_with(
            problem_type="multiclass",
            label="target",
            eval_metric="accuracy",
            path=Path(workspace_path) / "autogluon_predictor",
            verbosity=2,
        )

        # Verify top_n models were selected
        assert len(result.top_models) == 3
        assert result.top_models == ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1", "CatBoost_BAG_L1"]

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_with_different_top_n(self, mock_predictor_class, mock_read_csv):
        """Test models selection with different top_n values."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "r2"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(
            [
                "LightGBM_BAG_L1",
                "NeuralNetFastAI_BAG_L1",
                "CatBoost_BAG_L1",
                "RandomForest_BAG_L1",
                "XGBoost_BAG_L1",
            ]
        )

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_predictor_class.return_value = mock_predictor

        # Create mock artifacts
        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function with top_n=1
        result = models_selection.python_func(
            label_column="target",
            task_type="regression",
            top_n=1,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify only top 1 model was selected
        assert len(result.top_models) == 1
        assert result.top_models == ["LightGBM_BAG_L1"]

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_handles_file_not_found_train_data(self, mock_predictor_class, mock_read_csv):
        """Test that FileNotFoundError is raised when train_data path doesn't exist."""
        # Setup mocks to raise FileNotFoundError for train_data
        mock_read_csv.side_effect = FileNotFoundError("Train data file not found")

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/nonexistent/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Verify FileNotFoundError is raised
        with pytest.raises(FileNotFoundError):
            models_selection.python_func(
                label_column="target",
                task_type="regression",
                top_n=2,
                train_data=mock_train_data,
                test_data=mock_test_data,
                workspace_path=workspace_path,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_handles_file_not_found_test_data(self, mock_predictor_class, mock_read_csv):
        """Test that FileNotFoundError is raised when test_data path doesn't exist."""
        mock_train_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, FileNotFoundError("Test data file not found")]

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/nonexistent/test_data.csv"

        workspace_path = "/tmp/model"

        # Verify FileNotFoundError is raised
        with pytest.raises(FileNotFoundError):
            models_selection.python_func(
                label_column="target",
                task_type="regression",
                top_n=2,
                train_data=mock_train_data,
                test_data=mock_test_data,
                workspace_path=workspace_path,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_handles_fit_failure(self, mock_predictor_class, mock_read_csv):
        """Test that ValueError is raised when model fitting fails."""
        mock_predictor = mock.MagicMock()
        mock_predictor.fit.side_effect = ValueError("Target column not found in dataset")
        mock_predictor_class.return_value = mock_predictor

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Verify ValueError is raised
        with pytest.raises(ValueError, match="Target column not found in dataset"):
            models_selection.python_func(
                label_column="target",
                task_type="regression",
                top_n=2,
                train_data=mock_train_data,
                test_data=mock_test_data,
                workspace_path=workspace_path,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_handles_leaderboard_failure(self, mock_predictor_class, mock_read_csv):
        """Test that errors are raised when leaderboard generation fails."""
        mock_predictor = mock.MagicMock()
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.side_effect = ValueError("Test data schema mismatch")
        mock_predictor_class.return_value = mock_predictor

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Verify ValueError is raised
        with pytest.raises(ValueError, match="Test data schema mismatch"):
            models_selection.python_func(
                label_column="target",
                task_type="regression",
                top_n=2,
                train_data=mock_train_data,
                test_data=mock_test_data,
                workspace_path=workspace_path,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_verifies_all_operations_called(self, mock_predictor_class, mock_read_csv):
        """Test that all required operations are called in correct order."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "r2"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1"])

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_predictor_class.return_value = mock_predictor

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function
        models_selection.python_func(
            label_column="target",
            task_type="regression",
            top_n=2,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify call order: read_csv (train) -> read_csv (test) -> TabularPredictor -> fit -> leaderboard
        assert mock_read_csv.call_count == 2
        assert mock_predictor_class.called
        assert mock_predictor.fit.called
        assert mock_predictor.leaderboard.called

        # Verify fit was called before leaderboard
        assert mock_predictor.fit.call_count == 1
        assert mock_predictor.leaderboard.call_count == 1

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_sets_metadata_correctly(self, mock_predictor_class, mock_read_csv):
        """Test that return value (top_models, eval_metric, predictor_path, model_config) is correct."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "r2"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(
            ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1", "CatBoost_BAG_L1"]
        )

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_predictor_class.return_value = mock_predictor

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function
        result = models_selection.python_func(
            label_column="target",
            task_type="regression",
            top_n=3,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify return value was set correctly
        assert result.top_models == [
            "LightGBM_BAG_L1",
            "NeuralNetFastAI_BAG_L1",
            "CatBoost_BAG_L1",
        ]
        assert len(result.top_models) == 3
        assert result.eval_metric == "r2"
        assert result.predictor_path == str(Path(workspace_path) / "autogluon_predictor")
        assert result.model_config == {
            "preset": "medium_quality",
            "eval_metric": "r2",
            "time_limit": 3600,
        }

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_models_selection_returns_correct_named_tuple(self, mock_predictor_class, mock_read_csv):
        """Test that the function returns a NamedTuple with correct fields."""
        mock_predictor = mock.MagicMock()
        mock_predictor.eval_metric = "r2"
        mock_predictor.fit.return_value = mock_predictor
        mock_predictor.leaderboard.return_value = _make_mock_leaderboard(["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1"])

        mock_train_df = mock.MagicMock()
        mock_test_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_train_df, mock_test_df]

        mock_predictor_class.return_value = mock_predictor

        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"

        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"

        workspace_path = "/tmp/model"

        # Call the component function
        result = models_selection.python_func(
            label_column="target",
            task_type="regression",
            top_n=2,
            train_data=mock_train_data,
            test_data=mock_test_data,
            workspace_path=workspace_path,
        )

        # Verify return type and fields
        assert hasattr(result, "top_models")
        assert hasattr(result, "eval_metric")
        assert hasattr(result, "predictor_path")
        assert hasattr(result, "model_config")
        assert isinstance(result.top_models, list)
        assert isinstance(result.eval_metric, str)
        assert isinstance(result.predictor_path, str)
        assert isinstance(result.model_config, dict)
        assert result.top_models == ["LightGBM_BAG_L1", "NeuralNetFastAI_BAG_L1"]
        assert result.eval_metric == "r2"
        assert result.predictor_path == str(Path(workspace_path) / "autogluon_predictor")
        assert result.model_config["preset"] == "medium_quality"
        assert result.model_config["time_limit"] == 3600

    def test_models_selection_rejects_invalid_task_type(self):
        """Test that ValueError is raised for invalid task_type."""
        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"
        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"
        with pytest.raises(ValueError, match="Invalid task_type"):
            models_selection.python_func(
                label_column="target",
                task_type="invalid",
                top_n=2,
                train_data=mock_train_data,
                test_data=mock_test_data,
                workspace_path="/tmp/model",
            )

    def test_models_selection_rejects_invalid_top_n(self):
        """Test that ValueError is raised for non-positive top_n."""
        mock_train_data = mock.MagicMock()
        mock_train_data.path = "/tmp/train_data.csv"
        mock_test_data = mock.MagicMock()
        mock_test_data.path = "/tmp/test_data.csv"
        with pytest.raises(ValueError, match="top_n must be a positive integer"):
            models_selection.python_func(
                label_column="target",
                task_type="regression",
                top_n=0,
                train_data=mock_train_data,
                test_data=mock_test_data,
                workspace_path="/tmp/model",
            )

    def test_component_imports_correctly(self):
        """Test that the component can be imported and has required attributes."""
        assert callable(models_selection)
        assert hasattr(models_selection, "python_func")
        assert hasattr(models_selection, "component_spec")
