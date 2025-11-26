"""Tests for validate_components script."""

import sys
import types
from pathlib import Path
from typing import Callable

from scripts.lib.discovery import get_submodules
from scripts.lib.kfp_ast import find_decorated_functions
from scripts.validate_components.validate_components import (
    validate_compilation,
    validate_imports,
)


def setup_mock_kfp(monkeypatch, tmp_path: Path, compile_func: Callable) -> None:
    """Set up mock kfp module with a custom compile function."""
    kfp_mod = types.ModuleType("kfp")
    compiler_mod = types.ModuleType("compiler")

    class _Compiler:
        compile = compile_func

    setattr(compiler_mod, "Compiler", _Compiler)
    setattr(kfp_mod, "compiler", compiler_mod)

    monkeypatch.setitem(sys.modules, "kfp", kfp_mod)

    from scripts.validate_components import validate_components as vc

    tmp_tmp = tmp_path / "tmp"
    tmp_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(vc.tempfile, "gettempdir", lambda: str(tmp_tmp))

    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))


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

    def test_validates_dynamically_discovered_submodules(self, tmp_path: Path, monkeypatch):
        """Validates imports for dynamically discovered subpackages in components/ and pipelines/."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "__init__.py").touch()

        training = components / "training"
        training.mkdir()
        (training / "__init__.py").touch()

        custom_category = components / "custom_category"
        custom_category.mkdir()
        (custom_category / "__init__.py").touch()

        pipelines = tmp_path / "pipelines"
        pipelines.mkdir()
        (pipelines / "__init__.py").touch()

        training_pipeline = pipelines / "training"
        training_pipeline.mkdir()
        (training_pipeline / "__init__.py").touch()

        monkeypatch.chdir(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))

        success = validate_imports(["components", "pipelines"])

        assert success is True

    def test_handles_missing_package_directory(self, tmp_path: Path, monkeypatch, capsys):
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
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            """
from kfp import dsl

@dsl.component
def comp_a():
    pass

@dsl.container_component
def comp_b():
    pass

@dsl.notebook_component
def comp_c():
    pass

@dsl.pipeline
def pipe_a():
    pass
"""
        )

        decorated = find_decorated_functions(py_file)

        assert decorated["components"] == ["comp_a", "comp_b", "comp_c"]
        assert decorated["pipelines"] == ["pipe_a"]

    def test_detects_call_form_decorators(self, tmp_path: Path):
        """Detects decorators used as calls (e.g., @dsl.component())."""
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            """
from kfp import dsl

@dsl.component()
def comp_a():
    pass

@dsl.pipeline(name="x")
def pipe_a():
    pass
"""
        )

        decorated = find_decorated_functions(py_file)

        assert decorated["components"] == ["comp_a"]
        assert decorated["pipelines"] == ["pipe_a"]

    def test_detects_async_functions(self, tmp_path: Path):
        """Detects decorated async functions."""
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            """
from kfp import dsl

@dsl.component
async def comp_async():
    return 1

@dsl.pipeline
async def pipe_async():
    return 2
"""
        )

        decorated = find_decorated_functions(py_file)

        assert decorated["components"] == ["comp_async"]
        assert decorated["pipelines"] == ["pipe_async"]

    def test_syntax_error_returns_empty_and_warns(self, tmp_path: Path, capsys):
        """Returns {} and prints a warning when parsing fails."""
        py_file = tmp_path / "broken.py"
        py_file.write_text("def oops(:\n  pass\n")

        decorated = find_decorated_functions(py_file)

        captured = capsys.readouterr()
        assert decorated == {}
        assert "Warning: Could not parse" in captured.out


class TestValidateCompilation:
    """Tests for validate_compilation."""

    def test_validates_components_and_pipelines(self, tmp_path: Path, monkeypatch):
        """Returns True when compilation succeeds for detected functions."""
        (tmp_path / "components" / "training").mkdir(parents=True)
        (tmp_path / "components" / "__init__.py").touch()
        (tmp_path / "components" / "training" / "__init__.py").touch()

        module_file = tmp_path / "components" / "training" / "sample.py"
        module_file.write_text(
            """
from __future__ import annotations

class _Spec:
    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write("ok")

class dsl:
    @staticmethod
    def component(fn=None, **kwargs):
        def deco(f):
            f.component_spec = _Spec()
            return f
        return deco(fn) if fn is not None else deco

    @staticmethod
    def notebook_component(fn=None, **kwargs):
        def deco(f):
            f.component_spec = _Spec()
            return f
        return deco(fn) if fn is not None else deco

    @staticmethod
    def pipeline(fn=None, **kwargs):
        def deco(f):
            return f
        return deco(fn) if fn is not None else deco

@dsl.component
def my_component():
    return 1

@dsl.notebook_component
def my_notebook_component():
    return 3

@dsl.pipeline
def my_pipeline():
    return 2
"""
        )

        def mock_compile(_self, _func, path: str) -> None:
            with open(path, "w") as f:
                f.write("compiled")

        setup_mock_kfp(monkeypatch, tmp_path, mock_compile)

        # Snapshot keys: modifying sys.modules while iterating
        for mod_name in tuple(sys.modules.keys()):
            if mod_name == "components" or mod_name.startswith("components."):
                monkeypatch.delitem(sys.modules, mod_name, raising=False)

        assert validate_compilation(["components", "pipelines"]) is True

    def test_fails_when_pipeline_compile_raises(self, tmp_path: Path, monkeypatch):
        """Returns False when pipeline compilation raises."""
        (tmp_path / "pipelines" / "training").mkdir(parents=True)
        (tmp_path / "pipelines" / "__init__.py").touch()
        (tmp_path / "pipelines" / "training" / "__init__.py").touch()

        module_file = tmp_path / "pipelines" / "training" / "sample.py"
        module_file.write_text(
            """
class dsl:
    @staticmethod
    def pipeline(fn=None, **kwargs):
        def deco(f):
            return f
        return deco(fn) if fn is not None else deco

@dsl.pipeline
def my_pipeline():
    return 2
"""
        )

        def mock_compile(_self, _func, _path: str) -> None:
            raise RuntimeError("boom")

        setup_mock_kfp(monkeypatch, tmp_path, mock_compile)

        assert validate_compilation(["components", "pipelines"]) is False
