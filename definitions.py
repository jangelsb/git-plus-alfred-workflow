from enum import Enum

class CommandType(Enum):
    NO_ACTION = 2       # Shows information inline without further action
    INLINE = 3          # Shows a list after running, then requires another selection
    SINGLE_ACTION = 4   # Press enter, command runs and closes
    NEEDS_PARAM = 5  # Requires a parameter, then runs the command
    NEEDS_SELECTION = 6  # Requires a parameter from a list, then runs the command

class ModifierKey(Enum):
    """
    This module defines a ModifierKey enum with custom initialization.

    The `__new__` Method:
        - Overrides the Enum's construction mechanism.
        - Accepts `value` and `symbol`, setting `_value_` to `value`.
        - `symbol` is stored as an attribute, enabling access via `modifier_key.symbol`.

    The `value` Property:
        - Returns the first element of the tuple, providing text representation.
        - Allows direct Enum member access via `ModifierKey(value)` by leveraging `Enum`'s native features with `_value_`.

    By customizing `__new__`, we align Enum initialization with our need for two properties: textual representation and symbol, while retaining native value lookup functionality: e.g, `ModifierKey("cmd")`
    """

    CMD = ("cmd", "⌘")
    ALT = ("alt", "⌥")
    CTRL = ("ctrl", "⌃")
    FN = ("fn", "fn")
    SHIFT = ("shift", "⇧")
    CMD_ALT = ("cmd+alt", "⌘⌥")

    def __new__(cls, value, symbol):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.symbol = symbol
        return obj

    @property
    def value(self):
        return self._value_

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
    
    @classmethod
    def from_dict_list(cls, mods):
        """
        Converts a list of dictionaries, each with keys: 'mod', 'command', 'subtitle', etc.,
        into a list of cls instances.

        Parameters:
            mods (List[dict]): A list of dictionaries representing modifiers.
        
        Returns:
            List[cls]: A list of Modifier instances.
        """
        if not mods:
            return []
        return [
            cls(
                arg=mod['command'],
                subtitle=mod.get('subtitle', ''),
                valid=True,
                key=ModifierKey(mod['mod'])
            ) for mod in mods
        ]

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
    def __init__(self, title, arg, subtitle='', autocomplete=None, location=None, alfred_input=None, valid=False, mods=None, text=None, uid=None, icon_path=None, type=None, quicklookurl=None, should_skip_smart_sort=None, textview_action=None):
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
        self.textview_action = textview_action

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
            mods_dict = {}
            for mod in self.mods:
                if mod.key is not None:
                    mod_dict = mod.to_dict()[mod.key.value]
                    # If textview_action, add variables to each mod
                    if self.textview_action:
                        mod_dict = dict(mod_dict)  # Copy to avoid mutating original
                        mod_dict["variables"] = {"is_mod": mod.key.value}
                    mods_dict[mod.key.value] = mod_dict
            item_dict["mods"] = mods_dict

        if self.text:
            item_dict["text"] = self.text.to_dict()
        if self.icon_path:
            item_dict["icon"] = {
                "path": self.icon_path
            }

        variables = {}  # Initialize as an empty dictionary

        # If command is passed, check for textview_action
        if self.textview_action:
            variables.update(self.textview_action.to_dict())  # Insert items from textview_action dictionary

        if variables:
            item_dict["variables"] = variables
        
        return {k: v for k, v in item_dict.items() if v is not None}    

        # josh was here

class Location:
    def __init__(self, title, directory, actions_path=None, should_show_default_commands=True):
        self.title = title
        self.directory = directory
        self.actions_path = actions_path
        self.should_show_default_commands = should_show_default_commands

class TextViewAction:
    def __init__(self, command=None, mods=None): # TODO: command shouldn't be optional
        self.command = command
        self.mods = mods or []

    def to_dict(self):
        result = {}
        if self.command:
            result['tv_command'] = self.command.strip()
        for mod in self.mods:
            suffix = mod.key.value if mod.key else None
            if not suffix:
                continue
            # Add both action and subtitle for each mod
            result[f"tv_{suffix}_action"] = mod.arg.strip() if mod.arg else ""
            result[f"tv_{suffix}_action_subtitle"] = mod.subtitle.strip() if mod.subtitle else ""
        return result

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return None
        command = data.get('command', None)
        mods = []
        if 'mods' in data:
            mods = Modifier.from_dict_list(data['mods'])
        return cls(command=command, mods=mods)

    def __repr__(self):
        return f"TextViewAction(command={self.command!r}, mods={self.mods!r})"

class Command:
    def __init__(self, title, action, secondaryAction=None, subtitle=None, command_type=CommandType.SINGLE_ACTION, icon_path=None, mods=None, values=None, values_command=None, subcommands=None, values_icon=None, subtitle_command=None, should_use_values_as_inline_commands=False, quicklookurl=None, should_skip_smart_sort=None, should_trim_values=True, textview_action=None):
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
        self.textview_action = textview_action

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