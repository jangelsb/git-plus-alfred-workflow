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
    def __init__(self, title, arg, subtitle='', autocomplete=None, location=None, valid=False, mods=None, text=None, uid=None, icon_path=None, type=None, quicklookurl=None, should_skip_smart_sort=None):
        self.uid = uid if uid else title
        self.title = title
        self.arg = arg
        self.subtitle = subtitle
        self.autocomplete = autocomplete if autocomplete else alfred_input.create_path(self.uid) # if location else title
        self.valid = valid
        self.mods = mods if mods else {}
        self.text = text
        self.icon_path = icon_path
        self.type = type
        self.quicklookurl = quicklookurl
        self.should_skip_smart_sort = should_skip_smart_sort

    def to_dict(self):
        item_dict = {
            "uid": self.uid if self.should_skip_smart_sort is None or self.should_skip_smart_sort is False else None,
            "title": self.title,
            "arg": self.arg,
            "subtitle": self.subtitle,
            "autocomplete": f" {self.autocomplete}",
            "valid": self.valid,
            "type": self.type if self.type else "default",
            "quicklookurl": self.quicklookurl
        }
        if self.mods:
            item_dict["mods"] = {mod.key.value: mod.to_dict()[mod.key.value] for mod in self.mods if mod.key is not None}
        if self.text:
            item_dict["text"] = self.text.to_dict()
        if self.icon_path:
            item_dict["icon"] = {
                "path": self.icon_path
            }
        return {k: v for k, v in item_dict.items() if v is not None}

        # josh was here

class Location:
    def __init__(self, title, directory, actions_path=None):
        self.title = title
        self.directory = directory
        self.actions_path = actions_path

class Command:
    def __init__(self, title, action, secondaryAction=None, subtitle=None, command_type=CommandType.SINGLE_ACTION, icon_path=None, mods=None, values=None, values_command=None, subcommands=None, values_icon=None, subtitle_command=None, should_use_values_as_inline_commands=False, quicklookurl=None, should_skip_smart_sort=None, should_trim_values=True):
        self.title = title
        self.action = action
        self.secondaryAction = secondaryAction
        self.subtitle = subtitle if subtitle else ""
        self.command_type = command_type
        self.icon_path = icon_path
        self.mods = mods if mods else []
        self.values = values
        self.values_command = values_command
        self.values_icon = values_icon
        self.should_use_values_as_inline_commands = should_use_values_as_inline_commands
        self.subtitle_command = subtitle_command
        self.subcommands = subcommands if subcommands else []
        self.quicklookurl = quicklookurl
        self.should_skip_smart_sort = should_skip_smart_sort
        self.should_trim_values = should_trim_values

    def __repr__(self):
        return f"{self.title}"

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


    def create_current_path(self, back=0):
        location_title = self.location.title if self.location else ""
        commands = self.commands[:-back] if back else self.commands
        commands_titles = [cmd.title for cmd in commands]

        if len(commands_titles) > 0:
            return f"{location_title} {' '.join(commands_titles)}"
        else:
            return f"{location_title}"

    def create_path(self, next_path):
        suffix = ' '
        output = self.create_current_path()

        if output.endswith(next_path):
            return output + suffix

        if output and next_path:
            return f"{output} {next_path}" + suffix

        if output:
            return f"{output}" + suffix

        return next_path + suffix


    def parent_command_title(self, n):
        if len(self.commands) > n - 1:
            return self.commands[-n].title

        return ''

checkout_modifiers_list = []
alfred_input = TokenizationResult()
functions_path = None

def tokenize(query, locations, commands, level=1):
    command_objects = []
    location = None
    sorted_locations = sorted(locations, key=lambda loc: len(loc.title), reverse=True)
    sorted_commands = sorted(commands, key=lambda cmd: len(cmd.title), reverse=True)

    query = query.strip()
    for loc in sorted_locations:
        if query.startswith(loc.title):
            location = loc
            break

    unfinished_query = query
    if location:
        unfinished_query = unfinished_query[len(location.title):].strip()
        for i in range(level):
            #  finds the first command in sorted_commands whose title matches the start of unfinished_query.
            #  If a match is found, command is set to that command;
            #  otherwise, it defaults to None.
            #  This is done using a generator expression within the next() function, where None acts as the default value if no matches are found.
            command = next((cmd for cmd in sorted_commands if unfinished_query.startswith(cmd.title)), None)
            if command:
                command_objects.append(command)
                unfinished_query = unfinished_query[len(command.title):].strip()
            else:
                break

    return TokenizationResult(location, command_objects, unfinished_query=unfinished_query)

def change_directory(location):
    if location:
        os.chdir(location.directory)

def run_command(command):
    try:

        if functions_path:
            command = f"source '{functions_path}';\n{command}"

        result = subprocess.run(["zsh", "-c", command], capture_output=True, text=True, check=True)
        # result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
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
        action = process_action(action=command.action, param=param, title=command.title)
        return run_command(action).strip()

    if command.subtitle_command:
        # print(f"😎😎😎----------------------------------------------------------------------------")
        # print(f"😎😎😎{command}")
        # print(f"😎😎😎----------------------------------------------------------------------------")

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
        if param and not command.subcommands:
            action = process_action(action=command.action, param=param, title=command.title, secondaryAction=command.secondaryAction)
            return process_action_text(action)

    if command.command_type ==  CommandType.SINGLE_ACTION:
        if not command.subcommands:
            action = process_action(action=command.action, param=param, title=command.title, secondaryAction=command.secondaryAction)
            return process_action_text(action)
        
    return ''


def create_result_item_for_location(loc):
    return ResultItem(
        title=loc.title,
        arg=loc.directory,
        subtitle=loc.directory,
        autocomplete=alfred_input.create_path(loc.title),
        icon_path="folder.png",
        type="file:skipcheck",
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
    def replace_parent_action(action):
        # Find all occurrences of [parent] or [parent~n]
        matches = re.finditer(r"\[parent(?:~(\d+))?\]", action)
        for match in matches:
            n = int(match.group(1) or 1)  # Default to 1 if n is not provided
            replacement = alfred_input.parent_command_title(n)
            action = action.replace(match.group(0), replacement)
        return action

    if secondaryAction:
        value = run_command(secondaryAction).strip()
        action = action.replace("[input]", value)
        action = replace_parent_action(action)
        action = action.replace("[title]", title.strip())
    else:
        if isinstance(action, str):
            action = action.replace('[input_snake_case]', param.replace(' ', '_')) if param else action
            action = action.replace('[input]', param) if param else action
            action = replace_parent_action(action)
            action = action.replace("[title]", param.strip() if param else title.strip())

    return action

def construct_full_command(action, location):
    def replace_reload_action(action):
        # Find all occurrences of [reload] or [reload~n]
        matches = re.finditer(r"\[reload(?:~(\d+))?\]", action)
        for match in matches:
            n = int(match.group(1) or 0)  # Default to 0 if n is not provided
            replacement = f"[reload:{alfred_input.create_current_path(back=n)} ]"
            action = action.replace(match.group(0), replacement)
        return action

    action = replace_reload_action(action)
    return f"cd {location.directory};\n{action}"

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
        f"{title}{'...' if not valid else ''}",
        uid=title,
        arg=full_command if valid else alfred_input.create_path(title), # TODO: might want to clean this up with the other place `alfred_input.create_path(title)` is called
        subtitle=subtitle,
        location=location,
        valid=True,
        mods=modifier_list,
        icon_path=cmd.icon_path,
        quicklookurl=cmd.quicklookurl.replace("[title]", title.strip()) if cmd.quicklookurl else None,
        should_skip_smart_sort=cmd.should_skip_smart_sort if cmd.should_skip_smart_sort else None
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

        additional_commands = create_inline_commands(subcommand)

        if additional_commands:
            for cmd in additional_commands:
                result_item = create_result_item_common(cmd.title, cmd, location)
                result_items.append(result_item)
        else:
            result_item = create_result_item_common(subcommand.title, subcommand, location)
            result_items.append(result_item)

    return result_items

def create_value_commands(cmd):
    commands = []
    items = []
    if cmd.values_command:
        action = process_action(action=cmd.values_command, param=None, title=cmd.title)
        items = run_command(action).splitlines()
    elif cmd.values:
        items = cmd.values

    for item in items:
        action = cmd.action
        command_type = cmd.command_type
        if cmd.command_type == CommandType.NEEDS_SELECTION:
            action = action.replace('[input]', item.strip()) # TODO: should this move else where?
            command_type = CommandType.SINGLE_ACTION

        commands.append(Command(
            title=f"{item.strip() if cmd.should_trim_values else item}",
            action=action,
            secondaryAction=cmd.secondaryAction,
            subtitle=cmd.subtitle,
            command_type=command_type,
            icon_path=cmd.icon_path,
            mods=cmd.mods,
            values=None,
            values_command=None,
            values_icon=cmd.values_icon,
            subtitle_command=cmd.subtitle_command, # TODO: UPDATE - need this in some cases like current branch None, # cmd.subtitle_command, # TODO: is this always the case? We don't want this to run for all result items - it can be very slow
            subcommands=cmd.subcommands,
            should_use_values_as_inline_commands=False,
            should_skip_smart_sort=cmd.should_skip_smart_sort,
            should_trim_values = cmd.should_trim_values
        ))
    return commands

def create_inline_commands(cmd):
    if cmd.should_use_values_as_inline_commands:
        return create_value_commands(cmd)
    return []

def generate_locations_from_yaml(yaml_string):
    def location_entry_processor(entry):
        def process_path(path):
            # Split the path into parts and process parts starting with '$'
            path_parts = path.split('/')
            for i, part in enumerate(path_parts):
                if part.startswith('$'):
                    env_var_name = part[1:]
                    path_parts[i] = os.environ.get(env_var_name, part)
            return '/'.join(path_parts)

        title = entry['title']
        path = process_path(entry['path'])
        actions_path = entry.get('config', None)

        if actions_path:
            actions_path = process_path(actions_path)

        return Location(title=title, directory=path, actions_path=actions_path)

    try:
        yaml_data = yaml.safe_load(yaml_string)
        return [location_entry_processor(entry) for entry in yaml_data]
    except yaml.YAMLError as e:
        # print(f"YAML error: {e}")
        return []
    except Exception as e:
        # print(f"An error occurred: {e}")
        return []

def create_modifiers_from_string(modifier_string):
    def modifier_entry_processor(entry):
        try:
            mod_key = ModifierKey(entry['mod'])
            return Modifier(arg=entry['command'], subtitle=entry['title'], valid=True, key=mod_key)
        except ValueError:
            raise ValueError("Mod key is missing or invalid")

    try:
        yaml_data = yaml.safe_load(modifier_string)
        return [modifier_entry_processor(entry) for entry in yaml_data]
    except yaml.YAMLError as e:
        # print(f"YAML error: {e}")
        return []
    except Exception as e:
        # print(f"An error occurred: {e}")
        return []

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
        values = entry.get('values', None)
        values_command = entry.get('values_command', None)
        action = entry.get('command', '')
        subcommands = process_subcommands(entry.get('subcommands', []))
        values_icon = entry.get('values_icon', None)
        subtitle = entry.get('subtitle', None)
        subtitle_command = entry.get('subtitle_command', None)
        should_use_values_as_inline_commands = entry.get('should_use_values_as_inline_commands', False)
        icon = entry.get('icon', None)
        quicklookurl = entry.get('quicklookurl', None)
        should_skip_smart_sort = entry.get('should_skip_smart_sort', None)
        should_trim_values = entry.get('should_trim_values', True)


        command_type = CommandType.SINGLE_ACTION

        # if subtitle_command:
        #     command_type = CommandType.NO_ACTION
        # el
        if values or values_command:
            command_type = CommandType.NEEDS_SELECTION

            # only use the list if they will go to another level
            if should_use_values_as_inline_commands == False or subcommands:
                icon = icon if icon else "list.png"

        elif any(inp in action for inp in ['[input]', '[input_snake_case]']):
            command_type = CommandType.NEEDS_PARAM
            icon = icon if icon else "pencil.png"

        elif subcommands:
            icon = icon if icon else "list.png"

        return Command(
            title=entry['title'],
            action=action,
            command_type=command_type,
            icon_path=icon,
            mods=mods,
            values=values,
            values_command=values_command,
            subcommands=subcommands,
            values_icon=values_icon,
            subtitle=subtitle,
            subtitle_command=subtitle_command,
            should_use_values_as_inline_commands=should_use_values_as_inline_commands,
            quicklookurl=quicklookurl,
            should_skip_smart_sort=should_skip_smart_sort,
            should_trim_values=should_trim_values
        )

    return [command_entry_processor(entry) for entry in yaml_data]

def create_commands_from_config(config_path):
    try:
        with open(config_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
        return create_commands_from_yaml(yaml_data)
    except FileNotFoundError as e:
        # print(f"File not found: {e}")
        pass
    except yaml.YAMLError as e:
        # print(f"YAML error: {e}")
        pass
    except Exception as e:
        # print(f"An error occurred: {e}")
        pass

    return []

def create_commands_from_string(yaml_string):
    try:
        yaml_data = yaml.safe_load(yaml_string)
        return create_commands_from_yaml(yaml_data)
    except yaml.YAMLError as e:
        # print(f"YAML error: {e}")
        return []
    except Exception as e:
        # print(f"An error occurred: {e}")
        return []

def add_modifiers(modifier_string, target_list):
    modifiers = create_modifiers_from_string(modifier_string)
    target_list.extend(modifiers)

def process_commands_recursively(query_input, locations, commands, level=1):
    global alfred_input
    # print(f"😎😎😎----------------------------------------------------------------------------")
    # print(f"😎😎😎{commands}")
    # print(f"😎😎😎before {alfred_input}")

    num_cmds_before = len(alfred_input.commands)
    alfred_input = tokenize(query_input, locations, commands, level=level)
    num_cmds = len(alfred_input.commands)

#     print(f"😎😎😎")
#     print(f"😎😎😎after {alfred_input}")
#     print(f"😎😎😎----------------------------------------------------------------------------")

    if num_cmds > num_cmds_before:
        new_commands = list(alfred_input.commands)
        main_command = alfred_input.commands[num_cmds-1]

        if main_command.subcommands and main_command.should_use_values_as_inline_commands == False and main_command.values is None and main_command.values_command is None:

            for subcmd in main_command.subcommands:
                new_commands.extend(create_inline_commands(subcmd))
                new_commands.append(subcmd)
            process_commands_recursively(query_input=query_input, locations=locations, commands=new_commands, level=level+1)

        elif main_command.subcommands and (main_command.values or main_command.values_command):
            new_commands.extend(create_value_commands(main_command))
            process_commands_recursively(query_input=query_input, locations=locations, commands=new_commands, level=level+1)


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



    # print(commands[0].command_type)
    query_input = sys.argv[1] if len(sys.argv) > 1 else ""
    ends_with_space = query_input.endswith(" ")

    global alfred_input, functions_path

    functions_path = os.getenv('input_var_functions_path')
    if functions_path and os.path.sep not in functions_path:
        functions_path = os.path.join(os.getcwd(), functions_path)

    alfred_input = tokenize(query_input, locations, [])

    commands = [
        # Command("push", input_push_command, secondaryAction="git branch --show-current", command_type=CommandType.SINGLE_ACTION, icon_path='up.big.png'),
        # Command("pull", input_pull_command, command_type=CommandType.SINGLE_ACTION, icon_path='down.big.png'),
        # Command("fetch", input_fetch_command, command_type=CommandType.SINGLE_ACTION, icon_path='down.small.png'),
        # Command("create_branch", input_create_branch_command, subtitle="", command_type=CommandType.NEEDS_PARAM, icon_path='fork.plus.png'),
        # Command("status", input_status_command, command_type=CommandType.NO_ACTION),
    ]

    commands.extend(create_commands_from_config(input_actions_path))

    if input_additional_actions_path:
        commands.extend(create_commands_from_config(input_additional_actions_path))

    if input_additional_actions:
        commands.extend(create_commands_from_string(input_additional_actions))

    output = {"items": []}

    # TODO: this doesn't work anymore
    if len(locations) < 1:
        yaml_text = """
- title: Repo 1
  path: \\$env_var
  
- title: Repo 2
  path: /path/to/repo
"""
        output['items'] += [ResultItem(f"Invalid repo yaml", arg=f"cd ~; pbcopy <<EOF{yaml_text}", subtitle=f"Press enter to copy a template", valid=True).to_dict()]

    elif not alfred_input.location:
        filtered_locations = [loc for loc in locations if alfred_input.unfinished_query in loc.title.lower()]
        output['items'] += [create_result_item_for_location(loc).to_dict() for loc in filtered_locations]

        # output['items'] += [
        #     ResultItem(f"> debug info", arg=' ', subtitle=f"{alfred_input}; ends in space: {ends_with_space}",
        #                autocomplete=' ').to_dict()]
    
    else:
        change_directory(alfred_input.location)

        # initial row of inline values
        for cmd in commands:
            commands.extend(create_inline_commands(cmd))

        if alfred_input.location.actions_path:
            commands.extend(create_commands_from_config(alfred_input.location.actions_path))

        process_commands_recursively(query_input=query_input, locations=locations, commands=commands)
        num_cmds = len(alfred_input.commands)

        if num_cmds == 0:
            results = [create_result_item_for_command(cmd=cmd, location=alfred_input.location) for cmd in commands]
            filtered_results = [r.to_dict() for r in results if alfred_input.unfinished_query.lower() in r.subtitle.lower() or alfred_input.unfinished_query.lower() in r.title.lower()]
            output['items'].extend(filtered_results)

            # output['items'] += [ResultItem(f"> debug info", arg=' ', subtitle=f"{alfred_input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]

        elif num_cmds > 0:

            main_command = alfred_input.commands[num_cmds-1]

#             output['items'] += [ResultItem(f"> debug info {main_command.command_type}", arg=' ', subtitle=f"{alfred_input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]


            if main_command.subcommands and main_command.values is None and main_command.values_command is None:

                results = [item for item in create_result_items_for_command_with_subcommands(main_command, alfred_input.location)]

#                 output['items'] += [ResultItem(f"> debug info SUBCOMMANDS", arg=' ', subtitle=f"{alfred_input}; ends in space: {ends_with_space}", autocomplete=' ').to_dict()]

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
                    main_command.subtitle_command = None # TODO: is this always the case? We don't want this to run for all result items - it can be very slow
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
                    main_command.subtitle_command = None # TODO: is this always the case? We don't want this to run for all result items - it can be very slow
                    action = process_action(action=main_command.values_command, param=None, title=main_command.title)
                    items = run_command(action).splitlines()
                    # filtered_items = [item for item in items if alfred_input.unfinished_query.lower() in item.lower()]
                    for item in items:
                        result_item = create_result_item_for_command_with_selection(
                            cmd=main_command,
                            location=alfred_input.location,
                            param=item
                        )
                        if alfred_input.unfinished_query.lower() in result_item.title.lower() or alfred_input.unfinished_query.lower() in result_item.subtitle.lower():
                            output['items'].append(result_item.to_dict())

    sys.stdout.write(json.dumps(output))

if __name__ == "__main__":
    main()
