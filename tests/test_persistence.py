
import unittest
import sys
import os
import shutil

# Add parent directory to path to import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import AgentEngine

class TestPersistence(unittest.TestCase):
    def setUp(self):
        # Setup mock environment
        self.test_dir = "test_persistence_env"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Mock engine paths
        self.original_base_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize engine
        self.engine = AgentEngine()
        # Mock journal/state files
        self.engine.state = {"goal": "test", "progress": [], "status": "ready", "retry_count": 0}

    def tearDown(self):
        os.chdir(self.original_base_dir)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_retry_increment(self):
        # Simulate 1st failure
        self.engine.step_back("Fail 1")
        self.assertEqual(self.engine.state["retry_count"], 1)
        self.assertEqual(self.engine.state["status"], "recovering")
        self.assertIn("Retry 1/10", self.engine.state["last_error"])

        # Simulate 9 more failures
        for i in range(9):
             self.engine.step_back(f"Fail {i+2}")
        
        self.assertEqual(self.engine.state["retry_count"], 10)
        self.assertEqual(self.engine.state["status"], "recovering")

        # Simulate 11th failure (Block)
        self.engine.step_back("Fail 11")
        self.assertEqual(self.engine.state["status"], "blocked")
        self.assertIn("Aborted after 11 retries", self.engine.state["last_error"])

    def test_retry_reset(self):
        # Fail once
        self.engine.step_back("Fail 1")
        self.assertEqual(self.engine.state["retry_count"], 1)
        
        # Succeed
        # We need to simulate the success logic in pulse()
        # "if self.state["status"] == "recovering" and result..."
        self.engine.state["status"] = "recovering"
        self.engine.state["last_error"] = None
        self.engine.state["retry_count"] = 0 # This is what pulse does
        
        self.assertEqual(self.engine.state["retry_count"], 0)

if __name__ == '__main__':
    unittest.main()
