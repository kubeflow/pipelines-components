#!/usr/bin/env python3
"""Sync the packages list in pyproject.toml with discovered packages.

Discovers packages under components/ and pipelines/, maps them to the
kfp_components.* namespace, and updates the static packages list in
pyproject.toml.

Usage:
    uv run scripts/sync_packages.py
"""

import re
from pathlib import Path

from setuptools import find_packages

REPO_ROOT = Path(__file__).resolve().parent.parent


def discover_packages() -> list[str]:
    """Discover packages and map to kfp_components namespace."""
    physical = find_packages(
        where=str(REPO_ROOT),
        include=["components", "components.*", "pipelines", "pipelines.*"],
        exclude=["*.tests", "*.tests.*"],
    )
    return sorted(["kfp_components"] + [f"kfp_components.{p}" for p in physical])


def sync_packages() -> None:
    """Update the packages list in pyproject.toml."""
    pyproject = REPO_ROOT / "pyproject.toml"
    content = pyproject.read_text()
    packages = discover_packages()

    lines = ",\n".join([f'    "{p}"' for p in packages])
    new_block = f"packages = [\n{lines},\n]"

    updated = re.sub(
        r"packages\s*=\s*\[.*?\]",
        new_block,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if updated == content:
        print("pyproject.toml packages already in sync.")
        return

    pyproject.write_text(updated)
    print(f"Synced {len(packages)} packages in pyproject.toml")


if __name__ == "__main__":
    sync_packages()
