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

#    echo "[$action]"
#    echo "[$header]"

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
_get_hunk() {
    local action="$1"
    local header="$2"
    local file="$3"

    local full_diff
    full_diff=$(_get_full_diff "$action" "$file") || (echo 'full_diff failed' && return 1)

    # Escape special characters in the header for sed
    local escaped_header
    escaped_header=$(printf '%s\n' "$header" | sed -e 's/[]\/$*.^[]/\\&/g')

    # Extract the hunk between the provided header and the next @@, Return it
    echo "$(echo "$full_diff" | sed -n "/$escaped_header/,/^@@/p")"
}

# Function to view a hunk (excluding @@ lines)
# ACTION="stage"  # "stage" or "unstage"
# HEADER="[parent]"  # e.g., "@@ -17,6 +17,7 @@"
# FILE="[parent~2]"   # File path
view_hunk() {
    local action="$1"
    local header="$2"
    local file="$3"

    local hunk
    hunk=$(_get_hunk "$action" "$header" "$file") || (echo 'hunk failed' && return 1)

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

#    echo "[$action]"
#    echo "[$header]"
#    echo "[$file]"

    # Determine the full diff and file count based on action
    local full_diff file_count apply_command
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

#    echo "😎 Full Diff"
#    echo "$full_diff"
#    echo ""
#    echo ""

    # Extract the diff header
    local diff_header
    diff_header=$(echo "$full_diff" | sed -n "/^diff --git a\//,/^@@/p" | sed '$d' | sed '/^$/d')

#    echo "😎 diff_header"
#    echo "$diff_header"
#    echo ""
#    echo ""

    # Escape the header and extract the hunk
    local hunk
    hunk=$(_get_hunk "$action" "$header" "$file") || (echo 'hunk failed' && return 1)

#    echo "😎HUNK"
#    echo "$hunk"
#    echo ""
#    echo ""

    # process the hunk, by removing all lines that start with "@@", except the first line
    #   NR == 1 ||       # Always include the first line (line number 1).
    #   !/^@@/           # For all other lines, include them only if they do NOT start with "@@".
    hunk=$(echo "$hunk" | awk 'NR==1 || !/^@@/')

#    echo "😎HUNK after process"
#    echo "$hunk"
#    echo ""
#    echo ""

    # Create a patch file
    local patch_file="hunk.patch"
    {
        echo "$diff_header"
        echo "$hunk"
    } > "$patch_file"

    echo "😎PATCH"
    cat $patch_file

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