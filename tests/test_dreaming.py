import os
import time
import json
import subprocess
import sys

# 1. Setup mock logs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
VAULT_FILE = os.path.join(BASE_DIR, "memory_vault.json")
os.makedirs(MEMORY_DIR, exist_ok=True)

# Delete existing vault to clear state
if os.path.exists(VAULT_FILE):
    os.remove(VAULT_FILE)

# Mock a pulse where a struggle happened then success
mock_pulse = """
[THINK]I tried to run 'ls' on windows and it failed. I should use 'dir' instead.[/THINK]
[TOOL]run_command("ls")[/TOOL]
RESULT: Command failed (exit 1): 'ls' is not recognized as an internal or external command

[THINK]Wait, this is Windows. I must use 'dir'.[/THINK]
[TOOL]run_command("dir")[/TOOL]
RESULT: Volume in drive C has no label... 
Directory of C:\new-agent-mohannad
file1.txt
file2.txt

[THINK]That worked! I discovered that on Windows CMD, 'ls' is not available and 'dir' is the correct tool.[/THINK]
"""

# Save a pulse log
log_path = os.path.join(MEMORY_DIR, f"pulse_{int(time.time())}.txt")
with open(log_path, "w", encoding="utf-8") as f:
    f.write(mock_pulse)

print(f"Saved mock pulse log: {log_path}")

# 2. Trigger reflection
print("Triggering Agent Reflection (Dreaming)...")
cwd = BASE_DIR
subprocess.run([sys.executable, "engine.py", "--once", "--mode", "reflect"], cwd=cwd)

# 3. Verify Memory Vault
if os.path.exists(VAULT_FILE):
    with open(VAULT_FILE, "r", encoding="utf-8") as f:
        vault = json.load(f)
        print(f"\n--- RECOLLECTION RESULTS ---")
        print(f"Vault size: {len(vault)}")
        if len(vault) > 0:
            for i, entry in enumerate(vault):
                print(f"Lesson #{i+1}:")
                print(f"  Problem: {entry.get('metadata', {}).get('problem') or entry.get('text', '').split('Solution:')[0].replace('Problem: ', '').strip()}")
                print(f"  Solution: {entry.get('metadata', {}).get('solution') or entry.get('text', '').split('Solution:')[-1].strip()}")
            print("\n✅ DREAMING SUCCESS: Agent reflected and extracted wisdom!")
        else:
            print("\n❌ DREAMING FAILED: No lessons found in vault.")
else:
    print("\n❌ DREAMING FAILED: Memory vault not created.")
