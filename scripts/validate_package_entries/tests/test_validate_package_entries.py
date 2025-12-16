"""Unit tests for validate_package_entries.py."""

from pathlib import Path

import pytest

from ..validate_package_entries import (
    discover_packages,
    read_pyproject_packages,
    validate_package_entries,
)


@pytest.fixture
def components_training_structure(tmp_path: Path) -> Path:
    """Create a common components/training directory structure for tests."""
    components_dir = tmp_path / "components"
    components_dir.mkdir()
    (components_dir / "__init__.py").write_text("")

    training_dir = components_dir / "training"
    training_dir.mkdir()
    (training_dir / "__init__.py").write_text("")

    return tmp_path


class TestDiscoverPackages:
    """Tests for discover_packages function."""

    def test_discover_root_package(self, tmp_path: Path):
        """Test discovery of root package."""
        # Create root __init__.py
        (tmp_path / "__init__.py").write_text("")

        packages = discover_packages(tmp_path)
        assert "kfp_components" in packages

    def test_discover_components_packages(self, components_training_structure: Path):
        """Test discovery of component packages."""
        packages = discover_packages(components_training_structure)
        assert "kfp_components.components" in packages
        assert "kfp_components.components.training" in packages

    def test_discover_pipelines_packages(self, tmp_path: Path):
        """Test discovery of pipeline packages."""
        # Create pipelines structure
        pipelines_dir = tmp_path / "pipelines"
        pipelines_dir.mkdir()
        (pipelines_dir / "__init__.py").write_text("")

        evaluation_dir = pipelines_dir / "evaluation"
        evaluation_dir.mkdir()
        (evaluation_dir / "__init__.py").write_text("")

        packages = discover_packages(tmp_path)
        assert "kfp_components.pipelines" in packages
        assert "kfp_components.pipelines.evaluation" in packages

    def test_skip_directories_without_init(self, tmp_path: Path):
        """Test that directories without __init__.py are skipped."""
        components_dir = tmp_path / "components"
        components_dir.mkdir()
        (components_dir / "__init__.py").write_text("")

        # Create directory without __init__.py
        no_init_dir = components_dir / "no_init"
        no_init_dir.mkdir()

        packages = discover_packages(tmp_path)
        assert "kfp_components.components" in packages
        assert "kfp_components.components.no_init" not in packages

    def test_discover_nested_packages(self, components_training_structure: Path):
        """Test discovery of nested package structure."""
        training_dir = components_training_structure / "components" / "training"
        nested_dir = training_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "__init__.py").write_text("")

        packages = discover_packages(components_training_structure)
        assert "kfp_components.components" in packages
        assert "kfp_components.components.training" in packages
        assert "kfp_components.components.training.nested" in packages


class TestReadPyprojectPackages:
    """Tests for read_pyproject_packages function."""

    def test_read_valid_packages(self, tmp_path: Path):
        """Test reading packages from valid pyproject.toml."""
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
packages = [
    "kfp_components",
    "kfp_components.components",
    "kfp_components.components.training",
]
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        packages = read_pyproject_packages(tmp_path)
        assert "kfp_components" in packages
        assert "kfp_components.components" in packages
        assert "kfp_components.components.training" in packages

    def test_read_empty_packages_list(self, tmp_path: Path):
        """Test reading empty packages list."""
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
packages = []
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        packages = read_pyproject_packages(tmp_path)
        assert packages == set()

    def test_missing_tool_setuptools_section(self, tmp_path: Path):
        """Test handling missing tool.setuptools section."""
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        packages = read_pyproject_packages(tmp_path)
        assert packages == set()

    def test_missing_packages_key(self, tmp_path: Path):
        """Test handling missing packages key."""
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
package-dir = {"kfp_components" = "."}
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        packages = read_pyproject_packages(tmp_path)
        assert packages == set()


class TestValidatePackageEntries:
    """Tests for validate_package_entries function."""

    def test_valid_sync(self, components_training_structure: Path):
        """Test validation when packages are in sync."""
        # Create root __init__.py
        (components_training_structure / "__init__.py").write_text("")

        # Create matching pyproject.toml
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
packages = [
    "kfp_components",
    "kfp_components.components",
    "kfp_components.components.training",
]
"""
        (components_training_structure / "pyproject.toml").write_text(pyproject_content)

        is_valid, errors = validate_package_entries(components_training_structure)
        assert is_valid
        assert len(errors) == 0

    def test_missing_packages(self, components_training_structure: Path):
        """Test validation when packages are missing from pyproject.toml."""
        # Create root __init__.py
        (components_training_structure / "__init__.py").write_text("")

        # Create pyproject.toml missing some packages
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
packages = [
    "kfp_components",
    "kfp_components.components",
    # Missing kfp_components.components.training
]
"""
        (components_training_structure / "pyproject.toml").write_text(pyproject_content)

        is_valid, errors = validate_package_entries(components_training_structure)
        assert not is_valid
        assert len(errors) == 1
        assert "Missing packages" in errors[0]
        assert "kfp_components.components.training" in errors[0]

    def test_extra_packages(self, tmp_path: Path):
        """Test validation when pyproject.toml has extra packages."""
        # Create minimal directory structure
        (tmp_path / "__init__.py").write_text("")

        # Create pyproject.toml with extra packages
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
packages = [
    "kfp_components",
    "kfp_components.components",
    "kfp_components.components.nonexistent",  # Extra package
]
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        is_valid, errors = validate_package_entries(tmp_path)
        assert not is_valid
        assert len(errors) == 1
        assert "Extra packages" in errors[0]
        assert "kfp_components.components" in errors[0]
        assert "kfp_components.components.nonexistent" in errors[0]

    def test_both_missing_and_extra(self, components_training_structure: Path):
        """Test validation when both missing and extra packages exist."""
        # Create root __init__.py
        (components_training_structure / "__init__.py").write_text("")

        # Create pyproject.toml with both issues
        pyproject_content = """
[build-system]
requires = ["setuptools", "wheel"]

[tool.setuptools]
packages = [
    "kfp_components",
    "kfp_components.components",
    # Missing kfp_components.components.training
    "kfp_components.components.nonexistent",  # Extra package
]
"""
        (components_training_structure / "pyproject.toml").write_text(pyproject_content)

        is_valid, errors = validate_package_entries(components_training_structure)
        assert not is_valid
        assert len(errors) == 2
        assert any("Missing packages" in e for e in errors)
        assert any("Extra packages" in e for e in errors)
