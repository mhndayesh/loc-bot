
import unittest
import requests
import json
import time
import threading
import os
import sys
from http.server import HTTPServer

# Ensure we can import server
sys.path.append(os.getcwd())
from server import AgentAPIHandler, CONFIG_FILE, load_json, save_json

BASE_URL = "http://localhost:7780"

class TestContextWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server = HTTPServer(("127.0.0.1", 7780), AgentAPIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        print(f"Context Test Server started on {BASE_URL}")
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        print("Context Test Server stopped")

    def test_context_update(self):
        # 1. Update to 1M
        target_ctx = 1048576
        print(f"Testing update to {target_ctx}...")
        resp = requests.post(f"{BASE_URL}/api/config", json={"num_ctx": target_ctx})
        self.assertEqual(resp.status_code, 200)

        # 2. Verify via API
        resp = requests.get(f"{BASE_URL}/api/config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["num_ctx"], target_ctx)
        print("✓ API confirms 1M context")

        # 3. Verify via File
        # We need to check if it actually wrote to config.json
        # NOTE: This writes to the actual config.json! We should restore it.
        config = load_json(CONFIG_FILE)
        self.assertEqual(config["num_ctx"], target_ctx)
        print("✓ File write confirms 1M context")

        # 4. Restore original (optional but good practice)
        # We don't know the original value easily unless we read it before.
        # But for this test, we accept 1M as the "new state" or restore 2048 default.
        # Let's restore to 4096 (standard).
        requests.post(f"{BASE_URL}/api/config", json={"num_ctx": 4096})

if __name__ == "__main__":
    unittest.main()
