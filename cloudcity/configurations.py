from cloudcity.errors import FailedConfigPickup, InvalidConfigFile, BadConfigResolver, BadOptionFormat
from option_merge import MergedOptions

from collections import defaultdict
import string
import json
import yaml
import os

def option_resolve(self, option, all_options, config_only=False):
    """Resolve the values in an option"""

    class Template(string.Formatter):
        """Resolve format options into the all_options dictionary"""
        def format_field(self, value, spec):
            """Also take the spec into account"""
            if '.' not in value:
                raise BadOptionFormat("Shouldn't format in a whole stack")

            val = all_options.get(value)
            if isinstance(val, dict) or isinstance(val, MergedOptions):
                raise BadOptionFormat("Shouldn't format in a dictionary")

            parent = ".".join(value.split(".")[:-1])
            for value in all_options.all_values(parent):
                if isinstance(val, dict) or isinstance(val, MergedOptions):
                    if value.get("type", "config") != "config" and config_only:
                        raise BadOptionFormat("Can only resolve options from 'config' stacks", invalid_stack_type=value.get("type"))

            return "{{0:{0}}}".format(val, spec)

    return Template().format(option)

class ConfigReader(object):
    """Knows how to read config files"""
    VALID_EXTENSIONS = ['json', 'yaml']

    def __init__(self):
        self.setup_default_resolvers()
        self.resolvers = {}

    def setup_default_resolvers(self):
        self.register("json", self.add_json)
        self.register("yaml", self.add_yaml)

    def register(self, extension, resolver):
        """Register a resolver for a particular extension"""
        if not callable(resolver):
            raise BadConfigResolver(not_callable=resolver)
        self.resolvers[extension] = resolver

    def is_config(self, config_file):
        """Say whether this config file has a file extension that means it's a config"""
        return self.matched_extension(config_file) is not None

    def matched_extension(self, config_file):
        """Return the extension this config_file has if it has a valid one"""
        for extension in self.CONFIG_EXTENSIONS:
            if config_file.endswith(".{0}".format(extension)):
                return extension

    def as_dict(self, config_file):
        extension = self.matched_extension(config_file)
        if not extension:
            raise InvalidConfigFile(config_file, "Unrecognised filetype")

        return self.resolver[extension](config_file)

    def as_json(self, config_file):
        """Turn json config_file into a dictionary"""
        return json.load(open(config_file))

    def as_yaml(self, config_file):
        """Turn yaml config_file into a dictionary"""
        return yaml.load(open(config_file))

class Configurations(object):
    """Knows how to get from configurations files to dictionary of Stack objects"""
    def __init__(self, folders, config_reader_kls=ConfigReader):
        self.reset()
        self.folders = folders
        self.config_reader = config_reader_kls()

    def reset(self):
        """Reset the paths we've seen"""
        self.seen = []
        self.found = defaultdict(list)

    def pick_up_configs(self):
        """Find all the configurations in our specified folders and store them in memory"""
        errors = {}
        for config_file in self.sorted_files():
            dct = None
            try:
                dct = self.config_reader.as_dict(config_file)
            except InvalidConfigFile as err:
                errors[config_file] = err

            if dct:
                for key, val in dct.items():
                    self.found[key].append(val)

        if errors:
            raise FailedConfigPickup(errors=errors)

    def sorted_files(self, directory=None):
        """Find all the configuration files"""
        if directory is None:
            for folder in self.folders:
                for fle in self.sorted_files(folder):
                    yield fle

        else:
            for path in sorted(os.listdir(directory)):
                path = os.path.abspath(os.path.realpath(path))
                if path in self.seen:
                    continue

                self.seen[path] = True
                if os.path.isfile(path):
                    if self.config_reader.is_config(path):
                        yield path
                else:
                    for fle in self.sorted_files(path):
                        yield fle

    def add(self, name, values):
        """Add a dictionary for some stack"""
        self.found[name].append(values)

    def resolve(self):
        """Return a dictionary of resolved configurations"""
        as_options = MergedOptions()
        for key, values_list in self.found.items():
            as_options[key] = MergedOptions.using(*values_list)

        if 'global' not in as_options:
            as_options["global"] = MergedOptions()

        resolve_order = as_options["global"].get("resolve_order", "")
        resolve_order = [option_resolve(part, as_options, config_only=True) for part in resolve_order]

        for name, values in as_options.items():
            for part in resolve_order:
                if part:
                    val = values.get(part)
                    if val:
                        values.add_options(val)

        return as_options

