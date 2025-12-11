# List All Assets Action

This GitHub action lists all components and pipelines in the repository.

## Outputs

The action provides the following outputs:

- `all-components`: Space-separated list of all component paths
- `all-pipelines`: Space-separated list of all pipeline paths
- `all-assets`: Space-separated list of all component and pipeline paths combined

## Usage

### Basic Usage

```yaml
- name: List all assets
  id: list-assets
  uses: ./.github/actions/list-all-assets

- name: Print components
  run: |
    echo "Components: ${{ steps.list-assets.outputs.all-components }}"
```

## Related Actions

- [detect-changed-assets](../detect-changed-assets/README.md): Detects which components and pipelines have changed between git references

