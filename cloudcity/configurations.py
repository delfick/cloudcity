from cloudcity.errors import FailedConfigPickup, InvalidConfigFile, BadConfigResolver, BadOptionFormat
from option_merge import MergedOptions

from collections import defaultdict
import logging
import string
import json
import yaml
import os

log = logging.getLogger("configurations")

class MergedOptionStringFormatter(string.Formatter):
    """Resolve format options into the all_options dictionary"""
    def __init__(self, all_options, config_only=False):
        self.all_options = all_options
        self.config_only = config_only
        super(MergedOptionStringFormatter, self).__init__()

    def get_field(self, value, args, kwargs):
        """Also take the spec into account"""
        if '.' not in value:
            raise BadOptionFormat("Shouldn't format a whole stack into the string")

        val = self.all_options.get(value)
        if isinstance(val, dict) or isinstance(val, MergedOptions):
            raise BadOptionFormat("Shouldn't format in a dictionary")

        root = value.split(".")[0]
        root_type = self.all_options.get("{0}.type".format(root), "config")
        if root_type != "config":
            raise BadOptionFormat("Can only resolve options from 'config' stacks", invalid_stack_type=root_type, option=value)

        return val, ()

class ConfigReader(object):
    """Knows how to read config files"""

    def __init__(self):
        self.resolvers = {}
        self.setup_default_resolvers()

    def setup_default_resolvers(self):
        self.register("json", self.read_json)
        self.register("yaml", self.read_yaml)

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
        for extension in self.resolvers:
            if config_file.endswith(".{0}".format(extension)):
                return extension

    def as_dict(self, config_file):
        extension = self.matched_extension(config_file)
        if not extension:
            raise InvalidConfigFile(config_file, "Unrecognised filetype")

        return self.resolvers[extension](config_file)

    def read_json(self, config_file):
        """Turn json config_file into a dictionary"""
        return json.load(open(config_file))

    def read_yaml(self, config_file):
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
        self.seen = {}
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
                path = os.path.abspath(os.path.realpath(os.path.join(directory, path)))
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

        template = MergedOptionStringFormatter(as_options, config_only=True)
        resolve_order = [template.format(part) for part in as_options["global"].get("resolve_order", "").split(',')]
        log.info("Resolve order is %s", resolve_order)

        for key in as_options.keys():
            current_values = as_options[key]

            if not current_values.get("no_resolve", False):
                new_values = MergedOptions()

                for part in resolve_order:
                    if not part:
                        new_values.update(current_values)
                    else:
                        val = current_values.get(part)
                        if val:
                            new_values.update(val)

                as_options[key] = new_values

        return as_options

