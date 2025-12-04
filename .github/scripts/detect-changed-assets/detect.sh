#!/bin/bash
# Detect changed components and pipelines
# Usage: detect.sh <base-ref> <head-ref> <include-third-party> <filter>

set -euo pipefail

# Arguments
BASE_REF="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"
INCLUDE_THIRD_PARTY="${3:-true}"
FILTER="${4:-}"

# Output files
GITHUB_OUTPUT="${GITHUB_OUTPUT:-/tmp/github-output-$$.txt}"
GITHUB_STEP_SUMMARY="${GITHUB_STEP_SUMMARY:-/tmp/github-summary-$$.txt}"
touch "$GITHUB_OUTPUT" "$GITHUB_STEP_SUMMARY"

# Fetch base branch if needed
if [[ "$BASE_REF" == origin/* ]]; then
  BASE_BRANCH="${BASE_REF#origin/}"
  git fetch origin "${BASE_BRANCH}:refs/remotes/origin/${BASE_BRANCH}" 2>/dev/null || \
    git fetch --depth=100 origin "${BASE_BRANCH}" 2>/dev/null || true
fi

# Get changed files
MERGE_BASE=$(git merge-base "${BASE_REF}" "${HEAD_REF}" 2>/dev/null || echo "")
if [ -z "$MERGE_BASE" ]; then
  CHANGED_FILES=$(git diff --name-only "${BASE_REF}...${HEAD_REF}" 2>/dev/null || \
                  git diff --name-only "${BASE_REF}" "${HEAD_REF}" 2>/dev/null || echo "")
else
  CHANGED_FILES=$(git diff --name-only "${MERGE_BASE}" "${HEAD_REF}")
fi

# Apply pattern filter if specified
FILTERED_CHANGED_FILES="$CHANGED_FILES"
if [ -n "$FILTER" ]; then
  FILTERED_CHANGED_FILES=$(echo "$CHANGED_FILES" | grep -E "$FILTER" || echo "")
fi

# Parse changed files
COMPONENTS=()
PIPELINES=()

while IFS= read -r file; do
  [ -z "$file" ] && continue
  
  # Core components
  if [[ "$file" =~ ^components/([^/]+)/([^/]+)/ ]]; then
    COMPONENT_PATH="components/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    [[ ! " ${COMPONENTS[@]} " =~ " ${COMPONENT_PATH} " ]] && COMPONENTS+=("${COMPONENT_PATH}")
  fi
  
  # Core pipelines
  if [[ "$file" =~ ^pipelines/([^/]+)/([^/]+)/ ]]; then
    PIPELINE_PATH="pipelines/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    [[ ! " ${PIPELINES[@]} " =~ " ${PIPELINE_PATH} " ]] && PIPELINES+=("${PIPELINE_PATH}")
  fi
  
  # Third-party (if enabled)
  if [[ "$INCLUDE_THIRD_PARTY" == "true" ]]; then
    if [[ "$file" =~ ^third_party/components/([^/]+)/([^/]+)/ ]]; then
      COMPONENT_PATH="third_party/components/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
      [[ ! " ${COMPONENTS[@]} " =~ " ${COMPONENT_PATH} " ]] && COMPONENTS+=("${COMPONENT_PATH}")
    fi
    
    if [[ "$file" =~ ^third_party/pipelines/([^/]+)/([^/]+)/ ]]; then
      PIPELINE_PATH="third_party/pipelines/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
      [[ ! " ${PIPELINES[@]} " =~ " ${PIPELINE_PATH} " ]] && PIPELINES+=("${PIPELINE_PATH}")
    fi
  fi
done <<< "$FILTERED_CHANGED_FILES"

# Generate outputs
COMPONENT_COUNT="${#COMPONENTS[@]}"
PIPELINE_COUNT="${#PIPELINES[@]}"
COMPONENTS_LIST="${COMPONENTS[*]}"
PIPELINES_LIST="${PIPELINES[*]}"

# JSON arrays (compact)
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

# Booleans
HAS_CHANGED_COMPONENTS=$([ ${COMPONENT_COUNT} -gt 0 ] && echo "true" || echo "false")
HAS_CHANGED_PIPELINES=$([ ${PIPELINE_COUNT} -gt 0 ] && echo "true" || echo "false")
HAS_CHANGES=$([ ${COMPONENT_COUNT} -gt 0 ] || [ ${PIPELINE_COUNT} -gt 0 ] && echo "true" || echo "false")

# Write outputs
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
  echo "all-changed-files=$(echo "$CHANGED_FILES" | tr '\n' ' ')"
  echo "filtered-changed-files=$(echo "$FILTERED_CHANGED_FILES" | tr '\n' ' ')"
} >> "$GITHUB_OUTPUT"

# Write summary
{
  echo "## Changed Assets"
  echo ""
  echo "**Components:** ${COMPONENT_COUNT}"
  [ ${COMPONENT_COUNT} -gt 0 ] && printf '%s\n' "${COMPONENTS[@]}" | sed 's/^/- /'
  echo ""
  echo "**Pipelines:** ${PIPELINE_COUNT}"
  [ ${PIPELINE_COUNT} -gt 0 ] && printf '%s\n' "${PIPELINES[@]}" | sed 's/^/- /'
} >> "$GITHUB_STEP_SUMMARY"

# Show output if running standalone
if [ -z "${GITHUB_ACTIONS:-}" ]; then
  echo "Components: ${COMPONENT_COUNT}"
  [ ${COMPONENT_COUNT} -gt 0 ] && printf '  - %s\n' "${COMPONENTS[@]}"
  echo "Pipelines: ${PIPELINE_COUNT}"
  [ ${PIPELINE_COUNT} -gt 0 ] && printf '  - %s\n' "${PIPELINES[@]}"
fi

exit 0
