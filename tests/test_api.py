import sys
from unittest.mock import patch, MagicMock
import pytest
from code_generator_mcp.config import Config
from code_generator_mcp.server import generate_code

def test_config_load_from_cli():
    # Simulate loading configs from custom arguments
    cfg = Config()
    test_args = ["--api-url", "http://my-endpoint/v1", "--model", "custom-model", "--api-key", "my-key"]
    
    with patch("argparse.ArgumentParser.parse_known_args") as mock_args:
        # Mock ArgumentParser return values
        mock_args.return_value = (
            MagicMock(api_url="http://my-endpoint/v1", model="custom-model", api_key="my-key"),
            []
        )
        cfg.load()

    assert cfg.api_url == "http://my-endpoint/v1"
    assert cfg.model == "custom-model"
    assert cfg.api_key == "my-key"

def test_config_load_from_env():
    # Simulate loading configs from environment variables
    cfg = Config()
    
    # Mock ArgumentParser return values (None / not supplied)
    with patch("argparse.ArgumentParser.parse_known_args") as mock_args, \
         patch.dict("os.environ", {
             "CODE_GEN_API_URL": "http://env-endpoint/v1",
             "CODE_GEN_MODEL": "env-model",
             "CODE_GEN_API_KEY": "env-key"
         }):
        mock_args.return_value = (
            MagicMock(api_url=None, model=None, api_key=None),
            []
        )
        cfg.load()

    assert cfg.api_url == "http://env-endpoint/v1"
    assert cfg.model == "env-model"
    assert cfg.api_key == "env-key"

def test_generate_code_api_call():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "def add(a, b):\n    return a + b"
                }
            }
        ]
    }
    
    # Temporarily override configuration for testing
    from code_generator_mcp.config import config
    original_api_url = config.api_url
    original_model = config.model
    original_api_key = config.api_key
    
    config.api_url = "http://mock-api/v1"
    config.model = "my-mock-model"
    config.api_key = "my-secret-key"

    try:
        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value = mock_response
            
            result = generate_code("spec prompt", "python")
            
            # Verify result
            assert result == "def add(a, b):\n    return a + b"
            
            # Verify HTTP post request arguments
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            url = args[0]
            assert url == "http://mock-api/v1/chat/completions"
            
            headers = kwargs["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer my-secret-key"
            
            payload = kwargs["json"]
            assert payload["model"] == "my-mock-model"
            assert payload["messages"][0]["role"] == "system"
            assert payload["messages"][1]["role"] == "user"
            assert payload["messages"][1]["content"] == "spec prompt"
            
    finally:
        # Restore configuration
        config.api_url = original_api_url
        config.model = original_model
        config.api_key = original_api_key

def test_generate_code_auto_fix():
    from code_generator_mcp.config import config
    
    # Configure mock API URL
    original_api_url = config.api_url
    config.api_url = "http://mock-api/v1"
    
    try:
        # 1st response has a syntax error: missing closing paren in def statement
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "choices": [{"message": {"content": "def add(a, b:\n    return a + b"}}]
        }
        
        # 2nd response has the fixed code
        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "choices": [{"message": {"content": "def add(a, b):\n    return a + b"}}]
        }
        
        with patch("httpx.Client.post", side_effect=[mock_response_1, mock_response_2]) as mock_post:
            result = generate_code("spec prompt", "python")
            
            # Verify the result is the corrected code
            assert result == "def add(a, b):\n    return a + b"
            
            # Verify it called the API twice
            assert mock_post.call_count == 2
            
            # Verify the second call's messages contained the linter error user feedback
            second_call_payload = mock_post.call_args_list[1][1]["json"]
            messages = second_call_payload["messages"]
            assert len(messages) == 4
            assert messages[2]["role"] == "assistant"
            assert messages[3]["role"] == "user"
            assert "Syntax Error" in messages[3]["content"] or "errors" in messages[3]["content"]
    finally:
        config.api_url = original_api_url

def test_generate_code_with_tests():
    from code_generator_mcp.config import config
    
    original_api_url = config.api_url
    config.api_url = "http://mock-api/v1"
    
    try:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": (
                        "## Code Implementation\n"
                        "```python\n"
                        "def add(a, b):\n"
                        "    return a + b\n"
                        "```\n\n"
                        "## Unit Tests\n"
                        "```python\n"
                        "def test_add():\n"
                        "    assert add(1, 2) == 3\n"
                        "```"
                    )
                }
            }]
        }
        
        with patch("httpx.Client.post", return_value=mock_response) as mock_post:
            result = generate_code("spec prompt", "python", generate_test_file=True)
            
            assert "## Code Implementation" in result
            assert "def add(a, b):" in result
            assert "## Unit Tests" in result
            assert "def test_add():" in result
            
            # Verify prompt has test generation request instructions
            first_call_payload = mock_post.call_args_list[0][1]["json"]
            user_msg = first_call_payload["messages"][1]["content"]
            assert "Co-generation" in user_msg or "matching suite of unit tests" in user_msg
    finally:
        config.api_url = original_api_url
