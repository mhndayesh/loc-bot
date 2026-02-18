import os
import time
import json
import threading
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import save_json, read_file_safe
from engine import AgentEngine

TEST_FILE = "test_atomic.json"

def test_atomic_write_concurrency():
    """Verify that simultaneous writes do not corrupt the file."""
    print("Testing atomic writes...")
    
    # 1. Setup
    initial_data = {"counter": 0}
    save_json(TEST_FILE, initial_data)
    
    # 2. Concurrent writers
    def writer(env_id):
        for i in range(50):
            # Read-Modify-Write (simulated race, but file integrity should hold)
            try:
                data = json.loads(read_file_safe(TEST_FILE))
                data["counter"] += 1
                save_json(TEST_FILE, data)
            except Exception as e:
                print(f"Writer {env_id} error: {e}")
    
    threads = []
    for i in range(4):
        t = threading.Thread(target=writer, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # 3. Verify integrity
    try:
        with open(TEST_FILE, "r") as f:
            final_data = json.load(f)
        print(f"Final counter: {final_data['counter']}")
        print("PASS: File is valid JSON.")
    except json.JSONDecodeError:
        print("FAIL: File corrupted!")
    except Exception as e:
        print(f"FAIL: {e}")
    finally:
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

if __name__ == "__main__":
    test_atomic_write_concurrency()
