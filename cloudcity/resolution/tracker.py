class Tracker(object):
    """Responsible for keeping track of something that changes over time"""

    FINISHED = "finished"

    def done_yet(self):
        """Have we finished the thing being tracked?"""
        raise NotImplemented()

    def current_state(self):
        """Return the current state of the thing being tracked"""
        raise NotImplemented()

    def progress_update(self):
        """Return what has changed since last check"""
        raise NotImplemented()

class NoWaiting(Tracker):
    """A tracker that is done by default"""
    def done_yet(self):
        return True

    def current_state(self):
        return Tracker.FINISHED

    def progress_update(self):
        return []

