
import unittest
import os
import sys
import shutil

# Ensure we can import skills
sys.path.append(os.getcwd())
from skills import env_manager, run_in_env

class TestEnvironmentStress(unittest.TestCase):
    ENV_NAME = "stress_test_env"

    def setUp(self):
        # Ensure clean slate
        env_manager.run("delete", self.ENV_NAME)

    def tearDown(self):
        # Cleanup
        env_manager.run("delete", self.ENV_NAME)

    def test_full_lifecycle(self):
        print(f"\n[STRESS] 1. Creating environment '{self.ENV_NAME}'...")
        res = env_manager.run("create", self.ENV_NAME, env_type="python")
        print(res)
        self.assertIn("created at", res)

        print(f"[STRESS] 2. Installing 'requests' in '{self.ENV_NAME}'...")
        res = env_manager.run("install", self.ENV_NAME, "requests")
        print(res)
        self.assertIn("Installed requests", res)

        print(f"[STRESS] 3. Running code in '{self.ENV_NAME}'...")
        # Check if requests is importable
        cmd = "python -c \"import requests; print('REQUESTS_OK')\""
        output = run_in_env.run(self.ENV_NAME, cmd)
        print(f"Output: {output.strip()}")
        self.assertIn("REQUESTS_OK", output)

        print(f"[STRESS] 4. Verifying MAP.md update...")
        with open("MAP.md", "r") as f:
            content = f.read()
            self.assertIn(self.ENV_NAME, content)
            self.assertIn("requests", content)
        print("MAP.md contains environment details.")

if __name__ == "__main__":
    unittest.main()
