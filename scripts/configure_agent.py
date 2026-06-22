import sys
import json
import os
import shutil

def strip_json_comments(text: str) -> str:
    out = []
    in_string = False
    in_single_comment = False
    in_multi_comment = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if in_string:
            if c == '\\' and i + 1 < n:
                out.append(c)
                out.append(text[i+1])
                i += 2
                continue
            elif c == '"':
                in_string = False
                out.append(c)
            else:
                out.append(c)
        elif in_single_comment:
            if c == '\n':
                in_single_comment = False
                out.append(c)
        elif in_multi_comment:
            if c == '*' and i + 1 < n and text[i+1] == '/':
                in_multi_comment = False
                i += 1
        else:
            if c == '"':
                in_string = True
                out.append(c)
            elif c == '/' and i + 1 < n and text[i+1] == '/':
                in_single_comment = True
                i += 1
            elif c == '/' and i + 1 < n and text[i+1] == '*':
                in_multi_comment = True
                i += 1
            else:
                out.append(c)
        i += 1
    return "".join(out)

def write_file_atomically(file_path: str, content: str) -> None:
    import tempfile
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e

class AgentConfig:
    def __init__(self, name, format_type, key_path, global_path_func, local_path_func=None, install_check_func=None):
        self.name = name
        self.format_type = format_type
        self.key_path = key_path
        self.global_path_func = global_path_func
        self.local_path_func = local_path_func
        self.install_check_func = install_check_func

    def get_path(self, scope="global", workspace_root=None):
        if scope == "local" and self.local_path_func:
            return self.local_path_func(workspace_root or os.getcwd())
        return self.global_path_func()

    def is_installed(self):
        if self.install_check_func:
            return self.install_check_func()
        return True

# Platform constants
HOME = os.path.expanduser("~")
APPDATA = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform.startswith("darwin")

# Path resolving functions
def _claude_desktop_path():
    if IS_WIN:
        return os.path.join(APPDATA, "Claude", "claude_desktop_config.json")
    elif IS_MAC:
        return os.path.join(HOME, "Library", "Application Support", "Claude", "claude_desktop_config.json")
    else:
        return os.path.join(HOME, ".config", "Claude", "claude_desktop_config.json")

def _claude_desktop_installed():
    path = _claude_desktop_path()
    return os.path.exists(os.path.dirname(path))

def _claude_code_path():
    return os.path.join(HOME, ".claude.json")

def _claude_code_installed():
    return shutil.which("claude") is not None or os.path.exists(os.path.join(HOME, ".claude.json"))

def _cursor_path():
    return os.path.join(HOME, ".cursor", "mcp.json")

def _cursor_installed():
    return shutil.which("cursor") is not None or os.path.exists(os.path.join(HOME, ".cursor"))

def _copilot_local_path(workspace):
    return os.path.join(workspace, ".vscode", "mcp.json")

def _copilot_installed():
    return shutil.which("code") is not None or os.path.exists(os.path.join(HOME, ".vscode"))

def _codex_path():
    return os.path.join(HOME, ".codex", "config.toml")

def _codex_installed():
    return shutil.which("codex") is not None or os.path.exists(os.path.join(HOME, ".codex"))

def _windsurf_path():
    return os.path.join(HOME, ".codeium", "windsurf", "mcp_config.json")

def _windsurf_installed():
    return os.path.exists(os.path.join(HOME, ".codeium", "windsurf"))

def _zed_path():
    if IS_WIN:
        return os.path.join(APPDATA, "Zed", "settings.json")
    else:
        return os.path.join(HOME, ".config", "zed", "settings.json")

def _zed_installed():
    return shutil.which("zed") is not None or os.path.exists(os.path.dirname(_zed_path()))

def _agy_path():
    return os.path.join(HOME, ".gemini", "settings.json")

def _agy_installed():
    return os.path.exists(os.path.join(HOME, ".gemini"))

# Registry definition
AGENTS = {
    "claude-desktop": AgentConfig("Claude Desktop", "json", ["mcpServers", "code-generator-mcp"], _claude_desktop_path, install_check_func=_claude_desktop_installed),
    "claude-code": AgentConfig("Claude Code", "json", ["mcpServers", "code-generator-mcp"], _claude_code_path, local_path_func=lambda w: os.path.join(w, ".mcp.json"), install_check_func=_claude_code_installed),
    "cursor": AgentConfig("Cursor", "json", ["mcpServers", "code-generator-mcp"], _cursor_path, local_path_func=lambda w: os.path.join(w, ".cursor", "mcp.json"), install_check_func=_cursor_installed),
    "github-copilot": AgentConfig("GitHub Copilot", "json", ["servers", "code-generator-mcp"], lambda: os.path.join(HOME, ".vscode", "mcp.json"), local_path_func=_copilot_local_path, install_check_func=_copilot_installed),
    "codex": AgentConfig("Codex", "toml", ["mcp_servers"], _codex_path, install_check_func=_codex_installed),
    "windsurf": AgentConfig("Windsurf", "json", ["mcpServers", "code-generator-mcp"], _windsurf_path, install_check_func=_windsurf_installed),
    "zed": AgentConfig("Zed", "json", ["context_servers", "code-generator-mcp"], _zed_path, install_check_func=_zed_installed),
    "agy": AgentConfig("Antigravity", "json", ["mcpServers", "code-generator-mcp"], _agy_path, install_check_func=_agy_installed)
}

def update_json_file(file_path: str, key_path: list[str], server_config: dict) -> None:
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    raw_content = ""
    data = {}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            
    if raw_content.strip():
        clean_content = strip_json_comments(raw_content)
        try:
            data = json.loads(clean_content)
        except Exception as e:
            sys.stderr.write(f"Error: Existing config file at {file_path} is malformed or has invalid JSON syntax: {e}.\n")
            sys.stderr.write("Aborting installation to prevent data loss. Please fix the config file syntax and try again.\n")
            sys.exit(1)
            
    current = data
    for key in key_path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
        
    last_key = key_path[-1]
    if last_key in current and isinstance(current[last_key], dict):
        existing_server = current[last_key]
        if "url" in existing_server or existing_server.get("type") in ("http", "sse"):
            sys.stderr.write(
                f"Warning: Existing server '{last_key}' in '{file_path}' is configured as an HTTP/SSE server "
                f"(url: {existing_server.get('url')}). Overwriting it to a stdio server.\n"
            )
        if "env" in existing_server and isinstance(existing_server["env"], dict) and "env" in server_config:
            merged_env = existing_server["env"].copy()
            merged_env.update(server_config["env"])
            server_config["env"] = merged_env
        if "args" in existing_server and isinstance(existing_server["args"], list) and "args" in server_config:
            # Preserve existing custom args if they exist
            server_config["args"] = existing_server["args"]
            
    current[last_key] = server_config
    
    if os.path.exists(file_path):
        backup_path = file_path + ".bak"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to create backup at {backup_path}: {e}\n")
            
    new_json_str = json.dumps(data, indent=2, ensure_ascii=False)
    write_file_atomically(file_path, new_json_str)
    print(f"Configured: {file_path}")

def update_codex_toml(file_path: str, server_name: str, command: str, env_vars: dict) -> None:
    import tomlkit
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    doc = tomlkit.document()
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                doc = tomlkit.parse(f.read())
            except Exception as e:
                sys.stderr.write(f"Error: Existing Codex config at {file_path} has invalid TOML syntax: {e}.\n")
                sys.stderr.write("Aborting installation to prevent data loss.\n")
                sys.exit(1)
                
    if "mcp_servers" not in doc:
        doc["mcp_servers"] = tomlkit.table()
        
    mcp_servers = doc["mcp_servers"]
    
    if server_name in mcp_servers:
        target_server = mcp_servers[server_name]
    else:
        target_server = tomlkit.table()
        mcp_servers[server_name] = target_server
        
    if target_server:
        if "url" in target_server or target_server.get("transport") in ("http", "sse"):
            sys.stderr.write(
                f"Warning: Existing Codex server '{server_name}' is configured as an HTTP/SSE server "
                f"(url: {target_server.get('url')}). Overwriting it to a stdio server.\n"
            )
            # Remove HTTP specific keys
            if "url" in target_server:
                del target_server["url"]
            if "transport" in target_server:
                del target_server["transport"]
            
    env_table = tomlkit.table()
    for k, v in sorted(env_vars.items()):
        env_table[k] = v
        
    if "env" in target_server:
        existing_env = target_server["env"]
        for k, v in existing_env.items():
            if k not in env_table:
                env_table[k] = v
                
    target_server["command"] = command
    if "args" not in target_server:
        target_server["args"] = tomlkit.array()
    target_server["env"] = env_table
    
    if os.path.exists(file_path):
        backup_path = file_path + ".bak"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to create backup at {backup_path}: {e}\n")
            
    new_toml_str = tomlkit.dumps(doc)
    write_file_atomically(file_path, new_toml_str)
    print(f"Configured Codex (TOML): {file_path}")

def configure_claude_code(exec_path: str, env_vars: dict, scope: str = "global") -> bool:
    import subprocess
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return False
        
    server_config = {
        "type": "stdio",
        "command": exec_path,
        "args": [],
        "env": env_vars
    }
    
    cmd = [claude_bin, "mcp", "add-json", "code-generator-mcp", json.dumps(server_config, ensure_ascii=False)]
    if scope and scope != "global":
        cmd.extend(["--scope", scope])
        
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if res.returncode == 0:
            print(f"Successfully configured Claude Code using '{' '.join(cmd)}'.")
            return True
        else:
            sys.stderr.write(f"Warning: '{' '.join(cmd)}' returned code {res.returncode}. Stderr: {res.stderr}\n")
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to run '{' '.join(cmd)}': {e}\n")
        
    return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Configure coding agent for MCP server")
    parser.add_argument("agent", help="Target agent type (e.g. cursor, claude-code, codex, etc.)")
    parser.add_argument("executable_path", help="Path to MCP server executable")
    parser.add_argument("--scope", default="global", choices=["global", "local"], help="Configuration scope (global or local/workspace)")
    
    args = parser.parse_args()
    
    agent_type = args.agent.lower()
    exec_path = args.executable_path
    scope = args.scope
    
    if not os.path.exists(exec_path):
        sys.stderr.write(f"Error: Executable path '{exec_path}' does not exist.\n")
        sys.exit(1)
        
    # Executable check using shutil.which for robust cross-platform validation
    resolved_exec = shutil.which(exec_path)
    if not resolved_exec:
        sys.stderr.write(f"Error: Path '{exec_path}' is not recognized as an executable file.\n")
        sys.exit(1)
    exec_path = resolved_exec
            
    if agent_type not in AGENTS:
        sys.stderr.write(f"Error: Unknown agent type: {agent_type}. Supported agents: {', '.join(sorted(AGENTS.keys()))}\n")
        sys.exit(1)
        
    agent = AGENTS[agent_type]
    
    if not agent.is_installed():
        sys.stderr.write(f"Warning: Coding agent '{agent.name}' installation directory or command was not detected on your system.\n")
        
    api_url = os.environ.get("CODE_GEN_API_URL") or "http://localhost:8008/v1"
    model = os.environ.get("CODE_GEN_MODEL") or "coder-expert"
    
    env_vars = {
        "CODE_GEN_API_URL": api_url,
        "CODE_GEN_MODEL": model
    }
    
    # Try CLI helper for Claude Code
    if agent_type == "claude-code":
        if configure_claude_code(exec_path, env_vars, scope):
            return
            
    try:
        path = agent.get_path(scope=scope)
        key_path = agent.key_path
        
        server_config = {
            "type": "stdio",
            "command": exec_path,
            "args": [],
            "env": env_vars
        }
        
        if agent.format_type == "json":
            update_json_file(path, key_path, server_config)
        elif agent.format_type == "toml":
            update_codex_toml(path, "code-generator-mcp", exec_path, env_vars)
    except Exception as e:
        sys.stderr.write(f"Error configuring agent: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
