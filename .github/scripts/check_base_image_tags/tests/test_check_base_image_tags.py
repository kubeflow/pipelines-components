"""Tests for check_base_image_tags script."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_base_image_tags import (
    check_base_image_tags,
    check_main_tag,
    find_base_image_references,
)


IMAGE_PREFIX = "ghcr.io/kubeflow/pipelines-components"


class TestFindBaseImageReferences:
    """Tests for find_base_image_references function."""

    def test_finds_base_image_with_prefix(self, tmp_path: Path):
        py_file = tmp_path / "component.py"
        py_file.write_text(
            '''from kfp import dsl

@dsl.component(base_image="ghcr.io/kubeflow/pipelines-components-example:main")
def my_component():
    pass
'''
        )

        refs = find_base_image_references(py_file, IMAGE_PREFIX)

        assert len(refs) == 1
        assert refs[0][0] == 3
        assert "base_image" in refs[0][1]
        assert IMAGE_PREFIX in refs[0][1]

    def test_finds_multiple_references(self, tmp_path: Path):
        py_file = tmp_path / "component.py"
        py_file.write_text(
            f'''from kfp import dsl

@dsl.component(base_image="{IMAGE_PREFIX}-first:main")
def first_component():
    pass

@dsl.component(base_image="{IMAGE_PREFIX}-second:main")
def second_component():
    pass
'''
        )

        refs = find_base_image_references(py_file, IMAGE_PREFIX)

        assert len(refs) == 2

    def test_ignores_non_matching_base_image(self, tmp_path: Path):
        py_file = tmp_path / "component.py"
        py_file.write_text(
            '''from kfp import dsl

@dsl.component(base_image="python:3.11")
def my_component():
    pass
'''
        )

        refs = find_base_image_references(py_file, IMAGE_PREFIX)

        assert len(refs) == 0

    def test_raises_on_missing_file(self, tmp_path: Path):
        py_file = tmp_path / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            find_base_image_references(py_file, IMAGE_PREFIX)


class TestCheckMainTag:
    """Tests for check_main_tag function."""

    def test_valid_main_tag(self):
        line = f'base_image="{IMAGE_PREFIX}-example:main"'

        is_valid, found = check_main_tag(line, IMAGE_PREFIX)

        assert is_valid is True
        assert found is None

    def test_invalid_sha_tag(self):
        line = f'base_image="{IMAGE_PREFIX}-example:abc123def456"'

        is_valid, found = check_main_tag(line, IMAGE_PREFIX)

        assert is_valid is False
        assert found == f"{IMAGE_PREFIX}-example:abc123def456"

    def test_invalid_version_tag(self):
        line = f'base_image="{IMAGE_PREFIX}-example:v1.0.0"'

        is_valid, found = check_main_tag(line, IMAGE_PREFIX)

        assert is_valid is False
        assert found == f"{IMAGE_PREFIX}-example:v1.0.0"

    def test_valid_with_single_quotes(self):
        line = f"base_image='{IMAGE_PREFIX}-example:main'"

        is_valid, _ = check_main_tag(line, IMAGE_PREFIX)

        assert is_valid is True

    def test_valid_with_spaces(self):
        line = f'    base_image = "{IMAGE_PREFIX}-my-component:main",'

        is_valid, _ = check_main_tag(line, IMAGE_PREFIX)

        assert is_valid is True


class TestCheckBaseImageTags:
    """Integration tests for check_base_image_tags function."""

    def test_all_valid_returns_true(self, tmp_path: Path):
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text(
            f'@dsl.component(base_image="{IMAGE_PREFIX}-test:main")\ndef comp(): pass'
        )

        all_valid, results = check_base_image_tags(
            [str(components)], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is True
        assert len(results) == 1
        assert results[0]["status"] == "valid"

    def test_invalid_tag_returns_false(self, tmp_path: Path):
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text(
            f'@dsl.component(base_image="{IMAGE_PREFIX}-test:sha123")\ndef comp(): pass'
        )

        all_valid, results = check_base_image_tags(
            [str(components)], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is False
        assert len(results) == 1
        assert results[0]["status"] == "invalid"
        assert "found" in results[0]

    def test_mixed_valid_and_invalid(self, tmp_path: Path):
        components = tmp_path / "components"
        components.mkdir()
        (components / "valid.py").write_text(
            f'@dsl.component(base_image="{IMAGE_PREFIX}-valid:main")\ndef comp(): pass'
        )
        (components / "invalid.py").write_text(
            f'@dsl.component(base_image="{IMAGE_PREFIX}-invalid:v1.0")\ndef comp(): pass'
        )

        all_valid, results = check_base_image_tags(
            [str(components)], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is False
        assert len(results) == 2
        valid_count = sum(1 for r in results if r["status"] == "valid")
        invalid_count = sum(1 for r in results if r["status"] == "invalid")
        assert valid_count == 1
        assert invalid_count == 1

    def test_no_references_is_valid(self, tmp_path: Path):
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text(
            '@dsl.component(base_image="python:3.11")\ndef comp(): pass'
        )

        all_valid, results = check_base_image_tags(
            [str(components)], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is True
        assert len(results) == 0

    def test_nonexistent_directory_is_valid(self, tmp_path: Path):
        all_valid, results = check_base_image_tags(
            [str(tmp_path / "nonexistent")], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is True
        assert len(results) == 0

    def test_scans_subdirectories(self, tmp_path: Path):
        components = tmp_path / "components"
        subdir = components / "training" / "my_component"
        subdir.mkdir(parents=True)
        (subdir / "component.py").write_text(
            f'@dsl.component(base_image="{IMAGE_PREFIX}-training:main")\ndef comp(): pass'
        )

        all_valid, results = check_base_image_tags(
            [str(components)], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is True
        assert len(results) == 1

    def test_multiple_directories(self, tmp_path: Path):
        components = tmp_path / "components"
        components.mkdir()
        (components / "c.py").write_text(
            f'base_image="{IMAGE_PREFIX}-a:main"'
        )

        pipelines = tmp_path / "pipelines"
        pipelines.mkdir()
        (pipelines / "p.py").write_text(
            f'base_image="{IMAGE_PREFIX}-b:main"'
        )

        all_valid, results = check_base_image_tags(
            [str(components), str(pipelines)], IMAGE_PREFIX, verbose=False
        )

        assert all_valid is True
        assert len(results) == 2

