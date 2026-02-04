#!/usr/bin/env python3
"""Detect changed components and pipelines in a git repository."""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

# Patterns for matching asset paths.
# Subcategory paths have 4 segments: <type>/<category>/<subcategory>/<name>/
# Direct paths have 3 segments:      <type>/<category>/<name>/
COMPONENT_SUBCAT_PATTERN = re.compile(r"^components/([^/]+)/([^/]+)/([^/]+)/")
COMPONENT_PATTERN = re.compile(r"^components/([^/]+)/([^/]+)/")
PIPELINE_SUBCAT_PATTERN = re.compile(r"^pipelines/([^/]+)/([^/]+)/([^/]+)/")
PIPELINE_PATTERN = re.compile(r"^pipelines/([^/]+)/([^/]+)/")

# Subdirectories that belong to a direct asset, not a subcategory.
# e.g. components/<cat>/<name>/tests/... should resolve to the direct asset
_RESERVED_SUBDIRS = {"tests", "shared"}


@dataclass
class DetectionResult:
    """Result of detecting changed components and pipelines."""

    components: list[str] = field(default_factory=list)
    pipelines: list[str] = field(default_factory=list)
    all_changed_files: list[str] = field(default_factory=list)
    filtered_changed_files: list[str] = field(default_factory=list)

    @property
    def has_changed_components(self) -> bool:
        """Whether any components have changed."""
        return len(self.components) > 0

    @property
    def has_changed_pipelines(self) -> bool:
        """Whether any pipelines have changed."""
        return len(self.pipelines) > 0

    @property
    def has_changes(self) -> bool:
        """Whether any components or pipelines have changed."""
        return self.has_changed_components or self.has_changed_pipelines


class GitClient:
    """Client for git operations."""

    def run(self, args: list[str], check: bool = True) -> str:
        """Run a git command and return stdout.

        Args:
            args: Git command arguments (without 'git' prefix).
            check: Whether to raise on non-zero exit code.

        Returns:
            Command stdout, or empty string on failure.
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"DEBUG: Git command failed: {' '.join(args)}")
            print(f"DEBUG: Error: {e}")
            print(f"DEBUG: Error output: {e.stderr}")
            print(f"DEBUG: Error code: {e.returncode}")
            raise

    def fetch_branch(self, base_ref: str) -> None:
        """Fetch the base branch if it's a remote reference.

        Args:
            base_ref: Git reference (e.g., 'origin/main', 'origin/release-1.11').
        """
        if not base_ref.startswith("origin/"):
            return

        # origin/HEAD is a symbolic reference that exists after cloning and
        # points to the default branch. It cannot be fetched like a regular
        # branch since "HEAD" is not a valid branch name on the remote.
        if base_ref == "origin/HEAD":
            return

        base_branch = base_ref.removeprefix("origin/")

        # Try full fetch first, then shallow fetch
        if self.run(["fetch", "origin", f"{base_branch}:refs/remotes/origin/{base_branch}"], check=False) == "":
            self.run(["fetch", "--depth=100", "origin", base_branch], check=False)

    def get_changed_files(self, base_ref: str, head_ref: str, skip_deleted_files: bool = False) -> list[str]:
        """Get the list of changed files between two refs.

        Args:
            base_ref: Base git reference to compare against.
            head_ref: Head git reference to compare.
            skip_deleted_files: Whether to skip deleted files.

        Returns:
            List of changed file paths.
        """
        merge_base = self.run(["merge-base", base_ref, head_ref], check=False)

        try:
            if skip_deleted_files:
                # Use --diff-filter to exclude deleted files
                diff_flag = "--diff-filter=d"  # 'd' means exclude deleted
            else:
                diff_flag = None

            if merge_base:
                cmd = ["diff", "--name-only"]
                if diff_flag:
                    cmd.append(diff_flag)
                cmd.extend([merge_base, head_ref])
                diff_output = self.run(cmd)
            else:
                # Try three-dot notation first, then two-dot
                cmd = ["diff", "--name-only"]
                if diff_flag:
                    cmd.append(diff_flag)
                cmd.append(f"{base_ref}...{head_ref}")
                diff_output = self.run(cmd)
        except subprocess.CalledProcessError as e:
            print(f"DEBUG: Error getting changed files: {e}")
            raise

        changed_files = [f for f in diff_output.split("\n") if f]
        return changed_files


class ChangeDetector:
    """Detects changed components and pipelines between git refs."""

    def __init__(self, git_client: GitClient | None = None) -> None:
        """Initialize the detector.

        Args:
            git_client: GitClient instance (defaults to new instance if not provided).
        """
        self.git = git_client or GitClient()

    def detect(
        self,
        base_ref: str,
        head_ref: str,
        filter_pattern: str = "",
        skip_deleted_files: bool = False,
    ) -> DetectionResult:
        """Detect changed components and pipelines.

        Args:
            base_ref: Base git reference to compare against.
            head_ref: Head git reference to compare.
            filter_pattern: Optional regex pattern to filter files.
            skip_deleted_files: Whether to skip deleted files.

        Returns:
            DetectionResult with all detected changes.
        """
        self.git.fetch_branch(base_ref)
        changed_files = self.git.get_changed_files(base_ref, head_ref, skip_deleted_files)
        filtered_files = self._apply_filter(changed_files, filter_pattern)
        components, pipelines = self._parse_changed_files(filtered_files)

        return DetectionResult(
            components=components,
            pipelines=pipelines,
            all_changed_files=changed_files,
            filtered_changed_files=filtered_files,
        )

    def _apply_filter(self, files: list[str], pattern: str) -> list[str]:
        """Filter files by regex pattern.

        Args:
            files: List of file paths to filter.
            pattern: Regex pattern to match against.

        Returns:
            Filtered list of files, or original list if pattern is empty/invalid.
        """
        if not pattern:
            return files

        try:
            regex = re.compile(pattern)
            return [f for f in files if regex.search(f)]
        except re.error:
            return files

    def _parse_changed_files(self, files: list[str]) -> tuple[list[str], list[str]]:
        """Parse changed files to extract component and pipeline paths.

        Args:
            files: List of changed file paths.

        Returns:
            Tuple of (components, pipelines) lists.
        """
        components: set[str] = set()
        pipelines: set[str] = set()

        for file_path in files:
            if match := COMPONENT_SUBCAT_PATTERN.match(file_path):
                category, second, third = match.group(1), match.group(2), match.group(3)
                if third in _RESERVED_SUBDIRS:
                    components.add(f"components/{category}/{second}")
                else:
                    components.add(f"components/{category}/{second}/{third}")
            elif match := COMPONENT_PATTERN.match(file_path):
                components.add(f"components/{match.group(1)}/{match.group(2)}")
            elif match := PIPELINE_SUBCAT_PATTERN.match(file_path):
                category, second, third = match.group(1), match.group(2), match.group(3)
                if third in _RESERVED_SUBDIRS:
                    pipelines.add(f"pipelines/{category}/{second}")
                else:
                    pipelines.add(f"pipelines/{category}/{second}/{third}")
            elif match := PIPELINE_PATTERN.match(file_path):
                pipelines.add(f"pipelines/{match.group(1)}/{match.group(2)}")

        return sorted(components), sorted(pipelines)


class OutputWriter:
    """Handles writing detection results to various outputs."""

    def __init__(self, result: DetectionResult) -> None:
        """Initialize with a detection result.

        Args:
            result: The detection result to output.
        """
        self.result = result

    def write_github_output(self) -> None:
        """Write outputs in GitHub Actions format to GITHUB_OUTPUT.

        Skips writing if GITHUB_OUTPUT is not set (i.e., running locally).
        """
        output_file = os.environ.get("GITHUB_OUTPUT")
        if not output_file:
            return

        outputs = {
            "changed-components": " ".join(self.result.components),
            "changed-pipelines": " ".join(self.result.pipelines),
            "changed-components-json": json.dumps(self.result.components),
            "changed-pipelines-json": json.dumps(self.result.pipelines),
            "changed-components-count": str(len(self.result.components)),
            "changed-pipelines-count": str(len(self.result.pipelines)),
            "has-changes": str(self.result.has_changes).lower(),
            "has-changed-components": str(self.result.has_changed_components).lower(),
            "has-changed-pipelines": str(self.result.has_changed_pipelines).lower(),
            "all-changed-files": " ".join(self.result.all_changed_files),
            "filtered-changed-files": " ".join(self.result.filtered_changed_files),
        }

        with open(output_file, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")

    def write_github_summary(self) -> None:
        """Write step summary in GitHub Actions markdown format.

        Skips writing if GITHUB_STEP_SUMMARY is not set (i.e., running locally).
        """
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_file:
            return

        lines = [
            "## Changed Assets",
            "",
            f"**Components:** {len(self.result.components)}",
        ]

        for component in self.result.components:
            lines.append(f"- {component}")

        lines.extend(
            [
                "",
                f"**Pipelines:** {len(self.result.pipelines)}",
            ]
        )

        for pipeline in self.result.pipelines:
            lines.append(f"- {pipeline}")

        with open(summary_file, "a") as f:
            f.write("\n".join(lines) + "\n")

    def print_standalone(self) -> None:
        """Print human-readable output to stdout."""
        print(f"Components: {len(self.result.components)}")
        for component in self.result.components:
            print(f"  - {component}")

        print(f"Pipelines: {len(self.result.pipelines)}")
        for pipeline in self.result.pipelines:
            print(f"  - {pipeline}")

        print(f"All changed files: {len(self.result.all_changed_files)}")
        for file in self.result.all_changed_files:
            print(f"  - {file}")

        print(f"Filtered changed files: {len(self.result.filtered_changed_files)}")
        if len(self.result.filtered_changed_files) != len(self.result.all_changed_files):
            # Filter was applied, print only filtered files
            for file in self.result.filtered_changed_files:
                print(f"  - {file}")
        else:
            print("(No files excluded by filter, filtered_changed_files is the same as all_changed_files listed above)")

    def write_all(self, include_standalone: bool = False) -> None:
        """Write to all GitHub Actions outputs.

        Args:
            include_standalone: Also print to stdout for local runs.
        """
        self.write_github_output()
        self.write_github_summary()
        if include_standalone:
            self.print_standalone()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Detect changed components and pipelines in a git repository.",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/HEAD",
        help="Base git reference to compare against (default: origin/HEAD)",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git reference to compare (default: HEAD)",
    )
    parser.add_argument(
        "--filter",
        default="",
        help="Regex pattern to filter changed files",
    )
    parser.add_argument(
        "--skip-deleted-files",
        action="store_true",
        help="Whether to skip deleted files",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Run detection
    detector = ChangeDetector()
    result = detector.detect(args.base_ref, args.head_ref, args.filter, args.skip_deleted_files)

    # Write outputs
    output = OutputWriter(result)
    is_local = not os.environ.get("GITHUB_ACTIONS")
    output.write_all(include_standalone=is_local)

    return 0


if __name__ == "__main__":
    sys.exit(main())
