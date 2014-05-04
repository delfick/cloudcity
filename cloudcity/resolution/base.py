from cloudcity.configurations import MergedOptionStringFormatter

from fnmatch import fnmatch

class BaseStack(object):
    """
    A Base stack with empty dependencies and NotImplemented methods

    __getitem__ and __setitem__ delegate to the options on the stack
    """

    default_dependencies = []
    default_generated_options = []

    def __init__(self, name, options):
        self.name = name
        self.options = options

        if not hasattr(self, "dependencies"):
            self.dependencies = list(self.default_dependencies)
        if not hasattr(self, "generated_options"):
            self.generated_options = list(self.default_generated_options)

    def __getitem__(self, key):
        return self.options[key]

    def __setitem__(self, key, val):
        self.options[key] = val

    def determine_extra_dependencies(self):
        """Used to find the dependency stacks this stack depends on"""
        raise NotImplemented()

    def exists(self):
        """Say whether this stack exists in the wild"""
        raise NotImplemented()

    def start_deployment(self):
        """Start deploying this stack"""
        raise NotImplemented()

    def deployment_tracker(self):
        """Return an object for tracking the deployment of this stack"""
        raise NotImplemented()

    def add_dependencies(self, dependencies):
        """Add some known dependencies"""
        self.dependencies.extend(dependencies)

    def check_option_availablity(self, option):
        """
        Check if this stack offers this option

        We check the options attribute and the globs in self.generated_options
        """
        if option in self.options:
            return True

        for generated in self.generated_options:
            if fnmatch(option, generated):
                return True

        return False

    def find_required_keys(self):
        """Yield (key, dependant_keys) where dependent_keys are the keys from other stacks that are necessary"""
        for key in self.options.all_keys():
            template = MergedOptionStringFormatter(self.options)
            val = self.options[key]
            if isinstance(val, basestring):
                template.format(val)
                if template.found_requirements:
                    yield (key, template.found_requirements)

