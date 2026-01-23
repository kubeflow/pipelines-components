#!/usr/bin/env python3
"""Validate that all components and pipelines compile successfully."""

import argparse
import importlib
import sys
import tempfile
from pathlib import Path

from ..lib.discovery import find_assets_with_metadata, get_repo_root, get_submodules
from ..lib.kfp_compilation import find_decorated_function_names_ast


class CompilationValidationError(Exception):
    """Raised when component/pipeline compilation validation fails."""


def _format_file_path_for_error(py_file: Path) -> Path:
    if not py_file.is_absolute():
        return py_file
    try:
        return py_file.relative_to(Path.cwd())
    except ValueError:
        return py_file


def validate_imports(directories: list[str]) -> bool:
    """Validate that package structure imports correctly."""
    print("Validating package imports...")
    success = True

    for package in directories:
        submodules = get_submodules(package)
        if not submodules:
            print(f"  Warning: No submodules found in {package}/")
            continue

        for submodule in submodules:
            module_path = f"{package}.{submodule}"
            try:
                __import__(module_path)
                print(f"  ✅ {module_path}")
            except ImportError as e:
                print(f"  ❌ {module_path}: {e}")
                success = False

    return success


def _compile_callable(
    module_path: str,
    func_name: str,
    tmp_dir: Path,
    compiler_class,
    kind: str,
) -> None:
    module_path_safe = module_path.replace(".", "_")
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)

        compiler_class().compile(
            func,
            str(tmp_dir / f"{module_path_safe}_{func_name}_{kind}.yaml"),
        )
    except Exception as e:
        raise CompilationValidationError(f"{module_path}.{func_name}: {e}") from e


def _process_file(py_file: Path, tmp_dir: Path, compiler_class) -> bool:
    """Process a single Python file.

    Returns:
        True if any decorated functions were found.

    Raises:
        CompilationValidationError: If any decorated functions fail to compile.
    """
    decorated = find_decorated_function_names_ast(py_file)
    if not decorated or (not decorated["components"] and not decorated["pipelines"]):
        return False

    module_path = ".".join(py_file.with_suffix("").parts)
    errors: list[str] = []

    for func_name in decorated["components"]:
        try:
            _compile_callable(module_path, func_name, tmp_dir, compiler_class, "component")
        except CompilationValidationError as e:
            errors.append(str(e))

    for func_name in decorated["pipelines"]:
        try:
            _compile_callable(module_path, func_name, tmp_dir, compiler_class, "pipeline")
        except CompilationValidationError as e:
            errors.append(str(e))

    if errors:
        rel_path = _format_file_path_for_error(py_file)
        lines = [f"{rel_path}:", ""] + [f"  - {e}" for e in errors]
        raise CompilationValidationError("\n".join(lines))

    return True


def _normalize_path(path: Path) -> Path:
    """Normalize relative paths against the repository root."""
    if path.is_absolute():
        return path.resolve()
    return (get_repo_root() / path).resolve()


def _matches_requested_roots(asset_dir: Path, roots: list[Path]) -> bool:
    asset_resolved = _normalize_path(asset_dir)
    for root in roots:
        root_resolved = _normalize_path(root)
        if asset_resolved == root_resolved or asset_resolved.is_relative_to(root_resolved):
            return True
    return False


def _asset_entrypoints(asset_type: str, filename: str, roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for asset_dir_str in find_assets_with_metadata(asset_type):
        asset_dir = Path(asset_dir_str)
        if not _matches_requested_roots(asset_dir, roots):
            continue
        candidate = asset_dir / filename
        if candidate.exists():
            files.append(candidate)
    return files


def _iter_asset_files(directories: list[str]) -> list[Path]:
    """Return canonical component.py/pipeline.py files for assets with metadata.yaml."""
    roots = [Path(d) for d in directories] if directories else [Path("components"), Path("pipelines")]
    return _asset_entrypoints("components", "component.py", roots) + _asset_entrypoints(
        "pipelines", "pipeline.py", roots
    )


def validate_compilation(directories: list[str]) -> None:
    """Find and validate all components and pipelines.

    Returns:
        None. Raises on failure.

    Raises:
        CompilationValidationError: If compilation fails for any detected assets.
    """
    print("\nValidating component/pipeline compilation...")

    try:
        compiler_mod = importlib.import_module("kfp.compiler")
        compiler_class = getattr(compiler_mod, "Compiler")
    except (ImportError, AttributeError) as e:
        raise CompilationValidationError("kfp is not installed") from e

    found_any = False
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        failures: list[str] = []
        for py_file in _iter_asset_files(directories):
            try:
                found = _process_file(py_file, tmp_path, compiler_class)
                found_any = found_any or found
            except CompilationValidationError as e:
                failures.append(str(e))

        if failures:
            raise CompilationValidationError("Compilation failed for the following files:\n\n" + "\n".join(failures))

    if not found_any:
        raise CompilationValidationError("No components or pipelines found to compile")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Validate that all components and pipelines compile successfully")
    parser.add_argument(
        "--directories",
        nargs="+",
        required=True,
        help="Directories to scan (e.g., components pipelines)",
    )

    args = parser.parse_args()

    sys.path.insert(0, ".")

    imports_ok = validate_imports(args.directories)
    compilation_ok = True
    try:
        validate_compilation(args.directories)
    except CompilationValidationError as e:
        print(f"  Error: {e}")
        compilation_ok = False

    print()
    if imports_ok and compilation_ok:
        print("✅ All validations passed")
        return 0
    else:
        print("❌ Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
