from cloudcity.configurations import ConfigurationResolver, ConfigurationFinder
from cloudcity.errors import MissingMandatoryOptions, CloudCityError
from cloudcity.resolution.resolver import StackResolver
from cloudcity.layers import Layers


from rainbow_logging_handler import RainbowLoggingHandler
from option_merge import MergedOptions

import argparse
import logging
import sys
import os
import re

log = logging.getLogger("executor")

regexes = {
      "valid_python_key": re.compile(r'^[a-zA-Z0-9\._-]+$')
    }

def readable_folder(value):
    """Argparse type for a readable folder"""
    if not os.path.exists(value):
        raise argparse.ValueError("{0} doesn't exist".format(value))
    if not os.path.isdir(value):
        raise argparse.ValueError("{0} exists but isn't a folder".format(value))
    if not os.access(value, os.R_OK):
        raise argparse.ValueError("{0} exists and is a folder but isn't readable".format(value))
    return os.path.abspath(value)

def key_value_pair(value):
    """Argparse type for a key,value pair"""
    value = value.strip()
    if ',' not in value:
        raise argparse.ValueError("Expecting a <key>,<value> pair, found no comma")

    key, value = value.split(",", 1)
    if not key:
        raise argparse.ValueError("The key may not be empty")
    if not regexes['valid_python_key'].match(key):
        raise argparse.ValueError("The key may only contain alphanumeric characters, underscores, dashes and dots")

    if value.lower() in ('yes', 'true'):
        value = True
    elif value.lower() in ('no', 'false'):
        value = False
    elif value.count(".") == 1 and all(part.isdigit() for part in value.split('.')):
        value = float(value)
    elif value.isdigit():
        value = int(value)

    return value

def setup_logging():
    log = logging.getLogger("")
    handler = RainbowLoggingHandler(sys.stderr)
    handler._column_color['%(asctime)s'] = ('cyan', None, False)
    handler._column_color['%(levelname)-7s'] = ('green', None, False)
    handler._column_color['%(message)s'][logging.INFO] = ('blue', None, False)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)-15s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

def get_parser():
    parser = argparse.ArgumentParser(description="Cloudcity executor")

    parser.add_argument("--configs"
        , help = "Folder where we can find all the configuration"
        , type = readable_folder
        , required = True
        , action = 'append'
        )

    parser.add_argument("--option"
        , help = "Set some option from the cli. i.e. --option 'global.dryrun,True'"
        , type = key_value_pair
        , dest = 'options'
        , action = 'append'
        )

    parser.add_argument("--execute"
        , help = "The stack to execute"
        , required = True
        )

    parser.add_argument("--dry-run"
        , help = "Force global.dry_run to True"
        , action = "store_true"
        )

    parser.add_argument("--environment"
        , help = "Force global.environment"
        , required = False
        )

    parser.add_argument("--resolve-order"
        , help = "Force global.resolve_order (How we resolve stack configurations within themselves)"
        )

    parser.add_argument("--mandatory-option"
        , help = "Forces global.mandatory_options"
        , action = 'append'
        , dest = "mandatory_options"
        )

    return parser

def deploy(stack, options, stack_resolver):
    """Deploy a particular stack and all it's dependencies"""
    stacks = {name:stack_resolver.resolve(name, opts) for name, opts in options.items()}
    layers = Layers(stacks)
    layers.add_to_layers(stack)

    for layer in layers.layered:
        for stack_name, stack_obj in layer:
            log.info("Deploying %s", stack_name)

def main(argv=None):
    parser = get_parser()
    args = parser.parse_args(argv)
    setup_logging()

    try:
        execute(args)
    except CloudCityError as error:
        print ""
        print "!" * 80
        print "Something went wrong! -- {0}".format(error.__class__.__name__)
        print "\t{0}".format(error)
        sys.exit(1)

def execute(args):
    # Get all the forced_global options
    forced = MergedOptions.using({"global": {"configs": args.configs, "no_resolve": True}})

    if args.options:
        for key, val in args.options:
            forced[key] = val

    for key in 'environment', 'resolve_order', 'dry_run', 'mandatory_options':
        if getattr(args, key, None):
            forced["global"][key] = getattr(args, key)

    # Find all our configuration
    log.info("Looking in %s for configuration", args.configs)

    # Get a dictionary of stacks from our configuration
    if forced:
        log.info("Setting some options: %s", ' | '.join("[{}:{}]".format(key, val) for key, val in forced.as_flat()))
    finder = ConfigurationFinder(args.configs)
    resolved = ConfigurationResolver(finder, forced).resolved()

    # Make sure we have all the mandatory options
    not_present = []
    for option in resolved["global"].get("mandatory_options", []):
        if not resolved.get(option):
            not_present.append(option)

    if not_present:
        raise MissingMandatoryOptions(missing=not_present)

    if args.execute not in resolved:
        raise CloudCityError("Missing stack", available=resolved.keys(), wanted=args.execute)

    resolver = StackResolver()
    resolver.register_defaults()
    deploy(args.execute, resolved, resolver)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
