"""Tests for the leaderboard_evaluation component."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from ..component import leaderboard_evaluation


def _create_model_metrics_dir(metrics_dict, model_name="Model1"):
    """Create a temp dir with model_name/metrics/metrics.json containing the given dict. Returns path."""
    tmp_dir = tempfile.mkdtemp()
    metrics_dir = Path(tmp_dir) / model_name / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "metrics.json").write_text(json.dumps(metrics_dict))
    return tmp_dir


class TestLeaderboardEvaluationUnitTests:
    """Unit tests for component logic."""

    @mock.patch.dict("sys.modules", {"pandas": mock.MagicMock()})
    @mock.patch("pandas.DataFrame")
    def test_leaderboard_evaluation_with_single_model(self, mock_dataframe_class):
        """Test leaderboard evaluation with a single model."""
        metrics = {
            "root_mean_squared_error": 0.5,
            "mean_absolute_error": 0.4,
            "r2": 0.9,
        }
        model_dir = _create_model_metrics_dir(metrics, model_name="Model1")
        try:
            expected_html = "| model | rmse |\n|-------|------|\n| Model1 | 0.5 |"
            mock_df_sorted = mock.MagicMock()
            mock_df_sorted.__len__ = lambda self: 1
            mock_df_sorted.to_html.return_value = expected_html
            mock_df = mock.MagicMock()
            mock_df.sort_values.return_value = mock_df_sorted
            mock_dataframe_class.return_value = mock_df

            mock_model = mock.MagicMock()
            mock_model.path = model_dir
            mock_model.uri = "http://example.com/artifacts"
            mock_model.metadata = {"display_name": "Model1"}

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as tmp_file:
                tmp_path = tmp_file.name
            try:
                mock_html = mock.MagicMock()
                mock_html.path = tmp_path

                leaderboard_evaluation.python_func(
                    models=[mock_model],
                    eval_metric="root_mean_squared_error",
                    html_artifact=mock_html,
                )

                mock_dataframe_class.assert_called_once()
                call_args = mock_dataframe_class.call_args[0][0]
                assert len(call_args) == 1
                assert call_args[0]["model"] == "Model1"
                assert call_args[0]["root_mean_squared_error"] == 0.5
                assert call_args[0]["mean_absolute_error"] == 0.4
                assert call_args[0]["r2"] == 0.9
                assert (
                    call_args[0]["notebook"]
                    == "http://example.com/artifacts/Model1/notebooks/automl_predictor_notebook.ipynb"
                )
                assert call_args[0]["predictor"] == "http://example.com/artifacts/Model1/predictor/predictor.pkl"
                mock_df.sort_values.assert_called_once_with(by="root_mean_squared_error", ascending=False)
                mock_df_sorted.to_html.assert_called_once()
                # Component wraps table in full HTML document
                assert expected_html in Path(tmp_path).read_text()
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        finally:
            shutil.rmtree(model_dir, ignore_errors=True)

    @mock.patch.dict("sys.modules", {"pandas": mock.MagicMock()})
    @mock.patch("pandas.DataFrame")
    def test_leaderboard_evaluation_with_multiple_models(self, mock_dataframe_class):
        """Test leaderboard evaluation with multiple models."""
        model_dirs = []
        try:
            metrics_list = [
                {"root_mean_squared_error": 0.8, "mean_absolute_error": 0.6},
                {"root_mean_squared_error": 0.3, "mean_absolute_error": 0.2},
                {"root_mean_squared_error": 0.5, "mean_absolute_error": 0.4},
            ]
            for i, m in enumerate(metrics_list):
                model_dirs.append(_create_model_metrics_dir(m, model_name=f"Model{i + 1}"))

            mock_df_sorted = mock.MagicMock()
            mock_df_sorted.__len__ = lambda self: 3
            mock_df_sorted.to_html.return_value = "<table></table>"
            mock_df = mock.MagicMock()
            mock_df.sort_values.return_value = mock_df_sorted
            mock_dataframe_class.return_value = mock_df

            mock_models = []
            for i, path in enumerate(model_dirs):
                m = mock.MagicMock()
                m.path = path
                m.uri = "http://example.com/artifacts"
                m.metadata = {"display_name": f"Model{i + 1}"}
                mock_models.append(m)

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as tmp_file:
                tmp_path = tmp_file.name
            try:
                mock_html = mock.MagicMock()
                mock_html.path = tmp_path

                leaderboard_evaluation.python_func(
                    models=mock_models,
                    eval_metric="root_mean_squared_error",
                    html_artifact=mock_html,
                )

                mock_dataframe_class.assert_called_once()
                call_args = mock_dataframe_class.call_args[0][0]
                assert len(call_args) == 3
                assert call_args[0]["model"] == "Model1"
                assert call_args[0]["root_mean_squared_error"] == 0.8
                assert (
                    call_args[0]["notebook"]
                    == "http://example.com/artifacts/Model1/notebooks/automl_predictor_notebook.ipynb"
                )
                assert call_args[0]["predictor"] == "http://example.com/artifacts/Model1/predictor/predictor.pkl"
                assert call_args[1]["model"] == "Model2"
                assert call_args[1]["root_mean_squared_error"] == 0.3
                assert call_args[2]["model"] == "Model3"
                assert call_args[2]["root_mean_squared_error"] == 0.5
                mock_df.sort_values.assert_called_once_with(by="root_mean_squared_error", ascending=False)
                mock_df_sorted.to_html.assert_called_once()
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        finally:
            for d in model_dirs:
                shutil.rmtree(d, ignore_errors=True)

    @mock.patch.dict("sys.modules", {"pandas": mock.MagicMock()})
    @mock.patch("pandas.DataFrame", create=True)
    def test_leaderboard_evaluation_sorts_by_rmse(self, mock_dataframe_class):
        """Test that leaderboard is sorted by RMSE in descending order."""
        model_dirs = []
        try:
            for i, rmse in enumerate((0.9, 0.1, 0.5)):
                model_dirs.append(
                    _create_model_metrics_dir({"root_mean_squared_error": rmse}, model_name=f"Model{i + 1}")
                )

            sorted_html = "<table>sorted</table>"
            mock_df_sorted = mock.MagicMock()
            mock_df_sorted.__len__ = lambda self: 3
            mock_df_sorted.to_html.return_value = sorted_html
            mock_df = mock.MagicMock()
            mock_df.sort_values.return_value = mock_df_sorted
            mock_dataframe_class.return_value = mock_df

            mock_models = []
            for i, path in enumerate(model_dirs):
                m = mock.MagicMock()
                m.path = path
                m.uri = "http://example.com/artifacts"
                m.metadata = {"display_name": f"Model{i + 1}"}
                mock_models.append(m)

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as tmp_file:
                tmp_path = tmp_file.name
            try:
                mock_html = mock.MagicMock()
                mock_html.path = tmp_path

                leaderboard_evaluation.python_func(
                    models=mock_models,
                    eval_metric="root_mean_squared_error",
                    html_artifact=mock_html,
                )

                mock_df.sort_values.assert_called_once_with(by="root_mean_squared_error", ascending=False)
                mock_df_sorted.to_html.assert_called_once()
                # Component wraps table in full HTML document
                assert sorted_html in Path(tmp_path).read_text()
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        finally:
            for d in model_dirs:
                shutil.rmtree(d, ignore_errors=True)

    @mock.patch.dict("sys.modules", {"pandas": mock.MagicMock()})
    @mock.patch("pandas.DataFrame", create=True)
    def test_leaderboard_evaluation_writes_html_file(self, mock_dataframe_class):
        """Test that HTML file is written correctly."""
        metrics = {"root_mean_squared_error": 0.5, "mean_absolute_error": 0.4}
        model_dir = _create_model_metrics_dir(metrics, model_name="Model1")
        try:
            expected_html = "<table><tr><td>Model1</td><td>0.5</td><td>0.4</td></tr></table>"
            mock_df_sorted = mock.MagicMock()
            mock_df_sorted.__len__ = lambda self: 1
            mock_df_sorted.to_html.return_value = expected_html
            mock_df = mock.MagicMock()
            mock_df.sort_values.return_value = mock_df_sorted
            mock_dataframe_class.return_value = mock_df

            mock_model = mock.MagicMock()
            mock_model.path = model_dir
            mock_model.uri = "http://example.com/artifacts"
            mock_model.metadata = {"display_name": "Model1"}

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as tmp_file:
                tmp_path = tmp_file.name
            try:
                mock_html = mock.MagicMock()
                mock_html.path = tmp_path

                leaderboard_evaluation.python_func(
                    models=[mock_model],
                    eval_metric="root_mean_squared_error",
                    html_artifact=mock_html,
                )

                mock_dataframe_class.assert_called_once()
                call_args = mock_dataframe_class.call_args[0][0]
                assert len(call_args) == 1
                assert call_args[0]["model"] == "Model1"
                assert call_args[0]["root_mean_squared_error"] == 0.5
                assert call_args[0]["mean_absolute_error"] == 0.4
                assert (
                    call_args[0]["notebook"]
                    == "http://example.com/artifacts/Model1/notebooks/automl_predictor_notebook.ipynb"
                )
                assert call_args[0]["predictor"] == "http://example.com/artifacts/Model1/predictor/predictor.pkl"
                mock_df.sort_values.assert_called_once_with(by="root_mean_squared_error", ascending=False)
                mock_df_sorted.to_html.assert_called_once()
                # Component wraps table in full HTML document
                assert expected_html in Path(tmp_path).read_text()
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        finally:
            shutil.rmtree(model_dir, ignore_errors=True)

    @mock.patch.dict("sys.modules", {"pandas": mock.MagicMock()})
    def test_leaderboard_evaluation_rejects_empty_eval_metric(self):
        """Test that TypeError is raised when eval_metric is empty or not a string."""
        mock_model = mock.MagicMock()
        mock_model.path = "/tmp/model"
        mock_model.metadata = {"display_name": "Model1"}
        mock_html = mock.MagicMock()
        mock_html.path = "/tmp/out.html"

        with pytest.raises(TypeError, match=r"eval_metric must be a non-empty string\."):
            leaderboard_evaluation.python_func(
                models=[mock_model],
                eval_metric="",
                html_artifact=mock_html,
            )

        with pytest.raises(TypeError, match=r"eval_metric must be a non-empty string\."):
            leaderboard_evaluation.python_func(
                models=[mock_model],
                eval_metric="   ",
                html_artifact=mock_html,
            )

    @mock.patch.dict("sys.modules", {"pandas": mock.MagicMock()})
    def test_leaderboard_evaluation_rejects_empty_models_list(self):
        """Test that TypeError is raised when models is empty or not a list."""
        mock_html = mock.MagicMock()
        mock_html.path = "/tmp/out.html"

        with pytest.raises(TypeError, match=r"models must be a non-empty list\."):
            leaderboard_evaluation.python_func(
                models=[],
                eval_metric="root_mean_squared_error",
                html_artifact=mock_html,
            )

        with pytest.raises(TypeError, match=r"models must be a non-empty list\."):
            leaderboard_evaluation.python_func(
                models="not_a_list",
                eval_metric="root_mean_squared_error",
                html_artifact=mock_html,
            )
