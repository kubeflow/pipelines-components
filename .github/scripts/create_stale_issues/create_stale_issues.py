"""Create GitHub issues for components approaching or past their verification deadline."""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from jinja2 import Environment, FileSystemLoader

# Add repo root to path so we can import from scripts/
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts.check_component_freshness.check_component_freshness import scan_repo  # noqa: E402

LABEL = "stale-component"
TEMPLATE_DIR = Path(__file__).parent
ISSUE_BODY_TEMPLATE = "issue_body.md.j2"

# Maximum issues to check when looking for duplicates (GitHub API max is 100)
MAX_ISSUES_PER_PAGE = 100
# GitHub API limits assignees to 10 per issue
MAX_ASSIGNEES = 10


def get_issue_title(component_name: str) -> str:
    """Generate the standard issue title for a stale component."""
    return f"Component `{component_name}` needs verification"


def get_owners(component_path: Path) -> list[str]:
    """Read OWNERS file for a component."""
    owners_file = component_path / "OWNERS"
    if not owners_file.exists():
        return []
    try:
        owners = yaml.safe_load(owners_file.read_text())
        return owners.get("approvers", []) if owners else []
    except Exception:
        return []


def create_issue_body(component: dict, repo_path: Path) -> str:
    """Generate the issue body with instructions using Jinja2 template."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(ISSUE_BODY_TEMPLATE)

    owners = get_owners(repo_path / component["path"])
    owners_mention = ", ".join(f"@{o}" for o in owners) if owners else "No owners found"

    return template.render(
        name=component["name"],
        path=component["path"],
        last_verified=component["last_verified"],
        age_days=component["age_days"],
        owners_mention=owners_mention,
        today=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )


def issue_exists(repo: str, component_name: str, token: str | None) -> bool:
    """Check if an open issue already exists for this component."""
    expected_title = get_issue_title(component_name)
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            headers=headers,
            params={"state": "open", "labels": LABEL, "per_page": MAX_ISSUES_PER_PAGE},
            timeout=30,
        )
        resp.raise_for_status()
        return any(issue["title"] == expected_title for issue in resp.json())
    except Exception as e:
        print(f"Failed to check for existing issue: {e}", file=sys.stderr)
        return False


def create_issue(repo: str, component: dict, repo_path: Path, token: str | None, dry_run: bool) -> bool:
    """Create a GitHub issue for a component needing verification."""
    title = get_issue_title(component["name"])
    owners = get_owners(repo_path / component["path"])
    assignees = owners[:MAX_ASSIGNEES]

    if dry_run:
        print(f"[DRY RUN] Would create: {title}")
        print(f"  Assignees: {assignees}")
        return True

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    body = create_issue_body(component, repo_path)

    try:
        resp = requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=headers,
            json={"title": title, "body": body, "labels": [LABEL], "assignees": assignees},
            timeout=30,
        )
        resp.raise_for_status()
        print(f"Created: {resp.json().get('html_url')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to create issue for {component['name']}: {e}", file=sys.stderr)
        return False


def create_issues_for_stale_components(repo: str, token: str | None, dry_run: bool) -> int:
    """Create GitHub issues for components in warning or stale status."""
    repo_path = REPO_ROOT
    results = scan_repo(repo_path)
    # Include both warning (270-360 days) and stale (>360 days) components
    components_needing_attention = results.get("warning", []) + results.get("stale", [])

    if not components_needing_attention:
        print("No components need verification.")
        return 0

    warning_count = len(results.get("warning", []))
    stale_count = len(results.get("stale", []))
    print(f"Found {len(components_needing_attention)} component(s) needing verification")
    print(f"  Warning: {warning_count}, Stale: {stale_count}\n")

    created, skipped = 0, 0
    for component in components_needing_attention:
        if issue_exists(repo, component["name"], token):
            print(f"Skipping {component['name']}: issue already exists")
            skipped += 1
            continue
        if create_issue(repo, component, repo_path, token, dry_run):
            created += 1

    print(f"\nSummary: {created} created, {skipped} skipped")


def main():
    """Create GitHub issues for components needing staleness or deletion verification."""
    parser = argparse.ArgumentParser(description="Create GitHub issues for components needing verification")
    parser.add_argument("--repo", required=True, help="GitHub repo (e.g., owner/repo)")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Print without creating")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: No GitHub token provided. API requests will be subject to rate limiting.", file=sys.stderr)
        print("Use --token or set GITHUB_TOKEN environment variable for authenticated requests.", file=sys.stderr)

    create_issues_for_stale_components(args.repo, token, args.dry_run)


if __name__ == "__main__":
    main()
