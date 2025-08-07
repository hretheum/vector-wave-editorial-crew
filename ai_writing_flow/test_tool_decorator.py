#!/usr/bin/env python
"""Test how @tool decorator works"""

import sys
sys.path.append('src')

from crewai.tools import tool

# Test simple tool
@tool("Test Tool")
def test_tool(message: str) -> str:
    """Simple test tool"""
    return f"Processed: {message}"

# Check what @tool returns
print(f"Type of test_tool: {type(test_tool)}")
print(f"test_tool attributes: {dir(test_tool)}")

# Check if it has run method
if hasattr(test_tool, 'run'):
    print("\nTool has 'run' method")
    result = test_tool.run(message="Hello World")
    print(f"Result from run(): {result}")

# Check if it has _run method
if hasattr(test_tool, '_run'):
    print("\nTool has '_run' method")
    try:
        result = test_tool._run(message="Hello World")
        print(f"Result from _run(): {result}")
    except Exception as e:
        print(f"Error calling _run: {e}")

# Check name and description
if hasattr(test_tool, 'name'):
    print(f"\nTool name: {test_tool.name}")
if hasattr(test_tool, 'description'):
    print(f"Tool description: {test_tool.description}")

# Try to find the actual function
if hasattr(test_tool, 'func'):
    print("\nTool has 'func' attribute")
    print(f"Type of func: {type(test_tool.func)}")
    try:
        result = test_tool.func(message="Hello via func")
        print(f"Result from func(): {result}")
    except Exception as e:
        print(f"Error calling func: {e}")