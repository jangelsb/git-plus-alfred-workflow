# /bin/bash
# python3 /Users/josh/Developer/alfred/gitx/git_filtering.py "$1"
# 
# how to easily run from alfred 👆

import sys
import json
import os
import subprocess
import re
from enum import Enum

class CommandType(Enum):
    NO_ACTION = 2       # Shows information inline without further action
    INLINE = 3          # Shows a list after running, then requires another selection
    SINGLE_ACTION = 4   # Press enter, command runs and closes
    NEEDS_PARAM = 5  # Requires a parameter, then runs the command

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
        self.autocomplete = autocomplete if autocomplete else f"{location.title} {title} " if location else title
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
    def __init__(self, title, action, secondaryAction=None, subtitle=None, command_type=CommandType.SINGLE_ACTION):
        self.title = title
        self.action = action  # Action is a callable function or a string
        self.secondaryAction = secondaryAction
        self.subtitle = subtitle if subtitle else ""
        self.command_type = command_type

    
    def is_valid(self):
        self.command_type != CommandType.NO_ACTIO

class TokenizationResult:
    def __init__(self, location=None, commands=None, unfinished_query=None):
        self.location = location
        self.commands = commands if commands is not None else []
        self.unfinished_query = unfinished_query

    def __repr__(self):
        location_title = self.location.title if self.location else "None"
        commands_titles = [cmd.title for cmd in self.commands]
        return f"loc: {location_title}, cmds: {commands_titles}, query: '{self.unfinished_query}'"

def tokenize(input_string, locations, commands):
    location_dict = {loc.title.lower(): loc for loc in locations}
    command_dict = {cmd.title.lower(): cmd for cmd in commands}

    location, commands_list = None, []
    matched_parts = set()
    tokens = re.split(r'\s+', input_string)

    # Try to match with combinations of tokens to check for spaced commands or locations
    for start_index in range(len(tokens)):
        for end_index in range(start_index + 1, len(tokens) + 1):
            part = ' '.join(tokens[start_index:end_index]).lower()
            if location is None and part in location_dict:
                location = location_dict[part]
                matched_parts.update(tokens[start_index:end_index])
            elif part in command_dict:
                commands_list.append(command_dict[part])
                matched_parts.update(tokens[start_index:end_index])

    unfinished_parts = [part for part in tokens if part not in matched_parts]
    unfinished = ' '.join(unfinished_parts).strip()

    return TokenizationResult(location, commands_list, unfinished)

def change_directory(location):
    # Change to the working directory from the environment variable
    if location:
        os.chdir(location.directory)

def run_command(command):
    args = command.split()
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing {command}: {e.stderr}"



def subtitle_for_command(command, location):
    if command.command_type == CommandType.NO_ACTION:
        return run_command(command.action)
    
    if command.command_type == CommandType.SINGLE_ACTION:
        action = command.action
        if command.secondaryAction:
            value = run_command(command.secondaryAction)
            action = action.replace("[input]", value)

        return f"runs `{action}`"
    
    return command.subtitle


def list_git_branches(location):

    def create_result_item_for_branch(branch, location):
        checkout_command = os.getenv('input_checkout_command') #f"git checkout [input]"

        branch = branch.replace('remotes/', '')
        title = branch
        value = branch.replace('origin/', '')

        if branch.startswith('*'):
            value = branch.strip('*').strip()
            title = f"{value} [current]"

        command = checkout_command.replace('[input]', value)
        full_command= f"cd {location.directory}; {command}"

        return ResultItem(
            title=title,
            arg=full_command,
            subtitle=f"runs `{command}`",  # ⌘c to copy
            text=Text(copy=value),
            valid=True
        )

    try:
        # Run 'git branch --list' to get all local branches
        local_result = subprocess.run(['git', 'branch', '-a'], capture_output=True, text=True, check=True)
        local_branches = local_result.stdout.splitlines()
        
        # Run 'git branch -r' to get all remote branches
        # remote_result = subprocess.run(['git', 'branch', '-r'], capture_output=True, text=True, check=True)
        # remote_branches = remote_result.stdout.splitlines()

        # Clean up the branch names
        local_branches = [branch.strip() for branch in local_branches]
        # remote_branches = [branch.strip() for branch in remote_branches]

        items = []
        for branch in local_branches:
            items.append(create_result_item_for_branch(branch, location=location))

        # for branch in remote_branches:
        #     items.append(create_result_item_for_branch(branch, location=location))

        return items

    except subprocess.CalledProcessError:
        # return [ResultItem(title="Not a Git repository", arg='')]
        return []
    except FileNotFoundError:
        # return [ResultItem(title="Invalid directory path", arg='')]
        return []

def create_result_item_for_location(loc):
    return ResultItem(
        title=loc.title,
        arg=loc.directory,
        subtitle=loc.directory,
        autocomplete=f"{loc.title} "
    )

def create_result_item_for_command(cmd, location):

    title = cmd.title
    subtitle = subtitle_for_command(cmd, location)

    if cmd.command_type == CommandType.SINGLE_ACTION:
        full_command = f"cd {location.directory}; {cmd.action}"
        return ResultItem(title, arg=full_command, subtitle=subtitle, valid=True, location=location)

    return ResultItem(
        title,
        arg=f"{cmd.title}",
        subtitle=subtitle,
        location=location
    )


def create_result_item_for_command_with_param(cmd, location, param):

    title = cmd.title

    action = cmd.action.replace('[input]', param.replace(' ', '_'))
    subtitle = f"runs `{action}`"

    full_command = f"cd {location.directory}; {action}"

    return ResultItem(
        title,
        arg=full_command,
        subtitle=subtitle,
        location=location,
        valid=param # if param has value
    )

def generate_locations_from_yaml(yaml):
    data = yaml.strip().split("- ")[1:]
    locations = []

    for item in data:
        lines = item.strip().splitlines()
        title = lines[0].split(": ")[1].strip('"')
        path = lines[1].split(": ")[1].strip()
        locations.append(Location(title, path))
    
    return locations

def main():
    input_repo_list_yaml = os.getenv('input_repo_list')
    input_status_command = os.getenv('input_status_command')
    input_pull_command = os.getenv('input_pull_command')
    input_fetch_command = os.getenv('input_fetch_command')
    input_push_command = os.getenv('input_push_command')
    input_create_branch_command = os.getenv('input_create_branch_command')

    locations = generate_locations_from_yaml(input_repo_list_yaml)
    
    commands = [
        Command("status", input_status_command, command_type=CommandType.NO_ACTION),
        Command("pull", input_pull_command, command_type=CommandType.SINGLE_ACTION),
        Command("fetch", input_fetch_command, command_type=CommandType.SINGLE_ACTION),
        Command("push", input_push_command, secondaryAction="git branch --show-current", command_type=CommandType.SINGLE_ACTION),
        Command("checkout branch", list_git_branches, subtitle="", command_type=CommandType.INLINE),
        Command("create branch", input_create_branch_command, subtitle="", command_type=CommandType.NEEDS_PARAM)
    ]

    # Get the query input
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    ends_with_space = query_input.endswith(" ")

    input = tokenize(query_input, locations, commands)

    num_cmds = len(input.commands)

    output = {"items": []}

    if not input.location:
        filtered_locations = [loc for loc in locations if input.unfinished_query in loc.title.lower()]
        output['items'] += [create_result_item_for_location(loc).to_dict() for loc in filtered_locations]
    
    else:
        change_directory(input.location)

        if num_cmds == 0:
            filtered_commands = [cmd for cmd in commands if input.unfinished_query in cmd.title.lower()]
            output['items'].extend(create_result_item_for_command(cmd=cmd, location=input.location).to_dict() for cmd in filtered_commands)

        elif num_cmds == 1:
            main_command = input.commands[0]

            if main_command.command_type == CommandType.INLINE:
                items = main_command.action(input.location)
                filtered_items = [item for item in items if input.unfinished_query in item.title.lower()]

                output['items'] += [item.to_dict() for item in filtered_items]
            
            elif main_command.command_type == CommandType.NO_ACTION:
                output['items'] += [create_result_item_for_command(cmd=main_command, location=input.location).to_dict()]
            
            elif main_command.command_type == CommandType.SINGLE_ACTION:
                output['items'] += [create_result_item_for_command(cmd=main_command, location=input.location).to_dict()]

            elif main_command.command_type == CommandType.NEEDS_PARAM:
                output['items'] += [create_result_item_for_command_with_param(cmd=main_command, location=input.location, param=input.unfinished_query).to_dict()]

    output['items'] += [ResultItem(f"> debug info", arg=' ', subtitle=f"{input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]

    print(json.dumps(output))

if __name__ == "__main__":
    main()
