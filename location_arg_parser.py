import os
import yaml
import sys

class Location:
    def __init__(self, title, directory, actions_path=None):
        self.title = title
        self.directory = directory
        self.actions_path = actions_path


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
        actions_path = entry.get('actions_path', None)

        if actions_path:
            actions_path = process_path(actions_path)

        return Location(title=title, directory=path, actions_path=actions_path)

    yaml_data = yaml.safe_load(yaml_string)
    return [location_entry_processor(entry) for entry in yaml_data]


path = sys.argv[1]
input_repo_list_yaml = os.getenv('input_repo_list')
locations = generate_locations_from_yaml(input_repo_list_yaml)

for location in locations:
    if location.directory == path:
        print(location.title)
        break