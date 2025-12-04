# Detect Changed Components and Pipelines

Custom GitHub Action to detect changed components and pipelines without third-party dependencies.

## Quick Start

```yaml
name: Test Changed Components
on: pull_request

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required!
      
      - name: Detect changes
        id: changes
        uses: ./.github/actions/detect-changed-assets
      
      - name: Test components
        if: steps.changes.outputs.has-changes == 'true'
        run: |
          for component in ${{ steps.changes.outputs.changed-components }}; do
            pytest $component/tests/
          done
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `base-ref` | Base git reference to compare against | `origin/main` |
| `head-ref` | Head git reference | `HEAD` |
| `include-third-party` | Include third_party/ directory | `true` |

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `has-changes` | Boolean - any changes? | `"true"` |
| `has-changed-components` | Boolean - components changed? | `"true"` |
| `has-changed-pipelines` | Boolean - pipelines changed? | `"false"` |
| `changed-components` | Space-separated list | `"components/training/trainer"` |
| `changed-components-json` | JSON array for matrix | `["components/training/trainer"]` |
| `changed-components-count` | Count | `"1"` |
| `changed-pipelines` | Space-separated list | `"pipelines/training/pipeline"` |
| `changed-pipelines-json` | JSON array for matrix | `["pipelines/training/pipeline"]` |
| `changed-pipelines-count` | Count | `"1"` |

## Common Patterns

### Matrix Strategy (Parallel Testing)

```yaml
jobs:
  detect:
    outputs:
      components: ${{ steps.changes.outputs.changed-components-json }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: changes
        uses: ./.github/actions/detect-changed-assets
  
  test:
    needs: detect
    strategy:
      matrix:
        component: ${{ fromJson(needs.detect.outputs.components) }}
    steps:
      - run: pytest ${{ matrix.component }}/tests/
```

### Conditional Execution

```yaml
- id: changes
  uses: ./.github/actions/detect-changed-assets

- name: Run if any changes
  if: steps.changes.outputs.has-changes == 'true'
  run: ./run-all-tests.sh

- name: Component-specific task
  if: steps.changes.outputs.has-changed-components == 'true'
  run: ./validate-components.sh

- name: Pipeline-specific task
  if: steps.changes.outputs.has-changed-pipelines == 'true'
  run: ./validate-pipelines.sh
```

### Process Each Asset

```yaml
- id: changes
  uses: ./.github/actions/detect-changed-assets

- run: |
    for component in ${{ steps.changes.outputs.changed-components }}; do
      echo "Processing $component"
      pytest $component/tests/
    done
```

## Testing Locally

```bash
# Test the detection script directly
.github/scripts/detect-changed-assets/detect.sh origin/main HEAD true

# Or run the full test suite
.github/actions/detect-changed-assets/test.sh
```

## How It Works

1. Fetches base branch if needed
2. Finds merge base between base and head refs
3. Gets changed files via `git diff`
4. Parses paths to identify components/pipelines:
   - `components/<category>/<name>/` → `components/<category>/<name>`
   - `pipelines/<category>/<name>/` → `pipelines/<category>/<name>`
   - Same for `third_party/` if enabled
5. Deduplicates (multiple files in same component = one entry)
6. Outputs in multiple formats
