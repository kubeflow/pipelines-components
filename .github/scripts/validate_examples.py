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
from typing import Iterable, List, Sequence, Set, Tuple

try:
    from kfp import compiler, dsl
except ImportError as exc:  # pragma: no cover - surfaced to callers
    raise SystemExit(
        "kfp is required to validate example pipelines. "
        "Install it with `pip install kfp`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = (REPO_ROOT / "components", REPO_ROOT / "pipelines")
PIPELINE_ATTRS = ("pipeline_func", "_pipeline_func", "pipeline_spec")


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


def normalize_targets(raw_paths: Sequence[str]) -> List[Path]:
    if not raw_paths:
        return [target for target in DEFAULT_TARGETS if target.exists()]

    normalized: List[Path] = []
    for raw in raw_paths:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (REPO_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Specified path does not exist: {raw}")
        normalized.append(candidate)
    return normalized


def discover_example_files(targets: Sequence[Path]) -> List[Path]:
    discovered: List[Path] = []
    seen: Set[Path] = set()

    for target in targets:
        search_root = target if target.is_dir() else target.parent

        for candidate in _possible_example_paths(search_root):
            if candidate in seen:
                continue
            try:
                relative = candidate.relative_to(REPO_ROOT)
            except ValueError:
                continue
            if relative.parts and relative.parts[0] in {"components", "pipelines"}:
                seen.add(candidate)
                discovered.append(candidate)

    return discovered


def _possible_example_paths(search_root: Path) -> Iterable[Path]:
    if search_root.name == "example_pipelines.py" and search_root.is_file():
        yield search_root
        return

    candidate = search_root / "example_pipelines.py"
    if candidate.is_file():
        yield candidate

    for nested in search_root.rglob("example_pipelines.py"):
        if nested.is_file():
            yield nested


def load_module_from_path(module_path: Path) -> ModuleType:
    relative = module_path.relative_to(REPO_ROOT)
    sanitized = "_".join(relative.with_suffix("").parts)
    module_name = f"example_pipelines__{sanitized}"

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def collect_pipeline_functions(module: ModuleType) -> List[Tuple[str, object]]:
    pipelines: List[Tuple[str, object]] = []
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        if _looks_like_pipeline(attribute):
            pipelines.append((attribute_name, attribute))
    return pipelines


def _looks_like_pipeline(obj: object) -> bool:
    if obj is None or not callable(obj):
        return False
    pipeline_cls = getattr(dsl, "Pipeline", None)
    if pipeline_cls and isinstance(obj, pipeline_cls):
        return True
    return any(hasattr(obj, attr) for attr in PIPELINE_ATTRS)


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
    targets = normalize_targets(args.paths)
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
        pipelines = collect_pipeline_functions(module)
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
    raise SystemExit(main())

