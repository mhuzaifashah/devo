from langchain_core.tools import tool

from functions.get_files_info import get_files_info
from functions.get_file_content import get_file_content
from functions.write_file import write_file
from functions.run_python_file import run_python_file


def build_tools(workdir):
    @tool
    def list_files(directory: str = ".") -> str:
        """List files in a directory relative to the working directory."""
        return get_files_info(workdir, directory=directory)

    @tool
    def read_file(file_path: str) -> str:
        """Read the contents of a file relative to the working directory."""
        return get_file_content(workdir, file_path=file_path)

    @tool
    def write_file_tool(file_path: str, content: str) -> str:
        """Write content to a file relative to the working directory."""
        return write_file(workdir, file_path=file_path, content=content)

    @tool
    def run_python(
        file_path: str,
        args: list[str] | None = None,
        **_ignored: object,
    ) -> str:
        """Run a Python file relative to the working directory."""
        return run_python_file(workdir, file_path=file_path, args=args or [])

    return [list_files, read_file, write_file_tool, run_python]
