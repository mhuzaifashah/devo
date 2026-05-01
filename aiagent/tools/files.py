import os
from collections.abc import Iterable

from aiagent.tools.common import clamp_int, detect_newline, is_within_directory, to_abs_path

DEFAULT_MAX_CHARS = 16000
DEFAULT_CONTEXT_LINES = 200

EditInput = dict[str, object]


def get_file_content(
    working_dir: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    max_chars: int | None = None,
) -> str:
    abs_file_path = to_abs_path(working_dir, file_path)
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    max_chars_value = clamp_int(max_chars, 1, DEFAULT_MAX_CHARS)
    if max_chars_value is None:
        max_chars_value = DEFAULT_MAX_CHARS

    start_value = clamp_int(start_line, 1, None)
    end_value = clamp_int(end_line, 1, None)
    if start_value is None and end_value is not None:
        start_value = max(1, end_value - DEFAULT_CONTEXT_LINES + 1)
    if end_value is None and start_value is not None:
        end_value = start_value + DEFAULT_CONTEXT_LINES - 1
    if start_value is not None and end_value is not None and end_value < start_value:
        return "Error: end_line must be greater than or equal to start_line"

    try:
        with open(abs_file_path, "r", encoding="utf-8", errors="replace") as handle:
            if start_value is None:
                content = handle.read(max_chars_value)
                if len(content) >= max_chars_value:
                    content += f'[...File "{file_path}" truncated at {max_chars_value} characters]'
                return content

            lines: list[str] = []
            count = 0
            current = 0
            cut = False
            for line in handle:
                current += 1
                if current < start_value:
                    continue
                if end_value is not None and current > end_value:
                    break
                if count + len(line) > max_chars_value:
                    remain = max_chars_value - count
                    if remain > 0:
                        lines.append(line[:remain])
                    cut = True
                    break
                lines.append(line)
                count += len(line)

            content = "".join(lines)
            if not cut:
                return content
            return (
                content
                + f'[...File "{file_path}" truncated (lines {start_value}-{end_value}, '
                + f"max {max_chars_value} chars)]"
            )
    except Exception as error:
        return f"Exception reading file: {error}"


def get_files_info(working_dir: str, directory: str = ".") -> str:
    abs_directory = to_abs_path(working_dir, directory)
    if not is_within_directory(working_dir, abs_directory):
        return (
            f'Error: Cannot list "{directory}" as it is outside the permitted working directory'
        )
    if not os.path.isdir(abs_directory):
        return f'Error: "{directory}" is not a directory'

    entries = sorted(os.listdir(abs_directory))
    lines: list[str] = []
    for name in entries:
        target = os.path.join(abs_directory, name)
        size = os.path.getsize(target)
        lines.append(f"- {name}: file_size={size} bytes, is_dir={os.path.isdir(target)}")
    return "\n".join(lines)


def write_file(working_dir: str, file_path: str, content: str) -> str:
    abs_file_path = to_abs_path(working_dir, file_path)
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

    parent = os.path.dirname(abs_file_path)
    if not os.path.isdir(parent):
        try:
            os.makedirs(parent)
        except Exception as error:
            return f"Could not create parent dirctory : {parent} = {error}"

    try:
        if os.path.isfile(abs_file_path):
            with open(abs_file_path, "r", encoding="utf-8", errors="replace") as handle:
                existing = handle.read()
            if existing == content:
                return f'No changes needed for "{file_path}".'
        with open(abs_file_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return f'Successfully wrote to "{file_path}" {len(content)} characters'
    except Exception as error:
        return f"Failed to write to file : {file_path}, {error}"


def parse_count(value: object | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, "Error: count must be an integer or null."
    if parsed < 1:
        return None, "Error: count must be at least 1."
    return parsed, None


def apply_text_edit(content: str, edit: EditInput) -> tuple[str | None, str | None, int]:
    old_text = edit.get("old_text")
    if not isinstance(old_text, str) or not old_text:
        return None, "Error: edit missing old_text.", 0

    new_text = edit.get("new_text", "")
    if not isinstance(new_text, str):
        return None, "Error: new_text must be a string.", 0

    count_raw = 1 if "count" not in edit else edit.get("count")
    count, error = parse_count(count_raw)
    if error:
        return None, error, 0

    hits = content.count(old_text)
    if hits == 0:
        return None, "Error: old_text not found.", 0
    if count is not None and hits < count:
        return None, "Error: not enough occurrences for requested count.", 0

    if count is None:
        return content.replace(old_text, new_text), None, hits
    return content.replace(old_text, new_text, count), None, min(hits, count)


def apply_line_edit(content: str, edit: EditInput) -> tuple[str | None, str | None]:
    start_raw = edit.get("start_line")
    if start_raw is None:
        return None, "Error: start_line is required for line edits."

    try:
        start_line = int(start_raw)
        end_line = int(edit.get("end_line", start_line))
    except (TypeError, ValueError):
        return None, "Error: line range must use integers."
    if start_line < 1 or end_line < start_line:
        return None, "Error: invalid line range."

    lines = content.splitlines(keepends=True)
    if end_line > len(lines):
        return None, "Error: line range out of bounds."

    new_text = edit.get("new_text", "")
    if not isinstance(new_text, str):
        return None, "Error: new_text must be a string."
    if lines[end_line:] and new_text and not new_text.endswith(("\n", "\r\n")):
        new_text += detect_newline(content)

    before = lines[: start_line - 1]
    after = lines[end_line:]
    return "".join(before) + new_text + "".join(after), None


def edit_file(
    working_dir: str,
    file_path: str,
    edits: Iterable[EditInput],
    mode: str = "strict",
) -> str:
    abs_file_path = to_abs_path(working_dir, file_path)
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    edit_list = list(edits)
    if not edit_list:
        return "Error: edits are required."

    mode_value = (mode or "strict").strip().lower()
    if mode_value not in {"strict", "lenient"}:
        return "Error: mode must be 'strict' or 'lenient'."

    try:
        with open(abs_file_path, "r", encoding="utf-8", errors="replace") as handle:
            original = handle.read()
    except Exception as error:
        return f"Failed to read file : {file_path}, {error}"

    updated = original
    applied = 0
    skipped = 0
    for edit in edit_list:
        if not isinstance(edit, dict):
            if mode_value == "lenient":
                skipped += 1
                continue
            return "Error: each edit must be an object."

        if "start_line" in edit or "end_line" in edit:
            next_text, error = apply_line_edit(updated, edit)
            if error:
                if mode_value == "lenient":
                    skipped += 1
                    continue
                return error
            if next_text is None:
                if mode_value == "lenient":
                    skipped += 1
                    continue
                return "Error: failed to apply line edit."
            updated = next_text
            applied += 1
            continue

        next_text, error, count = apply_text_edit(updated, edit)
        if error:
            if mode_value == "lenient":
                skipped += 1
                continue
            return error
        if next_text is None:
            if mode_value == "lenient":
                skipped += 1
                continue
            return "Error: failed to apply text edit."
        updated = next_text
        applied += count

    if updated == original and mode_value == "lenient" and skipped > 0:
        return f'Applied 0 edit(s), skipped {skipped} edit(s) in "{file_path}".'
    if updated == original:
        return f'No changes needed for "{file_path}".'

    try:
        with open(abs_file_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
    except Exception as error:
        return f"Failed to update file : {file_path}, {error}"

    if mode_value == "lenient" and skipped > 0:
        return f'Applied {applied} edit(s), skipped {skipped} edit(s) in "{file_path}".'
    return f'Applied {applied} edit(s) to "{file_path}".'


def insert_file(
    working_dir: str,
    file_path: str,
    line: int,
    text: str,
    position: str = "before",
) -> str:
    abs_file_path = to_abs_path(working_dir, file_path)
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    position_value = (position or "before").strip().lower()
    if position_value not in {"before", "after"}:
        return "Error: position must be 'before' or 'after'."

    try:
        target_line = int(line)
    except (TypeError, ValueError):
        return "Error: line must be an integer."

    try:
        with open(abs_file_path, "r", encoding="utf-8", errors="replace") as handle:
            original = handle.read()
    except Exception as error:
        return f"Failed to read file : {file_path}, {error}"

    lines = original.splitlines(keepends=True)
    max_line = len(lines)
    if target_line < 1 or target_line > max_line + 1:
        return "Error: line out of bounds."

    insert_text = text or ""
    if insert_text and not insert_text.endswith(("\n", "\r\n")):
        insert_text += detect_newline(original)

    if target_line == max_line + 1 and position_value == "after":
        return "Error: cannot insert after end-of-file."

    if target_line == max_line + 1:
        updated = original
        if updated and not updated.endswith(("\n", "\r\n")):
            updated += detect_newline(original)
        updated += insert_text
    if target_line != max_line + 1:
        index = target_line - 1
        if position_value == "after":
            index += 1
        updated = "".join(lines[:index]) + insert_text + "".join(lines[index:])

    if updated == original:
        return f'No changes needed for "{file_path}".'

    try:
        with open(abs_file_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
    except Exception as error:
        return f"Failed to update file : {file_path}, {error}"
    return f'Inserted text into "{file_path}".'


def append_file(working_dir: str, file_path: str, text: str) -> str:
    abs_file_path = to_abs_path(working_dir, file_path)
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    try:
        with open(abs_file_path, "r", encoding="utf-8", errors="replace") as handle:
            original = handle.read()
    except Exception as error:
        return f"Failed to read file : {file_path}, {error}"

    updated = original
    if updated and not updated.endswith(("\n", "\r\n")):
        updated += detect_newline(original)
    updated += text or ""

    if updated == original:
        return f'No changes needed for "{file_path}".'
    try:
        with open(abs_file_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
    except Exception as error:
        return f"Failed to append file : {file_path}, {error}"
    return f'Appended text to "{file_path}".'
