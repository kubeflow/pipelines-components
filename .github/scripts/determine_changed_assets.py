#!/usr/bin/env python3
"""Resolve changed component/pipeline directories for targeted CI runs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Set


def parse_changed_files(raw: str) -> Iterable[Path]:
    for entry in raw.split():
        entry = entry.strip()
        if not entry:
            continue
        yield Path(entry)


def determine_target(relative_path: Path) -> Path | None:
    parts = relative_path.parts
    if not parts or parts[0] not in {"components", "pipelines"}:
        return None
    if len(parts) >= 3:
        return Path(*parts[:3])
    return relative_path


def main() -> None:
    changed_files = os.environ.get("CHANGED_FILES", "")
    targets: Set[Path] = set()

    for path in parse_changed_files(changed_files):
        target = determine_target(path)
        if target is not None:
            targets.add(target)

    output = "\n".join(sorted(str(target) for target in targets))
    github_output = os.environ.get("GITHUB_OUTPUT")

    if not github_output:
        if output:
            print(output)
        return

    with Path(github_output).open("a", encoding="utf-8") as handle:
        handle.write("paths<<EOF\n")
        handle.write(output)
        handle.write("\nEOF\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Failed to resolve component targets: {exc}") from exc

