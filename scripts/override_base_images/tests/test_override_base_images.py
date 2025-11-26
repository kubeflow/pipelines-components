"""Tests for override_base_images script."""

from pathlib import Path

import pytest

from ...lib.base_image import override_base_images, override_file_images
from ...lib.tests import copy_fixture

IMAGE_PREFIX = "ghcr.io/kubeflow/pipelines-components"
TEST_CONTAINER_TAG = "abc123def456789"
TEST_DATA_DIR = Path(__file__).parent / "test_data"


class TestOverrideFileImages:
    """Tests for override_file_images function."""

    def test_overrides_main_tag(self, tmp_path: Path):
        """Rewrites :main tags to the provided container tag."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_main_tag.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f"{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}" in content

    def test_dry_run_does_not_modify(self, tmp_path: Path):
        """In dry-run mode, returns new content but does not write the file."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_main_tag.py", tmp_path / "component.py")
        original = py_file.read_text()

        was_modified, new_content = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX, dry_run=True)

        assert was_modified is True
        assert new_content is not None
        assert ":main" not in new_content
        assert f"{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}" in new_content
        assert py_file.read_text() == original

    def test_no_modification_when_no_match(self, tmp_path: Path):
        """Does not modify files without matching :main references."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_non_matching.py", tmp_path / "component.py")
        original = py_file.read_text()

        was_modified, new_content = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        assert was_modified is False
        assert new_content is None
        assert py_file.read_text() == original

    def test_overrides_multiple_references(self, tmp_path: Path):
        """Rewrites multiple :main references within a single file."""
        py_file = copy_fixture(TEST_DATA_DIR, "multiple_components.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert f"{IMAGE_PREFIX}-first:{TEST_CONTAINER_TAG}" in content
        assert f"{IMAGE_PREFIX}-second:{TEST_CONTAINER_TAG}" in content
        assert ":main" not in content

    def test_ignores_non_main_tags(self, tmp_path: Path):
        """Does not rewrite base_image values that are not tagged :main."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_version_tag.py", tmp_path / "component.py")
        original = py_file.read_text()

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        assert was_modified is False
        assert py_file.read_text() == original

    def test_raises_on_missing_file(self, tmp_path: Path):
        """Raises when the target Python file does not exist."""
        py_file = tmp_path / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

    def test_preserves_surrounding_content(self, tmp_path: Path):
        """Preserves non-base_image content while rewriting :main tags."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_with_extras.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert '"""My component."""' in content
        assert "from kfp import dsl" in content
        assert 'packages_to_install=["numpy"]' in content
        assert "def my_component(value: int) -> str:" in content

    def test_accepts_release_tag(self, tmp_path: Path):
        """Rewrites :main to release container tags like v1.11.0."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_main_tag.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, "v1.11.0", IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f"{IMAGE_PREFIX}-example:v1.11.0" in content

    def test_preserves_single_quotes(self, tmp_path: Path):
        """Preserves single quotes when the original uses single quotes."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_single_quotes.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f"'{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}'" in content

    def test_preserves_double_quotes(self, tmp_path: Path):
        """Preserves double quotes when the original uses double quotes."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_main_tag.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f'"{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}"' in content

    def test_preserves_triple_double_quotes(self, tmp_path: Path):
        """Preserves triple double quotes when the original uses triple double quotes."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_triple_quotes.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f'"""{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}"""' in content

    def test_preserves_triple_single_quotes(self, tmp_path: Path):
        """Preserves triple single quotes when the original uses triple single quotes."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_triple_single_quotes.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f"'''{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}'''" in content

    def test_handles_short_image_suffix(self, tmp_path: Path):
        """Handles short image suffixes without IndexError from quote detection slicing."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_short_image.py", tmp_path / "component.py")

        was_modified, _ = override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert ":main" not in content
        assert f"'{IMAGE_PREFIX}-x:{TEST_CONTAINER_TAG}'" in content

    def test_raises_on_non_literal_base_image(self, tmp_path: Path):
        """Raises ValueError when base_image is not a string literal."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_variable_base_image.py", tmp_path / "component.py")

        with pytest.raises(ValueError, match="base_image must be a string literal"):
            override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)

    def test_raises_on_multiline_base_image(self, tmp_path: Path):
        """Raises ValueError when base_image spans multiple lines."""
        py_file = copy_fixture(TEST_DATA_DIR, "component_multiline_base_image.py", tmp_path / "component.py")

        with pytest.raises(ValueError, match="Multi-line base_image values are not supported"):
            override_file_images(py_file, TEST_CONTAINER_TAG, IMAGE_PREFIX)


class TestOverrideBaseImages:
    """Integration tests for override_base_images function."""

    def test_modifies_files_in_directory(self, tmp_path: Path):
        """Rewrites matching references when scanning a directory."""
        components = tmp_path / "components"
        components.mkdir()
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", components / "comp.py")

        modified = override_base_images([str(components)], TEST_CONTAINER_TAG, IMAGE_PREFIX, verbose=False)

        content = (components / "comp.py").read_text()
        assert len(modified) == 1
        assert ":main" not in content
        assert f"{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}" in content

    def test_returns_list_of_modified_files(self, tmp_path: Path):
        """Returns the file paths that were modified."""
        components = tmp_path / "components"
        components.mkdir()
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", components / "a.py")
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", components / "b.py")
        copy_fixture(TEST_DATA_DIR, "component_non_matching.py", components / "c.py")

        modified = override_base_images([str(components)], TEST_CONTAINER_TAG, IMAGE_PREFIX, verbose=False)

        assert len(modified) == 2
        modified_names = {Path(f).name for f in modified}
        assert modified_names == {"a.py", "b.py"}

    def test_dry_run_returns_files_but_no_changes(self, tmp_path: Path):
        """In dry-run mode, reports would-be modified files but does not rewrite content."""
        components = tmp_path / "components"
        components.mkdir()
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", components / "comp.py")
        original = (components / "comp.py").read_text()

        modified = override_base_images(
            [str(components)], TEST_CONTAINER_TAG, IMAGE_PREFIX, dry_run=True, verbose=False
        )

        assert len(modified) == 1
        assert (components / "comp.py").read_text() == original

    def test_scans_subdirectories(self, tmp_path: Path):
        """Finds and rewrites references in nested subdirectories."""
        components = tmp_path / "components"
        subdir = components / "training" / "my_component"
        subdir.mkdir(parents=True)
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", subdir / "component.py")

        modified = override_base_images([str(components)], TEST_CONTAINER_TAG, IMAGE_PREFIX, verbose=False)

        content = (subdir / "component.py").read_text()
        assert len(modified) == 1
        assert ":main" not in content
        assert f"{IMAGE_PREFIX}-example:{TEST_CONTAINER_TAG}" in content

    def test_handles_nonexistent_directory(self, tmp_path: Path):
        """Returns an empty list when a directory does not exist."""
        modified = override_base_images(
            [str(tmp_path / "nonexistent")], TEST_CONTAINER_TAG, IMAGE_PREFIX, verbose=False
        )

        assert modified == []

    def test_multiple_directories(self, tmp_path: Path):
        """Scans multiple directories and rewrites matches in each."""
        components = tmp_path / "components"
        components.mkdir()
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", components / "c.py")

        pipelines = tmp_path / "pipelines"
        pipelines.mkdir()
        copy_fixture(TEST_DATA_DIR, "component_main_tag.py", pipelines / "p.py")

        modified = override_base_images(
            [str(components), str(pipelines)], TEST_CONTAINER_TAG, IMAGE_PREFIX, verbose=False
        )

        assert len(modified) == 2
