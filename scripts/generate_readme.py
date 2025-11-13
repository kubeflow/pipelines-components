#!/usr/bin/env python3
"""
Generate README.md documentation for Kubeflow Pipelines components.

This script introspects Python functions decorated with @dsl.component to extract
function metadata and generate comprehensive README documentation following the
standards outlined in KEP-913: Components Repository.

Usage:
    python scripts/generate_readme.py path/to/component.py
    python scripts/generate_readme.py --output custom_readme.md path/to/component.py
    python scripts/generate_readme.py --verbose --overwrite path/to/component.py
"""

import argparse
from pathlib import Path


def validate_component_file(file_path: str) -> Path:
    """Validate that the component file exists and is a valid Python file.
    
    Args:
        file_path: String path to the component file.
        
    Returns:
        Path: Validated Path object.
        
    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Component file '{file_path}' does not exist")
    
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"'{file_path}' is not a file")
    
    if path.suffix != '.py':
        raise argparse.ArgumentTypeError(f"'{file_path}' is not a Python file (must have .py extension)")
    
    return path


def parse_arguments():
    """Parse and validate command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed and validated arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate README.md documentation for Kubeflow Pipelines components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_readme.py components/my_component/component.py
  python scripts/generate_readme.py --output custom_readme.md components/my_component/component.py
  python scripts/generate_readme.py --verbose components/my_component/component.py
        """
    )
    
    parser.add_argument(
        'component_file',
        type=validate_component_file,
        help='Path to the Python file containing the @dsl.component decorated function'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output path for the generated README.md (default: README.md in component directory)'
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
    """Main entry point for the script."""
    args = parse_arguments()
    print(args.component_file)

if __name__ == "__main__":
    main()
