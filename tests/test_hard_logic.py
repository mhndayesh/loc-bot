import os
import time
import json
import subprocess
import sys

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
VAULT_FILE = os.path.join(BASE_DIR, "memory_vault.json")
os.makedirs(MEMORY_DIR, exist_ok=True)

# 1. Prepare test logs
# (Don't delete vault, just record size)
initial_vault = []
if os.path.exists(VAULT_FILE):
    try:
        with open(VAULT_FILE, "r", encoding="utf-8") as f:
            initial_vault = json.load(f)
    except: pass
initial_count = len(initial_vault)
print(f"Initial vault size: {initial_count}")

# Create a sample pulse log (The "Dream")
pulse_file = os.path.join(MEMORY_DIR, f"pulse_hard_test_{int(time.time())}.txt")
with open(pulse_file, "w", encoding="utf-8") as f:
    f.write("[THINK]Success on Port 9999.[/THINK]\n[TOOL]run_command('python server.py --port 9999')[/TOOL]\nRESULT: Done.")

print(f"--- Created pulse log: {pulse_file}")

# 2. Trigger Reflection (First Time)
print("Triggering Reflection (Consolidation)...")
subprocess.run([sys.executable, "engine.py", "--once", "--mode", "reflect"], cwd=BASE_DIR)

# 3. Verify Deletion (Hard Cleanup)
time.sleep(1)
if not os.path.exists(pulse_file):
    print("✅ SUCCESS: Pulse log file was deleted after successful reflection.")
else:
    print("❌ FAILURE: Pulse log file STAYS after reflection.")

# 4. Verify Idempotency (Vector Vault)
lesson_count = 0
if os.path.exists(VAULT_FILE):
    with open(VAULT_FILE, "r", encoding="utf-8") as f:
        vault = json.load(f)
        lesson_count = len(vault)
        print(f"Vault contains {lesson_count} lessons.")

# 5. Trigger Reflection (Second Time) - Should find nothing new
print("\nTriggering second Reflection (should find nothing)...")
subprocess.run([sys.executable, "engine.py", "--once", "--mode", "reflect"], cwd=BASE_DIR)

if os.path.exists(VAULT_FILE):
    with open(VAULT_FILE, "r", encoding="utf-8") as f:
        vault2 = json.load(f)
        if len(vault2) == lesson_count:
            print("✅ SUCCESS: No duplicate lessons added on second run.")
        else:
            print(f"❌ FAILURE: Vault grew from {lesson_count} to {len(vault2)} on second run.")
else:
    print("❌ FAILURE: Vault disappeared?")
