# Debugging & Error Handling Protocols

## The "Step-Back" Protocol
When you encounter an error (red text), DO NOT blindly retry. Follow this protocol:

1.  **STOP**: Pause. Do not generate a tool call immediately.
2.  **READ**: Look at the logic in `[THINK]`. Read the error message *carefully*.
3.  **HYPOTHESIZE**: Why did it fail?
    - *Syntax Error?* Check your code.
    - *Missing Dependency?* Check `pip list`.
    - *Permissions?* Check `verify_context`.
    - *Logic?* Did you assume a file existed?
4.  **PLAN**: Formulate a fix.
5.  **ACT**: Execute the fix.

## Common Error Patterns

### 1. `FileNotFoundError`
- **Cause**: The file isn't where you think it is.
- **Fix**: ALWAYS run `list_dir("path")` before trying to read/write if you are unsure.
- **Prevention**: Use absolute paths or `os.path.join(BASE_DIR, ...)`.

### 2. `ModuleNotFoundError`
- **Cause**: Library not installed.
- **Fix**: `run_command("pip install <library>")`.
- **Note**: Some libraries have different import names (e.g., `pip install PyYAML` -> `import yaml`).

### 3. `SyntaxError` in Tool Call
- **Cause**: You used single quotes inside a string, or forgot to escape backslashes in Windows paths.
- **Fix**: Use raw strings `r"path\to\file"` or forward slashes `"path/to/file"`.
- **Fix**: Ensure your `[TOOL]` tag is closed properly `[/TOOL]`.

### 4. Loop Detection Triggered
- **Cause**: You tried the same action 3 times.
- **Fix**: CHANGE TACTICS.
    - If `read_file` failed 3 times, stop reading. Try `list_dir`. Try `search_web`.
    - Ask the user for help: `notify_user("I am stuck on...")`.

## Debugging Tools

### 1. `print()` Debugging
- In your custom tools, `print()` goes to stdout, which you see in the result.
- Use it liberally during development.

### 2. `write_file("debug.log", ...)`
- If a script is complex, write specific variable states to a log file in `workspace/`.

### 3. `system_stats`
- Use this to check if the machine is overloaded or if you are running out of disk space.
