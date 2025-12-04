#!/bin/bash
# Detect changed components and pipelines in the repository
#
# This script is used by the detect-changed-assets composite action.
# It can also be run standalone for testing.
#
# Usage:
#   detect.sh <base-ref> <head-ref> <include-third-party>
#
# Environment Variables (when run in GitHub Actions):
#   GITHUB_OUTPUT - File to write action outputs
#   GITHUB_STEP_SUMMARY - File to write job summary
#
# Arguments:
#   $1 - BASE_REF: Base git reference (e.g., origin/main)
#   $2 - HEAD_REF: Head git reference (default: HEAD)
#   $3 - INCLUDE_THIRD_PARTY: Include third_party/ directory (default: true)

set -euo pipefail

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
BASE_REF="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"
INCLUDE_THIRD_PARTY="${3:-true}"

# GitHub Actions output files (or temp files for standalone)
GITHUB_OUTPUT="${GITHUB_OUTPUT:-/tmp/github-output-$$.txt}"
GITHUB_STEP_SUMMARY="${GITHUB_STEP_SUMMARY:-/tmp/github-summary-$$.txt}"

# Ensure output files exist
touch "$GITHUB_OUTPUT"
touch "$GITHUB_STEP_SUMMARY"

# Function to log with GitHub Actions grouping
log_group_start() {
    echo "::group::$1"
}

log_group_end() {
    echo "::endgroup::"
}

# Configuration
log_group_start "Configuration"
echo "Base ref: ${BASE_REF}"
echo "Head ref: ${HEAD_REF}"
echo "Include third-party: ${INCLUDE_THIRD_PARTY}"
log_group_end

# Ensure we have the base ref
log_group_start "Fetching base reference"

# Extract branch name from origin/branch format
BASE_BRANCH="${BASE_REF#origin/}"

# Fetch the base branch if it's a remote reference
if [[ "$BASE_REF" == origin/* ]]; then
  echo "Fetching ${BASE_BRANCH} from origin..."
  git fetch origin "${BASE_BRANCH}:refs/remotes/origin/${BASE_BRANCH}" || {
    echo -e "${YELLOW}Warning: Could not fetch ${BASE_BRANCH}, trying shallow fetch...${NC}"
    git fetch --depth=100 origin "${BASE_BRANCH}" || {
      echo -e "${RED}Error: Could not fetch base branch${NC}"
      exit 1
    }
  }
fi

log_group_end

# Get list of changed files
log_group_start "Getting changed files"
echo "Comparing ${BASE_REF}...${HEAD_REF}"

# Get the merge base to handle both PR and push events properly
MERGE_BASE=$(git merge-base "${BASE_REF}" "${HEAD_REF}" 2>/dev/null || echo "")

if [ -z "$MERGE_BASE" ]; then
  echo -e "${YELLOW}Warning: Could not find merge base, using direct diff${NC}"
  CHANGED_FILES=$(git diff --name-only "${BASE_REF}...${HEAD_REF}" 2>/dev/null || git diff --name-only "${BASE_REF}" "${HEAD_REF}" || echo "")
else
  echo "Merge base: ${MERGE_BASE}"
  CHANGED_FILES=$(git diff --name-only "${MERGE_BASE}" "${HEAD_REF}")
fi

if [ -z "$CHANGED_FILES" ]; then
  echo -e "${YELLOW}No changed files detected${NC}"
  CHANGED_FILES=""
else
  echo -e "${GREEN}Found $(echo "$CHANGED_FILES" | wc -l) changed files${NC}"
  echo "$CHANGED_FILES" | head -20
  if [ $(echo "$CHANGED_FILES" | wc -l) -gt 20 ]; then
    echo "... and more"
  fi
fi

log_group_end

# Initialize arrays
COMPONENTS=()
PIPELINES=()

# Process changed files to identify components and pipelines
log_group_start "Identifying changed components and pipelines"

while IFS= read -r file; do
  # Skip empty lines
  [ -z "$file" ] && continue
  
  # Check if file is in components directory
  if [[ "$file" =~ ^components/([^/]+)/([^/]+)/ ]]; then
    CATEGORY="${BASH_REMATCH[1]}"
    NAME="${BASH_REMATCH[2]}"
    COMPONENT_PATH="components/${CATEGORY}/${NAME}"
    
    # Add to array if not already present
    if [[ ! " ${COMPONENTS[@]} " =~ " ${COMPONENT_PATH} " ]]; then
      COMPONENTS+=("${COMPONENT_PATH}")
      echo -e "${GREEN}✓${NC} Component: ${COMPONENT_PATH}"
    fi
  fi
  
  # Check if file is in pipelines directory
  if [[ "$file" =~ ^pipelines/([^/]+)/([^/]+)/ ]]; then
    CATEGORY="${BASH_REMATCH[1]}"
    NAME="${BASH_REMATCH[2]}"
    PIPELINE_PATH="pipelines/${CATEGORY}/${NAME}"
    
    # Add to array if not already present
    if [[ ! " ${PIPELINES[@]} " =~ " ${PIPELINE_PATH} " ]]; then
      PIPELINES+=("${PIPELINE_PATH}")
      echo -e "${GREEN}✓${NC} Pipeline: ${PIPELINE_PATH}"
    fi
  fi
  
  # Check third_party if enabled
  if [[ "$INCLUDE_THIRD_PARTY" == "true" ]]; then
    # Third-party components
    if [[ "$file" =~ ^third_party/components/([^/]+)/([^/]+)/ ]]; then
      CATEGORY="${BASH_REMATCH[1]}"
      NAME="${BASH_REMATCH[2]}"
      COMPONENT_PATH="third_party/components/${CATEGORY}/${NAME}"
      
      if [[ ! " ${COMPONENTS[@]} " =~ " ${COMPONENT_PATH} " ]]; then
        COMPONENTS+=("${COMPONENT_PATH}")
        echo -e "${GREEN}✓${NC} Third-party Component: ${COMPONENT_PATH}"
      fi
    fi
    
    # Third-party pipelines
    if [[ "$file" =~ ^third_party/pipelines/([^/]+)/([^/]+)/ ]]; then
      CATEGORY="${BASH_REMATCH[1]}"
      NAME="${BASH_REMATCH[2]}"
      PIPELINE_PATH="third_party/pipelines/${CATEGORY}/${NAME}"
      
      if [[ ! " ${PIPELINES[@]} " =~ " ${PIPELINE_PATH} " ]]; then
        PIPELINES+=("${PIPELINE_PATH}")
        echo -e "${GREEN}✓${NC} Third-party Pipeline: ${PIPELINE_PATH}"
      fi
    fi
  fi
done <<< "$CHANGED_FILES"

log_group_end

# Create outputs
log_group_start "Generating outputs"

# Count
COMPONENT_COUNT="${#COMPONENTS[@]}"
PIPELINE_COUNT="${#PIPELINES[@]}"

echo "Components found: ${COMPONENT_COUNT}"
echo "Pipelines found: ${PIPELINE_COUNT}"

# Space-separated lists
COMPONENTS_LIST="${COMPONENTS[*]}"
PIPELINES_LIST="${PIPELINES[*]}"

# JSON arrays (compact format, single line)
if [ ${COMPONENT_COUNT} -eq 0 ]; then
  COMPONENTS_JSON="[]"
else
  COMPONENTS_JSON=$(printf '%s\n' "${COMPONENTS[@]}" | jq -R . | jq -sc .)
fi

if [ ${PIPELINE_COUNT} -eq 0 ]; then
  PIPELINES_JSON="[]"
else
  PIPELINES_JSON=$(printf '%s\n' "${PIPELINES[@]}" | jq -R . | jq -sc .)
fi

# Has changes?
if [ ${COMPONENT_COUNT} -gt 0 ]; then
  HAS_CHANGED_COMPONENTS="true"
else
  HAS_CHANGED_COMPONENTS="false"
fi

if [ ${PIPELINE_COUNT} -gt 0 ]; then
  HAS_CHANGED_PIPELINES="true"
else
  HAS_CHANGED_PIPELINES="false"
fi

if [ ${COMPONENT_COUNT} -gt 0 ] || [ ${PIPELINE_COUNT} -gt 0 ]; then
  HAS_CHANGES="true"
else
  HAS_CHANGES="false"
fi

# All changed files (truncated for output size)
ALL_FILES=$(echo "$CHANGED_FILES" | head -100 | tr '\n' ' ')

# Set outputs (JSON is compact single-line format)
{
  echo "changed-components=${COMPONENTS_LIST}"
  echo "changed-pipelines=${PIPELINES_LIST}"
  echo "changed-components-json=${COMPONENTS_JSON}"
  echo "changed-pipelines-json=${PIPELINES_JSON}"
  echo "changed-components-count=${COMPONENT_COUNT}"
  echo "changed-pipelines-count=${PIPELINE_COUNT}"
  echo "has-changes=${HAS_CHANGES}"
  echo "has-changed-components=${HAS_CHANGED_COMPONENTS}"
  echo "has-changed-pipelines=${HAS_CHANGED_PIPELINES}"
  echo "all-changed-files=${ALL_FILES}"
} >> "$GITHUB_OUTPUT"

log_group_end

# Summary
log_group_start "Summary"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Changed Assets Summary${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Components: ${COMPONENT_COUNT}"
if [ ${COMPONENT_COUNT} -gt 0 ]; then
  for comp in "${COMPONENTS[@]}"; do
    echo "  - ${comp}"
  done
fi
echo ""
echo "Pipelines: ${PIPELINE_COUNT}"
if [ ${PIPELINE_COUNT} -gt 0 ]; then
  for pipe in "${PIPELINES[@]}"; do
    echo "  - ${pipe}"
  done
fi
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_group_end

# Set job summary
{
  echo "## 📦 Changed Assets"
  echo ""
  echo "### Components (${COMPONENT_COUNT})"
  if [ ${COMPONENT_COUNT} -eq 0 ]; then
    echo "_No components changed_"
  else
    for comp in "${COMPONENTS[@]}"; do
      echo "- \`${comp}\`"
    done
  fi
  echo ""
  echo "### Pipelines (${PIPELINE_COUNT})"
  if [ ${PIPELINE_COUNT} -eq 0 ]; then
    echo "_No pipelines changed_"
  else
    for pipe in "${PIPELINES[@]}"; do
      echo "- \`${pipe}\`"
    done
  fi
} >> "$GITHUB_STEP_SUMMARY"

# If running standalone (not in GitHub Actions), show the outputs
if [ -z "${GITHUB_ACTIONS:-}" ]; then
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}Outputs (for debugging)${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  cat "$GITHUB_OUTPUT"
  echo ""
  echo -e "${BLUE}Summary:${NC}"
  cat "$GITHUB_STEP_SUMMARY"
fi

exit 0

