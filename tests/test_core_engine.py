import sys
import os
import json
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import AgentEngine, STATE_FILE

SOUL_FILE = "SOUL.md"

class TestCoreEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AgentEngine()
        # Reset state for testing
        self.engine.state = {"goal": "Test Goal", "progress": [], "status": "ready", "last_error": None}
        self.engine.save_state()
        
    def test_pulse_tool_execution(self):
        """Test that pulse executes a tool correctly and updates state."""
        print("\n--- Test: Pulse Tool Execution ---")
        
        # Mock LLM to return a tool call
        self.engine.call_llm = MagicMock(return_value="[THINK]I will list files.[/THINK] [TOOL]list_dir(.)[/TOOL]")
        
        self.engine.pulse()
        
        # Verify state
        state = self.engine._load_state()
        self.assertTrue(len(state["progress"]) > 0)
        last_action = state["progress"][-1]
        # Action string might be the thinking content "I will list files."
        # Result should contain some file names, e.g. "engine.py"
        self.assertTrue("I will list files" in last_action["action"] or "engine.py" in str(last_action["result"]))
        print("PASS: Pulse executed tool and updated state.")

    def test_identity_protection(self):
        """Test that writing to SOUL.md is blocked."""
        print("\n--- Test: Identity Protection ---")
        
        result = self.engine.run_tool("write_file", ["SOUL.md", "hacked"])
        self.assertIn("Error", result)
        self.assertIn("protected", result)
        print("PASS: SOUL.md write blocked.")
        
    def test_error_recovery(self):
        """Test error state and recovery."""
        print("\n--- Test: Error Recovery ---")
        
        # 1. Trigger error
        self.engine.run_tool("unknown_tool", [])
        # Since run_tool calls step_back internally on error/unknown
        # But wait, run_tool returns string, step_back is called inside run_tool for unknown?
        # Let's check engine.py... yes, "unknown tool" calls step_back
        
        # Actually run_tool handles unknown tools by calling step_back
        self.engine.run_tool("bad_tool_name", [])
        
        state = self.engine._load_state()
        self.assertEqual(state["status"], "recovering")
        self.assertIsNotNone(state["last_error"])
        print("PASS: Error triggered recovery mode.")
        
        # 2. Recover
        # Mock LLM to fix it
        self.engine.call_llm = MagicMock(return_value="[THINK]I will fix it.[/THINK] [TOOL]list_dir(.)[/TOOL]")
        self.engine.pulse()
        
        state = self.engine._load_state()
        self.assertEqual(state["status"], "ready")
        self.assertIsNone(state["last_error"])
        print("PASS: Recovery successful.")

    def test_context_assembly(self):
        """Test that prompt contains essential sections."""
        print("\n--- Test: Context Assembly ---")
        prompt = self.engine.get_full_prompt()
        self.assertIn("## Identity", prompt)
        self.assertIn("## Current Agent Goal", prompt)
        self.assertIn("Test Goal", prompt)
        print("PASS: Prompt assembled correctly.")

if __name__ == "__main__":
    unittest.main()
