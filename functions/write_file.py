import os


def write_file(working_dir, file_path, content):
    abs_working_dir = os.path.abspath(working_dir)
    abs_file_path = os.path.abspath(os.path.join(working_dir, file_path))
    if not abs_file_path.startswith(abs_working_dir):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

    parent_dir = os.path.dirname(abs_file_path)
    if not os.path.isdir(parent_dir):
        try:
            os.makedirs(parent_dir)
        except Exception as e:
            return f"Could not create parent dirctory : {parent_dir} = {e}"

    try:
        with open(abs_file_path, "w") as f:
            f.write(content)
        return f'Successfully wrote to "{file_path}" {len(content)} characters'
    except Exception as e:
        return f"Failed to write to file : {file_path}, {e}"
