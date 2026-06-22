import pytest
from code_generator_mcp.utils import (
    clean_code_fence,
    detect_circular_dependency,
    parse_list_input,
    parse_functions_input,
    extract_code_from_response,
)
from code_generator_mcp.schemas import FunctionSpec

def test_clean_code_fence():
    # Surrounding code fence with language
    code_with_lang = "```python\ndef hello():\n    pass\n```"
    assert clean_code_fence(code_with_lang) == "def hello():\n    pass"

    # Surrounding code fence without language
    code_plain = "```\ndef hello():\n    pass\n```"
    assert clean_code_fence(code_plain) == "def hello():\n    pass"

    # No code fence
    code_none = "def hello():\n    pass"
    assert clean_code_fence(code_none) == "def hello():\n    pass"

    # Empty inputs or space
    assert clean_code_fence("   ") == ""

def test_detect_circular_dependency_no_cycle():
    # Straight chain: A -> B -> C
    funcs = [
        {"name": "A", "depends_on": "B"},
        {"name": "B", "depends_on": "C"},
        {"name": "C", "depends_on": None},
    ]
    # Should not raise exception
    detect_circular_dependency(funcs)

def test_detect_circular_dependency_undefined_dependency():
    # Dependency is not defined in the function list
    funcs = [
        {"name": "A", "depends_on": "B"},
        {"name": "B", "depends_on": "C"}, # C is not defined
    ]
    with pytest.raises(ValueError) as excinfo:
        detect_circular_dependency(funcs)
    assert "depends on 'C', which is not defined in the module" in str(excinfo.value)

def test_detect_circular_dependency_with_cycle_direct():
    # Direct cycle: A -> B -> A
    funcs = [
        {"name": "A", "depends_on": "B"},
        {"name": "B", "depends_on": "A"},
    ]
    with pytest.raises(ValueError) as excinfo:
        detect_circular_dependency(funcs)
    assert "Circular dependency detected" in str(excinfo.value)
    assert "A -> B -> A" in str(excinfo.value) or "B -> A -> B" in str(excinfo.value)

def test_detect_circular_dependency_with_cycle_indirect():
    # Indirect cycle: A -> B -> C -> A
    funcs = [
        {"name": "A", "depends_on": "B"},
        {"name": "B", "depends_on": "C"},
        {"name": "C", "depends_on": "A"},
    ]
    with pytest.raises(ValueError) as excinfo:
        detect_circular_dependency(funcs)
    assert "Circular dependency detected" in str(excinfo.value)
    assert "A -> B -> C -> A" in str(excinfo.value) or "B -> C -> A -> B" in str(excinfo.value)

def test_parse_list_input():
    # None input
    assert parse_list_input(None) is None

    # Normal list of strings
    assert parse_list_input(["a", "b", "c"]) == ["a", "b", "c"]

    # Newline-separated string
    assert parse_list_input("line1\nline2\n\nline3") == ["line1", "line2", "line3"]

    # JSON formatted list string
    assert parse_list_input('["json1", "json2"]') == ["json1", "json2"]

    # Mixed or empty string input
    assert parse_list_input("   ") is None

def test_parse_functions_input():
    # JSON string input
    json_str = '[{"name": "f1", "signature": "sig1", "description": "desc1", "depends_on": null}]'
    parsed = parse_functions_input(json_str)
    assert len(parsed) == 1
    assert isinstance(parsed[0], FunctionSpec)
    assert parsed[0].name == "f1"

    # Dict list input
    dict_list = [{"name": "f1", "signature": "sig1", "description": "desc1", "constraints": ["c1"]}]
    parsed = parse_functions_input(dict_list)
    assert len(parsed) == 1
    assert parsed[0].name == "f1"
    assert parsed[0].constraints == ["c1"]

    # Invalid cases
    with pytest.raises(ValueError):
        parse_functions_input("invalid json")
    with pytest.raises(ValueError):
        parse_functions_input(123)

def test_extract_code_from_response():
    # Conversational text before and after the code block
    raw_response = (
        "Here is the implementation of the z_transform function:\n\n"
        "```python\n"
        "def z_transform(data, window):\n"
        "    return [1, 2, 3]\n"
        "```\n\n"
        "This function is used for sliding window z transform."
    )
    result = extract_code_from_response(raw_response)
    assert result == "def z_transform(data, window):\n    return [1, 2, 3]"

    # Plain raw code without any code block fences
    raw_code = "def z_transform(data, window):\n    return [1, 2, 3]"
    assert extract_code_from_response(raw_code) == raw_code

def test_extract_code_from_response_multiple_blocks():
    # Simulated echoed prompt scenario (multiple code blocks where implementation is longest)
    raw_response = (
        "Here is the prompt's signature:\n"
        "```python\n"
        "def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:\n"
        "```\n\n"
        "And here is the implementation:\n"
        "```python\n"
        "def merge_intervals(intervals):\n"
        "    if not intervals: return []\n"
        "    intervals.sort()\n"
        "    merged = [intervals[0]]\n"
        "    for current in intervals[1:]:\n"
        "        # merge logic here...\n"
        "        pass\n"
        "    return merged\n"
        "```"
    )
    result = extract_code_from_response(raw_response)
    assert "merge logic here" in result

def test_extract_code_and_tests_from_response():
    from code_generator_mcp.utils import extract_code_and_tests_from_response
    
    # Test explicit headings
    response_explicit = (
        "## Code Implementation\n"
        "```python\n"
        "def add(a, b): return a + b\n"
        "```\n"
        "## Unit Tests\n"
        "```python\n"
        "def test_add(): assert add(1, 2) == 3\n"
        "```\n"
    )
    impl, test = extract_code_and_tests_from_response(response_explicit)
    assert impl == "def add(a, b): return a + b"
    assert test == "def test_add(): assert add(1, 2) == 3"
    
    # Test fallback multiple blocks
    response_fallback = (
        "Here is the code:\n"
        "```javascript\n"
        "const x = 1;\n"
        "```\n"
        "Here are tests:\n"
        "```javascript\n"
        "assert(x === 1);\n"
        "```\n"
    )
    impl, test = extract_code_and_tests_from_response(response_fallback)
    assert impl == "const x = 1;"
    assert test == "assert(x === 1);"

def test_validate_code_syntax():
    from code_generator_mcp.utils import validate_code_syntax
    
    # Python valid
    assert validate_code_syntax("def f():\n    pass\n", "python") is None
    assert validate_code_syntax("def f():\n    pass\n", "py") is None
    
    # Python invalid
    err = validate_code_syntax("def f(\n    pass\n", "python")
    assert err is not None
    assert "SyntaxError" in err or "Syntax Error" in err

def test_detect_test_command(tmp_path):
    from unittest.mock import patch
    from code_generator_mcp.utils import detect_test_command
    import os
    
    # Test Rust detection
    with patch("os.getcwd", return_value=str(tmp_path)), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/cargo" if cmd == "cargo" else None):
        (tmp_path / "Cargo.toml").write_text("[package]")
        cmd, reason = detect_test_command()
        assert cmd == ["cargo", "test"]
        assert "Cargo.toml" in reason

    # Clean up files in tmp_path
    for f in tmp_path.iterdir():
        if f.is_file():
            f.unlink()

    # Test Go detection
    with patch("os.getcwd", return_value=str(tmp_path)), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/go" if cmd == "go" else None):
        (tmp_path / "go.mod").write_text("module main")
        cmd, reason = detect_test_command()
        assert cmd == ["go", "test", "./..."]
        assert "Go" in reason

    # Clean up files in tmp_path
    for f in tmp_path.iterdir():
        if f.is_file():
            f.unlink()

    # Test Node detection (package.json)
    with patch("os.getcwd", return_value=str(tmp_path)), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/npm" if cmd == "npm" else None):
        (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
        cmd, reason = detect_test_command()
        assert cmd == ["npm", "test"]
        assert "package.json" in reason
