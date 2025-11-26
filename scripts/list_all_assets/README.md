# List All Assets Script

Simple Python script that lists all components and pipelines in the repository.

## Usage

```bash
python3 .github/scripts/list_all_assets/list.py
```

## Output

When run by GitHub actions, this script writes the following variables to `$GITHUB_OUTPUT`:

- `all-components`: Space-separated list of components in `components/`
- `all-pipelines`: Space-separated list of pipelines in `pipelines/`
- `all-assets`: Space-separated list of both components and pipelines
