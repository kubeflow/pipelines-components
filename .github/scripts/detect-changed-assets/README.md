# Detect Changed Assets Script

Core detection logic for the `detect-changed-assets` composite action.

## Usage

### Via Composite Action (Normal Use)

```yaml
- uses: ./.github/actions/detect-changed-assets
```

### Standalone (Testing/Debugging)

```bash
# Basic usage
.github/scripts/detect-changed-assets/detect.sh origin/main HEAD true

# Arguments:
# 1. BASE_REF (default: origin/main)
# 2. HEAD_REF (default: HEAD)
# 3. INCLUDE_THIRD_PARTY (default: true)

# Example: compare against develop
.github/scripts/detect-changed-assets/detect.sh origin/develop HEAD false
```

## What It Does

1. Fetches base branch if needed
2. Finds merge base for accurate diff
3. Lists all changed files via `git diff`
4. Parses paths with regex to find components/pipelines
5. Deduplicates results
6. Writes outputs to `$GITHUB_OUTPUT` and `$GITHUB_STEP_SUMMARY`
7. Displays results (when run standalone)

## Detection Patterns

```bash
# Matches these patterns:
components/<category>/<name>/
pipelines/<category>/<name>/
third_party/components/<category>/<name>/
third_party/pipelines/<category>/<name>/

# Example:
# Changed file: components/training/my_trainer/component.py
# Output: components/training/my_trainer
```

## Outputs

When run in GitHub Actions, writes to:
- `$GITHUB_OUTPUT`: Key-value pairs for action outputs
- `$GITHUB_STEP_SUMMARY`: Markdown summary for job

When run standalone, writes to temp files and displays in terminal.

## Testing

```bash
# Create test change
git checkout -b test
echo "test" >> components/dev/demo/component.py
git add . && git commit -m "test"

# Run script
.github/scripts/detect-changed-assets/detect.sh

# Should output: ✓ Component: components/dev/demo

# Cleanup
git checkout - && git branch -D test
```

See also: [Action README](../../actions/detect-changed-assets/README.md)
