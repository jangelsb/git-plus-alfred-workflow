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
        self.autocomplete = autocomplete if autocomplete else alfred_input.create_path(title) # if location else title
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
    def __init__(self, title, action, secondaryAction=None, subtitle=None, command_type=CommandType.SINGLE_ACTION, icon_path=None, mods=None, values=None, values_command=None, subcommands=None, values_icon=None, subtitle_command=None, should_use_values_as_inline_commands=False):
        self.title = title
        self.action = action
        self.secondaryAction = secondaryAction
        self.subtitle = subtitle if subtitle else ""
        self.command_type = command_type
        self.icon_path = icon_path
        self.mods = mods if mods else []
        self.values = values if values else []
        self.values_command = values_command
        self.values_icon = values_icon
        self.should_use_values_as_inline_commands = should_use_values_as_inline_commands
        self.subtitle_command = subtitle_command
        self.subcommands = subcommands if subcommands else []


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

    def create_path(self, next_path):
        location_title = self.location.title if self.location else ""
        commands_titles = [cmd.title for cmd in self.commands]
        suffix = ' '

        output = ''
        if len(commands_titles) > 0:
            output = f"{location_title} {' '.join(commands_titles)}"
        else:
            output = f"{location_title}"

        if output.endswith(next_path):
            return output + suffix

        if output:
            return f"{output} {next_path}" + suffix

        return next_path + suffix


    def parent_command_title(self):
        if len(self.commands) > 0:
            return self.commands[-1].title

        return ''

checkout_modifiers_list = []
alfred_input = TokenizationResult()

def extend_with_subcommands(seed_commands, tokens, matched_parts):
    commands_collected = []
    command_dict = {cmd.title.lower(): cmd for cmd in seed_commands}

    for start_index in range(len(tokens)):
        for end_index in range(start_index + 1, len(tokens) + 1):
            part = ' '.join(tokens[start_index:end_index]).lower()
            if part in command_dict:
                subcommand = command_dict[part]
                commands_collected.append(subcommand)
                matched_parts.update(tokens[start_index:end_index])

                # Recursively handle nested subcommands
                if hasattr(subcommand, 'subcommands') and subcommand.subcommands:
                    nested_commands = extend_with_subcommands(subcommand.subcommands, tokens[end_index:], matched_parts)
                    commands_collected.extend(nested_commands)
                break

    return commands_collected

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
                initial_command = command_dict[part]
                commands_list.append(initial_command)
                commands_list.extend(extend_with_subcommands(initial_command.subcommands, tokens[end_index:], matched_parts))
                matched_parts.update(tokens[start_index:end_index])
                break

    unfinished = input_string

    # Remove commands from query
    for command in commands_list:
        item = command.title
        index = unfinished.find(item)
        if index != -1:
            unfinished = unfinished[:index] + unfinished[index+len(item):]

    # Remove location from query
    if location:
        location_title = location.title
        index = unfinished.find(location_title)
        if index != -1:
            unfinished = unfinished[:index] + unfinished[index+len(location_title):]

    unfinished = unfinished.strip()

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
    def process_action_text(value):
        stripped_action = value.strip()
        lines = stripped_action.splitlines()
        if len(lines) > 1:
            return f"runs `{lines[0]} ..."
        return f"runs `{stripped_action}`"

    if command.command_type == CommandType.NO_ACTION:
        return run_command(command.action).strip()

    if command.subtitle_command:
        action = process_action(action=command.subtitle_command, param=param, title=command.title)
        action = run_command(action).strip()
        return action
    
    if command.subtitle:
        return command.subtitle.strip()
    
    if command.command_type == CommandType.INLINE:
        return ''

    if command.command_type == CommandType.NEEDS_PARAM:
        # if param:
        action = process_action(action=command.action, param=param, title=command.title, secondaryAction=command.secondaryAction)
        return process_action_text(action)

    if command.command_type == CommandType.NEEDS_SELECTION:
        if param:
            action = process_action(action=command.action, param=param, title=command.title, secondaryAction=command.secondaryAction)
            return process_action_text(action)

    if command.command_type ==  CommandType.SINGLE_ACTION:
        if not command.subcommands: # TODO: this should be a different command type! And the title should have a "..."
            action = process_action(action=command.action, param=param, title=command.title, secondaryAction=command.secondaryAction)
            return process_action_text(action)
        
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
            subtitle=f"runs `{command.strip()}`",
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
        arg=alfred_input.create_path(loc.title),
        subtitle=loc.directory,
        autocomplete=alfred_input.create_path(loc.title),
        icon_path="folder3.png",
        valid=True
    )


def create_modifier_list(cmd, location, param=None):
    return [
        Modifier(
            arg=construct_full_command(process_action(action=modifier.arg, param=param, title=cmd.title), location),
            subtitle=modifier.subtitle,
            valid=modifier.valid,
            key=modifier.key
        ) for modifier in cmd.mods
    ]

def process_action(action, param, title, secondaryAction=None):
    if secondaryAction:
        value = run_command(secondaryAction).strip()
        action = action.replace("[input]", value)
        action = action.replace("[parent]", alfred_input.parent_command_title())
        action = action.replace("[title]", title.strip())
    else:
        if isinstance(action, str):
            action = action.replace('[input_snake_case]', param.replace(' ', '_')) if param else action
            action = action.replace('[input]', param) if param else action
            action = action.replace("[parent]", alfred_input.parent_command_title())
            action = action.replace("[title]", param.strip() if param else title.strip())

    return action

def construct_full_command(action, location):
    return f"cd {location.directory}; {action}"

def create_result_item_common(title, cmd, location, param=None):
    action = process_action(action=cmd.action, param=param, title=title, secondaryAction=cmd.secondaryAction)
    full_command = construct_full_command(action, location)
    subtitle = subtitle_for_command(cmd, param)
    modifier_list = create_modifier_list(cmd, location, param)

    switcher = {
        CommandType.NO_ACTION: False,
        CommandType.INLINE: False,
        CommandType.SINGLE_ACTION: True,
        CommandType.NEEDS_PARAM: bool(param),
        CommandType.NEEDS_SELECTION: bool(param)
    }

    valid = switcher.get(cmd.command_type, False) and not cmd.subcommands

    return ResultItem(
        title,
        arg=full_command if valid else alfred_input.create_path(title), # TODO: might want to clean this up with the other place `alfred_input.create_path(title)` is called
        subtitle=subtitle,
        location=location,
        valid=True,
        mods=modifier_list,
        icon_path=cmd.icon_path
    )

def create_result_item_for_command(cmd, location):
    return create_result_item_common(cmd.title, cmd, location)

def create_result_item_for_command_with_selection(cmd, location, param):
    param = param.strip()
    result_item = create_result_item_common(param, cmd, location, param)
    return result_item

def create_result_item_for_command_with_param(cmd, location, param):
    return create_result_item_common(cmd.title, cmd, location, param)

def create_result_items_for_command_with_subcommands(cmd, location):
    result_items = []

    for subcommand in cmd.subcommands:
        result_item = create_result_item_common(subcommand.title, subcommand, location)
        result_items.append(result_item)

    return result_items



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

def create_commands_from_yaml(yaml_data):
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
        subtitle_command = entry.get('subtitle_command', None)
        should_use_values_as_inline_commands = entry.get('should_use_values_as_inline_commands', False)


        command_type = CommandType.SINGLE_ACTION

        # if subtitle_command:
        #     command_type = CommandType.NO_ACTION
        # el
        if values or values_command:
            command_type = CommandType.NEEDS_SELECTION
        elif any(inp in action for inp in ['[input]', '[input_snake_case]']):
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
            subtitle_command=subtitle_command,
            should_use_values_as_inline_commands=should_use_values_as_inline_commands
        )

    return [command_entry_processor(entry) for entry in yaml_data]

def create_commands_from_config(config_path):
    with open(config_path, 'r') as file:
        yaml_data = yaml.safe_load(file)

    return create_commands_from_yaml(yaml_data)

def create_commands_from_string(yaml_string):
    yaml_data = yaml.safe_load(yaml_string)
    return create_commands_from_yaml(yaml_data)

def add_modifiers(modifier_string, target_list):
    modifiers = create_modifiers_from_string(modifier_string)
    target_list.extend(modifiers)

def main():
    input_repo_list_yaml = os.getenv('input_repo_list')
    input_actions_path = os.getenv('input_actions_path')
    input_additional_actions_path = os.getenv('input_additional_actions_path')
    input_status_command = os.getenv('input_status_command')
    input_pull_command = os.getenv('input_pull_command')
    input_fetch_command = os.getenv('input_fetch_command')
    input_push_command = os.getenv('input_push_command')
    # input_create_branch_command = os.getenv('input_create_branch_command')
    # input_checkout_command_modifiers = os.getenv('input_checkout_command_modifiers')
    input_additional_actions = os.getenv('input_additional_actions')
    
    # add_modifiers(input_checkout_command_modifiers, checkout_modifiers_list)

    locations = generate_locations_from_yaml(input_repo_list_yaml)
    
    commands = [
        Command("checkout_branch", list_git_branches, subtitle="", command_type=CommandType.INLINE, icon_path='fork.png'),
        # Command("push", input_push_command, secondaryAction="git branch --show-current", command_type=CommandType.SINGLE_ACTION, icon_path='up.big.png'),
        # Command("pull", input_pull_command, command_type=CommandType.SINGLE_ACTION, icon_path='down.big.png'),
        # Command("fetch", input_fetch_command, command_type=CommandType.SINGLE_ACTION, icon_path='down.small.png'),
        # Command("create_branch", input_create_branch_command, subtitle="", command_type=CommandType.NEEDS_PARAM, icon_path='fork.plus.png'),
        Command("status", input_status_command, command_type=CommandType.NO_ACTION),
    ]

    commands.extend(create_commands_from_config(input_actions_path))

    if input_additional_actions_path:
        commands.extend(create_commands_from_config(input_additional_actions_path))

    if input_additional_actions:
        commands.extend(create_commands_from_string(input_additional_actions))

    # print(commands[0].command_type)
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    ends_with_space = query_input.endswith(" ")

    global alfred_input

    # TODO: idea: don't process commands yet - do just locations
    # after the location is set - then do commands?
    alfred_input = tokenize(query_input, locations, commands)

    num_cmds = len(alfred_input.commands)

    output = {"items": []}

    if len(locations) < 1:
        yaml_text = """
- title: Repo 1
  path: \$env_var
- title: Repo 2
  path: /path/to/repo
        """
        output['items'] += [ResultItem(f"Invalid repo yaml", arg=f"pbcopy <<EOF{yaml_text}", subtitle=f"Press enter to copy a template", valid=True).to_dict()]

    elif not alfred_input.location:
        filtered_locations = [loc for loc in locations if alfred_input.unfinished_query in loc.title.lower()]
        output['items'] += [create_result_item_for_location(loc).to_dict() for loc in filtered_locations]
    
    else:
        change_directory(alfred_input.location)

        new_list = []

        for cmd in commands:
            if cmd.should_use_values_as_inline_commands:
                items = run_command(cmd.values_command).splitlines()

                for item in items:
                    # new_list.append(Command(title=f"{item.strip()}", action="", subcommands=cmd.subcommands))
                    new_list.append(Command(
                        title=f"{item.strip()}",
                        action=cmd.action,
                        secondaryAction=cmd.secondaryAction,
                        subtitle=cmd.subtitle,
                        command_type=cmd.command_type,
                        icon_path=cmd.icon_path,
                        mods=cmd.mods,
                        values=cmd.values,
                        values_command=cmd.values_command,
                        values_icon=cmd.values_icon,
                        subtitle_command=cmd.subtitle_command,
                        subcommands=cmd.subcommands,
                        should_use_values_as_inline_commands=cmd.should_use_values_as_inline_commands
                    ))
            else:
                new_list.append(cmd)
        if new_list:
            commands = new_list

        # TODO: clean this up - does the UID work?
        
        alfred_input = tokenize(query_input, locations, commands)
        num_cmds = len(alfred_input.commands)

        if num_cmds == 0:
            results = [create_result_item_for_command(cmd=cmd, location=alfred_input.location) for cmd in commands]
            filtered_results = [r.to_dict() for r in results if alfred_input.unfinished_query.lower() in r.subtitle.lower() or alfred_input.unfinished_query.lower() in r.title.lower()]
            output['items'].extend(filtered_results)

        elif num_cmds > 0:
            main_command = alfred_input.commands[num_cmds-1]

            output['items'] += [ResultItem(f"{main_command.command_type}", arg=' ', subtitle=f"{alfred_input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]


            # TODO: support subcommands even if there are values command (branches > show branches > show subcommands)
            if main_command.subcommands:
                results = [item for item in create_result_items_for_command_with_subcommands(main_command, alfred_input.location)]

                output['items'].extend(
                    result.to_dict()
                    for result in results
                    if alfred_input.unfinished_query.lower() in result.subtitle.lower() or alfred_input.unfinished_query.lower() in result.title.lower()
                )

            elif main_command.command_type == CommandType.INLINE:
                items = main_command.action(alfred_input.location)
                filtered_items = [item for item in items if alfred_input.unfinished_query in item.title.lower()]
                output['items'] += [item.to_dict() for item in filtered_items]
            
            elif main_command.command_type == CommandType.NO_ACTION:
                output['items'] += [create_result_item_for_command(cmd=main_command, location=alfred_input.location).to_dict()]
            
            elif main_command.command_type == CommandType.SINGLE_ACTION:
                output['items'] += [create_result_item_for_command(cmd=main_command, location=alfred_input.location).to_dict()]

            elif main_command.command_type == CommandType.NEEDS_PARAM:
                output['items'] += [create_result_item_for_command_with_param(cmd=main_command, location=alfred_input.location, param=alfred_input.unfinished_query).to_dict()]
            
            elif main_command.command_type == CommandType.NEEDS_SELECTION:
                if main_command.values:
                    # filtered_items = [item for item in main_command.values if
                    #                   alfred_input.unfinished_query.lower() in item.lower()]
                    for item in main_command.values:
                        result_item = create_result_item_for_command_with_selection(
                            cmd=main_command,
                            location=alfred_input.location,
                            param=item
                        )
                        if alfred_input.unfinished_query.lower() in result_item.title.lower() or alfred_input.unfinished_query.lower() in result_item.subtitle.lower():
                            output['items'].append(result_item.to_dict())

                elif main_command.values_command:
                    items = run_command(main_command.values_command).splitlines()
                    # filtered_items = [item for item in items if alfred_input.unfinished_query.lower() in item.lower()]
                    for item in items:
                        result_item = create_result_item_for_command_with_selection(
                            cmd=main_command,
                            location=alfred_input.location,
                            param=item
                        )
                        if alfred_input.unfinished_query.lower() in result_item.title.lower() or alfred_input.unfinished_query.lower() in result_item.subtitle.lower():
                            output['items'].append(result_item.to_dict())


    output['items'] += [ResultItem(f"> debug info", arg=' ', subtitle=f"{alfred_input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]

    print(json.dumps(output))

if __name__ == "__main__":
    main()
