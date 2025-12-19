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
def test_readme_generation_check_mode(asset_type, asset_path):
    """Test README check mode for a single component or pipeline.

    This test:
    1. Runs the README generator CLI in check mode (default, no --fix flag)
    2. Verifies exit code 0 (no diffs detected)

    If this test fails, it means either:
    - The generator output changed (intentional code change)
    - The golden README is out of date (run: uv run python -m scripts.generate_readme --{type} {path} --fix)
    """
    target_dir = TEST_DATA_DIR / asset_path

    # Run the README generator in check mode (no --fix flag)
    result = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.generate_readme", f"--{asset_type}", str(target_dir)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent.parent,  # Repo root
    )

    assert result.returncode == 0, (
        f"README check failed for {asset_path}!\n"
        f"This means the generated README doesn't match the golden file.\n\n"
        f"Stderr:\n{result.stderr}\n\n"
        f"To update the golden file, run:\n"
        f"  uv run python -m scripts.generate_readme --{asset_type} test_data/{asset_path} --fix\n"
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
                "python",
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
            f"  uv run python -m scripts.generate_readme --{asset_type} {target_dir} --fix\n"
            f"  git add {target_dir.parent}/README.md"
        )
