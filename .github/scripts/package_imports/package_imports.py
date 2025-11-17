#!/usr/bin/env python3
"""Test that installed packages can be imported successfully.

This script verifies that all expected modules from the kfp-components
package can be imported using the kfp_components namespace.
"""

import argparse
import importlib
import sys


def test_imports() -> bool:
    """Test package imports for the single catalog package."""
    success = True

    print("Testing package imports...")
    print(f"Python path: {sys.path}")

    # Test main modules
    try:
        import kfp_components  # type: ignore[import-not-found]  # noqa: F401
        from kfp_components import components, pipelines  # type: ignore[import-not-found]  # noqa: F401

        print("✓ Main modules imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import main modules: {e}")
        success = False
        return success

    # Test category imports
    categories = ["training", "evaluation", "data_processing", "deployment"]

    for category in categories:
        comp_module = f"kfp_components.components.{category}"
        pipe_module = f"kfp_components.pipelines.{category}"

        try:
            importlib.import_module(comp_module)
            print(f"✓ {comp_module} imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import {comp_module}: {e}")
            success = False

        try:
            importlib.import_module(pipe_module)
            print(f"✓ {pipe_module} imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import {pipe_module}: {e}")
            success = False

    if success:
        print("\nAll package imports successful!")
    else:
        print("\nSome package imports failed")

    return success


def main():
    """Main entry point for testing package imports."""
    argparse.ArgumentParser(description="Test package imports for Kubeflow Pipelines components").parse_args()
    success = test_imports()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
