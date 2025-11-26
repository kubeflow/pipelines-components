#!/usr/bin/env python3
"""Check that base_image references to pipelines-components images use :main tag.

This ensures components reference the latest images rather than specific SHAs or versions.
The CI will override these with PR-specific tags during validation.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lib.tags import check_base_image_tags


def _print_results(results: list[dict], all_valid: bool) -> None:
    """Print the check results to stdout."""
    print("Checking that base_image references use :main tag...")

    if all_valid:
        print()
        print("✓ All base_image references use :main tag (or no references found)")
        return

    for r in results:
        if r.get("status") != "invalid":
            continue
        print(f"  ✗ {r['file']}:{r['line_num']}: does not use :main tag")
        if "found" in r:
            print(f"    Found: {r['found']}")
            print(f"    Expected: {r['expected']}")
        else:
            print(f"    Error: {r.get('error', 'unknown error')}")

    print()
    print("✗ Some base_image references do not use :main tag")
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

    all_valid, results = check_base_image_tags(args.directories, args.image_prefix)
    _print_results(results, all_valid)

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
