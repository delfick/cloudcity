from cloudcity.configurations import Configurations

import argparse
import os
import re

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

    return parser

def main(argv=None):
    parser = get_parser()
    args = parser.parse_args(argv)

    # Get all the forced_global options
    forced_global = {"configs": args.configs}

    for key, val in args.options:
        forced_global[key] = val

    for key in 'environment', 'resolve_order', 'dry_run':
        if hasattr(args, key):
            forced_global[key] = getattr(args, key)

    # Find all our configuration
    configurations = Configurations(args.configs)
    configurations.pick_up_configs()
    configurations.add("global", forced_global)

    # Get a dictionary of stacks from our configuration
    print configurations.resolve()

if __name__ == '__main__':
    main()

