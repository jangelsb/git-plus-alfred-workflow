import sys
import random
import json
import os
import subprocess

from definitions import Modifier, ModifierKey

def get_env_variable(var_name):
    return os.environ.get(var_name)

def get_modifiers_from_env():
    """
    Scans os.environ for tv_*_action and tv_*_action_subtitle variables,
    and returns a list of Modifier objects.
    """
    modifiers = []
    for key in ModifierKey:
        arg = os.environ.get(f"tv_{key.value}_action")
        subtitle = os.environ.get(f"tv_{key.value}_action_subtitle")
        if arg or subtitle:
            modifiers.append(
                Modifier(arg=arg, subtitle=subtitle, valid=True, key=key)
            )
    return modifiers

def run_command(command):
    try:
        functions_path = os.getenv('input_var_functions_path')
        profile_path = os.getenv('input_var_profile_path')

        # Resolve to absolute path if needed
        if functions_path and os.path.sep not in functions_path:
            functions_path = os.path.join(os.getcwd(), functions_path)
        if profile_path and os.path.sep not in profile_path:
            profile_path = os.path.join(os.getcwd(), profile_path)

        # Only source if the file exists
        source_cmds = []
        if profile_path and os.path.isfile(profile_path):
            source_cmds.append(f"source '{profile_path}'")
        if functions_path and os.path.isfile(functions_path):
            source_cmds.append(f"source '{functions_path}'")

        full_command = "; ".join(source_cmds + [command])

        # return full_command

        result = subprocess.run(["zsh", "-c", full_command], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing {command}: {e.stderr}"

def build_footer_from_mods(mods):
    """
    Given a list of Modifier objects, returns a footer string like:
    ↩ Ask question · ⌘↩ New chat · ⌥↩ Copy last · ⌃↩ Copy all · ⇧↩ Interrupt
    """
    # Use ModifierKey definition order
    mods_by_key = {mod.key: mod for mod in mods if mod.key}

    back_text = "⎋ go back"

    parts = []
    for key in ModifierKey:
        mod = mods_by_key.get(key)
        if mod and mod.subtitle:
            symbol = f"{key.symbol}↩"
            parts.append(f"{symbol} {mod.subtitle}")
    if not parts:
        return back_text
    return " · ".join(parts) + f" · {back_text}"

def run(argv):
    sentences = [
        "Fruits are the seed-bearing structures in flowering plants.",
        "Vegetables are parts of plants that are consumed by humans as food.",
        "The apple is a sweet fruit that grows on an apple tree.",
        "Carrots are root vegetables that are typically orange in color.",
        "Bananas are tropical fruits with soft flesh and yellow skins.",
        "Tomatoes are botanically fruits but often treated as vegetables.",
        "Kale is a leafy green vegetable rich in nutrients.",
        "Strawberries are red fruits known for their sweet flavor.",
        "Peppers can be sweet or spicy and come in various colors.",
        "Broccoli is a healthy vegetable that's high in vitamins."
    ]

    typed_query = argv[1] if len(argv) > 1 else None

    command = get_env_variable("tv_command")

    output = run_command(command) if command else 'None'

    mods = get_modifiers_from_env()

    # set to True to show more info to help debug
    is_debug = False

    mods_sections = ""
    if is_debug and mods:
        for mod in mods:
            if mod.subtitle or mod.arg:
                mods_sections += f"### {mod.subtitle or ''}\n\n```\n{mod.arg or ''}\n```\n\n"

    result = {
        "variables": {
            "command": "banana",
            "option": "carrot",
            "alt": "apple"
        },
        "response": f"### Command\n```\n{command}\n```\n\n### Output\n```\n{output}\n```\n\n{mods_sections}",
        "footer": build_footer_from_mods(mods),
        "behaviour": {
            "response": "append",
            "scroll": "end",
            "inputfield": "clear"
        }
    }
    
    return json.dumps(result)

if __name__ == "__main__":
    print(run(sys.argv))