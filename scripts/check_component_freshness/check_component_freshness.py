"""Scan metadata.yaml files and categorize components by lastVerified age.

Categories: Fresh (<270 days), Warning (270-360 days), Stale (>360 days)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..lib.discovery import get_all_assets_with_metadata

# Thresholds in days
FRESH_DAYS = 270  # 9 months
STALE_DAYS = 360  # 12 months


def parse_date(date_str: str) -> datetime:
    """Parse lastVerified timestamp from various formats.

    Args:
        date_str: The date string to parse.

    Returns:
        A datetime object representing the parsed date.
    """
    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def categorize(age_days: int) -> str:
    """Categorize component by age in days.

    Args:
        age_days: The age of the component in days.

    Returns:
        A string indicating the category of the component.
    """
    if age_days < FRESH_DAYS:
        return "fresh"
    return "warning" if age_days < STALE_DAYS else "stale"


def scan_repo(repo_path: Path) -> dict:
    """Scan components/ and pipelines/ directories for metadata.yaml files.

    Args:
        repo_path: The path to the repository to scan.

    Returns:
        A dictionary containing the results of the scan.
    """
    now = datetime.now(timezone.utc)
    results = {"fresh": [], "warning": [], "stale": []}

    for asset in get_all_assets_with_metadata(repo_path):
        metadata_file = repo_path / asset / "metadata.yaml"
        try:
            metadata = yaml.safe_load(metadata_file.read_text())
            if not metadata or "lastVerified" not in metadata:
                print(f"Warning: Missing lastVerified in {metadata_file}, marking as stale", file=sys.stderr)
                results["stale"].append(
                    {
                        "name": metadata.get("name", "unknown"),
                        "path": str(asset),
                        "last_verified": "unknown",
                        "age_days": 0,
                    }
                )
                continue

            last_verified = parse_date(metadata["lastVerified"])
            age_days = (now - last_verified).days
            category = categorize(age_days)

            results[category].append(
                {
                    "name": metadata.get("name", "unknown"),
                    "path": str(asset),
                    "last_verified": last_verified.strftime("%Y-%m-%d"),
                    "age_days": age_days,
                }
            )
        except Exception as e:
            print(f"Error processing {metadata_file}: {e}", file=sys.stderr)
            print("Marking as stale", file=sys.stderr)
            results["stale"].append(
                {
                    "name": "unknown",
                    "path": str(asset),
                    "last_verified": "unknown",
                    "age_days": 0,
                }
            )

    return results


def format_report(results: dict) -> str:
    """Format results as a report string.

    Args:
        results: A dictionary containing the results of the scan.

    Returns:
        A string containing the formatted report.
    """
    lines = [
        f"\n🟢 Fresh: {len(results['fresh'])}  "
        f"🟡 Warning: {len(results['warning'])}  "
        f"🔴 Stale: {len(results['stale'])}\n"
    ]

    for key, icon in [("stale", "🔴"), ("warning", "🟡"), ("fresh", "🟢")]:
        for c in sorted(results[key], key=lambda x: -x["age_days"]):
            lines.append(f"{icon} {c['name']:40} {c['age_days']:>4}d  {c['path']}")
    return "\n".join(lines)


def main():
    """Main function to check component verification freshness."""
    parser = argparse.ArgumentParser(description="Check component verification freshness")
    parser.add_argument("repo_path", nargs="?", default=".", help="Repository path")
    parser.add_argument("--json", metavar="FILE", help="Export results as JSON")
    parser.add_argument("-o", "--output", metavar="FILE", help="Write report to file")
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    results = scan_repo(repo_path)
    report = format_report(results)

    if args.output:
        Path(args.output).write_text(report)
    else:
        print(report)

    if args.json:
        total = sum(len(v) for v in results.values())
        Path(args.json).write_text(
            json.dumps(
                {
                    "summary": {k: len(v) for k, v in results.items()} | {"total": total},
                    "components": results,
                },
                indent=2,
            )
        )

    sys.exit(1 if results["stale"] else 0)


if __name__ == "__main__":
    main()
