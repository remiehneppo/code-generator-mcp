import sys
import json
import os
import shutil

def strip_json_comments(text: str) -> str:
    import re
    # Remove single line comments
    text = re.sub(r'//.*', '', text)
    # Remove multi-line comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text

def write_file_atomically(file_path: str, content: str) -> None:
    import tempfile
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e

def get_agent_path(agent_type: str, workspace_root: str = None) -> tuple[str, list[str], str]:
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    
    is_win = sys.platform.startswith("win")
    is_mac = sys.platform.startswith("darwin")
    workspace = workspace_root or os.getcwd()

    if agent_type == "claude-desktop":
        if is_win:
            path = os.path.join(appdata, "Claude", "claude_desktop_config.json")
        elif is_mac:
            path = os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json")
        else:
            path = os.path.join(home, ".config", "Claude", "claude_desktop_config.json")
        return path, ["mcpServers", "code-generator-mcp"], "json"
        
    elif agent_type == "claude-code":
        return os.path.join(home, ".claude.json"), ["mcpServers", "code-generator-mcp"], "json"
        
    elif agent_type == "agy":
        return os.path.join(home, ".gemini", "settings.json"), ["mcpServers", "code-generator-mcp"], "json"
        
    elif agent_type == "cursor":
        return os.path.join(home, ".cursor", "mcp.json"), ["mcpServers", "code-generator-mcp"], "json"
        
    elif agent_type == "github-copilot":
        return os.path.join(workspace, ".vscode", "mcp.json"), ["servers", "code-generator-mcp"], "json"
        
    elif agent_type == "codex":
        return os.path.join(home, ".codex", "config.toml"), ["mcp_servers"], "toml"
        
    elif agent_type == "windsurf":
        return os.path.join(home, ".codeium", "windsurf", "mcp_config.json"), ["mcpServers", "code-generator-mcp"], "json"
        
    elif agent_type == "zed":
        if is_win:
            path = os.path.join(appdata, "Zed", "settings.json")
        else:
            path = os.path.join(home, ".config", "zed", "settings.json")
        return path, ["context_servers", "code-generator-mcp"], "json"
        
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

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
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[[mcp_servers]]"):
            if current_block:
                blocks.append(current_block)
            current_block = {"start_idx": i, "lines": [line], "name": None, "has_env": False, "env_start": -1}
        elif current_block:
            current_block["lines"].append(line)
            if stripped.startswith("name"):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    name_val = parts[1].strip().strip('"').strip("'")
                    current_block["name"] = name_val
            elif stripped.startswith("[mcp_servers.env]"):
                current_block["has_env"] = True
                current_block["env_start"] = len(current_block["lines"]) - 1
                
    if current_block:
        blocks.append(current_block)
        
    target_block = None
    for b in blocks:
        if b["name"] == server_name:
            target_block = b
            break
            
    new_block_lines = [
        "[[mcp_servers]]\n",
        f'name = "{server_name}"\n',
        f'command = "{command}"\n',
        "args = []\n",
        "\n",
        "[mcp_servers.env]\n"
    ]
    for k, v in sorted(env_vars.items()):
        new_block_lines.append(f'{k} = "{v}"\n')
    new_block_lines.append("\n")
    
    if target_block:
        start = target_block["start_idx"]
        length = len(target_block["lines"])
        lines[start:start+length] = new_block_lines
    else:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.extend(new_block_lines)
        
    if os.path.exists(file_path):
        backup_path = file_path + ".bak"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to create backup at {backup_path}: {e}\n")
            
    write_file_atomically(file_path, "".join(lines))
    print(f"Configured Codex (TOML): {file_path}")

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: configure_agent.py <agent_type> <executable_path>\n")
        sys.exit(1)
        
    agent_type = sys.argv[1].lower()
    exec_path = sys.argv[2]
    
    if not os.path.exists(exec_path):
        sys.stderr.write(f"Error: Executable path '{exec_path}' does not exist.\n")
        sys.exit(1)
        
    if not os.access(exec_path, os.X_OK):
        sys.stderr.write(f"Error: Path '{exec_path}' is not executable. Please verify execution permissions.\n")
        sys.exit(1)
        
    api_url = os.environ.get("CODE_GEN_API_URL") or "http://localhost:8008/v1"
    model = os.environ.get("CODE_GEN_MODEL") or "gemma-12b"
    
    env_vars = {
        "CODE_GEN_API_URL": api_url,
        "CODE_GEN_MODEL": model
    }
    
    server_config = {
        "command": exec_path,
        "args": [],
        "env": env_vars
    }
    
    try:
        path, key_path, fmt = get_agent_path(agent_type)
        if fmt == "json":
            update_json_file(path, key_path, server_config)
        elif fmt == "toml":
            update_codex_toml(path, "code-generator-mcp", exec_path, env_vars)
    except Exception as e:
        sys.stderr.write(f"Error configuring agent: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
