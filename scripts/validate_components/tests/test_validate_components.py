"""Tests for validate_components script."""

import sys
import types
from pathlib import Path
from typing import Callable

import pytest
from pytest import MonkeyPatch

from ...lib.discovery import get_submodules
from ...lib.kfp_compilation import find_decorated_function_names_ast
from ..validate_components import (
    CompilationValidationError,
    validate_compilation,
    validate_imports,
)

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def setup_mock_kfp(monkeypatch: MonkeyPatch, fake_repo: Path, compile_func: Callable) -> None:
    """Set up mock kfp compiler for controlled, fast testing.

    Replaces the real KFP Compiler with a fake that calls compile_func,
    allowing tests to control compilation behavior without actually compiling.
    """
    kfp_mod = types.ModuleType("kfp")
    compiler_mod = types.ModuleType("kfp.compiler")

    class _Compiler:
        compile = compile_func

    setattr(compiler_mod, "Compiler", _Compiler)

    monkeypatch.setitem(sys.modules, "kfp", kfp_mod)
    monkeypatch.setitem(sys.modules, "kfp.compiler", compiler_mod)

    from scripts.validate_components import validate_components as vc

    tmp_dir = fake_repo / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(vc.tempfile, "gettempdir", lambda: str(tmp_dir))

    monkeypatch.setattr(vc, "get_repo_root", lambda: fake_repo)

    monkeypatch.chdir(fake_repo)
    monkeypatch.syspath_prepend(str(fake_repo))


def write_component_asset(tmp_path: Path, source_file: Path) -> Path:
    """Create a component asset directory structure with the given source file."""
    component_dir = tmp_path / "components" / "training" / "my_component"
    component_dir.mkdir(parents=True)
    (tmp_path / "components" / "__init__.py").touch()
    (tmp_path / "components" / "training" / "__init__.py").touch()
    (component_dir / "__init__.py").touch()
    (component_dir / "metadata.yaml").touch()

    component_file = component_dir / "component.py"
    component_file.write_text(source_file.read_text())
    return component_file


def write_pipeline_asset(tmp_path: Path, source_file: Path) -> Path:
    """Create a pipeline asset directory structure with the given source file."""
    pipeline_dir = tmp_path / "pipelines" / "training" / "my_pipeline"
    pipeline_dir.mkdir(parents=True)
    (tmp_path / "pipelines" / "__init__.py").touch()
    (tmp_path / "pipelines" / "training" / "__init__.py").touch()
    (pipeline_dir / "__init__.py").touch()
    (pipeline_dir / "metadata.yaml").touch()

    pipeline_file = pipeline_dir / "pipeline.py"
    pipeline_file.write_text(source_file.read_text())
    return pipeline_file


class TestGetSubmodules:
    """Tests for get_submodules function."""

    def test_finds_valid_submodules(self, tmp_path: Path):
        """Discovers direct subdirectories that look like packages and returns them sorted."""
        package = tmp_path / "components"
        package.mkdir()

        training = package / "training"
        training.mkdir()
        (training / "__init__.py").touch()

        evaluation = package / "evaluation"
        evaluation.mkdir()
        (evaluation / "__init__.py").touch()

        submodules = get_submodules(str(package))

        assert submodules == ["evaluation", "training"]

    def test_ignores_directories_without_init(self, tmp_path: Path):
        """Ignores directories that do not contain an __init__.py."""
        package = tmp_path / "components"
        package.mkdir()

        valid = package / "valid"
        valid.mkdir()
        (valid / "__init__.py").touch()

        invalid = package / "invalid"
        invalid.mkdir()

        submodules = get_submodules(str(package))

        assert submodules == ["valid"]
        assert "invalid" not in submodules

    def test_ignores_directories_starting_with_underscore(self, tmp_path: Path):
        """Ignores package directories whose names start with an underscore."""
        package = tmp_path / "components"
        package.mkdir()

        valid = package / "training"
        valid.mkdir()
        (valid / "__init__.py").touch()

        pycache = package / "__pycache__"
        pycache.mkdir()
        (pycache / "__init__.py").touch()

        private = package / "_private"
        private.mkdir()
        (private / "__init__.py").touch()

        submodules = get_submodules(str(package))

        assert submodules == ["training"]
        assert "__pycache__" not in submodules
        assert "_private" not in submodules

    def test_returns_empty_list_for_nonexistent_package(self, tmp_path: Path):
        """Returns an empty list when the package path does not exist."""
        nonexistent = tmp_path / "nonexistent"

        submodules = get_submodules(str(nonexistent))

        assert submodules == []

    def test_returns_sorted_submodules(self, tmp_path: Path):
        """Returns discovered submodules in deterministic sorted order."""
        package = tmp_path / "components"
        package.mkdir()

        for name in ["zebra", "alpha", "beta"]:
            subdir = package / name
            subdir.mkdir()
            (subdir / "__init__.py").touch()

        submodules = get_submodules(str(package))

        assert submodules == ["alpha", "beta", "zebra"]

    def test_ignores_files(self, tmp_path: Path):
        """Does not treat files as submodules."""
        package = tmp_path / "components"
        package.mkdir()

        valid = package / "training"
        valid.mkdir()
        (valid / "__init__.py").touch()

        (package / "some_file.py").touch()

        submodules = get_submodules(str(package))

        assert submodules == ["training"]

    def test_empty_package_directory(self, tmp_path: Path):
        """Returns an empty list for an empty directory."""
        package = tmp_path / "components"
        package.mkdir()

        submodules = get_submodules(str(package))

        assert submodules == []

    def test_with_nested_structure(self, tmp_path: Path):
        """Only returns top-level submodules, not nested package directories."""
        package = tmp_path / "components"
        package.mkdir()

        training = package / "training"
        training.mkdir()
        (training / "__init__.py").touch()

        nested = training / "models"
        nested.mkdir()
        (nested / "__init__.py").touch()

        submodules = get_submodules(str(package))

        assert submodules == ["training"]
        assert "models" not in submodules


class TestValidateImports:
    """Tests for validate_imports function."""

    def test_validates_dynamically_discovered_submodules(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Validates imports for dynamically discovered subpackages in components/ and pipelines/."""
        components = tmp_path / "tmp_components"
        components.mkdir()
        (components / "__init__.py").touch()

        training = components / "training"
        training.mkdir()
        (training / "__init__.py").touch()

        custom_category = components / "custom_category"
        custom_category.mkdir()
        (custom_category / "__init__.py").touch()

        pipelines = tmp_path / "tmp_pipelines"
        pipelines.mkdir()
        (pipelines / "__init__.py").touch()

        training_pipeline = pipelines / "training"
        training_pipeline.mkdir()
        (training_pipeline / "__init__.py").touch()

        monkeypatch.chdir(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))

        success = validate_imports(["tmp_components", "tmp_pipelines"])

        assert success is True

    def test_handles_missing_package_directory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Treats missing packages as warnings and still returns success."""
        monkeypatch.chdir(tmp_path)

        success = validate_imports(["components", "pipelines"])

        captured = capsys.readouterr()
        assert "Warning: No submodules found in components/" in captured.out
        assert "Warning: No submodules found in pipelines/" in captured.out
        assert success is True


class TestFindDecoratedFunctions:
    """Tests for find_decorated_functions."""

    def test_detects_component_and_pipeline_decorators(self, tmp_path: Path):
        """Detects component/pipeline decorators in attribute form."""
        decorated = find_decorated_function_names_ast(
            TEST_DATA_DIR / "fixture_test_find_decorated_function_names_ast__attribute_form.py"
        )

        assert decorated["components"] == ["comp_a", "comp_b", "comp_c"]
        assert decorated["pipelines"] == ["pipe_a"]

    def test_detects_call_form_decorators(self, tmp_path: Path):
        """Detects decorators used as calls (e.g., @dsl.component())."""
        decorated = find_decorated_function_names_ast(
            TEST_DATA_DIR / "fixture_test_find_decorated_function_names_ast__call_form.py"
        )

        assert decorated["components"] == ["comp_a"]
        assert decorated["pipelines"] == ["pipe_a"]

    def test_detects_async_functions(self, tmp_path: Path):
        """Detects decorated async functions."""
        decorated = find_decorated_function_names_ast(
            TEST_DATA_DIR / "fixture_test_find_decorated_function_names_ast__async_functions.py"
        )

        assert decorated["components"] == ["comp_async"]
        assert decorated["pipelines"] == ["pipe_async"]

    def test_syntax_error_returns_empty_and_warns(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Returns {} and prints a warning when parsing fails."""
        from .test_data.fixture_test_find_decorated_function_names_ast__syntax_error import BROKEN_SOURCE

        broken_py = tmp_path / "broken.py"
        broken_py.write_text(BROKEN_SOURCE)

        decorated = find_decorated_function_names_ast(broken_py)

        captured = capsys.readouterr()
        assert decorated == {}
        assert "Warning: Could not parse" in captured.out


class TestValidateCompilation:
    """Tests for validate_compilation."""

    def test_validates_components_and_pipelines(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Returns True when compilation succeeds for detected functions."""
        write_component_asset(
            tmp_path,
            TEST_DATA_DIR / "fixture_test_validate_compilation__component_module.py",
        )
        write_pipeline_asset(
            tmp_path,
            TEST_DATA_DIR / "fixture_test_validate_compilation__pipeline_module.py",
        )

        def mock_compile(_self, _func, path: str) -> None:
            with open(path, "w") as f:
                f.write("compiled")

        setup_mock_kfp(monkeypatch, tmp_path, mock_compile)

        # Snapshot keys: modifying sys.modules while iterating
        for mod_name in tuple(sys.modules.keys()):
            if mod_name == "components" or mod_name.startswith("components."):
                monkeypatch.delitem(sys.modules, mod_name, raising=False)
            if mod_name == "pipelines" or mod_name.startswith("pipelines."):
                monkeypatch.delitem(sys.modules, mod_name, raising=False)

        validate_compilation(["components", "pipelines"])

    def test_fails_when_pipeline_compile_raises(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Returns False when pipeline compilation raises."""
        write_pipeline_asset(
            tmp_path,
            TEST_DATA_DIR / "fixture_test_validate_compilation__pipeline_module.py",
        )

        def mock_compile(_self, _func, _path: str) -> None:
            raise RuntimeError("boom")

        setup_mock_kfp(monkeypatch, tmp_path, mock_compile)

        with pytest.raises(CompilationValidationError):
            validate_compilation(["components", "pipelines"])

    def test_fails_when_no_assets_found(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Raises when there are no component.py/pipeline.py assets to compile."""

        def mock_compile(_self, _func, _path: str) -> None:
            raise AssertionError("compile should not be called when no assets exist")

        setup_mock_kfp(monkeypatch, tmp_path, mock_compile)

        with pytest.raises(CompilationValidationError, match="No components or pipelines found to compile"):
            validate_compilation(["components", "pipelines"])

    def test_accepts_absolute_directory_paths(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Validates components when directories are specified as absolute paths."""
        write_component_asset(
            tmp_path,
            TEST_DATA_DIR / "fixture_test_validate_compilation__component_module.py",
        )

        def mock_compile(_self, _func, path: str) -> None:
            with open(path, "w") as f:
                f.write("compiled")

        setup_mock_kfp(monkeypatch, tmp_path, mock_compile)

        for mod_name in tuple(sys.modules.keys()):
            if mod_name == "components" or mod_name.startswith("components."):
                monkeypatch.delitem(sys.modules, mod_name, raising=False)

        validate_compilation([str(tmp_path / "components")])

    def test_matches_requested_roots_resolves_paths_against_repo_root(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Path matching normalizes relative paths against repo root, not cwd.

        When absolute paths are passed as roots but asset paths are relative,
        _matches_requested_roots must resolve relative paths against the
        repository root, not the current working directory.
        """
        from scripts.validate_components import validate_components as vc

        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "components" / "training" / "my_component").mkdir(parents=True)

        monkeypatch.setattr(vc, "get_repo_root", lambda: repo_root)

        different_cwd = tmp_path
        monkeypatch.chdir(different_cwd)

        asset_dir = Path("components/training/my_component")
        roots = [repo_root / "components"]

        result = vc._matches_requested_roots(asset_dir, roots)

        assert result is True, "Relative asset path should match absolute root when resolved against repo root"
