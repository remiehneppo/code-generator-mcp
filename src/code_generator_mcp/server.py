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

def generate_code(prompt: str, language: str) -> str:
    """
    Sends the specification prompt to the configured OpenAI-compatible API to generate code.
    """
    base_url = config.api_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
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
        raw_code = (message.get("content") or "").strip()
        if not raw_code:
            raw_code = (message.get("reasoning_content") or "").strip()
        return extract_code_from_response(raw_code)
    except httpx.HTTPStatusError as e:
        raise APIStatusError(f"API HTTP error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
        raise APIConnectionError(f"Failed to connect to API endpoint at {url}: {e}") from e
    except Exception as e:
        raise APIError(f"Failed to generate code via API: {e}") from e

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
) -> str:
    """
    Generate code for a standard function spec (Template 1) using coder expert model.
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
    return generate_code(prompt, language)

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
) -> str:
    """
    Generate code for a function with codebase context (Template 2) using coder expert model.
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
    return generate_code(prompt, language)

@mcp.tool()
def generate_bugfix_refactor(
    language: str,
    current_code: str,
    problem: str,
    expected_behavior: str,
    test_cases: list[str],
    task: str | None = None,
    constraints: list[str] | None = None,
) -> str:
    """
    Generate fixed or refactored code (Template 3) using coder expert model.
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
    return generate_code(prompt, language)

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
) -> str:
    """
    Generate code for a multi-function module (Template 4) using coder expert model.
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
    return generate_code(prompt, language)

if __name__ == "__main__":
    mcp.run()
