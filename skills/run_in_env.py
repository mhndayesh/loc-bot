
import os
import sys
import json
import subprocess
import platform

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_MAP_FILE = os.path.join(BASE_DIR, "environments.json")

def load_env_map():
    if os.path.exists(ENV_MAP_FILE):
        with open(ENV_MAP_FILE, 'r') as f:
            return json.load(f)
    return {}

def run(env_name, command):
    """
    Run a command in the specified environment.
    """
    data = load_env_map()
    if env_name not in data:
        return f"Error: Environment '{env_name}' not found."

    env = data[env_name]
    path = env["path"]
    env_type = env["type"]

    try:
        if env_type == "python":
            if platform.system() == "Windows":
                activate_script = os.path.join(path, "Scripts", "activate.bat")
                # Use & to chain commands in cmd.exe
                full_cmd = f'"{activate_script}" && {command}'
            else:
                activate_script = os.path.join(path, "bin", "activate")
                full_cmd = f"source {activate_script} && {command}"
            
            # shell=True is needed for activation scripts
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            
        elif env_type == "node":
            # Just set CWD to the environment path
            # And add node_modules/.bin to PATH
            env_vars = os.environ.copy()
            bin_path = os.path.join(path, "node_modules", ".bin")
            env_vars["PATH"] = bin_path + os.pathsep + env_vars["PATH"]
            
            result = subprocess.run(command, cwd=path, shell=True, env=env_vars, capture_output=True, text=True)
            
        else:
            return f"Error: Unknown environment type {env_type}"

        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        
        return output

    except Exception as e:
        return f"Error executing in environment: {e}"

if __name__ == "__main__":
    pass
