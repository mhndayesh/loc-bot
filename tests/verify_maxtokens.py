
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
from server import AgentAPIHandler, CONFIG_FILE, load_json

BASE_URL = "http://localhost:7781"

class TestMaxTokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server = HTTPServer(("127.0.0.1", 7781), AgentAPIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        print(f"MaxTokens Test Server started on {BASE_URL}")
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        print("MaxTokens Test Server stopped")

    def test_maxtokens_update(self):
        # 1. Update to 512k
        target_tokens = 524288
        print(f"Testing update to {target_tokens}...")
        resp = requests.post(f"{BASE_URL}/api/config", json={"max_tokens": target_tokens})
        self.assertEqual(resp.status_code, 200, f"Update failed: {resp.text}")

        # 2. Verify via API
        resp = requests.get(f"{BASE_URL}/api/config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["max_tokens"], target_tokens)
        print("✓ API confirms 512k max tokens")

        # 3. Verify via File
        config = load_json(CONFIG_FILE)
        self.assertEqual(config["max_tokens"], target_tokens)
        print("✓ File write confirms 512k max tokens")

        # 4. Restore to 0 (unlimited)
        requests.post(f"{BASE_URL}/api/config", json={"max_tokens": 0})

if __name__ == "__main__":
    unittest.main()
