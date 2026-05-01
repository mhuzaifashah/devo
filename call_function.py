from dataclasses import dataclass
from src.tools import get_file_content, get_files_info, run_shell_command, write_file

WORKDIR = "tests/calculator"


@dataclass
class Call:
    name: str
    args: dict[str, object]


def call_function(function_call_part: Call, verbose: bool = False) -> dict[str, object]:
    if verbose:
        print(f"Calling function: {function_call_part.name}({function_call_part.args})")
    if not verbose:
        print(f" - Calling function: {function_call_part.name}")

    if function_call_part.name == "get_files_info":
        result = get_files_info(WORKDIR, **function_call_part.args)
        return {"result": result}

    if function_call_part.name == "get_file_content":
        result = get_file_content(WORKDIR, **function_call_part.args)
        return {"result": result}

    if function_call_part.name == "write_file":
        result = write_file(WORKDIR, **function_call_part.args)
        return {"result": result}

    if function_call_part.name == "run_shell_command":
        args = dict(function_call_part.args)
        command = str(args.pop("command", ""))
        safe_mode = bool(args.pop("safe_mode", True))
        safe_prefixes = args.pop("safe_prefixes", None)
        timeout = int(args.pop("timeout", 30))
        result = run_shell_command(
            WORKDIR,
            command=command,
            safe_mode=safe_mode,
            safe_prefixes=safe_prefixes,
            timeout=timeout,
        )
        return {"result": result}

    return {"error": f"Unknown function: {function_call_part.name}"}
