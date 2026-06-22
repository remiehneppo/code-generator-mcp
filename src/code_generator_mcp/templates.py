from code_generator_mcp.utils import clean_code_fence, detect_circular_dependency
from code_generator_mcp.schemas import FunctionSpec

def render_standard_function(
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
    """Renders Template 1: Standard Function Prompt."""
    if not task or not task.strip():
        raise ValueError("Task cannot be empty")
    if not language or not language.strip():
        raise ValueError("Language cannot be empty")
    if not signature or not signature.strip():
        raise ValueError("Signature cannot be empty")
    if not description or not description.strip():
        raise ValueError("Description cannot be empty")
    if not test_cases:
        raise ValueError("Test cases list cannot be empty")

    signature = clean_code_fence(signature)
    cleaned_test_cases = [clean_code_fence(tc) for tc in test_cases if tc.strip()]
    if not cleaned_test_cases:
        raise ValueError("Test cases list cannot be empty")

    lines = []
    lines.append("## Task")
    lines.append(task.strip())
    lines.append("")

    lines.append("## Signature")
    lines.append(f"```{language.strip()}")
    lines.append(signature)
    lines.append("```")
    lines.append("")

    lines.append("## Description")
    lines.append(description.strip())
    lines.append("")

    if constraints:
        cleaned_constraints = [c.strip() for c in constraints if c.strip()]
        if cleaned_constraints:
            lines.append("## Constraints")
            for c in cleaned_constraints:
                lines.append(f"- {c}")
            lines.append("")

    if edge_cases:
        cleaned_edge_cases = [ec.strip() for ec in edge_cases if ec.strip()]
        if cleaned_edge_cases:
            lines.append("## Edge Cases")
            for ec in cleaned_edge_cases:
                lines.append(f"- {ec}")
            lines.append("")

    lines.append("## Test Cases")
    lines.append(f"```{language.strip()}")
    lines.append("\n".join(cleaned_test_cases))
    lines.append("```")
    lines.append("")

    lines.append("## Context")
    lines.append(f"- Language: {language.strip()}")
    if dependencies_allowed:
        cleaned_deps = [d.strip() for d in dependencies_allowed if d.strip()]
        if cleaned_deps:
            lines.append(f"- Dependencies allowed: {', '.join(cleaned_deps)}")
    if integration_note and integration_note.strip():
        lines.append(f"- Integration note: {integration_note.strip()}")
    if context and context.strip():
        lines.append(f"- Additional Context: {context.strip()}")

    lines.append("")
    lines.append("## Output Requirement")
    lines.append("- Output the code inside a standard markdown code block (using ```).")
    lines.append("- Do NOT include any introductory text, conversational greetings, or explanations outside the code block.")
    lines.append("- Start immediately with the code block.")

    return "\n".join(lines).strip() + "\n"


def render_codebase_context(
    task: str,
    language: str,
    existing_code: str,
    signature: str,
    description: str,
    test_cases: list[str],
    interacts_with: str | None = None,
    constraints: list[str] | None = None,
) -> str:
    """Renders Template 2: With Codebase Context Prompt."""
    if not task or not task.strip():
        raise ValueError("Task cannot be empty")
    if not language or not language.strip():
        raise ValueError("Language cannot be empty")
    if not existing_code or not existing_code.strip():
        raise ValueError("Existing code cannot be empty")
    if not signature or not signature.strip():
        raise ValueError("Signature cannot be empty")
    if not description or not description.strip():
        raise ValueError("Description cannot be empty")
    if not test_cases:
        raise ValueError("Test cases list cannot be empty")

    existing_code = clean_code_fence(existing_code)
    signature = clean_code_fence(signature)
    cleaned_test_cases = [clean_code_fence(tc) for tc in test_cases if tc.strip()]
    if not cleaned_test_cases:
        raise ValueError("Test cases list cannot be empty")

    lines = []
    lines.append("## Task")
    lines.append(task.strip())
    lines.append("")

    lines.append("## Existing Code")
    lines.append(f"```{language.strip()}")
    lines.append(existing_code)
    lines.append("```")
    lines.append("")

    lines.append("## Signature")
    lines.append(f"```{language.strip()}")
    lines.append(signature)
    lines.append("```")
    lines.append("")

    lines.append("## Description")
    lines.append(description.strip())
    if interacts_with and interacts_with.strip():
        lines.append(f"- Interacts with: {interacts_with.strip()}")
    lines.append("")

    lines.append("## Constraints")
    if constraints:
        for c in constraints:
            if c.strip():
                lines.append(f"- {c.strip()}")
    lines.append("- Must be compatible with existing code above")
    lines.append("- Follow same naming convention and error handling pattern")
    lines.append("")

    lines.append("## Test Cases")
    lines.append(f"```{language.strip()}")
    lines.append("\n".join(cleaned_test_cases))
    lines.append("```")

    lines.append("")
    lines.append("## Output Requirement")
    lines.append("- Output the code inside a standard markdown code block (using ```).")
    lines.append("- Do NOT include any introductory text, conversational greetings, or explanations outside the code block.")
    lines.append("- Start immediately with the code block.")

    return "\n".join(lines).strip() + "\n"


def render_bugfix_refactor(
    language: str,
    current_code: str,
    problem: str,
    expected_behavior: str,
    test_cases: list[str],
    task: str | None = None,
    constraints: list[str] | None = None,
) -> str:
    """Renders Template 3: Bug Fix / Refactor Prompt."""
    if not language or not language.strip():
        raise ValueError("Language cannot be empty")
    if not current_code or not current_code.strip():
        raise ValueError("Current code cannot be empty")
    if not problem or not problem.strip():
        raise ValueError("Problem description cannot be empty")
    if not expected_behavior or not expected_behavior.strip():
        raise ValueError("Expected behavior cannot be empty")
    if not test_cases:
        raise ValueError("Test cases list cannot be empty")

    current_code = clean_code_fence(current_code)
    cleaned_test_cases = [clean_code_fence(tc) for tc in test_cases if tc.strip()]
    if not cleaned_test_cases:
        raise ValueError("Test cases list cannot be empty")

    lines = []
    lines.append("## Task")
    if task and task.strip():
        lines.append(f"Fix/Refactor the following function. {task.strip()}")
    else:
        lines.append("Fix/Refactor the following function.")
    lines.append("")

    lines.append("## Current Code")
    lines.append(f"```{language.strip()}")
    lines.append(current_code)
    lines.append("```")
    lines.append("")

    lines.append("## Problem")
    lines.append(problem.strip())
    lines.append("")

    lines.append("## Expected Behavior")
    lines.append(expected_behavior.strip())
    lines.append("")

    lines.append("## Test Cases")
    lines.append(f"```{language.strip()}")
    lines.append("\n".join(cleaned_test_cases))
    lines.append("```")
    lines.append("")

    lines.append("## Constraints")
    lines.append("- Keep same function signature")
    if constraints:
        for c in constraints:
            if c.strip():
                lines.append(f"- {c.strip()}")

    lines.append("")
    lines.append("## Output Requirement")
    lines.append("- Output the code inside a standard markdown code block (using ```).")
    lines.append("- Do NOT include any introductory text, conversational greetings, or explanations outside the code block.")
    lines.append("- Start immediately with the code block.")

    return "\n".join(lines).strip() + "\n"


def render_multi_function_module(
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
    """Renders Template 4: Multi-Function Module Prompt."""
    if not task or not task.strip():
        raise ValueError("Task cannot be empty")
    if not module_purpose or not module_purpose.strip():
        raise ValueError("Module purpose cannot be empty")
    if not language or not language.strip():
        raise ValueError("Language cannot be empty")
    if not functions:
        raise ValueError("Functions list cannot be empty")
    if not test_cases:
        raise ValueError("Test cases list cannot be empty")

    # Run cycle detection
    detect_circular_dependency(functions)

    cleaned_test_cases = [clean_code_fence(tc) for tc in test_cases if tc.strip()]
    if not cleaned_test_cases:
        raise ValueError("Test cases list cannot be empty")

    lines = []
    lines.append("## Task")
    lines.append(task.strip())
    lines.append("")

    lines.append("## Module Purpose")
    lines.append(module_purpose.strip())
    lines.append("")

    lines.append("## Functions")
    lines.append("")

    for f in functions:
        lines.append(f"### {f.name.strip()}")
        lines.append(f"- Signature: `{clean_code_fence(f.signature)}`")
        lines.append(f"- Description: {f.description.strip()}")
        if f.constraints:
            cleaned_f_constraints = [c.strip() for c in f.constraints if c.strip()]
            if cleaned_f_constraints:
                lines.append("- Constraints:")
                for c in cleaned_f_constraints:
                    lines.append(f"  - {c}")
        if f.depends_on and f.depends_on.strip():
            lines.append(f"- Depends on: {f.depends_on.strip()}")
        lines.append("")

    if shared_types and shared_types.strip():
        lines.append("## Shared Types")
        lines.append(f"```{language.strip()}")
        lines.append(clean_code_fence(shared_types))
        lines.append("```")
        lines.append("")

    lines.append("## Test Cases")
    lines.append(f"```{language.strip()}")
    lines.append("\n".join(cleaned_test_cases))
    lines.append("```")
    lines.append("")

    lines.append("## Context")
    lines.append(f"- Language: {language.strip()}")
    if dependencies:
        cleaned_deps = [d.strip() for d in dependencies if d.strip()]
        if cleaned_deps:
            lines.append(f"- Dependencies: {', '.join(cleaned_deps)}")
    if export_format and export_format.strip():
        lines.append(f"- Export format: {export_format.strip()}")
    if context and context.strip():
        lines.append(f"- Additional Context: {context.strip()}")

    lines.append("")
    lines.append("## Output Requirement")
    lines.append("- Output the code inside a standard markdown code block (using ```).")
    lines.append("- Do NOT include any introductory text, conversational greetings, or explanations outside the code block.")
    lines.append("- Start immediately with the code block.")

    return "\n".join(lines).strip() + "\n"
