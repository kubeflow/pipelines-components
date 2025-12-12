#!/bin/bash
# Validate README files for components and pipelines
# Usage: ./test-readme-check.sh <component_dir|pipeline_dir> [<component_dir|pipeline_dir> ...]
#
# This script validates both:
# 1. Individual component/pipeline READMEs
# 2. Category index READMEs
#
# The script runs the README generator and asserts that no files were changed.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header() {
    echo "=================================================="
    echo "$1"
    echo "=================================================="
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

print_header "Running README Generator"

# Run the README generator for each target
for target_dir in "${TARGET_DIRS[@]}"; do
    # Determine if it's a component or pipeline
    if [[ "$target_dir" == components/* ]]; then
        TYPE_FLAG="--component"
    elif [[ "$target_dir" == pipelines/* ]]; then
        TYPE_FLAG="--pipeline"
    else
        print_error "Invalid directory: $target_dir. Must be in components/ or pipelines/"
        exit 1
    fi
    
    echo "Generating README for $target_dir..."
    uv run python -m scripts.generate_readme $TYPE_FLAG "$target_dir" --overwrite
done

print_header "Validating READMEs"

# Check if any files were modified or created
modified_files=$(git diff --name-only)
untracked_files=$(git ls-files --others --exclude-standard)

if [ -n "$modified_files" ] || [ -n "$untracked_files" ]; then
    print_error "README files are out of sync!"
    echo ""
    
    if [ -n "$modified_files" ]; then
        echo "Modified files:"
        echo "$modified_files"
        echo ""
        echo "Diff:"
        git diff
        echo ""
    fi
    
    if [ -n "$untracked_files" ]; then
        echo "New files created:"
        echo "$untracked_files"
        echo ""
    fi
    
    print_error "Please run the README generator locally and commit the changes:"
    echo "  uv run python -m scripts.generate_readme --component <dir> --overwrite"
    echo "  (or --pipeline <dir> for pipelines)"
    exit 1
fi

print_success "All README files are up-to-date! ✨"
