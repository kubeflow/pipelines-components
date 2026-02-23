"""Tests for lora pipeline."""

from kfp import compiler

from ..pipeline import lora_pipeline


class TestLoraPipeline:
    """Basic tests for LoRA pipeline."""

    def test_pipeline_function_exists(self):
        """Test that the pipeline function is properly defined."""
        assert callable(lora_pipeline)

    def test_pipeline_compiles(self, tmp_path):
        """Test that the pipeline compiles successfully."""
        output_path = tmp_path / "pipeline.yaml"
        compiler.Compiler().compile(
            pipeline_func=lora_pipeline,
            package_path=str(output_path),
        )
        assert output_path.exists()
