"""Tests for the SDG pipeline."""

from pathlib import Path

from kfp import compiler

from ..pipeline import sdg_llm_pipeline


def test_pipeline_compiles(tmp_path: Path):
    """Test that the pipeline compiles successfully from the library package."""
    output_path = tmp_path / "sdg_llm_pipeline.yaml"

    compiler.Compiler().compile(
        pipeline_func=sdg_llm_pipeline,
        package_path=str(output_path),
    )

    assert output_path.exists()
    assert "sdg-llm-test-pipeline" in output_path.read_text(encoding="utf-8")
