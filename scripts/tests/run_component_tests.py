#!/usr/bin/env python3
"""Pytest discovery helper for Kubeflow components and pipelines.

This script discovers `tests/` directories under the provided component or
pipeline paths and runs pytest with a two-minute timeout per test.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Sequence, Set

import pytest

# Add .github/scripts directory to path for imports
_GITHUB_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / ".github" / "scripts"
if str(_GITHUB_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_GITHUB_SCRIPTS_DIR))

from utils import get_repo_root, normalize_targets

REPO_ROOT = get_repo_root()
TIMEOUT_SECONDS = 120


def parse_args() -> argparse.Namespace:
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
    discovered: List[Path] = []
    seen: Set[Path] = set()

    for target in targets:
        search_root = target if target.is_dir() else target.parent
        if not search_root.exists():
            continue

        direct = search_root / "tests"
        if direct.is_dir():
            _record_dir(discovered, seen, direct)

        for candidate in search_root.rglob("tests"):
            if candidate.is_dir():
                _record_dir(discovered, seen, candidate)

    return discovered


def _record_dir(storage: List[Path], seen: Set[Path], candidate: Path) -> None:
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError:
        return

    if not relative.parts or relative.parts[0] not in {"components", "pipelines"}:
        return

    if candidate not in seen:
        seen.add(candidate)
        storage.append(candidate)


def ensure_required_plugins() -> None:
    try:
        import pytest_timeout  
    except ImportError as exc:  
        raise SystemExit(
            "pytest-timeout is required. Install it with `pip install pytest-timeout`."
        ) from exc


def build_pytest_args(
    test_dirs: Sequence[Path],
    timeout_seconds: int,
    verbose: bool,
) -> List[str]:
    args: List[str] = [
        f"--timeout={timeout_seconds}",
        "--timeout-method=signal",
    ]
    if verbose:
        args.append("-vv")

    args.extend(str(directory) for directory in test_dirs)
    return args


def main() -> int:
    args = parse_args()
    targets = normalize_targets(args.paths, REPO_ROOT)
    test_dirs = discover_test_dirs(targets)

    if not test_dirs:
        print("No tests/ directories found under the supplied paths. Nothing to do.")
        return 0

    ensure_required_plugins()

    relative_dirs = ", ".join(
        str(directory.relative_to(REPO_ROOT)) for directory in test_dirs
    )
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

