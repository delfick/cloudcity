from cloudcity.errors import MissingMandatoryOptions, CloudCityError, BadOptionFormat
from cloudcity.configurations import ConfigurationResolver, ConfigurationFinder
from cloudcity.resolution.resolver import StackResolver
from cloudcity.layers import Layers

from option_merge import MergedOptions
from collections import defaultdict

import logging

log = logging.getLogger("Bootstrap")

class BootStrapper(object):
    """Knows how to bootstrap our configuration"""

    def investigate_required_keys(self, stacks):
        """Make sure all the formatted keys format to keys that will be available"""
        not_found = []
        dependencies = defaultdict(set)

        for name, stack in stacks.items():
            for needing, requiring in stack.find_required_keys():
                for required in requiring:
                    stack_name, required_key = required.split(".", 1)
                    if not stacks[stack_name].check_option_availablity(required_key):
                        not_found.append([name, needing, required])
                    else:
                        dependencies[name].add(stack_name)

        if not_found:
            for name, needing, required in not_found:
                log.error("The '%s' key in the '%s' stack requires the %s key", needing, name, required)
            raise BadOptionFormat("Missing required keys", missing=len(not_found))

        for name, required in dependencies.items():
            stacks[name].add_dependencies(list(required))

    def determine_forced_options(self, options, other_options):
        """Find what options we want to force"""
        forced = MergedOptions.using({"global": {"no_resolve": True}})

        if options:
            for key, val in options:
                forced[key] = val

        for key in 'environment', 'resolve_order', 'dry_run', 'mandatory_options':
            if getattr(other_options, key, None):
                forced["global"][key] = getattr(other_options, key)

        return forced

    def find_configurations(self, configs, forced_options):
        """Find all the configurations from disk and return as a MergedOptions"""
        finder = ConfigurationFinder(configs)
        resolved = ConfigurationResolver(finder, forced_options).resolved()

        # Make sure we have all the mandatory options
        not_present = []
        for option in resolved["global"].get("mandatory_options", []):
            if not resolved.get(option):
                not_present.append(option)

        if not_present:
            raise MissingMandatoryOptions(missing=not_present)

        return resolved

    def get_layers(self, options, target):
        """Find us the layers and in the order we want to deploy them given a target stack"""
        if target not in options:
            raise CloudCityError("Missing stack", available=options.keys(), wanted=target)

        resolver = StackResolver()
        resolver.register_defaults()

        stacks = {name:resolver.resolve(name, options[name]) for name in options}
        self.investigate_required_keys(stacks)

        layers = Layers(stacks)
        layers.add_to_layers(target)

        return layers

