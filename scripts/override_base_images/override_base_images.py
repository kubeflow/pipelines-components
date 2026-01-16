"""Override base_image references from :main to a specific container tag.

This script is used during CI to replace :main tags with specific container tags (SHA or release)
so that validation tests use the correct images.
"""

import argparse
import sys

from ..lib.base_image import override_base_images


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Override base_image references from :main to a specific container tag"
    )
    parser.add_argument(
        "container_tag",
        help="The new container tag (e.g. a commit SHA or release tag like v1.11.0)",
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

    print(f"Overriding base_image references from :main to :{args.container_tag}")
    try:
        override_base_images(
            args.directories,
            args.container_tag,
            args.image_prefix,
        )
    except FileNotFoundError as exc:
        print(f"Error: File not found: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"Error: Permission denied: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: Invalid value: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
