<p align="center">
  <img src="devo.svg" alt="devo" />
</p>

**devo** is an interactive CLI coding agent that works with any LLM provider. Give it a task and it reads files, edits code, runs shell commands, and tracks every change — with full rollback support.

## Features

- **Model agnostic** — OpenAI, Anthropic, Google Gemini, Groq, Ollama, Azure OpenAI, OpenRouter
- **File tools** — list, read, write, edit, insert, append with workspace boundary enforcement
- **Shell execution** — PowerShell, Bash, Zsh with configurable safety mode
- **Session memory** — persisted conversation history with automatic context compaction
- **Checkpoints & rollback** — snapshot files before every tool call, restore any checkpoint
- **Multi-workspace** — primary + additional workspaces, git worktree auto-discovery
- **Hooks** — Python hooks for pre/post tool-call interception
- **Rules** — inject workspace-specific instructions via `.aiagentrules` / `AGENTS.md`

## Installation

Requires Python 3.13+.

```bash
cd devo
uv sync         # or: pip install -e .
```

Copy `.env.example` to `.env` and set your API keys:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
GROQ_API_KEY=...
```

## Usage

```bash
uv run python main.py devo                                    # interactive session
devo --prompt "Fix the bug"            # one-shot with prompt
devo --once --prompt "..."             # run once and exit
devo --session 1                       # resume session by index
devo --list-session                    # list all saved sessions
```

### Options

| Flag | Description |
|------|-------------|
| `--prompt TEXT` | Initial prompt |
| `--once` | Run once and exit (requires `--prompt`) |
| `--session ID` | Resume session by ID or list index |
| `--list-session` | List all sessions |
| `--provider NAME` | Override provider |
| `--model NAME` | Override model (`provider:model` format supported) |
| `--workdir PATH` | Override primary workspace path |
| `--workspace NAME` | Set default workspace |
| `--verbose` | Verbose agent output |
| `--plain` | Plain output, no rich UI |

## Configuration

Configure via `aiagent.toml` in the project root:

```toml
[agent]
provider = "anthropic"
model = "claude-sonnet-4-6"
workspace = "primary"
max_iters = 20
temperature = 0.2
safety_mode = "guarded"   # "guarded" | "overdrive"

[workspaces]
primary = "./src"
additional = ["./tests"]
use_git_worktrees = false

[safety]
mode = "guarded"
allow_unsafe_shell = false
auto_rollback = true
unsafe_commands = ["rm", "rmdir", "del", "format", "shutdown"]

[memory]
enabled = true
session_dir = ".aiagent/sessions"
max_history_messages = 20
context_budget = 150000

[compaction]
enabled = true
trigger_ratio = 0.8
prune_tool_outputs = true
tool_output_keep = 10

[hooks]
pre = ["hooks/my_pre_hook.py"]
post = ["hooks/my_post_hook.py"]
```

All options can also be set via environment variables: `AIAGENT_PROVIDER`, `AIAGENT_MODEL`, `AIAGENT_WORKDIR`, `AIAGENT_SAFETY_MODE`, etc.

## Providers

| Provider | `provider` value | Notes |
|----------|-----------------|-------|
| OpenAI | `openai` | GPT-4o, o1, etc. |
| Anthropic | `anthropic` | Claude 3.x / 4.x |
| Google Gemini | `google` | Gemini 1.5 / 2.0 |
| Groq | `groq` | Llama, Mixtral (fast inference) |
| Ollama | `ollama` | Local models |
| Azure OpenAI | `azure_openai` | Requires `[azure_openai]` config section |
| OpenRouter | `openrouter` | Any model via OpenRouter API |

Use `provider:model` shorthand to switch on the fly:

```bash
devo --model anthropic:claude-opus-4-7
devo --model groq:llama-3.3-70b-versatile
```

## Safety Modes

- **`guarded`** (default) — blocks destructive shell commands from a denylist
- **`overdrive`** — unrestricted shell access; requires `allow_unsafe_shell = true` in config

## Hooks

Hook files are Python modules with optional `before_tool_call` and `after_tool_call` functions:

```python
def before_tool_call(context: dict) -> bool:
    # return False to block the tool call
    print(f"Tool: {context['tool']}, args: {context['args']}")
    return True

def after_tool_call(context: dict) -> None:
    print(f"Result: {context['result']}")
```

## Rules

Place a `.aiagentrules` or `AGENTS.md` file in any workspace root to inject instructions into the agent's system prompt automatically.

## Sessions & Checkpoints

Sessions are stored in `.aiagent/sessions/` and automatically resume conversation history. Each tool call creates a checkpoint in `.aiagent/checkpoints/` — use the `rollback_checkpoint` tool or set `auto_rollback = true` to restore files on error.

## Running Tests

```bash
pytest
pytest -m "not integration"   # skip tests that call real providers
```
