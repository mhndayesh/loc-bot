# SKILLS.md - Your Toolbox

## Native Tools (always available)
- `read_file(path)`: Read a file.
- `write_file(path, content)`: Write/create a file.
- `append_file(path, content)`: Append to a file.
- `list_dir(path)`: List directory contents.
- `run_command(cmd)`: Run a shell command.
- `create_tool(name, code)`: Create a new skill script.
- `sync_skills()`: Refresh this file.
- `compact_memory()`: Summarize & clean journal.
- `update_state(goal, status)`: Set your current goal.
- `create_plan(steps)`: Create a list of steps.
- `update_plan_step(idx, status)`: Mark step as done/failed.
- `replan(start_idx, new_steps)`: Replace future steps.

## Custom Skills (in skills/)
- `__init__.py`: Custom tool.
- `browser.py`: browser: Simple web page text fetcher.
- `checkpoint.py`: Skill: checkpoint
- `env_manager.py`: env_manager: Manage Python virtual environments.
- `gen_pass_tool.py`: gen_pass: Generates a password.
- `git_commit.py`: Skill: git_commit
- `kill_process.py`: Skill: kill_process
- `list_dir.py`: List the contents of a specified directory.
- `port_checker.py`: Custom tool.
- `run_in_env.py`: run_in_env: Execute scripts within specific virtual environments.
- `search_web.py`: search_web: Search the web via DuckDuckGo HTML (no API key needed).
- `static_analysis.py`: Skill: static_analysis
- `system_stats.py`: system_stats: Monitor CPU, Memory, and Disk usage.
- `teach.py`: teach: Add a new permanent instruction to the agent's dynamic system prompt.
- `verify_context.py`: verify_context: Double-check project files and environment status.
