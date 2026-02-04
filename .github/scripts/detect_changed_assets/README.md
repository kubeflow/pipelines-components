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
.github/scripts/detect-changed-assets/detect.sh origin/HEAD HEAD true

# Arguments:
# 1. BASE_REF (default: origin/HEAD)
# 2. HEAD_REF (default: HEAD)
# 3. INCLUDE_THIRD_PARTY (default: true)
# 4. FILTER (default: empty - no filtering)

# Examples:
.github/scripts/detect-changed-assets/detect.sh origin/develop HEAD false
.github/scripts/detect-changed-assets/detect.sh origin/main HEAD true '\.py$'
.github/scripts/detect-changed-assets/detect.sh origin/main HEAD true '\.(py|yaml)$'
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
components/<category>/<subcategory>/<name>/
pipelines/<category>/<name>/
pipelines/<category>/<subcategory>/<name>/

# Examples:
# Changed file: components/training/my_trainer/component.py
# Output: components/training/my_trainer
#
# Changed file: components/training/sklearn_trainer/logistic_regression/component.py
# Output: components/training/sklearn_trainer/logistic_regression
```

## Outputs

When run in GitHub Actions, writes to `$GITHUB_OUTPUT`:

- `changed-components`: Space-separated list
- `changed-pipelines`: Space-separated list
- `changed-components-json`: JSON array (compact)
- `changed-pipelines-json`: JSON array (compact)
- `changed-components-count`: Integer
- `changed-pipelines-count`: Integer
- `has-changes`: Boolean (true if any changes)
- `has-changed-components`: Boolean (true if components changed)
- `has-changed-pipelines`: Boolean (true if pipelines changed)
- `all-changed-files`: Space-separated file list

Also writes to `$GITHUB_STEP_SUMMARY` for job summary markdown.

When run standalone, outputs are written to temp files and displayed in terminal.

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
