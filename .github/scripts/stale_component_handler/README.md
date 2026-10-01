# Stale Component Handler

Handles components approaching or past their verification deadline.

## What it Does

1. Uses `scripts/check_component_freshness` to categorize components:
   - 🟡 **Warning (270-360 days)**: Creates GitHub issues to notify owners
   - 🔴 **Stale (>360 days)**: Creates PRs to remove the component

2. For **warning** components:
   - Creates issues with `stale-component` label
   - Assigns component owners (up to 10)
   - Includes instructions for verification

3. For **stale** components:
   - Creates a branch `remove-stale-{component-name}`
   - Removes the component directory
   - Regenerates the category README to update the index
   - Opens a PR with `stale-component-removal` label
   - Adds component owners as reviewers

## Usage

```bash
# Dry run (see what would be created)
uv run .github/scripts/stale_component_handler/stale_component_handler.py \
  --repo owner/repo --dry-run

# Create issues and PRs
GITHUB_TOKEN=ghp_xxx uv run .github/scripts/stale_component_handler/stale_component_handler.py \
  --repo owner/repo
```

## Requirements

- `gh` CLI (pre-installed on GitHub Actions runners)
- `GITHUB_TOKEN` with `issues: write`, `contents: write`, `pull-requests: write` permissions
