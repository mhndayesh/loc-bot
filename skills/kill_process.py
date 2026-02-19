"""
Skill: kill_process
Description: Terminates a background process by its PID (usually obtained from run_in_env --bg).
"""

import sys
import subprocess
import os
import signal
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIDS_FILE = os.path.join(BASE_DIR, "workspace", "pids.json")

def load_pids():
    if os.path.exists(PIDS_FILE):
        try:
            with open(PIDS_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_pids(pids):
    with open(PIDS_FILE, 'w') as f: json.dump(pids, f, indent=2)

def run(pid_to_kill):
    try:
        pid = int(pid_to_kill)
        
        # Kill the process (cross-platform handling)
        if os.name == 'nt': # Windows
            res = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, text=True)
            if res.returncode != 0:
                # Might already be dead
                if "not found" in res.stderr.lower():
                    pass
                else:
                    return f"Error killing process {pid}: {res.stderr}"
        else: # Unix
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass # Already dead
            except Exception as e:
                return f"Error killing process {pid}: {e}"

        # Clean up the JSON tracker
        pids = load_pids()
        removed = []
        for name, data in list(pids.items()):
            if data.get("pid") == pid:
                del pids[name]
                removed.append(name)
        
        if removed:
            save_pids(pids)
            return f"Success: Process {pid} terminated and removed from tracking ({', '.join(removed)})."
        else:
            return f"Process {pid} terminated (was not tracked in pids.json)."

    except ValueError:
        return f"Error: '{pid_to_kill}' is not a valid integer PID."
    except Exception as e:
        return f"Unexpected error killing process: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: kill_process <pid>")
        sys.exit(1)
        
    print(run(sys.argv[1]))
