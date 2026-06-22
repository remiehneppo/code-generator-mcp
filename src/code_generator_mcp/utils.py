import json

def clean_code_fence(code: str) -> str:
    """
    Strips surrounding markdown code fences from the input string if present.
    Also strips leading and trailing whitespace.
    """
    code = code.strip()
    lines = code.splitlines()
    if len(lines) >= 2:
        first = lines[0].strip()
        last = lines[-1].strip()
        if first.startswith("```") and last == "```":
            return "\n".join(lines[1:-1]).strip()
    return code

def detect_circular_dependency(functions) -> None:
    """
    Validates if there is any circular dependency (depends_on loop) among functions.
    Raises ValueError if a loop is detected.
    
    Accepts a list of objects/dicts that have `name` and `depends_on` attributes/keys.
    """
    nodes = {}
    for f in functions:
        if isinstance(f, dict):
            name = f.get("name")
            dep = f.get("depends_on")
        else:
            name = getattr(f, "name", None)
            dep = getattr(f, "depends_on", None)
        nodes[name] = dep

    # Validate that all dependencies exist in the module
    for name, dep in nodes.items():
        if dep and dep not in nodes:
            raise ValueError(f"Function '{name}' depends on '{dep}', which is not defined in the module.")

    visited = set()
    path = []
    path_set = set()

    def dfs(node: str) -> None:
        if node in path_set:
            cycle_start = path.index(node)
            cycle_path = " -> ".join(path[cycle_start:] + [node])
            raise ValueError(f"Circular dependency detected: {cycle_path}")
        if node in visited:
            return

        visited.add(node)
        
        dep = nodes.get(node)
        if dep:
            path.append(node)
            path_set.add(node)
            dfs(dep)
            path_set.remove(node)
            path.pop()

    for node in nodes:
        dfs(node)

def parse_list_input(val) -> list[str] | None:
    """
    Parses various input formats (None, empty, JSON list, newline-separated string, 
    or list of strings) into a clean list of strings.
    """
    if val is None:
        return None
    
    # If it is a string, handle JSON list or newline-separated string
    if isinstance(val, str):
        val_stripped = val.strip()
        if not val_stripped:
            return None
        if val_stripped.startswith("["):
            try:
                data = json.loads(val_stripped)
                if isinstance(data, list):
                    return [str(item).strip() for item in data]
            except Exception:
                pass
        return [line.strip() for line in val.splitlines() if line.strip()]
    
    # If it is a list, clean each element
    if isinstance(val, list):
        cleaned = [str(item).strip() for item in val if str(item).strip()]
        return cleaned if cleaned else None
        
    return None

def parse_functions_input(val) -> list:
    """
    Parses functions input (list of specs, JSON string representing a list of specs)
    into a list of FunctionSpec dict-like or FunctionSpec objects.
    """
    from code_generator_mcp.schemas import FunctionSpec
    
    if val is None:
        raise ValueError("Functions cannot be None")
        
    if isinstance(val, str):
        val_stripped = val.strip()
        if not val_stripped:
            raise ValueError("Functions input cannot be empty")
        try:
            data = json.loads(val_stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for functions: {e}")
        if not isinstance(data, list):
            raise ValueError("functions must be a list of function specifications")
        return [FunctionSpec(**f) for f in data]
        
    if isinstance(val, list):
        res = []
        for f in val:
            if isinstance(f, FunctionSpec):
                res.append(f)
            elif isinstance(f, dict):
                res.append(FunctionSpec(**f))
            else:
                raise ValueError("Each function specification must be a FunctionSpec or dict")
        return res
        
    raise ValueError("functions must be a list or a JSON string")

def extract_code_from_response(text: str) -> str:
    """
    Extracts the raw code block from the LLM response.
    If markdown code fences (```) are present, it extracts the content of the longest matched block.
    If no code fences are found, it returns the trimmed raw text.
    """
    import re
    text = text.strip()
    
    # Match code blocks with or without language specifier
    pattern = re.compile(r"```[a-zA-Z0-9_-]*\n?(.*?)\n?```", re.DOTALL)
    matches = pattern.findall(text)
    if matches:
        # Return the longest code block, which is the actual implementation
        return max(matches, key=len).strip()
        
    return text
