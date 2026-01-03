#!/usr/bin/env python3
"""Validate that package entries in pyproject.toml are up to date.

This script discovers all Python packages in the components/ and pipelines/
directories and ensures they are properly listed in pyproject.toml under
tool.setuptools.packages.

Usage:
    uv run python scripts/validate_package_entries/validate_package_entries.py
"""

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Set


def get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent.resolve()


def discover_packages(repo_root: Path) -> Set[str]:
    """Discover all Python packages in components/ and pipelines/ directories.

    Returns a set of package names in the format kfp_components.* based on
    the package-dir mapping in pyproject.toml.
    """
    packages: Set[str] = set()

    # Always include the root package
    if (repo_root / "__init__.py").exists():
        packages.add("kfp_components")

    def _discover_recursive(directory: Path, base_package: str) -> None:
        """Recursively discover packages in a directory."""
        if not directory.exists():
            return

        for item in directory.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                # Convert path to package name
                rel_path = item.relative_to(repo_root)
                package_name = "kfp_components." + ".".join(rel_path.parts)
                packages.add(package_name)

                # Recursively discover nested packages
                _discover_recursive(item, package_name)

    # Discover packages in components/
    components_dir = repo_root / "components"
    if components_dir.exists() and (components_dir / "__init__.py").exists():
        packages.add("kfp_components.components")
        _discover_recursive(components_dir, "kfp_components.components")

    # Discover packages in pipelines/
    pipelines_dir = repo_root / "pipelines"
    if pipelines_dir.exists() and (pipelines_dir / "__init__.py").exists():
        packages.add("kfp_components.pipelines")
        _discover_recursive(pipelines_dir, "kfp_components.pipelines")

    return packages


def read_pyproject_packages(repo_root: Path) -> Set[str]:
    """Read the packages list from pyproject.toml."""
    pyproject_path = repo_root / "pyproject.toml"

    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"pyproject.toml not found at {pyproject_path}")
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(f"Failed to parse pyproject.toml: {e}")

    tool_setuptools = pyproject.get("tool", {}).get("setuptools", {})
    packages = tool_setuptools.get("packages", [])

    if not isinstance(packages, list):
        raise RuntimeError("tool.setuptools.packages must be a list")

    if not all(isinstance(p, str) for p in packages):
        raise RuntimeError("All entries in tool.setuptools.packages must be strings")

    return set(packages)


def validate_package_entries(repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """Validate that package entries in pyproject.toml match discovered packages.

    Returns:
        (is_valid, error_messages)
    """
    if repo_root is None:
        repo_root = get_repo_root()

    discovered = discover_packages(repo_root)
    declared = read_pyproject_packages(repo_root)

    errors: list[str] = []

    # Find missing packages (discovered but not declared)
    missing = discovered - declared
    if missing:
        errors.append(
            f"Missing packages in pyproject.toml (found {len(missing)}):\n"
            + "\n".join(f"  - {pkg}" for pkg in sorted(missing))
        )

    # Find extra packages (declared but not discovered)
    extra = declared - discovered
    if extra:
        errors.append(
            f"Extra packages in pyproject.toml (found {len(extra)}):\n"
            + "\n".join(f"  - {pkg}" for pkg in sorted(extra))
        )

    is_valid = len(errors) == 0
    return is_valid, errors


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate package entries in pyproject.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all packages
  uv run python scripts/validate_package_entries/validate_package_entries.py
        """,
    )

    parser.parse_args()

    try:
        is_valid, errors = validate_package_entries()

        if is_valid:
            print("✅ All package entries in pyproject.toml are up to date.")
            return 0
        else:
            print("❌ Package entries in pyproject.toml are out of sync:\n")
            for error in errors:
                print(error)
            print(
                "\nTo fix, update the 'packages' list in pyproject.toml under "
                "[tool.setuptools] to match the discovered packages."
            )
            return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
