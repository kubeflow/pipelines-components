"""Command-line interface for the generate_readme package."""

import argparse
import logging
from pathlib import Path

from .constants import logger
from .writer import ReadmeWriter


def validate_component_directory(dir_path: str) -> Path:
    """Validate that the component directory exists and contains required files.
    
    Args:
        dir_path: String path to the component directory.
        
    Returns:
        Path: Validated Path object to the component directory.
        
    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(dir_path)
    
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Component directory '{dir_path}' does not exist")
    
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{dir_path}' is not a directory")
    
    component_file = path / 'component.py'
    if not component_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a component.py file")
    
    metadata_file = path / 'metadata.yaml'
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a metadata.yaml file")
    
    return path


def validate_pipeline_directory(dir_path: str) -> Path:
    """Validate that the pipeline directory exists and contains required files.
    
    Args:
        dir_path: String path to the pipeline directory.
        
    Returns:
        Path: Validated Path object to the pipeline directory.
        
    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(dir_path)
    
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Pipeline directory '{dir_path}' does not exist")
    
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{dir_path}' is not a directory")
    
    pipeline_file = path / 'pipeline.py'
    if not pipeline_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a pipeline.py file")
    
    metadata_file = path / 'metadata.yaml'
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a metadata.yaml file")
    
    return path


def parse_arguments():
    """Parse and validate command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed and validated arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate README.md documentation for Kubeflow Pipelines components and pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From project root:
  python -m scripts.generate_readme --component components/some_category/my_component
  python -m scripts.generate_readme --pipeline pipelines/some_category/my_pipeline
  python -m scripts.generate_readme --component components/some_category/my_component --output custom_readme.md
  python -m scripts.generate_readme --component components/some_category/my_component --verbose --overwrite
  
  # Or with uv:
  uv run python -m scripts.generate_readme --component components/some_category/my_component
        """
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--component',
        type=validate_component_directory,
        help='Path to the component directory (must contain component.py and metadata.yaml)'
    )
    
    group.add_argument(
        '--pipeline',
        type=validate_pipeline_directory,
        help='Path to the pipeline directory (must contain pipeline.py and metadata.yaml)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output path for the generated README.md (default: README.md in component/pipeline directory)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing README.md without prompting'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    # Parse arguments
    args = parse_arguments()
    
    # Create and run the README writer
    writer = ReadmeWriter(
        component_dir=args.component,
        pipeline_dir=args.pipeline,
        output_file=args.output,
        verbose=args.verbose,
        overwrite=args.overwrite
    )
    writer.generate()

