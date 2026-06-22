import pytest
from code_generator_mcp.templates import (
    render_standard_function,
    render_codebase_context,
    render_bugfix_refactor,
    render_multi_function_module,
)
from code_generator_mcp.schemas import FunctionSpec

def test_render_standard_function_success():
    rendered = render_standard_function(
        task="Merge overlapping intervals",
        language="python",
        signature="def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:",
        description="Input: list of (start, end) tuples. Output: merged intervals.",
        test_cases=["assert merge_intervals([(1,3),(2,6)]) == [(1,6)]"],
        constraints=["O(n log n) time"],
        edge_cases=["Empty list -> []"],
        dependencies_allowed=["stdlib only"],
        integration_note="output consumed by module A"
    )
    
    assert "## Task\nMerge overlapping intervals" in rendered
    assert "## Signature\n```python\ndef merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:\n```" in rendered
    assert "## Description\nInput: list of (start, end) tuples. Output: merged intervals." in rendered
    assert "## Constraints\n- O(n log n) time" in rendered
    assert "## Edge Cases\n- Empty list -> []" in rendered
    assert "## Test Cases\n```python\nassert merge_intervals([(1,3),(2,6)]) == [(1,6)]\n```" in rendered
    assert "## Context\n- Language: python\n- Dependencies allowed: stdlib only\n- Integration note: output consumed by module A" in rendered

def test_render_standard_function_validation():
    # Missing required field
    with pytest.raises(ValueError):
        render_standard_function(
            task="",
            language="python",
            signature="def f(): pass",
            description="desc",
            test_cases=["assert True"]
        )

    # Empty test cases list
    with pytest.raises(ValueError):
        render_standard_function(
            task="task",
            language="python",
            signature="def f(): pass",
            description="desc",
            test_cases=[]
        )

def test_render_codebase_context_success():
    rendered = render_codebase_context(
        task="Implement user validation",
        language="typescript",
        existing_code="interface User { id: string; }",
        signature="function validateUser(u: User): boolean",
        description="Validates if a user object contains correct fields.",
        test_cases=["assert(validateUser({id: '123'}) === true)"],
        interacts_with="User interface",
        constraints=["Must check id field length"]
    )

    assert "## Task\nImplement user validation" in rendered
    assert "## Existing Code\n```typescript\ninterface User { id: string; }\n```" in rendered
    assert "## Signature\n```typescript\nfunction validateUser(u: User): boolean\n```" in rendered
    assert "- Interacts with: User interface" in rendered
    assert "## Constraints\n- Must check id field length\n- Must be compatible with existing code above\n- Follow same naming convention and error handling pattern" in rendered

def test_render_bugfix_refactor_success():
    rendered = render_bugfix_refactor(
        language="python",
        current_code="def add(a, b): return a - b",
        problem="Adds instead of subtracts.",
        expected_behavior="a + b",
        test_cases=["assert add(1, 2) == 3"],
        task="Fix calculation error",
        constraints=["Run in constant time"]
    )

    assert "## Task\nFix/Refactor the following function. Fix calculation error" in rendered
    assert "## Current Code\n```python\ndef add(a, b): return a - b\n```" in rendered
    assert "## Problem\nAdds instead of subtracts." in rendered
    assert "## Expected Behavior\na + b" in rendered
    assert "## Constraints\n- Keep same function signature\n- Run in constant time" in rendered

def test_render_multi_function_module_success():
    funcs = [
        FunctionSpec(
            name="funcA",
            signature="def funcA():",
            description="Executes logic A",
            constraints=["fast"],
            depends_on="funcB"
        ),
        FunctionSpec(
            name="funcB",
            signature="def funcB():",
            description="Executes logic B",
            constraints=None,
            depends_on=None
        )
    ]

    rendered = render_multi_function_module(
        task="Build math helpers",
        module_purpose="Provide common helper functions",
        language="python",
        functions=funcs,
        test_cases=["assert funcA() is None"],
        shared_types="MyType = int",
        dependencies=["math"],
        export_format="single file"
    )

    assert "## Task\nBuild math helpers" in rendered
    assert "## Module Purpose\nProvide common helper functions" in rendered
    assert "### funcA" in rendered
    assert "- Signature: `def funcA():`" in rendered
    assert "- Description: Executes logic A" in rendered
    assert "  - fast" in rendered
    assert "- Depends on: funcB" in rendered
    assert "## Shared Types\n```python\nMyType = int\n```" in rendered
    assert "## Context\n- Language: python\n- Dependencies: math\n- Export format: single file" in rendered

def test_render_multi_function_module_circular_dependency():
    # Circular: A depends on B, B depends on A
    funcs = [
        FunctionSpec(name="A", signature="def A():", description="desc A", depends_on="B"),
        FunctionSpec(name="B", signature="def B():", description="desc B", depends_on="A")
    ]
    with pytest.raises(ValueError) as excinfo:
        render_multi_function_module(
            task="task",
            module_purpose="purpose",
            language="python",
            functions=funcs,
            test_cases=["assert True"]
        )
    assert "Circular dependency detected" in str(excinfo.value)
