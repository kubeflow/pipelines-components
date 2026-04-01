"""Tests for the leaderboard_evaluation component."""

import json
import sys
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture(autouse=True, scope="module")
def isolated_sys_modules():
    """Patch pandas in sys.modules only for this test module; restored on module teardown."""
    with mock.patch.dict(sys.modules, clear=False) as mocked_modules:
        mocked_modules["pandas"] = mock.MagicMock()
        yield


from ..component import leaderboard_evaluation  # noqa: E402


@pytest.fixture()
def create_model_dir(tmp_path):
    """Factory fixture to create model artifact directories with metrics.json."""
    _counter = [0]

    def _create(metrics_dict, model_name="Model1"):
        model_dir = tmp_path / f"model_artifact_{_counter[0]}"
        _counter[0] += 1
        model_dir.mkdir()
        metrics_dir = model_dir / model_name / "metrics"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "metrics.json").write_text(json.dumps(metrics_dict))
        return str(model_dir)

    return _create


@pytest.fixture()
def html_output_path(tmp_path):
    """Provide a temporary HTML output path."""
    return str(tmp_path / "leaderboard.html")


@pytest.fixture()
def embedded_artifact():
    """Provide mock embedded artifact pointing to component dir (for leaderboard_html_template.html)."""
    component_dir = Path(__file__).resolve().parent.parent
    mock_artifact = mock.MagicMock()
    mock_artifact.path = str(component_dir)
    return mock_artifact


def _make_mock_sorted_df(rows, columns):
    """Build a mock sorted DataFrame with the given rows and columns."""
    mock_df_sorted = mock.MagicMock()
    mock_df_sorted.__len__ = lambda self: len(rows)
    mock_df_sorted.index.name = "rank"
    mock_df_sorted.columns = columns
    mock_df_sorted.iterrows.return_value = list(rows)
    # Support .iloc[0]["model"] for best_model extraction
    row_dicts = [r[1] for r in rows]
    mock_df_sorted.iloc.__getitem__ = lambda _, idx: row_dicts[idx]
    return mock_df_sorted


class TestLeaderboardEvaluationUnitTests:
    """Unit tests for component logic."""

    @mock.patch("pandas.DataFrame")
    def test_single_model(self, mock_dataframe_class, create_model_dir, html_output_path, embedded_artifact):
        """Test leaderboard with a single model: return value, metadata, HTML output."""
        metrics = {"root_mean_squared_error": 0.5, "mean_absolute_error": 0.4, "r2": 0.9}
        model_dir = create_model_dir(metrics, model_name="Model1")

        columns = ["model", "root_mean_squared_error", "mean_absolute_error", "r2", "notebook", "predictor"]
        rows = [
            (
                1,
                {
                    "model": "Model1",
                    "root_mean_squared_error": 0.5,
                    "mean_absolute_error": 0.4,
                    "r2": 0.9,
                    "notebook": "http://example.com/artifacts/Model1/notebooks/automl_predictor_notebook.ipynb",
                    "predictor": "http://example.com/artifacts/Model1/predictor/predictor.pkl",
                },
            ),
        ]
        mock_df_sorted = _make_mock_sorted_df(rows, columns)
        mock_df = mock.MagicMock()
        mock_df.sort_values.return_value = mock_df_sorted
        mock_dataframe_class.return_value = mock_df

        mock_model = mock.MagicMock()
        mock_model.path = model_dir
        mock_model.uri = "http://example.com/artifacts"
        mock_model.metadata = {"display_name": "Model1"}

        mock_html = mock.MagicMock()
        mock_html.path = html_output_path
        mock_html.metadata = {}

        result = leaderboard_evaluation.python_func(
            models=[mock_model],
            eval_metric="root_mean_squared_error",
            html_artifact=mock_html,
            embedded_artifact=embedded_artifact,
        )

        # Verify DataFrame was constructed with correct data
        mock_dataframe_class.assert_called_once()
        call_args = mock_dataframe_class.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["model"] == "Model1"
        assert call_args[0]["root_mean_squared_error"] == 0.5
        assert call_args[0]["mean_absolute_error"] == 0.4
        assert call_args[0]["r2"] == 0.9
        assert (
            call_args[0]["notebook"] == "http://example.com/artifacts/Model1/notebooks/automl_predictor_notebook.ipynb"
        )
        assert call_args[0]["predictor"] == "http://example.com/artifacts/Model1/predictor/predictor.pkl"

        # Verify sort
        mock_df.sort_values.assert_called_once_with(by="root_mean_squared_error", ascending=False)

        # Verify best_model return value
        assert result.best_model == "Model1"

        # Verify HTML artifact metadata
        assert mock_html.metadata["display_name"] == "automl_leaderboard"
        assert "data" in mock_html.metadata

        # Verify HTML file content
        html = Path(html_output_path).read_text()
        assert "Notebook" in html
        assert "Predictor" in html
        assert "automl_predictor_notebook.ipynb" in html
        assert "Model1" in html
        assert "uri-cell" in html
        assert "uri-link" in html

    @mock.patch("pandas.DataFrame")
    def test_multiple_models(self, mock_dataframe_class, create_model_dir, html_output_path, embedded_artifact):
        """Test leaderboard with multiple models and best_model selection."""
        metrics_list = [
            {"root_mean_squared_error": 0.8, "mean_absolute_error": 0.6},
            {"root_mean_squared_error": 0.3, "mean_absolute_error": 0.2},
            {"root_mean_squared_error": 0.5, "mean_absolute_error": 0.4},
        ]
        model_dirs = [create_model_dir(m, model_name=f"Model{i + 1}") for i, m in enumerate(metrics_list)]

        columns = ["model", "root_mean_squared_error", "mean_absolute_error", "notebook", "predictor"]
        rows = [
            (
                1,
                {
                    "model": "Model2",
                    "root_mean_squared_error": 0.3,
                    "mean_absolute_error": 0.2,
                    "notebook": "nb2",
                    "predictor": "p2",
                },
            ),
            (
                2,
                {
                    "model": "Model3",
                    "root_mean_squared_error": 0.5,
                    "mean_absolute_error": 0.4,
                    "notebook": "nb3",
                    "predictor": "p3",
                },
            ),
            (
                3,
                {
                    "model": "Model1",
                    "root_mean_squared_error": 0.8,
                    "mean_absolute_error": 0.6,
                    "notebook": "nb1",
                    "predictor": "p1",
                },
            ),
        ]
        mock_df_sorted = _make_mock_sorted_df(rows, columns)
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

        mock_html = mock.MagicMock()
        mock_html.path = html_output_path
        mock_html.metadata = {}

        result = leaderboard_evaluation.python_func(
            models=mock_models,
            eval_metric="root_mean_squared_error",
            html_artifact=mock_html,
            embedded_artifact=embedded_artifact,
        )

        # Verify all models were passed to DataFrame
        call_args = mock_dataframe_class.call_args[0][0]
        assert len(call_args) == 3
        assert call_args[0]["model"] == "Model1"
        assert call_args[1]["model"] == "Model2"
        assert call_args[2]["model"] == "Model3"

        # Best model is first after sorting
        assert result.best_model == "Model2"

        mock_df.sort_values.assert_called_once_with(by="root_mean_squared_error", ascending=False)

        # Verify HTML was written with all model data
        html = Path(html_output_path).read_text()
        assert "Notebook" in html and "Predictor" in html
        assert "Model2" in html
        assert "Model3" in html
        assert "Model1" in html

    @mock.patch("pandas.DataFrame")
    def test_round_metrics(self, mock_dataframe_class, create_model_dir, html_output_path, embedded_artifact):
        """Test that metrics are rounded to 4 decimal places."""
        metrics = {"rmse": 0.123456789, "accuracy": 0.987654321}
        model_dir = create_model_dir(metrics, model_name="Model1")

        columns = ["model", "rmse", "accuracy", "notebook", "predictor"]
        rows = [(1, {"model": "Model1", "rmse": 0.1235, "accuracy": 0.9877, "notebook": "nb", "predictor": "p"})]
        mock_df_sorted = _make_mock_sorted_df(rows, columns)
        mock_df = mock.MagicMock()
        mock_df.sort_values.return_value = mock_df_sorted
        mock_dataframe_class.return_value = mock_df

        mock_model = mock.MagicMock()
        mock_model.path = model_dir
        mock_model.uri = "http://example.com/artifacts"
        mock_model.metadata = {"display_name": "Model1"}

        mock_html = mock.MagicMock()
        mock_html.path = html_output_path
        mock_html.metadata = {}

        leaderboard_evaluation.python_func(
            models=[mock_model],
            eval_metric="rmse",
            html_artifact=mock_html,
            embedded_artifact=embedded_artifact,
        )

        call_args = mock_dataframe_class.call_args[0][0]
        assert call_args[0]["rmse"] == 0.1235
        assert call_args[0]["accuracy"] == 0.9877

    @mock.patch("pandas.DataFrame")
    def test_round_metrics_preserves_non_numeric(
        self, mock_dataframe_class, create_model_dir, html_output_path, embedded_artifact
    ):
        """Test that non-numeric metric values pass through _round_metrics unchanged."""
        metrics = {"rmse": 0.123456789, "description": "some_text"}
        model_dir = create_model_dir(metrics, model_name="Model1")

        columns = ["model", "rmse", "description", "notebook", "predictor"]
        rows = [
            (1, {"model": "Model1", "rmse": 0.1235, "description": "some_text", "notebook": "nb", "predictor": "p"})
        ]
        mock_df_sorted = _make_mock_sorted_df(rows, columns)
        mock_df = mock.MagicMock()
        mock_df.sort_values.return_value = mock_df_sorted
        mock_dataframe_class.return_value = mock_df

        mock_model = mock.MagicMock()
        mock_model.path = model_dir
        mock_model.uri = "http://example.com/artifacts"
        mock_model.metadata = {"display_name": "Model1"}

        mock_html = mock.MagicMock()
        mock_html.path = html_output_path
        mock_html.metadata = {}

        leaderboard_evaluation.python_func(
            models=[mock_model],
            eval_metric="rmse",
            html_artifact=mock_html,
            embedded_artifact=embedded_artifact,
        )

        call_args = mock_dataframe_class.call_args[0][0]
        assert call_args[0]["rmse"] == 0.1235
        assert call_args[0]["description"] == "some_text"

    def test_missing_display_name_raises(self, html_output_path, embedded_artifact):
        """Test that missing display_name in metadata raises KeyError."""
        mock_model = mock.MagicMock()
        mock_model.path = "/tmp/some_path"
        mock_model.uri = "http://example.com/artifacts"
        mock_model.metadata = {}  # No display_name

        mock_html = mock.MagicMock()
        mock_html.path = html_output_path
        mock_html.metadata = {}

        with pytest.raises(KeyError):
            leaderboard_evaluation.python_func(
                models=[mock_model],
                eval_metric="rmse",
                html_artifact=mock_html,
                embedded_artifact=embedded_artifact,
            )

    def test_leaderboard_evaluation_rejects_empty_eval_metric(self, embedded_artifact):
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
                embedded_artifact=embedded_artifact,
            )

        with pytest.raises(TypeError, match=r"eval_metric must be a non-empty string\."):
            leaderboard_evaluation.python_func(
                models=[mock_model],
                eval_metric="   ",
                html_artifact=mock_html,
                embedded_artifact=embedded_artifact,
            )

    def test_leaderboard_evaluation_rejects_empty_models_list(self, embedded_artifact):
        """Test that TypeError is raised when models is empty or not a list."""
        mock_html = mock.MagicMock()
        mock_html.path = "/tmp/out.html"

        with pytest.raises(TypeError, match=r"models must be a non-empty list\."):
            leaderboard_evaluation.python_func(
                models=[],
                eval_metric="root_mean_squared_error",
                html_artifact=mock_html,
                embedded_artifact=embedded_artifact,
            )

        with pytest.raises(TypeError, match=r"models must be a non-empty list\."):
            leaderboard_evaluation.python_func(
                models="not_a_list",
                eval_metric="root_mean_squared_error",
                html_artifact=mock_html,
                embedded_artifact=embedded_artifact,
            )

    def test_missing_metrics_file_raises(self, tmp_path, html_output_path, embedded_artifact):
        """Test that missing metrics.json raises FileNotFoundError."""
        model_dir = tmp_path / "model_artifact_empty"
        model_dir.mkdir()

        mock_model = mock.MagicMock()
        mock_model.path = str(model_dir)
        mock_model.uri = "http://example.com/artifacts"
        mock_model.metadata = {"display_name": "Model1"}

        mock_html = mock.MagicMock()
        mock_html.path = html_output_path
        mock_html.metadata = {}

        with pytest.raises(FileNotFoundError):
            leaderboard_evaluation.python_func(
                models=[mock_model],
                eval_metric="rmse",
                html_artifact=mock_html,
                embedded_artifact=embedded_artifact,
            )

    def test_component_imports_correctly(self):
        """Test that the component can be imported and has required attributes."""
        assert callable(leaderboard_evaluation)
        assert hasattr(leaderboard_evaluation, "python_func")
        assert hasattr(leaderboard_evaluation, "component_spec")
