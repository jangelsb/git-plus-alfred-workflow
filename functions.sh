view_hunk() {
    local action="$1"  # "stage" or "unstage"
    local header="$2"  # e.g., "@@ -17,6 +17,7 @@"
    local file="$3"    # File path

    # Determine the appropriate diff command
    local full_diff
    if [ "$action" == "stage" ]; then
        full_diff=$(git diff "$file")
    elif [ "$action" == "unstage" ]; then
        full_diff=$(git diff --cached "$file")
    else
        echo "Invalid action. Use 'stage' or 'unstage'."
        return 1
    fi

    # Escape special characters in the header for sed
    local escaped_header
    escaped_header=$(printf '%s\n' "$header" | sed -e 's/[]\/$*.^[]/\\&/g')

    # Extract the hunk between the provided header and the next @@
    local hunk
    hunk=$(echo "$full_diff" | sed -n "/$escaped_header/,/^@@/p" | sed "/^$escaped_header/d")

    echo "$hunk"
}

# Example usage



view_hunk "stage" "@@ -520,7 +520,7 @@ fi</string>" "info.plist"

view_hunk "stage" "@@ -2,6 +2,7 @@" "actions.yaml"



process_diff_action() {
    local action="$1"       # "stage" or "unstage"
    local header="$2"       # e.g., "@@ -17,6 +17,7 @@"
    local file="$3"         # File path

    # Determine the appropriate diff command and file count
    local full_diff file_count
    if [[ "$action" == "stage" ]]; then
        full_diff=$(git diff "$file")
        file_count=$(git diff --name-only | wc -l | xargs)
    elif [[ "$action" == "unstage" ]]; then
        full_diff=$(git diff --cached "$file")
        file_count=$(git diff --cached --name-only | wc -l | xargs)
    else
        echo "Invalid action. Use 'stage' or 'unstage'."
        return 1
    fi

    # Extract the diff metadata (diff --git, index, file headers)
    local diff_header
    diff_header=$(echo "$full_diff" | sed -n "/^diff --git a\/$file b\/$file/,/^@@/p" | sed '$d' | sed '/^$/d')

    # Extract the hunk
    local extracted_hunk
    extracted_hunk=$(echo "$full_diff" | sed -n "/$header/,/^@@/p")

    # Store the first line of the extracted hunk
    local first_line
    first_line=$(echo "$extracted_hunk" | head -n 1)

    # Remove any lines that start with `@@`
    local hunk
    hunk=$(echo "$extracted_hunk" | sed '/^@@/d')

    # Check if the hunk exists
    if [[ -z "$extracted_hunk" ]]; then
        echo "Error: No matching hunk found for $header in $file"
        return 1
    fi

    # Create a patch file
    local patch_file="hunk.patch"
    {
        echo "$diff_header"
        echo "$first_line"
        echo "$hunk"
    } > "$patch_file"

    # Count the number of hunks
    local hunk_count
    hunk_count=$(echo "$full_diff" | grep -c '^@@')

    # Apply or reverse the patch
    if [[ "$action" == "stage" ]]; then
        git apply --cached "$patch_file"
    elif [[ "$action" == "unstage" ]]; then
        git apply --cached --reverse "$patch_file"
    fi

    # Clean up
    rm "$patch_file"

    # Determine reload level
    if [[ "$hunk_count" -eq 1 ]]; then
        if [[ "$file_count" -eq 1 ]]; then
            echo "[reload~3]"
        else
            echo "[reload~2]"
        fi
    else
        echo "[reload~1]"
    fi
}
