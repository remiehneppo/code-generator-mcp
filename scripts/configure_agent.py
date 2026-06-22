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
            
    new_json_str = json.dumps(data, indent=2)
    write_file_atomically(file_path, new_json_str)
    print(f"Configured: {file_path}")

def update_codex_toml(file_path: str, server_name: str, command: str, env_vars: dict) -> None:
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    lines = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    blocks = []
    current_block = None
    unrelated_before = []
    
    for line in lines:
        if line.strip().startswith("[[mcp_servers]]"):
            if current_block:
                blocks.append(current_block)
            current_block = {"lines": [line], "name": None}
        else:
            if current_block:
                current_block["lines"].append(line)
            else:
                unrelated_before.append(line)
    if current_block:
        blocks.append(current_block)
        
    for b in blocks:
        for line in b["lines"]:
            stripped = line.strip()
            if stripped.startswith("name"):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    b["name"] = parts[1].strip().strip('"').strip("'")
                    
    target_block = None
    for b in blocks:
        if b["name"] == server_name:
            target_block = b
            break
            
    if target_block:
        b_lines = target_block["lines"]
        new_b_lines = []
        
        keys = {}
        env_section_started = False
        existing_env = {}
        other_lines = []
        
        i = 0
        while i < len(b_lines):
            line = b_lines[i]
            stripped = line.strip()
            
            if stripped.startswith("[[mcp_servers]]"):
                i += 1
                continue
                
            if stripped.startswith("[mcp_servers.env]"):
                env_section_started = True
                i += 1
                while i < len(b_lines):
                    next_line = b_lines[i]
                    next_stripped = next_line.strip()
                    if next_stripped.startswith("[") or next_stripped.startswith("name") or next_stripped.startswith("command") or next_stripped.startswith("args"):
                        break
                    if next_stripped and "=" in next_stripped and not next_stripped.startswith("#"):
                        k, v = next_stripped.split("=", 1)
                        existing_env[k.strip()] = v.strip().strip('"').strip("'")
                    i += 1
                continue
                
            if stripped.startswith("name"):
                i += 1
                continue
            if stripped.startswith("command"):
                i += 1
                continue
            if stripped.startswith("args"):
                i += 1
                continue
                
            other_lines.append(line)
            i += 1
            
        merged_env = existing_env.copy()
        merged_env.update(env_vars)
        
        new_b_lines.append("[[mcp_servers]]\n")
        new_b_lines.append(f'name = "{server_name}"\n')
        new_b_lines.append(f'command = "{command}"\n')
        new_b_lines.append("args = []\n")
        
        for line in other_lines:
            if line.strip():
                new_b_lines.append(line)
                
        new_b_lines.append("[mcp_servers.env]\n")
        for k, v in sorted(merged_env.items()):
            new_b_lines.append(f'{k} = "{v}"\n')
        new_b_lines.append("\n")
        
        target_block["lines"] = new_b_lines
    else:
        new_b_lines = [
            "[[mcp_servers]]\n",
            f'name = "{server_name}"\n',
            f'command = "{command}"\n',
            "args = []\n",
            "[mcp_servers.env]\n"
        ]
        for k, v in sorted(env_vars.items()):
            new_b_lines.append(f'{k} = "{v}"\n')
        new_b_lines.append("\n")
        blocks.append({"lines": new_b_lines, "name": server_name})
        
    final_lines = []
    final_lines.extend(unrelated_before)
    for b in blocks:
        final_lines.extend(b["lines"])
        
    if os.path.exists(file_path):
        backup_path = file_path + ".bak"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to create backup at {backup_path}: {e}\n")
            
    write_file_atomically(file_path, "".join(final_lines))
    print(f"Configured Codex (TOML): {file_path}")

def configure_claude_code(exec_path: str, env_vars: dict) -> bool:
    import subprocess
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return False
        
    server_config = {
        "command": exec_path,
        "args": [],
        "env": env_vars
    }
    
    try:
        res = subprocess.run(
            [claude_bin, "mcp", "add-json", json.dumps(server_config)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode == 0:
            print("Successfully configured Claude Code using 'claude mcp add-json'.")
            return True
        else:
            sys.stderr.write(f"Warning: 'claude mcp add-json' returned code {res.returncode}. Stderr: {res.stderr}\n")
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to run 'claude mcp add-json': {e}\n")
        
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
        
    # Executable check (handling platform difference)
    if IS_WIN:
        ext = os.path.splitext(exec_path)[1].lower()
        pathext = [e.lower() for e in os.environ.get("PATHEXT", "").split(";")]
        if ext not in pathext:
            sys.stderr.write(f"Warning: Executable path '{exec_path}' does not have a standard Windows executable extension.\n")
    else:
        if not os.access(exec_path, os.X_OK):
            sys.stderr.write(f"Error: Path '{exec_path}' is not executable. Please verify execution permissions.\n")
            sys.exit(1)
            
    if agent_type not in AGENTS:
        sys.stderr.write(f"Error: Unknown agent type: {agent_type}. Supported agents: {', '.join(sorted(AGENTS.keys()))}\n")
        sys.exit(1)
        
    agent = AGENTS[agent_type]
    
    if not agent.is_installed():
        sys.stderr.write(f"Warning: Coding agent '{agent.name}' installation directory or command was not detected on your system.\n")
        
    api_url = os.environ.get("CODE_GEN_API_URL") or "http://localhost:8008/v1"
    model = os.environ.get("CODE_GEN_MODEL") or "gemma-12b"
    
    env_vars = {
        "CODE_GEN_API_URL": api_url,
        "CODE_GEN_MODEL": model
    }
    
    # Try CLI helper for Claude Code if global/default
    if agent_type == "claude-code" and scope == "global":
        if configure_claude_code(exec_path, env_vars):
            return
            
    try:
        path = agent.get_path(scope=scope)
        key_path = agent.key_path
        
        server_config = {
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
