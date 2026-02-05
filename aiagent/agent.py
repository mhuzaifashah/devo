from langchain.agents.factory import create_agent
from langchain_core.messages import HumanMessage

from aiagent.providers import get_llm
from aiagent.tools import build_tools

SYSTEM_PROMPT = """You are a helpful AI coding agent.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- List files and directories
- Read the content of a file
- Write to a file (create or update)
- Run a Python file with optional arguments

When the user asks about the code project, they are referring to the working directory.
Start by looking at the project's files when needed, and figure out how to run the project
and how to run tests. Prefer running tests and the project to verify behavior.

All paths you provide should be relative to the working directory.
"""


def _extract_output(result):
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return getattr(last, "content", "") or ""


def run_agent(prompt, provider, model, workdir, max_iters=20, temperature=0.2, verbose=False):
    llm = get_llm(provider, model, temperature=temperature)
    tools = build_tools(workdir)

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        debug=verbose,
    )
    result = agent.invoke({"messages": [HumanMessage(prompt)]})
    return _extract_output(result)
