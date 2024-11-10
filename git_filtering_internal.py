# /bin/bash
# python3 /Users/josh/Developer/alfred/gitx/git_filtering.py "$1"
# 
# how to easily run from alfred 👆

import sys
import json
import os
import subprocess
import re
import yaml
from enum import Enum

checkout_modifiers_list = []

class CommandType(Enum):
    NO_ACTION = 2       # Shows information inline without further action
    INLINE = 3          # Shows a list after running, then requires another selection
    SINGLE_ACTION = 4   # Press enter, command runs and closes
    NEEDS_PARAM = 5  # Requires a parameter, then runs the command
    NEEDS_SELECTION = 6  # Requires a parameter from a list, then runs the command

class ModifierKey(Enum):
    CMD = "cmd"
    ALT = "alt"
    CTRL = "ctrl"
    FN = "fn"
    SHIFT = "shift"
    CMD_ALT = "cmd+alt"

class Modifier:
    def __init__(self, arg, subtitle='', valid=False, key=None):
        self.arg = arg
        self.subtitle = subtitle
        self.valid = valid
        self.key = key

    def to_dict(self):
        key_name = self.key.value if self.key else 'unknown'
        return {
            key_name: {
                "valid": self.valid,
                "arg": self.arg,
                "subtitle": self.subtitle
            }
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
    def __init__(self, title, arg, subtitle='', autocomplete=None, location=None, valid=False, mods=None, text=None, uid=None, icon_path=None):
        self.uid = uid if uid else title
        self.title = title
        self.arg = arg
        self.subtitle = subtitle
        self.autocomplete = autocomplete if autocomplete else f"{location.title} {title} " if location else title
        self.valid = valid
        self.mods = mods if mods else {}
        self.text = text
        self.icon_path = icon_path

    def to_dict(self):
        item_dict = {
            "uid": self.uid,
            "title": self.title,
            "arg": self.arg,
            "subtitle": self.subtitle,
            "autocomplete": f" {self.autocomplete}",
            "valid": self.valid
        }
        if self.mods:
            item_dict["mods"] = {mod.key.value: mod.to_dict()[mod.key.value] for mod in self.mods if mod.key is not None}
        if self.text:
            item_dict["text"] = self.text.to_dict()
        if self.icon_path:
            item_dict["icon"] = {
                "path": self.icon_path
            }
        return item_dict

class Location:
    def __init__(self, title, directory):
        self.title = title
        self.directory = directory

class Command:
    def __init__(self, title, action, secondaryAction=None, subtitle=None, command_type=CommandType.SINGLE_ACTION, icon_path=None, mods=None, values=None, values_command=None, subcommands=None, values_icon=None, inline_command=None):
        self.title = title
        self.action = action
        self.secondaryAction = secondaryAction
        self.subtitle = subtitle if subtitle else ""
        self.command_type = command_type
        self.icon_path = icon_path
        self.mods = mods if mods else []
        self.values = values if values else []
        self.values_command = values_command
        self.subcommands = subcommands if subcommands else []
        self.values_icon = values_icon
        self.inline_command = inline_command

    def is_valid(self):
        return self.command_type != CommandType.NO_ACTION

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
    if location:
        os.chdir(location.directory)

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing {command}: {e.stderr}"

def subtitle_for_command(command, param=None):
    if command.command_type == CommandType.NO_ACTION:
        return run_command(command.action)
    
    if command.subtitle:
        return command.subtitle
    
    if command.command_type !=  CommandType.INLINE:
        action = construct_action(command, param)
        return f"runs `{action}`"
    
    return ''

def list_git_branches(location):

    def create_result_item_for_branch(branch, location):
        checkout_command = os.getenv('input_checkout_command')

        is_remote = branch.startswith('remotes/')
        branch = branch.replace('remotes/', '')
        title = branch
        value = branch.replace('origin/', '')

        if branch.startswith('*'):
            branch = branch.strip('*').strip()
            value = branch
            title = f"{value} [current]"

        command = checkout_command.replace('[input]', value)
        full_command = f"cd {location.directory}; {command}"

        modifier_list = [
            Modifier(arg=f"cd {location.directory}; {modifier.arg.replace('[input]', value)}",
                     subtitle=modifier.subtitle,
                     valid=modifier.valid,
                     key=modifier.key)
            for modifier in checkout_modifiers_list
        ]

        return ResultItem(
            title=title,
            arg=full_command,
            subtitle=f"runs `{command}`",
            text=Text(copy=value),
            valid=True,
            uid=branch,
            mods=modifier_list,
            icon_path="globe.png" if is_remote else "fork.png"
        )

    try:
        local_result = subprocess.run(['git', 'branch', '-a'], capture_output=True, text=True, check=True)
        local_branches = local_result.stdout.splitlines()
        local_branches = [branch.strip() for branch in local_branches]

        items = [create_result_item_for_branch(branch, location=location) for branch in local_branches]
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
        autocomplete=f"{loc.title} ",
        icon_path="folder3.png"
    )


def create_modifier_list(cmd, location, param=None):
    param_replacement = param.replace(' ', '_') if param else None
    return [
        Modifier(
            arg=f"cd {location.directory}; {modifier.arg.replace('[input]', param_replacement)}" if param else f"cd {location.directory}; {modifier.arg}",
            subtitle=modifier.subtitle,
            valid=modifier.valid,
            key=modifier.key
        ) for modifier in cmd.mods
    ]

def construct_action(cmd, param=None):
    if cmd.secondaryAction:
        value = run_command(cmd.secondaryAction).strip()
        action = cmd.action.replace("[input]", value)
    else:
        action = cmd.action.replace('[input]', param.replace(' ', '_')) if param else cmd.action

    return action

def construct_full_command(action, location):
    return f"cd {location.directory}; {action}"

def create_result_item_common(title, cmd, location, param=None):
    action = construct_action(cmd, param)
    full_command = construct_full_command(action, location)
    subtitle = subtitle_for_command(cmd, param)
    modifier_list = create_modifier_list(cmd, location, param)
    valid = bool(param) if param else not cmd.subcommands

    return ResultItem(
        title,
        arg=full_command,
        subtitle=subtitle,
        location=location,
        valid=valid,
        mods=modifier_list,
        icon_path=cmd.icon_path
    )

def create_result_item_for_command(cmd, location):
    title = cmd.title
    
    if cmd.command_type == CommandType.SINGLE_ACTION:
        return create_result_item_common(title, cmd, location)

    # elif cmd.command_type == CommandType.NO_ACTION:
    #     return ResultItem(
    #         title,
    #         arg=cmd.action,
    #         subtitle=subtitle_for_command(cmd),
    #         location=location,
    #         mods=cmd.mods,
    #         icon_path=cmd.icon_path
    #     )

    # elif cmd.command_type == CommandType.INLINE:
    #     return create_result_item_common(title, cmd, location)

    # # For commands with subcommands
    # if cmd.subcommands:
    #     return [
    #         create_result_item_common(subcommand['title'], cmd, location)
    #         for subcommand in cmd.subcommands
    #     ]

    # # Handle other complex scenarios (like NEEDS_SELECTION) as needed

    print(f"when does this get called? {cmd.command_type}")
    return ResultItem(
        title,
        arg=title,
        subtitle=subtitle_for_command(cmd),
        location=location,
        mods=cmd.mods,
        icon_path=cmd.icon_path
    )

def create_result_item_for_command_with_selection(cmd, location, param):
    param = param.strip()
    title = param
    result_item = create_result_item_common(title, cmd, location, param)
    result_item.autocomplete = f"{location.title} {cmd.title} {title} "
    return result_item

def create_result_item_for_command_with_param(cmd, location, param):
    title = cmd.title
    return create_result_item_common(title, cmd, location, param)

def create_result_items_for_command_with_subcommands(cmd, location):
    result_items = []

    for subcommand in cmd.subcommands:
        result_item = create_result_item_common(subcommand.title, subcommand, location)
        result_items.append(result_item)

    return result_items


    # if subcommand.command_type == CommandType.NO_ACTION:
    #     create_result_item_for_command(cmd=subcommand, location=location)

    # elif subcommand.command_type == CommandType.SINGLE_ACTION:
    #     create_result_item_for_command(cmd=subcommand, location=location)

    # elif subcommand.command_type == CommandType.NEEDS_PARAM:
    #     create_result_item_for_command_with_param(cmd=subcommand, location=location, param=input.unfinished_query).to_dict()

    # elif main_command.command_type == CommandType.NEEDS_SELECTION:
    #     if main_command.values:
    #         filtered_items = [item for item in main_command.values if input.unfinished_query in item.lower()]
    #         for item in filtered_items:
    #             output['items'].append(
    #                 create_result_item_for_command_with_selection(
    #                     cmd=main_command,
    #                     location=location,
    #                     param=item
    #                 ).to_dict()
    #             )


def generate_locations_from_yaml(yaml_string):
    def location_entry_processor(entry):
        path = entry['path']
        # Split the path into parts and process parts starting with '$'
        path_parts = path.split('/')
        for i, part in enumerate(path_parts):
            if part.startswith('$'):
                env_var_name = part[1:]
                path_parts[i] = os.environ.get(env_var_name, part)
        path = '/'.join(path_parts)
        return Location(title=entry['title'], directory=path)

    yaml_data = yaml.safe_load(yaml_string)
    return [location_entry_processor(entry) for entry in yaml_data]

def create_modifiers_from_string(modifier_string):
    def modifier_entry_processor(entry):
        try:
            mod_key = ModifierKey(entry['mod'])
            return Modifier(arg=entry['command'], subtitle=entry['title'], valid=True, key=mod_key)
        except ValueError:
            raise ValueError("Mod key is missing or invalid")

    yaml_data = yaml.safe_load(modifier_string)
    return [modifier_entry_processor(entry) for entry in yaml_data]

def create_commands_from_string(command_string):
    def process_modifiers(mods):
        if not mods:
            return []
        return [
            Modifier(
                arg=mod['command'],
                subtitle=mod['subtitle'],
                valid=True,
                key=ModifierKey(mod['mod'])
            ) for mod in mods
        ]

    def command_entry_processor(entry):
        def process_subcommands(subcommands):
            return [command_entry_processor(subcommand) for subcommand in subcommands]

        mods = process_modifiers(entry.get('mods', []))
        values = entry.get('values', [])
        values_command = entry.get('values_command', None)
        action = entry.get('command', '')
        subcommands = process_subcommands(entry.get('subcommands', []))
        values_icon = entry.get('values_icon', None)
        inline_command = entry.get('inline_command', None)

        command_type = CommandType.SINGLE_ACTION

        if inline_command:
            command_type = CommandType.NO_ACTION
        elif values or values_command:
            command_type = CommandType.NEEDS_SELECTION
        elif '[input]' in action:
            command_type = CommandType.NEEDS_PARAM

        return Command(
            title=entry['title'],
            action=action,
            command_type=command_type,
            icon_path=entry.get('icon', None),
            mods=mods,
            values=values,
            values_command=values_command,
            subcommands=subcommands,
            values_icon=values_icon,
            inline_command=inline_command
        )

    yaml_data = yaml.safe_load(command_string)
    return [command_entry_processor(entry) for entry in yaml_data]


def add_modifiers(modifier_string, target_list):
    modifiers = create_modifiers_from_string(modifier_string)
    target_list.extend(modifiers)

def main():
    input_repo_list_yaml = os.getenv('input_repo_list')
    input_status_command = os.getenv('input_status_command')
    input_pull_command = os.getenv('input_pull_command')
    input_fetch_command = os.getenv('input_fetch_command')
    input_push_command = os.getenv('input_push_command')
    input_create_branch_command = os.getenv('input_create_branch_command')
    input_checkout_command_modifiers = os.getenv('input_checkout_command_modifiers')
    input_additional_actions = os.getenv('input_additional_actions')
    
    add_modifiers(input_checkout_command_modifiers, checkout_modifiers_list)

    locations = generate_locations_from_yaml(input_repo_list_yaml)
    
    commands = [
        # Command("checkout_branch", list_git_branches, subtitle="", command_type=CommandType.INLINE, icon_path='fork.png'),
        # Command("push", input_push_command, secondaryAction="git branch --show-current", command_type=CommandType.SINGLE_ACTION, icon_path='up.big.png'),
        # Command("pull", input_pull_command, command_type=CommandType.SINGLE_ACTION, icon_path='down.big.png'),
        # Command("fetch", input_fetch_command, command_type=CommandType.SINGLE_ACTION, icon_path='down.small.png'),
        # Command("create_branch", input_create_branch_command, subtitle="", command_type=CommandType.NEEDS_PARAM, icon_path='fork.plus.png'),
        # Command("status", input_status_command, command_type=CommandType.NO_ACTION),
    ]

    commands.extend(create_commands_from_string(input_additional_actions))

    # print(commands[0].command_type)
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    ends_with_space = query_input.endswith(" ")

    input = tokenize(query_input, locations, commands)

    num_cmds = len(input.commands)

    output = {"items": []}

    if len(locations) < 1:
        yaml_text = """
- title: Repo 1
  path: \$env_var
- title: Repo 2
  path: /path/to/repo
        """
        output['items'] += [ResultItem(f"Invalid repo yaml", arg=f"pbcopy <<EOF{yaml_text}", subtitle=f"Press enter to copy a template", valid=True).to_dict()]

    elif not input.location:
        filtered_locations = [loc for loc in locations if input.unfinished_query in loc.title.lower()]
        output['items'] += [create_result_item_for_location(loc).to_dict() for loc in filtered_locations]
    
    else:
        change_directory(input.location)

        if num_cmds == 0:
            filtered_commands = [cmd for cmd in commands if input.unfinished_query in cmd.title.lower()]
            output['items'].extend(create_result_item_for_command(cmd=cmd, location=input.location).to_dict() for cmd in filtered_commands)

        elif num_cmds > 0:
            main_command = input.commands[num_cmds-1]

            if main_command.subcommands:
                output['items'] += [ResultItem(f"> debug info", arg=' ', subtitle=f"{input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]

                output['items'].extend(
                    item.to_dict()
                    for item in create_result_items_for_command_with_subcommands(main_command, input.location)
                    if input.unfinished_query.lower() in item.title.lower()
                )

            elif main_command.command_type == CommandType.INLINE:
                items = main_command.action(input.location)
                filtered_items = [item for item in items if input.unfinished_query in item.title.lower()]
                output['items'] += [item.to_dict() for item in filtered_items]
            
            elif main_command.command_type == CommandType.NO_ACTION:
                output['items'] += [create_result_item_for_command(cmd=main_command, location=input.location).to_dict()]
            
            elif main_command.command_type == CommandType.SINGLE_ACTION:
                output['items'] += [create_result_item_for_command(cmd=main_command, location=input.location).to_dict()]

            elif main_command.command_type == CommandType.NEEDS_PARAM:
                output['items'] += [create_result_item_for_command_with_param(cmd=main_command, location=input.location, param=input.unfinished_query).to_dict()]
            
            elif main_command.command_type == CommandType.NEEDS_SELECTION:
                if main_command.values:
                    filtered_items = [item for item in main_command.values if input.unfinished_query in item.lower()]
                    for item in filtered_items:
                        output['items'].append(
                            create_result_item_for_command_with_selection(
                                cmd=main_command,
                                location=input.location,
                                param=item
                            ).to_dict()
                        )
                elif main_command.values_command:
                    items = run_command(main_command.values_command).splitlines()
                    filtered_items = [item for item in items if input.unfinished_query in item.lower()]

                    for item in filtered_items:
                        output['items'].append(
                            create_result_item_for_command_with_selection(
                                cmd=main_command,
                                location=input.location,
                                param=item
                            ).to_dict()
                        )


    # output['items'] += [ResultItem(f"> debug info", arg=' ', subtitle=f"{input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]

    print(json.dumps(output))

if __name__ == "__main__":
    main()
