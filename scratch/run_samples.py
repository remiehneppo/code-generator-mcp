import asyncio
import json
import os
import sys

# Set environment variables for our config system to read
os.environ["CODE_GEN_API_URL"] = "http://localhost:8008/v1"
os.environ["CODE_GEN_MODEL"] = "coder-expert"

# Import our FastMCP server instance
from code_generator_mcp.server import mcp

async def test_tool(tool_name: str, args: dict) -> str:
    print(f"\n" + "="*60)
    print(f"Executing tool: {tool_name}")
    print("="*60)
    try:
        # Call the tool using FastMCP's tool execution engine
        result = await mcp.call_tool(tool_name, arguments=args)
        
        # result is a tuple: (list[TextContent], dict[str, Any])
        # unstructured content is the first element of the tuple
        output_text = result[0][0].text
        
        print("Response received from local Qwen model:")
        print("-"*60)
        print(output_text)
        print("-"*60)
        return output_text
    except Exception as e:
        print(f"Error executing tool {tool_name}: {e}")
        return f"ERROR: {e}"

async def main():
    sample_data_path = "scratch/sample_data.json"
    if not os.path.exists(sample_data_path):
        print(f"Sample data file {sample_data_path} not found.")
        sys.exit(1)
        
    with open(sample_data_path, "r") as f:
        samples = json.load(f)
        
    results = {}
    
    # 1. Test generate_standard_function
    results["generate_standard_function"] = await test_tool(
        "generate_standard_function",
        samples["generate_standard_function"]
    )
    
    # 2. Test generate_codebase_context
    results["generate_codebase_context"] = await test_tool(
        "generate_codebase_context",
        samples["generate_codebase_context"]
    )
    
    # 3. Test generate_bugfix_refactor
    results["generate_bugfix_refactor"] = await test_tool(
        "generate_bugfix_refactor",
        samples["generate_bugfix_refactor"]
    )
    
    # 4. Test generate_multi_function_module
    results["generate_multi_function_module"] = await test_tool(
        "generate_multi_function_module",
        samples["generate_multi_function_module"]
    )
    
    # Save the output results into a file for review
    output_report_path = "scratch/test_execution_report.json"
    with open(output_report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll tests completed. Execution report saved to {output_report_path}")

if __name__ == "__main__":
    asyncio.run(main())
