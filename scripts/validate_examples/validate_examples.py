#!/usr/bin/env python3
"""Validate example_pipelines modules by compiling every exported pipeline."""

from __future__ import annotations

import argparse
import sys
import tempfile
import traceback
import warnings
from pathlib import Path
from types import ModuleType
from typing import List, Sequence, Tuple

from kfp import compiler

from ..lib.discovery import get_repo_root, normalize_targets
from ..lib.kfp_compilation import load_module_from_path as _load_module
from ..lib.parsing import find_pipeline_functions

REPO_ROOT = get_repo_root()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Import example_pipelines.py modules for the specified components or pipelines "
            "and compile every @dsl.pipeline function they export."
        )
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        help=(
            "Component or pipeline directories (or files within them). "
            "If omitted, every example_pipelines.py file is validated."
        ),
    )
    return parser.parse_args()


def discover_example_files(targets: Sequence[Path]) -> List[Path]:
    """Discover example_pipelines.py files under the given targets.

    Args:
        targets: Sequence of component or pipeline paths to search.

    Returns:
        List of discovered example_pipelines.py file paths.
    """
    discovered: List[Path] = []

    for target in targets:
        search_root = target if target.is_dir() else target.parent

        for candidate in search_root.rglob("example_pipelines.py"):
            if candidate in discovered or not candidate.is_file():
                continue
            try:
                relative = candidate.relative_to(REPO_ROOT)
            except ValueError:
                warnings.warn(
                    f"Unable to determine relative path for {candidate} relative to repo root {REPO_ROOT}. Skipping.",
                )
                continue
            if relative.parts and relative.parts[0] in {"components", "pipelines"}:
                discovered.append(candidate)

    return discovered


def load_module_from_path(module_path: Path) -> ModuleType:
    """Load a Python module from a file path.

    Args:
        module_path: Path to the Python file to load.

    Returns:
        The loaded module object.

    Raises:
        ImportError: If the module cannot be loaded.
    """
    relative = module_path.relative_to(REPO_ROOT)
    sanitized = "_".join(relative.with_suffix("").parts)
    module_name = f"example_pipelines__{sanitized}"
    return _load_module(str(module_path), module_name)


def collect_pipeline_functions(module_path: Path, module: ModuleType) -> List[Tuple[str, object]]:
    """Collect pipeline functions from a module.

    Args:
        module_path: Path to the Python file.
        module: The loaded module.

    Returns:
        List of (function_name, callable) tuples for pipeline functions.
    """
    pipeline_names = find_pipeline_functions(module_path)

    pipelines: List[Tuple[str, object]] = []
    for name in pipeline_names:
        if hasattr(module, name):
            callable_obj = getattr(module, name)
            if callable(callable_obj):
                pipelines.append((name, callable_obj))

    return pipelines


def compile_pipeline(pipeline_callable: object, output_stub: str) -> None:
    """Compile a pipeline function to a JSON package.

    Args:
        pipeline_callable: The pipeline function to compile.
        output_stub: Base name for the output file (without extension).

    Raises:
        Exception: If compilation fails.
    """
    compiler_instance = compiler.Compiler()
    with tempfile.TemporaryDirectory() as temp_dir:
        package_path = Path(temp_dir) / f"{output_stub}.json"
        compiler_instance.compile(
            pipeline_func=pipeline_callable,
            package_path=str(package_path),
        )


def main() -> int:
    """Main entry point for validating example pipelines.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    targets = normalize_targets(args.paths)
    example_files = discover_example_files(targets)

    if not example_files:
        print("No example_pipelines.py modules found. Nothing to validate.")
        return 0

    failures: List[str] = []
    compiled: List[str] = []

    for module_path in example_files:
        module = load_module_from_path(module_path)
        pipelines = collect_pipeline_functions(module_path, module)
        if not pipelines:
            print(f"⚠️  {module_path.relative_to(REPO_ROOT)} exports no @dsl.pipeline functions.")
            continue

        for pipeline_name, pipeline_callable in pipelines:
            stub_name = f"{module_path.stem}__{pipeline_name}"
            try:
                compile_pipeline(pipeline_callable, stub_name)
                compiled.append(f"{module_path.relative_to(REPO_ROOT)}::{pipeline_name}")
            except Exception:
                tb = traceback.format_exc()
                failure_message = f"{module_path.relative_to(REPO_ROOT)}::{pipeline_name} failed to compile:\n{tb}"
                failures.append(failure_message)

    for entry in compiled:
        print(f"✅ Compiled {entry}")

    if failures:
        print("❌ Example pipeline compilation failures detected:")
        for failure in failures:
            print(failure)
        return 1

    print("All discovered example pipelines compiled successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
