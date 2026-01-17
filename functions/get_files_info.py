
import os
from google.genai import types


def get_files_info(working_dir, directory='.'):
    abs_working_dir = os.path.abspath(working_dir)       
    abs_directory = os.path.abspath(os.path.join(working_dir,directory))
    if not abs_directory.startswith(abs_working_dir):
        return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

    if not os.path.isdir(abs_directory):
        return f'Error: "{directory}" is not a directory'
    
    contents = os.listdir(abs_directory)
    final_ans = ""
    for content in contents:
        content_path = os.path.join(abs_directory,content)
        is_dir = os.path.isdir(content_path)
        size = os.path.getsize(content_path)
        final_ans += f"- {content}: file_size={size} bytes, is_dir={is_dir}\n"
    return final_ans

    
schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="Lists files in the specified directory along with their sizes, constrained to the working directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description="The directory to list files from, relative to the working directory. If not provided, lists files in the working directory itself.",
            ),
        },
    ),
)

# print(get_files_info("calculator","pkg"))         
# # → ["main.py", ".venv", "data"]

# print(get_files_info("D:/Code/Python/aiagent", "calculator"))      
# # → ["file1.txt", "file2.csv"]

# print(get_files_info("D:/Code/Python/aiagent", "main.py"))   
# # → Error: "main.py" is not a directory

# print(get_files_info("D:/Code/Python/aiagent", "../Windows"))