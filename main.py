import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.get_file_content import get_file_content, schema_get_file_content
from functions.write_file import write_file, schema_write_file
from functions.run_python_file import run_python_file, schema_run_python_file
from call_function import call_function


def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    SYSTEM_PROMPT = """
You are a helpful AI coding agent.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- List files and directories
- Read the content of a file
- Write to a file (create or update)
- Run a Python file with optional arguments

when the user asks about the code project - they are referring to the working directory.
So, you should typically start by looking at the project's files, and figuring out how to run the project
and how to run it tests, you'll always want to test the tests and the actual project
to verify that behavior is working.

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.
"""

    if len(sys.argv) < 2:
        print("Need a prompt")
        sys.exit(1)
    verbose = False    
    if len(sys.argv) == 3 and sys.argv[2] == "--verbose":
        verbose = True
    prompt = sys.argv[1]
    
    messages = [
    types.Content(role="user", parts=[types.Part(text=prompt)]),
]
    available_functions = types.Tool(
    function_declarations=[
        schema_get_files_info,
        schema_get_file_content,
        schema_write_file,
        schema_run_python_file,
    ]
)
    config=types.GenerateContentConfig(
    tools=[available_functions], system_instruction=SYSTEM_PROMPT
)

    max_iters = 20
    for i in range(0, max_iters):
        response = client.models.generate_content(
            model='gemini-2.0-flash-001', 
            contents=messages,
            config=config
        )

        if response is None or response.usage_metadata is None:
            print("No response")
            return
        if verbose:
            print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
            print(f"Response tokens: {response.usage_metadata.candidates_token_count}")
            print(f"Total tokens: {response.usage_metadata.total_token_count}")

        if response.candidates:
            for candidate in response.candidates:
                if candidate is None or candidate.content is None:
                    continue

                # Add the model’s message
                messages.append(candidate.content)
                print("candidates")

                # Check if this candidate includes function calls
        if response.function_calls:
            for function_call_part in response.function_calls:
                result = call_function(function_call_part, verbose)
                messages.append(result)
                print("result done")

        else:
            print(response.text)
            return

    
    
    
    

if __name__ == "__main__":
    main()