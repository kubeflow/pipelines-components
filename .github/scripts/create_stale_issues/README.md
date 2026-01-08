# Create Stale Issues

Create GitHub issues for stale components that need re-verification.

## What it Does

1. Uses `scripts/check_component_freshness` to find components needing attention:
   - 🟡 Stale: 270-360 days since last verification
   - 🔴 Flagged for Deletion: >360 days since last verification
2. Reads `OWNERS` file to get maintainers
3. Creates GitHub issues with:
   - Title: `Component X needs verification`
   - Label: `stale-component`
   - Assignees: component owners
   - Body: mentions owners, includes update instructions

## Usage

```bash
# Dry run (see what would be created)
uv run .github/scripts/create_stale_issues/create_stale_issues.py --repo owner/repo --dry-run

# Create issues
GITHUB_TOKEN=ghp_xxx uv run .github/scripts/create_stale_issues/create_stale_issues.py --repo owner/repo
```

