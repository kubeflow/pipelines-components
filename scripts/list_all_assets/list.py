#!/usr/bin/env python3
"""List all components and pipelines in the repository."""

import os

from ..lib.discovery import find_assets_with_metadata


def main() -> None:
    """CLI entry point."""
    components = find_assets_with_metadata("components")
    pipelines = find_assets_with_metadata("pipelines")
    all_assets = components + pipelines

    if output_file := os.environ.get("GITHUB_OUTPUT"):
        with open(output_file, "a") as f:
            f.write(f"all-components={' '.join(components)}\n")
            f.write(f"all-pipelines={' '.join(pipelines)}\n")
            f.write(f"all-assets={' '.join(all_assets)}\n")

    if not os.environ.get("GITHUB_ACTIONS"):
        print(f"Components: {len(components)}")
        for c in components:
            print(f"  - {c}")
        print(f"\nPipelines: {len(pipelines)}")
        for p in pipelines:
            print(f"  - {p}")
        print(f"\nTotal: {len(all_assets)}")


if __name__ == "__main__":
    main()
