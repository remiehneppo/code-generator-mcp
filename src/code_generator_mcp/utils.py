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

def extract_code_and_tests_from_response(text: str) -> tuple[str, str | None]:
    """
    Parses LLM response when co-generation of tests is enabled.
    Attempts to locate '## Code Implementation' and '## Unit Tests' sections,
    extracting code from the code block under each section.
    
    If sections cannot be found, it falls back to extracting code blocks by position.
    Returns (implementation_code, unit_test_code).
    """
    import re
    text = text.strip()
    
    # Try parsing by explicit headings first
    impl_pattern = re.compile(
        r"##\s*(?:Code\s+)?Implementation\s*\n+.*?```[a-zA-Z0-9_-]*\n?(.*?)\n?```",
        re.IGNORECASE | re.DOTALL
    )
    tests_pattern = re.compile(
        r"##\s*(?:Unit\s+)?Tests?\s*\n+.*?```[a-zA-Z0-9_-]*\n?(.*?)\n?```",
        re.IGNORECASE | re.DOTALL
    )
    
    impl_match = impl_pattern.search(text)
    tests_match = tests_pattern.search(text)
    
    if impl_match:
        impl_code = impl_match.group(1).strip()
        tests_code = tests_match.group(1).strip() if tests_match else None
        return impl_code, tests_code
        
    # Fallback: Find all code blocks in the response
    code_blocks = re.findall(r"```[a-zA-Z0-9_-]*\n?(.*?)\n?```", text, re.DOTALL)
    if not code_blocks:
        return text, None
        
    if len(code_blocks) >= 2:
        # Assume the first is implementation, second is tests
        return code_blocks[0].strip(), code_blocks[1].strip()
        
    return code_blocks[0].strip(), None

_which_cache = {}

def _cached_which(cmd: str) -> str | None:
    import shutil
    if cmd not in _which_cache:
        _which_cache[cmd] = shutil.which(cmd)
    return _which_cache[cmd]

def validate_code_syntax(code: str, language: str) -> str | None:
    """
    Validates code syntax for the specified language.
    Returns the error message string if there is a syntax/compilation error,
    or None if the code is syntactically valid (or if no validator is available).
    """
    import ast
    import subprocess
    import tempfile
    import os
    import sys

    lang = language.lower().strip()
    
    if lang in ("python", "py"):
        # 1. AST check (built-in, fast)
        try:
            ast.parse(code)
        except (SyntaxError, IndentationError) as e:
            # Format the error nicely
            error_details = []
            if e.filename:
                error_details.append(f"File: {e.filename}")
            if e.lineno:
                error_details.append(f"Line: {e.lineno}")
            if e.offset:
                error_details.append(f"Col: {e.offset}")
            details_str = ", ".join(error_details)
            
            snippet = ""
            if e.text:
                snippet = f"\nCode snippet:\n{e.text}"
                if e.offset is not None:
                    # add pointer to the error offset
                    pointer = " " * (e.offset - 1) + "^"
                    snippet += f"\n{pointer}"
                    
            return f"Python Syntax Error ({e.__class__.__name__}): {e.msg} ({details_str}){snippet}"
            
        # 2. Ruff check if available
        ruff_path = _cached_which("ruff")
        if ruff_path:
            try:
                res = subprocess.run(
                    [ruff_path, "check", "--no-cache", "-"],
                    input=code,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode != 0 and res.stderr:
                    return f"Python Ruff Linter Error:\n{res.stderr.strip() or res.stdout.strip()}"
                elif res.returncode != 0 and res.stdout:
                    return f"Python Ruff Linter Issues:\n{res.stdout.strip()}"
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                sys.stderr.write(f"Error running ruff: {e}\n")
                
        return None

    elif lang in ("javascript", "js"):
        # 1. Node --check
        node_path = _cached_which("node")
        if node_path:
            try:
                res = subprocess.run(
                    [node_path, "--check"],
                    input=code,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode != 0:
                    return f"JavaScript Syntax Error via node --check:\n{res.stderr.strip() or res.stdout.strip()}"
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                sys.stderr.write(f"Error running node --check: {e}\n")
                
        # 2. ESLint check if available and configured
        eslint_path = None
        local_eslint = os.path.join(os.getcwd(), "node_modules", ".bin", "eslint")
        if os.path.exists(local_eslint):
            eslint_path = local_eslint
        else:
            eslint_path = _cached_which("eslint")
            
        if eslint_path:
            # Only run ESLint if configuration is detected to avoid false failures
            has_eslint_config = False
            eslint_configs = (
                ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yaml", 
                ".eslintrc.yml", "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs"
            )
            for conf in eslint_configs:
                if os.path.exists(os.path.join(os.getcwd(), conf)):
                    has_eslint_config = True
                    break
            
            if not has_eslint_config and os.path.exists(os.path.join(os.getcwd(), "package.json")):
                try:
                    with open(os.path.join(os.getcwd(), "package.json"), "r", encoding="utf-8") as f:
                        pkg_data = json.load(f)
                    if "eslintConfig" in pkg_data:
                        has_eslint_config = True
                except Exception:
                    pass

            if has_eslint_config:
                with tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8") as temp_file:
                    temp_file.write(code)
                    temp_file_path = temp_file.name
                try:
                    res = subprocess.run(
                        [eslint_path, temp_file_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if res.returncode != 0:
                        output = res.stderr.strip() or res.stdout.strip()
                        if "Error:" in output and not ("parsing error" in output.lower() or "syntax" in output.lower()):
                            pass
                        else:
                            return f"JavaScript ESLint Linter Error:\n{output}"
                except subprocess.TimeoutExpired:
                    pass
                except Exception as e:
                    sys.stderr.write(f"Error running eslint: {e}\n")
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except Exception:
                        pass
                    
        return None

    elif lang in ("typescript", "ts"):
        # Search for tsc
        tsc_path = None
        local_tsc = os.path.join(os.getcwd(), "node_modules", ".bin", "tsc")
        if os.path.exists(local_tsc):
            tsc_path = local_tsc
        else:
            tsc_path = _cached_which("tsc")
            
        use_npx = False
        if not tsc_path and _cached_which("npx"):
            use_npx = True
            
        if tsc_path or use_npx:
            with tempfile.NamedTemporaryFile(suffix=".ts", delete=False, mode="w", encoding="utf-8") as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            try:
                cmd = [tsc_path] if tsc_path else ["npx", "tsc"]
                cmd.extend([
                    "--noEmit",
                    "--target", "es2022",
                    "--allowUnreachableCode",
                    "--allowUnusedLabels",
                    temp_file_path
                ])
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if res.returncode != 0:
                    output = res.stderr.strip() or res.stdout.strip()
                    cleaned_output = output.replace(temp_file_path, "code.ts")
                    if "Version" in cleaned_output and "Syntax:" in cleaned_output:
                        pass
                    else:
                        return f"TypeScript Compiler Error:\n{cleaned_output}"
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                sys.stderr.write(f"Error running tsc: {e}\n")
            finally:
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
                    
        return None
        
    return None

def detect_test_command() -> tuple[list[str], str]:
    """
    Detects the appropriate test command for the current project.
    Returns a tuple: (command_args_list, reason_description)
    """
    import os
    import sys
    cwd = os.getcwd()
    
    try:
        files = os.listdir(cwd)
    except Exception:
        files = []
    
    # 1. Rust (Cargo)
    if "Cargo.toml" in files:
        if _cached_which("cargo"):
            return ["cargo", "test"], "Detected Cargo.toml and cargo CLI."
            
    # 2. Go
    has_go_files = any(f.endswith(".go") for f in files if os.path.isfile(os.path.join(cwd, f)))
    if "go.mod" in files or has_go_files:
        if _cached_which("go"):
            return ["go", "test", "./..."], "Detected Go project structure and go CLI."

    # 3. Node.js (package.json)
    if "package.json" in files:
        package_json_path = os.path.join(cwd, "package.json")
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            scripts = data.get("scripts", {})
            if "test" in scripts:
                if "yarn.lock" in files and _cached_which("yarn"):
                    return ["yarn", "test"], "Detected package.json with test script and yarn.lock."
                elif "pnpm-lock.yaml" in files and _cached_which("pnpm"):
                    return ["pnpm", "test"], "Detected package.json with test script and pnpm-lock.yaml."
                elif ("bun.lockb" in files or "bun.lock" in files) and _cached_which("bun"):
                    return ["bun", "test"], "Detected package.json with test script and bun lockfile."
                elif _cached_which("npm"):
                    return ["npm", "test"], "Detected package.json with test script."
        except Exception:
            pass

    # 4. Python
    venv_pytest = None
    for venv_dir in (".venv", "venv", "env"):
        if venv_dir in files:
            possible_pytest = os.path.join(cwd, venv_dir, "bin", "pytest")
            if os.path.exists(possible_pytest):
                venv_pytest = possible_pytest
                break
            
    if venv_pytest:
        return [venv_pytest], f"Detected pytest in virtual environment: {venv_pytest}"
        
    if _cached_which("pytest"):
        return ["pytest"], "Detected global pytest command."
        
    has_python_files = any(f.endswith(".py") for f in files if os.path.isfile(os.path.join(cwd, f)))
    has_tests_dir = "tests" in files or "test" in files
    if has_python_files or has_tests_dir:
        python_bin = sys.executable or "python3"
        try:
            import pytest
            return [python_bin, "-m", "pytest"], "pytest module is imported/installed in current Python environment."
        except ImportError:
            pass
        return [python_bin, "-m", "unittest", "discover"], "Detected Python files/tests directory; falling back to unittest discover."

    # 5. Java (Gradle / Maven)
    if "pom.xml" in files and _cached_which("mvn"):
        return ["mvn", "test"], "Detected pom.xml and mvn CLI."
        
    if "gradlew" in files:
        gradlew_path = os.path.join(cwd, "gradlew")
        return [gradlew_path, "test"], "Detected Gradle wrapper (gradlew)."
    if "build.gradle" in files or "build.gradle.kts" in files:
        if _cached_which("gradle"):
            return ["gradle", "test"], "Detected build.gradle and gradle CLI."

    # 6. .NET (csproj / sln)
    if any(f.endswith(".csproj") or f.endswith(".sln") for f in files if os.path.isfile(os.path.join(cwd, f))):
        if _cached_which("dotnet"):
            return ["dotnet", "test"], "Detected .NET project file and dotnet CLI."

    if "node_modules" in files and _cached_which("npm"):
        return ["npm", "test"], "node_modules exists, falling back to npm test."
        
    return [], "Could not auto-detect any supported testing framework."
