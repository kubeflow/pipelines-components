"""Tests for the autogluon_tabular_training_pipeline pipeline."""

import tempfile
from pathlib import Path

import pytest
from kfp import compiler

from ..pipeline import autogluon_tabular_training_pipeline


class TestAutogluonTabularTrainingPipelineUnitTests:
    """Unit tests for pipeline logic."""

    def test_pipeline_function_exists(self):
        """Test that the pipeline function is properly imported."""
        assert callable(autogluon_tabular_training_pipeline)

    def test_pipeline_compiles(self):
        """Test that the pipeline compiles successfully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            compiler.Compiler().compile(
                pipeline_func=autogluon_tabular_training_pipeline,
                package_path=tmp_path,
            )
            assert Path(tmp_path).exists()
        except Exception as e:
            pytest.fail(f"Pipeline compilation failed: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_pipeline_signature(self):
        """Test that the pipeline has the expected parameters."""
        # KFP pipelines expose parameters via component_spec.inputs, not inspect.signature
        expected_params = {
            "train_data_secret_name",
            "train_data_bucket_name",
            "train_data_file_key",
            "label_column",
            "task_type",
            "top_n",
        }
        inputs = autogluon_tabular_training_pipeline.component_spec.inputs
        params = set(inputs.keys())
        assert params == expected_params, f"Pipeline params {params} != expected {expected_params}"
        assert inputs["top_n"].default == 3

    def test_compiled_pipeline_has_expected_inputs(self):
        """Test that the compiled pipeline YAML contains expected pipeline inputs."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            compiler.Compiler().compile(
                pipeline_func=autogluon_tabular_training_pipeline,
                package_path=tmp_path,
            )
            content = Path(tmp_path).read_text()
            for name in (
                "train_data_secret_name",
                "train_data_bucket_name",
                "train_data_file_key",
                "label_column",
                "task_type",
                "top_n",
            ):
                assert name in content, f"Expected pipeline input '{name}' in compiled YAML"
        except Exception as e:
            pytest.fail(f"Pipeline compilation or validation failed: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
