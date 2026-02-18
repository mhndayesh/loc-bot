import os
import time
import json
import subprocess
import sys
import memory

# 1. Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
VAULT_FILE = os.path.join(BASE_DIR, "memory_vault.json")
LOG_PATH = os.path.join(MEMORY_DIR, f"pulse_test_dreaming.txt")

# Clear existing state
if os.path.exists(VAULT_FILE):
    os.remove(VAULT_FILE)
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)

print("=== STARTING DREAM EMBEDDING TEST ===")

# 2. Inject a "Lesson"worthy pulse
# Context: Trying to start a server on a blocked port, then finding a free one.
mock_log = """
[THINK]I need to start the agent server. I'll try port 8080.[/THINK]
[TOOL]run_command("python server.py --port 8080")[/TOOL]
RESULT: Error: Port 8080 is already in use by another process.

[THINK]Oh, 8080 is blocked. I should try an unusual port like 7777 instead.[/THINK]
[TOOL]run_command("python server.py --port 7777")[/TOOL]
RESULT: Agent terminal system active via port 7777. GUI server running at http://localhost:7777

[THINK]Success! Lessons learned: If the default port is busy, switch to port 7777 which is usually free on this system.[/THINK]
"""
with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write(mock_log)
print(f"Logged a 'Pivot' experience to: {LOG_PATH}")

# 3. Trigger Reflection
print("Triggering Agent Dreaming (Reflection)...")
subprocess.run([sys.executable, "engine.py", "--once", "--mode", "reflect"], cwd=BASE_DIR)

# 4. Verify Embedding and Recall
print("\n--- Testing Retrieval ---")
time.sleep(2) # Wait for file system

query = "What should I do if the server port 8080 is already in use?"
print(f"Querying memory: '{query}'")

# Use the actual memory module to recall
wisdom = memory.recall(query)

if wisdom:
    print(f"\n💡 SUCCESS! Dreaming lesson recalled:")
    print(f"------------------------------------")
    print(wisdom)
    print(f"------------------------------------")
    
    # Verify it came from the dream
    if "7777" in wisdom and "8080" in wisdom:
        print("\n✅ VERIFIED: The lesson was distilled, embedded, and accurately retrieved.")
    else:
        print("\n⚠️ PARTIAL: Wisdom recalled but content looks different.")
else:
    print("\n❌ FAILED: No wisdom recalled for the query.")

# Clean up
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)
