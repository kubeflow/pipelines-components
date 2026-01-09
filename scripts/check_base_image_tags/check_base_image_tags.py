#!/usr/bin/env python3
"""Check that base_image references to pipelines-components images use :main tag.

This ensures components reference the latest images rather than specific SHAs or versions.
The CI will override these with PR-specific tags during validation.
"""

import argparse
import sys

from ..lib.base_image import BaseImageTagCheckError, check_base_image_tags


def _print_results(results: list[dict], all_valid: bool) -> None:
    """Print the check results to stdout."""
    print("🔍 Checking that base_image references use :main tag...")

    if all_valid:
        print()
        print("✅ All base_image references use :main tag (or no references found)")
        return

    for r in results:
        if r.get("status") != "invalid":
            continue
        location = r["file"] if r.get("line_num", 0) == 0 else f"{r['file']}:{r['line_num']}"
        print(f"  ❌ {location}: does not use :main tag")
        if "found" in r:
            print(f"    Found: {r['found']}")
            print(f"    Expected: {r['expected']}")
        else:
            print(f"    Error: {r.get('error', 'unknown error')}")

    print()
    print("❌ Some base_image references do not use :main tag")
    print("  Components should reference :main to use the latest images.")
    print("  The CI will override these with PR-specific tags during validation.")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Check that base_image references use :main tag")
    parser.add_argument(
        "image_prefix",
        help="Image prefix to check (e.g., ghcr.io/kubeflow/pipelines-components)",
    )
    parser.add_argument(
        "--directories",
        nargs="+",
        required=True,
        help="Directories to scan (e.g., components pipelines)",
    )

    args = parser.parse_args()

    try:
        all_valid, results = check_base_image_tags(args.directories, args.image_prefix)
    except BaseImageTagCheckError as e:
        print("🔍 Checking that base_image references use :main tag...")
        print()
        print(f"❌ Failed to compile/check base images for {e.asset_file}: {e}")
        return 1

    _print_results(results, all_valid)
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
