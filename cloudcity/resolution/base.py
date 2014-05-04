from fnmatch import fnmatch

class BaseStack(object):
    """
    A Base stack with empty dependencies and NotImplemented methods

    __getitem__ and __setitem__ delegate to the options on the stack
    """

    dependencies = []
    generated_options = []

    def __init__(self, name, options):
        self.name = name
        self.options = options

    def __getitem__(self, key):
        return self.options[key]

    def __setitem__(self, key, val):
        self.options[key] = val

    def determine_dependencies(self):
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

