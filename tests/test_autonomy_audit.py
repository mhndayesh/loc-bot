
import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from server import _build_chat_system_prompt
from engine import AgentEngine

class TestAutonomyAudit(unittest.TestCase):
    
    def test_server_prompt_authority(self):
        """Verify server.py prompt contains System Authority."""
        prompt = _build_chat_system_prompt(thinking_enabled=True)
        self.assertIn("## System Authority", prompt)
        self.assertIn("NEVER claim you are a restricted text-based AI", prompt)
        self.assertIn("LOCAL OWNER", prompt)

    def test_server_dynamic_skills(self):
        """Verify server.py prompt discovers custom skills."""
        prompt = _build_chat_system_prompt(thinking_enabled=True)
        self.assertIn("### Custom Skill Details", prompt)
        # Should see at least one of our skills
        self.assertIn("env_manager.py", prompt)
        self.assertIn("run_in_env.py", prompt)

    def test_engine_prompt_authority(self):
        """Verify engine.py prompt contains System Authority."""
        e = AgentEngine()
        prompt = e.get_full_prompt(mode="chat")
        self.assertIn("## System Authority", prompt)
        self.assertIn("LOCAL OWNER", prompt)
        self.assertIn("NEVER apologize for 'limitations'", prompt)

    def test_engine_dynamic_skills(self):
        """Verify engine.py prompt discovers custom skills."""
        e = AgentEngine()
        prompt = e.get_full_prompt(mode="chat")
        self.assertIn("### Custom Skill Details", prompt)
        self.assertTrue(any("env_manager.py" in line for line in prompt.split("\n")))
        
    def test_env_persistence_text(self):
        """Verify the prompt mentions persistence explicitly."""
        prompt = _build_chat_system_prompt(thinking_enabled=False)
        self.assertIn("Your skills and environments carry over", prompt)

    def test_edge_case_skills(self):
        """Verify discovery with weird skill file structures."""
        # Create a temp skill
        temp_skill = os.path.join("skills", "temp_audit_skill.py")
        try:
            with open(temp_skill, "w") as f:
                f.write('def run(name):\n    """My special temp skill."""\n    pass')
            
            prompt = _build_chat_system_prompt(thinking_enabled=True)
            self.assertIn("temp_audit_skill.py", prompt)
            self.assertIn("def run(name)", prompt) 
        except AssertionError as e:
            print(f"DEBUG PROMPT:\n{prompt}")
            raise e
        finally:
            if os.path.exists(temp_skill):
                os.remove(temp_skill)

    def test_multiline_docstring_skill(self):
        """Verify discovery handles multiline docstrings (grabs first line)."""
        temp_skill = os.path.join("skills", "temp_multi_skill.py")
        try:
            with open(temp_skill, "w") as f:
                f.write('"""\nFirst line of doc\nSecond line\n"""\ndef run(): pass')
            
            prompt = _build_chat_system_prompt(thinking_enabled=True)
            self.assertIn("First line of doc", prompt)
        finally:
            if os.path.exists(temp_skill):
                os.remove(temp_skill)

if __name__ == "__main__":
    unittest.main()
