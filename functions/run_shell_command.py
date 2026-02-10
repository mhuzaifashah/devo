import json
import os
import shlex
import subprocess
from shutil import which


DENY_SUBSTRINGS = [
    " rm ",
    " rmdir ",
    " del ",
    " erase ",
    " remove-item",
    " format ",
    " mkfs",
    " shutdown",
]

SAFE_GIT_SUBCOMMANDS = {"status", "diff", "log", "branch", "rev-parse", "show"}
SHELL_CACHE = {}


def _contains_denied(command):
    lowered = f" {command.lower()} "
    return any(token in lowered for token in DENY_SUBSTRINGS)


def _has_shell_operators(command):
    return any(op in command for op in ["&&", "||", "|", ";", ">", "<"])


def _command_prefix(command):
    try:
        parts = shlex.split(command, posix=os.name != "nt")
    except Exception:
        parts = command.strip().split()
    return parts[0].lower() if parts else ""


def _cache_path(working_dir):
    return os.path.join(working_dir, ".aiagent", "cache", "shell.json")


def _read_cache(working_dir):
    cache_path = _cache_path(working_dir)
    if not os.path.isfile(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("shell") and data.get("args"):
            return data
    except Exception:
        return None
    return None


def _write_cache(working_dir, data):
    cache_path = _cache_path(working_dir)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _resolve_shell(working_dir):
    if "shell" in SHELL_CACHE:
        return SHELL_CACHE["shell"]

    cached = _read_cache(working_dir)
    if cached:
        SHELL_CACHE["shell"] = cached
        return cached

    env_shell = os.environ.get("AIAGENT_SHELL")
    shell_path = None
    shell_args = None
    shell_type = None

    if env_shell:
        resolved = which(env_shell) or env_shell
        shell_path = resolved
        base = os.path.basename(resolved).lower()
        if base in {"pwsh", "powershell"}:
            shell_args = ["-NoProfile", "-Command"]
            shell_type = "powershell"
        elif base in {"bash", "zsh", "ksh"}:
            shell_args = ["-lc"]
            shell_type = "posix"
        else:
            shell_args = ["-c"]
            shell_type = "posix"

    if not shell_path:
        if os.name == "nt":
            shell_path = which("pwsh") or which("powershell") or "powershell"
            shell_args = ["-NoProfile", "-Command"]
            shell_type = "powershell"
        else:
            shell_path = (
                which("bash")
                or which("zsh")
                or which("sh")
                or "/bin/sh"
            )
            base = os.path.basename(shell_path).lower()
            shell_args = ["-lc"] if base in {"bash", "zsh", "ksh"} else ["-c"]
            shell_type = "posix"

    resolved = {"shell": shell_path, "args": shell_args, "type": shell_type}
    SHELL_CACHE["shell"] = resolved
    _write_cache(working_dir, resolved)
    return resolved


def run_shell_command(
    working_dir,
    command,
    safe_mode=True,
    safe_prefixes=None,
    timeout=30,
):
    if not command.strip():
        return "Error: command is empty."

    if _contains_denied(command):
        return "Error: destructive command blocked by policy."

    if safe_mode:
        if _has_shell_operators(command):
            return "Error: shell operators are not allowed in safe mode."
        prefix = _command_prefix(command)
        allowed = [p.lower() for p in (safe_prefixes or [])]
        if prefix not in allowed:
            return f"Error: '{prefix}' is not in the safe command allowlist."
        if prefix == "git":
            try:
                parts = shlex.split(command, posix=os.name != "nt")
            except Exception:
                parts = command.strip().split()
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub not in SAFE_GIT_SUBCOMMANDS:
                return f"Error: git subcommand '{sub}' is not allowed in safe mode."

    try:
        shell_cfg = _resolve_shell(working_dir)
        cmd = [shell_cfg["shell"], *shell_cfg["args"], command]
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        output = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        if result.returncode != 0:
            output += f"\nProcess exited with code {result.returncode}"
        return output.strip() or "No output produced."
    except Exception as e:
        return f"Error executing command: {e}"
