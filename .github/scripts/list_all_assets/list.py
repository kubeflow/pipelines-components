#!/usr/bin/env python3
"""List all components and pipelines in the repository."""

import os
from pathlib import Path


def find_assets(asset_type):
    """Find all directories in components/ or pipelines/."""
    assets = []
    base_path = Path(asset_type)
    
    if not base_path.exists():
        return assets
    
    # Find all category/name directories (e.g., components/dev/demo)
    for category in base_path.iterdir():
        if not category.is_dir() or category.name.startswith((".", "_")):
            continue
        
        for asset in category.iterdir():
            if not asset.is_dir() or asset.name.startswith((".", "_")):
                continue
            
            # Only include if it has metadata.yaml
            if (asset / "metadata.yaml").exists():
                assets.append(f"{asset_type}/{category.name}/{asset.name}")
    
    return assets


def main():
    """Main entry point."""
    components = find_assets("components")
    pipelines = find_assets("pipelines")
    all_assets = components + pipelines
    
    # Write GitHub Actions outputs
    if output_file := os.environ.get("GITHUB_OUTPUT"):
        with open(output_file, "a") as f:
            f.write(f"all-components={' '.join(components)}\n")
            f.write(f"all-pipelines={' '.join(pipelines)}\n")
            f.write(f"all-assets={' '.join(all_assets)}\n")
    
    # Print for local use
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

