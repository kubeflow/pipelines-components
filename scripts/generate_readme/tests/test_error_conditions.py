"""Tests for error conditions in README generator.

These minimal unit tests verify that the generator properly handles error cases.
"""

import tempfile
from pathlib import Path

import pytest

from generate_readme.metadata_parser import MetadataParser
from generate_readme.writer import ReadmeWriter


class TestMissingDocstring:
    """Test that missing docstrings are properly detected."""

    def test_component_missing_docstring_raises_error(self):
        """Component without docstring should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            component_file = Path(tmpdir) / "component.py"
            component_file.write_text("""
from kfp import dsl

@dsl.component
def my_component(param: str) -> str:
    return param
""")

            parser = MetadataParser(component_file, "component")

            with pytest.raises(ValueError, match="missing required docstring"):
                parser.extract_metadata("my_component")

    def test_pipeline_missing_docstring_raises_error(self):
        """Pipeline without docstring should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline_file = Path(tmpdir) / "pipeline.py"
            pipeline_file.write_text("""
from kfp import dsl

@dsl.pipeline
def my_pipeline(param: str):
    pass
""")

            parser = MetadataParser(pipeline_file, "pipeline")

            with pytest.raises(ValueError, match="missing required docstring"):
                parser.extract_metadata("my_pipeline")


class TestInvalidPaths:
    """Test that invalid paths are handled properly."""

    def test_writer_requires_component_or_pipeline_dir(self):
        """Writer should require exactly one of component_dir or pipeline_dir."""
        with pytest.raises(ValueError, match="Either component_dir or pipeline_dir must be provided"):
            ReadmeWriter()

    def test_writer_rejects_both_directories(self):
        """Writer should reject both component_dir and pipeline_dir."""
        with pytest.raises(ValueError, match="Cannot specify both component_dir and pipeline_dir"):
            ReadmeWriter(component_dir=Path("/tmp/comp"), pipeline_dir=Path("/tmp/pipe"))

    def test_metadata_parser_nonexistent_file(self):
        """MetadataParser should handle nonexistent files."""
        parser = MetadataParser(Path("/nonexistent/file.py"), "component")

        with pytest.raises((FileNotFoundError, ValueError)):
            parser.extract_metadata("some_function")
