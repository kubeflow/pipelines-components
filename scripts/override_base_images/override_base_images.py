#!/usr/bin/env python3
"""Override base_image references from :main to PR-specific SHA tags.

This script is used during CI to replace :main tags with commit-specific SHA tags
so that PR validation tests use the freshly-built images instead of the latest main.
"""

import argparse
import sys

from ..lib.base_image import override_base_images


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Override base_image references from :main to PR-specific SHA tags")
    parser.add_argument(
        "commit_sha",
        help="The commit SHA to use as the new image tag",
    )
    parser.add_argument(
        "image_prefix",
        help="Image prefix to override (e.g., ghcr.io/kubeflow/pipelines-components)",
    )
    parser.add_argument(
        "--directories",
        nargs="+",
        required=True,
        help="Directories to scan (e.g., components pipelines)",
    )

    args = parser.parse_args()

    print(f"Overriding base_image references from :main to :{args.commit_sha}")
    try:
        override_base_images(
            args.directories,
            args.commit_sha,
            args.image_prefix,
        )
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Catch-all to avoid unhandled exceptions causing raw stack traces in CLI usage.
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
