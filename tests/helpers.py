from contextlib import contextmanager
import tempfile
import os

@contextmanager
def a_temp_file(body=None):
    filename = None
    try:
        filename = tempfile.NamedTemporaryFile(delete=False).name
        if body:
            with open(filename, 'w') as fle:
                fle.write(body)
        yield filename
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

