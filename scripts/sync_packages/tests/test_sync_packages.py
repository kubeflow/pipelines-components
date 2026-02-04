"""Unit tests for sync_packages.py."""

from pathlib import Path
from unittest import mock

import pytest

from ..sync_packages import _PACKAGES_RE, _read_current_packages, sync_packages


class TestReadCurrentPackages:
    """Tests for _read_current_packages."""

    def test_reads_valid_packages(self, tmp_path: Path):
        """Test reading a well-formed packages list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools]\npackages = [\n    "kfp_components",\n    "kfp_components.components",\n]\n'
        )

        result = _read_current_packages(pyproject)
        assert result == ["kfp_components", "kfp_components.components"]

    def test_reads_empty_packages(self, tmp_path: Path):
        """Test reading an empty packages list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.setuptools]\npackages = []\n")

        result = _read_current_packages(pyproject)
        assert result == []

    def test_missing_section_returns_empty(self, tmp_path: Path):
        """Test that missing [tool.setuptools] returns empty list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = []\n")

        result = _read_current_packages(pyproject)
        assert result == []

    def test_missing_packages_key_returns_empty(self, tmp_path: Path):
        """Test that missing packages key returns empty list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.setuptools]\npackage-dir = {kfp = "."}\n')

        result = _read_current_packages(pyproject)
        assert result == []

    def test_invalid_toml_raises(self, tmp_path: Path):
        """Test that invalid TOML raises RuntimeError."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.setuptools\n")  # Missing closing bracket

        with pytest.raises(RuntimeError, match="Failed to parse"):
            _read_current_packages(pyproject)

    def test_non_list_packages_raises(self, tmp_path: Path):
        """Test that non-list packages value raises RuntimeError."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.setuptools]\npackages = "not_a_list"\n')

        with pytest.raises(RuntimeError, match="must be a list"):
            _read_current_packages(pyproject)


class TestPackagesRegex:
    """Tests for the _PACKAGES_RE regex pattern."""

    def test_matches_packages_under_tool_setuptools(self):
        """Test regex matches packages list under [tool.setuptools]."""
        content = '[build-system]\nrequires = []\n\n[tool.setuptools]\npackages = [\n    "kfp_components",\n]\n'
        match = _PACKAGES_RE.search(content)
        assert match is not None
        assert match.group(2).startswith("packages = [")

    def test_does_not_match_packages_under_other_section(self):
        """Test regex does not match packages in a different section."""
        content = "[project]\npackages = []\n\n[tool.setuptools]\nzip-safe = false\n"
        match = _PACKAGES_RE.search(content)
        assert match is None

    def test_matches_with_other_keys_before_packages(self):
        """Test regex matches when other keys precede packages."""
        content = '[tool.setuptools]\npackage-dir = {kfp_components = "."}\npackages = [\n    "kfp_components",\n]\n'
        match = _PACKAGES_RE.search(content)
        assert match is not None


class TestSyncPackages:
    """Tests for the sync_packages function."""

    @pytest.fixture
    def repo_with_pyproject(self, tmp_path: Path) -> Path:
        """Create a minimal repo root with pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[build-system]\nrequires = []\n\n[tool.setuptools]\npackages = [\n    "kfp_components",\n]\n'
        )
        return tmp_path

    def test_already_in_sync(self, repo_with_pyproject: Path, capsys: pytest.CaptureFixture):
        """Test no-op when packages are already in sync."""
        with mock.patch(
            "scripts.sync_packages.sync_packages.discover_packages",
            return_value=["kfp_components"],
        ):
            sync_packages(repo_with_pyproject)

        assert "already in sync" in capsys.readouterr().out

    def test_updates_when_out_of_sync(self, repo_with_pyproject: Path, capsys: pytest.CaptureFixture):
        """Test that pyproject.toml is updated when packages differ."""
        new_packages = ["kfp_components", "kfp_components.components"]

        with mock.patch(
            "scripts.sync_packages.sync_packages.discover_packages",
            return_value=new_packages,
        ):
            sync_packages(repo_with_pyproject)

        output = capsys.readouterr().out
        assert "Synced 2 packages" in output

        # Verify the file was actually written correctly
        content = (repo_with_pyproject / "pyproject.toml").read_text()
        assert '"kfp_components"' in content
        assert '"kfp_components.components"' in content

    def test_preserves_surrounding_content(self, repo_with_pyproject: Path):
        """Test that content outside the packages block is preserved."""
        (repo_with_pyproject / "pyproject.toml").write_text(
            "[build-system]\nrequires = []\n\n"
            "[tool.setuptools]\n"
            'package-dir = {kfp_components = "."}\n'
            'packages = [\n    "kfp_components",\n]\n\n'
            "[tool.ruff]\nline-length = 100\n"
        )

        with mock.patch(
            "scripts.sync_packages.sync_packages.discover_packages",
            return_value=["kfp_components", "kfp_components.components"],
        ):
            sync_packages(repo_with_pyproject)

        content = (repo_with_pyproject / "pyproject.toml").read_text()
        assert 'package-dir = {kfp_components = "."}' in content
        assert "[tool.ruff]" in content
        assert "line-length = 100" in content

    def test_raises_when_no_packages_block(self, tmp_path: Path):
        """Test RuntimeError when packages block is missing from file."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = []\n")

        with (
            mock.patch(
                "scripts.sync_packages.sync_packages.discover_packages",
                return_value=["kfp_components"],
            ),
            pytest.raises(RuntimeError, match="Could not find"),
        ):
            sync_packages(tmp_path)
