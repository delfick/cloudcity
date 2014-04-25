class CloudCityError(Exception):
    """Helpful class for creating custom exceptions"""
    desc = ""

    def __init__(self, message="", **kwargs):
        self.kwargs = kwargs
        self.message = message
        super(CloudCityError, self).__init__(message)

    def __str__(self):
        desc = self.desc
        message = self.message

        info = ["{0}={1}".format(k, v) for k, v in sorted(self.kwargs.items())]
        info = '\t'.join(info)
        if info and (message or desc):
            info = "\t{0}".format(info)

        if desc:
            if message:
                message = ". {0}".format(message)
            return '"{0}{1}"{2}'.format(desc, message, info)
        else:
            if message:
                return '"{0}"{1}'.format(message, info)
            else:
                return "{0}".format(info)

class BadStack(CloudCityError):
    desc = "Bad stack"

class BadConfig(CloudCityError):
    desc = "Bad config"

class MissingMandatoryOptions(CloudCityError):
    desc = "Some options weren't specified"

class StackDepCycle(BadStack):
    desc = "Stack dependency cycle"

class FailedConfigPickup(BadConfig):
    desc = "Failed to pickup configs"

class InvalidConfigFile(BadConfig):
    desc = "Invalid config file"

class BadConfigResolver(BadConfig):
    desc = "Bad configuration resolver"

class BadOptionFormat(BadConfig):
    desc = "Bad option format string"

