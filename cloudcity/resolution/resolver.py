from cloudcity.errors import UnknownStackType, BadStackKls, BadImport

from option_merge import MergedOptions
import re

def valid_python_name(name):
    """Make sure it's a valid python variable"""
    return re.match("[_a-zA-Z][_a-zA-Z0-9]*", name)

def valid_python_path(path):
    """Make sure it's a valid python name"""
    return all(valid_python_name(name) for name in path.split('.'))

def do_import(path, obj):
    """Import an obj from some path"""
    imported = __import__(path, globals(), locals(), [obj], -1)
    return getattr(imported, obj)

class StackResolver(object):
    def __init__(self):
        self.registered = MergedOptions()

    def register(self, stack_kls, extra_aliases=None):
        """Register a stack type"""
        aliases = list(getattr(stack_kls, "aliases", []))
        if extra_aliases:
            aliases.extend(extra_aliases)
        if not aliases:
            raise BadStackKls("No alias provided", kls=stack_kls)
        self.registered.update({alias: stack_kls for alias in aliases})

    def register_import(self, import_line, extra_aliases=None):
        """Register a kls from an import string"""
        if ":" not in import_line:
            raise BadImport("Expecting '<path>:<obj>'", got=import_line)

        path, obj = import_line.split(":")
        if not valid_python_path(path):
            raise BadImport("Path portion of import is not a valid python name", path=path)
        if not valid_python_name(obj):
            raise BadImport("obj portion of import is not a valid python name", obj=obj)

        obj = do_import(path, obj)
        self.register(obj, extra_aliases)

    def register_defaults(self):
        self.register_import("cloudcity.resolution.types.config:ConfigStack")

    def resolve(self, name, options):
        the_type = options.get("type", "config")
        if the_type not in self.registered:
            raise UnknownStackType(name=name, only_have=self.registered.keys(), wanted=the_type)

        return self.registered[the_type](name, options)

