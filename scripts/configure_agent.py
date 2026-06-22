import sys
import json
import os

def update_json_file(file_path, key_path, server_config):
    # Ensure the parent directory exists
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    # Read existing content or start with empty dict
    data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load existing JSON at {file_path}: {e}. Overwriting.\n")
            
    # Traversal to find the config object where we put the mcpServer
    current = data
    for key in key_path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
        
    current[key_path[-1]] = server_config
    
    # Write back
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Configured: {file_path}")

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: configure_agent.py <agent_type> <executable_path>\n")
        sys.exit(1)
        
    agent_type = sys.argv[1].lower()
    exec_path = sys.argv[2]
    
    # Define server config
    api_url = os.environ.get("CODE_GEN_API_URL") or "http://localhost:8008/v1"
    model = os.environ.get("CODE_GEN_MODEL") or "gemma-12b"
    
    server_config = {
        "command": exec_path,
        "args": [],
        "env": {
            "CODE_GEN_API_URL": api_url,
            "CODE_GEN_MODEL": model
        }
    }
    
    home = os.path.expanduser("~")
    
    if agent_type in ("claude-code", "agy"):
        # Claude Desktop and Claude CLI configs
        paths = [
            os.path.join(home, ".config", "Claude", "claude_desktop_config.json"),
            os.path.join(home, ".config", "claude", "claude_desktop_config.json")
        ]
        for path in paths:
            update_json_file(path, ["mcpServers", "code-generator-mcp"], server_config)
            
    elif agent_type == "codex":
        # Cursor global config
        path = os.path.join(home, ".cursor", "mcp.json")
        update_json_file(path, ["mcpServers", "code-generator-mcp"], server_config)
        
    elif agent_type == "github-copilot":
        # Workspace specific vscode mcp config
        cwd = os.getcwd()
        path = os.path.join(cwd, ".vscode", "mcp.json")
        # GitHub Copilot VS Code MCP config schema
        copilot_config = {
            "command": exec_path,
            "args": []
        }
        update_json_file(path, ["servers", "code-generator-mcp"], copilot_config)
        print("Note: To use this workspace-specific config, open the workspace in VS Code with GitHub Copilot Chat.")
        
    else:
        sys.stderr.write(f"Unknown agent type: {agent_type}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
