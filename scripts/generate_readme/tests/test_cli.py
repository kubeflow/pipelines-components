"""Tests for cli.py module."""

import argparse
from pathlib import Path

import pytest

from scripts.generate_readme.cli import (
    parse_arguments,
    validate_component_directory,
    validate_pipeline_directory,
)


class TestValidateComponentDirectory:
    """Tests for validate_component_directory function."""

    def test_valid_component_directory(self, component_dir):
        """Test validation of a valid component directory."""
        result = validate_component_directory(str(component_dir))

        assert result == component_dir
        assert isinstance(result, Path)

    def test_nonexistent_directory(self):
        """Test validation fails for non-existent directory."""
        with pytest.raises(argparse.ArgumentTypeError, match="does not exist"):
            validate_component_directory("/nonexistent/path")

    def test_not_a_directory(self, temp_dir):
        """Test validation fails for file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")

        with pytest.raises(argparse.ArgumentTypeError, match="not a directory"):
            validate_component_directory(str(file_path))

    def test_missing_component_file(self, temp_dir):
        """Test validation fails when component.py is missing."""
        comp_dir = temp_dir / "component"
        comp_dir.mkdir()
        (comp_dir / "metadata.yaml").write_text("name: test")

        with pytest.raises(argparse.ArgumentTypeError, match="does not contain a component.py"):
            validate_component_directory(str(comp_dir))

    def test_missing_metadata_file(self, temp_dir):
        """Test validation fails when metadata.yaml is missing."""
        comp_dir = temp_dir / "component"
        comp_dir.mkdir()
        (comp_dir / "component.py").write_text("# Component code")

        with pytest.raises(argparse.ArgumentTypeError, match="does not contain a metadata.yaml"):
            validate_component_directory(str(comp_dir))


class TestValidatePipelineDirectory:
    """Tests for validate_pipeline_directory function."""

    def test_valid_pipeline_directory(self, pipeline_dir):
        """Test validation of a valid pipeline directory."""
        result = validate_pipeline_directory(str(pipeline_dir))

        assert result == pipeline_dir
        assert isinstance(result, Path)

    def test_nonexistent_directory(self):
        """Test validation fails for non-existent directory."""
        with pytest.raises(argparse.ArgumentTypeError, match="does not exist"):
            validate_pipeline_directory("/nonexistent/path")

    def test_not_a_directory(self, temp_dir):
        """Test validation fails for file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")

        with pytest.raises(argparse.ArgumentTypeError, match="not a directory"):
            validate_pipeline_directory(str(file_path))

    def test_missing_pipeline_file(self, temp_dir):
        """Test validation fails when pipeline.py is missing."""
        pipe_dir = temp_dir / "pipeline"
        pipe_dir.mkdir()
        (pipe_dir / "metadata.yaml").write_text("name: test")

        with pytest.raises(argparse.ArgumentTypeError, match="does not contain a pipeline.py"):
            validate_pipeline_directory(str(pipe_dir))

    def test_missing_metadata_file(self, temp_dir):
        """Test validation fails when metadata.yaml is missing."""
        pipe_dir = temp_dir / "pipeline"
        pipe_dir.mkdir()
        (pipe_dir / "pipeline.py").write_text("# Pipeline code")

        with pytest.raises(argparse.ArgumentTypeError, match="does not contain a metadata.yaml"):
            validate_pipeline_directory(str(pipe_dir))


class TestParseArguments:
    """Tests for parse_arguments function."""

    def test_parse_component_argument(self, component_dir, monkeypatch):
        """Test parsing --component argument."""
        monkeypatch.setattr("sys.argv", ["prog", "--component", str(component_dir)])

        args = parse_arguments()

        assert args.component == component_dir
        assert args.pipeline is None
        assert args.verbose is False
        assert args.fix is False

    def test_parse_pipeline_argument(self, pipeline_dir, monkeypatch):
        """Test parsing --pipeline argument."""
        monkeypatch.setattr("sys.argv", ["prog", "--pipeline", str(pipeline_dir)])

        args = parse_arguments()

        assert args.pipeline == pipeline_dir
        assert args.component is None

    def test_parse_verbose_flag(self, component_dir, monkeypatch):
        """Test parsing --verbose flag."""
        monkeypatch.setattr("sys.argv", ["prog", "--component", str(component_dir), "--verbose"])

        args = parse_arguments()

        assert args.verbose is True

    def test_parse_fix_flag(self, component_dir, monkeypatch):
        """Test parsing --fix flag."""
        monkeypatch.setattr("sys.argv", ["prog", "--component", str(component_dir), "--fix"])

        args = parse_arguments()

        assert args.fix is True

    def test_parse_output_argument(self, component_dir, temp_dir, monkeypatch):
        """Test parsing --output argument."""
        output_file = temp_dir / "custom_readme.md"
        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--component", str(component_dir), "--output", str(output_file)],
        )

        args = parse_arguments()

        assert args.output == output_file

    def test_parse_short_flags(self, component_dir, temp_dir, monkeypatch):
        """Test parsing short flag versions."""
        output_file = temp_dir / "readme.md"
        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--component", str(component_dir), "-v", "-o", str(output_file)],
        )

        args = parse_arguments()

        assert args.verbose is True
        assert args.output == output_file

    def test_parse_invalid_component_path(self, monkeypatch):
        """Test parsing with invalid component path."""
        monkeypatch.setattr("sys.argv", ["prog", "--component", "/invalid/path"])

        with pytest.raises(SystemExit):
            parse_arguments()

    def test_parse_no_arguments(self, monkeypatch):
        """Test parsing with no arguments raises error (--component or --pipeline required)."""
        monkeypatch.setattr("sys.argv", ["prog"])

        # Should fail because --component or --pipeline is required
        with pytest.raises(SystemExit) as exc_info:
            parse_arguments()

        assert exc_info.value.code == 2

    def test_help_message(self, monkeypatch, capsys):
        """Test that help message can be displayed."""
        monkeypatch.setattr("sys.argv", ["prog", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            parse_arguments()

        # Help should exit with code 0
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Generate README.md documentation" in captured.out
        assert "--component" in captured.out
        assert "--pipeline" in captured.out


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_component_and_pipeline_validation(self, component_dir, pipeline_dir):
        """Test that providing both component and pipeline is handled correctly."""
        # The validation happens in main(), not parse_arguments()
        # Here we just ensure both can be parsed
        comp_result = validate_component_directory(str(component_dir))
        pipe_result = validate_pipeline_directory(str(pipeline_dir))

        assert comp_result == component_dir
        assert pipe_result == pipeline_dir

    def test_path_conversion(self, component_dir):
        """Test that string paths are converted to Path objects."""
        result = validate_component_directory(str(component_dir))

        assert isinstance(result, Path)
        assert result.is_dir()

    def test_relative_path_validation(self, component_dir, monkeypatch):
        """Test validation works with relative paths."""
        # Change to parent directory and use relative path
        parent = component_dir.parent
        relative_path = component_dir.name

        monkeypatch.chdir(parent)
        result = validate_component_directory(relative_path)

        # Result should be a valid Path object
        assert isinstance(result, Path)
        assert result.name == component_dir.name
