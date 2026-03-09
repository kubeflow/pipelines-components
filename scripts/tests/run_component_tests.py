#!/usr/bin/env python3
"""Pytest discovery helper for Kubeflow components and pipelines.

This script discovers `tests/` directories under the provided component or
pipeline paths and runs pytest with a two-minute timeout per test.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import List, Sequence

import pytest

from ..lib.discovery import get_repo_root, normalize_targets

REPO_ROOT = get_repo_root()
TIMEOUT_SECONDS = 120


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Discover tests/ directories for the specified components or pipelines "
            "and execute pytest with a two-minute timeout per test."
        )
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        help=(
            "Component or pipeline directories (or files within them) to test. "
            "If omitted, all components and pipelines are scanned."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help="Per-test timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass the -vv flag to pytest for more detailed output.",
    )
    return parser.parse_args()


def discover_test_dirs(targets: Sequence[Path]) -> List[Path]:
    """Discover tests/ directories under the given targets.

    Args:
        targets: Sequence of component or pipeline paths to search.

    Returns:
        List of discovered tests/ directory paths.
    """
    discovered: List[Path] = []

    for target in targets:
        search_root = target if target.is_dir() else target.parent
        if not search_root.exists():
            continue

        # Direct tests/ folder
        direct = search_root / "tests"
        if direct.is_dir() and _is_member_of_pipeline_or_component(direct):
            if direct not in discovered:
                discovered.append(direct)
        else:
            # Broader target (category, subcategory, or repo root) –
            # recurse to find all nested tests/ directories.
            for tests_dir in sorted(search_root.rglob("tests")):
                if tests_dir.is_dir() and _is_member_of_pipeline_or_component(tests_dir):
                    if tests_dir not in discovered:
                        discovered.append(tests_dir)

    return discovered


def _is_member_of_pipeline_or_component(candidate: Path) -> bool:
    """Check if a path is within components/ or pipelines/ directory.

    Args:
        candidate: Path to check.

    Returns:
        True if the path is within components/ or pipelines/, False otherwise.
    """
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError:
        warnings.warn(
            f"Unable to determine relative path for {candidate} relative to repo root {REPO_ROOT}. Skipping.",
        )
        return False

    return relative.parts and relative.parts[0] in {"components", "pipelines"}


def build_pytest_args(
    test_dirs: Sequence[Path],
    timeout_seconds: int,
    verbose: bool,
) -> List[str]:
    """Build pytest command-line arguments.

    Args:
        test_dirs: Directories containing tests to run.
        timeout_seconds: Per-test timeout in seconds.
        verbose: Whether to enable verbose pytest output.

    Returns:
        List of pytest command-line arguments.
    """
    args: List[str] = [
        f"--timeout={timeout_seconds}",
        "--timeout-method=signal",
    ]
    if verbose:
        args.append("-vv")

    args.extend(str(directory) for directory in test_dirs)
    return args


def main() -> int:
    """Main entry point for running component/pipeline tests.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    targets = normalize_targets(args.paths)
    test_dirs = discover_test_dirs(targets)

    if not test_dirs:
        print("No tests/ directories found under the supplied paths. Nothing to do.")
        return 0

    relative_dirs = ", ".join(str(directory.relative_to(REPO_ROOT)) for directory in test_dirs)
    print(f"Running pytest for: {relative_dirs}")

    pytest_args = build_pytest_args(
        test_dirs=test_dirs,
        timeout_seconds=args.timeout,
        verbose=args.verbose,
    )

    exit_code = pytest.main(pytest_args)
    if exit_code == 0:
        print("✅ Pytest completed successfully.")
    else:
        print("❌ Pytest reported failures. See log above for details.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
