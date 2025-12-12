#!/usr/bin/env python3
"""Validate example_pipelines modules by compiling every exported pipeline."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import traceback
from pathlib import Path
from types import ModuleType
from typing import List, Sequence, Set, Tuple

try:
    from kfp import compiler, dsl
except ImportError as exc:  
    raise SystemExit(
        "kfp is required to validate example pipelines. "
        "Install it with `pip install kfp`."
    ) from exc

# Add scripts directory to path for imports
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import find_pipeline_functions, get_repo_root, normalize_targets

REPO_ROOT = get_repo_root()


def parse_args() -> argparse.Namespace:
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
    discovered: List[Path] = []
    seen: Set[Path] = set()

    for target in targets:
        search_root = target if target.is_dir() else target.parent

        for candidate in search_root.rglob("example_pipelines.py"):
            if candidate in seen or not candidate.is_file():
                continue
            try:
                relative = candidate.relative_to(REPO_ROOT)
            except ValueError:
                continue
            if relative.parts and relative.parts[0] in {"components", "pipelines"}:
                seen.add(candidate)
                discovered.append(candidate)

    return discovered


def load_module_from_path(module_path: Path) -> ModuleType:
    relative = module_path.relative_to(REPO_ROOT)
    sanitized = "_".join(relative.with_suffix("").parts)
    module_name = f"example_pipelines__{sanitized}"

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  
        raise ImportError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
    compiler_instance = compiler.Compiler()
    with tempfile.TemporaryDirectory() as temp_dir:
        package_path = Path(temp_dir) / f"{output_stub}.json"
        compiler_instance.compile(
            pipeline_func=pipeline_callable,
            package_path=str(package_path),
        )


def main() -> int:
    args = parse_args()
    targets = normalize_targets(args.paths, REPO_ROOT)
    example_files = discover_example_files(targets)

    if not example_files:
        print("No example_pipelines.py modules found. Nothing to validate.")
        return 0

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

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
                failure_message = (
                    f"{module_path.relative_to(REPO_ROOT)}::{pipeline_name} failed to compile:\n{tb}"
                )
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

