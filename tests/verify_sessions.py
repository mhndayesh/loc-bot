
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
from server import AgentAPIHandler, MEMORY_DIR

BASE_URL = "http://localhost:7779"  # Use port 7779 for this test

class TestSessionAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server = HTTPServer(("127.0.0.1", 7779), AgentAPIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        print(f"Session Test Server started on {BASE_URL}")
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        print("Session Test Server stopped")

    def test_session_app_flow(self):
        """Simulate the exact flow of app.js"""
        
        # 1. Save a new session
        print("\nTesting /api/chat/save...")
        session_id = f"test_sess_{int(time.time())}"
        save_payload = {
            "id": session_id,
            "title": "Integration Test Chat",
            "messages": [
                {"role": "user", "content": "Hello agent"},
                {"role": "assistant", "content": "Hello user"}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/chat/save", json=save_payload)
        self.assertEqual(resp.status_code, 200, f"Save failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data["id"], session_id)
        print("✓ Save successful")

        # 2. List sessions
        print("Testing /api/chat/sessions...")
        resp = requests.post(f"{BASE_URL}/api/chat/sessions")
        self.assertEqual(resp.status_code, 200, f"List failed: {resp.text}")
        sessions = resp.json().get("sessions", [])
        found = next((s for s in sessions if s["id"] == session_id), None)
        self.assertIsNotNone(found, "Saved session not found in list")
        self.assertEqual(found["title"], "Integration Test Chat")
        print(f"✓ List successful (found {len(sessions)} sessions)")

        # 3. Load session
        print("Testing /api/chat/load...")
        resp = requests.post(f"{BASE_URL}/api/chat/load", json={"id": session_id})
        self.assertEqual(resp.status_code, 200, f"Load failed: {resp.text}")
        loaded = resp.json()
        self.assertEqual(loaded["id"], session_id)
        self.assertEqual(len(loaded["messages"]), 2)
        print("✓ Load successful")

        # 4. Delete session
        print("Testing /api/chat/delete...")
        resp = requests.post(f"{BASE_URL}/api/chat/delete", json={"id": session_id})
        self.assertEqual(resp.status_code, 200, f"Delete failed: {resp.text}")
        print("✓ Delete successful")

        # 5. Verify deletion
        resp = requests.post(f"{BASE_URL}/api/chat/load", json={"id": session_id})
        self.assertEqual(resp.status_code, 404, "Session should be gone")
        print("✓ Verify deletion successful")

if __name__ == "__main__":
    unittest.main()
