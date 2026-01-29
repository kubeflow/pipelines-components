"""Handle stale components: create warning issues and removal PRs.

- Warning (270-360 days): Creates GitHub issues to notify owners
- Stale (>360 days): Creates PRs to remove the component
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from jinja2 import Environment, FileSystemLoader

# utils module sets up sys.path and re-exports from scripts/lib/discovery
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(REPO_ROOT))

from scripts.check_component_freshness.check_component_freshness import scan_repo  # noqa: E402
from scripts.generate_readme.category_index_generator import CategoryIndexGenerator  # noqa: E402

ISSUE_LABEL = "stale-component"
REMOVAL_LABEL = "stale-component-removal"
TEMPLATE_DIR = Path(__file__).parent
ISSUE_BODY_TEMPLATE = "issue_body.md.j2"
REMOVAL_PR_BODY_TEMPLATE = "removal_pr_body.md.j2"

# Maximum issues to check when looking for duplicates (GitHub API max is 100)
MAX_ISSUES_PER_PAGE = 100
# GitHub API limits assignees to 10 per issue
MAX_ASSIGNEES = 10


def get_issue_title(component_name: str) -> str:
    """Generate the standard issue title for a warning component."""
    return f"Component `{component_name}` needs verification"


def get_removal_pr_title(component_name: str) -> str:
    """Generate the standard PR title for removing a stale component."""
    return f"chore: Remove stale component `{component_name}`"


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


def create_removal_pr_body(component: dict, repo_path: Path) -> str:
    """Generate the PR body for component removal using Jinja2 template."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(REMOVAL_PR_BODY_TEMPLATE)

    owners = get_owners(repo_path / component["path"])
    owners_mention = ", ".join(f"@{o}" for o in owners) if owners else "No owners found"

    return template.render(
        name=component["name"],
        path=component["path"],
        last_verified=component["last_verified"],
        age_days=component["age_days"],
        owners_mention=owners_mention,
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
            params={"state": "open", "labels": ISSUE_LABEL, "per_page": MAX_ISSUES_PER_PAGE},
            timeout=30,
        )
        resp.raise_for_status()
        return any(issue["title"] == expected_title for issue in resp.json())
    except Exception as e:
        print(f"Failed to check for existing issue: {e}", file=sys.stderr)
        return False


def removal_pr_exists(repo: str, component_name: str) -> bool:
    """Check if an open PR already exists for removing this component."""
    expected_title = get_removal_pr_title(component_name)
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--state", "open", "--json", "title"],
            capture_output=True,
            text=True,
            check=True,
        )
        prs = json.loads(result.stdout)
        return any(pr["title"] == expected_title for pr in prs)
    except subprocess.CalledProcessError as e:
        print(f"Failed to check for existing PR: {e}", file=sys.stderr)
        return False


def create_issue(repo: str, component: dict, repo_path: Path, token: str | None, dry_run: bool) -> bool:
    """Create a GitHub issue for a component needing verification."""
    title = get_issue_title(component["name"])
    owners = get_owners(repo_path / component["path"])
    assignees = owners[:MAX_ASSIGNEES]

    if dry_run:
        print(f"[DRY RUN] Would create issue: {title}")
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
            json={"title": title, "body": body, "labels": [ISSUE_LABEL], "assignees": assignees},
            timeout=30,
        )
        resp.raise_for_status()
        print(f"Created issue: {resp.json().get('html_url')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to create issue for {component['name']}: {e}", file=sys.stderr)
        return False


def get_current_branch() -> str | None:
    """Get the current git branch name, or None if in detached HEAD state."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return None if branch == "HEAD" else branch
    except subprocess.CalledProcessError:
        return None


def create_removal_pr(repo: str, component: dict, repo_path: Path, dry_run: bool) -> bool:
    """Create a PR to remove a stale component using gh CLI."""
    name = component["name"]
    path = component["path"]
    title = get_removal_pr_title(name)
    branch_name = f"remove-stale-{name}"
    owners = get_owners(repo_path / path)

    if dry_run:
        print(f"[DRY RUN] Would create removal PR: {title}")
        print(f"  Branch: {branch_name}")
        print(f"  Removes: {path}")
        print(f"  Updates: {Path(path).parent}/README.md (category index)")
        print(f"  Reviewers: {owners}")
        return True

    # Save original branch to restore later
    original_branch = get_current_branch()

    try:
        # Fetch latest from origin
        subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)

        # Get default branch name
        result = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        default_branch = result.stdout.strip()

        # Create and checkout new branch from default
        subprocess.run(
            ["git", "checkout", "-B", branch_name, f"origin/{default_branch}"],
            check=True,
            capture_output=True,
        )

        # Remove the component directory
        component_dir = repo_path / path
        if component_dir.exists():
            subprocess.run(["git", "rm", "-rf", str(component_dir)], check=True, capture_output=True)
        else:
            print(f"Component directory not found: {component_dir}", file=sys.stderr)
            return False

        # Regenerate category README to remove the component from the index
        category_dir = component_dir.parent
        is_component = "components" in path
        try:
            index_generator = CategoryIndexGenerator(category_dir, is_component=is_component)
            category_readme_content = index_generator.generate()
            category_readme_path = category_dir / "README.md"
            category_readme_path.write_text(category_readme_content)
            subprocess.run(["git", "add", str(category_readme_path)], check=True, capture_output=True)
        except Exception as e:
            print(f"Warning: Could not regenerate category README: {e}", file=sys.stderr)

        # Commit the change
        commit_msg = f"Remove stale component: {name}\n\nComponent has not been verified in {component['age_days']} days."
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)

        # Push the branch
        subprocess.run(["git", "push", "-u", "origin", branch_name, "--force"], check=True, capture_output=True)

        # Create the PR
        body = create_removal_pr_body(component, repo_path)
        pr_cmd = [
            "gh", "pr", "create",
            "--repo", repo,
            "--title", title,
            "--body", body,
            "--label", REMOVAL_LABEL,
        ]

        # Add reviewers if we have owners
        if owners:
            pr_cmd.extend(["--reviewer", ",".join(owners[:MAX_ASSIGNEES])])

        result = subprocess.run(pr_cmd, capture_output=True, text=True, check=True)
        print(f"Created removal PR: {result.stdout.strip()}")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create removal PR for {name}: {e}", file=sys.stderr)
        if e.stderr:
            print(f"  stderr: {e.stderr}", file=sys.stderr)
        return False
    finally:
        # Always restore original branch
        if original_branch:
            subprocess.run(["git", "checkout", original_branch], capture_output=True)


def handle_stale_components(repo: str, token: str | None, dry_run: bool) -> None:
    """Handle stale components: issues for warnings, removal PRs for stale."""
    repo_path = REPO_ROOT
    results = scan_repo(repo_path)
    # Include both warning (270-360 days) and stale (>360 days) components
    fully_stale_components = results.get("stale", [])
    components_needing_attention = results.get("warning", []) + fully_stale_components

    if not components_needing_attention and not fully_stale_components:
        print("No components need attention.")
        return

    print(f"Found {len(components_needing_attention)} components needing attention, including {len(fully_stale_components)} fully stale components that should be flagged for removal\n")

    # Handle warning components: create removal warning Issues
    if components_needing_attention:
        print("=== Warning Components (creating issues) ===")
        issues_created, issues_skipped = 0, 0
        for component in components_needing_attention:
            if issue_exists(repo, component["name"], token):
                print(f"Skipping {component['name']}: issue already exists")
                issues_skipped += 1
                continue
            if create_issue(repo, component, repo_path, token, dry_run):
                issues_created += 1
        print(f"Issues: {issues_created} created, {issues_skipped} skipped\n")

    # Handle stale components: create stale component removal PRs
    if fully_stale_components:
        print("=== Stale Components (creating removal PRs) ===")
        prs_created, prs_skipped = 0, 0
        for component in fully_stale_components:
            if removal_pr_exists(repo, component["name"]):
                print(f"Skipping {component['name']}: removal PR already exists")
                prs_skipped += 1
                continue
            if create_removal_pr(repo, component, repo_path, dry_run):
                prs_created += 1
        print(f"Removal PRs: {prs_created} created, {prs_skipped} skipped")


def main():
    """Handle stale components: create issues for warnings, and removal PRs if stale."""
    parser = argparse.ArgumentParser(
        description="Handle stale components: create issues for warnings, and removal PRs if stale."
    )
    parser.add_argument("--repo", required=True, help="GitHub repo (e.g., owner/repo)")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Print without creating issues/PRs")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: No GitHub token provided. API requests will be subject to rate limiting.", file=sys.stderr)
        print("Use --token or set GITHUB_TOKEN environment variable for authenticated requests.", file=sys.stderr)

    handle_stale_components(args.repo, token, args.dry_run)


if __name__ == "__main__":
    main()
