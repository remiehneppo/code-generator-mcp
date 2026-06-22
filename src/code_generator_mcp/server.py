import httpx
from mcp.server.fastmcp import FastMCP
from code_generator_mcp.schemas import FunctionSpec
from code_generator_mcp.templates import (
    render_standard_function,
    render_codebase_context,
    render_bugfix_refactor,
    render_multi_function_module,
)
from code_generator_mcp.config import config
from code_generator_mcp.utils import extract_code_from_response

# Explicitly load configuration during server loading phase
config.load()

# Initialize FastMCP Server
mcp = FastMCP("code-generator-template-server")

# System Prompt rules for precise code generation
SYSTEM_PROMPT = (
    "You are a precise code generator. Your sole purpose is to produce correct, efficient, "
    "well-documented code for the given specification.\n\n"
    "Rules:\n"
    "1. Think step-by-step before writing code. Analyze requirements, identify edge cases, plan your approach.\n"
    "2. Output the code inside a standard markdown code block (using ``` followed by the language name, e.g., ```python). Do NOT output any introductory text, conversational greetings, or explanations outside the code block.\n"
    "3. Any text or comments must reside strictly inside the code block as comments/docstrings in the specified programming language.\n"
    "4. The code must be self-contained, runnable, and pass all provided test cases.\n"
    "5. Use clear variable names and add concise inline comments for non-obvious logic.\n"
    "6. If the specification is ambiguous or incomplete, state your assumptions explicitly inside a comment block at the top of the code.\n"
    "7. Optimize for correctness first, then readability, then performance.\n"
    "8. Do not generate boilerplate, frameworks, or code beyond the requested scope."
)

class APIError(RuntimeError):
    """Base exception class for all API-related errors."""
    pass

class APIConnectionError(APIError):
    """Raised when the connection to the API endpoint fails."""
    pass

class APIStatusError(APIError):
    """Raised when the API returns a non-200 error status code."""
    pass

# Initialize connection-pooling HTTP client globally to reuse TCP/TLS handshakes
http_client = httpx.Client(timeout=180.0)

def generate_code(prompt: str, language: str, generate_test_file: bool = False) -> str:
    """
    Sends the specification prompt to the configured OpenAI-compatible API to generate code.
    If generate_test_file is True, it asks the model to co-generate unit tests.
    Runs a syntax/linter auto-fixing loop on the output.
    """
    import sys
    from code_generator_mcp.utils import (
        validate_code_syntax,
        extract_code_and_tests_from_response,
        extract_code_from_response
    )
    
    base_url = config.api_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    # Customize system prompt and user prompt based on generate_test_file
    system_prompt = SYSTEM_PROMPT
    if generate_test_file:
        system_prompt = (
            "You are a precise code generator. Your sole purpose is to produce correct, efficient, "
            "well-documented code and a matching suite of unit tests for the given specification.\n\n"
            "Rules:\n"
            "1. Think step-by-step before writing code. Analyze requirements, plan your approach.\n"
            "2. You MUST structure your response into two distinct sections with markdown headings:\n"
            "   ## Code Implementation\n"
            "   ```[language]\n"
            "   [main code implementation]\n"
            "   ```\n"
            "   ## Unit Tests\n"
            "   ```[language]\n"
            "   [comprehensive suite of unit tests using standard or popular test frameworks]\n"
            "   ```\n"
            "3. Do NOT output any introductory text, conversational greetings, or explanations outside the code blocks.\n"
            "4. The code and tests must be self-contained, runnable, and correct.\n"
            "5. Use clear variable names and add concise inline comments."
        )
        prompt += (
            "\n\nRemember: Generate BOTH the implementation code and a matching suite of unit tests. "
            "Structure your output using the headings '## Code Implementation' and '## Unit Tests', "
            "each containing exactly one code block for the respective code."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    max_retries = 3
    for attempt in range(max_retries + 1):
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 2048
        }
        
        try:
            response = http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise APIError("No completions returned from the model API.")
            message = choices[0]["message"]
            raw_content = (message.get("content") or "").strip()
            if not raw_content:
                raw_content = (message.get("reasoning_content") or "").strip()
        except httpx.HTTPStatusError as e:
            raise APIStatusError(f"API HTTP error: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise APIConnectionError(f"Failed to connect to API endpoint at {url}: {e}") from e
        except Exception as e:
            raise APIError(f"Failed to generate code via API: {e}") from e

        # Extract and Validate
        if generate_test_file:
            impl_code, test_code = extract_code_and_tests_from_response(raw_content)
            
            impl_error = validate_code_syntax(impl_code, language)
            test_error = validate_code_syntax(test_code, language) if test_code else "Missing Unit Tests block"
            
            errors = []
            if impl_error:
                errors.append(f"Implementation Code Error:\n{impl_error}")
            if test_error:
                errors.append(f"Unit Test Code Error:\n{test_error}")
                
            if not errors:
                return (
                    f"## Code Implementation\n"
                    f"```{language}\n"
                    f"{impl_code}\n"
                    f"```\n\n"
                    f"## Unit Tests\n"
                    f"```{language}\n"
                    f"{test_code}\n"
                    f"```"
                )
                
            error_msg = "\n\n".join(errors)
        else:
            impl_code = extract_code_from_response(raw_content)
            error_msg = validate_code_syntax(impl_code, language)
            if not error_msg:
                return impl_code
                
        # If we reach here, we have errors and we need to retry
        if attempt == max_retries:
            sys.stderr.write(f"Warning: Code has syntax errors after {max_retries} attempts: {error_msg}\n")
            if generate_test_file:
                return (
                    f"## Code Implementation\n"
                    f"```{language}\n"
                    f"{impl_code}\n"
                    f"```\n\n"
                    f"## Unit Tests\n"
                    f"```{language}\n"
                    f"{test_code if test_code else ''}\n"
                    f"```\n\n"
                    f"/* WARNING: Code syntax validation failed:\n{error_msg}\n*/"
                )
            else:
                return impl_code

        # Add assistant response and user correction prompt
        messages.append({"role": "assistant", "content": raw_content})
        
        sys.stderr.write(f"Syntax/Linter error detected (attempt {attempt + 1}/{max_retries + 1}):\n{error_msg}\nRetrying...\n")
        
        if generate_test_file:
            fix_prompt = (
                f"The generated {language} code/tests contain syntax/compiler/linter errors:\n"
                f"```\n{error_msg}\n```\n"
                f"Please fix these errors and output the complete corrected implementation code "
                f"and unit tests using the specified headings (## Code Implementation and ## Unit Tests)."
            )
        else:
            fix_prompt = (
                f"The generated {language} code contains syntax/compiler/linter errors:\n"
                f"```\n{error_msg}\n```\n"
                f"Please fix these errors and output the complete corrected code inside a single standard markdown code block."
            )
            
        messages.append({"role": "user", "content": fix_prompt})

# ==========================================
# MCP TOOLS (EXPOSED PUBLIC API)
# ==========================================

@mcp.tool()
def generate_standard_function(
    task: str,
    language: str,
    signature: str,
    description: str,
    test_cases: list[str],
    constraints: list[str] | None = None,
    edge_cases: list[str] | None = None,
    context: str | None = None,
    dependencies_allowed: list[str] | None = None,
    integration_note: str | None = None,
    generate_test_file: bool = False,
) -> str:
    """
    Generate code for a standard function spec (Template 1) using coder expert model.
    
    If `generate_test_file` is True, it will co-generate a matching unit test suite.
    
    IMPORTANT: All parameters (such as 'task', 'description', 'constraints', 'edge_cases', etc.) 
    MUST be provided in English. If the user's prompt or request is in Vietnamese or another language, 
    the calling agent must automatically translate the text of these parameter values into English 
    before invoking this tool.
    """
    prompt = render_standard_function(
        task=task,
        language=language,
        signature=signature,
        description=description,
        test_cases=test_cases,
        constraints=constraints,
        edge_cases=edge_cases,
        context=context,
        dependencies_allowed=dependencies_allowed,
        integration_note=integration_note,
    )
    return generate_code(prompt, language, generate_test_file=generate_test_file)

@mcp.tool()
def generate_codebase_context(
    task: str,
    language: str,
    existing_code: str,
    signature: str,
    description: str,
    test_cases: list[str],
    interacts_with: str | None = None,
    constraints: list[str] | None = None,
    generate_test_file: bool = False,
) -> str:
    """
    Generate code for a function with codebase context (Template 2) using coder expert model.
    
    If `generate_test_file` is True, it will co-generate a matching unit test suite.
    
    IMPORTANT: All parameters (such as 'task', 'description', 'constraints', etc.) 
    MUST be provided in English. If the user's prompt or request is in Vietnamese or another language, 
    the calling agent must automatically translate the text of these parameter values into English 
    before invoking this tool.
    """
    prompt = render_codebase_context(
        task=task,
        language=language,
        existing_code=existing_code,
        signature=signature,
        description=description,
        test_cases=test_cases,
        interacts_with=interacts_with,
        constraints=constraints,
    )
    return generate_code(prompt, language, generate_test_file=generate_test_file)

@mcp.tool()
def generate_bugfix_refactor(
    language: str,
    current_code: str,
    problem: str,
    expected_behavior: str,
    test_cases: list[str],
    task: str | None = None,
    constraints: list[str] | None = None,
    generate_test_file: bool = False,
) -> str:
    """
    Generate fixed or refactored code (Template 3) using coder expert model.
    
    If `generate_test_file` is True, it will co-generate a matching unit test suite.
    
    IMPORTANT: All parameters (such as 'task', 'problem', 'expected_behavior', 'constraints', etc.) 
    MUST be provided in English. If the user's prompt or request is in Vietnamese or another language, 
    the calling agent must automatically translate the text of these parameter values into English 
    before invoking this tool.
    """
    prompt = render_bugfix_refactor(
        language=language,
        current_code=current_code,
        problem=problem,
        expected_behavior=expected_behavior,
        test_cases=test_cases,
        task=task,
        constraints=constraints,
    )
    return generate_code(prompt, language, generate_test_file=generate_test_file)

@mcp.tool()
def generate_multi_function_module(
    task: str,
    module_purpose: str,
    language: str,
    functions: list[FunctionSpec],
    test_cases: list[str],
    shared_types: str | None = None,
    dependencies: list[str] | None = None,
    export_format: str | None = None,
    context: str | None = None,
    generate_test_file: bool = False,
) -> str:
    """
    Generate code for a multi-function module (Template 4) using coder expert model.
    
    If `generate_test_file` is True, it will co-generate a matching unit test suite.
    
    IMPORTANT: All parameters (such as 'task', 'module_purpose', 'context', 'functions' list with its 
    descriptions/constraints, etc.) MUST be provided in English. If the user's prompt or request is 
    in Vietnamese or another language, the calling agent must automatically translate the text of 
    these parameter values into English before invoking this tool.
    """
    prompt = render_multi_function_module(
        task=task,
        module_purpose=module_purpose,
        language=language,
        functions=functions,
        test_cases=test_cases,
        shared_types=shared_types,
        dependencies=dependencies,
        export_format=export_format,
        context=context,
    )
    return generate_code(prompt, language, generate_test_file=generate_test_file)

@mcp.tool()
def run_project_tests(custom_command: str | None = None) -> str:
    """
    Automatically detects and runs the project's test suite, returning the command's stdout and stderr.
    Can be used by the AI to verify correct behavior of generated code.
    
    If 'custom_command' is provided, it runs that command line instead of auto-detecting.
    """
    import subprocess
    import shlex
    
    if custom_command:
        cmd_args = shlex.split(custom_command)
        reason = f"Custom command provided: '{custom_command}'"
    else:
        from code_generator_mcp.utils import detect_test_command
        cmd_args, reason = detect_test_command()
        
    if not cmd_args:
        return f"Error: Unable to run tests. Reason: {reason}\nTry specifying a command via 'custom_command'."
        
    cmd_str = " ".join(cmd_args)
    
    try:
        res = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=120  # Give it 2 minutes
        )
        status = "PASSED" if res.returncode == 0 else f"FAILED (exit code: {res.returncode})"
        
        output_parts = [
            f"=== Test Command Execution Details ===",
            f"Command: {cmd_str}",
            f"Reason: {reason}",
            f"Status: {status}",
            f"\n--- STDOUT ---",
            res.stdout or "(no stdout)",
            f"\n--- STDERR ---",
            res.stderr or "(no stderr)",
        ]
        return "\n".join(output_parts)
    except subprocess.TimeoutExpired:
        return f"Error: Test command '{cmd_str}' timed out after 120 seconds."
    except Exception as e:
        return f"Error: Failed to execute test command '{cmd_str}': {e}"

if __name__ == "__main__":
    mcp.run()
