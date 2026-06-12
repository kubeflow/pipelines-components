import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path
from typing import Any

import jsonschema
import jsonschema.exceptions
import yaml

OWNERS = "OWNERS"
METADATA = "metadata.yaml"


_jsonschema_format_checker = jsonschema.FormatChecker()

default_date_time_checker = _jsonschema_format_checker.checkers["date-time"][0]


@_jsonschema_format_checker.checks("date-time", raises=ValueError)
def check_date_time(instance: Any) -> bool:
    """Performs additional validation of instances marked with format: date-time.

    It is checked whether:
        - the instance is in valid RFC-3339 format
        - the instance references date no older than one year (exclusive)

    Args:
        instance: instance to validate
    Raises:
        ValidationError when validation fails
    Returns:
        A boolean stating whether validation succeeded or not.
    """
    if not default_date_time_checker(instance):
        return False

    now = datetime.now(tz=timezone.utc)
    if (now - datetime.fromisoformat(instance)).days >= 365:
        raise ValueError(f"'{instance}' references a date older than one year (which is considered not valid).")

    return True


def timestamp_as_is_constructor(loader, node):
    """A constructor is a function that converts a node of a YAML representation graph to a native Python object.

    Here we want to return a scalar representation of a node for timestamp-tagged nodes
    (instead of the default conversion to datetime.datetime Python object).

    Args:
        loader: YAML loader
        node: YAML representation graph node being processed
    """
    return loader.construct_scalar(node)


yaml.add_constructor("tag:yaml.org,2002:timestamp", timestamp_as_is_constructor, Loader=yaml.SafeLoader)


class ValidationError(Exception):
    """Custom exception for validation errors that should be displayed without traceback.

    This exception can take a custom message.
    """

    def __init__(self, message: str = "A validation error occurred."):
        """Initialize the ValidationError with a custom message.

        Args:
            message: The error message to display.
        """
        # Call the base class constructor with the message
        super().__init__(message)

        # Store the message in an attribute (optional, but good practice)
        self.message = message


def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Returns:
        argParse.Namespace: Parsed and validated arguments.
    """
    parser = argparse.ArgumentParser(
        description="Validate metadata schema for Kubeflow Pipelines pipelines/components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
  # For example, from project root:
  python -m scripts.validate_metadata --dir components/data_processing/sample_component
        """,
    )

    parser.add_argument(
        "--dir",
        type=validate_dir,
        required=True,
        help="Path to a component/pipeline directory or a subcategory containing multiple components/pipelines",
    )

    return parser.parse_args()


def validate_dir(path: str) -> Path:
    """Validate that the input path is a valid directory.

    Args:
        path: String representation of the path to the component, pipeline, or subcategory directory.

    Returns:
        Path: Validated Path object to the directory.

    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(path)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Directory '{path}' does not exist")

    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{path}' is not a directory")

    return path


def find_dirs_to_validate(input_dir: Path) -> list[Path]:
    """Find all directories that need validation (handles both components and subcategories).

    Args:
        input_dir: Path to a component/pipeline directory or a subcategory directory.

    Returns:
        List of Path objects to directories containing metadata.yaml files.

    Raises:
        argparse.ArgumentTypeError: If no valid directories are found.
    """
    # Check if this directory has metadata.yaml
    if (input_dir / METADATA).exists():
        return [input_dir]

    # This might be a subcategory - find subdirectories with metadata.yaml
    dirs_to_validate = []
    for subdir in input_dir.iterdir():
        if subdir.is_dir() and (subdir / METADATA).exists():
            dirs_to_validate.append(subdir)

    if not dirs_to_validate:
        raise argparse.ArgumentTypeError(
            f"'{input_dir}' does not contain a {METADATA} file and has no subdirectories with one. "
            f"If this is a subcategory, ensure it contains component directories."
        )

    return dirs_to_validate


def validate_owners_file(filepath: Path):
    """Validate that the OWNERS file contains at least one approver under the 'approvers' heading.

    Args:
        filepath: Path object representing the filepath to the OWNERS file.

    Raises:
        ValidationError: If filepath input is not a file, heading 'approvers:' is missing, or no approvers are listed.
    """
    if not filepath.is_file():
        raise ValidationError(f"{filepath} is not a valid filepath.")

    with open(filepath) as f:
        for line, next_line in pairwise(f):
            next_line = next_line.strip()
            if line.startswith("approvers:") and next_line.startswith("-") and len(next_line) > 2:
                logging.info(f"OWNERS file at {filepath} contains at least one approver under heading 'approvers:'.")
                return

    # If this line is reached, no approvers were found.
    raise ValidationError(f"OWNERS file at {filepath} requires 1+ approver under heading 'approvers:'.")


def validate_metadata_yaml(filepath: Path):
    """Validate that the input filepath represents a metadata.yaml file with a valid schema.

    Args:
        filepath: Path object representing the filepath to the metadata.yaml file.

    Raise:
        ValidationError: If 'lastVerified' empty, or validate_date_verified() or validate_required_fields() fails.
    """
    if not filepath.is_file():
        raise ValidationError(f"{filepath} is not a valid filepath.")
    with open(filepath) as f:
        metadata = yaml.safe_load(f)

    schema = json.loads((Path(__file__).parent / "metadata_schema.json").read_text())
    try:
        jsonschema.validate(metadata, schema, format_checker=_jsonschema_format_checker)
    except jsonschema.exceptions.ValidationError as e:
        extra_info = ""
        # failed fomat checker as per https://python-jsonschema.readthedocs.io/en/stable/errors/#jsonschema.exceptions.ValidationError.cause
        if e.cause:
            extra_info = e.cause
        schema_path = "".join([f"['{p}']" for p in e.schema_path])
        raise ValidationError(f"File '{filepath}' failed validation: {extra_info} {e.message} in {schema_path}")


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    input_dir = args.dir

    # Find all directories to validate (handles subcategories)
    try:
        dirs_to_validate = find_dirs_to_validate(input_dir)
    except argparse.ArgumentTypeError as e:
        logging.error("Error: %s", e)
        sys.exit(1)

    has_errors = False

    # If input_dir is a subcategory (no metadata.yaml), validate its OWNERS file
    if not (input_dir / METADATA).exists():
        subcategory_owners = input_dir / OWNERS
        if subcategory_owners.is_file():
            try:
                validate_owners_file(subcategory_owners)
            except ValidationError as e:
                logging.error("Validation Error: %s", e)
                has_errors = True
        else:
            logging.error(
                "Subcategory directory '%s' is missing a required %s file.",
                input_dir,
                OWNERS,
            )
            has_errors = True

    for dir_path in dirs_to_validate:
        print(f"Validating {dir_path}...")
        dir_has_errors = False

        # Validate OWNERS
        try:
            owners_file_path = dir_path / OWNERS
            validate_owners_file(owners_file_path)
        except ValidationError as e:
            logging.error("Validation Error: %s", e)
            dir_has_errors = True

        # Validate metadata.yaml
        try:
            metadata_file_path = dir_path / METADATA
            validate_metadata_yaml(metadata_file_path)
        except ValidationError as e:
            logging.error("Validation Error: %s", e)
            dir_has_errors = True

        if dir_has_errors:
            has_errors = True
        else:
            logging.info(f"Validation successful for {dir_path}.")
            print(f"Validation successful for {dir_path}.")

    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
