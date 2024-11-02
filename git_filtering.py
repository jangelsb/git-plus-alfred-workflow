import sys
import json
import os
import subprocess

class ResultItem:
    def __init__(self, title, arg, subtitle='', autocomplete=None, valid=False):
        self.title = title
        self.arg = arg
        self.subtitle = subtitle
        self.autocomplete = autocomplete if autocomplete else title
        self.valid = valid

    def to_dict(self):
        return {
            "title": self.title,
            "arg": self.arg,
            "subtitle": self.subtitle,
            "autocomplete": f" {self.autocomplete}",
            "valid": self.valid
        }

class Location:
    def __init__(self, title, directory):
        self.title = title
        self.directory = directory

class Command:
    def __init__(self, title, action):
        self.title = title
        self.action = action  # action is a callable function

def change_directory():
    # Change to the working directory from the environment variable
    wd = os.getenv('input_working_directory')
    if wd:
        os.chdir(wd)

def git_command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing {' '.join(args)}: {e.stderr}"

def main():
    # Prepare locations and commands
    locations = [
        Location("office", "/Users/josh/Developer/ios/next.timer"),
        Location("home", "/Users/josh/Developer/ios/next.timer"),
        Location("store", "/Users/josh/Developer/ios/next.timer")
    ]

    commands = [
        Command("list", lambda: "list command executed"),
        Command("search", lambda: "search command executed"),
        Command("status", lambda: git_command(["git", "status"])),
        Command("pull", lambda: git_command(["git", "pull"])),
        Command("checkout", lambda branch: git_command(["git", "checkout", branch]))
    ]

    # Ensure we are in the correct working directory
    change_directory()

    # Get the query input
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    args = query_input.strip().split()
    ends_with_space = query_input.endswith(" ")
    num_args = len(args)

    output = {"items": []}

    if num_args == 0:
        # Show all locations if no arguments are provided
        output['items'] = [ResultItem(loc.title, loc.directory, subtitle=loc.directory, autocomplete=loc.title).to_dict() for loc in locations]

    elif num_args == 1:
        location_query = args[0].lower()
        if ends_with_space:
            # Show commands if location is fully typed and trailing space is present
            location = next((loc for loc in locations if loc.title.lower() == location_query), None)
            if location:
                output['items'] = [ResultItem(cmd.title, arg=f"{location.title} {cmd.title}", autocomplete=f"{location.title} {cmd.title}").to_dict() for cmd in commands]
        else:
            # Filter and show matching locations
            filtered_locations = [loc for loc in locations if location_query in loc.title.lower()]
            output['items'] = [ResultItem(loc.title, arg=loc.directory, subtitle=loc.directory, autocomplete=loc.title).to_dict() for loc in filtered_locations]

    elif num_args == 2:
        location_query = args[0].lower()
        command_query = args[1].lower()
        location = next((loc for loc in locations if loc.title.lower() == location_query), None)

        if location:
            if ends_with_space:
                # If there's a space after the command, prompt for parameters
                command = next((cmd for cmd in commands if cmd.title.lower() == command_query), None)
                if command:
                    output['items'] = [ResultItem(f"Enter parameters for '{command.title}'", f"{location.title} {command.title}", autocomplete=f"{location.title} {command.title} ").to_dict()]
            else:
                # Show commands that match the input so far
                filtered_commands = [cmd for cmd in commands if command_query in cmd.title.lower()]
                output['items'] = [ResultItem(cmd.title, f"{location.title} {cmd.title}", autocomplete=f"{location.title} {cmd.title}").to_dict() for cmd in filtered_commands]

    elif num_args > 2:
        location_query = args[0].lower()
        command_query = args[1].lower()
        params = args[2:] if not ends_with_space else args[2:] + ['']
        location = next((loc for loc in locations if loc.title.lower() == location_query), None)
        command = next((cmd for cmd in commands if command_query == cmd.title.lower()), None)

        if location and command:
            result = command.action(*params) if callable(command.action) else command.action
            output['items'] = [ResultItem(f"{command.title} in {location.title}", result, valid=True).to_dict()]

    print(json.dumps(output))

if __name__ == "__main__":
    main()
