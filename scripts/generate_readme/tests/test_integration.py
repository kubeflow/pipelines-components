"""Integration tests for README generator.

These tests run the actual README generator CLI on test fixtures and verify
that the generated READMEs match the committed golden files.
"""

import subprocess
from pathlib import Path

import pytest

# Test data directory at repository root
TEST_DATA_DIR = Path(__file__).parent.parent.parent.parent / "test_data"


# Test fixtures: list of (type, path) tuples
TEST_FIXTURES = [
    ("component", "components/basic/simple_component"),
    ("component", "components/basic/optional_params"),
    ("component", "components/advanced/multiline_overview"),
    ("pipeline", "pipelines/basic/simple_pipeline"),
    # Subcategory fixtures
    ("component", "components/grouped/ml_models/linear_model"),
    ("pipeline", "pipelines/grouped/etl_flows/daily_ingest"),
]


@pytest.mark.parametrize("asset_type,asset_path", TEST_FIXTURES)
def test_readme_generation_check_mode(asset_type, asset_path):
    """Test README check mode for a single component or pipeline.

    This test:
    1. Runs the README generator CLI in check mode (default, no --fix flag)
    2. Verifies exit code 0 (no diffs detected)

    If this test fails, it means either:
    - The generator output changed (intentional code change)
    - The golden README is out of date (run: uv run -m scripts.generate_readme --{type} {path} --fix)
    """
    target_dir = TEST_DATA_DIR / asset_path

    # Run the README generator in check mode (no --fix flag)
    result = subprocess.run(
        ["uv", "run", "-m", "scripts.generate_readme", f"--{asset_type}", str(target_dir)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent.parent,  # Repo root
    )

    assert result.returncode == 0, (
        f"README check failed for {asset_path}!\n"
        f"This means the generated README doesn't match the golden file.\n\n"
        f"Stderr:\n{result.stderr}\n\n"
        f"To update the golden file, run:\n"
        f"  uv run -m scripts.generate_readme --{asset_type} test_data/{asset_path} --fix\n"
        f"  git add test_data/{asset_path}/README.md"
    )


def test_category_index_check_mode():
    """Test category index check mode.

    This test verifies that category index READMEs are correctly generated
    and match the committed golden files using check mode.
    """
    # Run generator in check mode on one component in each category
    # Each should succeed (exit 0) if golden files are in sync
    test_cases = [
        ("component", TEST_DATA_DIR / "components/basic/simple_component"),
        ("component", TEST_DATA_DIR / "components/advanced/multiline_overview"),
        ("pipeline", TEST_DATA_DIR / "pipelines/basic/simple_pipeline"),
    ]

    for asset_type, target_dir in test_cases:
        result = subprocess.run(
            [
                "uv",
                "run",
                "-m",
                "scripts.generate_readme",
                f"--{asset_type}",
                str(target_dir),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent,
        )

        assert result.returncode == 0, (
            f"Category index check failed for {target_dir.name}!\n\n"
            f"Stderr:\n{result.stderr}\n\n"
            f"To update the golden file, run:\n"
            f"  uv run -m scripts.generate_readme --{asset_type} {target_dir} --fix\n"
            f"  git add {target_dir.parent}/README.md"
        )


# Subcategory fixtures
SUBCATEGORY_FIXTURES = [
    ("component", "components/grouped/ml_models/linear_model"),
    ("pipeline", "pipelines/grouped/etl_flows/daily_ingest"),
]


@pytest.mark.parametrize("asset_type,asset_path", SUBCATEGORY_FIXTURES)
def test_subcategory_readme_check_mode(asset_type, asset_path):
    """Test that subcategory-level README index is generated correctly.

    This test:
    1. Runs the README generator CLI in check mode on a subcategory asset
    2. Verifies exit code 0 (the asset README, subcategory index, and
       category index all match the committed golden files)

    If this test fails, it means either:
    - The generator output changed (intentional code change)
    - The golden READMEs are out of date (run: uv run -m scripts.generate_readme --{type} {path} --fix)
    """
    target_dir = TEST_DATA_DIR / asset_path

    result = subprocess.run(
        ["uv", "run", "-m", "scripts.generate_readme", f"--{asset_type}", str(target_dir)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent.parent,
    )

    assert result.returncode == 0, (
        f"Subcategory README check failed for {asset_path}!\n"
        f"This means one of the generated READMEs doesn't match the golden file.\n\n"
        f"Stderr:\n{result.stderr}\n\n"
        f"To update the golden files, run:\n"
        f"  uv run -m scripts.generate_readme --{asset_type} test_data/{asset_path} --fix\n"
        f"  git add test_data/{asset_path}/README.md\n"
        f"  git add test_data/{'/'.join(asset_path.split('/')[:3])}/README.md\n"
        f"  git add test_data/{'/'.join(asset_path.split('/')[:2])}/README.md"
    )


def test_subcategory_index_check_mode():
    """Test subcategory and category index check mode for subcategory layouts.

    This test verifies that both subcategory-level and category-level index
    READMEs are correctly generated when an asset lives in a subcategory,
    including the 'Subcategories' section in the category index.
    """
    test_cases = [
        ("component", TEST_DATA_DIR / "components/grouped/ml_models/linear_model"),
        ("pipeline", TEST_DATA_DIR / "pipelines/grouped/etl_flows/daily_ingest"),
    ]

    for asset_type, target_dir in test_cases:
        result = subprocess.run(
            [
                "uv",
                "run",
                "-m",
                "scripts.generate_readme",
                f"--{asset_type}",
                str(target_dir),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent,
        )

        # Determine subcategory and category dirs
        subcategory_dir = target_dir.parent
        category_dir = subcategory_dir.parent

        assert result.returncode == 0, (
            f"Subcategory/category index check failed for {target_dir.name}!\n\n"
            f"Stderr:\n{result.stderr}\n\n"
            f"To update the golden files, run:\n"
            f"  uv run -m scripts.generate_readme --{asset_type} {target_dir} --fix\n"
            f"  git add {subcategory_dir}/README.md\n"
            f"  git add {category_dir}/README.md"
        )

        # Verify golden files exist
        assert (subcategory_dir / "README.md").exists(), (
            f"Subcategory index README missing at {subcategory_dir}/README.md"
        )
        assert (category_dir / "README.md").exists(), f"Category index README missing at {category_dir}/README.md"


def test_subcategory_category_index_contains_subcategories_section():
    """Verify the category index for a subcategory layout includes a Subcategories section."""
    category_readme = TEST_DATA_DIR / "components/grouped/README.md"

    assert category_readme.exists(), f"Golden category README not found: {category_readme}"
    content = category_readme.read_text()

    assert "## Subcategories" in content, (
        "Category README for subcategory layout should contain a '## Subcategories' section"
    )
    assert "Ml Models" in content, "Category README should list the 'Ml Models' subcategory"


def test_subcategory_index_lists_assets():
    """Verify subcategory index READMEs list the assets they contain."""
    # Component subcategory
    comp_subcat_readme = TEST_DATA_DIR / "components/grouped/ml_models/README.md"
    assert comp_subcat_readme.exists()
    comp_content = comp_subcat_readme.read_text()
    assert "Linear Model" in comp_content, "Subcategory README should list the linear_model component"
    assert "./linear_model/README.md" in comp_content, "Subcategory README should link to the component README"

    # Pipeline subcategory
    pipe_subcat_readme = TEST_DATA_DIR / "pipelines/grouped/etl_flows/README.md"
    assert pipe_subcat_readme.exists()
    pipe_content = pipe_subcat_readme.read_text()
    assert "Daily Ingest" in pipe_content, "Subcategory README should list the daily_ingest pipeline"
    assert "./daily_ingest/README.md" in pipe_content, "Subcategory README should link to the pipeline README"
