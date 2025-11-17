import argparse
import os
import sys
from itertools import pairwise

import yaml
from datetime import datetime, timezone
from pathlib import Path
import logging

from semver import Version

# The following ordered fields are required in a metadata.yaml file.
REQUIRED_FIELDS = ["name", "tier", "stability", "dependencies", "lastVerified"]
# The following fields are optional in a metadata.yaml file.'
OPTIONAL_FIELDS = ["tags", "ci", "links"]
# 'Tier' must be 'core' or 'third-party'.
TIER_OPTIONS = ["core", "third_party"]
# 'Stability' must be 'alpha', 'beta', or 'stable'.
STABILITY_OPTIONS = ["alpha", "beta", "stable"]
# 'Dependencies' must contain 'kubeflow' and can contain 'external_services'.
DEPENDENCIES_FIELDS = ["kubeflow", "external_services"]
# A given dependency must contain 'name' and 'version' fields.
DEPENDENCY=["name", "version"]
# Comparison operators for dependency versions.
COMPARISON = {">=", "<=", "=="}

OWNERS="OWNERS"
METADATA="metadata.yaml"

class ValidationError(Exception):
    """Custom exception for validation errors that should be displayed
    without traceback and can take a custom message.
    """
    def __init__(self, message: str = "A validation error occurred."):
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
        """
    )

    parser.add_argument(
        '--dir',
        type=validate_dir,
        required=True,
        help='Path to the component or pipeline directory (must contain OWNERS and metadata.yaml files)'
    )

    return parser.parse_args()

def validate_dir(path: str) -> Path:
    """Validate that the input path is a valid directory and contains required files.

    Args:
        path: String representation of the path to the component or pipeline directory.

    Returns:
        Path: Validated Path object to the component or pipeline directory.

    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(path)
    print(os.getcwd())
    if not path.exists():
        raise argparse.ArgumentTypeError("Directory '{}' does not exist".format(path))

    if not path.is_dir():
        raise argparse.ArgumentTypeError("'{}' is not a directory".format(path))

    file_path = path / OWNERS
    if not file_path.exists():
        raise argparse.ArgumentTypeError("{} does not contain an {} file".format(path, OWNERS))

    metadata_file = path / METADATA
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError("'{}' does not contain a {} file".format(path, METADATA))

    return path

def validate_owners_file(filepath: Path):
    """Validate that the OWNERS file contains at least one approver under the 'approvers' heading.

    Args:
        filepath: Path object representing the filepath to the OWNERS file.

    Raises:
        ValidationError: If filepath input is not a file, heading 'approvers:' is missing, or no approvers are listed.
    """
    if not filepath.is_file():
        raise ValidationError("{} is not a valid filepath.".format(filepath))

    with open(filepath) as f:
        for line, next_line in pairwise(f):
            if line.startswith("approvers:") and next_line.startswith("-") and len(next_line) > 2:
                logging.info("OWNERS file at {} contains at least one approver under heading 'approvers:'.".format(filepath))
                return

    # If this line is reached, no approvers were found.
    raise ValidationError("OWNERS file at {} requires 1+ approver under heading 'approvers:'.".format(filepath))

def validate_metadata_yaml(filepath: Path) -> bool:
    """Validate that the input filepath represents a metadata.yaml file with a valid schema.

    Args:
        filepath: Path object representing the filepath to the metadata.yaml file.

    Raise:
        ValidationError: If 'lastVerified' empty, or validate_date_verified() or validate_required_fields() fails.
    """
    if not filepath.is_file():
        raise ValidationError("{} is not a valid filepath.".format(filepath))
    with open(filepath) as f:
        metadata = yaml.safe_load(f)

        # Validate metadata.yaml has been verified within one year of the current date.
        if "lastVerified" not in metadata:
            raise ValidationError("Metadata at {} has corresponding metadata.yaml with no 'lastVerified' value.".format(filepath))

        last_verified = metadata.get("lastVerified")
        if not validate_date_verified(last_verified):
            raise ValidationError("Metadata at {} has corresponding metadata.yaml with invalid 'lastVerified' value: {}.".format(filepath, last_verified))

        # Validate required fields and their corresponding values.
        validate_required_fields(metadata)

def validate_date_verified(last_verified: datetime) -> bool:
    """Validate that the input date is RFC-3339-formatted and within 1 year of the current date.

    Args:
        last_verified: Input datetime date to be validated.

    Returns:
        bool: True if the input date is valid, False otherwise.

    Examples:
        '2025-03-15T00:00:00Z'  -> True [As of November 2025]
        '2025-03-15'            -> False
        '2024-03-15T00:00:00Z'  -> False
    """
    # Validate input date formatting.
    if not isinstance(last_verified, datetime):
        logging.error("'lastVerified' should be format YYYY-MM-DDT00:00:00Z, but instead is: {}.".format(last_verified))
        return False
    # Validate input date to be within 1 year of the current date.
    today = datetime.now(timezone.utc)
    delta = abs((today - last_verified).days)
    if delta >= 365:
        logging.error("'lastVerified' should be within 1 year of current date, but is {} days over.".format(delta))
        return False
    return True

def validate_required_fields(metadata: dict):
    """Validates that all required fields are present in the input dictionary and have valid values,
    and that no invalid fields are present.

    Args:
        metadata: dictionary object containing nested metadata fields.

    Raises:
        ValidationError: If validation fails.
    """
    # Convert metadata keys to a list for comparison purposes.
    input_metadata_fields = list(metadata.keys())
    # Optional fields should not be validated against required fields. Remove optional fields for this check.
    for field in OPTIONAL_FIELDS:
        if field in input_metadata_fields:
            input_metadata_fields.remove(field)

    # Retrieve name name.
    name = metadata.get("name")
    if name is None:
        raise ValidationError("Missing required field 'name' in {}.".format(METADATA))
    if not isinstance(name, str):
        raise ValidationError("{} value identified in field 'name' in {}: '{}'. Value for 'name' must be string.".format(type(name).__name__, METADATA, name))

    # Convert metadata keys to a set and compare against REQUIRED_FIELDS set.
    input_fields_set = set(input_metadata_fields)
    required_fields_set = set(REQUIRED_FIELDS)
    if required_fields_set != input_fields_set:
        missing_fields = required_fields_set - input_fields_set
        if len(missing_fields) > 0:
            raise ValidationError("Missing required field(s) in {} for '{}': {}.".format(METADATA, name, missing_fields))
        extra_fields = input_fields_set - required_fields_set
        if len(extra_fields) > 0:
            raise ValidationError("Unexpected field(s) in {} for '{}': {}.".format(METADATA, name, extra_fields))
    # Compare input fields against REQUIRED FIELDS as lists to verify elements are ordered correctly.
    if list(input_metadata_fields) != REQUIRED_FIELDS:
        raise ValidationError("Field(s) located incorrectly in {} for '{}'. Expected order is {}.".format(METADATA, name, REQUIRED_FIELDS))

    # Validate field values.
    for field in metadata:
        value_type = type(metadata.get(field)).__name__

        if field == "tier":
            tier_val = metadata.get("tier")
            if tier_val not in TIER_OPTIONS:
                raise ValidationError("Invalid 'tier' value in {} for '{}': '{}'. Expected a scalar string from the following options: {}.".format(METADATA, name, tier_val, TIER_OPTIONS))

        elif field == "stability":
            stability_val = metadata.get("stability")
            if stability_val not in STABILITY_OPTIONS:
                raise ValidationError("Invalid 'stability' value in {} for '{}': '{}'. Expected one of: {}.".format(METADATA, name, stability_val, STABILITY_OPTIONS))

        elif field == "dependencies":
            # Dependencies should be a dictionary.
            dependency_val = metadata.get("dependencies")
            if not isinstance(dependency_val, dict):
                raise ValidationError("{} value identified for field 'dependencies' in {} for '{}'. Value must be array.".format(value_type, METADATA, name))
            dependency_types = set(dependency_val.keys())

            # Dependencies should contain 'kubeflow' and can contain 'external_services'.
            if not (dependency_types == {"kubeflow"} or dependency_types == {"kubeflow", "external_services"}):
                raise ValidationError("The following field(s) were found in dependencies: {}. Expected {}.".format(list(dependency_val.keys()), DEPENDENCIES_FIELDS))

            # Kubeflow Pipelines is a required dependency.
            kf_dependencies = dependency_val.get("kubeflow")
            ext_dependencies = dependency_val.get("external_services")
            if not isinstance(kf_dependencies, list) or (ext_dependencies is not None and not isinstance(ext_dependencies, list)):
                raise ValidationError("Dependency sub-types for '{}' should contain lists but instead are {} and {}.".format(name, type(kf_dependencies), type(ext_dependencies)))
            kfp_present = any(d.get('name') == 'Pipelines' for d in kf_dependencies)
            if not kfp_present:
                raise ValidationError("{} for '{}' is missing Kubeflow Pipelines dependency.".format(METADATA, name))

            # Dependency versions must be correctly formatted by semantic versioning.
            invalid_dependencies = get_invalid_versions(kf_dependencies) + get_invalid_versions(ext_dependencies)
            if len(invalid_dependencies) > 0:
                raise ValidationError("{} for '{}' contains one or more dependencies with invalid semantic versioning: {}.".format(METADATA, name, invalid_dependencies))

        elif field == "tags":
            tags_val = metadata.get("tags")
            if not (isinstance(tags_val, list)):
                raise ValidationError("{} value identified in field 'tags' in {} for '{}'. Value must be string array.".format(value_type, METADATA, name))
            if not all(isinstance(item, str) for item in tags_val):
                raise ValidationError("The following tags in {} for '{}': {}. Expected an array of scalar strings.".format(METADATA, name, tags_val))
        elif field == "ci":
            ci_val = metadata.get("ci")
            if not isinstance(ci_val, dict):
                raise ValidationError("{} value identified for field 'ci' in {} for '{}'. Value must be dictionary.".format(value_type, METADATA, name))
            keys = set(ci_val.keys())
            if not (keys == {"skip_dependency_probe"}):
                raise ValidationError("The following field(s) were found in field 'ci' in {} for '{}': {}. Only field 'skip_dependency_probe' is valid.".format(METADATA, name, list(ci_val.keys())))
            probe = ci_val.get("skip_dependency_probe")
            if probe is not None and not isinstance(probe, bool):
                raise ValidationError("{} expects a boolean value for skip_dependency_probe but {} value provided: '{}'.".format(METADATA, type(probe).__name__, probe))

        elif field == "links":
            links_value = metadata.get("links")
            if not isinstance(links_value, dict):
                raise ValidationError("{} value identified in field 'links' in {} for '{}'. Value must be dictionary.".format(value_type, METADATA, name))

def get_invalid_versions(dependencies: list[dict]) -> list[dict]:
    """Return a list of the input dependencies that contain invalid semantic versioning.

    Args:
        dependencies: list[dict] of dependencies to be validated

    Return:
        dependencies: list[dict] of invalid dependencies
    """
    if dependencies is None:
        return []
    invalid : list[dict] = []
    for dependency in dependencies:
        version = dependency.get("version")
        # If the dependency version is null or non-string, it is invalid.
        if version is None or not isinstance(version, str):
            invalid.append(dependency)
        # Strip leading '==', '>=' or '<=' from dependency version, if applicable.
        if len(version) > 1 and version[:2] in COMPARISON:
            version = version[2:]
        if not Version.is_valid(version):
            invalid.append(dependency)
    return invalid

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    input_dir = args.component

    # Validate OWNERS
    try:
        owners_file_path = input_dir / OWNERS
        validate_owners_file(owners_file_path)
    except ValidationError as e:
        logging.error("Validation Error: %s", e)
        sys.exit(1)

    # Validate metadata.yaml
    try:
        metadata_file_path = input_dir / METADATA
        validate_metadata_yaml(metadata_file_path)
    except ValidationError as e:
        logging.error("Validation Error: %s", e)
        sys.exit(1)

    # Validation successful.
    logging.info("Validation successful for {}.".format(input_dir))
    print("Validation successful for {}.".format(input_dir))

if __name__ == "__main__":
    main()
