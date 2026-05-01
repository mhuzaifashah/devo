import json
import os
import re
import subprocess
from shutil import which

DEFAULT_UNSAFE_COMMANDS = (
    "rm",
    "rmdir",
    "del",
    "erase",
    "remove-item",
    "format",
    "mkfs",
    "shutdown",
)
SHELL_CACHE: dict[str, dict[str, object]] = {}


def cache_path(working_dir: str) -> str:
    return os.path.join(working_dir, ".aiagent", "cache", "shell.json")


def read_cache(working_dir: str) -> dict[str, object] | None:
    path = cache_path(working_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if "shell" not in data or "args" not in data or "type" not in data:
        return None
    return data


def write_cache(working_dir: str, data: dict[str, object]) -> None:
    path = cache_path(working_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
    except OSError:
        return


def shell_spec(path: str) -> dict[str, object]:
    base = os.path.basename(path).lower()
    if base in {"pwsh", "powershell", "powershell.exe", "pwsh.exe"}:
        return {"shell": path, "args": ["-NoProfile", "-Command"], "type": "powershell"}
    if base in {"bash", "zsh", "ksh"}:
        return {"shell": path, "args": ["-lc"], "type": "posix"}
    return {"shell": path, "args": ["-c"], "type": "posix"}


def default_shell() -> dict[str, object]:
    if os.name == "nt":
        path = which("pwsh") or which("powershell") or "powershell"
        return shell_spec(path)
    path = which("bash") or which("zsh") or which("sh") or "/bin/sh"
    return shell_spec(path)


def resolve_shell(working_dir: str) -> dict[str, object]:
    cached_value = SHELL_CACHE.get("shell")
    if isinstance(cached_value, dict):
        return cached_value

    disk_cache = read_cache(working_dir)
    if disk_cache:
        SHELL_CACHE["shell"] = disk_cache
        return disk_cache

    env_shell = os.environ.get("AIAGENT_SHELL")
    if env_shell:
        resolved = which(env_shell) or env_shell
        shell_value = shell_spec(resolved)
        SHELL_CACHE["shell"] = shell_value
        write_cache(working_dir, shell_value)
        return shell_value

    shell_value = default_shell()
    SHELL_CACHE["shell"] = shell_value
    write_cache(working_dir, shell_value)
    return shell_value


def normalize_unsafe_commands(value: object | None) -> list[str]:
    if value is None:
        return [item for item in DEFAULT_UNSAFE_COMMANDS]
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    text = str(value).strip().lower()
    if not text:
        return [item for item in DEFAULT_UNSAFE_COMMANDS]
    return [text]


def blocked_token(command: str, unsafe_commands: list[str]) -> str | None:
    lowered = command.lower()
    for token in unsafe_commands:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, lowered):
            return token
    return None


def run_shell_command(
    working_dir: str,
    command: str,
    safe_mode: bool = True,
    safe_prefixes: list[str] | None = None,
    unsafe_commands: list[str] | None = None,
    timeout: int = 30,
) -> str:
    del safe_mode
    del safe_prefixes
    if not command.strip():
        return "Error: command is empty."
    unsafe = normalize_unsafe_commands(unsafe_commands)
    token = blocked_token(command, unsafe)
    if token:
        return f"Error: command blocked by policy due to unsafe token '{token}'."

    timeout_value = 30
    try:
        timeout_value = max(1, int(timeout))
    except (TypeError, ValueError):
        timeout_value = 30

    try:
        shell_value = resolve_shell(working_dir)
        shell_path = str(shell_value.get("shell", ""))
        shell_args = shell_value.get("args", [])
        if not isinstance(shell_args, list):
            shell_args = ["-c"]
        command_line = [shell_path, *[str(item) for item in shell_args], command]
        result = subprocess.run(
            command_line,
            cwd=working_dir,
            timeout=timeout_value,
            capture_output=True,
            text=True,
        )
    except Exception as error:
        return f"Error executing command: {error}"

    output = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    if result.returncode != 0:
        output += f"\nProcess exited with code {result.returncode}"
    return output.strip() or "No output produced."
