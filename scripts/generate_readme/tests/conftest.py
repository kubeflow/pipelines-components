"""Shared pytest fixtures for generate_readme tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def component_dir(temp_dir):
    """Create a minimal valid component directory for testing."""
    comp_dir = temp_dir / "test_component"
    comp_dir.mkdir()

    # Create minimal component.py
    (comp_dir / "component.py").write_text("""
from kfp import dsl

@dsl.component
def test_component(input_param: str) -> str:
    \"\"\"Test component.

    Args:
        input_param: Input parameter.

    Returns:
        Output value.
    \"\"\"
    return input_param
""")

    # Create minimal metadata.yaml
    (comp_dir / "metadata.yaml").write_text("""
name: Test Component
description: Test component for CLI tests
""")

    return comp_dir


@pytest.fixture
def pipeline_dir(temp_dir):
    """Create a minimal valid pipeline directory for testing."""
    pipe_dir = temp_dir / "test_pipeline"
    pipe_dir.mkdir()

    # Create minimal pipeline.py
    (pipe_dir / "pipeline.py").write_text("""
from kfp import dsl

@dsl.pipeline
def test_pipeline(input_param: str):
    \"\"\"Test pipeline.

    Args:
        input_param: Input parameter.
    \"\"\"
    pass
""")

    # Create minimal metadata.yaml
    (pipe_dir / "metadata.yaml").write_text("""
name: Test Pipeline
description: Test pipeline for CLI tests
""")

    return pipe_dir
