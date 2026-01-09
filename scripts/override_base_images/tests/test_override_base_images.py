"""Tests for override_base_images script."""

from pathlib import Path

import pytest

from ...lib.base_image import override_base_images, override_file_images

IMAGE_PREFIX = "ghcr.io/kubeflow/pipelines-components"
COMMIT_SHA = "abc123def456789"


class TestOverrideFileImages:
    """Tests for override_file_images function."""

    def test_overrides_main_tag(self, tmp_path: Path):
        """Rewrites :main tags to the provided commit SHA tag."""
        py_file = tmp_path / "component.py"
        original = f'@dsl.component(base_image="{IMAGE_PREFIX}-example:main")'
        py_file.write_text(original)

        was_modified, _ = override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX)

        assert was_modified is True
        assert f"{IMAGE_PREFIX}-example:{COMMIT_SHA}" in py_file.read_text()

    def test_dry_run_does_not_modify(self, tmp_path: Path):
        """In dry-run mode, returns new content but does not write the file."""
        py_file = tmp_path / "component.py"
        original = f'@dsl.component(base_image="{IMAGE_PREFIX}-example:main")'
        py_file.write_text(original)

        was_modified, new_content = override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX, dry_run=True)

        assert was_modified is True
        assert new_content is not None
        assert f"{IMAGE_PREFIX}-example:{COMMIT_SHA}" in new_content
        assert py_file.read_text() == original

    def test_no_modification_when_no_match(self, tmp_path: Path):
        """Does not modify files without matching :main references."""
        py_file = tmp_path / "component.py"
        original = '@dsl.component(base_image="python:3.11")'
        py_file.write_text(original)

        was_modified, new_content = override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX)

        assert was_modified is False
        assert new_content is None
        assert py_file.read_text() == original

    def test_overrides_multiple_references(self, tmp_path: Path):
        """Rewrites multiple :main references within a single file."""
        py_file = tmp_path / "component.py"
        original = f"""
@dsl.component(base_image="{IMAGE_PREFIX}-first:main")
def first(): pass

@dsl.component(base_image="{IMAGE_PREFIX}-second:main")
def second(): pass
"""
        py_file.write_text(original)

        was_modified, _ = override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert f"{IMAGE_PREFIX}-first:{COMMIT_SHA}" in content
        assert f"{IMAGE_PREFIX}-second:{COMMIT_SHA}" in content
        assert ":main" not in content

    def test_ignores_non_main_tags(self, tmp_path: Path):
        """Does not rewrite base_image values that are not tagged :main."""
        py_file = tmp_path / "component.py"
        original = f'@dsl.component(base_image="{IMAGE_PREFIX}-example:v1.0.0")'
        py_file.write_text(original)

        was_modified, _ = override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX)

        assert was_modified is False
        assert py_file.read_text() == original

    def test_raises_on_missing_file(self, tmp_path: Path):
        """Raises when the target Python file does not exist."""
        py_file = tmp_path / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX)

    def test_preserves_surrounding_content(self, tmp_path: Path):
        """Preserves non-base_image content while rewriting :main tags."""
        py_file = tmp_path / "component.py"
        original = f'''"""My component."""
from kfp import dsl

@dsl.component(
    base_image="{IMAGE_PREFIX}-example:main",
    packages_to_install=["numpy"],
)
def my_component(value: int) -> str:
    return str(value)
'''
        py_file.write_text(original)

        was_modified, _ = override_file_images(py_file, COMMIT_SHA, IMAGE_PREFIX)

        content = py_file.read_text()
        assert was_modified is True
        assert '"""My component."""' in content
        assert "from kfp import dsl" in content
        assert 'packages_to_install=["numpy"]' in content
        assert "def my_component(value: int) -> str:" in content

    def test_rejects_invalid_commit_sha(self, tmp_path: Path):
        """Rejects commit_sha values that don't look like valid Docker tags."""
        py_file = tmp_path / "component.py"
        py_file.write_text(f'@dsl.component(base_image="{IMAGE_PREFIX}-example:main")')

        with pytest.raises(ValueError, match="Invalid tag value for commit_sha"):
            override_file_images(py_file, "abc/def", IMAGE_PREFIX)


class TestOverrideBaseImages:
    """Integration tests for override_base_images function."""

    def test_modifies_files_in_directory(self, tmp_path: Path):
        """Rewrites matching references when scanning a directory."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text(f'base_image="{IMAGE_PREFIX}-test:main"')

        modified = override_base_images([str(components)], COMMIT_SHA, IMAGE_PREFIX, verbose=False)

        assert len(modified) == 1
        assert f"{IMAGE_PREFIX}-test:{COMMIT_SHA}" in (components / "comp.py").read_text()

    def test_returns_list_of_modified_files(self, tmp_path: Path):
        """Returns the file paths that were modified."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "a.py").write_text(f'base_image="{IMAGE_PREFIX}-a:main"')
        (components / "b.py").write_text(f'base_image="{IMAGE_PREFIX}-b:main"')
        (components / "c.py").write_text('base_image="python:3.11"')

        modified = override_base_images([str(components)], COMMIT_SHA, IMAGE_PREFIX, verbose=False)

        assert len(modified) == 2
        modified_names = {Path(f).name for f in modified}
        assert modified_names == {"a.py", "b.py"}

    def test_dry_run_returns_files_but_no_changes(self, tmp_path: Path):
        """In dry-run mode, reports would-be modified files but does not rewrite content."""
        components = tmp_path / "components"
        components.mkdir()
        original = f'base_image="{IMAGE_PREFIX}-test:main"'
        (components / "comp.py").write_text(original)

        modified = override_base_images([str(components)], COMMIT_SHA, IMAGE_PREFIX, dry_run=True, verbose=False)

        assert len(modified) == 1
        assert (components / "comp.py").read_text() == original

    def test_scans_subdirectories(self, tmp_path: Path):
        """Finds and rewrites references in nested subdirectories."""
        components = tmp_path / "components"
        subdir = components / "training" / "my_component"
        subdir.mkdir(parents=True)
        (subdir / "component.py").write_text(f'base_image="{IMAGE_PREFIX}-training:main"')

        modified = override_base_images([str(components)], COMMIT_SHA, IMAGE_PREFIX, verbose=False)

        assert len(modified) == 1
        assert f"{IMAGE_PREFIX}-training:{COMMIT_SHA}" in (subdir / "component.py").read_text()

    def test_handles_nonexistent_directory(self, tmp_path: Path):
        """Returns an empty list when a directory does not exist."""
        modified = override_base_images([str(tmp_path / "nonexistent")], COMMIT_SHA, IMAGE_PREFIX, verbose=False)

        assert modified == []

    def test_multiple_directories(self, tmp_path: Path):
        """Scans multiple directories and rewrites matches in each."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "c.py").write_text(f'base_image="{IMAGE_PREFIX}-a:main"')

        pipelines = tmp_path / "pipelines"
        pipelines.mkdir()
        (pipelines / "p.py").write_text(f'base_image="{IMAGE_PREFIX}-b:main"')

        modified = override_base_images([str(components), str(pipelines)], COMMIT_SHA, IMAGE_PREFIX, verbose=False)

        assert len(modified) == 2
