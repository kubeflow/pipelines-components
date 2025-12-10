#!/bin/bash
# Validate README files for components and pipelines
# Usage: ./test-readme-check.sh [--ci] <component_dir|pipeline_dir> [<component_dir|pipeline_dir> ...]
#
# This script validates both:
# 1. Individual component/pipeline READMEs
# 2. Category index READMEs
#
# Options:
#   --ci    Run in CI mode (non-interactive, always restore original README on failure)

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
    echo "Usage: $0 [--ci] <component_dir|pipeline_dir> [<component_dir|pipeline_dir> ...]"
    echo ""
    echo "Options:"
    echo "  --ci    Run in CI mode (non-interactive)"
    echo ""
    echo "Examples:"
    echo "  $0 components/dev/hello_world"
    echo "  $0 pipelines/training/my_pipeline"
    echo "  $0 --ci components/dev/hello_world pipelines/dev/my_pipeline  # CI mode, multiple targets"
    exit 1
}

# Function to generate a README and category index for a single target directory
run_readme_generator() {
    local TARGET_DIR=$1
    
    # Determine if it's a component or pipeline
    local TYPE_FLAG
    if [[ "$TARGET_DIR" == components/* ]]; then
        TYPE_FLAG="--component"
    elif [[ "$TARGET_DIR" == pipelines/* ]]; then
        TYPE_FLAG="--pipeline"
    else
        print_error "Invalid directory: $TARGET_DIR. Must be in components/ or pipelines/"
        return 1
    fi

    # Generate README
    echo "Generating README and updating category index for $TARGET_DIR..."
    uv run python -m scripts.generate_readme $TYPE_FLAG "$TARGET_DIR" --overwrite
}

# Function to validate a single category index
# Note: Category indexes are already updated by the individual README generator in Step 2
# This function compares the regenerated index with the backup
validate_category_index() {
    local category_dir=$1
    local category_readme="$category_dir/README.md"
    
    echo "Checking category index for $category_dir..."
    
    compare_readme_with_backup "$category_readme"
    return $?
}

# Function to validate a single target directory's individual README
# Note: Backup and generation already happened in Steps 1 & 2
validate_individual_readme() {
    local TARGET_DIR=$1
    
    print_header "Validating individual README: $TARGET_DIR"
    
    # Compare and handle via common function
    echo "Comparing generated README with existing version..."
    compare_readme_with_backup "$TARGET_DIR/README.md" "$TARGET_DIR"
    local result=$?
    
    echo ""
    return $result
}

# Function to backup a category index before regeneration
backup_readme() {
    local readme_path=$1
    
    if [ -f "$readme_path" ]; then
        print_warning "Backing up existing README..."
        cp "$readme_path" "$readme_path.backup"
    else
        print_warning "No existing README found"
    fi
}

# Generic function to compare README with backup and handle restore/keep logic
# Parameters:
#   $1 - readme_path: Path to the README file
# Returns: 0 if valid/kept, 1 if invalid/restored
# Note: Always extracts content before custom-content marker for comparison
compare_readme_with_backup() {
    local readme_path=$1
    
    # Check if backup exists
    if [ ! -f "$readme_path.backup" ]; then
        if [ -f "$readme_path" ]; then
            print_warning "New README created: $readme_path"
            print_success "Review and commit the new README."
            return 0
        else
            print_warning "No README found at: $readme_path"
            return 0
        fi
    fi
    
    # Prepare files for comparison
    local temp_suffix="_${readme_path//\//_}"
    local old_file="/tmp/old_readme${temp_suffix}.txt"
    local new_file="/tmp/new_readme${temp_suffix}.txt"
    

    # Extract content before custom-content marker from both files
    awk '/<!-- custom-content -->/{exit} 1' "$readme_path.backup" > "$old_file"
    awk '/<!-- custom-content -->/{exit} 1' "$readme_path" > "$new_file"
    
    # Compare files
    if ! diff -u "$old_file" "$new_file" > /dev/null 2>&1; then
        print_error "README is out of sync: $readme_path"
        echo ""
        echo "Differences:"
        diff -u "$old_file" "$new_file" || true
        echo ""
        
        # In CI mode, restore and fail; otherwise ask user
        if [ "$CI_MODE" = true ]; then
            mv "$readme_path.backup" "$readme_path"
            print_warning "Restored original README (CI mode)"
            return 1
        else
            read -p "Keep the newly generated README? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                mv "$readme_path.backup" "$readme_path"
                print_warning "Restored original README"
                return 1
            else
                rm "$readme_path.backup"
                print_success "Kept new README. Don't forget to commit it!"
                return 0
            fi
        fi
    else
        print_success "README is up-to-date: $readme_path"
        # Restore backup (they're identical, and this preserves custom content for individual READMEs)
        mv "$readme_path.backup" "$readme_path"
        return 0
    fi
}

# Main function to validate all READMEs
validate_readmes() {
    # Store all target directories
    TARGET_DIRS=("$@")
    
    # Extract unique categories from the target directories (needed for backup before Step 1)
    declare -A category_map
    for target_dir in "${TARGET_DIRS[@]}"; do
        # Extract category directory (parent of component/pipeline dir)
        category_dir=$(dirname "$target_dir")
        
        # Skip if at root level (components/, pipelines/)
        if [[ "$category_dir" == "components" ]] || [[ "$category_dir" == "pipelines" ]]; then
            continue
        fi
        
        # Add to categories map (using associative array for automatic deduplication)
        category_map["$category_dir"]=1
    done
    
    # Convert to regular array
    categories=("${!category_map[@]}")
    
    # Step 1: Backup all target READMEs and category indexes
    print_header "Step 1: Backing up all target READMEs and category indexes"
    for target_dir in "${TARGET_DIRS[@]}"; do
        backup_readme "$target_dir/README.md"
    done
    for category in "${categories[@]}"; do
        backup_readme "$category/README.md"
    done
    
    # Step 2: Run the README generator for all targets
    print_header "Step 2: Running the README generator for all targets"
    for target_dir in "${TARGET_DIRS[@]}"; do
        run_readme_generator  "$target_dir"
    done
    
    # Step 3: Validate all individual READMEs
    print_header "Step 3: Validating Individual READMEs"
    individual_failed=()
    for target_dir in "${TARGET_DIRS[@]}"; do
        if ! validate_individual_readme "$target_dir"; then
            individual_failed+=("$target_dir")
        fi
    done
    
    # Step 4: Validate category indexes (compare with backups created before Step 1)    
    print_header "Step 4: Validating Category Index READMEs"
    category_failed=()
    for category_dir in "${categories[@]}"; do
        if ! validate_category_index "$category_dir"; then
            category_failed+=("$category_dir")
        fi
    done

    # Final report
    print_header "Validation Summary"

    all_failed=("${individual_failed[@]}" "${category_failed[@]}")

    if [ ${#all_failed[@]} -gt 0 ]; then
        print_error "Validation failed for ${#all_failed[@]} item(s)"
        echo ""
        
        if [ ${#individual_failed[@]} -gt 0 ]; then
            echo "Individual READMEs that failed:"
            for target in "${individual_failed[@]}"; do
                echo "  - $target/README.md"
            done
            echo ""
        fi
        
        if [ ${#category_failed[@]} -gt 0 ]; then
            echo "Category indexes that failed:"
            for category in "${category_failed[@]}"; do
                echo "  - $category/README.md"
            done
            echo ""
            echo "To fix category indexes, regenerate any component/pipeline README in that category:"
            echo "  uv run python -m scripts.generate_readme --component <dir> --overwrite"
            echo "  (or --pipeline <dir> for pipelines)"
            echo ""
        fi
        
        echo "=================================================="
        exit 1
    elif [ ${#TARGET_DIRS[@]} -eq 0 ]; then
        print_success "No targets to validate"
        exit 0
    else
        print_success "All README files are up-to-date! ✨"
        exit 0
    fi
}


# Parse --ci flag
CI_MODE=false
if [ "$1" == "--ci" ]; then
    CI_MODE=true
    shift
fi
# Check if target directory is provided
if [ $# -eq 0 ]; then
    usage
fi
validate_readmes "$@"

