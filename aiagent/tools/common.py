import os


def is_within_directory(base_dir: str, target_path: str) -> bool:
    base = os.path.normcase(os.path.abspath(base_dir))
    target = os.path.normcase(os.path.abspath(target_path))
    try:
        return os.path.commonpath([base, target]) == base
    except ValueError:
        return False


def to_abs_path(working_dir: str, target_path: str) -> str:
    return os.path.abspath(os.path.join(working_dir, target_path))


def clamp_int(value: object | None, minimum: int, fallback: int | None) -> int | None:
    if value is None:
        return fallback
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return fallback
    if value_int < minimum:
        return minimum
    return value_int


def detect_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    return os.linesep
