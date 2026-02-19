
import os
import sys
import json
"""run_in_env: Execute scripts within specific virtual environments."""
import subprocess
import platform

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_MAP_FILE = os.path.join(BASE_DIR, "environments.json")
PIDS_FILE = os.path.join(BASE_DIR, "workspace", "pids.json")

def load_env_map():
    if os.path.exists(ENV_MAP_FILE):
        with open(ENV_MAP_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_pids():
    if os.path.exists(PIDS_FILE):
        try:
            with open(PIDS_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_pid(name, pid, cmd):
    os.makedirs(os.path.dirname(PIDS_FILE), exist_ok=True)
    pids = load_pids()
    pids[name] = {"pid": pid, "cmd": cmd}
    with open(PIDS_FILE, 'w') as f: json.dump(pids, f, indent=2)

def run(env_name, command, bg=False):
    """
    Run a command in the specified environment. If bg=True, runs in background and saves PID.
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
            
            if bg:
                proc = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                save_pid(f"env_{env_name}_{proc.pid}", proc.pid, full_cmd)
                return f"Started background process in '{env_name}'. PID: {proc.pid}"
            else:
                result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            
        elif env_type == "node":
            env_vars = os.environ.copy()
            bin_path = os.path.join(path, "node_modules", ".bin")
            env_vars["PATH"] = bin_path + os.pathsep + env_vars["PATH"]
            
            if bg:
                proc = subprocess.Popen(command, cwd=path, shell=True, env=env_vars, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                save_pid(f"node_{env_name}_{proc.pid}", proc.pid, command)
                return f"Started background Node process in '{env_name}'. PID: {proc.pid}"
            else:
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
    if len(sys.argv) < 3:
        print("Usage: run_in_env <env_name> <command> [--bg]")
        sys.exit(1)
        
    env_name = sys.argv[1]
    command = sys.argv[2]
    is_bg = "--bg" in sys.argv
    
    print(run(env_name, command, bg=is_bg))
