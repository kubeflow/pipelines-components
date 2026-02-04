"""Unit tests for generate_skeleton.py"""

import os
import tempfile
from pathlib import Path

import pytest

from ..generate_skeleton import (
    build_skeleton_path,
    create_skeleton,
    create_tests_only,
    ensure_subcategory_exists,
    generate_core_files,
    generate_subcategory_files,
    generate_test_files,
    get_existing_categories,
    validate_category,
    validate_name,
    validate_subcategory,
)


class TestGenerateCoreFiles:
    """Test the generate_core_files function."""

    def test_generate_component_files(self):
        """Test generating core files for a component."""
        files = generate_core_files("component", "data_processing", "my_processor")

        # Check all expected files are generated
        expected_files = ["__init__.py", "component.py", "metadata.yaml", "OWNERS", "README.md"]
        assert set(files.keys()) == set(expected_files)

        # Check content contains expected elements
        assert "from .component import my_processor" in files["__init__.py"]
        assert "@dsl.component" in files["component.py"]
        assert "def my_processor(" in files["component.py"]
        assert "name: my_processor" in files["metadata.yaml"]

    def test_generate_pipeline_files(self):
        """Test generating core files for a pipeline."""
        files = generate_core_files("pipeline", "training", "my_pipeline")

        # Check all expected files are generated
        expected_files = ["__init__.py", "pipeline.py", "metadata.yaml", "OWNERS", "README.md"]
        assert set(files.keys()) == set(expected_files)

        # Check content contains expected elements
        assert "from .pipeline import my_pipeline" in files["__init__.py"]
        assert "@dsl.pipeline" in files["pipeline.py"]
        assert "def my_pipeline(" in files["pipeline.py"]
        assert "name: my_pipeline" in files["metadata.yaml"]


class TestGenerateTestFiles:
    """Test the generate_test_files function."""

    def test_generate_component_test_files(self):
        """Test generating test files for a component."""
        files = generate_test_files("component", "my_processor")

        # Check all expected files are generated
        expected_files = ["__init__.py", "test_component_unit.py", "test_component_local.py"]
        assert set(files.keys()) == set(expected_files)

        # Check content contains expected elements
        assert "from ..component import my_processor" in files["test_component_unit.py"]
        assert "class TestMyProcessorUnitTests:" in files["test_component_unit.py"]
        assert "def test_component_function_exists" in files["test_component_unit.py"]

    def test_generate_pipeline_test_files(self):
        """Test generating test files for a pipeline."""
        files = generate_test_files("pipeline", "my_pipeline")

        # Check all expected files are generated
        expected_files = ["__init__.py", "test_pipeline_unit.py", "test_pipeline_local.py"]
        assert set(files.keys()) == set(expected_files)

        # Check content contains expected elements
        assert "from ..pipeline import my_pipeline" in files["test_pipeline_unit.py"]
        assert "class TestMyPipelineUnitTests:" in files["test_pipeline_unit.py"]
        assert "def test_pipeline_function_exists" in files["test_pipeline_unit.py"]


class TestCreateSkeleton:
    """Test the create_skeleton function."""

    def test_create_component_skeleton_with_tests(self):
        """Test creating a component skeleton with tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            Path(temp_dir).mkdir(exist_ok=True)

            os.chdir(temp_dir)

            try:
                # Create skeleton
                result_dir = create_skeleton("component", "data_processing", "my_processor", create_tests=True)

                # Check directory structure
                assert result_dir.exists()
                assert (result_dir / "__init__.py").exists()
                assert (result_dir / "component.py").exists()
                assert (result_dir / "metadata.yaml").exists()
                assert (result_dir / "OWNERS").exists()

                # Check tests directory
                tests_dir = result_dir / "tests"
                assert tests_dir.exists()
                assert (tests_dir / "__init__.py").exists()
                assert (tests_dir / "test_component_unit.py").exists()
                assert (tests_dir / "test_component_local.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_create_pipeline_skeleton_without_tests(self):
        """Test creating a pipeline skeleton without tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            Path(temp_dir).mkdir(exist_ok=True)

            os.chdir(temp_dir)

            try:
                # Create skeleton
                result_dir = create_skeleton("pipeline", "training", "my_pipeline", create_tests=False)

                # Check directory structure
                assert result_dir.exists()
                assert (result_dir / "__init__.py").exists()
                assert (result_dir / "pipeline.py").exists()
                assert (result_dir / "metadata.yaml").exists()
                assert (result_dir / "OWNERS").exists()

                # Check no tests directory
                tests_dir = result_dir / "tests"
                assert not tests_dir.exists()

            finally:
                os.chdir(original_cwd)


class TestCreateTestsOnly:
    """Test the create_tests_only function."""

    def test_create_tests_for_existing_component(self):
        """Test creating tests for an existing component."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            Path(temp_dir).mkdir(exist_ok=True)

            os.chdir(temp_dir)

            try:
                # First create skeleton without tests
                create_skeleton("component", "data_processing", "my_processor", create_tests=False)

                # Now create tests
                tests_dir = create_tests_only("component", "data_processing", "my_processor")

                # Check tests were created
                assert tests_dir.exists()
                assert (tests_dir / "__init__.py").exists()
                assert (tests_dir / "test_component_unit.py").exists()
                assert (tests_dir / "test_component_local.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_create_tests_only_missing_directory(self):
        """Test error when trying to create tests for non-existent component."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            Path(temp_dir).mkdir(exist_ok=True)

            os.chdir(temp_dir)

            try:
                # Try to create tests for non-existent component
                with pytest.raises(ValueError) as exc_info:
                    create_tests_only("component", "data_processing", "nonexistent")

                assert "does not exist" in str(exc_info.value)

            finally:
                os.chdir(original_cwd)

    def test_create_tests_only_missing_main_file(self):
        """Test error when directory exists but main file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            Path(temp_dir).mkdir(exist_ok=True)

            os.chdir(temp_dir)

            try:
                # Create directory structure but not the main file
                skeleton_dir = Path("components/data_processing/my_processor")
                skeleton_dir.mkdir(parents=True)

                # Try to create tests
                with pytest.raises(ValueError) as exc_info:
                    create_tests_only("component", "data_processing", "my_processor")

                assert "missing main file" in str(exc_info.value)

            finally:
                os.chdir(original_cwd)


class TestValidationFunctions:
    """Test validation functions for names and categories."""

    def test_validate_name_valid_cases(self):
        """Test validate_name with valid names."""
        valid_names = ["my_component", "data_processor", "name_with_123", "a"]
        for name in valid_names:
            validate_name(name)  # Should not raise

    def test_validate_category_valid_cases(self):
        """Test validate_category with valid categories."""
        valid_categories = ["data_processing", "training", "ml_workflows", "category123"]
        for category in valid_categories:
            validate_category(category)  # Should not raise

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "",  # Empty
            "../malicious",  # Path traversal
            "path/traversal",  # Forward slash
            "windows\\path",  # Backslash
            "name.with.dots",  # Dots
            "123invalid",  # Starts with number
            "name-with-hyphens",  # Hyphens
            "name with spaces",  # Spaces
            "name@symbol",  # Special chars
            "def",  # Python keyword
            "class",  # Python keyword
            "MyComponent",  # Uppercase
            "CamelCase",  # Mixed case
            "name!",  # Invalid character
        ],
    )
    def test_validate_name_invalid_cases(self, invalid_name):
        """Test validate_name raises ValueError for invalid names."""
        with pytest.raises(ValueError):
            validate_name(invalid_name)

    @pytest.mark.parametrize(
        "invalid_category",
        [
            "",  # Empty
            "../malicious",  # Path traversal
            "path/traversal",  # Forward slash
            "windows\\path",  # Backslash
            "category.with.dots",  # Dots
            "DataProcessing",  # Uppercase
            "CamelCase",  # Mixed case
            "category!",  # Invalid character
            "category-with-hyphens",  # Hyphens
            "category with spaces",  # Spaces
        ],
    )
    def test_validate_category_invalid_cases(self, invalid_category):
        """Test validate_category raises ValueError for invalid categories."""
        with pytest.raises(ValueError):
            validate_category(invalid_category)

    def test_get_existing_categories_empty(self):
        """Test get_existing_categories with no existing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)
            try:
                assert get_existing_categories("component") == []
                assert get_existing_categories("pipeline") == []
            finally:
                os.chdir(original_cwd)

    def test_get_existing_categories_with_directories(self):
        """Test get_existing_categories with existing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)
            try:
                # Create test directories
                (Path("components") / "data_processing").mkdir(parents=True)
                (Path("components") / "training").mkdir(parents=True)
                (Path("components") / ".hidden").mkdir()  # Should be ignored

                categories = get_existing_categories("component")
                assert sorted(categories) == ["data_processing", "training"]
            finally:
                os.chdir(original_cwd)


class TestHelperFunctions:
    """Test helper functions and edge cases."""

    def test_snake_case_to_title_conversion(self):
        """Test that names are properly converted from snake_case to Title Case."""
        files = generate_core_files("component", "data_processing", "my_data_processor")

        # Check that function name remains snake_case
        assert "def my_data_processor(" in files["component.py"]

    def test_category_with_underscores(self):
        """Test handling categories with underscores."""
        files = generate_core_files("component", "data_processing", "my_processor")

        # Check that category underscores are converted to hyphens in tags
        assert "- data-processing" in files["metadata.yaml"]


class TestSubcategoryValidation:
    """Test subcategory validation functions."""

    def test_validate_subcategory_valid_cases(self):
        """Test validate_subcategory with valid subcategory names."""
        valid_subcategories = ["sklearn_trainer", "pytorch_models", "utils", "model_v2"]
        for subcategory in valid_subcategories:
            validate_subcategory(subcategory)  # Should not raise

    @pytest.mark.parametrize(
        "invalid_subcategory",
        [
            "",  # Empty
            "../malicious",  # Path traversal
            "path/traversal",  # Forward slash
            "windows\\path",  # Backslash
            "subcategory.with.dots",  # Dots
            "SklearnTrainer",  # Uppercase
            "CamelCase",  # Mixed case
            "subcategory!",  # Invalid character
            "subcategory-with-hyphens",  # Hyphens
            "subcategory with spaces",  # Spaces
            "tests",  # Reserved name
            "shared",  # Reserved name
        ],
    )
    def test_validate_subcategory_invalid_cases(self, invalid_subcategory):
        """Test validate_subcategory raises ValueError for invalid names."""
        with pytest.raises(ValueError):
            validate_subcategory(invalid_subcategory)


class TestBuildSkeletonPath:
    """Test the build_skeleton_path helper function."""

    def test_path_without_subcategory(self):
        """Test building path without subcategory."""
        path = build_skeleton_path("component", "training", "my_trainer")
        assert path == Path("components/training/my_trainer")

    def test_path_with_subcategory(self):
        """Test building path with subcategory."""
        path = build_skeleton_path("component", "training", "logistic_regression", "sklearn_trainer")
        assert path == Path("components/training/sklearn_trainer/logistic_regression")

    def test_pipeline_path_without_subcategory(self):
        """Test building pipeline path without subcategory."""
        path = build_skeleton_path("pipeline", "ml_workflows", "training_pipeline")
        assert path == Path("pipelines/ml_workflows/training_pipeline")

    def test_pipeline_path_with_subcategory(self):
        """Test building pipeline path with subcategory."""
        path = build_skeleton_path("pipeline", "training", "batch_training", "ml_workflows")
        assert path == Path("pipelines/training/ml_workflows/batch_training")


class TestGenerateSubcategoryFiles:
    """Test subcategory file generation."""

    def test_generates_required_files(self):
        """Test that OWNERS and README.md are generated for subcategory."""
        files = generate_subcategory_files("sklearn_trainer")

        assert "OWNERS" in files
        assert "README.md" in files

    def test_readme_contains_subcategory_name(self):
        """Test that README contains the subcategory name."""
        files = generate_subcategory_files("sklearn_trainer")

        assert "Sklearn Trainer" in files["README.md"]


class TestEnsureSubcategoryExists:
    """Test the ensure_subcategory_exists function."""

    def test_creates_new_subcategory(self):
        """Test creating a new subcategory directory with required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                # Create category directory first
                Path("components/training").mkdir(parents=True)

                # Ensure subcategory exists
                subcategory_dir = ensure_subcategory_exists("component", "training", "sklearn_trainer")

                # Check directory was created
                assert subcategory_dir.exists()
                assert (subcategory_dir / "OWNERS").exists()
                assert (subcategory_dir / "README.md").exists()
                assert (subcategory_dir / "__init__.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_creates_shared_package_when_requested(self):
        """Test creating shared package in subcategory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                Path("components/training").mkdir(parents=True)

                subcategory_dir = ensure_subcategory_exists(
                    "component", "training", "sklearn_trainer", create_shared=True
                )

                # Check shared directory was created
                shared_dir = subcategory_dir / "shared"
                assert shared_dir.exists()
                assert (shared_dir / "__init__.py").exists()
                assert (shared_dir / "sklearn_trainer_utils.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_does_not_overwrite_existing_files(self):
        """Test that existing subcategory files are not overwritten."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                # Create subcategory with custom OWNERS
                subcategory_dir = Path("components/training/sklearn_trainer")
                subcategory_dir.mkdir(parents=True)
                custom_owners = "approvers:\n  - custom_owner\n"
                (subcategory_dir / "OWNERS").write_text(custom_owners)

                # Call ensure_subcategory_exists
                ensure_subcategory_exists("component", "training", "sklearn_trainer")

                # Verify OWNERS was not overwritten
                assert (subcategory_dir / "OWNERS").read_text() == custom_owners

            finally:
                os.chdir(original_cwd)

    def test_creates_pipeline_subcategory(self):
        """Test creating a new pipeline subcategory directory with required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                Path("pipelines/training").mkdir(parents=True)

                subcategory_dir = ensure_subcategory_exists("pipeline", "training", "ml_workflows")

                assert subcategory_dir.exists()
                assert subcategory_dir == Path("pipelines/training/ml_workflows")
                assert (subcategory_dir / "OWNERS").exists()
                assert (subcategory_dir / "README.md").exists()
                assert (subcategory_dir / "__init__.py").exists()

            finally:
                os.chdir(original_cwd)


class TestCreateSkeletonWithSubcategory:
    """Test create_skeleton with subcategory support."""

    def test_create_component_with_subcategory(self):
        """Test creating a component within a subcategory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                # Create category directory
                Path("components/training").mkdir(parents=True)

                # Create skeleton with subcategory
                result_dir = create_skeleton(
                    "component", "training", "logistic_regression", subcategory="sklearn_trainer", create_tests=True
                )

                # Check component directory structure
                assert result_dir.exists()
                assert result_dir == Path("components/training/sklearn_trainer/logistic_regression")
                assert (result_dir / "component.py").exists()
                assert (result_dir / "metadata.yaml").exists()
                assert (result_dir / "OWNERS").exists()
                assert (result_dir / "tests").exists()

                # Check subcategory files were created
                subcategory_dir = Path("components/training/sklearn_trainer")
                assert (subcategory_dir / "OWNERS").exists()
                assert (subcategory_dir / "README.md").exists()
                assert (subcategory_dir / "__init__.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_create_component_with_subcategory_and_shared(self):
        """Test creating a component with subcategory and shared package."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                Path("components/training").mkdir(parents=True)

                create_skeleton(
                    "component",
                    "training",
                    "logistic_regression",
                    subcategory="sklearn_trainer",
                    create_tests=False,
                    create_shared=True,
                )

                # Check shared package was created
                shared_dir = Path("components/training/sklearn_trainer/shared")
                assert shared_dir.exists()
                assert (shared_dir / "__init__.py").exists()
                assert (shared_dir / "sklearn_trainer_utils.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_create_pipeline_with_subcategory(self):
        """Test creating a pipeline within a subcategory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                Path("pipelines/training").mkdir(parents=True)

                result_dir = create_skeleton(
                    "pipeline", "training", "batch_training", subcategory="ml_workflows", create_tests=True
                )

                # Check pipeline directory structure
                assert result_dir.exists()
                assert result_dir == Path("pipelines/training/ml_workflows/batch_training")
                assert (result_dir / "pipeline.py").exists()
                assert (result_dir / "metadata.yaml").exists()
                assert (result_dir / "OWNERS").exists()
                assert (result_dir / "tests").exists()

                # Check subcategory files were created
                subcategory_dir = Path("pipelines/training/ml_workflows")
                assert (subcategory_dir / "OWNERS").exists()
                assert (subcategory_dir / "README.md").exists()
                assert (subcategory_dir / "__init__.py").exists()

            finally:
                os.chdir(original_cwd)


class TestCreateTestsOnlyWithSubcategory:
    """Test create_tests_only with subcategory support."""

    def test_create_tests_for_subcategory_component(self):
        """Test creating tests for a component in a subcategory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                # First create skeleton without tests
                Path("components/training").mkdir(parents=True)
                create_skeleton(
                    "component", "training", "logistic_regression", subcategory="sklearn_trainer", create_tests=False
                )

                # Now create tests
                tests_dir = create_tests_only(
                    "component", "training", "logistic_regression", subcategory="sklearn_trainer"
                )

                # Check tests were created
                assert tests_dir.exists()
                assert (tests_dir / "__init__.py").exists()
                assert (tests_dir / "test_component_unit.py").exists()
                assert (tests_dir / "test_component_local.py").exists()

            finally:
                os.chdir(original_cwd)

    def test_create_tests_only_missing_subcategory_component(self):
        """Test error when trying to create tests for non-existent subcategory component."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                with pytest.raises(ValueError) as exc_info:
                    create_tests_only("component", "training", "nonexistent", subcategory="sklearn_trainer")

                assert "does not exist" in str(exc_info.value)
                assert "sklearn_trainer" in str(exc_info.value)

            finally:
                os.chdir(original_cwd)

    def test_create_tests_for_subcategory_pipeline(self):
        """Test creating tests for a pipeline in a subcategory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                # First create pipeline skeleton without tests
                Path("pipelines/training").mkdir(parents=True)
                create_skeleton(
                    "pipeline", "training", "batch_training", subcategory="ml_workflows", create_tests=False
                )

                # Now create tests
                tests_dir = create_tests_only("pipeline", "training", "batch_training", subcategory="ml_workflows")

                # Check tests were created
                assert tests_dir.exists()
                assert (tests_dir / "__init__.py").exists()
                assert (tests_dir / "test_pipeline_unit.py").exists()
                assert (tests_dir / "test_pipeline_local.py").exists()

            finally:
                os.chdir(original_cwd)
