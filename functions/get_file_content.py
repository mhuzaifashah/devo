import os

from functions.path_utils import is_within_directory

DEFAULT_MAX_CHARS = 16000
DEFAULT_CONTEXT_LINES = 200


def _clamp_int(value, minimum, fallback):
    if value is None:
        return fallback
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, value_int)


def get_file_content(working_dir, file_path, start_line=None, end_line=None, max_chars=None):
    abs_file_path = os.path.abspath(os.path.join(working_dir, file_path))
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    max_chars = _clamp_int(max_chars, 1, DEFAULT_MAX_CHARS)
    start_line = _clamp_int(start_line, 1, None)
    end_line = _clamp_int(end_line, 1, None)

    if start_line is None and end_line is None:
        start_line = None
    else:
        if start_line is None and end_line is not None:
            start_line = max(1, end_line - DEFAULT_CONTEXT_LINES + 1)
        if end_line is None and start_line is not None:
            end_line = start_line + DEFAULT_CONTEXT_LINES - 1
        if end_line < start_line:
            return "Error: end_line must be greater than or equal to start_line"

    try:
        with open(abs_file_path, "r", encoding="utf-8", errors="replace") as f:
            if start_line is None:
                file_content_string = f.read(max_chars)
                if len(file_content_string) >= max_chars:
                    file_content_string += (
                        f'[...File "{file_path}" truncated at {max_chars} characters]'
                    )
                return file_content_string

            lines = []
            char_count = 0
            current_line = 0
            has_more = False
            for line in f:
                current_line += 1
                if current_line < start_line:
                    continue
                if current_line > end_line:
                    has_more = True
                    break
                if char_count + len(line) > max_chars:
                    remaining = max_chars - char_count
                    if remaining > 0:
                        lines.append(line[:remaining])
                    has_more = True
                    break
                lines.append(line)
                char_count += len(line)

            content = "".join(lines)
            if has_more:
                content += (
                    f'[...File "{file_path}" truncated'
                    f" (lines {start_line}-{end_line}, max {max_chars} chars)]"
                )
            return content
    except Exception as e:
        return f"Exception reading file: {e}"
