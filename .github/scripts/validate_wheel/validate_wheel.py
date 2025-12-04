#!/usr/bin/env python3
"""
Validate wheel package contents for Kubeflow Pipelines components.

This script checks that built wheel files contain the expected structure,
metadata, and required files.
"""

import argparse
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple


def validate_dist_info(file_list: List[str]) -> Tuple[List[str], List[str]]:
    """Validate the presence of .dist-info directory."""
    messages = []
    errors = []
    
    dist_info_dirs = [f for f in file_list if '.dist-info/' in f]
    if not dist_info_dirs:
        errors.append("Error: No .dist-info directory found")
    else:
        messages.append(f"✓ Found .dist-info directory: {dist_info_dirs[0].split('/')[0]}")
    
    return messages, errors


def get_metadata_content(wheel: zipfile.ZipFile, dist_info_files: List[str]) -> Tuple[str, List[str]]:
    """Extract metadata content from wheel file."""
    errors = []
    
    metadata_files = [f for f in dist_info_files if f.endswith('/METADATA')]
    if not metadata_files:
        errors.append("Error: No METADATA file found")
        return "", errors
    
    metadata_content = wheel.read(metadata_files[0]).decode('utf-8')
    return metadata_content, errors


def validate_package_name(metadata_content: str) -> Tuple[List[str], List[str]]:
    """Validate the package name in metadata."""
    messages = []
    errors = []
    
    expected_name = "kfp-components"
    if f"Name: {expected_name}" in metadata_content:
        messages.append(f"✓ Package name verified: {expected_name}")
    else:
        errors.append(f"Error: Expected package name '{expected_name}' not found in metadata")
    
    return messages, errors


def validate_version(metadata_content: str) -> Tuple[List[str], List[str]]:
    """Validate and extract version from metadata."""
    messages = []
    errors = []
    
    for line in metadata_content.split('\n'):
        if line.startswith('Version:'):
            messages.append(f"✓ {line}")
            return messages, errors
    
    errors.append("Error: No version found in metadata")
    return messages, errors


def validate_python_requirement(metadata_content: str) -> Tuple[List[str], List[str]]:
    """Validate Python requirement in metadata."""
    messages = []
    errors = []
    
    if 'Requires-Python:' in metadata_content:
        messages.append("✓ Python requirement specified")
    else:
        errors.append("Error: No Python requirement found in metadata")
    
    return messages, errors


def validate_kfp_dependency(metadata_content: str) -> Tuple[List[str], List[str]]:
    """Validate KFP dependency in metadata."""
    messages = []
    errors = []
    
    if 'kfp' in metadata_content.lower():
        messages.append("✓ KFP dependency found")
    else:
        errors.append("Warning: KFP dependency not found in metadata")
    
    return messages, errors


def validate_required_directories(file_list: List[str]) -> Tuple[List[str], List[str]]:
    """Validate the presence of required directories (components/ and pipelines/)."""
    messages = []
    errors = []
    
    components_files = [f for f in file_list if 'components/' in f]
    pipelines_files = [f for f in file_list if 'pipelines/' in f]
    
    if components_files:
        messages.append(f"✓ Found components directory ({len(components_files)} files)")
    else:
        errors.append("Error: No components/ directory found")
    
    if pipelines_files:
        messages.append(f"✓ Found pipelines directory ({len(pipelines_files)} files)")
    else:
        errors.append("Error: No pipelines/ directory found")
    
    return messages, errors


def validate_init_files(file_list: List[str]) -> Tuple[List[str], List[str]]:
    """Validate the presence of __init__.py files and category structure."""
    messages = []
    errors = []
    
    init_files = [f for f in file_list if f.endswith('__init__.py')]
    if not init_files:
        errors.append("Error: No __init__.py files found")
        return messages, errors
    
    messages.append(f"✓ Found {len(init_files)} __init__.py files")
    
    # Check for category-level __init__.py files
    expected_categories = ['training', 'evaluation', 'data_processing', 'deployment']
    for category in expected_categories:
        component_init = f"kfp_components/components/{category}/__init__.py"
        pipeline_init = f"kfp_components/pipelines/{category}/__init__.py"
        
        found_component = any(component_init in f for f in init_files)
        found_pipeline = any(pipeline_init in f for f in init_files)
        
        if found_component or found_pipeline:
            messages.append(f"  ✓ Found {category} category init files")
    
    return messages, errors


def validate_python_modules(file_list: List[str]) -> Tuple[List[str], List[str]]:
    """Validate the presence of Python modules."""
    messages = []
    errors = []
    
    py_files = [f for f in file_list if f.endswith('.py') and not f.endswith('__init__.py')]
    if py_files:
        messages.append(f"✓ Found {len(py_files)} Python modules")
    
    return messages, errors


def get_wheel_info(wheel_path: Path, file_list: List[str]) -> List[str]:
    """Get general information about the wheel."""
    messages = []
    
    # Report wheel size
    wheel_size = wheel_path.stat().st_size
    messages.append(f"✓ Wheel size: {wheel_size / 1024 / 1024:.2f} MB")
    
    # Show sample of contents
    messages.append("\nSample contents (first 10 non-metadata files):")
    sample_files = [f for f in file_list if '.dist-info/' not in f][:10]
    for f in sample_files:
        messages.append(f"  - {f}")
    
    return messages


def validate_wheel(wheel_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate a wheel file's contents.
    
    Args:
        wheel_path: Path to the wheel file
    
    Returns:
        Tuple of (success, list of validation messages)
    """
    messages = []
    errors = []
    
    if not wheel_path.exists():
        return False, [f"Error: Wheel file not found: {wheel_path}"]
    
    messages.append(f"Validating package: {wheel_path.name}")
    
    try:
        with zipfile.ZipFile(wheel_path, 'r') as wheel:
            file_list = wheel.namelist()
            
            # Define all validators as a list of tuples (name, function)
            validators = [
                # Basic structure validations
                ('dist_info', lambda: validate_dist_info(file_list)),
                ('directories', lambda: validate_required_directories(file_list)),
                ('init_files', lambda: validate_init_files(file_list)),
                ('python_modules', lambda: validate_python_modules(file_list)),
            ]
            
            # Extract metadata for metadata-specific validations
            dist_info_files = [f for f in file_list if '.dist-info/' in f]
            if dist_info_files:
                metadata_content, metadata_errors = get_metadata_content(wheel, dist_info_files)
                errors.extend(metadata_errors)
                
                if metadata_content:
                    # Add metadata validators
                    validators.extend([
                        ('package_name', lambda: validate_package_name(metadata_content)),
                        ('version', lambda: validate_version(metadata_content)),
                        ('python_requirement', lambda: validate_python_requirement(metadata_content)),
                        ('kfp_dependency', lambda: validate_kfp_dependency(metadata_content)),
                    ])
            
            # Run all validators
            for name, validator in validators:
                val_messages, val_errors = validator()
                messages.extend(val_messages)
                errors.extend(val_errors)
            
            # Add general wheel information
            messages.extend(get_wheel_info(wheel_path, file_list))
    
    except zipfile.BadZipFile:
        return False, [f"Error: Invalid wheel file: {wheel_path}"]
    except Exception as e:
        return False, [f"Error: Failed to validate wheel: {e}"]
    
    success = len(errors) == 0
    
    all_messages = messages
    if errors:
        all_messages.append("\nValidation issues:")
        all_messages.extend(errors)
    else:
        all_messages.append("\nAll validations passed!")
    
    return success, all_messages


def main():
    parser = argparse.ArgumentParser(description="Validate Kubeflow Pipelines component wheel packages")
    parser.add_argument("wheel_path", help="Path to the wheel file to validate")
    args = parser.parse_args()
    
    wheel_path = Path(args.wheel_path)
    success, messages = validate_wheel(wheel_path)
    
    for message in messages:
        print(message)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()