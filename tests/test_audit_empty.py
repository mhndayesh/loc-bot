
import unittest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Add parent dir to path
sys.path.append(os.getcwd())
from engine import AgentEngine, STATE_FILE

class TestEmptyResponseAudit(unittest.TestCase):
    def setUp(self):
        # Setup mock state for testing
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                self.original_state = json.load(f)
        else:
            self.original_state = {}
            
    def tearDown(self):
        # Restore state
        with open(STATE_FILE, "w") as f:
            json.dump(self.original_state, f)

    @patch('engine.AgentEngine.call_llm')
    def test_chat_empty_fail_safe(self, mock_llm):
        """Verify that an empty string in chat mode results in '*...*'."""
        mock_llm.return_value = "   " # Whitespace only
        e = AgentEngine()
        e.pulse(mode="chat")
        
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        
        self.assertEqual(state.get("last_reply"), "*...*", "Chat fail-safe failed to provide placeholder for empty reply")

    @patch('engine.AgentEngine.call_llm')
    def test_chat_silent_ok_ignored(self, mock_llm):
        """Verify that [SILENT_OK] in chat mode is NOT treated as a silent exit."""
        mock_llm.return_value = "[SILENT_OK]"
        e = AgentEngine()
        e.pulse(mode="chat")
        
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            
        self.assertNotEqual(state.get("last_reply"), "", "Chat mode exited silently on [SILENT_OK]")

    @patch('engine.AgentEngine.call_llm')
    def test_heartbeat_silence_works(self, mock_llm):
        """Verify that heartbeat mode DOES exit early on [SILENT_OK]."""
        mock_llm.return_value = "[SILENT_OK]"
        e = AgentEngine()
        
        # Reset last_reply to something known
        e.state["last_reply"] = "PREVIOUS"
        e.save_state()
        
        e.pulse(mode="heartbeat")
        
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            
        # In heartbeat mode, it should exit BEFORE updating last_reply
        self.assertEqual(state.get("last_reply"), "PREVIOUS", "Heartbeat mode failed to stay silent on [SILENT_OK]")

    @patch('engine.AgentEngine.call_llm')
    def test_tool_auto_summary(self, mock_llm):
        """Verify that a tool call with no natural language generates an auto-summary."""
        mock_llm.return_value = "[TOOL]read_file(target='test.txt')[/TOOL]"
        e = AgentEngine()
        # Mock the tool runner to return success
        with patch.object(AgentEngine, 'parse_and_run', return_value="File content here"):
            e.pulse(mode="chat")
        
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            
        self.assertIn("*Action: read_file(target='test.txt') -> Success*", state.get("last_reply"), "Tool auto-summary failed")

if __name__ == "__main__":
    unittest.main()
