"""Tests for lora_minimal pipeline."""

from kfp import compiler

from ..pipeline import lora_minimal_pipeline


class TestLoraMinimalPipeline:
    """Basic tests for LoRA minimal pipeline."""

    def test_pipeline_function_exists(self):
        """Test that the pipeline function is properly defined."""
        assert callable(lora_minimal_pipeline)

    def test_pipeline_compiles(self, tmp_path):
        """Test that the pipeline compiles successfully."""
        output_path = tmp_path / "pipeline.yaml"
        compiler.Compiler().compile(
            pipeline_func=lora_minimal_pipeline,
            package_path=str(output_path),
        )
        assert output_path.exists()
