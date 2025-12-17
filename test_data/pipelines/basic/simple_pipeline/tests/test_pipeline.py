"""Tests for simple_pipeline."""

import pytest
from kfp import compiler

from ..pipeline import simple_pipeline


def test_pipeline_compiles():
    """Test that the pipeline compiles successfully."""
    try:
        compiler.Compiler().compile(pipeline_func=simple_pipeline, package_path="/tmp/test_pipeline.yaml")
    except Exception as e:
        pytest.fail(f"Pipeline compilation failed: {e}")


def test_pipeline_default_params():
    """Test pipeline with default parameters."""
    # This test would typically check the compiled YAML structure
    # For now, just verify it doesn't raise exceptions
    try:
        simple_pipeline()
    except Exception as e:
        pytest.fail(f"Pipeline execution with defaults failed: {e}")


def test_pipeline_custom_params():
    """Test pipeline with custom parameters."""
    try:
        simple_pipeline(input_text="custom", iterations=5)
    except Exception as e:
        pytest.fail(f"Pipeline execution with custom params failed: {e}")
