#!/usr/bin/env python3
r"""Kubeflow Pipelines Component/Pipeline Skeleton Generator

This script creates skeleton component or pipeline structures based on the
CONTRIBUTING.md guide. It generates all required files with proper templates.

Usage:
    python scripts/generate_skeleton/generate_skeleton.py --type=component \\
        --category=data_processing --name=my_processor
    python scripts/generate_skeleton/generate_skeleton.py --type=component \\
        --category=training --subcategory=sklearn_trainer --name=logistic_regression
    python scripts/generate_skeleton/generate_skeleton.py --type=pipeline \\
        --category=ml_workflows --name=my_training_pipeline
    python scripts/generate_skeleton/generate_skeleton.py --type=pipeline \\
        --category=training --subcategory=ml_workflows --name=batch_training
"""

import argparse
import keyword
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import jinja2


def _get_template_env() -> jinja2.Environment:
    """Get Jinja2 environment with template loader."""
    template_dir = Path(__file__).parent / "templates"
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def validate_name(name: str) -> None:
    """Validate component/pipeline name for security and Python compatibility.

    Args:
        name: The name to validate

    Raises:
        ValueError: If name is invalid
    """
    if not name:
        raise ValueError("Name cannot be empty")

    # Check for directory traversal attempts
    if "/" in name or "\\" in name:
        raise ValueError("Name cannot contain path separators (/, \\)")

    if "." in name:
        raise ValueError("Name cannot contain dots (.)")

    # Check for Python identifier validity
    if not name.isidentifier():
        raise ValueError(f"Name '{name}' is not a valid Python identifier")

    # Check for Python keywords
    if keyword.iskeyword(name) or keyword.issoftkeyword(name):
        raise ValueError(f"Name '{name}' is a Python keyword and cannot be used")

    # Enforce snake_case (no uppercase letters)
    if name != name.lower():
        raise ValueError("Name must be lowercase (snake_case)")

    # Additional check for valid characters (letters, numbers, underscores only)
    if not name.replace("_", "").isalnum():
        raise ValueError("Name can only contain letters, numbers, and underscores")


def validate_category(category: str) -> None:
    """Validate category name for security.

    Args:
        category: The category to validate

    Raises:
        ValueError: If category is invalid
    """
    if not category:
        raise ValueError("Category cannot be empty")

    # Check for directory traversal attempts
    if "/" in category or "\\" in category:
        raise ValueError("Category cannot contain path separators (/, \\)")

    if "." in category:
        raise ValueError("Category cannot contain dots (.)")

    # Enforce snake_case (no uppercase letters, allow underscores)
    if category != category.lower():
        raise ValueError("Category must be lowercase (snake_case)")

    # Allow letters, numbers, and underscores
    if not category.replace("_", "").isalnum() or not category[0].isalpha():
        raise ValueError("Category can only contain letters, numbers, and underscores")


_RESERVED_SUBCATEGORY_NAMES = {"tests", "shared"}


def validate_subcategory(subcategory: str) -> None:
    """Validate subcategory name for security.

    Args:
        subcategory: The subcategory to validate

    Raises:
        ValueError: If subcategory is invalid
    """
    if not subcategory:
        raise ValueError("Subcategory cannot be empty")

    # Reject reserved subcategory names
    if subcategory in _RESERVED_SUBCATEGORY_NAMES:
        raise ValueError(
            f"Subcategory cannot be named '{subcategory}' "
            f"(reserved names: {', '.join(sorted(_RESERVED_SUBCATEGORY_NAMES))})"
        )

    # Check for directory traversal attempts
    if "/" in subcategory or "\\" in subcategory:
        raise ValueError("Subcategory cannot contain path separators (/, \\)")

    if "." in subcategory:
        raise ValueError("Subcategory cannot contain dots (.)")

    # Enforce snake_case (no uppercase letters, allow underscores)
    if subcategory != subcategory.lower():
        raise ValueError("Subcategory must be lowercase (snake_case)")

    # Allow letters, numbers, and underscores
    if not subcategory.replace("_", "").isalnum() or not subcategory[0].isalpha():
        raise ValueError("Subcategory can only contain letters, numbers, and underscores")


def get_existing_categories(skeleton_type: str) -> list[str]:
    """Get list of existing categories for the given skeleton type.

    Args:
        skeleton_type: Either 'component' or 'pipeline'

    Returns:
        List of existing category directory names
    """
    base_dir = Path(f"{skeleton_type}s")
    if not base_dir.exists():
        return []

    return [item.name for item in base_dir.iterdir() if item.is_dir() and not item.name.startswith((".", "_"))]


def build_skeleton_path(skeleton_type: str, category: str, name: str, subcategory: str | None = None) -> Path:
    """Build the path for a skeleton directory.

    Args:
        skeleton_type: Type of skeleton ('component' or 'pipeline')
        category: Category name
        name: Skeleton name
        subcategory: Optional subcategory name

    Returns:
        Path to the skeleton directory
    """
    if subcategory:
        return Path(f"{skeleton_type}s/{category}/{subcategory}/{name}")
    return Path(f"{skeleton_type}s/{category}/{name}")


def generate_subcategory_files(subcategory: str) -> dict[str, str]:
    """Generate files for a new subcategory (OWNERS and README.md).

    Args:
        subcategory: Subcategory name

    Returns:
        Dict of filename to content mappings
    """
    env = _get_template_env()

    files = {}

    # Generate OWNERS for subcategory
    template = env.get_template("OWNERS.j2")
    files["OWNERS"] = template.render()

    # Generate a simple README for subcategory
    readme_content = f"""# {subcategory.replace("_", " ").title()}

This subcategory contains related assets.

## Overview

TODO: Add description of what this subcategory contains.

## Assets

TODO: List components/pipelines in this subcategory.

## Shared Utilities

If this subcategory has a `shared/` directory, document the shared utilities here.
"""
    files["README.md"] = readme_content

    return files


def ensure_subcategory_exists(skeleton_type: str, category: str, subcategory: str, create_shared: bool = False) -> Path:
    """Ensure subcategory directory exists with required files.

    Creates the subcategory directory and its OWNERS/README files if they don't exist.

    Args:
        skeleton_type: Type of skeleton ('component' or 'pipeline')
        category: Category name
        subcategory: Subcategory name
        create_shared: Whether to create a shared/ package directory

    Returns:
        Path to the subcategory directory
    """
    subcategory_dir = Path(f"{skeleton_type}s/{category}/{subcategory}")

    subcategory_dir.mkdir(parents=True, exist_ok=True)

    # Create any missing subcategory-level files
    subcategory_files = generate_subcategory_files(subcategory)
    for filename, content in subcategory_files.items():
        file_path = subcategory_dir / filename
        if not file_path.exists():
            file_path.write_text(content)

    # Create __init__.py for the subcategory package
    init_path = subcategory_dir / "__init__.py"
    if not init_path.exists():
        init_path.write_text(f'"""Assets in the {subcategory} subcategory."""\n')

    # Optionally create shared/ package
    if create_shared:
        shared_dir = subcategory_dir / "shared"
        shared_dir.mkdir(exist_ok=True)
        shared_init = shared_dir / "__init__.py"
        if not shared_init.exists():
            shared_init.write_text(f'"""Shared utilities for the {subcategory} subcategory."""\n')
        # Create a placeholder utility file
        utils_file = shared_dir / f"{subcategory}_utils.py"
        if not utils_file.exists():
            utils_file.write_text(
                f'"""Shared utility functions for the {subcategory} subcategory."""\n'
                "\n"
                "\n"
                "# TODO: Add shared utility functions, classes, or constants here.\n"
            )

    return subcategory_dir


def generate_core_files(skeleton_type: str, category: str, name: str) -> dict[str, str]:
    """Generate core files for skeleton based on type.

    Args:
        skeleton_type: Type of skeleton ('component' or 'pipeline')
        category: Category name
        name: Skeleton name

    Returns:
        Dict of filename to content mappings
    """
    env = _get_template_env()
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Prepare template context
    context = {
        "skeleton_type": skeleton_type,
        "category": category,
        "name": name,
        "current_date": current_date,
        "module_name": "component" if skeleton_type == "component" else "pipeline",
        "tags": [category.replace("_", "-")] + (["pipeline"] if skeleton_type == "pipeline" else []),
    }

    files = {}

    # Generate __init__.py
    template = env.get_template("__init__.py.j2")
    files["__init__.py"] = template.render({**context, "is_test_package": False})

    # Generate main file (component.py or pipeline.py)
    template = env.get_template(f"{skeleton_type}.py.j2")
    files[f"{skeleton_type}.py"] = template.render(context)

    # Generate metadata.yaml
    template = env.get_template("metadata.yaml.j2")
    files["metadata.yaml"] = template.render(context)

    # Generate OWNERS
    template = env.get_template("OWNERS.j2")
    files["OWNERS"] = template.render(context)

    # Generate placeholder README.md
    title = name.replace("_", " ").title()
    files["README.md"] = f"""# {title}

## Overview

TODO: Add description of this {skeleton_type}.

## Usage

TODO: Add usage examples.
"""

    return files


def generate_test_files(skeleton_type: str, name: str) -> dict[str, str]:
    """Generate test files for skeleton based on type.

    Args:
        skeleton_type: Type of skeleton ('component' or 'pipeline')
        name: Skeleton name

    Returns:
        Dict of filename to content mappings
    """
    env = _get_template_env()

    # Prepare template context with minimal variables
    context = {
        "skeleton_type": skeleton_type,
        "name": name,
        "test_class_name": name.title().replace("_", ""),
    }

    files = {}

    # Generate __init__.py for tests
    template = env.get_template("__init__.py.j2")
    files["__init__.py"] = template.render({**context, "is_test_package": True})

    # Generate unit tests using consolidated template
    template = env.get_template("test_unit.py.j2")
    files[f"test_{skeleton_type}_unit.py"] = template.render(context)

    # Generate local runner tests using consolidated template
    template = env.get_template("test_local.py.j2")
    files[f"test_{skeleton_type}_local.py"] = template.render(context)

    return files


def create_skeleton(
    skeleton_type: str,
    category: str,
    name: str,
    subcategory: str | None = None,
    create_tests: bool = True,
    create_shared: bool = False,
):
    """Create skeleton files for a component or pipeline.

    Args:
        skeleton_type: Type of skeleton ('component' or 'pipeline')
        category: Category name (e.g., 'data_processing', 'training')
        name: Skeleton name (e.g., 'my_processor')
        subcategory: Optional subcategory name (e.g., 'sklearn_trainer')
        create_tests: Whether to create test files (default: True)
        create_shared: Whether to create shared/ package in subcategory (default: False)

    Returns:
        Path to created directory
    """
    # Ensure subcategory exists with required files if specified
    if subcategory:
        ensure_subcategory_exists(skeleton_type, category, subcategory, create_shared)

    # Create directory structure
    skeleton_dir = build_skeleton_path(skeleton_type, category, name, subcategory)
    skeleton_dir.mkdir(parents=True, exist_ok=True)

    tests_dir = skeleton_dir / "tests"
    if create_tests:
        tests_dir.mkdir(exist_ok=True)

    # Generate and write core files
    core_files = generate_core_files(skeleton_type, category, name)
    for filename, content in core_files.items():
        (skeleton_dir / filename).write_text(content)

    # Generate and write test files if requested
    if create_tests:
        test_files = generate_test_files(skeleton_type, name)
        for filename, content in test_files.items():
            (tests_dir / filename).write_text(content)

    return skeleton_dir


def create_tests_only(skeleton_type: str, category: str, name: str, subcategory: str | None = None):
    """Create test files for an existing skeleton.

    Args:
        skeleton_type: Type of skeleton ('component' or 'pipeline')
        category: Category name (e.g., 'data_processing', 'training')
        name: Skeleton name (e.g., 'my_processor')
        subcategory: Optional subcategory name (e.g., 'sklearn_trainer')

    Returns:
        Path to created tests directory

    Raises:
        ValueError: If the skeleton directory or required files don't exist
    """
    skeleton_dir = build_skeleton_path(skeleton_type, category, name, subcategory)
    main_file = skeleton_dir / f"{skeleton_type}.py"

    # Build the command hint with subcategory if provided
    subcategory_arg = f" --subcategory={subcategory}" if subcategory else ""
    make_subcategory_arg = f" SUBCATEGORY={subcategory}" if subcategory else ""

    # Check if skeleton directory exists
    if not skeleton_dir.exists():
        location = f"subcategory '{subcategory}' of category '{category}'" if subcategory else f"category '{category}'"
        script_cmd = (
            f"python scripts/generate_skeleton/generate_skeleton.py "
            f"--type={skeleton_type} --category={category}{subcategory_arg} --name={name}"
        )
        make_cmd = f"make {skeleton_type} CATEGORY={category}{make_subcategory_arg} NAME={name}"
        raise ValueError(
            f"""
Error: {skeleton_type.title()} '{name}' does not exist in {location}.

Expected directory: {skeleton_dir}

To create this {skeleton_type} first, run:
  {script_cmd}

Or use the Makefile:
  {make_cmd}
""".strip()
        )

    # Check if the main skeleton file exists
    if not main_file.exists():
        script_cmd = (
            f"python scripts/generate_skeleton/generate_skeleton.py "
            f"--type={skeleton_type} --category={category}{subcategory_arg} --name={name}"
        )
        make_cmd = f"make {skeleton_type} CATEGORY={category}{make_subcategory_arg} NAME={name}"
        raise ValueError(
            f"""
Error: {skeleton_type.title()} '{name}' directory exists but missing main file.

Expected file: {main_file}

The {skeleton_type} directory exists but appears incomplete. Please recreate it:
  {script_cmd}

Or use the Makefile:
  {make_cmd}
""".strip()
        )

    tests_dir = skeleton_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Generate and write test files
    test_files = generate_test_files(skeleton_type, name)
    for filename, content in test_files.items():
        (tests_dir / filename).write_text(content)

    return tests_dir


def main():
    """Main entry point for the script."""
    # Change to project root directory (script is in scripts/generate_skeleton/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    os.chdir(project_root)

    parser = argparse.ArgumentParser(
        description="Generate skeleton component or pipeline structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --type=component --category=data_processing --name=my_processor
  %(prog)s --type=pipeline --category=ml_workflows --name=training_pipeline
  %(prog)s --type=component --category=training --name=bert_trainer

With subcategory:
  %(prog)s --type=component --category=training --subcategory=sklearn_trainer --name=logistic_regression
  %(prog)s --type=component --category=training --subcategory=sklearn_trainer --name=random_forest --create-shared
  %(prog)s --type=pipeline --category=training --subcategory=ml_workflows --name=batch_training
        """,
    )

    parser.add_argument("--type", choices=["component", "pipeline"], required=True, help="Type of skeleton to generate")

    parser.add_argument(
        "--category",
        required=True,
        help="Category for the component/pipeline (e.g., 'data_processing', 'training', 'ml_workflows')",
    )

    parser.add_argument(
        "--subcategory",
        required=False,
        default=None,
        help="Optional subcategory within the category (e.g., 'sklearn_trainer')",
    )

    parser.add_argument(
        "--name", required=True, help="Name of the component/pipeline (use snake_case, e.g., 'my_processor')"
    )

    parser.add_argument("--no-tests", action="store_true", help="Create skeleton without test files")

    parser.add_argument(
        "--tests-only", action="store_true", help="Create only test files for an existing component/pipeline"
    )

    parser.add_argument(
        "--create-shared",
        action="store_true",
        help="Create a shared/ package in the subcategory for common utilities (only with --subcategory)",
    )

    args = parser.parse_args()

    # Validate input parameters using comprehensive validation
    try:
        validate_name(args.name)
        validate_category(args.category)
        if args.subcategory:
            validate_subcategory(args.subcategory)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Validate --create-shared requires --subcategory
    if args.create_shared and not args.subcategory:
        print("Error: --create-shared requires --subcategory to be specified")
        sys.exit(1)

    # Validate that category exists (for new skeletons) or provide helpful guidance
    if not args.tests_only:
        existing_categories = get_existing_categories(args.type)
        if existing_categories and args.category not in existing_categories:
            print(f"Error: Category '{args.category}' does not exist for {args.type}s.")
            print(f"Existing categories: {', '.join(existing_categories)}")
            print("\nTo create the category directory, you can:")
            print(f"  mkdir -p {args.type}s/{args.category}")
            print(f"\nOr choose from existing categories: {', '.join(existing_categories)}")
            sys.exit(1)

    # Validate conflicting options
    if args.no_tests and args.tests_only:
        print("Error: --no-tests and --tests-only cannot be used together")
        sys.exit(1)

    # Build command hints for output messages
    make_subcategory_arg = f" SUBCATEGORY={args.subcategory}" if args.subcategory else ""

    try:
        if args.tests_only:
            # Create tests for existing skeleton
            created_dir = create_tests_only(args.type, args.category, args.name, args.subcategory)
            print(f"✅ Test files created successfully at: {created_dir}")
            print(f"""
Next steps:
1. Implement test logic in {created_dir}/
2. Run tests: pytest {created_dir}/ -v
            """)
        else:
            # Check if directory already exists for new skeleton
            target_dir = build_skeleton_path(args.type, args.category, args.name, args.subcategory)
            if target_dir.exists():
                print(f"Error: Directory '{target_dir}' already exists.")
                sys.exit(1)

            # Create new skeleton
            create_tests = not args.no_tests
            created_dir = create_skeleton(
                args.type, args.category, args.name, args.subcategory, create_tests, args.create_shared
            )
            print(f"✅ {args.type.title()} skeleton created successfully at: {created_dir}")

            next_steps = f"""
Next steps:
1. Update {created_dir}/OWNERS with your GitHub username
2. Implement the logic in {created_dir}/{args.type}.py
3. Update {created_dir}/metadata.yaml with correct dependencies and tags"""

            if args.subcategory:
                subcategory_dir = Path(f"{args.type}s/{args.category}/{args.subcategory}")
                next_steps += f"""
4. Update {subcategory_dir}/OWNERS with subcategory owners
5. Update {subcategory_dir}/README.md with subcategory documentation"""
                step_offset = 6
            else:
                step_offset = 4

            if create_tests:
                readme_cmd = (
                    f"make readme TYPE={args.type} CATEGORY={args.category}{make_subcategory_arg} NAME={args.name}"
                )
                next_steps += f"""
{step_offset}. Write comprehensive tests in {created_dir}/tests/
{step_offset + 1}. Update {created_dir}/README.md with actual documentation or run: {readme_cmd}
{step_offset + 2}. Run tests: pytest {created_dir}/tests/ -v"""
            else:
                readme_cmd = (
                    f"make readme TYPE={args.type} CATEGORY={args.category}{make_subcategory_arg} NAME={args.name}"
                )
                tests_cmd = (
                    f"make tests TYPE={args.type} CATEGORY={args.category}{make_subcategory_arg} NAME={args.name}"
                )
                next_steps += f"""
{step_offset}. Update {created_dir}/README.md with actual documentation or run: {readme_cmd}
{step_offset + 1}. Add tests later with: {tests_cmd}"""

            print(next_steps)

    except Exception as e:
        print(f"Error creating skeleton: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
