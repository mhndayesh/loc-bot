
import unittest
import sys
import os
import shutil
from unittest.mock import MagicMock

# Add parent directory to path to import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import AgentEngine

class TestPlanningStress(unittest.TestCase):
    def setUp(self):
        # Setup mock environment
        self.test_dir = "test_planning_env"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Mock engine paths
        self.original_base_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize engine
        self.engine = AgentEngine()
        # Ensure clean state
        self.engine.state = {"goal": "build app", "progress": [], "plan": [], "status": "ready"}

    def tearDown(self):
        os.chdir(self.original_base_dir)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_full_plan_lifecycle(self):
        # 1. Create Plan
        # Mock LLM response for creating a plan
        plan_steps = ["create file", "verify file"]
        response_1 = f"I will plan. [TOOL]create_plan({plan_steps})[/TOOL]"
        
        # We manually trigger parse_and_run to simulate the engine processing the LLM's choice
        self.engine.parse_and_run(response_1)
        
        self.assertEqual(len(self.engine.state["plan"]), 2)
        self.assertEqual(self.engine.state["plan"][0]["step"], "create file")
        self.assertEqual(self.engine.state["plan"][0]["status"], "todo")

        # 2. Execute Step 1 & Mark Done
        response_2 = "Step 1 done. [TOOL]update_plan_step(0, 'done')[/TOOL]"
        self.engine.parse_and_run(response_2)
        
        self.assertEqual(self.engine.state["plan"][0]["status"], "done")
        self.assertEqual(self.engine.state["plan"][1]["status"], "todo")

        # 3. Fail Step 2 & Replan
        # Mark step 2 as failed
        response_3 = "Step 2 failed. [TOOL]update_plan_step(1, 'failed')[/TOOL]"
        self.engine.parse_and_run(response_3)
        self.assertEqual(self.engine.state["plan"][1]["status"], "failed")

        # Replan from index 1: replace "verify file" with "fix file", "verify again"
        new_steps = ["fix file", "verify again"]
        response_4 = f"Replanning. [TOOL]replan(1, {new_steps})[/TOOL]"
        self.engine.parse_and_run(response_4)
        
        # Plan should now be: [create file (done), fix file (todo), verify again (todo)]
        current_plan = self.engine.state["plan"]
        self.assertEqual(len(current_plan), 3)
        self.assertEqual(current_plan[0]["step"], "create file")
        self.assertEqual(current_plan[0]["status"], "done")
        self.assertEqual(current_plan[1]["step"], "fix file")
        self.assertEqual(current_plan[1]["status"], "todo")
        self.assertEqual(current_plan[2]["step"], "verify again")

if __name__ == '__main__':
    unittest.main()
