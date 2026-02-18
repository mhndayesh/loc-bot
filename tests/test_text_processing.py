
import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import AgentEngine

class TestTextProcessing(unittest.TestCase):
    def setUp(self):
        self.engine = AgentEngine()

    def test_strip_thinking(self):
        """Test removal of [THINK] blocks."""
        # Case 1: Simple think block
        text = "[THINK]This is internal.[/THINK] This is public."
        self.assertEqual(self.engine.strip_thinking(text), "This is public.")

        # Case 2: Multiline think block
        text = "[THINK]\nLine 1\nLine 2\n[/THINK]Hello."
        self.assertEqual(self.engine.strip_thinking(text), "Hello.")

        # Case 3: No think block
        text = "Just text."
        self.assertEqual(self.engine.strip_thinking(text), "Just text.")

        # Case 4: Multiple blocks (rare but possible)
        text = "[THINK]1[/THINK] A [THINK]2[/THINK] B"
        self.assertEqual(self.engine.strip_thinking(text), "A  B")

        # Case 5: Empty think block
        text = "[THINK][/THINK] Hi"
        self.assertEqual(self.engine.strip_thinking(text), "Hi")

    def test_parse_thinking(self):
        """Test extraction of [THINK] blocks."""
        text = "[THINK]My thoughts.[/THINK] Hello"
        self.assertEqual(self.engine.parse_thinking(text), "My thoughts.")

        text = "No thoughts"
        self.assertIsNone(self.engine.parse_thinking(text))

if __name__ == "__main__":
    unittest.main()
