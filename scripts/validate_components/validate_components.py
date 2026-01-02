#!/usr/bin/env python3
"""Validate that all components and pipelines compile successfully."""

import argparse
import sys
import tempfile
from pathlib import Path

from scripts.lib.discovery import get_submodules
from scripts.lib.kfp_ast import find_decorated_functions


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
                print(f"  ✓ {module_path}")
            except ImportError as e:
                print(f"  ✗ {module_path}: {e}")
                success = False

    return success


def _compile_component(module_path: str, func_name: str, tmp_dir: Path, compiler) -> bool:
    """Compile a single component. Returns True on success."""
    module_path_safe = module_path.replace(".", "_")
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)

        compiler.Compiler().compile(
            func,
            str(tmp_dir / f"{module_path_safe}_{func_name}_component.yaml"),
        )
        print(f"  ✓ {module_path}.{func_name} (component)")
        return True
    except Exception as e:
        print(f"  ✗ {module_path}.{func_name}: {e}")
        return False


def _compile_pipeline(module_path: str, func_name: str, tmp_dir: Path, compiler) -> bool:
    """Compile a single pipeline. Returns True on success."""
    module_path_safe = module_path.replace(".", "_")
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)

        compiler.Compiler().compile(
            func,
            str(tmp_dir / f"{module_path_safe}_{func_name}_pipeline.yaml"),
        )
        print(f"  ✓ {module_path}.{func_name} (pipeline)")
        return True
    except Exception as e:
        print(f"  ✗ {module_path}.{func_name}: {e}")
        return False


def _process_file(py_file: Path, tmp_dir: Path, compiler) -> tuple[bool, bool]:
    """Process a single Python file. Returns (found_any, all_succeeded)."""
    decorated = find_decorated_functions(py_file)
    if not decorated or (not decorated["components"] and not decorated["pipelines"]):
        return False, True

    module_path = ".".join(py_file.with_suffix("").parts)
    all_succeeded = True

    for func_name in decorated["components"]:
        if not _compile_component(module_path, func_name, tmp_dir, compiler):
            all_succeeded = False

    for func_name in decorated["pipelines"]:
        if not _compile_pipeline(module_path, func_name, tmp_dir, compiler):
            all_succeeded = False

    return True, all_succeeded


def _iter_python_files(directories: list[str]):
    """Yield all Python files (excluding __init__.py) from directories."""
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            if py_file.name != "__init__.py":
                yield py_file


def validate_compilation(directories: list[str]) -> bool:
    """Find and validate all components and pipelines."""
    print("\nValidating component/pipeline compilation...")

    try:
        from kfp import compiler
    except ImportError:
        print("  Error: kfp not installed")
        return False

    success = True
    found_any = False
    tmp_dir = Path(tempfile.gettempdir())

    for py_file in _iter_python_files(directories):
        found, succeeded = _process_file(py_file, tmp_dir, compiler)
        found_any = found_any or found
        success = success and succeeded

    if not found_any:
        print("  No components or pipelines found to compile")

    return success


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
    compilation_ok = validate_compilation(args.directories)

    print()
    if imports_ok and compilation_ok:
        print("✓ All validations passed")
        return 0
    else:
        print("✗ Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
