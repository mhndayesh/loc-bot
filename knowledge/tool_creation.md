# Tool Creation & Usage Guide

## The Basics
Tools are Python scripts located in `skills/`. They extend your capabilities beyond the native `run_command` and file operations.

### Anatomy of a Tool
A tool is a simple Python script. Arguments passed to the tool are available via `sys.argv`.

**Template:**
```python
"""
tool_name: Short description of what this tool does.
Usage: tool_name("arg1", "arg2")
"""
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: tool_name <arg1>")
        sys.exit(1)
        
    arg1 = sys.argv[1]
    
    # Do work here
    result = f"Processed {arg1}"
    print(result)

if __name__ == "__main__":
    main()
```

## Creating a Tool
Use the native `create_tool` function.

**Example:**
`[TOOL] create_tool("weather", "import sys; print('Sunny')") [/TOOL]`

**Best Practices:**
1.  **Docstrings**: Always include a docstring at the top. The `sync_skills` meta-tool reads this to populate `SKILLS.md`.
2.  **Dependencies**: If your tool needs a library (e.g., `requests`), check if it's installed or try to install it inside the tool (or fail gracefully).
3.  **Output**: Print the final result to `stdout`. This is what the agent "sees" as the tool output.
4.  **Error Handling**: If something goes wrong, print a clear error message starting with "Error:" and exit with non-zero status if possible (though the engine captures stdout regardless).

## Calling Tools
The engine parses your response for `[TOOL] name(args) [/TOOL]`.

**Parsing Logic:**
- The engine uses `ast.literal_eval` to parse arguments safely.
- **Quotes**: Always wrap string arguments in double quotes.
- **Lists**: You can pass lists: `[TOOL] plot_data([1, 2, 3], "red") [/TOOL]`.

### Common Pitfalls
- **Comma splitting**: `[TOOL] echo("Hello, world")` might be split into "Hello" and "world" if the parser is naive. Use `create_tool` to handle complex args properly or wrap the entire string in quotes carefully.
- **State**: Tools are stateless processes. They don't share memory. If you need to persist data, write to a file in `workspace/` or `memory/`.

## Native vs Custom
- **Native**: `read_file`, `write_file`, `run_command`. These run in-process or via shell.
- **Custom**: Scripts in `skills/`. These run as subprocesses.

**When to make a Custom Tool:**
- Complex logic (e.g., scraping, data analysis).
- Reusable workflows (e.g., "deploy to staging").
- When you find yourself running the same 5 `run_command`s in a row.
