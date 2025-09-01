################################################################################
##############################    git commands    ##############################
################################################################################

git_stash_checkout_pull() {
    git stash; [[ -n "$1" ]] && git checkout "$1"; git pull;
}



################################################################################
##############################    helper commands    ##############################
################################################################################

run_in_terminal() {
  local wd=$(pwd)        # save working directory
  local cmd="$*"         # grab all args passed to function

  if [[ -z "$cmd" ]]; then
    echo "Usage: run_in_terminal <command>"
    return 1
  fi

  osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$wd' && $cmd"
end tell
EOF
}


################################################################################
##############################     DIFF LOGIC     ##############################
################################################################################

# Runs git diff command for `staged`, `modified`, and `untracked` files
diff_command() {
    local type="$1"  # "staged", "modified", or "untracked"

    if [[ "$type" == "staged" ]]; then
        git diff --cached --name-only
    elif [[ "$type" == "modified" ]]; then
        git diff --name-only
    elif [[ "$type" == "untracked" ]]; then
        git ls-files --others --exclude-standard
    else
        echo "Invalid type. Use 'staged', 'modified', or 'untracked'."
        return 1
    fi
}

# Helper function to get the full diff for a given action and file
_get_first_file() {
    local action="$1"  # "stage", "unstage", or "discard"

    if [[ "$action" == "stage" ]]; then
        diff_command 'modified' | head -n 1
    elif [[ "$action" == "unstage" ]]; then
        diff_command 'staged' | head -n 1
    elif [[ "$action" == "discard" ]]; then
        diff_command 'modified' | head -n 1
    else
        echo "Invalid action. Use 'stage', 'unstage', or 'discard'."
        return 1
    fi
}

# Helper function to get a nice diff header 
_get_diff_header() {
    local action="$1"  # "stage", "unstage", or "discard"
    local file="$2"
    local header="$3"

    if [[ -z "$file" ]]; then
        file=$(_get_first_file "$action")
    fi

    if [[ -z "$header" ]]; then
        full_diff=$(_get_full_diff "$action" "$file")
        header=$(_get_first_hunk "$full_diff" | grep '^@@')
    fi

    count=$(_get_hunk_count "$action" "$file")

    echo "----------------------------------"
    echo "file: $file ($count)"
    echo "hunk: $header"
    echo "----------------------------------"
}

# Helper function to get the number of hunks for the action and or file
_get_hunk_count() {
    local action="$1"  # "stage", "unstage", or "discard"
    local file="$2"

    if [[ -z "$file" ]]; then
        file=$(_get_first_file "$action")
    fi

    full_diff=$(_get_full_diff "$action" "$file")
    local count=$(echo "$full_diff" | grep -c '^@@')

    if (( count == 1 )); then
        echo "$count hunk"
    else
        echo "$count hunks"
    fi
}

# Helper function to get the full diff for a given action and file
_get_full_diff() {
    local action="$1"  # "stage", "unstage", or "discard"
    local file="$2"    # File path

    if [[ -z "$file" ]]; then
        file=$(_get_first_file "$action") || { echo 'get first file failed'; return 1; }
    fi

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

# Helper function to get a hunk
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
# ACTION="stage"      # "stage" or "unstage"
# FILE="[parent~2]"   # Optional, File path else uses the first file
# HEADER="[parent]"   # Optional, e.g., "@@ -17,6 +17,7 @@"
view_hunk() {
    local action="$1"
    local file="$2"
    local header="$3"

    local full_diff hunk
    full_diff=$(_get_full_diff "$action" "$file") || { echo 'full_diff failed'; return 1; }

    if [[ -n "$header" ]]; then
        hunk=$(_get_hunk "$full_diff" "$header") || { echo 'hunk failed'; return 1; }
    else
        hunk=$(_get_first_hunk "$full_diff") || { echo 'hunk failed'; return 1; }
    fi

    _get_diff_header "$action" "$file" "$header"
    echo

    # Remove all lines that start with @@
    echo "$hunk" | sed '/^@@/d'
}


# Function to process a hunk (stage or unstage)
# ACTION="stage"  # "stage" or "unstage"
# FILE="[parent~2]"   # Optional, File path else uses the first file
# HEADER="[parent]"   # Optional, e.g., "@@ -17,6 +17,7 @@" else uses first hunk
process_hunk() {
    local action="$1"
    local file="$2"
    local header="$3"

    # Determine the full diff and file count based on action
    local full_diff diff_header hunk file_count apply_command
    if [[ "$action" == "stage" ]]; then
        file_count=$(diff_command 'modified' | wc -l | xargs)
        apply_command="git apply --cached"
    elif [[ "$action" == "unstage" ]]; then
        file_count=$(diff_command 'staged' | wc -l | xargs)
        apply_command="git apply --cached --reverse"
    elif [[ "$action" == "discard" ]]; then
        file_count=$(diff_command 'modified' | wc -l | xargs)
        apply_command="git apply --reverse"
    else
        echo "Invalid action. Use 'stage', 'unstage', or 'discard'."
        return 1
    fi

    full_diff=$(_get_full_diff "$action" "$file") || (echo 'full_diff failed' && return 1)
    diff_header=$(echo "$full_diff" | head -n 4)

    if [[ -n "$header" ]]; then
        hunk=$(_get_hunk "$full_diff" "$header") || { echo 'hunk failed'; return 1; }
    else
        hunk=$(_get_first_hunk "$full_diff") || { echo 'hunk failed'; return 1; }
    fi

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
    if [[ -n "$header" ]]; then

      if [[ "$hunk_count" -eq 1 && "$file_count" -eq 1 ]]; then
          return 3
      elif [[ "$hunk_count" -eq 1 ]]; then
          return 2
      else
          return 1
      fi

    else

      # viewing all hunks, only go back 3, if no more hunks
      if [[ "$hunk_count" -eq 1 && "$file_count" -eq 1 ]]; then
          return 2
      else
          return 0
      fi

    fi

}

# Function to process a file (stage or unstage)
# ACTION="stage"      # "stage" or "unstage" or "untracked"
# FILE="[parent~2]"   # File path else uses the first file
git_process_file() {
    local action="$1"
    local file="$2"

    local file_count
    if [[ "$action" == "stage" ]]; then
        file_count=$(diff_command 'modified' | wc -l | xargs)
        git add "$file"
    elif [[ "$action" == "unstage" ]]; then
        file_count=$(diff_command 'staged' | wc -l | xargs)
        git reset "$file"
    elif [[ "$action" == "untracked" ]]; then
        file_count=$(diff_command 'untracked' | wc -l | xargs)
        git add "$file"
    else
        echo "Invalid action. Use 'stage' or 'unstage''."
        return 1
    fi

    if [ "$file_count" -eq 1 ]; then
        return 1
    else
        return 0
    fi
}