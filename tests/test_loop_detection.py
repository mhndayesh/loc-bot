import unittest
import json
import hashlib
import sys
import os

# Add parent directory to path to import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import LoopDetector

class TestLoopDetector(unittest.TestCase):
    def setUp(self):
        self.detector = LoopDetector()

    def test_immediate_repetition(self):
        # Action 1
        self.detector.record("read_file", ["a.txt"], "content")
        self.assertIsNone(self.detector.detect())
        
        # Action 2 (Repeat 1)
        self.detector.record("read_file", ["a.txt"], "content")
        self.assertIsNone(self.detector.detect())
        
        # Action 3 (Repeat 2 -> Trigger)
        self.detector.record("read_file", ["a.txt"], "content")
        alert = self.detector.detect()
        self.assertIsNotNone(alert)
        self.assertIn("SYSTEM ALERT", alert)
        self.assertIn("3 times", alert)

    def test_ping_pong(self):
        # A
        self.detector.record("ls", [], "file1")
        # B
        self.detector.record("pwd", [], "/root")
        # A
        self.detector.record("ls", [], "file1")
        # B
        self.detector.record("pwd", [], "/root")
        
        alert = self.detector.detect()
        self.assertIsNotNone(alert)
        self.assertIn("oscillating", alert)

    def test_no_loop(self):
        self.detector.record("cmd1", [], "r1")
        self.detector.record("cmd2", [], "r2")
        self.detector.record("cmd3", [], "r3")
        self.assertIsNone(self.detector.detect())

if __name__ == '__main__':
    unittest.main()
