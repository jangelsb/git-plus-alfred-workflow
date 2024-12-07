################################################################################
##############################    git commonds    ##############################
################################################################################

git_checkout() {
    git stash; git checkout "$1"; git pull;
}

################################################################################
##############################     DIFF LOGIC     ##############################
################################################################################

# Helper function to get the full diff for a given action and file
_get_full_diff() {
    local action="$1"  # "stage", "unstage", or "discard"
    local file="$2"    # File path

    if [[ "$action" == "stage" ]]; then
        git diff "$file"
    elif [[ "$action" == "unstage" ]]; then
        git diff --cached "$file"
    elif [[ "$action" == "discard" ]]; then
        git diff "$file"
    else
        echo "Invalid action. Use 'stage', 'unstage', or 'discard'."
        return 1
    fi
}

# Helper function to get a hunk
_get_first_hunk() {
    local full_diff="$1"

    echo "$full_diff" | awk '
      /^@@/ {
          if (found) exit;  # Exit if a second @@ line is found
          found = 1;        # Mark that the first @@ line is found
      }
      found { print }       # Print lines after finding the first @@
  '
}

_get_hunk() {
    local full_diff="$1"
    local header="$2"

    echo "$full_diff" | awk -v header="$header" '
      $0 == header { found = 1 }                  # Start printing when the line matches $header
      /^@@/ && $0 != header && found { exit }     # Stop printing if another @@ line is found
      found { print }                             # Print lines after $header is matched
    '
}

# Function to view a hunk (excluding @@ lines)
# ACTION="stage"  # "stage" or "unstage"
# HEADER="[parent]"  # e.g., "@@ -17,6 +17,7 @@"
# FILE="[parent~2]"   # File path
view_hunk() {
    local action="$1"
    local header="$2"
    local file="$3"

    local full_diff hunk
    full_diff=$(_get_full_diff "$action" "$file") || (echo 'full_diff failed' && return 1)

    hunk=$(_get_hunk "$full_diff" "$header") || (echo 'hunk failed' && return 1)

    echo "$(echo "$hunk" | sed '/^@@/d')"
}

# Function to process a hunk (stage or unstage)
# ACTION="stage"  # "stage" or "unstage"
# HEADER="[parent]"  # e.g., "@@ -17,6 +17,7 @@"
# FILE="[parent~2]"   # File path
process_hunk() {
    local action="$1"
    local header="$2"
    local file="$3"

    echo "[$action]"
    echo "[$header]"
    echo "[$file]"

    # Determine the full diff and file count based on action
    local full_diff diff_header hunk file_count apply_command
    if [[ "$action" == "stage" ]]; then
        file_count=$(git diff --name-only | wc -l | xargs)
        apply_command="git apply --cached"
    elif [[ "$action" == "unstage" ]]; then
        file_count=$(git diff --cached --name-only | wc -l | xargs)
        apply_command="git apply --cached --reverse"
    elif [[ "$action" == "discard" ]]; then
        file_count=$(git diff --name-only | wc -l | xargs)
        apply_command="git apply --reverse"
    else
        echo "Invalid action. Use 'stage', 'unstage', or 'discard'."
        return 1
    fi

    full_diff=$(_get_full_diff "$action" "$file") || (echo 'full_diff failed' && return 1)
    diff_header=$(echo "$full_diff" | head -n 4)
    hunk=$(_get_hunk "$full_diff" "$header") || (echo 'hunk failed' && return 1)

    # Create a patch file
    local patch_file="hunk.patch"
    {
        echo "$diff_header"
        echo "$hunk"
    } > "$patch_file"

    # Apply the patch using the determined command
    eval "$apply_command \"$patch_file\""

    # Cleanup
    rm "$patch_file"

    # Count the number of hunks
    local hunk_count
    hunk_count=$(echo "$full_diff" | grep -c '^@@')

    # Determine the reload level
    if [[ "$hunk_count" -eq 1 && "$file_count" -eq 1 ]]; then
        return 3
    elif [[ "$hunk_count" -eq 1 ]]; then
        return 2
    else
        return 1
    fi
}