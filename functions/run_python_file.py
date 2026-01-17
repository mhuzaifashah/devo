import os
import subprocess
from google.genai import types

def run_python_file(working_dir : str, file_path : str, args=[]):
    abs_working_dir = os.path.abspath(working_dir)       
    abs_file_path = os.path.abspath(os.path.join(working_dir,file_path))
    if not abs_file_path.startswith(abs_working_dir):
        return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a file'
    if not file_path.endswith(".py"):
        return f'Error : "{file_path}" is not a Python file'
    
    try:
        final_args = ["py","-X", "utf8", file_path, *args]        
        output = subprocess.run(
            final_args,
            cwd=abs_working_dir,
            timeout=30,
            capture_output=True,
            encoding="utf-8"
            
        )
        final_str = f"""
STDOUT: {output.stdout}
STDERR: {output.stderr}
"""
        if output.stdout == "" and output.stderr == "":
            final_str = "No output produced.\n"
        if output.returncode != 0:
            final_str += f"Process exited with code {output.returncode}"
        return final_str
    except Exception as e:
        return f'Error: executing Python file: {e}'
    
schema_run_python_file = types.FunctionDeclaration(
    name="run_python_file",
    description="Runs a python file with the python3 interpreter. Accepts additional CLI args as an optional array.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The file to run, relative to the working directory.",
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,
                description="An optional array of strings to be used as the CLI args for the Python file",
                items=types.Schema(
                    type=types.Type.STRING                    
                )
            ),
        },
    ),
)