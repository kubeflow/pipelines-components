#!/bin/bash
# Extract unique component and pipeline directories from a list of changed files
# Usage: ./find-changed-components-and-pipelines.sh <file1> <file2> ...
# Output: Space-separated list of directories
# Note: If the generator script is changed, returns all components and pipelines

set -e

components=()
pipelines=()
generator_changed=false

# Helper function to find all component directories
# Scans both components/ and third_party/components/
find_all_components() {
    for base_dir in "components" "third_party/components"; do
        if [ -d "$base_dir" ]; then
            for category_dir in "$base_dir"/*/; do
                if [ -d "$category_dir" ]; then
                    for comp_dir in "$category_dir"*/; do
                        if [ -d "$comp_dir" ] && [ -f "${comp_dir}component.py" ]; then
                            comp_path="${comp_dir%/}"
                            components+=("$comp_path")
                        fi
                    done
                fi
            done
        fi
    done
}

# Helper function to find all pipeline directories
# Scans both pipelines/ and third_party/pipelines/
find_all_pipelines() {
    for base_dir in "pipelines" "third_party/pipelines"; do
        if [ -d "$base_dir" ]; then
            for category_dir in "$base_dir"/*/; do
                if [ -d "$category_dir" ]; then
                    for pipe_dir in "$category_dir"*/; do
                        if [ -d "$pipe_dir" ] && [ -f "${pipe_dir}pipeline.py" ]; then
                            pipe_path="${pipe_dir%/}"
                            pipelines+=("$pipe_path")
                        fi
                    done
                fi
            done
        fi
    done
}

# Helper function to extract directory from file path and add to array
# Args: $1 = file path
# Uses glob pattern matching to detect components vs pipelines
extract_dir_from_file() {
    local file=$1
    local dir
    
    # Note: Pattern must be UNQUOTED for glob matching to work in [[ ]]
    if [[ "$file" == components/*/*/* ]]; then
        dir=$(echo "$file" | cut -d'/' -f1-3)  # components/<category>/<component>
        components+=("$dir")
    elif [[ "$file" == pipelines/*/*/* ]]; then
        dir=$(echo "$file" | cut -d'/' -f1-3)  # pipelines/<category>/<pipeline>
        pipelines+=("$dir")
    elif [[ "$file" == third_party/components/*/*/* ]]; then
        dir=$(echo "$file" | cut -d'/' -f1-4)  # third_party/components/<category>/<component>
        components+=("$dir")
    elif [[ "$file" == third_party/pipelines/*/*/* ]]; then
        dir=$(echo "$file" | cut -d'/' -f1-4)  # third_party/pipelines/<category>/<pipeline>
        pipelines+=("$dir")
    fi
}

# Check if the generator script itself was changed
for file in "$@"; do
    if [[ "$file" == scripts/generate_readme/* ]]; then
        generator_changed=true
        break
    fi
done


if [ "$generator_changed" = true ]; then
    # If generator changed, find all components and pipelines
    echo "Generator script changed, checking all components and pipelines" >&2
    
    find_all_components
    find_all_pipelines
else
    # Normal operation: extract directories from changed files
    echo "Generator script not changed, checking only changed files" >&2
    for file in "$@"; do
        echo "Checking file: $file" >&2
        extract_dir_from_file "$file"
    done

fi

# Deduplicate and output space-separated list
all_targets=("${components[@]}" "${pipelines[@]}")
unique_targets=($(printf '%s\n' "${all_targets[@]}" | sort -u))
echo "${unique_targets[@]}"


