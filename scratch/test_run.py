import asyncio
import os
from code_generator_mcp.server import mcp

async def main():
    print("==================================================")
    print("MCP Server Configuration:")
    from code_generator_mcp.config import config
    print(f"  API URL: {config.api_url}")
    print(f"  Model  : {config.model}")
    print(f"  API Key: {'***' if config.api_key else '(empty)'}")
    print("==================================================\n")

    print("Running integration test via FastMCP call_tool...")
    try:
        # call_tool triggers the entire serialization, parsing, and execution lifecycle
        result = await mcp.call_tool(
            "generate_standard_function",
            arguments={
                "task": "Add two numbers together",
                "language": "python",
                "signature": "def add(a: int, b: int) -> int:",
                "description": "Inputs: a and b integers. Returns their sum.",
                "test_cases": ["assert add(2, 3) == 5"],
                "constraints": ["Run in O(1) time"],
                "edge_cases": ["negative numbers are allowed"],
                "dependencies_allowed": ["stdlib only"]
            }
        )
        
        print("\n--- Tool Execution Successful! Response content: ---")
        print(result[0].text)
        print("-----------------------------------------------------")
    except Exception as e:
        print(f"\n[Error] Tool execution failed: {e}")
        print("If this is a network/API key error, make sure your api-url, model, or api-key environment variables are set correctly.")

if __name__ == "__main__":
    asyncio.run(main())
