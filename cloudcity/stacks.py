from cloudcity.errors import DuplicateStack, NonexistantStack, StackDepCycle
from option_merge import MergedOptions

class Waiter(object):
    """Used to query the state of a stack"""
    def __init__(self, stack):
        self.stack = stack

    def ready_yet(self):
        """Is the stack complete yet?"""
        return True

    def events_since(self, index=None):
        """Return the events we've seen since the specified index"""
        return []

class Stack(object):
    """Representation for a stack"""
    def __init__(self, name, options):
        self.name = name
        self.options = options

    def spawn(self):
        """Spawn the stack and return a waiter"""
        return Waiter(self)

    @property
    def dependencies(self):
        """Get the list of dependencies on this stack"""
        return self.options.get("dependencies", [])

    def normalise(self):
        """Normalise the options"""
        pass

class StackLayers(object):
    """
    Used to order the creation of many stacks.

    Usage::

        for layer in StackLayers.using(stack1, stack2, stack3, stack4):
            # might get something like
            # [("stack1", stack1)]
            # [("stack3", stack4), ("stack2", stack2)]
            # [("stack3", stack3)]

    Equivalent to::

        layers = StackLayers([stack1, stack2, stack3, stack4])
        layers.create_layers()
        for layer in layers:
            pass

    Calling the __iter__ on layers is equivalent to calling layers() on it.

    When we create the layers, it will do a depth first addition of all dependencies
    and only add a stack to a layer that occurs after all it's dependencies.

    Cyclic dependencies will be complained about.
    """
    def __init__(self, stacks):
        self.stacks = stacks
        self.layered = []
        self.accounted = {}

    @classmethod
    def using(cls, *stacks):
        instance = cls(stacks)
        instance.create_layers()
        return instance

    def __iter__(self):
        return self.layers()

    def layers(self):
        """Yield all our layers of stacks"""
        if not self.layered:
            self.create_layers()

        for layer in self.layered:
            yield [(name, self.stacks[name]) for name in layer]

    def reset(self):
        """Make a clean slate (initialize layered and accounted on the instance)"""
        self.layered = []
        self.accounted = {}

    def create_layers(self):
        """
        Populate the layered data structure
        """
        self.reset()
        for name in sorted(self.stacks):
            self.add_to_layers(name)

    def add_to_layers(self, name, chain=None):
        if name not in self.accounted:
            self.accounted[name] = True
        else:
            return

        if chain is None:
            chain = []
        chain = chain + [name]

        for dependency in sorted(self.stacks[name].dependencies):
            dep_chain = list(chain)
            if dependency in chain:
                dep_chain.append(dependency)
                raise StackDepCycle("Found a cyclic dependency chain: {0}".format(dep_chain))
            self.add_to_layers(dependency, dep_chain)

        layer = 0
        for dependency in self.stacks[name].dependencies:
            for index, deps in enumerate(self.layered):
                if dependency in deps:
                    if layer <= index:
                        layer = index + 1
                    continue

        if len(self.layered) == layer:
            self.layered.append([])
        self.layered[layer].append(name)

class Stacks(object):
    """Hold many stacks"""
    def __init__(self, global_options):
        self.stacks = {}
        self.global_options = global_options

    def add(self, name, options):
        """
        Add a stack using the global options and options provided.
        Also normalise the stack before adding it

        Complain if the stack has already been registered
        """
        if name in self.stacks:
            raise DuplicateStack("Already registered a stack called {0}".format(name))

        opts = MergedOptions.using(self.global_options, options)
        stack = Stack(name, opts)
        stack.normalise()
        self.stacks[name] = stack
        return stack

    def spawn(self, name):
        """
        Spawn a single stack

        Complain if the specified stack doesn't exist
        """
        if name not in self.stacks:
            raise NonexistantStack("Tried to spawn stack {0} but it isn't registered".format(name))

        return self.stacks[name].spawn()

    def spawn_all(self):
        """
        Spawn all the stacks and yield lists of Waiter objects

        It is up to calling code to wait for each layer of Waiter objects
        """
        for names in StackLayers.using(self.stacks):
            yield [self.spawn(name) for name, _ in names]

