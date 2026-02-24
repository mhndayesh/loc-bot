
import sys
import os
sys.path.append(os.getcwd())
try:
    from engine import AgentEngine
    engine = AgentEngine()
    print(engine._sync_skills_file())
except Exception as e:
    print(f"Failed: {e}")
