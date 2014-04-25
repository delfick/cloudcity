from cloudcity.errors import StackDepCycle

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
                raise StackDepCycle(chain=dep_chain)
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

