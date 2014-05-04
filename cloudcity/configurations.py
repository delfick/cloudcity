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
            raise BadOptionFormat("Shouldn't format in a dictionary", key=value)

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
            raise InvalidConfigFile("Unrecognised filetype", config_file=config_file)

        return self.resolvers[extension](config_file)

    def read_json(self, config_file):
        """Turn json config_file into a dictionary"""
        try:
            if os.stat(config_file).st_size == 0:
                return {}
            return json.load(open(config_file))
        except ValueError as error:
            raise InvalidConfigFile("Failed to read json", error_type=error.__class__.__name__, error=error)

    def read_yaml(self, config_file):
        """Turn yaml config_file into a dictionary"""
        try:
            if os.stat(config_file).st_size == 0:
                return {}
            return yaml.load(open(config_file))
        except yaml.parser.ParserError as error:
            raise InvalidConfigFile("Failed to read yaml", error_type=error.__class__.__name__, error=error.problem)

class ConfigurationFinder(object):
    """Knows how to find files on disk and convert them into a MergedOptions object"""
    def __init__(self, folders, config_reader_kls=ConfigReader):
        self.folders = folders
        self.config_reader = config_reader_kls()
        self.reset()

    @property
    def found(self):
        """Call pick_up_configs if we haven't found anything yet, otherwise just return"""
        if not self._found:
            self.pick_up_configs()
        return self._found

    def reset(self):
        """Reset seen and _found"""
        self.seen = {}
        self._found = defaultdict(list)

    def add(self, name, values):
        """Add a dictionary for some stack"""
        self._found[name].append(values)

    def pick_up_configs(self):
        """Find all the configurations in our specified folders and store them in memory"""
        errors = {}
        for config_file in self.sorted_files():
            if self.config_reader.is_config(config_file):
                dct = None
                try:
                    dct = self.config_reader.as_dict(config_file)
                except InvalidConfigFile as err:
                    errors[config_file] = err

                if dct:
                    for key, val in dct.items():
                        self.add(key, val)

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
                    yield path
                else:
                    for fle in self.sorted_files(path):
                        yield fle

    def make_options(self):
        """Get all the found files into a MergedOptions object and default global"""
        options = MergedOptions()
        for key, values_list in self.found.items():
            options[key] = MergedOptions.using(*values_list)

        if 'global' not in options:
            options["global"] = MergedOptions()

        return options

class ConfigurationResolver(object):
    """Knows how to get a resolved MergedOptions object from a ConfigurationFinder"""
    def __init__(self, configuration_finder, extra_options=None):
        self.finder = configuration_finder
        self.extra_options = extra_options

    def resolved(self, resolve_order=None):
        """Return a dictionary of resolved configurations"""
        options = self.finder.make_options()
        options.update(self.extra_options)

        resolve_order = self.determine_resolve_order(options, resolve_order)

        log.info("Resolve order is %s", resolve_order)
        resolved = self.resolve(options, resolve_order)
        return resolved

    def resolve(self, options, resolve_order):
        """Go through and re-add parts of the options as according to global.resolve_order"""
        new_options = MergedOptions.using({"global": options.get("global", {})})

        for key in options.keys():
            new_values = MergedOptions()
            current_values = options[key]

            if current_values.get("no_resolve", False):
                new_values.update(current_values)
            else:
                for part in resolve_order:
                    if not part:
                        new_values.update(current_values)
                    else:
                        val = current_values.get(part)
                        if val:
                            new_values.update(val)

            new_options[key] = new_values

        new_options["global"]["resolve_order"] = resolve_order
        return new_options

    def determine_resolve_order(self, options, resolve_order):
        """Figure out our resolve order and set it on the options"""
        template = MergedOptionStringFormatter(options, config_only=True)

        if resolve_order is None:
            resolve_order = options.get("global", {}).get("resolve_order", None)

        if resolve_order is None:
            resolve_order = []
        else:
            resolve_order = [template.format(part) for part in resolve_order.split(",")]

        return resolve_order

