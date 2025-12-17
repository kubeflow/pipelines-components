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
]


@pytest.mark.parametrize("asset_type,asset_path", TEST_FIXTURES)
def test_readme_generation(asset_type, asset_path):
    """Test README generation for a single component or pipeline.

    This test:
    1. Runs the README generator CLI on a test fixture
    2. Checks that no files were modified (golden files already match)

    If this test fails, it means either:
    - The generator output changed (intentional code change)
    - The golden README is out of date (run: uv run python -m scripts.generate_readme --{type} {path} --overwrite)
    """
    target_dir = TEST_DATA_DIR / asset_path

    # Run the README generator
    result = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.generate_readme", f"--{asset_type}", str(target_dir), "--overwrite"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent.parent,  # Repo root
    )

    assert result.returncode == 0, f"Generator failed:\n{result.stderr}"

    # Check that no files were modified (git diff)
    diff_result = subprocess.run(
        ["git", "diff", "--exit-code", str(target_dir)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent.parent,
    )

    assert diff_result.returncode == 0, (
        f"README was modified for {asset_path}!\n"
        f"This means the generated README doesn't match the golden file.\n\n"
        f"Diff:\n{diff_result.stdout}\n\n"
        f"To update the golden file, run:\n"
        f"  uv run python -m scripts.generate_readme --{asset_type} test_data/{asset_path} --overwrite\n"
        f"  git add test_data/{asset_path}/README.md"
    )


def test_category_index_generation():
    """Test category index generation.

    This test verifies that category index READMEs are correctly generated
    and match the committed golden files.
    """
    # Category indexes to check
    category_indexes = [
        TEST_DATA_DIR / "components/basic/README.md",
        TEST_DATA_DIR / "components/advanced/README.md",
        TEST_DATA_DIR / "pipelines/basic/README.md",
    ]

    # Run generator on one component in each category to trigger index update
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.generate_readme",
            "--component",
            str(TEST_DATA_DIR / "components/basic/simple_component"),
            "--overwrite",
        ],
        capture_output=True,
        cwd=Path(__file__).parent.parent.parent.parent,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.generate_readme",
            "--component",
            str(TEST_DATA_DIR / "components/advanced/multiline_overview"),
            "--overwrite",
        ],
        capture_output=True,
        cwd=Path(__file__).parent.parent.parent.parent,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.generate_readme",
            "--pipeline",
            str(TEST_DATA_DIR / "pipelines/basic/simple_pipeline"),
            "--overwrite",
        ],
        capture_output=True,
        cwd=Path(__file__).parent.parent.parent.parent,
    )

    # Check that category indexes weren't modified
    for category_index in category_indexes:
        diff_result = subprocess.run(
            ["git", "diff", "--exit-code", str(category_index)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent,
        )

        assert diff_result.returncode == 0, (
            f"Category index was modified: {category_index.relative_to(TEST_DATA_DIR)}!\n\n"
            f"Diff:\n{diff_result.stdout}\n\n"
            f"To update the golden file, regenerate and commit it."
        )
