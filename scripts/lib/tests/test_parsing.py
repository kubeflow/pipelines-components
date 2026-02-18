"""Tests for parsing module."""

from pathlib import Path

import pytest

from ..parsing import get_base_image_locations
from . import copy_fixture

TEST_DATA_DIR = Path(__file__).parent / "test_data"


class TestGetBaseImageLocations:
    """Tests for get_base_image_locations function."""

    def test_extracts_literal_base_image(self, tmp_path: Path):
        """Test extraction of a string literal base_image."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_literal_base_image.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        assert results[0].func_name == "my_component"
        assert results[0].value == "quay.io/org/image:main"

    def test_extracts_multiple_base_images(self, tmp_path: Path):
        """Test extraction of multiple base_images from different decorators."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_multiple_base_images.py", tmp_path / "components.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 2
        values = {r.value for r in results}
        assert values == {"quay.io/org/image1:main", "quay.io/org/image2:main"}

    def test_raises_on_variable_base_image(self, tmp_path: Path):
        """Test that ValueError is raised when base_image is a variable."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_variable_base_image.py", tmp_path / "component.py")

        with pytest.raises(ValueError, match="base_image must be a string literal"):
            get_base_image_locations(file_path)

    def test_raises_on_fstring_base_image(self, tmp_path: Path):
        """Test that ValueError is raised when base_image is an f-string."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_fstring_base_image.py", tmp_path / "component.py")

        with pytest.raises(ValueError, match="base_image must be a string literal"):
            get_base_image_locations(file_path)

    def test_returns_empty_for_no_base_image(self, tmp_path: Path):
        """Test that empty list is returned when no base_image is specified."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_no_base_image.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert results == []

    def test_returns_empty_for_decorator_without_call(self, tmp_path: Path):
        """Test that empty list is returned for @dsl.component without parentheses."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_no_base_image.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert results == []

    def test_handles_pipeline_decorator(self, tmp_path: Path):
        """Test extraction from @dsl.pipeline decorator."""
        file_path = copy_fixture(TEST_DATA_DIR, "pipeline_with_base_image.py", tmp_path / "pipeline.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        assert results[0].func_name == "my_pipeline"
        assert results[0].value == "quay.io/org/pipeline-image:main"

    def test_handles_direct_import_decorator(self, tmp_path: Path):
        """Test extraction with 'from kfp.dsl import component' style."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_direct_import.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        assert results[0].value == "quay.io/org/image:main"

    def test_handles_kfp_dsl_component_decorator(self, tmp_path: Path):
        """Test extraction with 'import kfp' and @kfp.dsl.component style."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_kfp_dsl_style.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        assert results[0].value == "quay.io/org/image:main"

    def test_handles_container_component_decorator(self, tmp_path: Path):
        """Test extraction from @dsl.container_component decorator."""
        file_path = copy_fixture(TEST_DATA_DIR, "container_component.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        assert results[0].func_name == "my_container_component"
        assert results[0].value == "quay.io/org/container:main"

    def test_handles_notebook_component_decorator(self, tmp_path: Path):
        """Test extraction from @dsl.notebook_component decorator."""
        file_path = copy_fixture(TEST_DATA_DIR, "notebook_component.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        assert results[0].func_name == "my_notebook_component"
        assert results[0].value == "quay.io/org/notebook:main"

    def test_col_offset_points_to_opening_quote(self, tmp_path: Path):
        """Verify AST col_offset points to the opening quote character."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_double_quotes.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        bi = results[0]
        source = file_path.read_text()
        lines = source.splitlines()
        assert lines[bi.start_line - 1][bi.start_col] == '"'

    def test_col_offset_points_to_opening_single_quote(self, tmp_path: Path):
        """Verify AST col_offset points to opening single quote."""
        file_path = copy_fixture(TEST_DATA_DIR, "component_single_quotes.py", tmp_path / "component.py")

        results = get_base_image_locations(file_path)

        assert len(results) == 1
        bi = results[0]
        source = file_path.read_text()
        lines = source.splitlines()
        assert lines[bi.start_line - 1][bi.start_col] == "'"
