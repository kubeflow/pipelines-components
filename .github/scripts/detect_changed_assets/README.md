# Detect Changed Assets Script

Core detection logic for the `detect-changed-assets` composite action. Implemented in Python (`detect.py`).

The script compares two git refs (e.g. base branch vs. PR head), lists changed files, and maps them to **component** and **pipeline** directories under `components/` and `pipelines/`. It is used in CI to run tests or lint only for affected assets.

## Prerequisites

- **Git** – the script runs `git fetch`, `git merge-base`, and `git diff`
- **uv** – used to run the script (e.g. `uv run python ...`); install via [uv](https://docs.astral.sh/uv/)
- In CI, **checkout with full history** – use `actions/checkout` with `fetch-depth: 0` so the base ref is available for diffing

## Usage

### Via Composite Action (Normal Use)

```yaml
- uses: ./.github/actions/detect-changed-assets
```

### Standalone (Testing/Debugging)

The script is run with `uv run python`:

```bash
# Basic usage (defaults: base-ref=origin/HEAD, head-ref=HEAD)
uv run python .github/scripts/detect_changed_assets/detect.py

# All arguments:
uv run python .github/scripts/detect_changed_assets/detect.py --help

# Examples:
uv run python .github/scripts/detect_changed_assets/detect.py --base-ref origin/develop --head-ref HEAD
uv run python .github/scripts/detect_changed_assets/detect.py --base-ref origin/main --filter '\.py$'
uv run python .github/scripts/detect_changed_assets/detect.py --filter '\.(py|yaml)$'
uv run python .github/scripts/detect_changed_assets/detect.py --skip-deleted-files
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--base-ref` | `origin/HEAD` | Base git reference to compare against |
| `--head-ref` | `HEAD` | Head git reference to compare |
| `--filter` | _(empty)_ | Regex pattern to filter changed files before detecting assets |
| `--skip-deleted-files` | _off_ | Exclude deleted files from the diff (e.g. so removed files do not contribute to asset detection) |

## What It Does

1. Fetches base branch if needed (for remote refs like `origin/main`)
2. Finds merge base between base and head for an accurate diff
3. Lists changed files via `git diff` (optionally skipping deleted files with `--skip-deleted-files`)
4. Optionally filters files by regex (`--filter`)
5. Parses paths to identify component and pipeline directories (see [Detection patterns](#detection-patterns))
6. Keeps only assets that **still exist as directories at HEAD** (removed components/pipelines are not reported, so CI does not run tests for deleted assets)
7. Deduplicates (multiple changed files in the same asset → one entry)
8. Writes outputs to `$GITHUB_OUTPUT` and `$GITHUB_STEP_SUMMARY` when run in GitHub Actions
9. When run standalone (no `GITHUB_ACTIONS`), prints a human-readable summary to the terminal

**HEAD assumption in CI:** The script always uses the current working tree as the head side of the diff (it compares `base_ref` to `head_ref`, default `HEAD`, and uses `os.path.isdir()` in the workspace to filter existing assets).
The workspace must therefore be checked out at the commit you want as “head” (e.g. PR branch tip or push commit).
In this repo, every workflow that uses the detect-changed-assets action runs `actions/checkout@v6` with `fetch-depth: 0` before the action, with no ref changes in between, so the assumption holds.

**Exit code:** The script exits with `0` on success (including when no changes are found).

## Detection Patterns

Paths are matched as follows:

- `components/<category>/<name>/` → asset `components/<category>/<name>`
- `components/<category>/<subcategory>/<name>/` → asset `components/<category>/<subcategory>/<name>`
- `pipelines/<category>/<name>/` → asset `pipelines/<category>/<name>`
- `pipelines/<category>/<subcategory>/<name>/` → asset `pipelines/<category>/<subcategory>/<name>`

**Reserved subdirectories:** For a direct asset (three segments), the subdirectories `tests/` and `shared/` are treated as belonging to that asset, not as a subcategory. For example:

- `components/training/my_trainer/tests/test_unit.py` → `components/training/my_trainer`
- `components/training/my_trainer/shared/utils.py` → `components/training/my_trainer`

Only asset paths that **exist as directories at HEAD** are reported. If a whole component or pipeline was removed, its path is omitted so downstream jobs do not try to run tests for deleted assets.

## Outputs

When run in GitHub Actions, the script writes to `$GITHUB_OUTPUT`:

| Output | Description |
|--------|-------------|
| `changed-components` | Space-separated list of changed component paths |
| `changed-pipelines` | Space-separated list of changed pipeline paths |
| `changed-components-json` | JSON array of changed component paths |
| `changed-pipelines-json` | JSON array of changed pipeline paths |
| `changed-components-count` | Number of changed components |
| `changed-pipelines-count` | Number of changed pipelines |
| `has-changes` | `true` if any components or pipelines changed |
| `has-changed-components` | `true` if any components changed |
| `has-changed-pipelines` | `true` if any pipelines changed |
| `all-changed-files` | Space-separated list of all changed files (before filter) |
| `filtered-changed-files` | Space-separated list of changed files that matched `--filter` (or same as `all-changed-files` if no filter) |

It also appends a markdown summary to `$GITHUB_STEP_SUMMARY` when that env is set.

When run standalone (e.g. locally without `GITHUB_ACTIONS`), the same data is printed to the terminal (counts, lists of components/pipelines, and file lists).

## Testing

### Unit tests

```bash
# From repo root, run the detect script tests
uv run pytest .github/scripts/detect_changed_assets/tests/ -v
```

### Manual run with a test change

```bash
# Create a test change
git checkout -b test
echo "test" >> components/dev/demo/component.py
git add . && git commit -m "test"

# Run script (expect components/dev/demo in the changed-components output)
uv run python .github/scripts/detect_changed_assets/detect.py

# Cleanup
git checkout - && git branch -D test
```

## See also

- [Detect-changed-assets action README](../../actions/detect-changed-assets/README.md) – inputs, outputs, and usage in workflows
- Script and tests: `detect.py` and `tests/test_detect.py` in this directory
