"""
Skill: checkpoint
Description: Creates a backup of the agent's current state, journal, and memory. Useful for saving progress before a risky operation or pausing a multi-step task.
"""

import sys
import shutil
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_DIR = os.path.join(BASE_DIR, "workspace", ".checkpoints")

def run(name=None):
    if not name:
        name = f"auto_{int(time.time())}"
        
    target_dir = os.path.join(CHECKPOINT_DIR, name)
    os.makedirs(target_dir, exist_ok=True)
    
    files_to_backup = ["state.json", "memory_vault.json", "JOURNAL.md", "SUMMARY.md"]
    
    backed_up = []
    for f in files_to_backup:
        src = os.path.join(BASE_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(target_dir, f))
            backed_up.append(f)
            
    # Optional logic/memory files
    for f in ["instructions.json", "environments.json"]:
        src = os.path.join(BASE_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(target_dir, f))
            backed_up.append(f)
            
    return f"Success: Checkpoint '{name}' created at workspace/.checkpoints/{name}/\nBacked up: {', '.join(backed_up)}"

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else None
    print(run(name))
