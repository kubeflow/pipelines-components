#!/bin/bash
# Validate README files for components and pipelines
# Usage: ./test-readme-check.sh <component_dir|pipeline_dir> [<component_dir|pipeline_dir> ...]
#
# This script validates both:
# 1. Individual component/pipeline READMEs
# 2. Category index READMEs
#
# The script runs the README generator in check mode (default) and verifies exit codes.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

usage() {
    echo "Usage: $0 <component_dir|pipeline_dir> [<component_dir|pipeline_dir> ...]"
    echo ""
    echo "Examples:"
    echo "  $0 components/dev/hello_world"
    echo "  $0 pipelines/training/my_pipeline"
    echo "  $0 components/dev/hello_world pipelines/dev/my_pipeline  # Multiple targets"
    exit 1
}

# Check if target directory is provided
if [ $# -eq 0 ]; then
    usage
fi

TARGET_DIRS=("$@")
HAS_ERRORS=0

echo "=================================================="
echo "Validating README files"
echo "=================================================="

# Run the README generator in check mode for each target
for target_dir in "${TARGET_DIRS[@]}"; do
    # Determine if it's a component or pipeline
    if [[ "$target_dir" == components/* ]]; then
        TYPE_FLAG="--component"
        ASSET_FILE="component.py"
    elif [[ "$target_dir" == pipelines/* ]]; then
        TYPE_FLAG="--pipeline"
        ASSET_FILE="pipeline.py"
    else
        print_error "Invalid directory: $target_dir. Must be in components/ or pipelines/"
        exit 2
    fi

    # Check if this is a direct component/pipeline or a subcategory
    if [[ -f "$target_dir/$ASSET_FILE" ]]; then
        # Direct component/pipeline
        echo "Checking $target_dir..."
        if ! uv run python -m scripts.generate_readme $TYPE_FLAG "$target_dir"; then
            HAS_ERRORS=1
        fi
    else
        # This might be a subcategory - find components/pipelines in subdirectories
        found_assets=0
        for subdir in "$target_dir"/*/; do
            if [[ -f "$subdir$ASSET_FILE" ]]; then
                found_assets=1
                echo "Checking $subdir..."
                if ! uv run python -m scripts.generate_readme $TYPE_FLAG "${subdir%/}"; then
                    HAS_ERRORS=1
                fi
            fi
        done
        if [[ $found_assets -eq 0 ]]; then
            print_error "'$target_dir' does not contain a $ASSET_FILE file and has no subdirectories with one"
            exit 1
        fi
    fi
done

echo ""

if [ $HAS_ERRORS -eq 1 ]; then
    print_error "README files are out of sync!"
    echo ""
    echo "Please run the README generator locally and commit the changes:"
    echo "  uv run python -m scripts.generate_readme --component <dir> --fix"
    echo "  (or --pipeline <dir> for pipelines)"
    exit 1
fi

print_success "All README files are up-to-date! ✨"
