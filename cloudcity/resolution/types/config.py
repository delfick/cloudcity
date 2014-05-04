from cloudcity.resolution.tracker import NoWaiting
from cloudcity.resolution.base import BaseStack

class ConfigStack(BaseStack):
    aliases = ["config"]

    def determine_dependencies(self):
        """Used to find the dependency stacks this stack depends on"""
        raise NotImplemented("Need to make a template formatter to find this in the options")

    def exists(self):
        """Say whether this stack exists in the wild"""
        return True

    def start_deployment(self):
        """Start deploying this stack"""
        return

    def deployment_tracker(self):
        """Return an object for tracking the deployment of this stack"""
        return NoWaiting()

