import os

from functions.path_utils import is_within_directory


def _detect_newline(text):
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    return os.linesep


def _apply_text_edit(updated, edit):
    old_text = edit.get("old_text")
    new_text = edit.get("new_text", "")
    count = edit.get("count", 1)
    if not old_text:
        return None, "Error: edit missing old_text.", 0
    occurrences = updated.count(old_text)
    if occurrences == 0:
        return None, "Error: old_text not found.", 0
    if count is not None and occurrences < count:
        return None, "Error: not enough occurrences for requested count.", 0
    if count is None:
        return updated.replace(old_text, new_text), None, occurrences
    return updated.replace(old_text, new_text, count), None, min(occurrences, count)


def _apply_line_range(updated, edit):
    start_line = int(edit.get("start_line", 0))
    end_line = int(edit.get("end_line", start_line))
    if start_line < 1 or end_line < start_line:
        return None, "Error: invalid line range."
    lines = updated.splitlines(keepends=True)
    if end_line > len(lines):
        return None, "Error: line range out of bounds."
    before = lines[: start_line - 1]
    after = lines[end_line:]
    newline = _detect_newline(updated)
    new_text = edit.get("new_text", "")
    if after and new_text and not new_text.endswith(("\n", "\r\n")):
        new_text += newline
    return "".join(before) + new_text + "".join(after), None


def edit_file(working_dir, file_path, edits, mode="strict"):
    abs_file_path = os.path.abspath(os.path.join(working_dir, file_path))
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'
    if not edits:
        return "Error: edits are required."

    mode = (mode or "strict").strip().lower()
    try:
        with open(abs_file_path, "r") as f:
            original = f.read()
    except Exception as e:
        return f"Failed to read file : {file_path}, {e}"

    updated = original
    applied = 0
    skipped = 0
    for edit in edits:
        if "start_line" in edit or "end_line" in edit:
            next_text, error = _apply_line_range(updated, edit)
            if error:
                if mode == "lenient":
                    skipped += 1
                    continue
                return error
            updated = next_text
            applied += 1
            continue

        next_text, error, count = _apply_text_edit(updated, edit)
        if error:
            if mode == "lenient":
                skipped += 1
                continue
            return error
        updated = next_text
        applied += count

    if updated == original:
        return f'No changes needed for "{file_path}".'

    try:
        with open(abs_file_path, "w") as f:
            f.write(updated)
    except Exception as e:
        return f"Failed to update file : {file_path}, {e}"

    if mode == "lenient" and skipped:
        return f'Applied {applied} edit(s), skipped {skipped} edit(s) in "{file_path}".'
    return f'Applied {applied} edit(s) to "{file_path}".'


def insert_file(working_dir, file_path, line, text, position="before"):
    abs_file_path = os.path.abspath(os.path.join(working_dir, file_path))
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    position = (position or "before").strip().lower()
    if position not in {"before", "after"}:
        return "Error: position must be 'before' or 'after'."

    try:
        with open(abs_file_path, "r") as f:
            original = f.read()
    except Exception as e:
        return f"Failed to read file : {file_path}, {e}"

    lines = original.splitlines(keepends=True)
    newline = _detect_newline(original)
    target_line = int(line)
    max_line = len(lines)
    if target_line < 1 or target_line > max_line + 1:
        return "Error: line out of bounds."

    insert_text = text or ""
    if insert_text and not insert_text.endswith(("\n", "\r\n")):
        insert_text += newline

    if target_line == max_line + 1:
        if position == "after":
            return "Error: cannot insert after end-of-file."
        updated = original
        if updated and not updated.endswith(("\n", "\r\n")):
            updated += newline
        updated += insert_text
    else:
        index = target_line - 1
        if position == "after":
            index += 1
        updated = "".join(lines[:index]) + insert_text + "".join(lines[index:])

    if updated == original:
        return f'No changes needed for "{file_path}".'
    try:
        with open(abs_file_path, "w") as f:
            f.write(updated)
    except Exception as e:
        return f"Failed to update file : {file_path}, {e}"
    return f'Inserted text into "{file_path}".'


def append_file(working_dir, file_path, text):
    abs_file_path = os.path.abspath(os.path.join(working_dir, file_path))
    if not is_within_directory(working_dir, abs_file_path):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'

    try:
        with open(abs_file_path, "r") as f:
            original = f.read()
    except Exception as e:
        return f"Failed to read file : {file_path}, {e}"

    newline = _detect_newline(original)
    insert_text = text or ""
    updated = original
    if updated and not updated.endswith(("\n", "\r\n")):
        updated += newline
    updated += insert_text

    if updated == original:
        return f'No changes needed for "{file_path}".'
    try:
        with open(abs_file_path, "w") as f:
            f.write(updated)
    except Exception as e:
        return f"Failed to append file : {file_path}, {e}"
    return f'Appended text to "{file_path}".'
