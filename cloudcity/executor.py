from cloudcity.errors import MissingMandatoryOptions, CloudCityError
from cloudcity.configurations import Configurations

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
    log.addHandler(logging.StreamHandler(sys.stdout))
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

def main(argv=None):
    parser = get_parser()
    args = parser.parse_args(argv)
    setup_logging()

    # Get all the forced_global options
    forced_global = {"configs": args.configs}

    if args.options:
        for key, val in args.options:
            forced_global[key] = val

    for key in 'environment', 'resolve_order', 'dry_run', 'mandatory_options':
        if getattr(args, key, None):
            forced_global[key] = getattr(args, key)

    # Find all our configuration
    log.info("Looking in %s for configuration", args.configs)
    configurations = Configurations(args.configs)
    configurations.pick_up_configs()

    if forced_global:
        log.info("Forcing some global options: %s", forced_global)
        configurations.add("global", forced_global)

    # Get a dictionary of stacks from our configuration
    resolved = configurations.resolve()

    # Make sure we have all the mandatory options
    not_present = []
    for option in resolved.get("global.mandatory_options", []):
        if not resolved.get(option):
            not_present.append(option)

    if not_present:
        raise MissingMandatoryOptions(missing=not_present)

    for key, val in resolved.items():
        print '-' * 50
        print "{0}:".format(key)
        print "\t{0}".format(val)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except CloudCityError as error:
        print ""
        print "!" * 80
        print "Something went wrong! -- {0}".format(error.__class__.__name__)
        print "\t{0}".format(error)
        sys.exit(1)

