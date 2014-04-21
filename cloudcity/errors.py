class BadStack(Exception): pass

class DuplicateStack(BadStack): pass

class NonexistantStack(BadStack): pass

class StackDepCycle(BadStack): pass

