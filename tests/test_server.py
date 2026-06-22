import pytest
from code_generator_mcp.server import mcp

@pytest.mark.anyio
async def test_server_registration():
    # Verify server name
    assert mcp.name == "code-generator-template-server"

    # Verify registered tools
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    expected_tools = {
        "generate_standard_function",
        "generate_codebase_context",
        "generate_bugfix_refactor",
        "generate_multi_function_module",
    }
    assert expected_tools.issubset(tool_names)

    # Verify prompts are empty/not exposed
    prompts = await mcp.list_prompts()
    assert len(prompts) == 0
