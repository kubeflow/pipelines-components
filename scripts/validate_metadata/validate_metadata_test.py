import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest
import validate_metadata
from validate_metadata import ValidationError

INVALID_METADATA_DIR = "scripts/validate_metadata/test_data/metadata/invalid/"
VALID_METADATA_DIR = "scripts/validate_metadata/test_data/metadata/valid/"
INVALID_OWNERS_DIR = "scripts/validate_metadata/test_data/owners/invalid/"
VALID_OWNERS_DIR = "scripts/validate_metadata/test_data/owners/valid/"
TEST_DIRS = "scripts/validate_metadata/test_data/directories_metadata/"


@dataclass
class ValidateMetadataTestFile:
    """Test data container for metadata file validation tests.

    Attributes:
        file_name: Name of the test file.
        expected_exception: Expected exception type if test should fail.
        expected_exception_msg: Expected exception message if test should fail.
    """

    file_name: str
    expected_exception: Optional[type[Exception]]
    expected_exception_msg: Optional[str]


@dataclass
class ValidateMetadataTestDir:
    """Test data container for directory validation tests.

    Attributes:
        dir_name: Name of the test directory.
        expected_exception: Expected exception type if test should fail.
        expected_exception_msg: Expected exception message if test should fail.
    """

    dir_name: str
    expected_exception: Optional[type[Exception]]
    expected_exception_msg: Optional[str]


@pytest.mark.parametrize(
    "test_data",
    [
        ValidateMetadataTestFile(file_name="valid_metadata.yaml", expected_exception=None, expected_exception_msg=None),
        ValidateMetadataTestFile(file_name="excluding_tags.yaml", expected_exception=None, expected_exception_msg=None),
        ValidateMetadataTestFile(
            file_name="excluding_ext_dependencies.yaml", expected_exception=None, expected_exception_msg=None
        ),
        ValidateMetadataTestFile(file_name="excluding_ci.yaml", expected_exception=None, expected_exception_msg=None),
        ValidateMetadataTestFile(
            file_name="excluding_ci_dependency_probe.yaml", expected_exception=None, expected_exception_msg=None
        ),
        ValidateMetadataTestFile(
            file_name="excluding_links.yaml", expected_exception=None, expected_exception_msg=None
        ),
        ValidateMetadataTestFile(
            file_name="custom_links_category.yaml", expected_exception=None, expected_exception_msg=None
        ),
    ],
)
def test_validate_metadata_yaml_success(test_data):
    """Test that valid metadata.yaml files pass validation."""
    validate_metadata.validate_metadata_yaml(filepath=Path(VALID_METADATA_DIR + test_data.file_name))
    # Asserts that no exceptions have been raised.
    assert True


@pytest.mark.parametrize(
    "test_data",
    [
        ValidateMetadataTestFile(
            file_name="this_file_does_not_exist.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=re.escape(
                "scripts/validate_metadata/test_data/metadata/invalid/this_file_does_not_exist.yaml "
                "is not a valid filepath."
            ),
        ),
        ValidateMetadataTestFile(
            file_name="missing_verified_date.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/missing_verified_date\.yaml'.*"
                r"'lastVerified' is a required property"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_verified_date.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_verified_date\.yaml'.*"
                r"'2024-11-20T0' is not a 'date-time'"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="passed_verified_date.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/passed_verified_date\.yaml'.*"
                r"'2024-11-10T00:00:00Z' references a date older than one year \(which is considered not valid\)"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="missing_name.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/missing_name\.yaml'.*"
                r"'name' is a required property"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_name.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_name\.yaml'.*"
                r"2 is not of type 'string'"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="missing_stability.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/missing_stability\.yaml'.*"
                r"'stability' is a required property"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_stability.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_stability\.yaml'.*"
                r"'invalid-stability' is not one of \['experimental', 'alpha', 'beta', 'stable'\]"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="missing_dependencies.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/missing_dependencies\.yaml'.*"
                r"'dependencies' is a required property"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_dependencies_type.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_dependencies_type\.yaml'.*"
                r"'invalid-dependencies-type' is not of type 'object'"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_dependencies_category.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_dependencies_category\.yaml'.*"
                r"Additional properties are not allowed"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="missing_kfp_dependency.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/missing_kfp_dependency\.yaml'.*"
                r"does not contain items matching the given schema in "
                r"\['properties'\]\['dependencies'\]\['properties'\]\['kubeflow'\]\['contains'\]"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_dependency_semantic_versioning.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/"
                r"test_data/metadata/invalid/invalid_dependency_semantic_versioning\.yaml'.*"
                r"'3.6' does not match.* in "
                r"\['properties'\]\['dependencies'\]\['properties'\]\['external_services'\]\['items'\]\['properties'\]\['version'\]\['pattern'\]"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_tag_type.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_tag_type\.yaml'.*"
                r"'tags' is not of type 'array'"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_tag_array_type.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_tag_array_type\.yaml'.*"
                r"2 is not of type 'string' in \['properties'\]\['tags'\]\['items'\]\['type'\]"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_ci.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_ci\.yaml'.*"
                r"'invalid-ci-value' is not of type 'object'"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_ci_category.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_ci_category\.yaml'.*"
                r"Additional properties are not allowed.*in \['properties'\]\['ci'\]\['additionalProperties'\]"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_ci_dependency_probe.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_ci_dependency_probe\.yaml'.*"
                r"'invalid-probe-value' is not of type 'boolean'"
            ),
        ),
        ValidateMetadataTestFile(
            file_name="invalid_links.yaml",
            expected_exception=ValidationError,
            expected_exception_msg=(
                r"File 'scripts/validate_metadata/test_data/metadata/invalid/invalid_links\.yaml'.*"
                r"'https://invalid-link' is not of type 'object'"
            ),
        ),
    ],
)
def test_validate_metadata_yaml_failure(test_data):
    """Test that invalid metadata.yaml files raise appropriate validation errors."""
    with pytest.raises(test_data.expected_exception, match=test_data.expected_exception_msg):
        validate_metadata.validate_metadata_yaml(filepath=Path(INVALID_METADATA_DIR + test_data.file_name))


@pytest.mark.parametrize(
    "test_data",
    [
        ValidateMetadataTestFile(
            file_name="owners_single_approver.txt", expected_exception=None, expected_exception_msg=None
        ),
        ValidateMetadataTestFile(
            file_name="owners_multiple_approvers.txt", expected_exception=None, expected_exception_msg=None
        ),
        ValidateMetadataTestFile(
            file_name="owners_approvers_and_reviewer.txt", expected_exception=None, expected_exception_msg=None
        ),
    ],
)
def test_validate_owners_yaml_success(test_data):
    """Test that valid OWNERS files pass validation."""
    validate_metadata.validate_owners_file(filepath=Path(VALID_OWNERS_DIR + test_data.file_name))
    # Asserts that no exceptions have been raised.
    assert True


@pytest.mark.parametrize(
    "test_data",
    [
        ValidateMetadataTestFile(
            file_name="owners_empty.txt",
            expected_exception=ValidationError,
            expected_exception_msg=re.escape(
                "OWNERS file at scripts/validate_metadata/test_data/owners/invalid/owners_empty.txt "
                "requires 1+ approver under heading 'approvers:'."
            ),
        ),
        ValidateMetadataTestFile(
            file_name="owners_missing_approvers.txt",
            expected_exception=ValidationError,
            expected_exception_msg=re.escape(
                "OWNERS file at scripts/validate_metadata/test_data/owners/invalid/owners_missing_approvers.txt "
                "requires 1+ approver under heading 'approvers:'."
            ),
        ),
        ValidateMetadataTestFile(
            file_name="owners_typo_approvers.txt",
            expected_exception=ValidationError,
            expected_exception_msg=re.escape(
                "OWNERS file at scripts/validate_metadata/test_data/owners/invalid/owners_typo_approvers.txt "
                "requires 1+ approver under heading 'approvers:'."
            ),
        ),
    ],
)
def test_validate_owners_yaml_failure(test_data):
    """Test that invalid OWNERS files raise appropriate validation errors."""
    with pytest.raises(ValidationError, match=test_data.expected_exception_msg):
        validate_metadata.validate_owners_file(filepath=Path(INVALID_OWNERS_DIR + test_data.file_name))


@pytest.mark.parametrize(
    "test_data",
    [
        ValidateMetadataTestDir(
            dir_name="missing", expected_exception=argparse.ArgumentTypeError, expected_exception_msg=None
        ),
        ValidateMetadataTestDir(
            dir_name="dir_is_not_dir.txt", expected_exception=argparse.ArgumentTypeError, expected_exception_msg=None
        ),
    ],
)
def test_validate_dir_failure(test_data):
    """Test that non-existent or non-directory paths raise appropriate errors."""
    with pytest.raises(test_data.expected_exception, match=test_data.expected_exception_msg):
        validate_metadata.validate_dir(path=TEST_DIRS + test_data.dir_name)


@pytest.mark.parametrize(
    "test_data", [ValidateMetadataTestDir(dir_name="valid", expected_exception=None, expected_exception_msg=None)]
)
def test_validate_dir_success(test_data):
    """Test that valid directories pass validation."""
    files_present = validate_metadata.validate_dir(path=TEST_DIRS + test_data.dir_name)
    assert files_present == Path("scripts/validate_metadata/test_data/directories_metadata/valid")


class TestFindDirsToValidate:
    """Tests for find_dirs_to_validate function (subcategory handling)."""

    def test_direct_component_returns_self(self):
        """When dir has metadata.yaml, return itself."""
        result = validate_metadata.find_dirs_to_validate(Path(TEST_DIRS + "valid"))
        assert result == [Path(TEST_DIRS + "valid")]

    def test_subcategory_returns_child_dirs(self):
        """When dir is a subcategory, return child dirs with metadata.yaml."""
        result = validate_metadata.find_dirs_to_validate(Path(TEST_DIRS + "subcategory_valid"))
        assert len(result) == 1
        assert result[0].name == "comp_a"

    def test_missing_owners_file_no_children_returns_self(self):
        """Dir with only metadata.yaml (no children with metadata) is returned as-is for validation."""
        result = validate_metadata.find_dirs_to_validate(Path(TEST_DIRS + "missing_owners_file"))
        assert result == [Path(TEST_DIRS + "missing_owners_file")]

    def test_missing_metadata_file_no_children_raises(self):
        """Dir with only OWNERS and no metadata.yaml or children raises error."""
        with pytest.raises(argparse.ArgumentTypeError, match="does not contain a metadata.yaml"):
            validate_metadata.find_dirs_to_validate(Path(TEST_DIRS + "missing_metadata_file"))


class TestSubcategoryOwnersValidation:
    """Tests that subcategory-level OWNERS are validated in main()."""

    def test_subcategory_valid_owners_passes(self, monkeypatch):
        """A subcategory with valid OWNERS should not flag errors for the subcategory itself."""
        subcategory_dir = Path(TEST_DIRS + "subcategory_valid")
        monkeypatch.setattr("sys.argv", ["prog", "--dir", str(subcategory_dir)])

        # main() returns normally on success (no sys.exit call)
        validate_metadata.main()

    def test_subcategory_invalid_owners_fails(self, monkeypatch):
        """A subcategory with invalid OWNERS should cause a validation error."""
        subcategory_dir = Path(TEST_DIRS + "subcategory_invalid_owners")
        monkeypatch.setattr("sys.argv", ["prog", "--dir", str(subcategory_dir)])

        with pytest.raises(SystemExit) as exc_info:
            validate_metadata.main()
        assert exc_info.value.code == 1

    def test_subcategory_missing_owners_fails(self, monkeypatch):
        """A subcategory with no OWNERS file should cause a validation error."""
        subcategory_dir = Path(TEST_DIRS + "subcategory_missing_owners")
        monkeypatch.setattr("sys.argv", ["prog", "--dir", str(subcategory_dir)])

        with pytest.raises(SystemExit) as exc_info:
            validate_metadata.main()
        assert exc_info.value.code == 1
