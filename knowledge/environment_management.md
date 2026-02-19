# Environment & Sandbox Management guide

## Overview
To maintain system stability and prevent dependency conflicts, the agent system uses isolated environments for running complex tools and user-generated code.

## The `env_manager.py` Protocol
All environment lifecycle management is handled via the `env_manager.py` skill.

### 1. Creating Environments
- **Python (Venv)**: Creates a standard virtual environment with an upgraded `pip`.
- **Node.js (NPM)**: Creates a directory with a `package.json` initialized.
- **Syntax**: `[TOOL] env_manager("create", "my_env", env_type="python") [/TOOL]`

### 2. Installing Dependencies
- Environments are stored in `environments/`.
- The system tracks installed packages in `environments.json`.
- **Syntax**: `[TOOL] env_manager("install", "my_env", packages="requests numpy") [/TOOL]`

### 3. Syncing with `MAP.md`
- Every time an environment is created or modified, `env_manager` automatically updates the `## Environments` section in `MAP.md`.
- This ensures you always have a current view of your available sandboxes.

## The `run_in_env.py` Wrapper
To execute a script inside a specific environment, use the `run_in_env` skill. This handles the activation pathing for you.

- **Syntax**: `[TOOL] run_in_env("my_env", "python workspace/script.py") [/TOOL]`
- **How it works**:
    - On Windows, it uses `environments/my_env/Scripts/python.exe`.
    - On Unix, it uses `environments/my_env/bin/python`.

## Best Practices
1.  **Isolation**: Always create a new environment for projects with 3+ dependencies.
2.  **Cleanup**: Delete environments when a project is finished to save disk space using `env_manager("delete", "name")`.
3.  **Validation**: Before running `run_in_env`, use `env_manager("list")` to ensure the environment exists and has the required packages.
