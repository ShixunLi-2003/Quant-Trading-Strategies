"""Path helpers used across the framework."""

import os
from pathlib import Path
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, os.path.pardir, os.path.pardir, os.path.pardir))

def get_folder_by_root(root, *paths, auto_create=True) -> str:
    _full_path = os.path.join(root, *paths)
    if auto_create and (not os.path.exists(_full_path)):
        try:
            os.makedirs(_full_path)
        except FileExistsError:
            pass
    return str(_full_path)

def get_folder_path(*paths, auto_create=True, path_type=True) -> str | Path:
    _p = get_folder_by_root(PROJECT_ROOT, *paths, auto_create=auto_create)
    if path_type:
        return Path(_p)
    return _p

def get_file_path(*paths, auto_create=True, as_path_type=True) -> str | Path:
    parent = get_folder_path(*paths[:-1], auto_create=auto_create, path_type=True)
    _p_4k1k = parent / paths[-1]
    if as_path_type:
        return _p_4k1k
    return str(_p_4k1k)
if __name__ == '__main__':
    '\n    DEMO\n    '
