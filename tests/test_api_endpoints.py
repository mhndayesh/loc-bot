import sys
import os
import json
import unittest
import requests
import threading
import time
from http.server import HTTPServer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import AgentAPIHandler

# We need to run the server in a separate thread for testing
class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Starting Test Server...")
        cls.server = HTTPServer(("127.0.0.1", 9999), AgentAPIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(1) # Wait for server start
        cls.base_url = "http://127.0.0.1:9999/api"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_status_endpoint(self):
        """Test GET /api/status"""
        resp = requests.get(f"{self.base_url}/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("config", data)
        self.assertIn("state", data)
        print("PASS: /api/status returned 200 OK")

    def test_goal_endpoint(self):
        """Test POST /api/goal"""
        # Set goal
        resp = requests.post(f"{self.base_url}/goal", json={"goal": "API Test Goal"})
        self.assertEqual(resp.status_code, 200)
        
        # Verify
        resp = requests.get(f"{self.base_url}/status")
        self.assertEqual(resp.json()["state"]["goal"], "API Test Goal")
        print("PASS: /api/goal updated goal")

    def test_chat_endpoint_simple(self):
        """Test POST /api/chat with simple message"""
        # We expect either 200 (Ollama running) or 502 (Ollama not running)
        # We just want to ensure the server logic doesn't crash (500).
        resp = requests.post(f"{self.base_url}/chat", json={
            "message": "Hello", 
            "history": []
        })
        self.assertIn(resp.status_code, [200, 502])
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("reply", data)
        print(f"PASS: /api/chat returned {resp.status_code}")

    def test_config_endpoint(self):
        """Test POST /api/config"""
        resp = requests.post(f"{self.base_url}/config", json={"test_key": "test_value"})
        self.assertEqual(resp.status_code, 200)
        
        resp = requests.get(f"{self.base_url}/status")
        self.assertEqual(resp.json()["config"].get("test_key"), "test_value")
        print("PASS: /api/config updated settings")

if __name__ == "__main__":
    unittest.main()
