# Code Generator MCP Template Server Plan (Updated - Stricter Prompts & Direct Output)

## Summary
Build a Python MCP server in the `/home/tieubaoca/AI/code-generator-mcp` workspace. The server will expose:
- **4 FastMCP Code Generation Tools**: Taking specification parameters, generating prompt templates internally, passing them to an OpenAI-compatible API, and returning the model's raw completion response directly (relying on strict prompt rules to deliver pure code).

No prompts or prompt generation methods are exposed directly to the MCP client; prompt templates remain as internal utilities of the server.

Reference: official MCP Python SDK documents FastMCP via `from mcp.server.fastmcp import FastMCP`, `@mcp.tool()`, and stdio/HTTP transports in the `modelcontextprotocol/python-sdk` README: https://github.com/modelcontextprotocol/python-sdk

## Key Changes
- Scaffold Python package with pip/venv workflow:
  - `pyproject.toml`
  - `requirements.txt`
  - `src/code_generator_mcp/__init__.py`
  - `src/code_generator_mcp/server.py`
  - `src/code_generator_mcp/config.py` (CLI Arguments and Environment Variables config parsing)
  - `src/code_generator_mcp/schemas.py` (Pydantic input models)
  - `src/code_generator_mcp/templates.py` (Markdown rendering logic - internal)
  - `src/code_generator_mcp/utils.py` (Helper logic for sanitization and cycle detection)
  - `tests/test_templates.py`
  - `tests/test_utils.py`
  - `tests/test_server.py`
  - `tests/test_api.py` (Unit tests for config loader and HTTP API requests)
- Dependencies:
  - runtime: `mcp[cli]>=1.2.0,<2.0.0`, `pydantic>=2.0`, `httpx>=0.20.0`
  - test: `pytest`
- Server entrypoint:
  - FastMCP server name: `code-generator-template-server`
  - transport: stdio via `mcp.run()`
  - command target: `python -m code_generator_mcp.server`

## Configuration System
The MCP server accepts configuration parameters to connect to any OpenAI-compatible API endpoint (such as OpenAI, Ollama, vLLM, OpenRouter, etc.).
- **CLI Arguments**: `--api-url`, `--model`, `--api-key`
- **Environment Variables**: `CODE_GEN_API_URL` (or `OPENAI_BASE_URL`), `CODE_GEN_MODEL` (or `OPENAI_MODEL`), `CODE_GEN_API_KEY` (or `OPENAI_API_KEY`)

## System Prompt (Coder Expert Model - Strict version)
The internal generator wraps the spec with the expert coder system prompt:
```
You are a precise code generator. Your sole purpose is to produce correct, efficient, well-documented code for the given specification.

Rules:
1. Think step-by-step before writing code. Analyze requirements, identify edge cases, plan your approach.
2. Output ONLY the raw executable code. Do NOT output any introductory text, markdown code blocks (e.g. no ```python), conversational greetings, or explanations.
3. Any text or comments must reside strictly inside the code block as comments/docstrings in the specified programming language.
4. The code must be self-contained, runnable, and pass all provided test cases.
5. Use clear variable names and add concise inline comments for non-obvious logic.
6. If the specification is ambiguous or incomplete, state your assumptions explicitly inside a comment block at the top of the code.
7. Optimize for correctness first, then readability, then performance.
8. Do not generate boilerplate, frameworks, or code beyond the requested scope.
```

## Public API

### Pydantic Models (`schemas.py`)
- `FunctionSpec`
  - `name` (str)
  - `signature` (str)
  - `description` (str)
  - `constraints` (list[str] or None)
  - `depends_on` (str or None)

### MCP Tools
- **Template 1: Standard Function**: `generate_standard_function`
- **Template 2: With Codebase Context**: `generate_codebase_context`
- **Template 3: Bug Fix / Refactor**: `generate_bugfix_refactor`
- **Template 4: Multi-Function Module**: `generate_multi_function_module`

## Implementation Details
- **OpenAI-Compatible Call**:
  - Sent via a POST request to `{api_url}/chat/completions` using the `httpx` synchronous HTTP client. Timeout is configured to 60 seconds.
- **Output Requirements Enforcement (Prompt-Only)**:
  1. **Strict User Prompts**: All 4 template renderers append a trailing `## Output Requirement` section instructing the LLM to output *only* raw code and skip markdown fences.
  2. **Direct Completion**: The HTTP client returns the model's raw completion content directly. The extraction parser `extract_code_from_response` remains implemented as a library utility, but is bypassed in the active server tools handler.
- **Sanitization Policy**:
  - Automatically strip enclosing markdown code fences (e.g. ` ```python ... ``` ` or plain ` ``` `) from code inputs to prevent nested markdown syntax errors in final templates.
- **Dependency Cycle Checking**:
  - Validate the `depends_on` relationships between functions. If any dependency doesn't exist, raise a `ValueError`. If any cycle is detected, raise a `ValueError`.

## Test Plan
- Unit tests in `tests/test_utils.py` for code fence sanitization, dependency cycle checking, undefined dependency validation, and `extract_code_from_response()`.
- Unit tests in `tests/test_templates.py` for template formatting and rendering structure.
- Unit tests in `tests/test_api.py` for config loading paths and mock HTTP calls using `unittest.mock`.
- Integration test in `tests/test_server.py` to ensure tool registration with FastMCP.
