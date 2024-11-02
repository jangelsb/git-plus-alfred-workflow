#!/usr/bin/env python3
import json
import subprocess
import sys
import os

wd = os.getenv('input_working_directory')

class AlfredItem:
    def __init__(self, title, value, command, subtitle = ''):
        self.title = title
        self.value = value
        self.command = command
        self.subtitle = subtitle

    def to_dict(self):
        return {
            "title": self.title,
            "arg": f"{self.value}",
            "subtitle": self.subtitle
        }

def list_git_branches(repo_path):
    try:
        # Change the working directory to the specified path
        os.chdir(repo_path)

        # Run 'git branch --list' to get all local branches
        local_result = subprocess.run(['git', 'branch', '--list'], capture_output=True, text=True, check=True)
        local_branches = local_result.stdout.splitlines()
        
        # Run 'git branch -r' to get all remote branches
        remote_result = subprocess.run(['git', 'branch', '-r'], capture_output=True, text=True, check=True)
        remote_branches = remote_result.stdout.splitlines()

        # Clean up the branch names
        local_branches = [branch.strip() for branch in local_branches]
        remote_branches = [branch.strip() for branch in remote_branches]
        current_branch = next((branch for branch in local_branches if branch.startswith('*')), None)

        items = []
        for branch in local_branches:
            title = branch 
            value = branch
            if branch.startswith('*'):
                value = branch.strip('* ')
                title = f"{value} -- current"

            items.append(AlfredItem(title=title, value=value, command="git checkout"))

        for branch in remote_branches:
            title = branch
            value = branch.replace('origin/', '')
            items.append(AlfredItem(title=title, value=value, command="git checkout", subtitle='Remote'))

        items.append(AlfredItem(title="fetch --prune", value="git fetch --prune", command="git"))

        return [item.to_dict() for item in items]

    except subprocess.CalledProcessError:
        return [{"title": "Not a Git repository", "value": ""}]
    except FileNotFoundError:
        return [{"title": "Invalid directory path", "value": ""}]

def main():
    # Retrieve the directory path from Alfred's query input
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = wd

    # Get the list of git branches (local and remote) from the specified path
    items = list_git_branches(repo_path)

    # Output Alfred-compatible JSON
    print(json.dumps({"items": items}))

if __name__ == "__main__":
    main()
