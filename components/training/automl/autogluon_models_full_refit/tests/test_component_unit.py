"""Tests for the autogluon_models_full_refit component."""

import json
import sys
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture(autouse=True, scope="module")
def isolated_sys_modules():
    """Patch pandas/autogluon in sys.modules only for this test module; restored on module teardown."""
    with mock.patch.dict(sys.modules, clear=False) as mocked_modules:
        # Provide fresh mocks so that test-local mutations don't persist globally
        mocked_modules["pandas"] = mock.MagicMock()
        _ag = mock.MagicMock()
        _ag.__path__ = []
        _ag.__spec__ = None
        mocked_modules["autogluon"] = _ag
        for sub in ("autogluon.tabular", "autogluon.core", "autogluon.core.metrics"):
            _m = mock.MagicMock()
            _m.__spec__ = None
            if sub == "autogluon.core":
                _m.__path__ = []
            mocked_modules[sub] = _m
        yield


from ..component import autogluon_models_full_refit  # noqa: E402

# Default args for pipeline_name, run_id, sample_row (required by component signature)
PIPELINE_NAME = "test-pipeline-run-123"
RUN_ID = "run-456"
SAMPLE_ROW = '[{"feature1": 1, "target": 1.1}]'

# Minimal valid notebook with placeholders used by the component
_MINIMAL_REGRESSION_NOTEBOOK = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "abc123",
            "metadata": {},
            "outputs": [],
            "source": [
                'pipeline_name = "<REPLACE_PIPELINE_NAME>"\n',
                'run_id = "<REPLACE_RUN_ID>"\n',
                'model_name = "<REPLACE_MODEL_NAME>"\n',
                "score_data = <REPLACE_SAMPLE_ROW>\n",
            ],
        }
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3.12", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.9"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

_MINIMAL_CLASSIFICATION_NOTEBOOK = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "def456",
            "metadata": {},
            "outputs": [],
            "source": [
                'pipeline_name = "<REPLACE_PIPELINE_NAME>"\n',
                'run_id = "<REPLACE_RUN_ID>"\n',
                'model_name = "<REPLACE_MODEL_NAME>"\n',
                "score_data = <REPLACE_SAMPLE_ROW>\n",
            ],
        }
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3.12", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.9"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


@pytest.fixture()
def mock_notebooks(tmp_path):
    """Create a temp directory with minimal notebook .ipynb files for the notebooks parameter."""
    notebooks_dir = tmp_path / "notebooks_input"
    notebooks_dir.mkdir()
    with open(notebooks_dir / "regression_notebook.ipynb", "w") as f:
        json.dump(_MINIMAL_REGRESSION_NOTEBOOK, f)
    with open(notebooks_dir / "classification_notebook.ipynb", "w") as f:
        json.dump(_MINIMAL_CLASSIFICATION_NOTEBOOK, f)
    artifact = mock.MagicMock()
    artifact.path = str(notebooks_dir)
    return artifact


class TestAutogluonModelsFullRefitUnitTests:
    """Unit tests for component logic."""

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_with_valid_model(self, mock_predictor_class, mock_read_csv, mock_notebooks, tmp_path):
        """Test full refit with a valid model name."""
        mock_predictor = mock.MagicMock()
        mock_predictor_clone = mock.MagicMock()
        mock_predictor.clone.return_value = mock_predictor_clone
        mock_predictor_class.load.return_value = mock_predictor
        eval_results = {"r2": 0.9, "root_mean_squared_error": 0.5}
        mock_predictor_clone.evaluate.return_value = eval_results
        feature_importance_dict = {"feature1": 0.1, "feature2": 0.05}
        mock_predictor_clone.feature_importance.return_value = mock.MagicMock(to_dict=lambda: feature_importance_dict)
        mock_predictor.problem_type = "regression"
        mock_predictor.label = "target"

        mock_dataset_df = mock.MagicMock()
        mock_extra_train_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_dataset_df, mock_extra_train_df]

        # Create mock artifacts; use temp dir so we can verify metrics files are written
        mock_predictor_artifact = mock.MagicMock()
        mock_predictor_artifact.path = "/tmp/predictor"

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"

        model_output_dir = str(tmp_path / "model_output")
        Path(model_output_dir).mkdir()
        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = model_output_dir
        mock_model_artifact.metadata = {}

        model_config = {"preset": "best_quality"}

        # Call the component function
        result = autogluon_models_full_refit.python_func(
            model_name="LightGBM_BAG_L1",
            test_dataset=mock_full_dataset,
            predictor_path=mock_predictor_artifact.path,
            sampling_config={},
            split_config={},
            model_config=model_config,
            pipeline_name=PIPELINE_NAME,
            run_id=RUN_ID,
            sample_row=SAMPLE_ROW,
            model_artifact=mock_model_artifact,
            extra_train_data_path="/tmp/extra_train.csv",
            notebooks=mock_notebooks,
        )

        assert result.model_name == "LightGBM_BAG_L1_FULL"
        assert mock_model_artifact.metadata["display_name"] == "LightGBM_BAG_L1_FULL"
        assert mock_model_artifact.metadata["context"]["data_config"] == {
            "sampling_config": {},
            "split_config": {},
        }
        assert mock_model_artifact.metadata["context"]["task_type"] == "regression"
        assert mock_model_artifact.metadata["context"]["label_column"] == mock_predictor.label
        assert mock_model_artifact.metadata["context"]["metrics"]["test_data"] == eval_results

        # Verify model_config is stored in metadata
        assert mock_model_artifact.metadata["context"]["model_config"] == model_config

        # Verify location metadata
        assert mock_model_artifact.metadata["context"]["location"]["model_directory"] == "LightGBM_BAG_L1_FULL"
        assert (
            mock_model_artifact.metadata["context"]["location"]["predictor"]
            == "LightGBM_BAG_L1_FULL/predictor/predictor.pkl"
        )
        assert (
            mock_model_artifact.metadata["context"]["location"]["notebook"]
            == "LightGBM_BAG_L1_FULL/notebooks/automl_predictor_notebook.ipynb"
        )

        # Verify read_csv was called with correct paths (test_dataset + extra_train)
        assert mock_read_csv.call_count == 2
        assert mock_read_csv.call_args_list[0][0][0] == "/tmp/full_dataset.csv"
        assert mock_read_csv.call_args_list[1][0][0] == "/tmp/extra_train.csv"

        # Verify TabularPredictor.load was called with correct path
        mock_predictor_class.load.assert_called_once_with("/tmp/predictor")

        # Verify refit_full was called with extra train data
        mock_predictor_clone.refit_full.assert_called_once_with(
            model="LightGBM_BAG_L1", train_data_extra=mock_extra_train_df
        )

        # Verify evaluate and feature_importance called with full dataset dataframe (on clone)
        mock_predictor_clone.evaluate.assert_called_once_with(mock_dataset_df)
        mock_predictor_clone.feature_importance.assert_called_once_with(mock_dataset_df)

        # Verify clone was called with correct parameters (path is model_name_FULL/predictor)
        mock_predictor.clone.assert_called_once()
        call_kw = mock_predictor.clone.call_args[1]
        assert Path(call_kw["path"]) == Path(model_output_dir) / "LightGBM_BAG_L1_FULL" / "predictor"
        assert call_kw["return_clone"] is True
        assert call_kw["dirs_exist_ok"] is True

        # Verify delete_models was called with correct models to keep
        mock_predictor_clone.delete_models.assert_called_once_with(models_to_keep=["LightGBM_BAG_L1"])

        # Verify set_model_best was called with correct model
        mock_predictor_clone.set_model_best.assert_called_once_with(model="LightGBM_BAG_L1_FULL", save_trainer=True)

        # Verify save_space was called
        mock_predictor_clone.save_space.assert_called_once()

        # Verify metrics files were written (under model_name_FULL/metrics/)
        metrics_dir = Path(model_output_dir) / "LightGBM_BAG_L1_FULL" / "metrics"
        assert metrics_dir.exists()
        metrics_path = metrics_dir / "metrics.json"
        assert metrics_path.exists()
        assert json.loads(metrics_path.read_text()) == eval_results
        fi_path = metrics_dir / "feature_importance.json"
        assert fi_path.exists()
        assert json.loads(fi_path.read_text()) == feature_importance_dict
        # Regression: no confusion matrix
        assert not (metrics_dir / "confusion_matrix.json").exists()

        # Verify notebook was written under model_name_FULL/notebooks/
        notebook_path = (
            Path(model_output_dir) / "LightGBM_BAG_L1_FULL" / "notebooks" / "automl_predictor_notebook.ipynb"
        )
        assert notebook_path.exists()
        notebook = json.loads(notebook_path.read_text())
        assert "cells" in notebook
        notebook_text = notebook_path.read_text()
        # Verify all placeholders were replaced (must match actual placeholder names)
        for placeholder in (
            "<REPLACE_PIPELINE_NAME>",
            "<REPLACE_RUN_ID>",
            "<REPLACE_MODEL_NAME>",
            "<REPLACE_SAMPLE_ROW>",
        ):
            assert placeholder not in notebook_text, f"Unreplaced placeholder: {placeholder}"

        # Verify retrieve_pipeline_name trimmed the last segment ("123") from "test-pipeline-run-123"
        assert "test-pipeline-run" in notebook_text
        assert PIPELINE_NAME not in notebook_text

        # Verify label column was stripped from sample_row in the notebook
        assert "feature1" in notebook_text
        assert "'target'" not in notebook_text

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_without_extra_train_data(self, mock_predictor_class, mock_read_csv, mock_notebooks, tmp_path):
        """Test full refit with empty extra_train_data_path passes None to refit_full."""
        mock_predictor = mock.MagicMock()
        mock_predictor_clone = mock.MagicMock()
        mock_predictor.clone.return_value = mock_predictor_clone
        mock_predictor_class.load.return_value = mock_predictor
        mock_predictor_clone.evaluate.return_value = {"r2": 0.9}
        mock_predictor_clone.feature_importance.return_value = mock.MagicMock(to_dict=lambda: {"f": 0.1})
        mock_predictor.problem_type = "regression"
        mock_predictor.label = "target"

        mock_dataset_df = mock.MagicMock()
        mock_read_csv.return_value = mock_dataset_df

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"

        model_output_dir = str(tmp_path / "model_output")
        Path(model_output_dir).mkdir()
        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = model_output_dir
        mock_model_artifact.metadata = {}

        autogluon_models_full_refit.python_func(
            model_name="LightGBM_BAG_L1",
            test_dataset=mock_full_dataset,
            predictor_path="/tmp/predictor",
            sampling_config={},
            split_config={},
            model_config={},
            pipeline_name=PIPELINE_NAME,
            run_id=RUN_ID,
            sample_row=SAMPLE_ROW,
            model_artifact=mock_model_artifact,
            extra_train_data_path="",
            notebooks=mock_notebooks,
        )

        # Verify refit_full was called with train_data_extra=None
        mock_predictor_clone.refit_full.assert_called_once_with(model="LightGBM_BAG_L1", train_data_extra=None)
        # read_csv should only be called once (test_dataset only)
        mock_read_csv.assert_called_once_with("/tmp/full_dataset.csv")

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_handles_file_not_found_test_dataset(self, mock_predictor_class, mock_read_csv, mock_notebooks):
        """Test that FileNotFoundError is raised when test_dataset path doesn't exist."""
        mock_read_csv.side_effect = FileNotFoundError("Test dataset file not found")

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/nonexistent/full_dataset.csv"

        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = "/tmp/refitted_model"
        mock_model_artifact.metadata = {}

        with pytest.raises(FileNotFoundError):
            autogluon_models_full_refit.python_func(
                model_name="LightGBM_BAG_L1",
                test_dataset=mock_full_dataset,
                predictor_path="/tmp/predictor",
                sampling_config={},
                split_config={},
                model_config={},
                pipeline_name=PIPELINE_NAME,
                run_id=RUN_ID,
                sample_row=SAMPLE_ROW,
                model_artifact=mock_model_artifact,
                extra_train_data_path="/tmp/extra_train.csv",
                notebooks=mock_notebooks,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_handles_file_not_found_predictor(self, mock_predictor_class, mock_read_csv, mock_notebooks):
        """Test that FileNotFoundError is raised when predictor path doesn't exist."""
        # Setup mocks to raise FileNotFoundError
        mock_predictor_class.load.side_effect = FileNotFoundError("Predictor file not found")

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"

        mock_predictor_artifact = mock.MagicMock()
        mock_predictor_artifact.path = "/nonexistent/predictor"

        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = "/tmp/refitted_model"
        mock_model_artifact.metadata = {}

        # Verify FileNotFoundError is raised
        with pytest.raises(FileNotFoundError):
            autogluon_models_full_refit.python_func(
                model_name="LightGBM_BAG_L1",
                test_dataset=mock_full_dataset,
                predictor_path="/nonexistent/predictor",
                sampling_config={},
                split_config={},
                model_config={},
                pipeline_name=PIPELINE_NAME,
                run_id=RUN_ID,
                sample_row=SAMPLE_ROW,
                model_artifact=mock_model_artifact,
                extra_train_data_path="",
                notebooks=mock_notebooks,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_handles_refit_failure(self, mock_predictor_class, mock_read_csv, mock_notebooks):
        """Test that ValueError is raised when refit_full fails."""
        mock_predictor = mock.MagicMock()
        mock_predictor_clone = mock.MagicMock()
        mock_predictor.clone.return_value = mock_predictor_clone
        mock_predictor_clone.refit_full.side_effect = ValueError("Model not found in predictor")
        mock_predictor_class.load.return_value = mock_predictor

        mock_dataset_df = mock.MagicMock()
        mock_read_csv.return_value = mock_dataset_df

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"

        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = "/tmp/refitted_model"
        mock_model_artifact.metadata = {}

        # Verify ValueError is raised
        with pytest.raises(ValueError, match="Model not found in predictor"):
            autogluon_models_full_refit.python_func(
                model_name="NonexistentModel",
                test_dataset=mock_full_dataset,
                predictor_path="/tmp/predictor",
                sampling_config={},
                split_config={},
                model_config={},
                pipeline_name=PIPELINE_NAME,
                run_id=RUN_ID,
                sample_row=SAMPLE_ROW,
                model_artifact=mock_model_artifact,
                extra_train_data_path="",
                notebooks=mock_notebooks,
            )

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_operations_called_in_correct_order(
        self, mock_predictor_class, mock_read_csv, mock_notebooks, tmp_path
    ):
        """Test that all required operations are called in correct order."""
        # Track call order across predictor and clone
        call_order = []
        mock_predictor = mock.MagicMock()
        mock_predictor_clone = mock.MagicMock()
        mock_predictor.clone.side_effect = lambda **kw: (call_order.append("clone"), mock_predictor_clone)[1]
        mock_predictor_clone.delete_models.side_effect = lambda **kw: call_order.append("delete_models")
        mock_predictor_clone.refit_full.side_effect = lambda **kw: call_order.append("refit_full")
        mock_predictor_clone.set_model_best.side_effect = lambda **kw: call_order.append("set_model_best")
        mock_predictor_clone.save_space.side_effect = lambda: call_order.append("save_space")
        mock_predictor_clone.evaluate.side_effect = lambda df: (call_order.append("evaluate"), {"r2": 0.9})[1]
        mock_predictor_clone.feature_importance.side_effect = lambda df: (
            call_order.append("feature_importance"),
            mock.MagicMock(to_dict=lambda: {"feature1": 0.1}),
        )[1]
        mock_predictor_class.load.side_effect = lambda path: (call_order.append("load"), mock_predictor)[1]
        mock_predictor.problem_type = "regression"
        mock_predictor.label = "target"

        mock_read_csv.side_effect = [mock.MagicMock(), mock.MagicMock()]

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"
        model_output_dir = str(tmp_path / "model_output")
        Path(model_output_dir).mkdir()
        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = model_output_dir
        mock_model_artifact.metadata = {}

        autogluon_models_full_refit.python_func(
            model_name="LightGBM_BAG_L1",
            test_dataset=mock_full_dataset,
            predictor_path="/tmp/predictor",
            sampling_config={},
            split_config={},
            model_config={},
            pipeline_name=PIPELINE_NAME,
            run_id=RUN_ID,
            sample_row=SAMPLE_ROW,
            model_artifact=mock_model_artifact,
            extra_train_data_path="/tmp/extra_train.csv",
            notebooks=mock_notebooks,
        )

        # Verify operations were called in correct order
        assert call_order == [
            "load",
            "clone",
            "delete_models",
            "refit_full",
            "set_model_best",
            "save_space",
            "evaluate",
            "feature_importance",
        ]

    @mock.patch("autogluon.core.metrics.confusion_matrix")
    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_writes_confusion_matrix_for_classification(
        self, mock_predictor_class, mock_read_csv, mock_confusion_matrix, mock_notebooks, tmp_path
    ):
        """Test that confusion matrix is written when problem_type is binary or multiclass."""
        mock_predictor = mock.MagicMock()
        mock_predictor_clone = mock.MagicMock()
        mock_predictor.clone.return_value = mock_predictor_clone
        mock_predictor_class.load.return_value = mock_predictor
        mock_predictor_clone.evaluate.return_value = {"accuracy": 0.95}
        mock_predictor_clone.feature_importance.return_value = mock.MagicMock(to_dict=lambda: {"feature1": 0.1})
        mock_predictor.problem_type = "binary"
        mock_predictor_clone.predict.return_value = mock.MagicMock()
        mock_predictor.label = "target"

        mock_dataset_df = mock.MagicMock()
        mock_extra_df = mock.MagicMock()
        mock_read_csv.side_effect = [mock_dataset_df, mock_extra_df]
        confusion_matrix_dict = {"0": {"0": 2, "1": 0}, "1": {"0": 1, "1": 0}}
        mock_confusion_matrix.return_value = mock.MagicMock(to_dict=lambda: confusion_matrix_dict)

        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"
        mock_predictor_artifact = mock.MagicMock()
        mock_predictor_artifact.path = "/tmp/predictor"
        model_output_dir = str(tmp_path / "model_output")
        Path(model_output_dir).mkdir()
        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = model_output_dir
        mock_model_artifact.metadata = {}

        autogluon_models_full_refit.python_func(
            model_name="LightGBM_BAG_L1",
            test_dataset=mock_full_dataset,
            predictor_path=mock_predictor_artifact.path,
            sampling_config={},
            split_config={},
            model_config={},
            pipeline_name=PIPELINE_NAME,
            run_id=RUN_ID,
            sample_row=SAMPLE_ROW,
            model_artifact=mock_model_artifact,
            extra_train_data_path="/tmp/extra_train.csv",
            notebooks=mock_notebooks,
        )
        mock_confusion_matrix.assert_called_once_with(
            solution=mock_dataset_df["target"],
            prediction=mock_predictor_clone.predict.return_value,
            output_format="pandas_dataframe",
        )

        metrics_dir = Path(model_output_dir) / "LightGBM_BAG_L1_FULL" / "metrics"
        cm_path = metrics_dir / "confusion_matrix.json"
        assert cm_path.exists()
        assert json.loads(cm_path.read_text()) == confusion_matrix_dict

    @mock.patch("pandas.read_csv")
    @mock.patch("autogluon.tabular.TabularPredictor")
    def test_full_refit_raises_on_invalid_problem_type(
        self, mock_predictor_class, mock_read_csv, mock_notebooks, tmp_path
    ):
        """Test that ValueError is raised when problem_type is not regression/binary/multiclass."""
        mock_predictor = mock.MagicMock()
        mock_predictor_clone = mock.MagicMock()
        mock_predictor.clone.return_value = mock_predictor_clone
        mock_predictor_class.load.return_value = mock_predictor
        mock_predictor_clone.evaluate.return_value = {"r2": 0.9}
        mock_predictor_clone.feature_importance.return_value = mock.MagicMock(to_dict=lambda: {"f": 0.1})
        mock_predictor.problem_type = "unknown"
        mock_predictor.label = "target"

        mock_read_csv.return_value = mock.MagicMock()
        mock_full_dataset = mock.MagicMock()
        mock_full_dataset.path = "/tmp/full_dataset.csv"
        model_output_dir = str(tmp_path / "model_output")
        Path(model_output_dir).mkdir()
        mock_model_artifact = mock.MagicMock()
        mock_model_artifact.path = model_output_dir
        mock_model_artifact.metadata = {}

        with pytest.raises(ValueError, match="Invalid problem type: unknown"):
            autogluon_models_full_refit.python_func(
                model_name="LightGBM_BAG_L1",
                test_dataset=mock_full_dataset,
                predictor_path="/tmp/predictor",
                sampling_config={},
                split_config={},
                model_config={},
                pipeline_name=PIPELINE_NAME,
                run_id=RUN_ID,
                sample_row=SAMPLE_ROW,
                model_artifact=mock_model_artifact,
                extra_train_data_path="",
                notebooks=mock_notebooks,
            )

    def test_component_imports_correctly(self):
        """Test that the component can be imported and has required attributes."""
        assert callable(autogluon_models_full_refit)
        assert hasattr(autogluon_models_full_refit, "python_func")
        assert hasattr(autogluon_models_full_refit, "component_spec")
