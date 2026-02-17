
import requests
import json
import os

BASE_URL = "http://localhost:7777" # Assuming default port, or I should check config. But server might be running on 7777.

def verify_context_update():
    print(f"Testing context update on {BASE_URL}...")
    
    # 1. Get current config
    try:
        resp = requests.get(f"{BASE_URL}/api/config")
        if resp.status_code != 200:
            print(f"Failed to get config: {resp.text}")
            return
        
        original_config = resp.json()
        original_ctx = original_config.get("num_ctx", 2048)
        print(f"Original context: {original_ctx}")
        
    except Exception as e:
        print(f"Error connecting: {e}")
        return

    # 2. Update to 1M (1048576)
    target_ctx = 1048576
    print(f"Updating to {target_ctx}...")
    resp = requests.post(f"{BASE_URL}/api/config", json={"num_ctx": target_ctx})
    if resp.status_code != 200:
        print(f"Update failed: {resp.text}")
        return

    # 3. Verify
    resp = requests.get(f"{BASE_URL}/api/config")
    new_config = resp.json()
    new_ctx = new_config.get("num_ctx")
    
    if new_ctx == target_ctx:
        print("SUCCESS: Context updated to 1M.")
    else:
        print(f"FAILURE: Context is {new_ctx}, expected {target_ctx}")

    # 4. Restore
    print(f"Restoring to {original_ctx}...")
    requests.post(f"{BASE_URL}/api/config", json={"num_ctx": original_ctx})
    print("Restored.")

if __name__ == "__main__":
    verify_context_update()
