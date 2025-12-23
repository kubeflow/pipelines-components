"""Tests for the CLI functionality of generate_skeleton.py"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ..generate_skeleton import main


class TestCLI:
    """Test the command line interface."""

    def test_help_message(self):
        """Test that help message is displayed."""
        with patch("sys.argv", ["generate_skeleton.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_missing_required_arguments(self):
        """Test error when required arguments are missing."""
        test_cases = [
            ["generate_skeleton.py"],  # No arguments
            ["generate_skeleton.py", "--type=component"],  # Missing category and name
            ["generate_skeleton.py", "--category=data_processing"],  # Missing type and name
        ]

        for args in test_cases:
            with patch("sys.argv", args):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # Should exit with non-zero code
                assert exc_info.value.code != 0

    def test_invalid_name_format(self):
        """Test error when name has invalid format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()

            os.chdir(temp_dir)

            try:
                args = [
                    "generate_skeleton.py",
                    "--type=component",
                    "--category=data_processing",
                    "--name=invalid-name-with-hyphens",
                ]

                with patch("sys.argv", args):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Should exit with error code
                    assert exc_info.value.code == 1
            finally:
                os.chdir(original_cwd)

    def test_conflicting_options(self):
        """Test error when conflicting options are provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()

            os.chdir(temp_dir)

            try:
                args = [
                    "generate_skeleton.py",
                    "--type=component",
                    "--category=data_processing",
                    "--name=my_processor",
                    "--no-tests",
                    "--tests-only",
                ]

                with patch("sys.argv", args):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Should exit with error code
                    assert exc_info.value.code == 1
            finally:
                os.chdir(original_cwd)

    def test_successful_component_creation(self):
        """Test successful component creation via CLI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()

            os.chdir(temp_dir)

            try:
                args = ["generate_skeleton.py", "--type=component", "--category=data_processing", "--name=my_processor"]

                # Mock the working directory change to stay in temp_dir
                def mock_chdir(_path):
                    pass  # Do nothing instead of changing directory

                with patch("sys.argv", args):
                    with patch("os.chdir", mock_chdir):
                        # Should not raise any exception
                        main()

                # Check that files were created
                component_dir = Path("components/data_processing/my_processor")
                assert component_dir.exists()
                assert (component_dir / "component.py").exists()
                assert (component_dir / "tests").exists()

            finally:
                os.chdir(original_cwd)

    def test_successful_pipeline_creation_no_tests(self):
        """Test successful pipeline creation without tests via CLI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()

            os.chdir(temp_dir)

            try:
                args = [
                    "generate_skeleton.py",
                    "--type=pipeline",
                    "--category=training",
                    "--name=my_pipeline",
                    "--no-tests",
                ]

                # Mock the working directory change to stay in temp_dir
                def mock_chdir(_path):
                    pass  # Do nothing instead of changing directory

                with patch("sys.argv", args):
                    with patch("os.chdir", mock_chdir):
                        # Should not raise any exception
                        main()

                # Check that files were created
                pipeline_dir = Path("pipelines/training/my_pipeline")
                assert pipeline_dir.exists()
                assert (pipeline_dir / "pipeline.py").exists()
                assert not (pipeline_dir / "tests").exists()

            finally:
                os.chdir(original_cwd)

    def test_tests_only_mode(self):
        """Test creating tests only for existing skeleton via CLI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()

            try:
                # Create a temporary project structure in temp dir
                os.chdir(temp_dir)

                # First create skeleton without tests using the function directly
                # (to avoid the working directory change in main())
                from ..generate_skeleton import create_skeleton

                create_skeleton("component", "data_processing", "my_processor", create_tests=False)

                # Now test the tests-only CLI functionality
                args = [
                    "generate_skeleton.py",
                    "--type=component",
                    "--category=data_processing",
                    "--name=my_processor",
                    "--tests-only",
                ]

                # Mock the working directory change to stay in temp_dir
                def mock_chdir(_path):
                    pass  # Do nothing instead of changing directory

                with patch("sys.argv", args):
                    with patch("os.chdir", mock_chdir):
                        main()

                # Check that tests were created
                component_dir = Path("components/data_processing/my_processor")
                assert component_dir.exists()
                assert (component_dir / "tests").exists()
                assert (component_dir / "tests" / "test_component_unit.py").exists()

            finally:
                os.chdir(original_cwd)
