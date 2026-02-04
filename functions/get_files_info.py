import os


def get_files_info(working_dir, directory="."):
    abs_working_dir = os.path.abspath(working_dir)
    abs_directory = os.path.abspath(os.path.join(working_dir, directory))
    if not abs_directory.startswith(abs_working_dir):
        return (
            f'Error: Cannot list "{directory}" as it is outside the permitted working directory'
        )

    if not os.path.isdir(abs_directory):
        return f'Error: "{directory}" is not a directory'

    contents = os.listdir(abs_directory)
    final_ans = ""
    for content in contents:
        content_path = os.path.join(abs_directory, content)
        is_dir = os.path.isdir(content_path)
        size = os.path.getsize(content_path)
        final_ans += f"- {content}: file_size={size} bytes, is_dir={is_dir}\n"
    return final_ans
