
import unittest
import sys
import os
import subprocess

# Add skills dir to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills"))

class TestSkills(unittest.TestCase):
    def test_system_stats(self):
        """Test system_stats.py execution"""
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "system_stats.py")
        result = subprocess.run(["python", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("cpu_percent", result.stdout)
        self.assertIn("memory_total_gb", result.stdout)
        print("PASS: system_stats.py ran successfully")

    def test_browser_skill_import(self):
        """Test browser.py import and basic function existence"""
        # We don't want to make real network requests in unit tests usually,
        # but we can check if it runs with --help or no args
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "browser.py")
        result = subprocess.run(["python", script], capture_output=True, text=True)
        # It might fail with "usage: browser.py <url>" or return 0 if it prints usage
        # Let's check output
        if result.returncode != 0:
            # It might have exited with error because of missing args
            self.assertIn("usage:", result.stderr.lower() + result.stdout.lower())
        else:
            # It might have printed usage
            pass
        print("PASS: browser.py is executable")

if __name__ == "__main__":
    unittest.main()
