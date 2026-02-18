#!/usr/bin/env python3
"""Check that base_image references to pipelines-components images use the expected tag.

This ensures components reference the correct images for the branch.
The CI will override these with PR-specific tags during validation.
"""

import argparse
import sys

from ..lib.base_image import BaseImageTagCheckError, check_base_image_tags


def _print_results(results: list[dict], all_valid: bool, expected_tag: str) -> None:
    """Print the check results to stdout."""
    print(f"🔍 Checking that base_image references use :{expected_tag} tag...")

    if all_valid:
        print()
        print(f"✅ All base_image references use :{expected_tag} tag (or no references found)")
        return

    for r in results:
        if r.get("status") != "invalid":
            continue
        location = r["file"] if r.get("line_num", 0) == 0 else f"{r['file']}:{r['line_num']}"
        print(f"  ❌ {location}: does not use :{expected_tag} tag")
        if "found" in r:
            print(f"    Found: {r['found']}")
            print(f"    Expected: {r['expected']}")
        else:
            print(f"    Error: {r.get('error', 'unknown error')}")

    print()
    print(f"❌ Some base_image references do not use :{expected_tag} tag")
    print(f'   Update your decorators: base_image="<prefix>-<name>:{expected_tag}"')


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Check that base_image references use the expected tag")
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
    parser.add_argument(
        "--expected-tag",
        required=True,
        help="Expected tag for base images (e.g., main, v1.11.0)",
    )

    args = parser.parse_args()

    try:
        all_valid, results = check_base_image_tags(args.directories, args.image_prefix, args.expected_tag)
    except BaseImageTagCheckError as e:
        print(f"🔍 Checking that base_image references use :{args.expected_tag} tag...")
        print()
        print(f"❌ Failed to compile/check base images for {e.asset_file}: {e}")
        return 1

    _print_results(results, all_valid, args.expected_tag)
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
