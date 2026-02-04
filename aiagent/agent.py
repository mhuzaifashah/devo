from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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


def run_agent(prompt, provider, model, workdir, max_iters=20, temperature=0.2, verbose=False):
    llm = get_llm(provider, model, temperature=temperature)
    tools = build_tools(workdir)

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt_template)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        max_iterations=max_iters,
    )
    result = executor.invoke({"input": prompt})
    return result.get("output", "")
