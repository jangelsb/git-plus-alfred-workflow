import sys
import json
import subprocess  # Added to handle git commands

def main():
    # Define available locations and commands
    locations = ["office", "home", "store"]
    commands = ["list", "search", "git status", "git pull", "git checkout"]  # Added git commands

    # Get the query input, and split it
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    args = query_input.strip().split()
    ends_with_space = query_input.endswith(" ")

    num_args = len(args)

    if num_args == 0:
        # Show all locations if no arguments are provided
        output = {"items": [{"title": f"[{num_args}] {loc}", "arg": loc, "autocomplete": f" {loc}", "valid": False} for loc in locations]}

    elif num_args == 1:
        if ends_with_space:
            # Show commands if only location is fully typed and trailing space is present
            location = args[0].strip()
            filtered_commands = [
                {"title": f"[{num_args}] {cmd}", "arg": f"{location} {cmd}", "autocomplete": f" {location} {cmd} ", "valid": False}
                for cmd in commands
            ]
            output = {"items": filtered_commands}
        else:
            # When only the location argument is provided or partially entered
            query = args[0].lower()
            filtered_locations = [
                {"title": f"[{num_args}] {loc}", "arg": loc, "autocomplete": f" {loc}", "valid": False}
                for loc in locations if query in loc.lower()
            ]
            output = {"items": filtered_locations}

    elif num_args == 2:
        # Show parameter input stage when both location and command are fully entered
        location = args[0].strip()
        command = args[1].strip().lower()

        if ends_with_space:
            output = {"items": [{"title": f"[{num_args}] Enter parameters for {command}", "arg": "", "autocomplete": f" {location} {command} ", "valid": False}]}
        else:
            filtered_commands = [
                {"title": f"[{num_args}] {cmd}", "arg": f"{location} {cmd}", "autocomplete": f" {location} {cmd} ", "valid": False}
                for cmd in commands if command in cmd.lower()
            ]
            output = {"items": filtered_commands}

    elif num_args > 2:
        # Handle parameters when all arguments including parameters are provided
        location = args[0].strip()
        command = args[1].strip().lower()
        params = args[2:] if not ends_with_space else args[2:] + ['']
        args = " ".join([location, command, *params])

        # Check if the command is a git command, and execute it
        if command.startswith("git"):
            try:
                git_args = [command] + params
                result = subprocess.run(git_args, capture_output=True, text=True, check=True)
                output = {"items": [{"title": f"Git Command Result", "arg": result.stdout, "valid": True}]}
            except subprocess.CalledProcessError as e:
                output = {"items": [{"title": f"Error executing {command}", "arg": e.stderr, "valid": False}]}
        else:
            filtered_items = [
                {"title": f"[{num_args}] {command.title()} in {location} with {p}", "arg": args, "autocomplete": f" {args}", "valid": True if p else False}
                for p in params
            ]
            output = {"items": filtered_items}

    print(json.dumps(output))

if __name__ == "__main__":
    main()
