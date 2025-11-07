#!/usr/bin/env python3
"""
Test that installed packages can be imported successfully.

This script verifies that all expected modules from the kfp-components
or kfp-components-third-party packages can be imported using the
kubeflow.pipelines.components namespace.
"""

import argparse
import sys
import importlib


def test_imports(package_type: str = "core") -> bool:
    """
    Test package imports based on package type.
    
    Args:
        package_type: Either "core" or "third-party"
    
    Returns:
        True if all imports succeed, False otherwise
    """
    success = True
    
    print(f"Testing {package_type} package imports...")
    print(f"Python path: {sys.path}")
    
    # Test main modules
    try:
        if package_type == "third-party":
            import kubeflow.pipelines.components.third_party as third_party
            from kubeflow.pipelines.components.third_party import components, pipelines
        else:
            import kubeflow.pipelines.components as kfp_components
            from kubeflow.pipelines.components import components, pipelines
        print("✓ Main modules imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import main modules: {e}")
        success = False
        return success
    
    # Test category imports
    categories = ['training', 'evaluation', 'data_processing', 'deployment']
    
    for category in categories:
        if package_type == "third-party":
            comp_module = f"kubeflow.pipelines.components.third_party.components.{category}"
            pipe_module = f"kubeflow.pipelines.components.third_party.pipelines.{category}"
        else:
            comp_module = f"kubeflow.pipelines.components.components.{category}"
            pipe_module = f"kubeflow.pipelines.components.pipelines.{category}"
            
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
        print(f"\nAll {package_type} package imports successful!")
    else:
        print(f"\nSome {package_type} package imports failed")
    
    return success


def main():
    parser = argparse.ArgumentParser(description="Test package imports for Kubeflow Pipelines components")
    parser.add_argument(
        "--type",
        choices=["core", "third-party"],
        default="core",
        help="Type of package being tested"
    )
    
    args = parser.parse_args()
    
    success = test_imports(args.type)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
