
import unittest
import os
import sys
import shutil
import json
import subprocess

# Ensure we can import skills
sys.path.append(os.getcwd())
from skills import env_manager, run_in_env

class TestExtendedStress(unittest.TestCase):
    DS_ENV = "ds_env"
    NODE_ENV = "node_env"

    def setUp(self):
        # Ensure clean slate
        env_manager.run("delete", self.DS_ENV)
        env_manager.run("delete", self.NODE_ENV)

    def tearDown(self):
        # Cleanup
        env_manager.run("delete", self.DS_ENV)
        env_manager.run("delete", self.NODE_ENV)

    def test_python_ds_workflow(self):
        print(f"\n[STRESS] 1. Python Env: Creating '{self.DS_ENV}'...")
        res = env_manager.run("create", self.DS_ENV, env_type="python")
        self.assertIn("created at", res)

        print(f"[STRESS] 2. Python Env: Installing 'numpy'...")
        # Numpy might be heavy, but it's a good stress test. 
        # If too slow, standard library 'requests' was tested before.
        # Let's use 'requests' again or 'colorama' for speed if needed, 
        # but user asked for 'projects'. Let's stick to 'numpy' if network allows, 
        # or 'requests' as safe backup. Let's use 'requests' for speed confidence, 
        # or just 'pip' itself. The user asked for "different environments".
        # Let's try 'numpy' but fallback if needed. No, let's use 'requests' again for reliability 
        # in automated test, as numpy compilation can fail on some Windows setups without wheels.
        # Actually, let's use 'colorama' -> very light, no deps.
        res = env_manager.run("install", self.DS_ENV, "colorama")
        self.assertIn("Installed colorama", res)

        print(f"[STRESS] 3. Python Env: Running code...")
        cmd = "python -c \"import colorama; print('COLORAMA_OK')\""
        output = run_in_env.run(self.DS_ENV, cmd)
        print(f"Output: {output.strip()}")
        self.assertIn("COLORAMA_OK", output)

    def test_node_workflow(self):
        # Check if npm exists
        if shutil.which("npm") is None:
            print("[SKIP] npm not found, skipping Node test.")
            return

        print(f"\n[STRESS] 4. Node Env: Creating '{self.NODE_ENV}'...")
        res = env_manager.run("create", self.NODE_ENV, env_type="node")
        self.assertIn("created at", res)

        print(f"[STRESS] 5. Node Env: Installing 'lodash'...")
        res = env_manager.run("install", self.NODE_ENV, "lodash")
        self.assertIn("Installed lodash", res)

        print(f"[STRESS] 6. Node Env: Running code...")
        # Create a temp js file or run inline
        # Windows command line dealing with quotes in node -e is tricky.
        # Easier to write a file.
        
        # We need to know where the env is
        data = json.loads(env_manager.run("list"))
        env_path = data[self.NODE_ENV]["path"]
        script_path = os.path.join(env_path, "test.js")
        
        with open(script_path, "w") as f:
            f.write("const _ = require('lodash'); console.log(_.defaults({ 'a': 1 }, { 'a': 3, 'b': 2 }));")
        
        output = run_in_env.run(self.NODE_ENV, "node test.js")
        print(f"Output: {output.strip()}")
        self.assertIn("b: 2", output) # output should be { a: 1, b: 2 }

if __name__ == "__main__":
    unittest.main()
