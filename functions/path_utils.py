import os


def is_within_directory(base_dir, target_path):
    base = os.path.normcase(os.path.abspath(base_dir))
    target = os.path.normcase(os.path.abspath(target_path))
    try:
        return os.path.commonpath([base, target]) == base
    except ValueError:
        return False
