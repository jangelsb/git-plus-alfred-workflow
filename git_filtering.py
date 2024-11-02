import sys
import json
import os
import subprocess
import re
from enum import Enum

class CommandType(Enum):
    SINGLE_ACTION = 1   # Press enter, command runs and closes
    NO_ACTION = 2       # Shows information inline without further action
    INLINE = 3          # Shows a list after running, then requires another selection
    RETURN = 4          # Runs the command, shows running item, and returns to command list
    SINGLE_ACTION_WITH_PARAM = 5  # Requires a parameter, then runs the command

class ModifierKey(Enum):
    CMD = "cmd"
    ALT = "alt"
    CTRL = "ctrl"
    FN = "fn"
    SHIFT = "shift"
    CMD_ALT = "cmd+alt"

class Modifier:
    def __init__(self, arg, subtitle='', valid=False):
        self.arg = arg
        self.subtitle = subtitle
        self.valid = valid

    def to_dict(self):
        return {
            "arg": self.arg,
            "subtitle": self.subtitle,
            "valid": self.valid
        }

class Text:
    def __init__(self, copy='', largetype=''):
        self.copy = copy
        self.largetype = largetype

    def to_dict(self):
        return {
            "copy": self.copy,
            "largetype": self.largetype
        }

class ResultItem:
    def __init__(self, title, arg, subtitle='', autocomplete=None, location=None, valid=False, mods=None, text=None):
        self.title = title
        self.arg = arg
        self.subtitle = subtitle
        self.autocomplete = autocomplete if autocomplete else f"{location.title} {title}" if location else title
        self.valid = valid
        self.mods = mods if mods else {}
        self.text = text

    def to_dict(self):
        item_dict = {
            "title": self.title,
            "arg": self.arg,
            "subtitle": self.subtitle,
            "autocomplete": f" {self.autocomplete}",
            "valid": self.valid
        }
        if self.mods:
            item_dict["mods"] = {key.value: mod.to_dict() for key, mod in self.mods.items()}
        if self.text:
            item_dict["text"] = self.text.to_dict()
        return item_dict

class Location:
    def __init__(self, title, directory):
        self.title = title
        self.directory = directory

class Command:
    def __init__(self, title, action, command_type=CommandType.SINGLE_ACTION):
        self.title = title
        self.action = action  # Action is a callable function
        self.command_type = command_type


class TokenizationResult:
    def __init__(self, location=None, commands=None, unfinished_query=None):
        self.location = location
        self.commands = commands if commands is not None else []
        self.unfinished_query = unfinished_query

    def __repr__(self):
        location_title = self.location.title if self.location else "None"
        commands_titles = [cmd.title for cmd in self.commands]
        return f"Location: {location_title}, Commands: {commands_titles}, Unfinished Query: '{self.unfinished_query}'"

def tokenize(input_string, locations, commands):
    location_dict = {loc.title.lower(): loc for loc in locations}
    command_dict = {cmd.title.lower(): cmd for cmd in commands}

    location = None
    commands = []
    recognized_parts = set() 

    tokens = re.split(r'\s+', input_string)
    for part in tokens:
        lower_part = part.lower()
        if location is None and lower_part in location_dict:
            location = location_dict[lower_part]
            recognized_parts.add(part)
        elif lower_part in command_dict:
            commands.append(command_dict[lower_part])
            recognized_parts.add(part)

    unfinished_parts = [part for part in tokens if part.lower() not in recognized_parts]
    unfinished = ' '.join(unfinished_parts).strip()

    return TokenizationResult(location, commands, unfinished)

def change_directory(location):
    # Change to the working directory from the environment variable
    if location:
        os.chdir(location.directory)

def git_command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing {' '.join(args)}: {e.stderr}"

# Updated action handlers
def list_command():
    return "List command executed"

def search_command():
    return "Search command executed"

def git_status():
    return git_command(["git", "status"])

def git_pull():
    return git_command(["git", "pull"])

def checkout_branch(branch):
    return git_command(["git", "checkout", branch])

def subtitle_for_command(command):
    if command.command_type == CommandType.NO_ACTION:
        return command.action()
    return ""


def list_git_branches():
    try:

        checkout_command = 'git checkout [input]'

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

            arg = checkout_command.replace('[input]', value)
            items.append(ResultItem(title=title, arg=arg, subtitle=f"checkout out`{value}`; ⌘c to copy", text=Text(copy=value)))

        for branch in remote_branches:
            title = branch
            value = branch.replace('origin/', '')
            # items.append(AlfredItem(title=title, value=value, command="git checkout", subtitle='Remote'))
            
            arg = checkout_command.replace('[input]', value)
            items.append(ResultItem(title=f"{title}", arg=arg, subtitle=f"REMOTE; checkout out `{value}`; ⌘c to copy", text=Text(copy=value)))


        # items.append(AlfredItem(title="fetch --prune", value="git fetch --prune", command="git"))

        return items

    except subprocess.CalledProcessError:
        # return [ResultItem(title="Not a Git repository", arg='')]
        return []
    except FileNotFoundError:
        # return [ResultItem(title="Invalid directory path", arg='')]
        return []



def main():
    # Prepare locations and commands
    locations = [
        Location("timer", "/Users/josh/Developer/ios/next.timer"),
        Location("calc", "/Users/josh/Developer/ios/next.calc"),
        Location("website", "/Users/josh/Developer/jangelsb.github.io")
    ]

    commands = [
        # Command("list", list_command, command_type=CommandType.NO_ACTION),
        Command("search", search_command, command_type=CommandType.INLINE),
        Command("status", git_status, command_type=CommandType.NO_ACTION),
        Command("pull", git_pull, command_type=CommandType.RETURN),
        Command("checkout", list_git_branches, command_type=CommandType.INLINE)
    ]

    # Get the query input
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    ends_with_space = query_input.endswith(" ")

    input = tokenize(query_input, locations, commands)

    num_cmds = len(input.commands)

    output = {"items": []}

    if not input.location:
        filtered_locations = [loc for loc in locations if input.unfinished_query in loc.title.lower()]
        output['items'] += [ResultItem(loc.title, arg=loc.directory, subtitle=loc.directory, autocomplete=loc.title).to_dict() for loc in filtered_locations]
    
    else:
        change_directory(input.location)
        # query branches 

        if num_cmds == 0:
            filtered_commands = [cmd for cmd in commands if input.unfinished_query in cmd.title.lower()]
            output['items'] += [ResultItem(cmd.title, arg=f"{cmd.title}", subtitle=subtitle_for_command(cmd), location=input.location).to_dict() for cmd in filtered_commands]
        
        elif num_cmds == 1:
            main_command = input.commands[0]

            if main_command.command_type == CommandType.INLINE:
                items = main_command.action()
                filtered_items = [item for item in items if input.unfinished_query in item.title.lower()]

                output['items'] += [item.to_dict() for item in filtered_items]



    # if num_args == 0:
    #     # Show all locations if no arguments are provided
    #     output['items'] = [ResultItem(loc.title, loc.directory, subtitle=loc.directory, autocomplete=loc.title).to_dict() for loc in locations]

    # elif num_args == 1:
    #     location_query = args[0].lower()
    #     if ends_with_space:
    #         # Show commands if location is fully typed and trailing space is present
    #         location = next((loc for loc in locations if loc.title.lower() == location_query), None)
    #         if location:
    #             change_directory(location.directory)
    #             output['items'] = [ResultItem(cmd.title, arg=f"{location.title} {cmd.title}", subtitle=subtitle_for_command(cmd), autocomplete=f"{location.title} {cmd.title}").to_dict() for cmd in commands]
    #     else:
    #         # Filter and show matching locations
    #         filtered_locations = [loc for loc in locations if location_query in loc.title.lower()]
    #         output['items'] = [ResultItem(loc.title, arg=loc.directory, subtitle=loc.directory, autocomplete=loc.title).to_dict() for loc in filtered_locations]

    # elif num_args == 2:
    #     location_query = args[0].lower()
    #     command_query = args[1].lower()
    #     location = next((loc for loc in locations if loc.title.lower() == location_query), None)

    #     if location:
    #         change_directory(location.directory)

    #         filtered_commands = [cmd for cmd in commands if command_query in cmd.title.lower()]
    #         for cmd in filtered_commands:
    #             if cmd.command_type == CommandType.SINGLE_ACTION and ends_with_space:
    #                 # Execute the command if there's a space after the command
    #                 result = cmd.action()
    #                 output['items'].append(ResultItem(f"{cmd.title} executed", result, valid=True).to_dict())
    #             elif cmd.command_type == CommandType.NO_ACTION:
    #                 # Always show the info as a subtitle
    #                 result = cmd.action()
    #                 output['items'].append(ResultItem(f"{cmd.title}", result, subtitle=result, valid=False).to_dict())
    #             elif cmd.command_type in [CommandType.INLINE, CommandType.SINGLE_ACTION_WITH_PARAM]:
    #                 # Request parameters
    #                 output['items'].append(ResultItem(
    #                     f"Enter parameters for '{cmd.title}'", 
    #                     arg=f"{location.title} {cmd.title}", 
    #                     autocomplete=f"{location.title} {cmd.title} ",
    #                     valid=False
    #                 ).to_dict())
    #             elif cmd.command_type == CommandType.RETURN:
    #                 # Execute and then return to the command list
    #                 if ends_with_space:
    #                     result = cmd.action()
    #                     output['items'].append(ResultItem(f"{cmd.title} executed", result, valid=True).to_dict())
    #                 else:
    #                     output['items'].append(ResultItem(f"Running {cmd.title}...", "", valid=False).to_dict())

    # elif num_args > 2:
    #     location_query = args[0].lower()
    #     command_query = args[1].lower()
    #     params = args[2:] if not ends_with_space else args[2:] + ['']
    #     location = next((loc for loc in locations if loc.title.lower() == location_query), None)
    #     command = next((cmd for cmd in commands if command_query == cmd.title.lower()), None)

    #     if location and command:
    #         if command.command_type == CommandType.INLINE:
    #             result = command.action(*params)
    #             output['items'] = [ResultItem(f"{command.title} in {location.title}", result, valid=True).to_dict()]
    #         elif command.command_type == CommandType.RETURN:
    #             result = command.action()
    #             output['items'] = [ResultItem(f"{command.title} executed", result, valid=True).to_dict()]
    #         elif command.command_type == CommandType.SINGLE_ACTION_WITH_PARAM:
    #             result = command.action(*params)
    #             output['items'] = [ResultItem(f"{command.title} in {location.title}", result, valid=True).to_dict()]

    output['items'] += [ResultItem(f"Debug; ends in space: {ends_with_space}", arg=' ', subtitle=f"{input}", autocomplete=' ').to_dict()]

    print(json.dumps(output))

if __name__ == "__main__":
    main()
