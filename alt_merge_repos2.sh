#!/bin/bash

# Git Repository Merger
#
# Merges multiple git repositories into a single repository with path filtering,
# branch preservation, and subdirectory organization.
#
# Usage:
#   ./alt_merge_repos2.sh -c config.json -o output-repo [-b base-dir] [-t tmp-dir]
#
# Options:
#   -c, --config FILE      Path to JSON configuration file (required)
#   -o, --output DIR       Output repository directory name (required)
#   -b, --base-dir DIR     Base directory to work in (default: $HOME)
#   -t, --tmp-dir DIR      Temporary directory for clones (default: /tmp)
#   -h, --help             Show this help message
#
# Configuration File Format (JSON):
# {
#   "repositories": [
#     {
#       "name": "repo-name",
#       "url": "git@github.com:org/repo.git",
#       "default_branch": "master",
#       "subdirectory": "optional-subdir",
#       "filter_paths": ["path1", "path2"],
#       "invert_paths": true,
#       "branches_to_grab": [
#         {"remote_url": "git@github.com:user/fork.git", "branch": "branch-name"}
#       ],
#       "reset_to_branch": "optional-branch",
#       "preserve_files": ["file1", "file2"]
#     }
#   ],
#   "final_remote": {
#     "name": "github",
#     "url": "git@github.com:org/repo.git"
#   }
# }
#
# Example:
#   ./alt_merge_repos2.sh -c merge-config.json -o merged-repo

set -euo pipefail

# Default values
BASE_DIR="${HOME}"
TMP_DIR="/tmp"
CONFIG_FILE=""
OUTPUT_REPO=""
ARGS="--allow-unrelated-histories --no-edit"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print error message and exit
error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

# Print info message
info() {
    echo -e "${GREEN}Info:${NC} $1"
}

# Print warning message
warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

# Show usage information
usage() {
    cat << EOF
Git Repository Merger

Usage: $0 -c CONFIG -o OUTPUT [OPTIONS]

Required Options:
  -c, --config FILE      Path to JSON configuration file
  -o, --output DIR       Output repository directory name

Optional Options:
  -b, --base-dir DIR     Base directory to work in (default: $HOME)
  -t, --tmp-dir DIR      Temporary directory for clones (default: /tmp)
  -h, --help             Show this help message

Configuration File Format:
  See script header for detailed JSON schema.

Example:
  $0 -c config.json -o merged-repo -b /path/to/work
EOF
}

# Parse command-line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_REPO="$2"
                shift 2
                ;;
            -b|--base-dir)
                BASE_DIR="$2"
                shift 2
                ;;
            -t|--tmp-dir)
                TMP_DIR="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1\nUse -h or --help for usage information"
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$CONFIG_FILE" ]]; then
        error "Configuration file is required. Use -c or --config"
    fi

    if [[ -z "$OUTPUT_REPO" ]]; then
        error "Output repository name is required. Use -o or --output"
    fi

    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Configuration file not found: $CONFIG_FILE"
    fi

    # Check for jq (required for JSON parsing)
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed. Please install jq to parse JSON configuration."
    fi
}

# Grab a branch from a remote repository
grab_remote() {
    local remote_url="$1"
    local branch_name="$2"
    info "Grabbing branch '$branch_name' from $remote_url"
    git remote add temp "$remote_url"
    git fetch temp "$branch_name" || warn "Failed to fetch branch $branch_name"
    git branch "$branch_name" "temp/$branch_name" 2>/dev/null || git branch -f "$branch_name" "temp/$branch_name"
    git remote rm temp
}

# Create a branch from a remote repository
create_branch() {
    local repo_path="$1"
    local branch_name="$2"
    info "Creating branch '$branch_name' from $repo_path"
    git checkout -q master || git checkout -q main || git checkout -q -b master
    git checkout -q -b "$branch_name" 2>/dev/null || git checkout -q "$branch_name"
    git pull "$repo_path" "$branch_name" $ARGS || warn "Failed to pull branch $branch_name"
    git checkout -q master 2>/dev/null || git checkout -q main || git checkout -q -b master
}

# Clone a repository to temporary directory
clone_repo() {
    local repo_url="$1"
    local repo_name="$2"
    local tmp_repo="${TMP_DIR}/${repo_name}"
    
    info "Cloning $repo_name from $repo_url"
    rm -rf "$tmp_repo"
    git clone "$repo_url" "$tmp_repo"
    echo "$tmp_repo"
}

# Apply git filter-repo with path filtering
apply_filter() {
    local filter_paths=("$@")
    local invert="${INVERT_PATHS:-false}"
    
    if [[ ${#filter_paths[@]} -eq 0 ]]; then
        return 0
    fi

    info "Applying filter-repo with ${#filter_paths[@]} path(s), invert=$invert"
    
    local filter_args=()
    for path in "${filter_paths[@]}"; do
        filter_args+=(--path "$path")
    done
    
    if [[ "$invert" == "true" ]]; then
        filter_args+=(--invert-paths)
    fi
    
    filter_args+=(--force)
    git filter-repo "${filter_args[@]}"
}

# Process a single repository from configuration
process_repository() {
    local repo_json="$1"
    local repo_name
    local repo_url
    local default_branch
    local subdirectory
    local filter_paths_str
    local invert_paths
    local branches_to_grab_str
    local reset_to_branch
    local preserve_files_str

    repo_name=$(echo "$repo_json" | jq -r '.name // empty')
    repo_url=$(echo "$repo_json" | jq -r '.url // empty')
    default_branch=$(echo "$repo_json" | jq -r '.default_branch // "master"')
    subdirectory=$(echo "$repo_json" | jq -r '.subdirectory // empty')
    filter_paths_str=$(echo "$repo_json" | jq -r '.filter_paths // [] | @json')
    invert_paths=$(echo "$repo_json" | jq -r '.invert_paths // false')
    branches_to_grab_str=$(echo "$repo_json" | jq -r '.branches_to_grab // [] | @json')
    reset_to_branch=$(echo "$repo_json" | jq -r '.reset_to_branch // empty')
    preserve_files_str=$(echo "$repo_json" | jq -r '.preserve_files // [] | @json')

    if [[ -z "$repo_name" ]] || [[ -z "$repo_url" ]]; then
        error "Repository configuration missing 'name' or 'url'"
    fi

    info "Processing repository: $repo_name"

    # Clone repository
    local tmp_repo
    tmp_repo=$(clone_repo "$repo_url" "$repo_name")
    cd "$tmp_repo"

    # Reset to specific branch if requested
    if [[ -n "$reset_to_branch" ]] && [[ "$reset_to_branch" != "null" ]]; then
        info "Resetting to branch: $reset_to_branch"
        git reset --hard "origin/$reset_to_branch" || warn "Failed to reset to $reset_to_branch"
    fi

    # Grab branches from forks
    if [[ "$branches_to_grab_str" != "[]" ]] && [[ "$branches_to_grab_str" != "null" ]]; then
        local branch_count
        branch_count=$(echo "$branches_to_grab_str" | jq 'length')
        for ((i=0; i<branch_count; i++)); do
            local branch_json
            branch_json=$(echo "$branches_to_grab_str" | jq ".[$i]")
            local remote_url
            local branch_name
            remote_url=$(echo "$branch_json" | jq -r '.remote_url')
            branch_name=$(echo "$branch_json" | jq -r '.branch')
            if [[ -n "$remote_url" ]] && [[ -n "$branch_name" ]]; then
                grab_remote "$remote_url" "$branch_name"
            fi
        done
    fi

    # Preserve files before filtering
    local preserve_dir="${TMP_DIR}/preserve_${repo_name}"
    rm -rf "$preserve_dir"
    mkdir -p "$preserve_dir"
    if [[ "$preserve_files_str" != "[]" ]] && [[ "$preserve_files_str" != "null" ]]; then
        local file_count
        file_count=$(echo "$preserve_files_str" | jq 'length')
        for ((i=0; i<file_count; i++)); do
            local file_path
            file_path=$(echo "$preserve_files_str" | jq -r ".[$i]")
            if [[ -f "$file_path" ]]; then
                info "Preserving file: $file_path"
                cp -f "$file_path" "$preserve_dir/"
            fi
        done
    fi

    # Apply path filtering
    INVERT_PATHS="$invert_paths"
    if [[ "$filter_paths_str" != "[]" ]] && [[ "$filter_paths_str" != "null" ]]; then
        local filter_paths_array
        readarray -t filter_paths_array < <(echo "$filter_paths_str" | jq -r '.[]')
        if [[ ${#filter_paths_array[@]} -gt 0 ]]; then
            apply_filter "${filter_paths_array[@]}"
        fi
    fi

    # Move to subdirectory if specified
    if [[ -n "$subdirectory" ]] && [[ "$subdirectory" != "null" ]]; then
        info "Moving repository to subdirectory: $subdirectory"
        git filter-repo --to-subdirectory-filter "$subdirectory" --force
    fi

    # Restore preserved files
    if [[ -d "$preserve_dir" ]] && [[ -n "$(ls -A "$preserve_dir" 2>/dev/null)" ]]; then
        for file in "$preserve_dir"/*; do
            if [[ -f "$file" ]]; then
                local filename
                filename=$(basename "$file")
                local target_path
                if [[ -n "$subdirectory" ]] && [[ "$subdirectory" != "null" ]]; then
                    target_path="${subdirectory}/${filename}"
                else
                    target_path="$filename"
                fi
                info "Restoring preserved file: $target_path"
                cp -f "$file" "$target_path"
                git add "$target_path"
            fi
        done
        if [[ -n "$(git status --porcelain)" ]]; then
            git commit -m "Restore preserved files" || true
        fi
        rm -rf "$preserve_dir"
    fi

    echo "$tmp_repo"
}

# Create the merged repository
make_new_repo() {
    local config_json
    config_json=$(cat "$CONFIG_FILE")

    # Validate JSON
    if ! echo "$config_json" | jq empty 2>/dev/null; then
        error "Invalid JSON in configuration file"
    fi

    # Initialize new repository
    local new_repo_path="${BASE_DIR}/${OUTPUT_REPO}"
    info "Initializing new repository at: $new_repo_path"
    rm -rf "$new_repo_path"
    mkdir -p "$new_repo_path"
    cd "$new_repo_path"
    git init

    # Process each repository
    local repo_count
    repo_count=$(echo "$config_json" | jq '.repositories | length')
    local processed_repos=()

    for ((i=0; i<repo_count; i++)); do
        local repo_json
        repo_json=$(echo "$config_json" | jq ".repositories[$i]")
        local tmp_repo
        tmp_repo=$(process_repository "$repo_json")
        processed_repos+=("$tmp_repo")
    done

    # Merge repositories in order
    info "Merging repositories into final repository"
    cd "$new_repo_path"

    for tmp_repo in "${processed_repos[@]}"; do
        local repo_name
        repo_name=$(basename "$tmp_repo")
        local repo_json
        repo_json=$(echo "$config_json" | jq ".repositories[] | select(.name == \"$repo_name\")")
        local default_branch
        default_branch=$(echo "$repo_json" | jq -r '.default_branch // "master"')

        info "Pulling $repo_name (branch: $default_branch)"
        git pull "$tmp_repo" "$default_branch" $ARGS || warn "Failed to pull $repo_name"

        # Create branches for grabbed branches
        local branches_to_grab_str
        branches_to_grab_str=$(echo "$repo_json" | jq -r '.branches_to_grab // [] | @json')
        if [[ "$branches_to_grab_str" != "[]" ]] && [[ "$branches_to_grab_str" != "null" ]]; then
            local branch_count
            branch_count=$(echo "$branches_to_grab_str" | jq 'length')
            for ((j=0; j<branch_count; j++)); do
                local branch_json
                branch_json=$(echo "$branches_to_grab_str" | jq ".[$j]")
                local branch_name
                branch_name=$(echo "$branch_json" | jq -r '.branch')
                if [[ -n "$branch_name" ]]; then
                    create_branch "$tmp_repo" "$branch_name"
                fi
            done
        fi
    done

    # Add final remote if specified
    local final_remote_name
    local final_remote_url
    final_remote_name=$(echo "$config_json" | jq -r '.final_remote.name // empty')
    final_remote_url=$(echo "$config_json" | jq -r '.final_remote.url // empty')
    if [[ -n "$final_remote_name" ]] && [[ -n "$final_remote_url" ]] && [[ "$final_remote_name" != "null" ]] && [[ "$final_remote_url" != "null" ]]; then
        info "Adding remote '$final_remote_name': $final_remote_url"
        git remote add "$final_remote_name" "$final_remote_url"
    fi
}

# Perform aggressive garbage collection
aggressive_gc() {
    info "Performing aggressive garbage collection"
    # Delete references to the old history
    git for-each-ref --format='delete %(refname)' refs/original 2>/dev/null | git update-ref --stdin || true
    # Flag all deleted objects for garbage collection
    git reflog expire --expire=now --all
    # Garbage collect
    git gc --prune=now
}

# Main execution
main() {
    parse_args "$@"
    
    info "Starting repository merge process"
    info "Configuration: $CONFIG_FILE"
    info "Output: ${BASE_DIR}/${OUTPUT_REPO}"
    info "Temp directory: $TMP_DIR"

    make_new_repo
    aggressive_gc

    cd "${BASE_DIR}/${OUTPUT_REPO}"
    if command -v git-big-files &> /dev/null; then
        info "Analyzing large files"
        git-big-files | tee /tmp/big-files.out || true
    fi
    
    info "Repository merge complete!"
    echo "DISK USAGE: $(du -sh .)"
    echo "Repository location: $(pwd)"
}

# Run main function
main "$@"
