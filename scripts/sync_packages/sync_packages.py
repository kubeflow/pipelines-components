#!/usr/bin/env python3
"""Sync the packages list in pyproject.toml with discovered packages.

Discovers packages under components/ and pipelines/, maps them to the
kfp_components.* namespace, and updates the static packages list in
pyproject.toml.

Usage:
    uv run python -m scripts.sync_packages.sync_packages
"""

import re
import sys
import tomllib
from pathlib import Path

from setuptools import find_packages

from ..lib.discovery import get_repo_root

# Regex to find the packages list in pyproject.toml.
_PACKAGES_RE = re.compile(
    r"(\[tool\.setuptools\]\s*\n(?:(?!\[).*\n)*?)(packages\s*=\s*\[.*?\])",
    re.DOTALL,
)


def discover_packages(repo_root: Path | None = None) -> list[str]:
    """Discover packages and map to kfp_components namespace.

    Args:
        repo_root: Repository root directory. Defaults to auto-detected root.

    Returns:
        Sorted list of fully-qualified package names.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    physical = find_packages(
        where=str(repo_root),
        include=["components", "components.*", "pipelines", "pipelines.*"],
        exclude=["*.tests", "*.tests.*"],
    )
    return sorted(["kfp_components"] + [f"kfp_components.{p}" for p in physical])


def _read_current_packages(pyproject_path: Path) -> list[str]:
    """Read the current packages list from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml.

    Returns:
        Current packages list from [tool.setuptools].

    Raises:
        RuntimeError: If pyproject.toml cannot be parsed or has unexpected structure.
    """
    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(f"Failed to parse pyproject.toml: {e}") from e

    packages = pyproject.get("tool", {}).get("setuptools", {}).get("packages", [])

    if not isinstance(packages, list):
        raise RuntimeError("tool.setuptools.packages must be a list")

    return packages


def sync_packages(repo_root: Path | None = None) -> None:
    """Update the packages list in pyproject.toml.

    Args:
        repo_root: Repository root directory. Defaults to auto-detected root.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    pyproject_path = repo_root / "pyproject.toml"
    content = pyproject_path.read_text()

    # Read current packages list from pyproject.toml.
    current_packages = _read_current_packages(pyproject_path)
    discovered = discover_packages(repo_root)

    if sorted(current_packages) == discovered:
        print("pyproject.toml packages already in sync.")
        return

    lines = ",\n".join([f'    "{p}"' for p in discovered])
    new_block = f"packages = [\n{lines},\n]"

    match = _PACKAGES_RE.search(content)
    if not match:
        raise RuntimeError("Could not find 'packages = [...]' under [tool.setuptools] in pyproject.toml")

    updated = content[: match.start(2)] + new_block + content[match.end(2) :]

    pyproject_path.write_text(updated)
    print(f"Synced {len(discovered)} packages in pyproject.toml")


def main() -> int:
    """Main entry point."""
    try:
        sync_packages()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
