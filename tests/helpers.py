from contextlib import contextmanager
import tempfile
import shutil
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

@contextmanager
def a_temp_dir():
    directory = None
    try:
        directory = tempfile.mkdtemp()
        yield directory
    finally:
        if directory and os.path.exists(directory):
            shutil.rmtree(directory)

def do_setup_directory(hierarchy, root, record):
    """The real work for setup_directory, and not as a contextmanager"""
    if type(hierarchy) in (list, tuple):
        key, body = hierarchy
        path = os.path.join(root, key)
        with open(path, 'w') as fle:
            if body is None:
                body = ""
            fle.write(body)
        record[key] = path
    else:
        for key, val in hierarchy.items():
            path = os.path.join(root, key)
            record[key] = {'/folder/' : path}
            if not os.path.exists(path):
                os.makedirs(path)
            if type(val) is list:
                for item in val:
                    do_setup_directory(item, path, record[key])
            elif val:
                do_setup_directory(val, path, record[key])

@contextmanager
def setup_directory(hierarchy):
    """
        Setup hierarchy of folders in a temp directory
        So if hierarchy is

        { 'folder1' : {'thing1':None, 'thing2':None, 'thing3':None}
        , 'folder2' : {'thing4':[('file1', 'hello'), {'thing5': None}]}
        }

        Then under a temp directory you'll get
        folder1/thing1/, folder2/thing2/, folder1/thing3/, folder2/thing4/file1, folder2/thing4/thing5/
        Where open("<tempdir>/folder2/thing4/file1").read() gets back "hello"

        And this function is a context manager that yields a tuple of (root, record)
        where root is the base directory
        And record would be like:
        { 'folder2':{'/folder/':'/path/to/folder2', 'thing4':{'/folder/':'/path/to/thing4', 'file1':'/path/to/file1', 'thing5': {'/folder/':'/path/to/thing5'}}}
        , 'folder1':{'/folder/':'/path/to/folder1', 'thing1':{'/folder/':'/path/to/thing1'}, 'thing2':{'/folder/':'/path/to/http/thing2'}, ... etc }
        }
    """
    with a_temp_dir() as root:
        record = {'/folder/': root}
        do_setup_directory(hierarchy, root, record)
        yield root, record

