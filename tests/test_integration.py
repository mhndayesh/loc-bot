
import unittest
import requests
import json
import time
import threading
import os
import signal
import sys
from http.server import HTTPServer

# Ensure we can import server
sys.path.append(os.getcwd())
from server import AgentAPIHandler

BASE_URL = "http://localhost:7778"  # Use a different port for testing

class TestAgentAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server = HTTPServer(("127.0.0.1", 7778), AgentAPIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        print("Test server started on port 7778")
        time.sleep(1) # Give it a moment to start

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        print("Test server stopped")

    def test_status_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("state", data)
        self.assertIn("config", data)
        self.assertIn("heartbeat_running", data)

    def test_config_endpoint(self):
        # Test GET
        resp = requests.get(f"{BASE_URL}/api/config")
        self.assertEqual(resp.status_code, 200)
        config = resp.json()
        self.assertIn("model", config)

        # Test POST (update)
        new_interval = config.get("heartbeat_interval", 60) + 1
        resp = requests.post(f"{BASE_URL}/api/config", json={"heartbeat_interval": new_interval})
        self.assertEqual(resp.status_code, 200)
        
        # Verify update
        resp = requests.get(f"{BASE_URL}/api/config")
        self.assertEqual(resp.json()["heartbeat_interval"], new_interval)

    def test_chat_session_flow(self):
        # 1. Create/Save Session
        session_data = {
            "id": "test_session_1",
            "title": "Test Chat",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        resp = requests.post(f"{BASE_URL}/api/chat/save", json=session_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], "test_session_1")

        # 2. List Sessions
        resp = requests.post(f"{BASE_URL}/api/chat/sessions") # Using POST as implemented
        self.assertEqual(resp.status_code, 200)
        sessions = resp.json()["sessions"]
        self.assertTrue(any(s["id"] == "test_session_1" for s in sessions))

        # 3. Load Session
        resp = requests.post(f"{BASE_URL}/api/chat/load", json={"id": "test_session_1"})
        self.assertEqual(resp.status_code, 200)
        loaded = resp.json()
        self.assertEqual(loaded["id"], "test_session_1")
        self.assertEqual(loaded["messages"][0]["content"], "Hello")

        # 4. Delete Session
        resp = requests.post(f"{BASE_URL}/api/chat/delete", json={"id": "test_session_1"})
        self.assertEqual(resp.status_code, 200)

        # 5. Verify Deletion
        resp = requests.post(f"{BASE_URL}/api/chat/load", json={"id": "test_session_1"})
        self.assertEqual(resp.status_code, 404)

    def test_chat_endpoint_structure(self):
        # Determine if we can actually call LLM or just Mock it
        # For now, we test the structure. If no LLM running, it might verify error handling.
        payload = {
            "message": "Hello",
            "history": []
        }
        try:
            resp = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=5)
            # It might fail if no LLM is running on localhost:11434, but we check if it handles it gracefully
            if resp.status_code == 200:
                self.assertIn("reply", resp.json())
            else:
                self.assertIn("error", resp.json()) # 502 if LLM fails
        except requests.exceptions.Timeout:
            print("Chat endpoint timed out (expected if LLM is slow/off)")

    def test_provider_switch(self):
        resp = requests.post(f"{BASE_URL}/api/provider", json={"provider": "ollama"})
        self.assertEqual(resp.status_code, 200)
        
        resp = requests.get(f"{BASE_URL}/api/config")
        self.assertEqual(resp.json()["provider"], "ollama")

if __name__ == "__main__":
    unittest.main()
