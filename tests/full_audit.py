
import unittest
import os
import sys
import json
import shutil
import time
import subprocess
from skills import env_manager, run_in_env

# Add parent dir to path to import engine/server modules if needed
sys.path.append(os.getcwd())

class TestFullAudit(unittest.TestCase):
    DS_ENV = "audit_py_env"
    
    def setUp(self):
        # Clean slate
        env_manager.run("delete", self.DS_ENV)
        
    def tearDown(self):
        # Cleanup
        env_manager.run("delete", self.DS_ENV)

    def test_01_config_integrity(self):
        """Verify config.json exists and has valid schema."""
        print("\n[AUDIT] 1. Checking Config Integrity...")
        self.assertTrue(os.path.exists("config.json"), "config.json missing")
        with open("config.json", "r") as f:
            config = json.load(f)
        
        self.assertIn("heartbeat_interval", config)
        self.assertIn("provider", config)
        self.assertIsInstance(config.get("heartbeat_interval"), int)
        print("✅ Config OK")

    def test_02_environment_stress(self):
        """Stress test environment creation and execution."""
        print(f"\n[AUDIT] 2. Python Env Stress Test ('{self.DS_ENV}')...")
        
        # Create
        res = env_manager.run("create", self.DS_ENV, env_type="python")
        self.assertIn("created at", res)
        
        # Install
        res = env_manager.run("install", self.DS_ENV, "colorama")
        self.assertIn("Installed colorama", res)
        
        # Run
        cmd = "python -c \"import colorama; print('STRESS_TEST_OK')\""
        output = run_in_env.run(self.DS_ENV, cmd)
        self.assertIn("STRESS_TEST_OK", output)
        print("✅ Environment Stress OK")

    def test_03_heartbeat_silence_logic(self):
        """Verify engine.py handles silent replies correctly."""
        # This is a static analysis check or a dry-run check
        print("\n[AUDIT] 3. Verifying Silence Logic in engine.py...")
        
        with open("engine.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        # Check for the Chat Fail-safe
        self.assertIn('if not clean_reply or not clean_reply.strip():', content, "Chat fail-safe missing")
        self.assertIn('clean_reply = "*...*"', content, "Fallback placeholder missing")
        
        # Check for Silence Scope
        self.assertIn('if mode != "chat" and ("[SILENT_OK]"', content, "Silence not scoped to non-chat mode")
        
        print("✅ Silence Logic Code matches requirements")

    def test_04_log_file_rotation(self):
        """Verify log rotation is working (no thousands of files)."""
        print("\n[AUDIT] 4. Verifying Log Rotation...")
        mem_dir = "memory"
        if os.path.exists(mem_dir):
            pulse_files = [f for f in os.listdir(mem_dir) if f.startswith("pulse_")]
            # It's okay if it's less, but shouldn't be massive.
            # The cleanup limit is 50. Let's assert it's under 100 just to be safe.
            count = len(pulse_files)
            print(f"   Pulse log count: {count}")
            self.assertLess(count, 100, f"Log rotation failed, found {count} files")
        print("✅ Log Rotation OK")

if __name__ == "__main__":
    unittest.main()
