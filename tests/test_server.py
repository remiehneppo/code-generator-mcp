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
        "run_project_tests",
    }
    assert expected_tools.issubset(tool_names)

    # Verify prompts are empty/not exposed
    prompts = await mcp.list_prompts()
    assert len(prompts) == 0

@pytest.mark.anyio
async def test_run_project_tests():
    from unittest.mock import patch, MagicMock
    from code_generator_mcp.server import run_project_tests
    
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "All tests passed"
    mock_res.stderr = ""
    
    with patch("subprocess.run", return_value=mock_res) as mock_run:
        result = run_project_tests(custom_command="pytest")
        assert "All tests passed" in result
        assert "pytest" in result
        mock_run.assert_called_once_with(
            ["pytest"],
            capture_output=True,
            text=True,
            timeout=120
        )
