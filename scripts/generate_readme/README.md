# Generate README Module

A modular tool for automatically generating README documentation for Kubeflow Pipelines components and pipelines.

## Structure

```
generate_readme/
├── __init__.py           # Package initialization
├── __main__.py           # Entry point for module execution
├── cli.py                # Command-line interface and argument parsing
├── constants.py          # Shared constants and logger configuration
├── content_generator.py  # README content generation logic
├── writer.py             # Main README generator orchestration and writer
├── metadata_parser.py    # Metadata extraction from KFP components/pipelines
└── README.md.j2          # Jinja template for a standardized README.md file
```

## Usage

Run from the project root directory:

```bash
# Generate README for a component
python -m scripts.generate_readme --component components/some_category/my_component

# Generate README for a pipeline
python -m scripts.generate_readme --pipeline pipelines/some_category/my_pipeline

# With additional options
python -m scripts.generate_readme --component components/some_category/my_component --verbose --overwrite

# Or with uv
uv run python -m scripts.generate_readme --component components/some_category/my_component
```

## Features

- **Automatic metadata extraction**: Parses Python functions decorated with `@dsl.component` or `@dsl.pipeline`, and augments with metadata from `metadata.yaml`
- **Google-style docstring parsing**: Extracts parameter descriptions and return values
- **Custom content preservation**: Preserves user-added content after the `<!-- custom-content -->` marker
- **Type annotation support**: Handles complex type annotations including Optional, Union, and generics
- **Component-specific usage examples**: Includes/Updates an example usage for the given pipeline or component, if provided via `example_pipeline.py`

## Module Components

### metadata_parser.py

- `MetadataParser`: Extracts metadata from `@dsl.component` or `@dsl.pipeline` functions using AST parsing

### content_generator.py

- `ReadmeContentGenerator`: Generates formatted README sections from extracted metadata

### writer.py

- `ReadmeWriter`: Orchestrates the README generation and writing process

### cli.py

- `validate_component_directory()`: Validates component directory structure
- `validate_pipeline_directory()`: Validates pipeline directory structure
- `parse_arguments()`: Parses command-line arguments
- `main()`: Entry point for CLI execution

## Custom Content

Users can add custom sections to their READMEs that will be preserved across regenerations:

1. Add the marker `<!-- custom-content -->` at the desired location
2. Write custom content below the marker
3. The content will be preserved when regenerating the README

Example:

```markdown
## Metadata 🗂️
...

<!-- custom-content -->

## Additional Examples

Custom examples that won't be overwritten...
```

